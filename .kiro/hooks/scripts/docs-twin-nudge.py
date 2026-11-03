#!/usr/bin/env python3
"""PostToolUse hook on file-writing tools (fs_write, fs_append, str_replace, delete_file).

When a source file or a doc changes, print a short instruction telling the agent which
documents must be updated in the SAME turn, in BOTH docs/en and docs/el. PostToolUse hooks
cannot block; stdout is added to the agent's context. Silent when the path is irrelevant.

De-duplicates per path within a turn using .kiro/.docs-nudge-state, which the Stop hook
(docs-sync-check.sh) deletes at the end of every turn.
"""

import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
STATE = os.path.join(ROOT, ".kiro", ".docs-nudge-state")

# (path prefix or exact file, [docs to update in docs/en AND docs/el])
SOURCE_RULES = [
    (
        "src/tools/",
        [
            "03-solution-design.md: section 4 tool contracts (inputs, outputs, policy-referenced fields); section 5 if report fields changed",
            "README.md capability table only if a new AgentCore feature is exercised",
        ],
    ),
    (
        "src/agent/",
        [
            "03-solution-design.md: section 2 (agent role), section 5 (InvestigationReport schema), section 7 (memory use)",
        ],
    ),
    (
        "src/market_sim/",
        [
            "04-synthetic-data-and-evaluation.md: section 2 simulator and scenario catalogue (ids, labels, scripts)",
        ],
    ),
    (
        "src/detector/",
        [
            "04-synthetic-data-and-evaluation.md: section 3 detector rule and detector version",
        ],
    ),
    (
        "infra/",
        [
            "03-solution-design.md: section 1 architecture, section 3 data model, section 8 identity",
            "STATUS.md deployed-resources table after any deploy",
        ],
    ),
    (
        "policies/",
        [
            "03-solution-design.md: section 6 policy set table (control, rule type, file); section 11 demo script if it adds a demo moment",
        ],
    ),
    (
        "evals/",
        [
            "04-synthetic-data-and-evaluation.md: section 4 harness, metrics, baselines, promotion rule",
            "STATUS.md last evaluation run",
        ],
    ),
    (
        "scripts/",
        [
            "05-build-plan.md if a milestone is affected; STATUS.md if phase or resources change",
        ],
    ),
    (
        "agentcore/",
        [
            "STATUS.md deployed resources; 03-solution-design.md section 2 if the set of AgentCore services changes; section 6 if policies change",
        ],
    ),
    (
        "agentcore.json",
        [
            "STATUS.md deployed resources; 03-solution-design.md section 2 if the set of AgentCore services changes",
        ],
    ),
    (
        "pyproject.toml",
        [
            "05-build-plan.md Phase 0 stack line and README status table if the stack changes",
        ],
    ),
]

CLOSING = (
    "Also append to decision-log.md (en and el) if an alternative was chosen, and mark new claims "
    "[verified ...] or [unverified]. Rules: .kiro/steering/docs-maintenance.md."
)


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0
    tool_input = event.get("tool_input") or {}
    path = tool_input.get("path") or tool_input.get("file_path") or ""
    if not path:
        return 0
    cwd = event.get("cwd") or ROOT
    abs_path = path if os.path.isabs(path) else os.path.join(cwd, path)
    try:
        rel = os.path.relpath(os.path.abspath(abs_path), ROOT).replace(os.sep, "/")
    except ValueError:
        return 0
    if rel.startswith(".."):
        return 0

    # De-dupe within the turn.
    key = rel + "\n"
    try:
        with open(STATE, encoding="utf-8") as fh:
            if key in fh.read():
                return 0
    except FileNotFoundError:
        pass

    message = None
    if rel.startswith("docs/en/") and rel.endswith(".md"):
        twin = "docs/el/" + rel[len("docs/en/") :]
        message = (
            f"[docs-twin-sync] {rel} changed. Mirror the same change in {twin} in THIS turn: same headings in the "
            "same order, same tables and rows, same numbers, sources and URLs, same checkboxes and code blocks; "
            "technical terms stay in English inside the Greek text; verification markers unchanged. "
            f"If {twin} does not exist, create it as a full translation. If the change genuinely needs no Greek "
            f"edit (e.g. an English-only typo), run `touch {twin}` so the Stop parity check passes."
        )
    elif rel.startswith("docs/el/") and rel.endswith(".md"):
        twin = "docs/en/" + rel[len("docs/el/") :]
        message = (
            f"[docs-twin-sync] {rel} changed. docs/en is canonical: if this was a content change (not a translation "
            f"fix), apply the same change to {twin} in THIS turn so headings, tables, numbers and sources match."
        )
    else:
        for prefix, docs in SOURCE_RULES:
            if rel == prefix or rel.startswith(prefix):
                bullets = "\n".join(f"  - {d}" for d in docs)
                message = (
                    f"[docs-twin-sync] Source changed: {rel}. Update in THIS turn, in BOTH docs/en and docs/el:\n"
                    f"{bullets}\n{CLOSING}"
                )
                break

    if message is None:
        return 0

    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "a", encoding="utf-8") as fh:
        fh.write(key)
    print(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
