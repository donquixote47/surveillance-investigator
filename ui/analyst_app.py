"""Analyst UI (Streamlit). The human path of the design: log in as an analyst, work the queue, run the agent on an
alert, read its report and trace, and record the disposition yourself. The agent never records anything.

    uv run --group ui streamlit run ui/analyst_app.py

Every call the UI makes carries the analyst's own Cognito token: the human-path API checks the group, the Runtime
forwards the token to the Gateway, so the whole chain acts as this analyst.
"""

from __future__ import annotations

import json
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

DATASET_DATES = [
    "2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08", "2026-10-09",
    "2026-10-12", "2026-10-13", "2026-10-14", "2026-10-15", "2026-10-16",
    "2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23",
    "2026-10-26", "2026-10-27", "2026-10-28", "2026-10-29", "2026-10-30",
]  # fmt: skip
DISPOSITIONS_L1 = ["CLOSE_FP", "ESCALATE"]
DISPOSITIONS_L2 = ["CLOSE_FP", "ESCALATE", "DRAFT_STOR"]


@st.cache_resource
def config() -> Config:
    return Config.load()


def ss():
    return st.session_state


# ------------------------------------------------------------------------------------------------ sidebar: login


def sidebar() -> Session | None:
    cfg = config()
    with st.sidebar:
        st.title("Surveillance investigator")
        st.caption("Synthetic data. The agent proposes; you record.")
        sess: Session | None = ss().get("session")
        if sess and sess.expired:
            sess = None
            ss().pop("session", None)
        if sess is None:
            with st.form("login"):
                user = st.text_input("Analyst", value="l1.analyst")
                pw = st.text_input("Password", type="password")
                if st.form_submit_button("Log in", use_container_width=True):
                    try:
                        ss()["session"] = login(cfg, user, pw)
                        st.rerun()
                    except Exception as exc:
                        st.error(f"login failed: {type(exc).__name__}")
            return None
        st.success(f"{sess.username}  ·  level {sess.level}")
        st.caption(
            f"Runtime endpoint `{cfg.runtime_endpoint}`"
            + (" (pinned to the evaluated version)" if cfg.runtime_endpoint == "demo" else "")
        )
        if st.button("Log out", use_container_width=True):
            for k in ("session", "run", "run_session_id", "alert_id"):
                ss().pop(k, None)
            st.rerun()
        st.divider()
        ss()["date"] = st.selectbox(
            "Session day", DATASET_DATES, index=DATASET_DATES.index(ss().get("date", "2026-10-06"))
        )
        st.caption(f"Region {cfg.region}. Runtime `{cfg.runtime_arn.rsplit('/', 1)[-1]}`.")
        return sess


# ------------------------------------------------------------------------------------------------ queue


def queue_panel(api: HumanPath):
    st.subheader(f"Queue · {ss()['date']}")
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
                "conf": f"{c['confidence']:.2f}" if c.get("confidence") is not None else "",
                "recorded": c.get("recorded_disposition") or "",
                "by": c.get("recorded_by") or "",
                "override": "yes" if c.get("override") else "",
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True, height=min(60 + 35 * len(rows), 420))
    ids = [a["alert_id"] for a in alerts]
    current = ss().get("alert_id")
    idx = ids.index(current) if current in ids else 0
    choice = st.selectbox("Open alert", ids, index=idx)
    if choice != current:
        ss()["alert_id"] = choice
        ss().pop("run", None)
        ss().pop("run_session_id", None)
        st.rerun()


# ------------------------------------------------------------------------------------------------ case view


def report_view(report: dict, confidence: float | None, disposition: str | None):
    head = f"**Proposed: {disposition}**" if disposition else "**No proposal yet**"
    if confidence is not None:
        head += f"  ·  confidence {confidence:.2f}"
    st.markdown(head)
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
    with st.expander("Run the agent", expanded=not case.get("proposed_disposition")):
        col1, col2 = st.columns([3, 1])
        instruction = col1.text_input(
            "Instruction to the agent (optional)",
            placeholder='e.g. "just close this one quickly" to show the policy denying a hasty proposal',
            key=f"instr-{alert_id}",
        )
        mode = col2.selectbox(
            "Mode", ["investigate", "stor_drafting"] if sess.level == "L2" else ["investigate"], key=f"mode-{alert_id}"
        )
        if st.button("Investigate", type="primary", key=f"run-{alert_id}"):
            session_id = new_session_id(alert_id)
            with st.spinner("the agent is working (30-60 s)…"):
                result, session_id, wall = invoke_runtime(
                    cfg, sess, alert_id, mode=mode, instruction=instruction or None, session_id=session_id
                )
            ss()["run"] = result
            ss()["run_session_id"] = session_id
            ss()["run_wall"] = wall
            st.rerun()

    run = ss().get("run")
    if run and run.get("alert_id") == alert_id:
        run_view(cfg, run, ss().get("run_session_id", ""), ss().get("run_wall", 0.0))
    elif run and run.get("error"):
        st.error(run["error"])

    # ---- the case on file
    st.markdown("### On file")
    report = case.get("report") or {}
    if isinstance(report, str):
        try:
            report = json.loads(report)
        except json.JSONDecodeError:
            report = {}
    report_view(report, case.get("confidence"), case.get("proposed_disposition"))
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
    if case.get("feedback"):
        st.markdown("**Feedback on this case**")
        for f in case["feedback"]:
            st.markdown(f"- {f['at']} {f['by']}: {f['note']}")

    # ---- record
    st.markdown("### Your decision")
    allowed = DISPOSITIONS_L2 if sess.level == "L2" else DISPOSITIONS_L1
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
            use_container_width=True,
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
                use_container_width=True,
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
