"""Attribute alerts to the scenario that caused them, or to BACKGROUND, and produce the labels table.

Labels are ground truth for evaluation only. They are written to a separate location and never reach the
tools the agent can call.
"""

from __future__ import annotations

import json

import pandas as pd

from market_sim.types import NS_PER_S, Disposition, Role, Truth

LABEL_COLUMNS = [
    "alert_id",
    "truth",
    "injected_scenario",
    "expected_disposition",
    "key_discriminators",
    "expected_tools",
    "notes",
    "trader_role",
]

_BACKGROUND_DISCRIMINATORS: dict[str, list[str]] = {
    str(Role.MARKET_MAKER): [
        "registered market maker on this instrument",
        "two-sided quoting; cancels follow re-quotes on fair-value moves",
        "quote sizes typical for the desk",
    ],
    str(Role.ALGO): [
        "PEGGED child orders with parent ids",
        "cancels are re-pegs when the touch moves",
        "parent order explains the children",
    ],
    str(Role.AGENCY): [
        "client orders with parent ids",
        "time-out cancels of unfilled client remainders",
        "no own-account benefit",
    ],
    str(Role.CLIENT): ["small client flow", "passive orders expire after a random lifetime", "no pattern"],
    str(Role.PROP): ["no injected behaviour; ordinary activity"],
}

CLOSE_TOOLS = [
    "get_alert",
    "get_order_events",
    "compute_discriminators",
    "get_trader_profile",
    "get_market_events",
    "get_trader_alert_history",
]


def attribute(
    alerts: pd.DataFrame,
    injections: pd.DataFrame,
    traders: pd.DataFrame,
    window_s: float = 60.0,
    cancel_within_s: float = 5.0,
) -> pd.DataFrame:
    role_by = dict(zip(traders["trader_id"], traders["role"], strict=False))
    pad_lo = int(window_s * NS_PER_S)
    pad_hi = int(cancel_within_s * NS_PER_S)
    inj_by_key: dict[tuple[str, str, str], list] = {}
    for r in injections.itertuples():
        inj_by_key.setdefault((r.date, r.instrument, r.trader_id), []).append(r)

    rows = []
    for a in alerts.itertuples():
        hit = None
        for r in inj_by_key.get((a.date, a.instrument, a.trader_id), []):
            if a.window_start <= r.t_end + pad_hi and a.window_end >= r.t_start - pad_lo:
                hit = r
                break
        role = role_by.get(a.trader_id, str(Role.PROP))
        if hit is not None:
            rows.append(
                {
                    "alert_id": a.alert_id,
                    "truth": hit.truth,
                    "injected_scenario": hit.scenario_id,
                    "expected_disposition": hit.expected_disposition,
                    "key_discriminators": hit.key_discriminators,
                    "expected_tools": hit.expected_tools,
                    "notes": hit.notes,
                    "trader_role": role,
                }
            )
        else:
            rows.append(
                {
                    "alert_id": a.alert_id,
                    "truth": str(Truth.FALSE_POSITIVE),
                    "injected_scenario": "BACKGROUND",
                    "expected_disposition": str(Disposition.CLOSE_FP),
                    "key_discriminators": json.dumps(
                        _BACKGROUND_DISCRIMINATORS.get(role, _BACKGROUND_DISCRIMINATORS[str(Role.PROP)])
                    ),
                    "expected_tools": json.dumps(CLOSE_TOOLS),
                    "notes": f"Background {role.lower().replace('_', ' ')} activity that tripped the naive detector.",
                    "trader_role": role,
                }
            )
    return pd.DataFrame(rows, columns=LABEL_COLUMNS)


def coverage(injections: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    """Per injection: how many alerts it produced. Detector recall on TRUE_ABUSE must be 1.0."""
    counts = labels[labels["injected_scenario"] != "BACKGROUND"].groupby("injected_scenario").size()
    inj_counts = injections.groupby("scenario_id").size()
    df = pd.DataFrame({"injected": inj_counts, "alerts": counts}).fillna(0).astype(int)
    df["missed_injections"] = (df["injected"] - df["alerts"]).clip(lower=0)
    return df.sort_index()


def missed_injections(
    alerts: pd.DataFrame, injections: pd.DataFrame, window_s: float = 60.0, cancel_within_s: float = 5.0
) -> pd.DataFrame:
    """Injections with no overlapping alert for the same trader/date/instrument."""
    pad_lo = int(window_s * NS_PER_S)
    pad_hi = int(cancel_within_s * NS_PER_S)
    rows = []
    for r in injections.itertuples():
        a = alerts[
            (alerts["date"] == r.date) & (alerts["trader_id"] == r.trader_id) & (alerts["instrument"] == r.instrument)
        ]
        ok = (
            ((a["window_start"] <= r.t_end + pad_hi) & (a["window_end"] >= r.t_start - pad_lo)).any()
            if len(a)
            else False
        )
        if not ok:
            rows.append({"date": r.date, "scenario_id": r.scenario_id, "trader_id": r.trader_id, "truth": r.truth})
    return pd.DataFrame(rows, columns=["date", "scenario_id", "trader_id", "truth"])
