"""Evidence faithfulness: numbers and categorical claims in a fact must appear in the tool outputs (data doc 4.2)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evals"))

from faithfulness import check_categorical, check_fact, numbers_in  # noqa: E402

GROUND = (
    '{"trader_id": "T-X1104-10", "desk": "PROP-EQ", "role": "PROP", "registered_mm_instruments": [], '
    '"typical_order_size": 500}\n'
    '{"order_types": ["LIMIT", "MARKET"], "max_resting_size_vs_depth": 15.7, "opposite_side_fill_qty": 1423, '
    '"ms_before_first_cancel": 360.5}\n'
    "NEW BUY LIMIT O-00019290 qty 38461 at 9994 at 12:50:39.339"
)
GROUND_MM = GROUND.replace(
    '"role": "PROP", "registered_mm_instruments": []', '"role": "MARKET_MAKER", "registered_mm_instruments": ["SYN.A"]'
)


def test_numbers_grounded_and_not():
    n, un = check_fact("38,461 shares at 15.7x depth, 1423 filled 360 ms before the cancel", GROUND, numbers_in(GROUND))
    assert n == 4 and un == []
    n, un = check_fact("a 40,000-share order at 15.7x depth", GROUND, numbers_in(GROUND))
    assert un == ["40,000"]


def test_categorical_positive_claims_must_be_in_the_tool_outputs():
    _c, un = check_categorical("role PROP on desk PROP-EQ, LIMIT and MARKET orders only", GROUND)
    assert _c == 4 and un == []
    _c, un = check_categorical("the trader is a MARKET_MAKER on the ETF-MM desk", GROUND)
    assert sorted(un) == ["ETF-MM", "MARKET_MAKER"]
    _c, un = check_categorical("a PEGGED order was re-priced three times", GROUND)
    assert un == ["PEGGED"]


def test_categorical_negated_claims_are_not_checked():
    _c, un = check_categorical("no PEGGED or ICEBERG orders; LIMIT only", GROUND)
    assert un == [] and _c == 1  # LIMIT is the only positive assertion
    _c, un = check_categorical("order types LIMIT only, not MARKET_MAKER quoting", GROUND)
    assert un == []


def test_registration_claim_matches_the_profile():
    # fact says not registered, profile list is empty: fine
    _c, un = check_categorical("role PROP, registered_mm_instruments empty", GROUND)
    assert un == []
    _c, un = check_categorical("not a registered market maker on SYN.A", GROUND)
    assert un == []
    # fact says registered, profile list is empty: caught
    _c, un = check_categorical("registered market maker on SYN.A quoting both sides", GROUND)
    assert un == ["registered"]
    # fact says not registered, profile says registered: caught
    _c, un = check_categorical("role MARKET_MAKER but no registration on SYN.A", GROUND_MM)
    assert "not registered" in un
    # fact says registered, profile agrees: fine
    _c, un = check_categorical("registered MARKET_MAKER on SYN.A", GROUND_MM)
    assert un == []
