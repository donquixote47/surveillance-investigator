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
        "that order was removed. Accepted explanations, each with the evidence that must be cited: registered "
        "market making on the instrument (two-sided quoting, cancels follow re-quotes, sizes typical for the desk); "
        "algorithmic re-pricing (pegged or child orders of a parent, cancels symmetric with the touch); a risk-system "
        "cancellation (risk event recorded, all sides pulled together, no beneficial opposite fill); a market-wide "
        "reaction to a public event (event recorded, other participants cancelling in the same second); genuine "
        "execution of the resting order (partial executions, iceberg replenishment, size reduction after a partial); "
        "an evident entry error (one-off, cancelled within seconds, no opposite execution, corrected order follows); "
        "a position closed at a loss after an adverse move (no favourable move before the trader's trade, round trip "
        "negative, no reversion). Prior dispositions on the trader are context and never a sufficient reason to "
        "close. Every closure records the analyst, the time, the evidence cited and the explanation relied upon, and "
        "is retained for five years (Delegated Regulation (EU) 2016/957)."
    ),
    "escalation_standard": (
        "Escalation and reporting (section 6.3). An alert is escalated to Level 2 when the core spoofing features are "
        "present and no accepted explanation is supported by the tape, or when the evidence is mixed. A Level 1 "
        "analyst may propose a STOR draft (DRAFT_STOR) when, in addition, the pattern repeats within the session or "
        "across sessions, or the trader's profile offers no legitimate reason for one-sided large resting orders. "
        "Only Level 2 records a DRAFT_STOR disposition and decides on filing with the competent authority under MAR "
        "Art. 16(2). Partial execution of the resting order does not by itself exclude spoofing: a late third-party "
        "hit after the trader's own opposite-side trade is consistent with a spoofer caught in the book."
    ),
}


def get(topic: str) -> str:
    if topic == "all":
        return "\n\n".join(f"[{k}]\n{v}" for k, v in PROCEDURES.items())
    return PROCEDURES.get(topic, f"unknown topic {topic!r}; valid: {', '.join(PROCEDURES)}, all")
