"""Analyst UI (Streamlit). The human path of the design: log in as an analyst, work the queue, run the agent on an
alert, read its report and trace, and record the disposition yourself. The agent never records anything.

    uv run --group ui streamlit run ui/analyst_app.py

Every call the UI makes carries the analyst's own Cognito token: the human-path API checks the group, the Runtime
forwards the token to the Gateway, so the whole chain acts as this analyst.
"""

from __future__ import annotations

import json
import secrets
import sys
from datetime import date
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from surv_client import (
    Config,
    HumanPath,
    Session,
    invoke_runtime,
    login,
    logs_console_url,
    new_session_id,
    session_spans,
    trace_console_url,
)

st.set_page_config(page_title="Surveillance investigator", page_icon="🔎", layout="wide")

# Session days in the firm's tables, newest first (the way a queue reads): seed8 (November, the generalisation set,
# loaded 2026-11-11) then seed7 (October, the evaluated set). The demo script's alerts are on the October days.
DATASET_DATES = [
    "2026-11-27", "2026-11-26", "2026-11-25", "2026-11-24", "2026-11-23",
    "2026-11-20", "2026-11-19", "2026-11-18", "2026-11-17", "2026-11-16",
    "2026-11-13", "2026-11-12", "2026-11-11", "2026-11-10", "2026-11-09",
    "2026-11-06", "2026-11-05", "2026-11-04", "2026-11-03", "2026-11-02",
    "2026-10-30", "2026-10-29", "2026-10-28", "2026-10-27", "2026-10-26",
    "2026-10-23", "2026-10-22", "2026-10-21", "2026-10-20", "2026-10-19",
    "2026-10-16", "2026-10-15", "2026-10-14", "2026-10-13", "2026-10-12",
    "2026-10-09", "2026-10-08", "2026-10-07", "2026-10-06", "2026-10-05",
]  # fmt: skip
DEFAULT_DATE = DATASET_DATES[0]


def show_date(iso: str) -> str:
    """Dates are stored and queried as ISO (YYYY-MM-DD, the tables' sort key); the UI shows DD-MM-YYYY."""
    y, m, d = iso.split("-")
    return f"{d}-{m}-{y}"


DISPOSITIONS_L1 = ["CLOSE_FP", "ESCALATE"]
DISPOSITIONS_L2 = ["CLOSE_FP", "ESCALATE", "DRAFT_STOR"]


@st.cache_resource
def config() -> Config:
    return Config.load()


@st.cache_resource
def session_store() -> dict[str, Session]:
    """Logged-in sessions, server side, for the life of the Streamlit process. `st.session_state` dies with the
    browser connection, so a page refresh used to mean a new login. The browser keeps only an opaque random id in
    the URL (`?s=`); the Cognito tokens never leave this process. The UI listens on loopback only."""
    return {}


def ss():
    return st.session_state


def restore_from_url() -> None:
    """On a fresh connection (page refresh, new tab on the same URL) pick up the session, day and alert the URL
    names. Expired or unknown ids are dropped from the URL."""
    qp = st.query_params
    sid = qp.get("s")
    if sid and "session" not in ss():
        sess = session_store().get(sid)
        if sess and not sess.expired:
            ss()["session"] = sess
            ss()["sid"] = sid
        else:
            session_store().pop(sid, None)
            qp.pop("s", None)
    if "date" not in ss() and qp.get("d") in DATASET_DATES:
        ss()["date"] = qp["d"]
    if "alert_id" not in ss() and qp.get("a"):
        ss()["alert_id"] = qp["a"]
    if "run_session_id" not in ss() and qp.get("r"):
        ss()["run_session_id"] = qp["r"]  # the investigation session that may be asked to draft the STOR


def remember_in_url(**kv: str | None) -> None:
    for k, v in kv.items():
        if v is None:
            st.query_params.pop(k, None)
        elif st.query_params.get(k) != v:
            st.query_params[k] = v


# ------------------------------------------------------------------------------------------------ sidebar: login


def sidebar() -> Session | None:
    cfg = config()
    restore_from_url()
    with st.sidebar:
        st.title("Surveillance investigator")
        st.caption("Synthetic data. The agent proposes; you record.")
        sess: Session | None = ss().get("session")
        if sess and sess.expired:
            sess = None
            session_store().pop(ss().pop("sid", ""), None)
            ss().pop("session", None)
            remember_in_url(s=None)
        if sess is None:
            with st.form("login"):
                user = st.text_input("Analyst", value="l1.analyst")
                pw = st.text_input("Password", type="password")
                if st.form_submit_button("Log in", width="stretch"):
                    try:
                        sess = login(cfg, user, pw)
                        sid = secrets.token_urlsafe(16)
                        session_store()[sid] = sess
                        ss()["session"], ss()["sid"] = sess, sid
                        remember_in_url(s=sid)
                        st.rerun()
                    except Exception as exc:
                        st.error(f"login failed: {type(exc).__name__}")
            return None
        st.success(f"{sess.username}  ·  level {sess.level}")
        st.caption(
            f"Runtime endpoint `{cfg.runtime_endpoint}`"
            + (" (pinned to the evaluated version)" if cfg.runtime_endpoint == "demo" else "")
        )
        if st.button("Log out", width="stretch"):
            session_store().pop(ss().get("sid", ""), None)
            for k in ("session", "sid", "run", "run_session_id", "alert_id", "draft"):
                ss().pop(k, None)
            remember_in_url(s=None, a=None, r=None)
            st.rerun()
        st.divider()
        saved = ss().get("date", DEFAULT_DATE)
        new_date = st.selectbox(
            "Session day",
            DATASET_DATES,
            index=DATASET_DATES.index(saved if saved in DATASET_DATES else DEFAULT_DATE),
            format_func=show_date,
        )
        if new_date != saved:  # a new day: the selected alert and any run belong to the old one
            for k in ("alert_id", "run", "run_session_id", "draft"):
                ss().pop(k, None)
            remember_in_url(a=None, r=None)
        ss()["date"] = new_date
        remember_in_url(d=new_date)
        st.caption(f"Region {cfg.region}. Runtime `{cfg.runtime_arn.rsplit('/', 1)[-1]}`.")
        return sess


# ------------------------------------------------------------------------------------------------ queue


def queue_panel(api: HumanPath):
    st.subheader(f"Queue · {show_date(ss()['date'])}")
    q = api.queue(ss()["date"])
    if q.get("error"):
        st.error(q["error"])
        return
    alerts = q["alerts"]
    if not alerts:
        st.info("no alerts on this day")
        return
    rows = []
    for a in alerts:
        c = a.get("case") or {}
        rows.append(
            {
                "alert": a["alert_id"],
                "time": a["window_start_time"][:8],
                "trader": a["trader_id"],
                "trigger": a["trigger"],
                "status": a["status"],
                "proposed": c.get("proposed_disposition") or "",
                "certainty": (
                    f"{confidence_band(float(c['confidence']))[0]} ({float(c['confidence']):.2f})"
                    if c.get("confidence") is not None
                    else ""
                ),
                "recorded": c.get("recorded_disposition") or "",
                "by": c.get("recorded_by") or "",
                "override": "yes" if c.get("override") else "",
            }
        )
    ids = [a["alert_id"] for a in alerts]
    current = ss().get("alert_id")
    if current not in ids:  # first visit to this day: open the first alert in the queue
        current = ids[0]
        ss()["alert_id"] = current
    remember_in_url(a=current)
    c_cap, c_help = st.columns([6, 1])
    c_cap.caption(f"{len(ids)} alerts. Click a row to open it; the open one is **{current}**.")
    with c_help.popover("columns"):
        st.markdown(
            "**proposed**: the agent's proposal, if it has run. **certainty**: the agent's own estimate that a "
            "reviewer would record the same, as high / medium / low with its 0-1 figure (details under the proposal). "
            "**recorded / by**: "
            "the analyst's decision. **override**: the analyst recorded something other than the agent proposed."
        )
    event = st.dataframe(
        rows,
        width="stretch",
        hide_index=True,
        height=min(60 + 35 * len(rows), 420),
        on_select="rerun",
        selection_mode="single-row",
        key=f"queue-{ss()['date']}",
    )
    picked = event.selection.rows if event is not None and hasattr(event, "selection") else []
    if picked and ids[picked[0]] != current:
        # a row click opens that alert; the table's selection is then cleared so the dropdown below stays in step
        ss()["alert_id"] = ids[picked[0]]
        for k in ("run", "run_session_id", "draft"):
            ss().pop(k, None)
        ss().pop(f"queue-{ss()['date']}", None)
        remember_in_url(a=ids[picked[0]], r=None)
        st.rerun()
    choice = st.selectbox("Open alert", ids, index=ids.index(current), key=f"open-{ss()['date']}-{current}")
    if choice != current:
        ss()["alert_id"] = choice
        for k in ("run", "run_session_id", "draft"):
            ss().pop(k, None)
        remember_in_url(a=choice, r=None)
        st.rerun()


# ------------------------------------------------------------------------------------------------ case view


def confidence_band(c: float) -> tuple[str, str]:
    """The agent's `confidence` is its own estimate that a Level-2 reviewer would record the same disposition. On
    372 evaluated proposals it ranks cases well (escalations under 0.65 were the boundary false positives, those at
    0.70 and above the spoofs; every close was right) but it is not calibrated as a probability, and no real reviewer
    has scored it yet. So the UI shows "agent certainty" as high / medium / low with its meaning spelled out, the
    raw figure in small type, and never a percentage."""
    if c >= 0.80:
        return "high", "the agent expects a reviewer to record the same; the standard is met plainly on the tape"
    if c >= 0.65:
        return "medium", "the evidence points one way; read the report before recording"
    return "low", "the agent could not clear this under the firm's standard; a reviewer may well close it"


CERTAINTY_EXPLAINED = """**Agent certainty** is the agent's own estimate of how likely a Level-2 reviewer is to record the
same disposition after reading the tape. It is shown as a band, not a percentage, because it has not been checked
against real reviewers.

| band | figure | what it has meant on the evaluation set (372 proposals) |
|---|---|---|
| **high** | 0.80 and above | closes of market makers, algos, icebergs: every one agreed with the ground truth |
| **medium** | 0.65 to 0.79 | the spoofs and layering it escalated (89% agreed), and closes of harder false positives (all agreed) |
| **low** | below 0.65 | escalations of stop-outs, news reactions, fat fingers: cases the firm's standard has not decided; the ground truth would have closed 82% of them. Nothing the agent closed at low certainty was wrong. |

So **low certainty on an escalation is not weak evidence of abuse**. It means the agent could not clear the alert under
the standard it was given and is telling you a reviewer may. The sentence *what would change the agent's mind* says
what would close it.

Treat the figure as a ranking: look at medium and high escalations first. Whether 0.60 means sixty percent is
something only your reviewers' recorded decisions can establish; the system keeps them for that."""  # noqa: E501


def report_view(report: dict, confidence: float | None, disposition: str | None):
    head = f"**Proposed: {disposition}**" if disposition else "**No proposal yet**"
    st.markdown(head)
    if confidence is not None:
        band, meaning = confidence_band(float(confidence))
        colour = {"high": "green", "medium": "blue", "low": "orange"}[band]
        c_text, c_help = st.columns([6, 1])
        c_text.markdown(
            f"Agent certainty: :{colour}[**{band} ({float(confidence):.2f})**]. {meaning[0].upper()}{meaning[1:]}.  "
            "<span style='color:grey;font-size:0.85em'>The figure is the agent's own estimate on a 0-1 scale, "
            "not a measured probability.</span>",
            unsafe_allow_html=True,
        )
        with c_help.popover("what is this?"):
            st.markdown(CERTAINTY_EXPLAINED)
        if band == "low" and report and report.get("what_would_change_my_mind"):
            st.info(f"**What would change the agent's mind:** {report['what_would_change_my_mind']}")
    if not report:
        return
    st.markdown(report.get("summary", ""))
    c1, c2 = st.columns([3, 2])
    with c1:
        st.markdown("**Evidence**")
        for e in report.get("evidence", []):
            st.markdown(f"`{e['id']}` *{e['source']}*: {e['fact']}")
    with c2:
        st.markdown("**Legitimate explanations considered**")
        for x in report.get("legitimate_explanations_considered", []):
            mark = {"ruled_out": "✗", "supported": "✓", "undetermined": "?"}.get(x.get("verdict"), "·")
            cites = f" ({', '.join(x.get('ruled_out_by', []))})" if x.get("ruled_out_by") else ""
            st.markdown(f"{mark} {x['explanation']}{cites}")
        st.markdown("**Indicators matched**")
        st.markdown(", ".join(report.get("indicators_matched", [])) or "none")
        if report.get("indicators_not_matched"):
            st.caption("not matched: " + ", ".join(report["indicators_not_matched"]))
    st.markdown(f"**What would change the agent's mind:** {report.get('what_would_change_my_mind', '')}")
    st.caption(f"Window: {report.get('window_used', '')}")
    if report.get("memory_used"):
        st.markdown("**Memory used** (what analysts recorded before, and what the agent did with it):")
        for m in report["memory_used"]:
            st.markdown(f"- {m}")
    else:
        st.caption("Memory used: nothing from prior analyst decisions applied to this alert")
    if report.get("tool_calls"):
        st.caption("Tools (from the agent's trace): " + " → ".join(report["tool_calls"]))


def provenance_view(cfg: Config, case: dict):
    """Where the proposal on file came from (written by the agent's guard next to the proposal): who ran the
    investigation, in which session, with which model and briefing. The session id is the key to the trace, so the
    link works for anyone who opens the case later, not only in the browser session that ran it."""
    prov = case.get("proposal_provenance") or {}
    if isinstance(prov, str):
        try:
            prov = json.loads(prov)
        except json.JSONDecodeError:
            prov = {}
    if prov:
        bits = [f"investigated by {prov['analyst']}" if prov.get("analyst") else "", prov.get("model_id", "")]
        if prov.get("bundle") and prov["bundle"] != "none":
            bits.append(f"bundle {prov['bundle']}")
        if prov.get("memory") == "off":
            bits.append("memory off")
        st.caption("Proposal: " + " · ".join(b for b in bits if b))
        if prov.get("analyst_instruction"):
            st.caption(f"Analyst's briefing for this run: “{prov['analyst_instruction']}”")
        if prov.get("session_id"):
            url = logs_console_url(cfg, prov["session_id"])
            st.caption(f"session `{prov['session_id']}`" + (f" · [trace of this investigation]({url})" if url else ""))
    earlier = case.get("proposal_history") or []
    if earlier:
        st.caption(
            "Earlier proposals on this alert, replaced before any decision: "
            + "; ".join(
                f"{h.get('disposition')} at {str(h.get('proposed_at', ''))[:16].replace('T', ' ')}"
                + (f" (session `{h['session_id']}`)" if h.get("session_id") else "")
                for h in earlier
            )
        )


def case_panel(cfg: Config, sess: Session, api: HumanPath):
    alert_id = ss().get("alert_id")
    if not alert_id:
        st.info("pick an alert from the queue")
        return
    data = api.case(alert_id)
    if data.get("error"):
        st.error(data["error"])
        return
    alert, case = data["alert"], data.get("case") or {}
    st.subheader(f"{alert_id} · {alert['instrument']} · {alert['trader_id']} · {alert['scenario']}")
    st.caption(
        f"{alert['trigger']} · window {alert.get('window_start_time', '')} to {alert.get('window_end_time', '')}"
    )
    st.markdown(f"*Detector:* {alert['trigger_summary']}")

    # ---- run the agent
    decided = case.get("recorded_disposition")
    with st.expander("Run the agent", expanded=not case.get("proposed_disposition") and not decided):
        if decided:
            # the tools Lambda refuses a proposal on a decided case and the agent stops at get_alert; the button
            # would only spend a session to say so
            st.info(
                f"This alert is decided: **{decided}** recorded by {case.get('recorded_by')} at "
                f"{str(case.get('recorded_at', ''))[:16].replace('T', ' ')}. The agent does not investigate a "
                "decided alert, and the report on file is the one the decision was taken on. Reopening is a "
                "Level-2 step."
            )
        else:
            instruction = st.text_input(
                "Ask the agent to check something specific (optional)",
                placeholder="e.g. the desk says this was a client parent order; look for it",
                help="A briefing, the way you would brief a junior. The agent still runs the full procedure and the "
                "Gateway's rules apply whatever is written here. The text is stored on the case next to the "
                "proposal it steered, and in the session trace.",
                key=f"instr-{alert_id}",
            )
            already = case.get("proposed_disposition")
            if already:
                st.caption(
                    f"A proposal is on file ({already}, {str(case.get('proposed_at', ''))[:16].replace('T', ' ')}). "
                    "Running again starts a new session, repeats the full procedure and replaces it; the earlier "
                    "proposal's line stays on the case and its report in its session's trace."
                )
            if st.button("Investigate again" if already else "Investigate", type="primary", key=f"run-{alert_id}"):
                session_id = new_session_id(alert_id)
                with st.spinner("the agent is working (30-60 s)…"):
                    result, session_id, wall = invoke_runtime(
                        cfg, sess, alert_id, mode="investigate", instruction=instruction or None, session_id=session_id
                    )
                ss()["run"] = result
                ss()["run_session_id"] = session_id
                ss()["run_wall"] = wall
                ss().pop("draft", None)
                remember_in_url(r=session_id)
                st.rerun()

    run = ss().get("run")
    if run and run.get("alert_id") == alert_id:
        run_view(cfg, run, ss().get("run_session_id", ""), ss().get("run_wall", 0.0))
    elif run and run.get("error"):
        st.error(run["error"])

    # ---- Level 2: draft the STOR narrative, in the session that proposed DRAFT_STOR
    # The Gateway admits the drafting tool only to L2 (policy 07) and only after a DRAFT_STOR proposal in the same
    # policy session (policy 05); the policy session is the Runtime session, so the button comes back on it.
    this_run = run if run and run.get("alert_id") == alert_id else None
    proposed_now = ((this_run or {}).get("proposal") or {}).get("disposition")
    # the session that proposed: this connection's run, or the one the URL remembers (`?r=`) after a refresh; the
    # id carries the alert id, so a session of another alert is never offered
    run_sid = ss().get("run_session_id") or ""
    same_alert_session = run_sid if f"-{alert_id}-" in run_sid else ""
    if sess.level == "L2" and (proposed_now or case.get("proposed_disposition")) == "DRAFT_STOR":
        st.markdown("### STOR narrative")
        draft = ss().get("draft")
        if draft and draft.get("alert_id") == alert_id:
            if draft.get("stor_draft"):
                st.json(draft["stor_draft"])
            if draft.get("final_text"):
                st.markdown(draft["final_text"])
            if draft.get("error"):
                st.error(draft["error"])
        elif same_alert_session:
            st.caption(
                "The agent proposed DRAFT_STOR. As Level 2 you can ask it to draft the narrative from the report on "
                "file; the draft is yours to edit, sign or discard."
            )
            if st.button("Draft the STOR narrative", key=f"draft-{alert_id}"):
                with st.spinner("drafting (15-30 s)…"):
                    result, _sid, _wall = invoke_runtime(
                        cfg, sess, alert_id, mode="draft_stor", instruction=None, session_id=same_alert_session
                    )
                ss()["draft"] = result
                st.rerun()
        else:
            st.caption(
                "A STOR draft is requested in the investigation session that proposed DRAFT_STOR (the Gateway's "
                "rule 05 checks for that proposal in the session's history). Run the investigation again as Level 2, "
                "then draft."
            )

    # ---- the case on file
    st.markdown("### On file")
    report = case.get("report") or {}
    if isinstance(report, str):
        try:
            report = json.loads(report)
        except json.JSONDecodeError:
            report = {}
    report_view(report, case.get("confidence"), case.get("proposed_disposition"))
    provenance_view(cfg, case)
    if case.get("recorded_disposition"):
        st.success(
            f"Recorded **{case['recorded_disposition']}** by {case['recorded_by']} at {case['recorded_at']}"
            + ("  ·  **override** of the agent's proposal" if case.get("override") else "")
        )
        st.markdown(f"> {case.get('analyst_note', '')}")
        st.caption(
            "This decision is now in AgentCore Memory under the trader and the desk; "
            "the agent will recall it next time."
        )
    for h in reversed(case.get("decision_history") or []):
        st.warning(
            f"Superseded: **{h.get('recorded_disposition')}** by {h.get('recorded_by')} at {h.get('recorded_at')} "
            f"({h.get('analyst_note', '')}). Replaced by {h.get('superseded_by')} at {h.get('superseded_at')}: "
            f"{h.get('superseded_note', '')}"
        )
    if case.get("stor_draft"):
        st.markdown("**STOR narrative draft on file**")
        st.caption(
            f"{case.get('stor_draft_id', '')} · drafted {str(case.get('stor_draft_at', ''))[:16].replace('T', ' ')} · "
            "not filed; Level 2 edits, signs or discards"
        )
        draft_on_file = case["stor_draft"]
        if isinstance(draft_on_file, str):
            try:
                draft_on_file = json.loads(draft_on_file)
            except json.JSONDecodeError:
                pass
        st.json(draft_on_file, expanded=False)
    if case.get("feedback"):
        st.markdown("**Feedback on this case**")
        for f in case["feedback"]:
            st.markdown(f"- {f['at']} {f['by']}: {f['note']}")

    # ---- record
    st.markdown("### Your decision")
    allowed = DISPOSITIONS_L2 if sess.level == "L2" else DISPOSITIONS_L1
    if not decided:
        with st.form(f"record-{alert_id}"):
            proposed = case.get("proposed_disposition")
            default = allowed.index(proposed) if proposed in allowed else 0
            disp = st.radio("Disposition", allowed, index=default, horizontal=True)
            note = st.text_area(
                "Note for the record (required)", placeholder="your reasoning, with reference to the tape", height=80
            )
            if st.form_submit_button("Record disposition"):
                r = api.record(alert_id, disp, note)
                if r.get("error"):
                    st.error(r["error"])
                else:
                    st.success(f"recorded {r['recorded_disposition']}" + (" (override)" if r.get("override") else ""))
                    st.rerun()
    elif sess.level == "L2":
        # A decision is recorded once. Level 2 may replace it, explicitly and with a reason; the earlier decision
        # stays on the case (shown above as "Superseded").
        st.caption(
            "A decision is recorded and cannot be overwritten. As Level 2 you can supersede it: the earlier decision "
            "stays on the case with your reason."
        )
        with st.form(f"supersede-{alert_id}"):
            disp = st.radio("New disposition", allowed, horizontal=True)
            note = st.text_area("Why the recorded decision is replaced (required)", height=80)
            confirm = st.checkbox(f"I am superseding the recorded {decided}")
            if st.form_submit_button("Supersede the decision"):
                if not confirm:
                    st.error("tick the box to confirm that you are replacing a recorded decision")
                else:
                    r = api.record(alert_id, disp, note, supersede=True)
                    if r.get("error"):
                        st.error(r["error"])
                    else:
                        st.success(f"recorded {r['recorded_disposition']}, superseding {r.get('superseded')}")
                        st.rerun()
    else:
        st.caption("A decision is recorded and cannot be overwritten. Only Level 2 can supersede it, with a reason.")
    with st.form(f"feedback-{alert_id}"):
        fb = st.text_input(
            "Feedback for the agent (saved on the case and written to AgentCore Memory for the trader and the desk)"
        )
        if st.form_submit_button("Send feedback"):
            r = api.feedback(alert_id, fb)
            st.error(r["error"]) if r.get("error") else st.success("feedback saved")


def run_view(cfg: Config, run: dict, session_id: str, wall: float):
    st.markdown("### This run")
    if run.get("error"):
        st.error(run["error"])
    u = run.get("usage") or {}
    st.caption(
        f"session `{session_id}` · {wall:.0f} s wall · model {run.get('model_id')} · "
        f"{u.get('model_calls', '?')} model calls · "
        f"{u.get('input_tokens', '?')} in / {u.get('output_tokens', '?')} out tokens"
    )
    calls = run.get("tool_calls") or []
    if calls:
        st.dataframe(
            [
                {
                    "#": i + 1,
                    "tool": c["tool"],
                    "ms": c.get("ms", 0),
                    "status": c.get("status", ""),
                    "input": json.dumps(c.get("input", {}))[:80],
                }
                for i, c in enumerate(calls)
            ],
            width="stretch",
            hide_index=True,
            height=min(60 + 35 * len(calls), 400),
        )
    for rej in run.get("rejections") or []:
        st.warning(rej[:800])
    p = run.get("proposal")
    if p:
        report_view(p["report"], p["confidence"], p["disposition"])
        st.caption(f"Gateway: {run.get('proposal_result')}")
    elif not run.get("error"):
        st.warning("the agent finished without a proposal")
    if run.get("stor_draft"):
        with st.expander("STOR draft (not filed)"):
            st.json(run["stor_draft"])
    if run.get("final_text"):
        with st.expander("Agent's closing note", expanded=False):
            st.markdown(run["final_text"])
    with st.expander("Trace (CloudWatch spans for this session)"):
        try:
            spans = session_spans(cfg, session_id)
        except Exception as exc:
            spans = []
            st.caption(f"trace not readable from this machine ({type(exc).__name__}); open it in the console")
        if spans:
            trace_ids = sorted({s.trace_id for s in spans if s.trace_id})
            st.dataframe(
                [
                    {"span": s.name, "kind": s.kind, "ms": round(s.duration_ms), "status": s.status}
                    for s in spans
                    if s.kind or s.tool
                ],
                width="stretch",
                hide_index=True,
                height=min(60 + 35 * len(spans), 400),
            )
            for t in trace_ids:
                st.markdown(f"[trace {t}]({trace_console_url(cfg, t)})")
        else:
            st.caption("spans arrive in CloudWatch a minute or two after the run")
        if cfg.runtime_log_group:
            st.markdown(f"[Logs Insights for this session]({logs_console_url(cfg, session_id)})")


# ------------------------------------------------------------------------------------------------ main


def main():
    sess = sidebar()
    if sess is None:
        st.markdown("## Log in as an analyst to start")
        st.markdown(
            "Test users: `l1.analyst` (Level 1), `l2.reviewer` (Level 2). Passwords are held outside the repository."
        )
        return
    cfg = config()
    api = HumanPath(cfg, sess)
    left, right = st.columns([2, 3])
    with left:
        queue_panel(api)
    with right:
        case_panel(cfg, sess, api)
    st.caption(
        f"{date.today().isoformat()} · every number in a report comes from a tool result; the trace shows which one."
    )


main()
