"""The throttling report reads a session's log lines the way the Runtime writes them (2026-11-18).

Run v6 reported 2 failed investigations while 79 of its 169 invocations had met a 429: the agent's retries hide a
throttle that recovers. The report counts them from the Runtime's log and says, from the position of the throttled
request, which limit answered. The lines below are in the Runtime's format, shortened.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from gateway_throttling import Throttle, by_analyst, report, throttles

GW = "https://surv-default-surv-investigator-x.gateway.bedrock-agentcore.eu-west-2.amazonaws.com/mcp"


def _request(at: str, status: str = "200 OK") -> str:
    return (
        f'2026-11-17 {at} INFO [httpx] [_client.py:1740] [trace_id=abc] - HTTP Request: POST {GW} "HTTP/1.1 {status}"'
    )


def _retry(at: str, attempt: int, of: int, delay: int) -> str:
    return (
        f"2026-11-17 {at} WARNING [surv.investigator] [investigator.py:110] [trace_id=abc] - "
        f"gateway answered 429; retry {attempt}/{of} in {delay}s"
    )


def _twelve_requests() -> list[str]:
    """Opening the MCP session and nine tools: twelve requests within a few seconds."""
    return [_request(f"23:59:{38 + i // 2:02d},{(i % 2) * 500:03d}") for i in range(12)]


def test_a_proposal_that_waits_and_goes_through_is_one_throttle_on_request_thirteen():
    lines = [
        *_twelve_requests(),
        _retry("23:59:59,336", 1, 5, 2),
        _retry("00:00:01,400", 2, 5, 4),
        _request("00:00:05,601"),
        "Traceback lines and anything without a timestamp are ignored",
    ]
    (one,) = throttles(lines)
    assert one == Throttle(request_number=13, pause_s=one.pause_s, retries=2, waited_s=6, gave_up=False)
    assert 15 < one.pause_s < 16, "the model wrote the report in between"
    assert one.is_the_proposal


def test_a_request_the_agent_gave_up_on_is_marked():
    lines = [*_twelve_requests(), *[_retry(f"23:59:{50 + i},000", i + 1, 3, 2 ** (i + 1)) for i in range(3)]]
    lines.append(_request("00:00:10,000", "429 Too Many Requests"))
    (one,) = throttles(lines)
    assert one.gave_up and one.retries == 3 and one.waited_s == 14

    cut_off = throttles([*_twelve_requests(), _retry("23:59:59,000", 1, 5, 2)])
    assert cut_off[0].gave_up, "a log that ends inside a wait is a session that did not finish"


def test_a_throttle_in_the_middle_of_the_tool_calls_is_not_read_as_the_proposal():
    lines = [
        _request("23:59:38,000"),
        _request("23:59:38,200"),
        _retry("23:59:38,400", 1, 5, 2),
        _request("23:59:40,500"),
    ]
    (one,) = throttles(lines)
    assert one.request_number == 3 and one.pause_s < 1 and not one.is_the_proposal


def test_the_report_counts_sessions_and_names_the_limit():
    sessions = {
        "a": [Throttle(13, 11.0, 1, 2, False)],
        "b": [Throttle(13, 14.0, 3, 14, True)],
        "c": [Throttle(4, 0.2, 1, 2, False)],
        "d": [],
    }
    text = report(sessions, invocations=10)
    assert "sessions that met a 429: 3 of 10 invocations; throttled requests: 3" in text
    assert "2 of 3 on a request that followed a pause" in text and "1 elsewhere" in text
    assert "request number of the throttled request: 4: 1, 13: 2" in text
    assert "requests the agent gave up on (still 429 after the last wait): 1" in text
    assert report({"d": []}, invocations=10) == "sessions that met a 429: 0 of 10 invocations; throttled requests: 0"


def test_throttled_sessions_are_counted_per_analyst():
    """The limits are per analyst: the breakdown shows whether one analyst did the work of several."""
    stream = "2026/11/18/[runtime-logs-{}]0a1b"
    per_session = {
        stream.format("s1"): [Throttle(13, 11.0, 1, 2, False)],
        stream.format("s2"): [Throttle(13, 12.0, 5, 62, True)],
        stream.format("s3"): [],
        stream.format("s9"): [Throttle(13, 10.0, 1, 2, False)],  # an attempt that failed and was run again
    }
    analyst_of = {"s1": "l1.analyst", "s2": "l1.analyst", "s3": "l1.analyst2", "s4": "l1.analyst2"}
    assert by_analyst(per_session, analyst_of) == (
        "by analyst: l1.analyst: 2 throttled of 2 investigations; l1.analyst2: 0 throttled of 2 investigations; "
        "unknown: 1 throttled of 0 investigations"
    )
