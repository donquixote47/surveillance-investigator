"""The firm's written surveillance procedures, as the `get_procedures` tool returns them and as they are
ingested into Memory. Synthetic, but written the way a mid-sized firm's compliance manual reads, and aligned
with Delegated Regulation (EU) 2016/522 Annex II and Delegated Regulation (EU) 2016/957."""

PROCEDURES: dict[str, str] = {
    "spoofing_definition": (
        "Spoofing and layering (Market Abuse Procedures, section 4.3). The firm treats as spoofing the submission "
        "of one or more orders on one side of the order book, typically away from the touch and large relative to "
        "the visible depth, that the trader does not intend to execute, in order to move other participants' prices "
        "and execute on the other side, followed by the removal of the resting orders once the opposite-side trade "
        "has taken place. Layering is the same conduct with orders spread over several price levels. Reference: "
        "Delegated Regulation (EU) 2016/522 Annex II section 1 point 5(e), supplementary indicator 4(f) (a high "
        "ratio of cancelled orders or of orders to trades). Attempts are reportable (MAR Art. 15). Indicators may "
        "be assessed over time frames shorter or longer than a trading session (Delegated Regulation (EU) 2026/788, "
        "point 10); an analyst must state the window used."
    ),
    "closure_standard": (
        "Closing a spoofing or layering alert as a false positive (section 6.2). An alert may be closed at Level 1 "
        "only when the record shows, with reference to the tape, at least one legitimate explanation that accounts "
        "for the pattern AND the absence of the two core spoofing features in the window: (a) a resting order the "
        "trader did not intend to execute, and (b) a benefit to the trader from an opposite-side execution before "
        "that order was removed. Accepted explanations, each with the evidence that must be cited: registered market "
        "making on the instrument (two-sided quoting, cancels follow re-quotes, sizes typical for the desk); "
        "algorithmic re-pricing (pegged or child orders of a parent, cancels symmetric with the touch); a risk-system "
        "cancellation (risk event recorded, all sides pulled together, no beneficial opposite fill); a market-wide "
        "reaction to a public event (event recorded, other participants cancelling in the same second); genuine "
        "execution of the resting order (partial executions, iceberg replenishment, size reduction after a partial): "
        "the test is the order of events. Executions on the resting order BEFORE the trader's first opposite-side "
        "trade (same_side_fill_qty_before_opposite_trade), when they are a material part of it (as a rule of thumb at "
        "least a tenth of the quantity submitted, same_side_fill_share, or more than the opposite-side quantity), show "
        "an order that was working and therefore feature (a) absent; a smaller opposite-side trade while such an "
        "order is working, and a later cancel or reduction of its remainder, are ordinary order management and not "
        "feature (b), whatever the round trip. "
        "A hidden (ICEBERG, reserve) order cannot serve to move prices, because spoofing works by displaying size; "
        "treat its total quantity as the client's order, not as a signal. For an AGENCY trader, executions under "
        "different parent order ids are different clients' orders and are not one round trip; "
        "an evident entry error (one-off, cancelled within seconds, no opposite execution, corrected order follows); "
        "a position closed at a loss after an adverse move (no favourable move before the trader's trade, round trip "
        "negative, no reversion). How the explanation and the two features fit together: an accepted explanation that "
        "is supported by the tape is what shows feature (a) absent, because it gives the resting order a purpose "
        "other than moving the price (a quote, a child of a parent, a genuine attempt to buy that an event or a risk "
        "cut interrupted). Feature (b) is a benefit: an opposite-side execution at a price the resting order moved in "
        "the trader's favour (price_move_ticks > 0 towards the trader, with reversion after the cancel) or a positive "
        "round trip earned off a ONE-SIDED resting order. An opposite-side execution with no favourable move and no "
        "reversion is an ordinary trade, not feature (b). For a registered market maker or an algorithm quoting both "
        "sides, the spread earned between its own bid and ask executions (a positive round trip of a tick or two "
        "with cancel_symmetry near 1) is the ordinary income of the activity, not feature (b): feature (b) needs a "
        "one-sided resting order whose presence moved the price before the trader traded the other way. "
        "Where the window holds an order that is by itself three times the depth or more (large_orders in the "
        "discriminators), both features are decided on that order's own record, and the explanation relied upon must "
        "account for that order: its own executions before the trader's opposite-side trade "
        "(executed_qty_before_opposite_trade, executed_share_before_opposite_trade) are the figures for the "
        "genuine-execution test, and its own opposite-side trade, price move and reversion are the figures for "
        "feature (b). Executions on the trader's other orders in the window, such as his quotes, and two-sided "
        "quoting around it, show nothing about that order and do not make it a quote. The round trip over the "
        "window (round_trip_ticks) mixes that order's opposite-side trade with executions on the trader's other "
        "orders: it is not a figure for that order, and a loss on it does not make the order a stop-out unless the "
        "tape shows the position that was closed. Where no single order is "
        "that large, as in layering, the features are assessed on the resting side as a whole. Size alone "
        "is not a feature: a large resting order with a supported explanation and no benefit "
        "is closed. Prior dispositions on the trader are context and never a sufficient reason to close. Every "
        "closure records the analyst, the time, the evidence cited and the explanation relied upon, and is retained "
        "for five years (Delegated Regulation (EU) 2016/957)."
    ),
    "escalation_standard": (
        "Escalation and reporting (section 6.3). An alert is escalated to Level 2 when the core spoofing features are "
        "present and no accepted explanation is supported by the tape, or when the evidence is mixed. A Level 1 "
        "analyst may propose a STOR draft (DRAFT_STOR) when, in addition, the pattern repeats within the session or "
        "across sessions, or the trader's profile offers no legitimate reason for one-sided large resting orders. "
        "Only Level 2 records a DRAFT_STOR disposition and decides on filing with the competent authority under MAR "
        "Art. 16(2). Partial execution of the resting order does not by itself exclude spoofing. When the pattern is "
        "ONE-SIDED (a resting order several times the depth, cancels on that side only, cancel_symmetry near 0) and "
        "the executions on it arrive only AFTER the trader's own opposite-side trade "
        "(same_side_fill_qty_before_opposite_trade = 0, same_side_fill_qty_after_opposite_trade > 0), with the "
        "remainder then cancelled, that is a spoofer caught in the book and is escalated. This test has no meaning "
        "for two-sided quoting (bids and asks resting together, cancel_symmetry near 1, sizes at or near the depth): "
        "there the first execution on either side is always 'opposite' to the other, and the sequence of fills says "
        "nothing about intent. Where the discriminators list the order (large_orders), this test is read on that "
        "order's own record (executed_qty_before_opposite_trade = 0, executed_qty_after_opposite_trade > 0, the "
        "remainder cancelled), whatever the trader's other orders in the window did: two-sided quoting around a "
        "single order several times the depth does not take the test away."
    ),
}


def get(topic: str) -> str:
    if topic == "all":
        return "\n\n".join(f"[{k}]\n{v}" for k, v in PROCEDURES.items())
    return PROCEDURES.get(topic, f"unknown topic {topic!r}; valid: {', '.join(PROCEDURES)}, all")
