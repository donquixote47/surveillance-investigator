#!/usr/bin/env python3
"""Stop hook: keep code, architecture and the bilingual docs in sync.

Three checks, run at the end of every agent turn:

1. Source vs docs: if any file under the source paths is newer than every doc and newer than the
   marker .kiro/.docs-sync-last, ask the agent to review and update the docs (both languages).
2. EN/EL parity: for every docs/en/X.md there must be a docs/el/X.md (and vice versa) with the
   same number of headings, table rows, checkboxes and fenced code blocks, and the Greek file
   must not be older than the English one.
3. Rule parity: the standing instructions exist twice, .kiro/steering/X.md for Kiro and
   .claude/rules/X.md for Claude Code (copied 2026-11-16). Each file must exist on both sides with
   identical content, or the two tools work to different rules.

Output {"decision":"block","reason":...} to make the agent do another turn. Blocks at most once
per identical set of findings (guard file), so a forgotten fix cannot loop forever; it will nag
again after the next change. Also clears the per-turn de-dupe state of the PostToolUse nudge.
"""

import hashlib
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
MARKER = os.path.join(ROOT, ".kiro", ".docs-sync-last")
GUARD = os.path.join(ROOT, ".kiro", ".docs-sync-blocked")
NUDGE_STATE = os.path.join(ROOT, ".kiro", ".docs-nudge-state")

SRC_PATHS = ["src", "app", "ui", "infra", "policies", "evals", "scripts", "agentcore", "agentcore.json", "pyproject.toml"]
DOC_PATHS = ["README.md", "docs"]
EXCLUDE_DIRS = {"__pycache__", ".venv", "node_modules", "cdk.out", ".git", "runs", ".cache", ".cli", "dist", "build", ".ruff_cache", ".pytest_cache"}
EXCLUDE_NAMES = {".DS_Store"}
MTIME_TOLERANCE_S = 2  # en and el written in the same turn count as in sync


def iter_files(path: str):
    full = os.path.join(ROOT, path)
    if os.path.isfile(full):
        yield full
        return
    for dirpath, dirnames, filenames in os.walk(full):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for name in filenames:
            if name in EXCLUDE_NAMES or name.endswith(".pyc"):
                continue
            yield os.path.join(dirpath, name)


def newest(paths):
    best, best_path = 0.0, None
    for p in paths:
        for f in iter_files(p):
            try:
                m = os.stat(f).st_mtime
            except OSError:
                continue
            if m > best:
                best, best_path = m, f
    return best, best_path


def mtime(path: str) -> float:
    try:
        return os.stat(path).st_mtime
    except OSError:
        return 0.0


def structure(path: str) -> dict:
    """Cheap structural fingerprint: headings, table rows, checkboxes, fenced blocks."""
    counts = {"headings": 0, "table_rows": 0, "checkboxes": 0, "fences": 0}
    in_fence = False
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                s = line.rstrip("\n")
                if s.startswith("```"):
                    counts["fences"] += 1
                    in_fence = not in_fence
                    continue
                if in_fence:
                    continue
                if re.match(r"^#{1,6}\s", s):
                    counts["headings"] += 1
                elif s.lstrip().startswith("|"):
                    counts["table_rows"] += 1
                if re.match(r"^\s*[-*]\s\[[ xX]\]\s", s):
                    counts["checkboxes"] += 1
    except OSError:
        pass
    return counts


def rel(path: str) -> str:
    return os.path.relpath(path, ROOT).replace(os.sep, "/")


def source_findings() -> list[str]:
    src_newest, _ = newest(SRC_PATHS)
    if src_newest == 0:
        return []
    doc_newest, _ = newest(DOC_PATHS)
    ref = max(doc_newest, mtime(MARKER))
    if src_newest <= ref:
        return []
    changed = []
    for p in SRC_PATHS:
        for f in iter_files(p):
            if mtime(f) > ref:
                changed.append(rel(f))
    changed.sort()
    shown = ", ".join(changed[:25]) + (" ..." if len(changed) > 25 else "")
    return [
        "Source files changed after the docs were last updated: "
        + shown
        + ". Review and update the related documents in BOTH docs/en and docs/el (03-solution-design.md tool "
        "contracts and policy set; 04-synthetic-data-and-evaluation.md scenarios and harness; STATUS.md phase "
        "and deployed resources; decision-log.md), per .kiro/steering/docs-maintenance.md. If nothing needs to "
        "change, say so in one line. Either way run: touch .kiro/.docs-sync-last"
    ]


def parity_findings() -> list[str]:
    en_dir = os.path.join(ROOT, "docs", "en")
    el_dir = os.path.join(ROOT, "docs", "el")
    if not os.path.isdir(en_dir):
        return []
    en = {f for f in os.listdir(en_dir) if f.endswith(".md")}
    el = {f for f in os.listdir(el_dir) if f.endswith(".md")} if os.path.isdir(el_dir) else set()

    findings = []
    for name in sorted(en - el):
        findings.append(f"docs/el/{name} is missing: create it as a full Greek twin of docs/en/{name}.")
    for name in sorted(el - en):
        findings.append(f"docs/el/{name} has no English twin: create docs/en/{name} or remove the orphan.")
    for name in sorted(en & el):
        en_p, el_p = os.path.join(en_dir, name), os.path.join(el_dir, name)
        problems = []
        if mtime(en_p) > mtime(el_p) + MTIME_TOLERANCE_S:
            problems.append("English is newer than Greek")
        s_en, s_el = structure(en_p), structure(el_p)
        diffs = [f"{k} {s_en[k]} vs {s_el[k]}" for k in s_en if s_en[k] != s_el[k]]
        if diffs:
            problems.append("structure differs (en vs el): " + ", ".join(diffs))
        if problems:
            findings.append(f"docs/en/{name} <-> docs/el/{name}: " + "; ".join(problems) + ".")
    if findings:
        findings.append(
            "Fix the Greek twins now: same headings in the same order, same tables and rows, same checkboxes, "
            "same code blocks, same numbers and sources; technical terms stay in English. If an English change "
            "needs no Greek edit, `touch` the Greek file."
        )
    return findings


def steering_findings() -> list[str]:
    kiro_dir = os.path.join(ROOT, ".kiro", "steering")
    claude_dir = os.path.join(ROOT, ".claude", "rules")
    if not os.path.isdir(kiro_dir) or not os.path.isdir(claude_dir):
        return []  # a checkout that carries only one tool's rules has nothing to compare
    kiro = {f for f in os.listdir(kiro_dir) if f.endswith(".md")}
    claude = {f for f in os.listdir(claude_dir) if f.endswith(".md")}
    findings = []
    for name in sorted(kiro - claude):
        findings.append(f".claude/rules/{name} is missing: copy .kiro/steering/{name} there.")
    for name in sorted(claude - kiro):
        findings.append(f".kiro/steering/{name} is missing: copy .claude/rules/{name} there.")
    for name in sorted(kiro & claude):
        try:
            with open(os.path.join(kiro_dir, name), "rb") as a, open(os.path.join(claude_dir, name), "rb") as b:
                same = a.read() == b.read()
        except OSError:
            same = False
        if not same:
            findings.append(
                f".kiro/steering/{name} and .claude/rules/{name} differ: make them identical "
                "(the newer edit is the one to keep; copy it over the other)."
            )
    return findings


def main() -> int:
    # Clear the PostToolUse nudge de-dupe state at the end of every turn.
    try:
        os.remove(NUDGE_STATE)
    except OSError:
        pass

    findings = source_findings() + parity_findings() + steering_findings()
    if not findings:
        try:
            os.remove(GUARD)
        except OSError:
            pass
        return 0

    digest = hashlib.sha256("\n".join(findings).encode("utf-8")).hexdigest()
    try:
        with open(GUARD, encoding="utf-8") as fh:
            if fh.read().strip() == digest:
                return 0  # already asked once for exactly these findings; don't loop
    except FileNotFoundError:
        pass
    os.makedirs(os.path.dirname(GUARD), exist_ok=True)
    with open(GUARD, "w", encoding="utf-8") as fh:
        fh.write(digest)

    reason = "Docs sync check (bilingual):\n- " + "\n- ".join(findings)
    print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
