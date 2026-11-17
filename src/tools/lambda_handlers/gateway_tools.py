"""One Lambda for all Gateway tools under target `surv`. The Gateway passes the tool's input properties as
the event and `bedrockAgentCoreToolName` (`surv___<tool>`) in the client context; we strip the prefix and
dispatch. Returns plain JSON; errors come back as {"error": ...} so the agent sees why.

Why one function and not one per tool: a Gateway target maps exactly one Lambda ARN to a tool schema, and the
tool-name prefix is the target name. Splitting tools across Lambdas would mean several targets and several
prefixes, which the policies in `policies/` do not want. Least privilege is applied at the data layer instead:
this function can read every table and write only `cases`, and it has no code path that sets a recorded
disposition.
"""

from __future__ import annotations

import json
import traceback
import uuid
from datetime import UTC, datetime
from typing import Any

from botocore.exceptions import ClientError

from tools import data_access as da
from tools import memory_access as mem
from tools import procedures
from tools.schema import REQUIRED_INPUTS, TARGET_NAME, TOOL_NAMES

NS_PER_S = 1_000_000_000
DISPOSITIONS = ("CLOSE_FP", "ESCALATE", "DRAFT_STOR")
# Where a proposal came from, written next to it on the case: the investigation session (which is also the Gateway
# policy session and the key to the trace), who ran it, the model and configuration, and the analyst's briefing.
# The agent's guard fills it from the Runtime request, not the model; anything else in the object is dropped.
PROVENANCE_KEYS = ("session_id", "analyst", "model_id", "bundle", "mode", "memory", "analyst_instruction")
PROVENANCE_MAX_CHARS = 2000


# ----------------------------------------------------------------------------------------------
# dispatch
# ----------------------------------------------------------------------------------------------


# The six lookups a proposal rests on. The Gateway's policies 03a, 03b and 04 allow a proposal only after each of
# them RETURNED the alert's id (`output.alert_id` of the recorded response; a policy can match on what a tool
# answered, not only on what was asked: devguide, "Authoring temporal policies"). So `alert_id` in the answer of
# one of these tools is the firm's statement that the lookup answered for that alert. An answer that is an error
# never carries it: a Lambda that RETURNS `{"error": ...}` has returned successfully as far as the Gateway knows,
# and until 2026-11-17 a failed lookup therefore satisfied the "look before you propose" rules.
EVIDENCE_TOOLS = (
    "get_alert",
    "get_order_events",
    "compute_discriminators",
    "get_trader_profile",
    "get_market_events",
    "get_trader_alert_history",
)


def handler(event: dict, context) -> dict:
    tool = _tool_name(context, event)
    if tool not in TOOL_NAMES:
        return {"error": f"unknown tool {tool!r}", "known_tools": TOOL_NAMES}
    missing = [k for k in REQUIRED_INPUTS[tool] if k not in event or event[k] in (None, "")]
    if missing:
        return {"error": f"{tool}: missing required input(s) {missing}"}
    try:
        out = TOOL_IMPL[tool](event)
    except Exception as exc:  # the agent needs the reason, not a stack dump
        print(traceback.format_exc())
        return {"error": f"{tool} failed: {type(exc).__name__}: {exc}"}
    if tool in EVIDENCE_TOOLS and isinstance(out, dict) and "error" in out:
        out.pop("alert_id", None)  # whatever the tool built before it failed, a failure names no alert
    return out


def _tool_name(context, event: dict) -> str:
    name = None
    try:
        name = context.client_context.custom["bedrockAgentCoreToolName"]
    except Exception:
        name = event.get("__tool__")  # local testing without a Gateway
    if not name:
        return ""
    delimiter = "___"
    return name[name.index(delimiter) + len(delimiter) :] if delimiter in name else name


# ----------------------------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------------------------


def _event_row(item: dict) -> dict:
    out = {
        "ts": int(item["ts"]),
        "time": da.hhmmss(item["ts"]),
        "order_id": item["order_id"],
        "event": item["event"],
        "side": item["side"],
        "qty": int(item["qty"]),
        "remaining_qty": int(item["remaining_qty"]),
        "order_type": item["order_type"],
    }
    for k in ("price_ticks", "best_bid", "best_ask"):
        if item.get(k) is not None:
            out[k] = item[k]
    if item.get("parent_order_id"):
        out["parent_order_id"] = item["parent_order_id"]
    return out


def _alert_or_error(alert_id: str) -> tuple[dict | None, dict | None]:
    alert = da.get_alert(alert_id)
    if alert is None:
        return None, {"error": f"alert {alert_id!r} not found"}
    return alert, None


def _on_instrument(items: list[dict], alert: dict) -> list[dict]:
    """Only the alert's instrument. The trader partition and the by_date index hold every instrument the firm
    trades; a book, a mid or a discriminator mixed across two of them would be wrong without any error. The
    synthetic datasets have one instrument, so this is a no-op there and a guard everywhere else."""
    return [i for i in items if i.get("instrument") == alert["instrument"]]


def _events_frame(items: list[dict]):
    """DynamoDB items -> the order_events DataFrame compute_discriminators expects."""
    import pandas as pd

    cols = [
        "instrument",
        "ts",
        "order_id",
        "trader_id",
        "event",
        "side",
        "price_ticks",
        "qty",
        "remaining_qty",
        "order_type",
        "parent_order_id",
        "best_bid",
        "best_ask",
        "date",
    ]
    rows = []
    for it in items:
        rows.append(
            {
                "instrument": it["instrument"],
                "ts": int(it["ts"]),
                "order_id": it["order_id"],
                "trader_id": it["trader_id"],
                "event": it["event"],
                "side": it["side"],
                "price_ticks": float(it["price_ticks"]) if it.get("price_ticks") is not None else float("nan"),
                "qty": int(it["qty"]),
                "remaining_qty": int(it["remaining_qty"]),
                "order_type": it["order_type"],
                "parent_order_id": it.get("parent_order_id"),
                "best_bid": float(it["best_bid"]) if it.get("best_bid") is not None else float("nan"),
                "best_ask": float(it["best_ask"]) if it.get("best_ask") is not None else float("nan"),
                "date": it["date"],
            }
        )
    df = pd.DataFrame(rows, columns=cols)
    if not df.empty:
        df["ts"] = df["ts"].astype("int64")
    return df


# ----------------------------------------------------------------------------------------------
# tools
# ----------------------------------------------------------------------------------------------


def get_alert(ev: dict) -> dict:
    alert, err = _alert_or_error(ev["alert_id"])
    if err:
        return err
    return {
        **{
            k: alert[k]
            for k in (
                "alert_id",
                "date",
                "scenario",
                "instrument",
                "trader_id",
                "trigger",
                "trigger_ts",
                "window_start",
                "window_end",
                "trigger_summary",
                "detector_version",
                "detector_params",
                "status",
            )
        },
        "window_start_time": da.hhmmss(alert["window_start"]),
        "window_end_time": da.hhmmss(alert["window_end"]),
        "window_seconds": (int(alert["window_end"]) - int(alert["window_start"])) / NS_PER_S,
    }


def get_order_events(ev: dict) -> dict:
    alert, err = _alert_or_error(ev["alert_id"])
    if err:
        return err
    pad = min(max(float(ev.get("pad_seconds") or 0), 0.0), 600.0)
    t0 = int(alert["window_start"]) - int(pad * NS_PER_S)
    t1 = int(alert["window_end"]) + int(pad * NS_PER_S)
    items = _on_instrument(da.trader_day_events(alert["trader_id"], alert["date"], t0, t1), alert)
    page_size = 400
    start = 0
    token = da.decode_token(ev.get("next_token"))
    if token and "offset" in token:
        start = int(token["offset"])
    page = items[start : start + page_size]
    out = {
        "alert_id": alert["alert_id"],
        "trader_id": alert["trader_id"],
        "pad_seconds": pad,
        "events": [_event_row(i) for i in page],
        "event_count": len(page),
        "total_in_range": len(items),
    }
    if start + page_size < len(items):
        out["next_token"] = da.encode_token({"offset": start + page_size})
    return out


def reconstruct_book(ev: dict) -> dict:
    alert, err = _alert_or_error(ev["alert_id"])
    if err:
        return err
    at_ts = int(ev.get("at_ts") or alert["trigger_ts"])
    levels = min(max(int(ev.get("levels") or 5), 1), 20)
    sample_ms = max(int(ev.get("sample_every_ms") or 1000), 50)
    lookback_min = 20
    t0 = at_ts - lookback_min * 60 * NS_PER_S
    day = _on_instrument(da.day_events(alert["date"], t0, at_ts), alert)
    # resting state per order at at_ts: last event's remaining; price from the last price-bearing event
    state: dict[str, dict] = {}
    for it in day:  # already in time order within the query (sk is ts-ordered)
        if it["order_type"] == "MARKET":
            continue
        oid = it["order_id"]
        s = state.setdefault(
            oid,
            {"side": it["side"], "price": None, "remaining": 0, "trader": it["trader_id"], "first_ts": int(it["ts"])},
        )
        if it.get("price_ticks") is not None:
            s["price"] = float(it["price_ticks"])
        s["remaining"] = int(it["remaining_qty"])
    depth: dict[tuple[str, float], dict] = {}
    for s in state.values():
        if s["remaining"] <= 0 or s["price"] is None:
            continue
        d = depth.setdefault((s["side"], s["price"]), {"total_qty": 0, "trader_qty": 0})
        d["total_qty"] += s["remaining"]
        if s["trader"] == alert["trader_id"]:
            d["trader_qty"] += s["remaining"]
    bids = sorted(
        [{"price_ticks": p, **v} for (side, p), v in depth.items() if side == "BUY"], key=lambda r: -r["price_ticks"]
    )[:levels]
    asks = sorted(
        [{"price_ticks": p, **v} for (side, p), v in depth.items() if side == "SELL"], key=lambda r: r["price_ticks"]
    )[:levels]
    best_bid = bids[0]["price_ticks"] if bids else None
    best_ask = asks[0]["price_ticks"] if asks else None
    # BBO path from pre-event BBO fields through the alert window
    w0, w1 = int(alert["window_start"]), int(alert["window_end"])
    win = [
        i
        for i in _on_instrument(da.day_events(alert["date"], w0, w1), alert)
        if i.get("best_bid") is not None and i.get("best_ask") is not None
    ]
    path = []
    next_t = w0
    for it in win:
        ts = int(it["ts"])
        if ts >= next_t:
            bb, ba = float(it["best_bid"]), float(it["best_ask"])
            path.append({"time": da.hhmmss(ts), "best_bid": bb, "best_ask": ba, "mid": (bb + ba) / 2})
            next_t = ts + sample_ms * 1_000_000
    return {
        "alert_id": alert["alert_id"],
        "at_ts": at_ts,
        "at_time": da.hhmmss(at_ts),
        "lookback_minutes": lookback_min,
        "note": (
            f"depth tabulated from the tape of the previous {lookback_min} minutes; "
            "orders resting longer than that are not shown"
        ),
        "bids": bids,
        "asks": asks,
        "mid_ticks": (best_bid + best_ask) / 2 if best_bid is not None and best_ask is not None else None,
        "spread_ticks": (best_ask - best_bid) if best_bid is not None and best_ask is not None else None,
        "bbo_path": path,
    }


def compute_discriminators(ev: dict) -> dict:
    from tools.discriminators import compute_discriminators as compute

    alert, err = _alert_or_error(ev["alert_id"])
    if err:
        return err
    stats = da.instrument_stats(alert["instrument"], alert["date"])
    if not stats or not stats.get("avg_depth_top5"):
        # every "size vs depth" number divides by this; a silent default of 1 would report a 300-share order as
        # 300 times the depth and read as a spoof
        return {
            "error": (
                f"no instrument statistics (avg_depth_top5) for {alert['instrument']} on {alert['date']}; "
                "the size-versus-depth discriminators cannot be computed"
            )
        }
    depth = float(stats["avg_depth_top5"])
    mine = _events_frame(_on_instrument(da.trader_day_events(alert["trader_id"], alert["date"]), alert))
    w0, w1 = int(alert["window_start"]), int(alert["window_end"])
    # the market-wide cancel count needs other traders' rows just before our first cancel;
    # one minute of context is enough
    others = _events_frame(_on_instrument(da.day_events(alert["date"], w0 - 60 * NS_PER_S, w1 + 15 * NS_PER_S), alert))
    d = compute(alert, mine, depth, all_events=others if not others.empty else None).to_dict()
    for f in d.get("opposite_side_fills", []):
        f["time"] = da.hhmmss(f["ts"])
    for o in d.get("large_orders", []):  # times a report can quote; the faithfulness check matches them as strings
        o["placed_time"] = da.hhmmss(o["placed_ts"])
        if o.get("opposite_trade_ts") is not None:
            o["opposite_trade_time"] = da.hhmmss(o["opposite_trade_ts"])
    d["evidence_id"] = f"DISC-{alert['alert_id']}"
    d["avg_depth_top5"] = depth
    d["otr"] = None if d["otr"] == "inf" else d["otr"]
    return d


def get_trader_profile(ev: dict) -> dict:
    tr = da.get_trader(ev["trader_id"])
    if tr is None:
        return {"error": f"trader {ev['trader_id']!r} not found"}
    risk = (
        json.loads(tr.get("risk_limit_events") or "[]")
        if isinstance(tr.get("risk_limit_events"), str)
        else (tr.get("risk_limit_events") or [])
    )
    reg = (
        json.loads(tr.get("registered_mm_instruments") or "[]")
        if isinstance(tr.get("registered_mm_instruments"), str)
        else (tr.get("registered_mm_instruments") or [])
    )
    in_window = risk
    alert = None
    if ev.get("alert_id"):
        # With `alert_id` this is the profile of THAT alert's trader, and the answer says so by returning the
        # alert's id (policy 03b needs it). An unknown alert was silently ignored until 2026-11-17, and any trader
        # was accepted, so a profile read for somebody else counted as evidence for the alert.
        alert, err = _alert_or_error(ev["alert_id"])
        if err:
            return err
        if alert["trader_id"] != ev["trader_id"]:
            return {
                "error": (
                    f"alert {alert['alert_id']} is on trader {alert['trader_id']}, not {ev['trader_id']}; "
                    "pass the alert's own trader_id"
                )
            }
        w0, w1 = int(alert["window_start"]) - 5 * NS_PER_S, int(alert["window_end"]) + 5 * NS_PER_S
        in_window = [r for r in risk if w0 <= int(r["ts"]) <= w1]
    out = {
        "trader_id": tr["trader_id"],
        "name": tr.get("name"),
        "desk": tr.get("desk"),
        "role": tr.get("role"),
        "registered_mm_instruments": reg,
        "typical_order_size": int(tr.get("typical_order_size") or 0),
        "typical_daily_otr": float(tr.get("typical_daily_otr") or 0),
        "risk_limit_events_in_window": [{**r, "time": da.hhmmss(r["ts"])} for r in in_window],
        "risk_limit_events_total": len(risk),
    }
    if alert:
        out["alert_id"] = alert["alert_id"]
    return out


def get_trader_alert_history(ev: dict) -> dict:
    from datetime import date as _date
    from datetime import timedelta

    # With `alert_id` the history is the one an analyst of THAT alert may see: priors up to the alert's own date,
    # and never the alert itself. Without it (older callers) the caller's `before_date` stands and nothing can be
    # excluded, because the tool does not know which alert is being investigated.
    current = None
    if ev.get("alert_id"):
        current, err = _alert_or_error(ev["alert_id"])
        if err:
            return err
        if current["trader_id"] != ev["trader_id"]:
            return {
                "error": (
                    f"alert {current['alert_id']} is on trader {current['trader_id']}, not {ev['trader_id']}; "
                    "pass the alert's own trader_id"
                )
            }
    lookback = int(ev.get("lookback_days") or 90)
    before = (current["date"] if current else None) or ev.get("before_date") or _date.today().isoformat()
    after = (_date.fromisoformat(before) - timedelta(days=lookback)).isoformat()
    # One row per alert. A decision recorded through the human path is in BOTH places (the history table and the
    # case), so the case row, which also carries the proposal it answered, replaces the history row instead of
    # being listed next to it.
    by_alert: dict[str, dict] = {r["alert_id"]: r for r in da.history(ev["trader_id"], before, after)}
    for c in da.recorded_cases_for_trader(ev["trader_id"]):
        if c.get("recorded_disposition") and after <= c.get("date", "") <= before:
            by_alert[c["alert_id"]] = {
                "alert_id": c["alert_id"],
                "date": c.get("date"),
                "scenario": c.get("scenario"),
                "proposed_disposition": c.get("proposed_disposition"),
                "recorded_disposition": c.get("recorded_disposition"),
                "recorded_by": c.get("recorded_by"),
                "analyst_note": c.get("analyst_note"),
                "override": bool(c.get("override")),
            }
    excluded = 0
    if current and by_alert.pop(current["alert_id"], None) is not None:
        excluded = 1  # the alert under investigation is not its own prior
    rows = sorted(by_alert.values(), key=lambda r: (r.get("date") or "", r.get("alert_id") or ""), reverse=True)
    out = [
        {
            k: r.get(k)
            for k in (
                "alert_id",
                "date",
                "scenario",
                "proposed_disposition",
                "recorded_disposition",
                "recorded_by",
                "analyst_note",
                "override",
            )
        }
        for r in rows
    ]
    result = {
        "trader_id": ev["trader_id"],
        "lookback_days": lookback,
        "before_date": before,
        "alerts": out,
        "count": len(out),
        "excluded_current_alert": excluded,
    }
    if current:
        result["alert_id"] = current["alert_id"]  # the history was read for this alert (policy 04 needs it)
    return result


def get_market_events(ev: dict) -> dict:
    # With `alert_id` the instrument and the window are the alert's own (nothing to copy, and the lookup is tied to
    # the alert); without it the caller passes instrument, window_start and window_end as before.
    pad = float(ev.get("pad_seconds") or 60)
    if ev.get("alert_id"):
        alert, err = _alert_or_error(ev["alert_id"])
        if err:
            return err
        instrument, w0, w1 = alert["instrument"], int(alert["window_start"]), int(alert["window_end"])
    else:
        missing = [k for k in ("instrument", "window_start", "window_end") if ev.get(k) in (None, "")]
        if missing:
            return {
                "error": (
                    f"get_market_events: pass alert_id, or instrument, window_start and window_end ({missing} missing)"
                )
            }
        instrument, w0, w1 = ev["instrument"], int(ev["window_start"]), int(ev["window_end"])
    date = da.date_of(w0)
    rows = da.market_events(date, w0 - int(pad * NS_PER_S), w1 + int(pad * NS_PER_S))
    rows = [r for r in rows if r.get("instrument") in ("*", instrument)]
    out = {
        "events": [
            {
                "ts": int(r["ts"]),
                "time": da.hhmmss(r["ts"]),
                "instrument": r["instrument"],
                "type": r["type"],
                "description": r["description"],
                "seconds_from_window_start": (int(r["ts"]) - w0) / NS_PER_S,
            }
            for r in rows
        ],
        "instrument": instrument,
        "window_start": w0,
        "window_end": w1,
    }
    if ev.get("alert_id"):
        out["alert_id"] = ev["alert_id"]
    return out


def get_instrument_stats(ev: dict) -> dict:
    s = da.instrument_stats(ev["instrument"], ev["date"])
    if s is None:
        return {"error": f"no stats for {ev['instrument']} on {ev['date']}"}
    return {
        k: s.get(k)
        for k in (
            "instrument",
            "date",
            "adv",
            "n_trades",
            "avg_spread_ticks",
            "avg_depth_top5",
            "tick_size",
            "open_ticks",
            "close_ticks",
        )
    }


def get_procedures(ev: dict) -> dict:
    return {"topic": ev["topic"], "text": procedures.get(ev["topic"])}


def recall_memory(ev: dict) -> dict:
    alert, err = _alert_or_error(ev["alert_id"])
    if err:
        return err
    q = (
        ev.get("query") or ""
    ).strip() or "prior dispositions, overrides and analyst notes on this trader and instrument"
    k = int(ev.get("top_k") or 5)
    # the decision recorded on this same alert is the answer, not a prior (memory_access.visible_to)
    trader_notes, dropped_t = mem.visible_to(mem.recall(mem.trader_ns(ev["trader_id"]), q, k), alert)
    tr = da.get_trader(ev["trader_id"]) or {}
    desk = tr.get("desk")
    desk_notes, dropped_d = mem.visible_to(mem.recall(mem.desk_ns(desk), q, k), alert) if desk else ([], 0)
    instrument_notes, dropped_i = mem.visible_to(mem.recall(mem.instrument_ns(ev["instrument"]), q, min(k, 3)), alert)
    procs = mem.recall(mem.PROCEDURES_NS, q, 2)
    return {
        "alert_id": alert["alert_id"],
        "trader_id": ev["trader_id"],
        "desk": desk,
        "trader_notes": trader_notes,
        "desk_notes": desk_notes,
        "instrument_notes": [
            {k2: v for k2, v in r.items() if k2 in ("text", "score", "source")} for r in instrument_notes
        ],
        "procedures": [{k2: v for k2, v in r.items() if k2 in ("text", "score", "source")} for r in procs],
        "count": len(trader_notes) + len(desk_notes) + len(instrument_notes) + len(procs),
        "excluded_own_decision": dropped_t + dropped_d + dropped_i,
        "note": "context only: prior dispositions never replace evidence from the current window (closure standard)",
    }


def _provenance(raw: Any) -> dict[str, str]:
    """The known keys of the `provenance` input as short strings; everything else is dropped."""
    if not isinstance(raw, dict):
        return {}
    out = {}
    for k in PROVENANCE_KEYS:
        v = raw.get(k)
        if v is None or v == "":
            continue
        out[k] = str(v)[:PROVENANCE_MAX_CHARS]
    return out


def _decided(alert_id: str, case: dict) -> dict:
    return {
        "error": (
            f"alert {alert_id} is already decided ({case.get('recorded_disposition')} recorded by "
            f"{case.get('recorded_by')} at {case.get('recorded_at')}); a proposal on a decided case is refused and "
            "nothing was written. Reopening a decided alert is a Level-2 step, not an agent action. Stop and say so."
        ),
        "alert_id": alert_id,
        "recorded_disposition": case.get("recorded_disposition"),
        "recorded_by": case.get("recorded_by"),
        "recorded_at": case.get("recorded_at"),
    }


def propose_disposition(ev: dict) -> dict:
    alert, err = _alert_or_error(ev["alert_id"])
    if err:
        return err
    disp = str(ev["disposition"]).upper()
    if disp not in DISPOSITIONS:
        return {"error": f"disposition must be one of {DISPOSITIONS}"}
    report = ev.get("report") or {}
    for k in ("summary", "evidence", "legitimate_explanations_considered"):
        if k not in report or not report[k]:
            return {"error": f"report.{k} is required"}
    try:
        conf = float(ev["confidence"])
    except TypeError, ValueError:
        return {"error": "confidence must be a number between 0 and 1"}
    if not 0.0 <= conf <= 1.0:
        return {"error": "confidence must be between 0 and 1"}
    # A decided case takes no further proposal: the report on file is the one the analyst decided on, and it stays.
    # The read catches every decided case (including ones recorded before the lock existed); the condition on the
    # write closes the gap between this read and the write.
    case = da.get_case(alert["alert_id"]) or {}
    if case.get("recorded_disposition") or case.get("decision_lock"):
        return _decided(alert["alert_id"], case)
    now = datetime.now(UTC).isoformat(timespec="seconds")
    case_id = f"C-{alert['alert_id']}"
    prov = _provenance(ev.get("provenance"))
    names = {"#d": "date", "#st": "status"}
    values: dict[str, Any] = {
        ":c": case_id,
        ":t": alert["trader_id"],
        ":dt": alert["date"],
        ":s": alert["scenario"],
        ":p": disp,
        ":conf": da.to_ddb(conf),
        ":r": json.dumps(report),
        ":at": now,
        ":status": "PROPOSED",
        ":zero": 0,
        ":one": 1,
    }
    # SET only proposal fields: this function has no code path that touches recorded_* (and its IAM role may not
    # name those attributes in an update at all; infra/surv_firm/stack.py)
    update = (
        "SET case_id = :c, trader_id = :t, #d = :dt, scenario = :s, proposed_disposition = :p, "
        "confidence = :conf, report = :r, proposed_at = :at, #st = if_not_exists(#st, :status), "
        "proposal_count = if_not_exists(proposal_count, :zero) + :one"
    )
    if case.get("proposed_disposition"):
        # an earlier proposal is being replaced (a second investigation before anyone decided): keep its line.
        # The earlier report itself is in that session's trace, found by the session id kept here.
        earlier_prov = case.get("proposal_provenance")
        if isinstance(earlier_prov, str):
            try:
                earlier_prov = json.loads(earlier_prov)
            except json.JSONDecodeError:
                earlier_prov = {}
        earlier = {
            "disposition": case.get("proposed_disposition"),
            "confidence": da.to_ddb(float(case["confidence"])) if case.get("confidence") is not None else None,
            "proposed_at": case.get("proposed_at"),
            "session_id": (earlier_prov or {}).get("session_id"),
            "replaced_at": now,
        }
        update += ", proposal_history = list_append(if_not_exists(proposal_history, :empty), :ph)"
        values.update({":empty": [], ":ph": [{k: v for k, v in earlier.items() if v is not None}]})
    if prov:
        update += ", proposal_provenance = :prov"
        values[":prov"] = json.dumps(prov)
    else:
        update += " REMOVE proposal_provenance"  # never leave the previous proposal's provenance on this one
    try:
        da.table("CASES_TABLE").update_item(
            Key={"alert_id": alert["alert_id"]},
            UpdateExpression=update,
            ConditionExpression="attribute_not_exists(decision_lock)",
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
        )
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "ConditionalCheckFailedException":
            raise
        return _decided(alert["alert_id"], da.get_case(alert["alert_id"]) or {})
    return {
        "alert_id": alert["alert_id"],
        "disposition": disp,
        "case_id": case_id,
        "proposed_at": now,
        "status": "PROPOSED: awaiting a human decision",
    }


def draft_stor_narrative(ev: dict) -> dict:
    alert, err = _alert_or_error(ev["alert_id"])
    if err:
        return err
    case = da.get_case(alert["alert_id"])
    if not case or not case.get("proposed_disposition"):
        return {"error": "no proposal recorded for this alert; call propose_disposition first"}
    if case["proposed_disposition"] != "DRAFT_STOR":
        return {
            "error": (
                f"a STOR draft needs a DRAFT_STOR proposal; this alert's proposal is {case['proposed_disposition']}"
            )
        }
    report = json.loads(case["report"]) if isinstance(case.get("report"), str) else (case.get("report") or {})
    tr = da.get_trader(alert["trader_id"]) or {}
    facts = "; ".join(f"[{e.get('id')}] {e.get('fact')}" for e in report.get("evidence", []))
    fields = {
        "description_of_suspicious_activity": report.get("summary", ""),
        "instrument": alert["instrument"],
        "persons_involved": (
            f"{alert['trader_id']} ({tr.get('role', '?')}, desk {tr.get('desk', '?')}); "
            "client identities to be completed by Level 2"
        ),
        "reasons_for_suspicion": facts,
        "indicators": report.get("indicators_matched", []),
        "period": (
            f"{alert['date']} {da.hhmmss(alert['window_start'])} to {da.hhmmss(alert['window_end'])} "
            "(detector window; see report.window_used)"
        ),
        "reference": "Delegated Regulation (EU) 2016/957 Annex (STOR template); MAR Art. 16(2)",
    }
    draft_id = f"STOR-DRAFT-{uuid.uuid4().hex[:8]}"
    now = datetime.now(UTC).isoformat(timespec="seconds")
    # The draft is the agent's output, like the proposal, so it lives on the case next to it (2026-11-12; before this
    # it was returned and kept only in the session trace). SET only stor_draft_*: no code path here touches
    # recorded_*. Each new draft replaces the previous; the earlier ones remain in their sessions' traces.
    da.table("CASES_TABLE").update_item(
        Key={"alert_id": alert["alert_id"]},
        UpdateExpression="SET stor_draft = :d, stor_draft_id = :i, stor_draft_at = :at",
        ExpressionAttributeValues={":d": json.dumps(fields), ":i": draft_id, ":at": now},
    )
    return {
        "alert_id": alert["alert_id"],
        "stor_fields": fields,
        "status": "DRAFT: not filed; Level 2 decides under MAR Art. 16(2)",
        "draft_id": draft_id,
        "drafted_at": now,
    }


TOOL_IMPL: dict[str, Any] = {
    "get_alert": get_alert,
    "get_order_events": get_order_events,
    "reconstruct_book": reconstruct_book,
    "compute_discriminators": compute_discriminators,
    "get_trader_profile": get_trader_profile,
    "get_trader_alert_history": get_trader_alert_history,
    "get_market_events": get_market_events,
    "get_instrument_stats": get_instrument_stats,
    "get_procedures": get_procedures,
    "recall_memory": recall_memory,
    "propose_disposition": propose_disposition,
    "draft_stor_narrative": draft_stor_narrative,
}

if set(TOOL_IMPL) != set(TOOL_NAMES):  # fail at import so a schema/impl drift never reaches the Gateway
    raise RuntimeError(f"tool schema and implementations differ: {set(TOOL_IMPL) ^ set(TOOL_NAMES)}")
if TARGET_NAME != "surv":
    raise RuntimeError(
        f"the Gateway target must be named 'surv' (policies use the surv___ prefix); schema says {TARGET_NAME!r}"
    )
