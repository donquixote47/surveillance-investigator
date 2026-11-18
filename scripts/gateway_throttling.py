#!/usr/bin/env python
"""How often a run's investigations were throttled by the Gateway, at which request, and what the wait cost.

The agent retries a 429 inside its MCP client, so a throttled investigation that recovers looks like any other in
a run's results. On 2026-11-18 that hid the size of it: run v6 reported 2 failed investigations, and 79 of its 169
invocations had met a 429. This reads the Runtime's own log, which is the only place the throttle is written (the
Gateway's vended log has no record of a request it rate-limited).

    uv run scripts/gateway_throttling.py evals/runs/20261117T2346-sonnet-v6
    uv run scripts/gateway_throttling.py --from 2026-11-18T12:10 --to 2026-11-18T13:10 --endpoint demo

Which limit answered. The log names neither the tool nor the limit; the position in the session does. A ten-tool
investigation makes 12 Gateway requests before its proposal (three to open the MCP session, nine tools within a
few seconds), the model then writes the report for 10 to 15 s, and request 13 is `propose_disposition`. So a 429
on a request that follows a pause of several seconds, twelve or more requests in, is the write limit (3 proposals
a minute per analyst); a 429 a few hundred milliseconds after the previous request is the request limit (60 a
minute per analyst). The report prints the position and the pause, and says which reading they support.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

REGION = "eu-west-2"
STAMP = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d),(\d{3}) ")
REQUEST = re.compile(r'HTTP Request: POST \S+gateway\.bedrock-agentcore\S+ "HTTP/1\.1 (\d{3})')
RETRY = re.compile(r"gateway answered (\d{3}); retry (\d+)/(\d+) in (\d+)s")
PAUSE_OF_A_MODEL_TURN = 5.0  # seconds; tool calls follow one another within a second


@dataclass
class Throttle:
    request_number: int  # 1-based position of the throttled request among the session's Gateway requests
    pause_s: float  # seconds since the previous Gateway request of the session
    retries: int  # how many times the agent asked again
    waited_s: int  # the back-off it slept through, without jitter
    gave_up: bool  # the last answer was still a 429

    @property
    def is_the_proposal(self) -> bool:
        return self.request_number >= 12 and self.pause_s >= PAUSE_OF_A_MODEL_TURN


def _when(line: str) -> datetime | None:
    m = STAMP.match(line)
    return datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S") + timedelta(milliseconds=int(m.group(2))) if m else None


def throttles(lines: list[str]) -> list[Throttle]:
    """The throttled requests of one session, from its app-log lines in time order. The retry happens below the
    HTTP client's own logging, so a request that recovers shows as warnings followed by one request line."""
    out: list[Throttle] = []
    requests = 0
    last_request: datetime | None = None
    open_one: dict | None = None
    for line in lines:
        ts = _when(line.strip())
        if ts is None:
            continue
        retry = RETRY.search(line)
        if retry:
            attempt, delay = int(retry.group(2)), int(retry.group(4))
            if open_one is None:
                pause = (ts - last_request).total_seconds() if last_request else 0.0
                open_one = {"number": requests + 1, "pause": pause, "retries": 0, "waited": 0}
            open_one["retries"] = max(open_one["retries"], attempt)
            open_one["waited"] += delay
            continue
        request = REQUEST.search(line)
        if request:
            requests += 1
            last_request = ts
            if open_one is not None:
                gave_up = request.group(1) == "429"
                out.append(
                    Throttle(open_one["number"], open_one["pause"], open_one["retries"], open_one["waited"], gave_up)
                )
                open_one = None
    if open_one is not None:  # the log ends inside a wait: the session was cut off
        out.append(Throttle(open_one["number"], open_one["pause"], open_one["retries"], open_one["waited"], True))
    return out


def report(per_session: dict[str, list[Throttle]], invocations: int | None) -> str:
    sessions = {s: t for s, t in per_session.items() if t}
    every = [t for ts in sessions.values() for t in ts]
    lines = []
    of = f" of {invocations} invocations" if invocations else ""
    lines.append(f"sessions that met a 429: {len(sessions)}{of}; throttled requests: {len(every)}")
    if not every:
        return "\n".join(lines)
    proposal = sum(t.is_the_proposal for t in every)
    lines.append(
        f"where: {proposal} of {len(every)} on a request that followed a pause of {PAUSE_OF_A_MODEL_TURN:.0f} s or more, "
        "twelve or more requests in (the proposal: the write limit); "
        f"{len(every) - proposal} elsewhere (the request limit, or a session that does not follow the usual order)"
    )
    numbers = Counter(t.request_number for t in every)
    lines.append(
        "request number of the throttled request: " + ", ".join(f"{n}: {c}" for n, c in sorted(numbers.items()))
    )
    pauses = sorted(t.pause_s for t in every)
    lines.append(
        f"pause before it: min {pauses[0]:.1f} s, median {pauses[len(pauses) // 2]:.1f} s, max {pauses[-1]:.1f} s"
    )
    retries = Counter(t.retries for t in every)
    lines.append("times the agent asked again: " + ", ".join(f"{n}: {c}" for n, c in sorted(retries.items())))
    waits = sorted(t.waited_s for t in every)
    lines.append(
        f"wait per throttled request: median {waits[len(waits) // 2]} s, longest {waits[-1]} s, in all {sum(waits)} s"
    )
    lines.append(f"requests the agent gave up on (still 429 after the last wait): {sum(t.gave_up for t in every)}")
    return "\n".join(lines)


def _window(args: argparse.Namespace) -> tuple[datetime, datetime, int | None]:
    if args.run:
        results = args.run / "results.json"
        source = json.loads((results if results.exists() else args.run / "run.json").read_text())
        start = datetime.fromisoformat(source["started_at"])
        progress = args.run / "progress.jsonl"
        end = datetime.fromtimestamp(progress.stat().st_mtime, tz=UTC) + timedelta(minutes=2)
        return start, end, sum(1 for _ in progress.open())
    if not (args.start and args.end):
        raise SystemExit("give a run folder, or --from and --to")
    as_utc = lambda s: datetime.fromisoformat(s).replace(tzinfo=UTC)  # noqa: E731
    return as_utc(args.start), as_utc(args.end), None


SESSION_IN_STREAM = re.compile(r"\[runtime-logs-(.+?)\]")


def by_analyst(per_session: dict[str, list[Throttle]], analyst_of: dict[str, str]) -> str:
    """Throttled sessions per analyst, out of that analyst's investigations in the run. The limits are counted per
    analyst, so this is where it shows whether one analyst did the work of several. `analyst_of` maps a Runtime
    session id to the analyst the agent reported; a session that failed reported none and is listed as unknown."""
    done = Counter(analyst_of.values())
    met = Counter()
    for stream, found in per_session.items():
        if found:
            session = SESSION_IN_STREAM.search(stream)
            met[analyst_of.get(session.group(1), "unknown") if session else "unknown"] += 1
    names = sorted(set(done) | set(met), key=lambda n: (n == "unknown", n))
    return "by analyst: " + "; ".join(f"{n}: {met[n]} throttled of {done[n]} investigations" for n in names)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", nargs="?", type=Path, help="a run folder under evals/runs")
    ap.add_argument("--from", dest="start", help="UTC, e.g. 2026-11-18T12:10")
    ap.add_argument("--to", dest="end", help="UTC")
    ap.add_argument("--endpoint", default="DEFAULT", help="the Runtime endpoint whose log to read")
    args = ap.parse_args()

    import boto3

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from smoke_gateway import CREDS, load_env

    start, end, invocations = _window(args)
    group = re.sub(r"-DEFAULT$", f"-{args.endpoint}", load_env(CREDS)["SURV_RUNTIME_LOG_GROUP"])
    logs = boto3.client("logs", region_name=REGION)
    t0, t1 = int(start.timestamp() * 1000), int(end.timestamp() * 1000)
    streams: set[str] = set()
    pages = logs.get_paginator("filter_log_events").paginate(
        logGroupName=group, startTime=t0, endTime=t1, filterPattern='"gateway answered"'
    )
    for page in pages:
        streams.update(e["logStreamName"] for e in page["events"])
    per_session = {}
    for stream in sorted(streams):
        events = logs.get_log_events(
            logGroupName=group, logStreamName=stream, startTime=t0, endTime=t1, startFromHead=True
        )
        per_session[stream] = throttles([e["message"] for e in events["events"]])
    print(f"{group}\n{start:%Y-%m-%d %H:%M} to {end:%H:%M} UTC")
    print(report(per_session, invocations))
    if args.run:
        analyst_of = {}
        for saved in (args.run / "responses").glob("*.json"):
            response = json.loads(saved.read_text()).get("response") or {}
            if response.get("session_id"):
                analyst_of[response["session_id"]] = response.get("analyst") or "unknown"
        print(by_analyst(per_session, analyst_of))
    return 0


if __name__ == "__main__":
    sys.exit(main())
