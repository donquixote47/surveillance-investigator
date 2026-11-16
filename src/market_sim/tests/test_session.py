"""End-to-end guard: every catalogue scenario must trip the detector (recall 1.0 by construction) and
the labels must attribute each alert to the right scenario."""

import pandas as pd

from detector.labels import attribute, missed_injections
from detector.rule import detect
from market_sim.config import SimConfig
from market_sim.run import run_session
from market_sim.scenarios import CATALOGUE_LATEST, SCENARIOS, false_specs, true_specs


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


def test_catalogue_1_is_the_first_build_and_2_adds_the_registered_spoofer() -> None:
    """The mix is sampled from the catalogue, so a dataset can be rebuilt from its seed only if the catalogue it
    was built from still yields the same list in the same order. seed7 and seed8 are catalogue 1."""
    v1 = [s.id for s in true_specs(1)]
    assert v1 == ["S-SPOOF-1", "S-SPOOF-2", "S-LAYER-1", "S-SPOOF-3", "S-SPOOF-4", "S-SPOOF-5"]
    assert [s.weight for s in true_specs(1)] == [0.30, 0.15, 0.20, 0.10, 0.10, 0.15]
    assert len(false_specs(1)) == 9 and len(false_specs(CATALOGUE_LATEST)) == 9
    assert [s.id for s in true_specs(2)] == [*v1, "S-SPOOF-6"]
    assert SCENARIOS["S-SPOOF-6"].since == 2 and SCENARIOS["S-SPOOF-6"].registered_here


def test_registered_market_maker_who_spoofs_defeats_the_registration_rule() -> None:
    """S-SPOOF-6: the profile says registered market maker, the window holds his two-sided quoting, and one large
    one-sided order was placed, never executed, and cancelled after he traded the other way. The threshold rules
    close it ("registered, symmetric cancels"), which is the reading the scenario exists to test."""
    import json

    from detector.baseline import classify
    from tools.discriminators import compute_discriminators

    tab = run_session(SimConfig(), seed=4, date="2026-12-01", scenario_ids=["S-SPOOF-6"])
    alerts = detect(tab.order_events, tab.instrument_stats)
    labels = attribute(alerts, tab.injections, tab.traders)
    mine = labels[labels.injected_scenario == "S-SPOOF-6"]
    assert len(mine) == 1 and mine.iloc[0].truth == "TRUE_ABUSE"
    alert = alerts[alerts.alert_id == mine.iloc[0].alert_id].iloc[0].to_dict()
    profile = tab.traders.set_index("trader_id").to_dict("index")[alert["trader_id"]]
    assert profile["role"] == "MARKET_MAKER" and "SYN.A" in json.loads(profile["registered_mm_instruments"])

    oe = tab.order_events
    depth = float(tab.instrument_stats.avg_depth_top5.iloc[0])
    d = compute_discriminators(alert, oe[oe.trader_id == alert["trader_id"]], depth, all_events=oe).to_dict()
    assert len(d["large_order_ids"]) == 1 and d["max_resting_size_vs_depth"] >= 8
    large = oe[oe.order_id == d["large_order_ids"][0]]
    assert list(large.event) == ["NEW", "CANCEL"]  # placed, never executed, pulled
    assert d["cancel_symmetry"] >= 0.6  # the quoting in the window makes the cancels look two-sided
    verdict = classify(d, profile, tab.market_events.to_dict("records"), alert)
    assert (verdict.disposition, verdict.rule) == ("CLOSE_FP", "R1-registered-mm")

    # The window-level numbers describe his quoting: measured to a fill on one of his quotes that came before the
    # large order existed, the price "moved against" him and the order looks close to the touch.
    assert d["price_move_ticks"] <= 0 and d["reversion_ticks"] == 0.0 and d["distance_from_touch_ticks"] < 1.0
    # The large order's own entry says what happened to it: several times the depth, away from the touch, nothing
    # of his on the other side, never executed, pulled in full a fraction of a second after he traded the other
    # way, with the price having moved his way and come back.
    (e,) = d["large_orders"]
    assert e["order_id"] == d["large_order_ids"][0] and d["large_orders_omitted"] == 0
    assert e["size_vs_depth"] >= 8 and e["distance_from_touch_ticks"] >= 2 and e["other_side_resting_vs_depth"] == 0.0
    assert e["executed_qty_before_opposite_trade"] == 0 and e["executed_qty_after_opposite_trade"] == 0
    assert e["cancelled_qty"] == e["qty"] and e["final_state"] == "CANCELLED"
    assert e["opposite_trade_qty"] > 0 and 100 <= e["ms_from_opposite_trade_to_first_withdrawal"] <= 500
    assert e["price_move_ticks"] > 0 and e["reversion_ticks"] > 0
    assert (
        d["notes"][0].startswith(f"large order {e['order_id']} (") and "other order(s) of the trader" in d["notes"][0]
    )
