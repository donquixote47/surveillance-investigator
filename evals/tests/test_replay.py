"""Trajectory replay helpers: the recorded span result is unwrapped to the tool's JSON, and the diff names paths."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from replay_trajectory import canonical, diff  # noqa: E402

RECORDED = (
    'meta=None content=[TextContent(type=\'text\', text=\'{"alert_id": "A-261104-0010", "depth": 15.7, '
    '"events": [{"side": "BUY"}, {"side": "SELL"}]}\', annotations=None, meta=None)] '
    "structuredContent=None isError=False"
)


def test_recorded_repr_is_unwrapped_to_the_tool_json():
    v = canonical(RECORDED)
    assert v == {"alert_id": "A-261104-0010", "depth": 15.7, "events": [{"side": "BUY"}, {"side": "SELL"}]}
    assert canonical('{"a": 1}') == {"a": 1}
    assert canonical("plain text") == "plain text"
    assert canonical(None) is None


def test_diff_names_the_paths_that_differ():
    a = {"alert_id": "A", "depth": 15.7, "events": [{"side": "BUY"}, {"side": "SELL"}], "only_recorded": 1}
    b = {"alert_id": "A", "depth": 15.8, "events": [{"side": "BUY"}], "only_replayed": 2}
    d = diff(a, b)
    assert "/depth: recorded '15.7', replayed '15.8'" in d
    assert "/events: 2 items recorded, 1 replayed" in d
    assert "/only_recorded: missing in replay" in d
    assert "/only_replayed: missing in recorded" in d
    assert diff(a, a) == []
