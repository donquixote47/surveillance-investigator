"""Single source of truth for the Gateway tool definitions (target `surv`).

Used by: the CDK stack / `agentcore add gateway-target` (exported as the Lambda target's toolSchema), the
Lambda dispatcher (which tools exist, which inputs are required), and the docs. Output fields that temporal
policies reference (`alert_id`, `trader_id`, `evidence_id`, `disposition`) are declared so the Gateway's
Cedar schema knows them.

`record_disposition` and `send_feedback` are deliberately absent: they live on the human path.
"""

from __future__ import annotations

import json

TARGET_NAME = "surv"


def _s(desc: str) -> dict:
    return {"type": "string", "description": desc}


def _i(desc: str) -> dict:
    return {"type": "integer", "description": desc}


def _n(desc: str) -> dict:
    return {"type": "number", "description": desc}


def _b(desc: str) -> dict:
    return {"type": "boolean", "description": desc}


def _arr(items: dict, desc: str) -> dict:
    return {"type": "array", "description": desc, "items": items}


def _obj(props: dict, desc: str, required: list[str] | None = None) -> dict:
    d = {"type": "object", "description": desc, "properties": props}
    if required:
        d["required"] = required
    return d


ORDER_EVENT = _obj(
    {
        "ts": _i("nanoseconds since epoch"),
        "time": _s("HH:MM:SS.mmm, venue local time"),
        "order_id": _s(""),
        "event": _s("NEW, MODIFY, CANCEL, FILL or PARTIAL_FILL"),
        "side": _s("BUY or SELL"),
        "price_ticks": _n("limit price in ticks; absent for market orders"),
        "qty": _i("NEW = size, FILL/PARTIAL_FILL = executed, CANCEL = removed, MODIFY = signed delta"),
        "remaining_qty": _i("open quantity after the event"),
        "order_type": _s("LIMIT, MARKET, PEGGED or ICEBERG"),
        "parent_order_id": _s("client or algo parent order, if any"),
        "best_bid": _n("best bid immediately before the event, ticks"),
        "best_ask": _n("best ask immediately before the event, ticks"),
    },
    "one order lifecycle event",
)

TOOLS: list[dict] = [
    {
        "name": "get_alert",
        "description": (
            "Start of every investigation. Returns the alert raised by the surveillance detector: trader, "
            "instrument, the detector's scenario (SPOOFING or LAYERING), trigger, time window and the detector's "
            "own one-line summary with its parameters."
        ),
        "inputSchema": _obj({"alert_id": _s("alert identifier, e.g. A-261005-0002")}, "", ["alert_id"]),
        "outputSchema": _obj(
            {
                "alert_id": _s(""),
                "date": _s("YYYY-MM-DD"),
                "scenario": _s("SPOOFING or LAYERING"),
                "instrument": _s(""),
                "trader_id": _s(""),
                "trigger": _s("OPPOSITE_FILL_CANCEL or LARGE_QUICK_CANCEL"),
                "trigger_ts": _i("nanoseconds since epoch"),
                "window_start": _i("nanoseconds since epoch"),
                "window_end": _i("nanoseconds since epoch"),
                "window_start_time": _s("HH:MM:SS.mmm"),
                "window_end_time": _s("HH:MM:SS.mmm"),
                "window_seconds": _n("length of the detector window; the detector uses a fixed 60 s look-back"),
                "trigger_summary": _s("the detector's explanation of why it fired"),
                "detector_version": _s(""),
                "detector_params": _s("JSON of the detector parameters in force"),
                "status": _s("OPEN, IN_REVIEW, CLOSED or ESCALATED"),
            },
            "",
            ["alert_id", "trader_id", "instrument", "window_start", "window_end"],
        ),
    },
    {
        "name": "get_order_events",
        "description": (
            "The trader's raw order lifecycle events (NEW, MODIFY, CANCEL, FILL, PARTIAL_FILL) inside the alert "
            "window, optionally padded, with the best bid and ask before each event. Paginated; follow next_token."
        ),
        "inputSchema": _obj(
            {
                "alert_id": _s(""),
                "pad_seconds": _n("seconds of context before and after the window (default 0, max 600)"),
                "next_token": _s("pagination token from a previous call"),
            },
            "",
            ["alert_id"],
        ),
        "outputSchema": _obj(
            {
                "alert_id": _s(""),
                "trader_id": _s(""),
                "events": _arr(ORDER_EVENT, "events in time order"),
                "event_count": _i("events returned in this page"),
                "total_in_range": _i("events in the requested range"),
                "next_token": _s("present when more pages follow"),
            },
            "",
            ["alert_id", "events"],
        ),
    },
    {
        "name": "reconstruct_book",
        "description": (
            "What the market looked like: the best bid/ask path through the window and resting depth by price "
            "level at a given instant, separating the trader's own orders from everyone else's. Depth is "
            "tabulated from the whole day's tape up to the instant (no re-matching)."
        ),
        "inputSchema": _obj(
            {
                "alert_id": _s(""),
                "at_ts": _i("instant for the depth snapshot, ns since epoch (default: the alert's trigger_ts)"),
                "levels": _i("price levels per side in the snapshot (default 5, max 20)"),
                "sample_every_ms": _i("BBO path sampling interval (default 1000)"),
            },
            "",
            ["alert_id"],
        ),
        "outputSchema": _obj(
            {
                "alert_id": _s(""),
                "at_ts": _i(""),
                "at_time": _s(""),
                "bids": _arr(
                    _obj(
                        {"price_ticks": _n(""), "total_qty": _i(""), "trader_qty": _i("the alert's trader's share")}, ""
                    ),
                    "best first",
                ),
                "asks": _arr(
                    _obj({"price_ticks": _n(""), "total_qty": _i(""), "trader_qty": _i("")}, ""), "best first"
                ),
                "mid_ticks": _n(""),
                "spread_ticks": _n(""),
                "bbo_path": _arr(
                    _obj({"time": _s(""), "best_bid": _n(""), "best_ask": _n(""), "mid": _n("")}, ""),
                    "sampled through the window",
                ),
            },
            "",
            ["alert_id"],
        ),
    },
    {
        "name": "compute_discriminators",
        "description": (
            "The deterministic numbers an analyst computes for a spoofing alert, from the tape and the instrument's "
            "average depth: order-to-trade ratio, cancel ratio and latency, peak resting size vs depth, distance from "
            "the touch at placement, same-side vs opposite-side executions and whether the same-side executions came "
            "before or after the trader's opposite-side trade, MODIFY reductions, cancel symmetry across "
            "sides, price move before the trader's opposite-side execution, post-cancel move and reversion, round-trip "
            "P&L in ticks, repetitions over the session, and how many other traders cancelled in the second before "
            "this trader's first cancel. Vocabulary follows Delegated Regulation (EU) 2016/522 Annex II. Every value "
            "is reproducible from get_order_events."
        ),
        "inputSchema": _obj({"alert_id": _s("")}, "", ["alert_id"]),
        "outputSchema": _obj(
            {
                "alert_id": _s(""),
                "evidence_id": _s("stable id for citing this computation in the report"),
                "trader_id": _s(""),
                "window_seconds": _n(""),
                "avg_depth_top5": _n("instrument's average one-side top-5 depth for the day"),
                "dominant_side": _s("side with the larger gross submitted size in the window"),
                "gross_submitted_dominant": _i(""),
                "gross_submitted_other": _i(""),
                "otr": _n("(NEW+MODIFY+CANCEL)/executions; null when no executions"),
                "cancel_ratio": _n("cancelled or reduced qty / submitted qty"),
                "median_cancel_latency_ms": _n("placement to cancel, dominant side"),
                "max_resting_size_vs_depth": _n(""),
                "distance_from_touch_ticks": _n("size-weighted at placement; negative = improving the touch"),
                "distinct_price_levels": _i(""),
                "large_order_ids": _arr(_s(""), "dominant-side orders >= 3 x depth"),
                "same_side_fill_qty": _i("executed on the trader's own dominant-side orders"),
                "same_side_fill_qty_before_opposite_trade": _i(
                    "of those, executed before the trader's first opposite-side execution (an order that was working)"
                ),
                "same_side_fill_qty_after_opposite_trade": _i(
                    "of those, executed after the trader's first opposite-side execution (a third party hitting a "
                    "resting order before it was pulled)"
                ),
                "same_side_fill_share": _n("same_side_fill_qty / gross submitted on the dominant side"),
                "opposite_side_fill_qty": _i(""),
                "opposite_side_fills": _arr(
                    _obj(
                        {
                            "ts": _i(""),
                            "time": _s(""),
                            "price_ticks": _n(""),
                            "qty": _i(""),
                            "ms_before_first_cancel": _n(""),
                        },
                        "",
                    ),
                    "",
                ),
                "modify_reduction_qty": _i(""),
                "cancel_symmetry": _n("1 = equal cancels on both sides, 0 = one-sided"),
                "price_move_ticks": _n("+ = moved the way a spoofer on the dominant side would want, before he traded"),
                "post_cancel_move_ticks": _n("same orientation, 10 s after the last cancel"),
                "reversion_ticks": _n("favourable pre-trade move undone after the cancel; 0 when there was none"),
                "round_trip_ticks": _n("SELL VWAP minus BUY VWAP in the window; negative = a loss"),
                "repetitions_in_session": _i(""),
                "market_wide_cancels_1s_before_first_cancel": _i("distinct other traders"),
                "order_types": _obj({}, "counts by order type"),
                "parent_order_ids": _arr(_s(""), ""),
                "notes": _arr(_s(""), "deterministic remarks, e.g. executions on the dominant side"),
            },
            "",
            ["alert_id", "evidence_id", "dominant_side"],
        ),
    },
    {
        "name": "get_trader_profile",
        "description": (
            "Who the trader is: role (MARKET_MAKER, PROP, AGENCY, CLIENT, ALGO), desk, instruments on which the firm "
            "has registered market-making obligations, typical order size and typical daily order-to-trade ratio, and "
            "any risk-system events (kill switch, limit breach) recorded inside the alert window."
        ),
        "inputSchema": _obj(
            {"trader_id": _s(""), "alert_id": _s("optional; when given, risk events are filtered to the alert window")},
            "",
            ["trader_id"],
        ),
        "outputSchema": _obj(
            {
                "trader_id": _s(""),
                "name": _s(""),
                "desk": _s(""),
                "role": _s(""),
                "registered_mm_instruments": _arr(_s(""), ""),
                "typical_order_size": _i(""),
                "typical_daily_otr": _n(""),
                "risk_limit_events_in_window": _arr(
                    _obj({"ts": _i(""), "time": _s(""), "instrument": _s(""), "reason": _s("")}, ""), ""
                ),
                "risk_limit_events_total": _i("all recorded risk events for the trader"),
            },
            "",
            ["trader_id", "role"],
        ),
    },
    {
        "name": "get_trader_alert_history",
        "description": (
            "Prior alerts on this trader and how analysts dispositioned them, newest first. Prior dispositions are "
            "context, not evidence about the current window."
        ),
        "inputSchema": _obj(
            {"trader_id": _s(""), "lookback_days": _i("default 90"), "before_date": _s("YYYY-MM-DD; default today")},
            "",
            ["trader_id"],
        ),
        "outputSchema": _obj(
            {
                "trader_id": _s(""),
                "alerts": _arr(
                    _obj(
                        {
                            "alert_id": _s(""),
                            "date": _s(""),
                            "scenario": _s(""),
                            "proposed_disposition": _s(""),
                            "recorded_disposition": _s(""),
                            "recorded_by": _s(""),
                            "analyst_note": _s(""),
                            "override": _b("true when the analyst changed the proposal"),
                        },
                        "",
                    ),
                    "",
                ),
                "count": _i(""),
            },
            "",
            ["trader_id", "alerts"],
        ),
    },
    {
        "name": "get_market_events",
        "description": (
            "Public market events (news, scheduled macro prints, halts, auctions, open/close) "
            "in and around the window; '*' means market-wide."
        ),
        "inputSchema": _obj(
            {
                "instrument": _s(""),
                "window_start": _i("ns since epoch"),
                "window_end": _i("ns since epoch"),
                "pad_seconds": _n("default 60"),
            },
            "",
            ["instrument", "window_start", "window_end"],
        ),
        "outputSchema": _obj(
            {
                "events": _arr(
                    _obj(
                        {
                            "ts": _i(""),
                            "time": _s(""),
                            "instrument": _s(""),
                            "type": _s(""),
                            "description": _s(""),
                            "seconds_from_window_start": _n(""),
                        },
                        "",
                    ),
                    "",
                )
            },
            "",
            ["events"],
        ),
    },
    {
        "name": "get_instrument_stats",
        "description": (
            "Normalisers for 'large' and 'far from the touch': average daily volume, average spread, "
            "average top-5 depth per side, tick size, for the instrument and day."
        ),
        "inputSchema": _obj({"instrument": _s(""), "date": _s("YYYY-MM-DD")}, "", ["instrument", "date"]),
        "outputSchema": _obj(
            {
                "instrument": _s(""),
                "date": _s(""),
                "adv": _i(""),
                "n_trades": _i(""),
                "avg_spread_ticks": _n(""),
                "avg_depth_top5": _n(""),
                "tick_size": _n(""),
                "open_ticks": _n(""),
                "close_ticks": _n(""),
            },
            "",
            ["instrument", "date"],
        ),
    },
    {
        "name": "get_procedures",
        "description": (
            "The firm's written surveillance procedures: the definition of spoofing and layering it applies, "
            "the closure standard for a false positive, and the escalation standard. "
            "Topics: spoofing_definition, closure_standard, escalation_standard, all."
        ),
        "inputSchema": _obj(
            {"topic": _s("spoofing_definition, closure_standard, escalation_standard or all")}, "", ["topic"]
        ),
        "outputSchema": _obj({"topic": _s(""), "text": _s("")}, "", ["topic", "text"]),
    },
    {
        "name": "recall_memory",
        "description": (
            "What analysts have recorded before about this trader, the trader's desk and this instrument, "
            "and the firm's procedures, "
            "retrieved from AgentCore Memory by meaning. Returns prior dispositions (with override flags and the "
            "analyst's note), analyst feedback, instrument notes. Context for the investigation, never a reason on its "
            "own to close an alert. Call it right after get_alert, before the evidence tools."
        ),
        "inputSchema": _obj(
            {
                "alert_id": _s("the alert under investigation"),
                "trader_id": _s("the alerted trader"),
                "instrument": _s("the alert's instrument"),
                "query": _s("what you want to know, e.g. 'prior dispositions and analyst notes on this trader'"),
                "top_k": _i("records per namespace, default 5"),
            },
            "",
            ["alert_id", "trader_id", "instrument"],
        ),
        "outputSchema": _obj(
            {
                "alert_id": _s(""),
                "trader_id": _s(""),
                "desk": _s("the trader's desk, from the profile"),
                "trader_notes": _arr(
                    _obj(
                        {
                            "text": _s(""),
                            "score": _n(""),
                            "source": _s(""),
                            "metadata": _obj({}, ""),
                            "record_id": _s(""),
                        },
                        "",
                    ),
                    "prior dispositions, overrides and feedback on this trader",
                ),
                "desk_notes": _arr(
                    _obj(
                        {
                            "text": _s(""),
                            "score": _n(""),
                            "source": _s(""),
                            "metadata": _obj({}, ""),
                            "record_id": _s(""),
                        },
                        "",
                    ),
                    "the same, for every trader on this desk (corrections carry across days through the desk)",
                ),
                "instrument_notes": _arr(_obj({"text": _s(""), "score": _n(""), "source": _s("")}, ""), ""),
                "procedures": _arr(_obj({"text": _s(""), "score": _n(""), "source": _s("")}, ""), ""),
                "count": _i("total records returned"),
            },
            "",
            ["alert_id", "trader_id", "trader_notes", "count"],
        ),
    },
    {
        "name": "propose_disposition",
        "description": (
            "The agent's only write. Records a PROPOSED disposition and the investigation report for the alert. "
            "Nothing is closed, escalated or filed: a human analyst records the decision through a different path. "
            "The report must cite evidence from the tools called in this session."
        ),
        "inputSchema": _obj(
            {
                "alert_id": _s(""),
                "disposition": _s("CLOSE_FP, ESCALATE or DRAFT_STOR"),
                "confidence": _n("0-1"),
                "report": _obj(
                    {
                        "alert_id": _s("the alert this report is about"),
                        "scenario": _s("the detector scenario (SPOOFING or LAYERING)"),
                        "summary": _s("one paragraph a Level-2 reviewer can read in 30 seconds"),
                        "evidence": _arr(
                            _obj({"id": _s("E1, E2, ..."), "source": _s("tool name"), "fact": _s("")}, ""), ""
                        ),
                        "indicators_matched": _arr(_s(""), "Annex II indicator vocabulary"),
                        "indicators_not_matched": _arr(_s(""), ""),
                        "legitimate_explanations_considered": _arr(
                            _obj(
                                {
                                    "explanation": _s(""),
                                    "ruled_out_by": _arr(_s(""), "evidence ids"),
                                    "verdict": _s("ruled_out, supported or undetermined"),
                                },
                                "",
                            ),
                            "",
                        ),
                        "what_would_change_my_mind": _s(""),
                        "memory_used": _arr(_s(""), "prior dispositions or analyst feedback relied on"),
                        "window_used": _s(
                            "the detector window the analysis covered, and whether a longer frame was considered"
                        ),
                        "tool_calls": _arr(
                            _s(""), "tools called before this proposal, filled by the agent from its trace"
                        ),
                    },
                    "",
                    ["summary", "evidence", "legitimate_explanations_considered"],
                ),
            },
            "",
            ["alert_id", "disposition", "confidence", "report"],
        ),
        "outputSchema": _obj(
            {
                "alert_id": _s(""),
                "disposition": _s(""),
                "case_id": _s(""),
                "proposed_at": _s(""),
                "status": _s("PROPOSED: awaiting a human decision"),
            },
            "",
            ["alert_id", "disposition", "case_id"],
        ),
    },
    {
        "name": "draft_stor_narrative",
        "description": (
            "Drafts the narrative fields of a Suspicious Transaction and Order Report (MAR Art. 16, template in "
            "Delegated Regulation (EU) 2016/957) from the recorded proposal. Only meaningful after a DRAFT_STOR "
            "proposal. The draft is stored on the case (stor_draft, stor_draft_id, stor_draft_at) for Level 2 to "
            "edit, sign or discard; nothing is filed anywhere."
        ),
        "inputSchema": _obj({"alert_id": _s("")}, "", ["alert_id"]),
        "outputSchema": _obj(
            {
                "alert_id": _s(""),
                "stor_fields": _obj(
                    {
                        "description_of_suspicious_activity": _s(""),
                        "instrument": _s(""),
                        "persons_involved": _s(""),
                        "reasons_for_suspicion": _s(""),
                        "indicators": _arr(_s(""), ""),
                        "period": _s(""),
                    },
                    "",
                ),
                "status": _s("DRAFT: not filed"),
            },
            "",
            ["alert_id", "stor_fields"],
        ),
    },
]

TOOL_NAMES = [t["name"] for t in TOOLS]
REQUIRED_INPUTS = {t["name"]: list(t["inputSchema"].get("required", [])) for t in TOOLS}


def gateway_tool_schema() -> dict:
    """The `toolSchema.inlinePayload` the Gateway Lambda target expects."""
    return {"inlinePayload": TOOLS}


def export(path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(TOOLS, fh, indent=2)


if __name__ == "__main__":
    print(json.dumps(TOOLS, indent=2))
