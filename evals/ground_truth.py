"""Ground truth for AgentCore Evaluations, generated from the dataset labels (data doc section 4.1).

Per alert: `expected_response` (Builtin.Correctness, trace level), `assertions` (Builtin.GoalSuccessRate,
session level) and `expected_trajectory` (Builtin.Trajectory*Match, session level, programmatic). The same
text feeds `evals/evaluate_sessions.py` (scores sessions the harness already ran) and, as a file in the SDK's
dataset schema, `OnDemandEvaluationDatasetRunner`.

    uv run evals/ground_truth.py                      # writes evals/ground_truth/seed7.json
    uv run evals/ground_truth.py --alert A-261006-0006   # print one alert's reference inputs

Tool names carry the Gateway target prefix (`surv___get_alert`): that is how they appear in the spans and how
the trajectory evaluators compare them [verified 2026-11-05 on a pilot session].
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "data" / "synthetic" / "seed7"
TOOL_PREFIX = "surv___"

CORE_FEATURES = (
    "(a) a large resting order away from the touch that was never meant to trade and "
    "(b) an opposite-side fill followed by a cancel, with a benefit to the trader"
)

# What a Level-2 reviewer would expect the report to say about each false-positive family
# (data doc section 2.2, scenario table)
FP_EXPLANATION = {
    "BACKGROUND": "registered market maker quoting two-sided; cancels are re-quotes on fair-value moves; sizes typical",
    "F-MM-1": "registered market maker quoting two-sided; cancels are re-quotes on fair-value moves; sizes typical",
    "F-ALGO-1": "agency algo desk working a buy and a sell parent at once; PEGGED children re-pegged every few seconds, "
    "filled on both sides (parent/child structure, symmetric cancels)",
    "F-ICE-1": "agency ICEBERG order that executed in slices against institutional sweeps; the later sale is a different "
    "client's parent order",
    "F-PARTIAL-1": "large order with two large partial executions, then a MODIFY cutting it to a residual that later "
    "completed; intent consistent with the resting side",
    "F-SPOOFLIKE-HARD-1": "registered market maker selling inventory: asks inside the touch re-priced down with the market, "
    "same-side executions dominate, no reversion after the cancels",
    "F-MM-LARGE-1": "registered market maker working one large order at the front of the queue: a material part of it "
    "executed before his small passive execution on the other side, and the remainder was withdrawn seconds later; "
    "an order that was there to trade, judged on its own record and not on the registration",
    "F-STOP-1": "momentum trader stopped out: the market moved against the resting bids, he sold at a loss "
    "(negative round trip) and cancelled; nothing to revert",
    "F-NEWS-1": "market event (news) within 200 ms before the cancels and a market-wide cancel storm, not only this trader",
    "F-FAT-1": "single fat-finger order (about ten times the usual size) cancelled within two seconds and re-entered at "
    "the right size; no opposite-side fill",
    "F-RISK-1": "kill switch: a risk-limit event in the window cancelled every order at once (both sides), "
    "recorded in the trader profile",
}


def _list(v: Any) -> list[str]:
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except json.JSONDecodeError:
            return [v]
    return [str(x) for x in (v if v is not None else [])]


def reference_inputs(label: dict[str, Any]) -> dict[str, Any]:
    """Build the three ground-truth fields for one labelled alert. Nothing here is shown to the agent."""
    expected = str(label["expected_disposition"])
    truth = str(label["truth"])
    scenario = str(label["injected_scenario"])
    kd = _list(label.get("key_discriminators"))
    tools = _list(label.get("expected_tools"))
    role = label.get("trader_role")
    notes = str(label.get("notes") or "").strip()

    expected_response = (
        f"Proposed disposition: {expected}. Trader role: {role}. "
        + (f"{notes} " if notes else "")
        + "Key discriminators: "
        + "; ".join(kd)
        + "."
    )
    if truth == "FALSE_POSITIVE":
        expected_response += f" Legitimate explanation supported: {FP_EXPLANATION.get(scenario, kd[0] if kd else '')}."
    else:
        expected_response += (
            f" No legitimate explanation is supported; both core features are present: {CORE_FEATURES}."
        )

    assertions = [
        f"The agent called {TOOL_PREFIX}propose_disposition exactly once and proposed {expected}.",
        f"The agent called {TOOL_PREFIX}compute_discriminators and {TOOL_PREFIX}get_trader_profile before "
        f"{TOOL_PREFIX}propose_disposition.",
        "Every number stated in the report's evidence facts appears in a tool result of this session.",
        "The report names the alert's detector window and says whether the agent looked beyond it.",
    ]
    if truth == "FALSE_POSITIVE":
        assertions.append(
            "The report marks one legitimate explanation as supported and it matches the tape: "
            f"{FP_EXPLANATION.get(scenario, '; '.join(kd))}."
        )
        assertions.append(
            "The report does not claim an opposite-side fill followed by a cancel with a benefit to the trader."
        )
    else:
        assertions.append(
            "The report considers market making and at least one other legitimate explanation and rules them out "
            "with evidence from the trader profile or the market events."
        )
        assertions.append(
            f"The report states both core features of spoofing with numbers from the tools: {CORE_FEATURES}."
        )
        if "repeat" in " ".join(kd).lower():
            assertions.append("The report cites the number of repetitions of the pattern in the session.")

    trajectory = [TOOL_PREFIX + t for t in tools if t != "propose_disposition"] + [TOOL_PREFIX + "propose_disposition"]
    return {
        "expected_response": expected_response,
        "assertions": assertions,
        "expected_trajectory": trajectory,
    }


def dataset_file(labels: list[dict[str, Any]]) -> dict[str, Any]:
    """The SDK's predefined-scenario dataset: one scenario per alert, one turn with the Runtime payload."""
    scenarios = []
    for lab in labels:
        ref = reference_inputs(lab)
        scenarios.append(
            {
                "scenario_id": lab["alert_id"],
                "turns": [
                    {
                        "input": {"alert_id": lab["alert_id"], "mode": "investigate"},
                        "expected_response": ref["expected_response"],
                    }
                ],
                "expected_trajectory": ref["expected_trajectory"],
                "assertions": ref["assertions"],
                "metadata": {
                    "truth": lab["truth"],
                    "injected_scenario": lab["injected_scenario"],
                    "expected_disposition": lab["expected_disposition"],
                },
            }
        )
    return {"scenarios": scenarios}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--alert", default=None)
    args = ap.parse_args()
    labels = pd.read_parquet(args.dataset / "labels" / "labels.parquet").to_dict("records")
    if args.alert:
        lab = next((x for x in labels if x["alert_id"] == args.alert), None)
        if lab is None:
            raise SystemExit(f"unknown alert {args.alert}")
        print(json.dumps(reference_inputs(lab), indent=1))
        return 0
    out = args.out or ROOT / "evals" / "ground_truth" / f"{args.dataset.name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(dataset_file(labels), indent=1))
    print(f"{len(labels)} scenarios -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
