"""End-to-end guard: every catalogue scenario must trip the detector (recall 1.0 by construction) and
the labels must attribute each alert to the right scenario."""

import pandas as pd

from detector.labels import attribute, missed_injections
from detector.rule import detect
from market_sim.config import SimConfig
from market_sim.run import run_session
from market_sim.scenarios import SCENARIOS


def test_every_scenario_produces_an_alert_and_is_attributed() -> None:
    tab = run_session(SimConfig(), seed=7, date="2026-10-05", scenario_ids=list(SCENARIOS))
    assert len(tab.injections) == len(SCENARIOS)
    alerts = detect(tab.order_events, tab.instrument_stats)
    missed = missed_injections(alerts, tab.injections)
    assert missed.empty, missed.to_string()
    labels = attribute(alerts, tab.injections, tab.traders)
    attributed = set(labels[labels.injected_scenario != "BACKGROUND"].injected_scenario)
    assert attributed == set(SCENARIOS)
    truths = labels.set_index("injected_scenario")["truth"].to_dict()
    assert truths["S-SPOOF-1"] == "TRUE_ABUSE" and truths["F-MM-1"] == "FALSE_POSITIVE"
    # background alerts are false positives with a role-based explanation
    bg = labels[labels.injected_scenario == "BACKGROUND"]
    assert (bg.truth == "FALSE_POSITIVE").all()


def test_same_seed_same_tape() -> None:
    a = run_session(SimConfig(), seed=11, date="2026-10-06", scenario_ids=["S-SPOOF-1", "F-MM-1"]).order_events
    b = run_session(SimConfig(), seed=11, date="2026-10-06", scenario_ids=["S-SPOOF-1", "F-MM-1"]).order_events
    pd.testing.assert_frame_equal(a, b)


def test_tape_invariants() -> None:
    tab = run_session(SimConfig(), seed=3, date="2026-10-07", scenario_ids=["S-LAYER-1"])
    oe = tab.order_events
    assert oe.ts.is_monotonic_increasing
    assert (oe.qty[oe.event != "MODIFY"] > 0).all()
    assert (oe.remaining_qty >= 0).all()
    assert oe.loc[oe.event == "NEW", "order_id"].is_unique
    # every executed quantity appears on both sides of a trade
    fills = oe[oe.event.isin(["FILL", "PARTIAL_FILL"])].qty.sum()
    assert fills == 2 * tab.trades.qty.sum()
    # the ICEBERG/MARKET/PEGGED types are used by the background and scenarios
    assert {"LIMIT", "MARKET", "PEGGED"} <= set(oe.order_type.unique())
