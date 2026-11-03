"""Threshold baseline: what a firm gets from `compute_discriminators` plus a handful of if/then rules,
with no LLM. The agent is evaluated against this on the same dataset. If the baseline wins, that is a
finding; if it fails the gate, that is also a finding (see data doc section 3).

Rules are deliberately the obvious ones an analyst would write down first. They are not tuned on the
labels.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from market_sim.types import NS_PER_S, Disposition, MarketEventType, Role


@dataclass
class BaselineDecision:
    disposition: str
    rule: str
    reason: str


def classify(
    disc: dict,
    profile: dict,
    market_events: list[dict],
    alert: dict,
    event_window_s: float = 2.0,
    min_symmetry: float = 0.6,
) -> BaselineDecision:
    """`disc`: Discriminators.to_dict(); `profile`: a traders-table row (registered_mm_instruments and
    risk_limit_events as JSON strings or lists); `market_events`: rows for the date (ts, type, instrument)."""
    reg = profile.get("registered_mm_instruments") or "[]"
    reg = json.loads(reg) if isinstance(reg, str) else list(reg)
    risk = profile.get("risk_limit_events") or "[]"
    risk = json.loads(risk) if isinstance(risk, str) else list(risk)
    role = str(profile.get("role", ""))
    instrument = str(alert["instrument"])
    w0, w1 = int(alert["window_start"]), int(alert["window_end"])
    symmetry = float(disc.get("cancel_symmetry") or 0.0)
    types = disc.get("order_types") or {}
    same = int(disc.get("same_side_fill_qty") or 0)
    opp = int(disc.get("opposite_side_fill_qty") or 0)
    gross = int(disc.get("gross_submitted_dominant") or 0)
    reps = int(disc.get("repetitions_in_session") or 0)
    move = disc.get("price_move_ticks")
    mw = int(disc.get("market_wide_cancels_1s_before_first_cancel") or 0)

    # 1. registered market maker quoting two-sided
    if role == str(Role.MARKET_MAKER) and instrument in reg and symmetry >= min_symmetry:
        return BaselineDecision(
            str(Disposition.CLOSE_FP),
            "R1-registered-mm",
            f"registered MM on {instrument}, cancel symmetry {symmetry:.2f}",
        )
    # 2. pegged algo children with parents, two-sided
    if "PEGGED" in types and disc.get("parent_order_ids") and symmetry >= min_symmetry:
        return BaselineDecision(
            str(Disposition.CLOSE_FP),
            "R2-pegged-algo",
            f"PEGGED children of {len(disc['parent_order_ids'])} parent(s), symmetry {symmetry:.2f}",
        )
    # 3. risk kill switch inside the window
    for ev in risk:
        if w0 <= int(ev.get("ts", -1)) <= w1 + int(event_window_s * NS_PER_S):
            return BaselineDecision(
                str(Disposition.CLOSE_FP),
                "R3-risk-event",
                f"risk event at {ev['ts']}: {ev.get('reason', '')}",
            )
    # 4. market event just before the cancels, or a market-wide cancel storm
    for ev in market_events:
        if str(ev.get("type")) in (str(MarketEventType.NEWS), str(MarketEventType.MACRO_PRINT)) and ev.get(
            "instrument"
        ) in ("*", instrument):
            if w0 <= int(ev["ts"]) <= w1:
                return BaselineDecision(str(Disposition.CLOSE_FP), "R4-market-event", f"{ev['type']} inside the window")
    if mw >= 5:
        return BaselineDecision(
            str(Disposition.CLOSE_FP),
            "R4-cancel-storm",
            f"{mw} other traders' cancels in the second before ours",
        )
    # 5. the resting orders were genuinely executing
    if same > 0 and ("ICEBERG" in types or (gross and same / gross >= 0.15)):
        return BaselineDecision(
            str(Disposition.CLOSE_FP),
            "R5-genuine-execution",
            f"{same} executed on the dominant-side orders ({same / max(gross, 1):.0%} of gross)",
        )
    # 6. no opposite fill, single episode: fat finger
    if opp == 0 and reps == 0 and str(alert.get("trigger")) == "LARGE_QUICK_CANCEL":
        return BaselineDecision(
            str(Disposition.CLOSE_FP),
            "R6-fat-finger",
            "large order cancelled quickly with no opposite execution and no repetition",
        )
    # 7. price went against the resting side before the trader traded, or he closed the round trip at a loss:
    #    no manipulation benefit
    if isinstance(move, (int, float)) and move <= -0.5:
        return BaselineDecision(
            str(Disposition.CLOSE_FP),
            "R7-adverse-move",
            f"price moved {move:+.1f} ticks against the resting side",
        )
    rt = disc.get("round_trip_ticks")
    if isinstance(rt, (int, float)) and rt <= -1.0 and not (isinstance(move, (int, float)) and move > 0):
        return BaselineDecision(
            str(Disposition.CLOSE_FP),
            "R7-loss",
            f"sold {-rt:.1f} ticks below where he bought in the same window",
        )
    # otherwise escalate; repeated cycles are the strong call
    if reps >= 3:
        return BaselineDecision(
            str(Disposition.DRAFT_STOR),
            "R8-repeated",
            f"{reps} large-order/opposite-fill/cancel cycles in the session",
        )
    return BaselineDecision(str(Disposition.ESCALATE), "R9-default", "no legitimate explanation matched")
