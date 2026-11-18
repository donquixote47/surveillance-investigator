"""What goes into the Runtime bundle is fixed (decision log 2026-11-18).

The AgentCore CLI zips the agent's folder, whole, with whatever `uv pip install` resolves from the folder's
`[project].dependencies`. Two things follow. Every package is locked to one version there, or a deploy that changes
nothing in the agent cuts a new Runtime version (v18, 2026-11-17: a boto3 patch release). And the folder holds the
agent and nothing else: a test file or a note left in it ships to the Runtime, and editing it is a new version.
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

import pytest
from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import lock_runtime_deps  # noqa: E402
from lock_runtime_deps import PYPROJECT, STAGING, from_staging, norm, read_pyproject  # noqa: E402

# What the packager leaves out of the zip (`@aws/agentcore-cdk`, packaging/helpers.js, EXCLUDED_ENTRIES).
PACKAGER_SKIPS = {".git", ".venv", "__pycache__", ".pytest_cache", ".DS_Store", "node_modules"}


def test_every_package_of_the_bundle_is_locked_to_one_version():
    _, direct, locked = read_pyproject()
    declared = tomllib.loads(PYPROJECT.read_text())["project"]["dependencies"]
    assert declared[: len(direct)] == direct, "the direct requirements come first"
    pins = declared[len(direct) :]
    assert pins, "no locked block: run scripts/lock_runtime_deps.py"
    for pin in pins:
        assert re.fullmatch(r"[A-Za-z0-9._-]+==[A-Za-z0-9.!+_-]+", pin), f"not an exact version: {pin}"
    assert len({norm(p.split("==")[0]) for p in pins}) == len(pins) == len(locked), "one line per package"


def test_the_lock_satisfies_the_direct_requirements():
    _, direct, locked = read_pyproject()
    for line in direct:
        req = Requirement(line)
        assert norm(req.name) in locked, f"{req.name} is required and not locked"
        assert req.specifier.contains(locked[norm(req.name)]), f"{line}: locked at {locked[norm(req.name)]}"


def test_the_bundle_folder_holds_the_agent_and_nothing_else():
    shipped = {p.name for p in PYPROJECT.parent.iterdir()} - PACKAGER_SKIPS
    assert shipped == {
        "AGENTS.md",
        "README.md",
        "investigator.py",
        "main.py",
        "prompt.py",
        "pyproject.toml",
        "report.py",
    }


def test_the_last_local_build_carried_the_locked_set():
    """`agentcore build` and `agentcore deploy` leave what they installed in the staging folder, with a copy of the
    pyproject.toml they read. When that copy is this file, what was installed is the lock."""
    staged = STAGING / "pyproject.toml"
    if not staged.exists() or staged.read_bytes() != PYPROJECT.read_bytes():
        pytest.skip("no local build of this pyproject.toml (run `agentcore build`)")
    _, _, locked = read_pyproject()
    assert from_staging() == locked


def test_the_outdated_report_flags_a_locked_version_that_has_an_advisory(monkeypatch, capsys):
    """A lock stops security fixes from arriving by themselves; `--outdated` is the look that replaces them. It
    exits 2 when a locked version has a published advisory, and names the version that fixes it. The advisory
    database is stubbed: the test is about what the report does with an answer, not about the network."""
    locked = {"alpha": "1.0.0", "beta": "2.0.0"}
    monkeypatch.setattr(lock_runtime_deps, "resolve", lambda _req: {"alpha": "1.0.1", "beta": "2.0.0"})

    def osv(path, body=None):
        if path == "querybatch":
            assert [q["package"]["name"] for q in body["queries"]] == ["alpha", "beta"]
            assert [q["version"] for q in body["queries"]] == ["1.0.0", "2.0.0"]
            return {"results": [{}, {"vulns": [{"id": "GHSA-test"}]}]}
        assert path == "vulns/GHSA-test"
        ranges = [{"events": [{"introduced": "0"}, {"fixed": "2.0.1"}]}]
        other = {"package": {"name": "gamma"}, "ranges": [{"events": [{"fixed": "9.9.9"}]}]}
        return {"summary": "a test advisory", "affected": [{"package": {"name": "Beta"}, "ranges": ranges}, other]}

    monkeypatch.setattr(lock_runtime_deps, "_osv", osv)
    assert lock_runtime_deps.report_outdated(["alpha >= 1"], locked) == 2
    out = capsys.readouterr().out
    assert "alpha: 1.0.0 -> 1.0.1" in out and "beta: " not in out, "only what an upgrade would change is listed"
    assert "beta==2.0.0  GHSA-test  fixed in 2.0.1" in out and "9.9.9" not in out

    monkeypatch.setattr(lock_runtime_deps, "_osv", lambda path, body=None: {"results": [{}, {}]})
    assert lock_runtime_deps.report_outdated(["alpha >= 1"], locked) == 0
    assert "none" in capsys.readouterr().out
