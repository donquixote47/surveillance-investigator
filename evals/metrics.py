"""Metrics for a dataset run (data doc section 4.2). Pure functions over per-alert rows, so the same code scores
the agent, the threshold baseline and "escalate everything", and the tests need no AWS.

A row is one alert joined with its label and with what the agent wrote to `cases`:
    alert_id, truth, injected_scenario, expected_disposition, trader_role,
    proposed (CLOSE_FP | ESCALATE | DRAFT_STOR | None), confidence, status (ok | no_proposal | error),
    duration_s, wall_s, input_tokens, output_tokens, model_calls, n_tool_calls, n_rejections, memory_used
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from statistics import mean, median
from typing import Any

TRUE_ABUSE = "TRUE_ABUSE"
FALSE_POSITIVE = "FALSE_POSITIVE"
CLOSE = "CLOSE_FP"
ESCALATE = "ESCALATE"
DRAFT_STOR = "DRAFT_STOR"
DISPOSITIONS = (CLOSE, ESCALATE, DRAFT_STOR)

# Rough list prices per million tokens (in, out). Claude 5.5 is not in the Pricing API for eu-west-2 (checked
# 2026-11-05: 768 products, none from Anthropic) and the pricing page renders its Anthropic table client-side, so
# these are the build plan's working figures, labelled as assumptions wherever they appear.
ASSUMED_PRICES_PER_M = {
    "haiku": (0.10, 0.50),
    "sonnet": (2.00, 10.00),
    "opus": (4.00, 20.00),
}


def price_for(model_id: str | None) -> tuple[float, float] | None:
    m = (model_id or "").lower()
    for k, v in ASSUMED_PRICES_PER_M.items():
        if k in m:
            return v
    return None


def _rate(num: int, den: int) -> float | None:
    return None if den == 0 else num / den


def _pct(x: float | None, nd: int = 1) -> str:
    return "n/a" if x is None else f"{100 * x:.{nd}f}%"


def _p(values: list[float], q: float) -> float | None:
    vals = sorted(v for v in values if v is not None and not math.isnan(v))
    if not vals:
        return None
    k = (len(vals) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return round(vals[lo] if lo == hi else vals[lo] + (vals[hi] - vals[lo]) * (k - lo), 1)


def direction(disp: str | None) -> str | None:
    """Collapse a disposition to the truth it implies: CLOSE_FP says FALSE_POSITIVE, the other two say TRUE_ABUSE."""
    if disp is None:
        return None
    return FALSE_POSITIVE if disp == CLOSE else TRUE_ABUSE


def compute(rows: list[dict[str, Any]], *, model_id: str | None = None) -> dict[str, Any]:
    """Headline metrics plus the per-scenario table. `proposed is None` means the agent recorded nothing: it is
    never a gate miss (nothing was closed) but counts against agreement, because the analyst does all the work."""
    n = len(rows)
    truth = Counter(r["truth"] for r in rows)
    n_true, n_fp = truth.get(TRUE_ABUSE, 0), truth.get(FALSE_POSITIVE, 0)
    proposed = Counter(r["proposed"] or "NONE" for r in rows)
    status = Counter(r.get("status", "ok") for r in rows)

    missed = sorted(r["alert_id"] for r in rows if r["truth"] == TRUE_ABUSE and r["proposed"] == CLOSE)
    gate_holds = not missed
    safe_closed = sum(1 for r in rows if r["truth"] == FALSE_POSITIVE and r["proposed"] == CLOSE)
    raw_safe_close = _rate(safe_closed, n_fp)
    safe_close = raw_safe_close if gate_holds else None

    escalations = [r for r in rows if r["proposed"] in (ESCALATE, DRAFT_STOR)]
    strong = [r for r in rows if r["proposed"] == DRAFT_STOR]
    escalation_precision = _rate(sum(1 for r in escalations if r["truth"] == TRUE_ABUSE), len(escalations))
    strong_precision = _rate(sum(1 for r in strong if r["truth"] == TRUE_ABUSE), len(strong))

    exact = sum(1 for r in rows if r["proposed"] is not None and r["proposed"] == r["expected_disposition"])
    direction_ok = sum(1 for r in rows if direction(r["proposed"]) == r["truth"])
    agreement = _rate(exact, n)
    unproposed_true = sorted(r["alert_id"] for r in rows if r["truth"] == TRUE_ABUSE and r["proposed"] is None)

    # expected x proposed confusion
    confusion: dict[str, dict[str, int]] = {e: dict.fromkeys([*DISPOSITIONS, "NONE"], 0) for e in DISPOSITIONS}
    for r in rows:
        confusion[r["expected_disposition"]][r["proposed"] or "NONE"] += 1

    per_scenario: dict[str, dict[str, Any]] = {}
    by_s: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_s[r["injected_scenario"]].append(r)
    for s, rs in sorted(by_s.items(), key=lambda kv: (kv[1][0]["truth"] != TRUE_ABUSE, kv[0])):
        c = Counter(r["proposed"] or "NONE" for r in rs)
        confs = [float(r["confidence"]) for r in rs if r.get("confidence") is not None]
        per_scenario[s] = {
            "n": len(rs),
            "truth": rs[0]["truth"],
            "expected": rs[0]["expected_disposition"],
            CLOSE: c.get(CLOSE, 0),
            ESCALATE: c.get(ESCALATE, 0),
            DRAFT_STOR: c.get(DRAFT_STOR, 0),
            "NONE": c.get("NONE", 0),
            "agreement": _rate(sum(1 for r in rs if r["proposed"] == r["expected_disposition"]), len(rs)),
            "close_rate": _rate(c.get(CLOSE, 0), len(rs)),
            "mean_confidence": round(mean(confs), 2) if confs else None,
            "missed": sorted(r["alert_id"] for r in rs if r["truth"] == TRUE_ABUSE and r["proposed"] == CLOSE),
        }

    durations = [float(r["duration_s"]) for r in rows if r.get("duration_s") is not None]
    walls = [float(r["wall_s"]) for r in rows if r.get("wall_s") is not None]
    tin = [int(r["input_tokens"]) for r in rows if r.get("input_tokens") is not None]
    tout = [int(r["output_tokens"]) for r in rows if r.get("output_tokens") is not None]
    calls = [int(r["n_tool_calls"]) for r in rows if r.get("n_tool_calls") is not None]
    price = price_for(model_id)
    cost = (sum(tin) * price[0] + sum(tout) * price[1]) / 1e6 if price and (tin or tout) else None

    prior_recorded = sorted(r["alert_id"] for r in rows if r.get("prior_recorded"))
    bundles_seen = sorted({str(r.get("bundle")) for r in rows if r.get("bundle")})
    view_mismatch = sorted(r["alert_id"] for r in rows if r.get("model_view_agrees") is False)
    return {
        "n": n,
        "prior_recorded": prior_recorded,
        "model_view_mismatch": view_mismatch,
        "bundles_seen": bundles_seen,
        "n_true_abuse": n_true,
        "n_false_positive": n_fp,
        "proposed_counts": dict(proposed),
        "status_counts": dict(status),
        "gate": {"holds": gate_holds, "missed": missed, "unproposed_true_abuse": unproposed_true},
        "true_abuse_recall": _rate(n_true - len(missed), n_true),
        "safe_close_rate": safe_close,
        "raw_safe_close_rate": raw_safe_close,
        "safe_closed": safe_closed,
        "escalation_precision": escalation_precision,
        "strong_call_precision": strong_precision,
        "n_escalations": len(escalations),
        "n_strong_calls": len(strong),
        "agreement": agreement,
        "override_rate": None if agreement is None else 1 - agreement,
        "direction_agreement": _rate(direction_ok, n),
        "confusion": confusion,
        "per_scenario": per_scenario,
        "latency": {
            "agent_p50_s": _p(durations, 0.5),
            "agent_p95_s": _p(durations, 0.95),
            "wall_p50_s": _p(walls, 0.5),
            "wall_p95_s": _p(walls, 0.95),
            "agent_mean_s": round(mean(durations), 1) if durations else None,
        },
        "tokens": {
            "input_total": sum(tin),
            "output_total": sum(tout),
            "input_mean": round(mean(tin)) if tin else None,
            "output_mean": round(mean(tout)) if tout else None,
            "input_max": max(tin) if tin else None,
            "tool_calls_mean": round(mean(calls), 1) if calls else None,
            "tool_calls_median": median(calls) if calls else None,
            "assumed_price_per_m": price,
            "estimated_cost_usd": round(cost, 2) if cost is not None else None,
            "estimated_cost_per_alert_usd": round(cost / n, 3) if cost is not None and n else None,
        },
    }


def rows_from_labels(labels: list[dict[str, Any]], proposed_by_alert: dict[str, str | None]) -> list[dict[str, Any]]:
    """Rows for a scorer that only has a disposition per alert (threshold baseline, escalate-everything)."""
    return [
        {
            "alert_id": lab["alert_id"],
            "truth": lab["truth"],
            "injected_scenario": lab["injected_scenario"],
            "expected_disposition": lab["expected_disposition"],
            "trader_role": lab.get("trader_role"),
            "proposed": proposed_by_alert.get(lab["alert_id"]),
            "confidence": None,
            "status": "ok",
        }
        for lab in labels
    ]


def regression(
    current: dict[str, Any],
    previous: dict[str, Any] | None,
    *,
    current_faith: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Promotion rule, data doc section 4.4: gate holds, safe close rate does not drop by more than 2 points,
    evidence faithfulness stays at 100% (number level, once `evals/faithfulness.py` has run), no scenario
    regresses to 0% close."""
    out: dict[str, Any] = {"gate_holds": current["gate"]["holds"], "checks": []}
    if previous is None:
        out["verdict"] = "no previous run to compare with"
        out["previous"] = None
        return out
    out["previous"] = previous.get("run_id")
    pm, cm = previous["metrics"], current
    deltas = {}
    for k in ("raw_safe_close_rate", "agreement", "escalation_precision", "direction_agreement", "true_abuse_recall"):
        a, b = pm.get(k), cm.get(k)
        deltas[k] = None if a is None or b is None else round(b - a, 4)
    deltas["gate_missed"] = len(cm["gate"]["missed"]) - len(pm["gate"]["missed"])
    out["deltas"] = deltas
    checks = out["checks"]
    checks.append(("gate holds", cm["gate"]["holds"]))
    d = deltas["raw_safe_close_rate"]
    checks.append(("safe close rate not down by more than 2 points", d is None or d >= -0.02))
    newly_zero = [
        s
        for s, v in cm["per_scenario"].items()
        if v["truth"] == FALSE_POSITIVE
        and v["close_rate"] == 0
        and s in pm["per_scenario"]
        and (pm["per_scenario"][s].get("close_rate") or 0) > 0
    ]
    checks.append(
        (f"no false-positive scenario regressed to 0% close ({', '.join(newly_zero) or 'none'})", not newly_zero)
    )
    scen = {}
    for s, v in cm["per_scenario"].items():
        p = pm["per_scenario"].get(s)
        if p:
            scen[s] = {
                "close_rate_delta": None
                if v["close_rate"] is None or p.get("close_rate") is None
                else round(v["close_rate"] - p["close_rate"], 3),
                "agreement_delta": None
                if v["agreement"] is None or p.get("agreement") is None
                else round(v["agreement"] - p["agreement"], 3),
            }
    out["per_scenario"] = scen
    pending = "" if current_faith else ", faithfulness pending"
    out["verdict"] = f"PASS (offline promotion rule{pending})" if all(ok for _, ok in checks) else "FAIL"
    return out


def _eval_name(x: dict[str, Any]) -> str:
    name = str(x.get("evaluatorName") or x.get("evaluatorId") or "?")
    if name.startswith("Builtin."):
        name = name[len("Builtin.") :]
    elif "-" in name and x.get("evaluatorName") is None:  # custom id "name-XXXX"
        name = name.rsplit("-", 1)[0]
    if x.get("evaluationDimensionName"):
        name += "/" + str(x["evaluationDimensionName"])
    return name


def summarize_evaluations(saved: list[dict[str, Any]], rows_by_alert: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Aggregate the per-session Evaluate results: mean score and pass rate per evaluator, token usage, rubric by
    scenario and the weakest sessions. `saved` is the list of `<run>/evaluations/<alert>.json` contents."""
    per_eval: dict[str, list[tuple[str, float]]] = defaultdict(list)
    tokens: dict[str, dict[str, int]] = defaultdict(lambda: {"input": 0, "output": 0, "calls": 0})
    errors = 0
    explanations: dict[str, dict[str, str]] = defaultdict(dict)
    for s in saved:
        errors += len(s.get("errors") or [])
        for x in s.get("results") or []:
            name = _eval_name(x)
            if x.get("errorCode") or x.get("errorMessage"):
                errors += 1
                continue
            if x.get("value") is not None:
                per_eval[name].append((s["alert_id"], float(x["value"])))
                explanations[name][s["alert_id"]] = str(x.get("explanation") or "")
            tu = x.get("tokenUsage") or {}
            if tu:
                tokens[name]["input"] += int(tu.get("inputTokens") or 0)
                tokens[name]["output"] += int(tu.get("outputTokens") or 0)
                tokens[name]["calls"] += 1
    evaluators: dict[str, Any] = {}
    for name, vals in sorted(per_eval.items()):
        scores = [v for _, v in vals]
        by_s: dict[str, list[float]] = defaultdict(list)
        for a, v in vals:
            r = rows_by_alert.get(a)
            if r:
                by_s[r["injected_scenario"]].append(v)
        evaluators[name] = {
            "n": len(scores),
            "mean": round(mean(scores), 3),
            "pass_rate": round(sum(1 for v in scores if v >= 1.0) / len(scores), 3),
            "zero_rate": round(sum(1 for v in scores if v <= 0.0) / len(scores), 3),
            "per_scenario_mean": {s: round(mean(v), 2) for s, v in sorted(by_s.items())},
            "lowest": [
                {"alert_id": a, "value": v, "explanation": explanations[name].get(a, "")[:400]}
                for a, v in sorted(vals, key=lambda av: av[1])[:5]
                if v < 1.0
            ],
            "tokens": tokens.get(name),
        }
    return {"n_sessions": len(saved), "errors": errors, "evaluators": evaluators}


def render_markdown(
    run: dict[str, Any],
    *,
    baselines: dict[str, dict[str, Any]] | None = None,
    reg: dict[str, Any] | None = None,
    rows: list[dict[str, Any]] | None = None,
    evaluations: dict[str, Any] | None = None,
    faithfulness: dict[str, Any] | None = None,
) -> str:
    m = run["metrics"]
    g = m["gate"]
    lines = []
    lines.append(f"# Dataset run `{run['run_id']}`")
    lines.append("")
    lines.append(
        f"- Dataset `{run.get('dataset')}`, {m['n']} alerts ({m['n_true_abuse']} TRUE_ABUSE, "
        f"{m['n_false_positive']} FALSE_POSITIVE); backend `{run.get('backend')}`, model `{run.get('model_id')}`, "
        f"analyst `{run.get('user')}`, mode `{run.get('mode')}`, memory {'on' if run.get('memory', True) else 'OFF'}, "
        f"bundle {run.get('bundle') or 'none (code defaults)'}, concurrency {run.get('concurrency')}."
    )
    lines.append(
        f"- Started {run.get('started_at')}, finished {run.get('finished_at')} ({run.get('elapsed_min')} min)."
    )
    if run.get("notes"):
        lines.append(f"- Notes: {run['notes']}")
    lines.append("")
    lines.append("## Headline")
    lines.append("")
    lines.append("| metric | value |")
    lines.append("|---|---|")
    gate_txt = (
        "**holds** (0 TRUE_ABUSE proposed CLOSE_FP)"
        if g["holds"]
        else f"**FAILED**: {len(g['missed'])} missed: {', '.join(g['missed'])}"
    )
    lines.append(f"| gate | {gate_txt} |")
    if g["unproposed_true_abuse"]:
        lines.append(
            f"| true-abuse alerts with no proposal | {len(g['unproposed_true_abuse'])}: {', '.join(g['unproposed_true_abuse'])} |"
        )
    sc = (
        _pct(m["safe_close_rate"])
        if g["holds"]
        else f"n/a (gate failed: {len(g['missed'])} missed; raw {_pct(m['raw_safe_close_rate'])})"
    )
    lines.append(f"| safe close rate | {sc} ({m['safe_closed']} of {m['n_false_positive']} false positives closed) |")
    lines.append(
        f"| escalation precision | {_pct(m['escalation_precision'])} ({m['n_escalations']} ESCALATE/DRAFT_STOR) |"
    )
    lines.append(f"| strong-call precision | {_pct(m['strong_call_precision'])} ({m['n_strong_calls']} DRAFT_STOR) |")
    lines.append(f"| agreement with label (exact disposition) | {_pct(m['agreement'])} |")
    lines.append(f"| **override rate** (1 - agreement) | **{_pct(m['override_rate'])}** |")
    lines.append(f"| direction agreement (close vs not-close) | {_pct(m['direction_agreement'])} |")
    lines.append(f"| proposals | {m['proposed_counts']} |")
    lines.append(f"| run status | {m['status_counts']} |")
    if m.get("prior_recorded"):
        lines.append(
            f"| alerts with a disposition recorded before this run (visible to the agent through history and Memory) "
            f"| {len(m['prior_recorded'])}: {', '.join(m['prior_recorded'])} |"
        )
    if m.get("bundles_seen"):
        lines.append(f"| configuration bundle reported by the agent | {', '.join(m['bundles_seen'])} |")
    if m.get("model_view_mismatch"):
        lines.append(f"| model's proposal differs from what `cases` holds | {', '.join(m['model_view_mismatch'])} |")
    lat, tok = m["latency"], m["tokens"]
    lines.append(
        f"| latency, agent p50 / p95 | {lat['agent_p50_s']} s / {lat['agent_p95_s']} s (wall p50 {lat['wall_p50_s']} s) |"
    )
    lines.append(
        f"| tokens per alert, in / out (mean) | {tok['input_mean']} / {tok['output_mean']} (max in {tok['input_max']}) |"
    )
    lines.append(f"| tool calls per alert (mean / median) | {tok['tool_calls_mean']} / {tok['tool_calls_median']} |")
    if tok["estimated_cost_usd"] is not None:
        pi, po = tok["assumed_price_per_m"]
        lines.append(
            f"| estimated model cost | ${tok['estimated_cost_usd']} total, ${tok['estimated_cost_per_alert_usd']} per alert "
            f"(assumed ${pi}/${po} per M tokens in/out; not verified against the pricing page) |"
        )
    lines.append("")
    if baselines:
        lines.append("## Against the baselines (same alerts)")
        lines.append("")
        lines.append(
            "| scorer | gate | safe close rate | raw safe close | escalation precision | agreement | override rate |"
        )
        lines.append("|---|---|---|---|---|---|---|")
        for name, bm in [("agent (this run)", m), *baselines.items()]:
            bg = bm["gate"]
            gate_cell = "holds" if bg["holds"] else f"{len(bg['missed'])} missed"
            lines.append(
                f"| {name} | {gate_cell} | {_pct(bm['safe_close_rate'])} | {_pct(bm['raw_safe_close_rate'])} "
                f"| {_pct(bm['escalation_precision'])} | {_pct(bm['agreement'])} | {_pct(bm['override_rate'])} |"
            )
        lines.append("")
    lines.append("## Confusion: expected (rows) x proposed (columns)")
    lines.append("")
    lines.append("| expected \\ proposed | CLOSE_FP | ESCALATE | DRAFT_STOR | none |")
    lines.append("|---|---|---|---|---|")
    for e in DISPOSITIONS:
        c = m["confusion"][e]
        lines.append(f"| {e} | {c[CLOSE]} | {c[ESCALATE]} | {c[DRAFT_STOR]} | {c['NONE']} |")
    lines.append("")
    lines.append("## Per scenario")
    lines.append("")
    lines.append(
        "| scenario | truth | expected | n | CLOSE_FP | ESCALATE | DRAFT_STOR | none | agreement | mean conf | gate misses |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for s, v in m["per_scenario"].items():
        lines.append(
            f"| {s} | {v['truth']} | {v['expected']} | {v['n']} | {v[CLOSE]} | {v[ESCALATE]} | {v[DRAFT_STOR]} | {v['NONE']} "
            f"| {_pct(v['agreement'], 0)} | {v['mean_confidence'] if v['mean_confidence'] is not None else '-'} "
            f"| {', '.join(v['missed']) or '-'} |"
        )
    lines.append("")
    if reg:
        lines.append("## Regression against the previous run")
        lines.append("")
        if reg.get("previous") is None:
            lines.append(reg["verdict"])
        else:
            lines.append(f"Previous run: `{reg['previous']}`. Verdict: **{reg['verdict']}**.")
            lines.append("")
            for name, ok in reg["checks"]:
                lines.append(f"- [{'x' if ok else ' '}] {name}")
            lines.append("")
            d = reg["deltas"]
            lines.append("| delta | value |")
            lines.append("|---|---|")
            for k, v in d.items():
                if k == "gate_missed":
                    lines.append(f"| gate misses | {v:+d} |")
                elif v is not None:
                    lines.append(f"| {k} | {100 * v:+.1f} pts |")
            moved = {s: v for s, v in reg["per_scenario"].items() if v["agreement_delta"]}
            if moved:
                lines.append("")
                lines.append("| scenario | agreement delta | close-rate delta |")
                lines.append("|---|---|---|")
                for s, v in sorted(moved.items(), key=lambda kv: kv[1]["agreement_delta"]):
                    cr = v["close_rate_delta"]
                    lines.append(
                        f"| {s} | {100 * v['agreement_delta']:+.0f} pts | {'-' if cr is None else f'{100 * cr:+.0f} pts'} |"
                    )
        lines.append("")
    if faithfulness and faithfulness.get("n_with_report"):
        f = faithfulness
        lines.append("## Evidence faithfulness")
        lines.append("")
        lines.append(
            f"{f['n_with_report']} reports checked against their sessions' tool results (`evals/faithfulness.py`): "
            f"**{_pct(f['alert_rate'])} of reports** have every number grounded; {f['numbers_checked'] - f['numbers_unmatched']} of "
            f"{f['numbers_checked']} numbers matched ({_pct(f['number_rate'])})."
            + (f" {f['n_no_spans']} session(s) had no spans." if f.get("n_no_spans") else "")
        )
        lines.append("")
        if f["offenders"]:
            lines.append("| alert | scenario | proposed | source | unmatched | fact |")
            lines.append("|---|---|---|---|---|---|")
            for o in f["offenders"][:60]:
                fact = o["fact"].replace("|", "/").replace("\n", " ")
                lines.append(
                    f"| {o['alert_id']} | {o['scenario']} | {o['proposed']} | {o['source']} | {', '.join(o['unmatched'])} | {fact} |"
                )
            if len(f["offenders"]) > 60:
                lines.append(f"| ... | | | | {len(f['offenders']) - 60} more in results.json | |")
            lines.append("")
    if evaluations and evaluations.get("evaluators"):
        lines.append("## AgentCore Evaluations")
        lines.append("")
        lines.append(
            f"{evaluations['n_sessions']} sessions scored against ground truth generated from the labels "
            f"(`evals/ground_truth.py`); {evaluations['errors']} evaluator error(s). Pass = score 1.0."
        )
        lines.append("")
        lines.append("| evaluator | n | mean | pass rate | judge tokens in / out |")
        lines.append("|---|---|---|---|---|")
        for name, e in evaluations["evaluators"].items():
            t = e.get("tokens") or {}
            tok = f"{t.get('input', 0):,} / {t.get('output', 0):,}" if t else "programmatic"
            lines.append(f"| {name} | {e['n']} | {e['mean']:.2f} | {_pct(e['pass_rate'], 0)} | {tok} |")
        lines.append("")
        scen_names = sorted({s for e in evaluations["evaluators"].values() for s in e["per_scenario_mean"]})
        if scen_names:
            heads = list(evaluations["evaluators"].keys())
            lines.append("| scenario | " + " | ".join(heads) + " |")
            lines.append("|---|" + "---|" * len(heads))
            for s in scen_names:
                cells = [
                    f"{evaluations['evaluators'][h]['per_scenario_mean'].get(s, float('nan')):.2f}"
                    if s in evaluations["evaluators"][h]["per_scenario_mean"]
                    else "-"
                    for h in heads
                ]
                lines.append(f"| {s} | " + " | ".join(cells) + " |")
            lines.append("")
        for name, e in evaluations["evaluators"].items():
            if e["lowest"]:
                lines.append(f"Lowest `{name}` scores:")
                lines.append("")
                for low in e["lowest"]:
                    expl = low["explanation"].replace("\n", " ").replace("|", "/")[:300]
                    lines.append(f"- {low['alert_id']} = {low['value']:g}: {expl}")
                lines.append("")
    if rows:
        wrong = [r for r in rows if r["proposed"] != r["expected_disposition"]]
        lines.append(f"## Disagreements with the label ({len(wrong)})")
        lines.append("")
        lines.append("| alert | scenario | expected | proposed | conf | status | summary |")
        lines.append("|---|---|---|---|---|---|---|")
        for r in sorted(wrong, key=lambda r: (r["truth"] != TRUE_ABUSE, r["injected_scenario"], r["alert_id"])):
            summ = (r.get("summary") or r.get("error") or "").replace("|", "/").replace("\n", " ")[:160]
            lines.append(
                f"| {r['alert_id']} | {r['injected_scenario']} | {r['expected_disposition']} | {r['proposed'] or '-'} "
                f"| {r.get('confidence') if r.get('confidence') is not None else '-'} | {r.get('status')} | {summ} |"
            )
        lines.append("")
    return "\n".join(lines)
