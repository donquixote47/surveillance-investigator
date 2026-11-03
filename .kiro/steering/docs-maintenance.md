# Docs maintenance rules

The docs are the project deliverable as much as the code: the mentor reads them, and George uses them to learn the domain. Keep them in sync in the same turn as the change, not later.

## Bilingual rule

`docs/en/<name>.md` is canonical. `docs/el/<name>.md` is its Greek twin: same file name, same headings in the same order, same tables, same numbers and sources. When one changes, change the other in the same turn. Technical terms stay in English inside the Greek text (spoofing, layering, order book, STOR, Gateway, Policy), with a short Greek gloss on first use in each document. Don't translate code, tool names, file paths, or policy text.

## What to update when

| Change | Update (en and el) |
|---|---|
| New or changed tool in the mock back end (`src/tools/`, `infra/`) | `03-solution-design.md` tool contract table; README capability table if a new AgentCore feature is exercised |
| New or changed policy (`policies/`) | `03-solution-design.md` policy set table (control, rule type, file); demo script if it creates a demo moment |
| New or changed scenario in the simulator (`src/market_sim/`) | `04-synthetic-data-and-evaluation.md` scenario catalogue; label definitions if they change |
| AgentCore resource created, updated, or deleted | `STATUS.md` deployed-resources table (name, id or ARN, region, created, cost note) |
| Phase started or finished | `STATUS.md` phase line and "next step"; README status table; tick the milestone in `05-build-plan.md` |
| Any decision with alternatives (framework, service, naming, scope) | Append an entry to `decision-log.md` |
| A claim in the docs found wrong | Fix it, mark `[verified ...]` or `[unverified]`, add a decision-log line |
| New AgentCore behaviour learned or an assumption proven wrong | `.kiro/steering/agentcore-gotchas.md` with date |
| New domain fact learned | `.kiro/steering/domain-primer.md` (compact) and `01-domain-primer.md` or `glossary.md` (detail) |
| New reading found useful | `06-learning-resources.md` |
| New script, secret location, deploy command or prerequisite | `07-resume.md` |

## Docs-sync hooks contract (`.kiro/hooks/docs-sync.json`)

Two hooks enforce the table above and the bilingual rule. Treat their messages as instructions to act in the current turn, not as warnings.

**1. PostToolUse nudge (`docs-twin-nudge.py`).** Fires after every `fs_write`, `fs_append`, `str_replace` or `delete_file`. If the path is under `src/`, `infra/`, `policies/`, `evals/`, `scripts/`, `agentcore.json` or `pyproject.toml`, it prints exactly which documents to update (for example `policies/` -> design doc section 6 policy set table). If the path is under `docs/en/`, it tells you to mirror the change in the `docs/el/` twin; if under `docs/el/`, to mirror in `docs/en/` when it was a content change. Do the update before finishing the turn. Silent for other paths; one message per path per turn.

**2. Stop check (`docs-sync-check.py`).** At the end of the turn it (a) compares source mtimes against `README.md`, `docs/**` and the marker `.kiro/.docs-sync-last`, and (b) checks EN/EL parity: every `docs/en/X.md` has a `docs/el/X.md` and vice versa, the Greek file is not older than the English one, and both have the same counts of headings, table rows, checkboxes and code fences. Any finding produces a follow-up turn with the list.

When you get a Stop follow-up:
1. Fix the listed items in both languages (missing twin: write the full translation; structure mismatch: align headings/tables/checkboxes; source changed: update the docs per the table above).
2. If a source change genuinely needs no doc change, say so in one line and run `touch .kiro/.docs-sync-last`.
3. If an English edit genuinely needs no Greek edit (English-only typo), run `touch docs/el/<file>` so the mtime check passes.

The Stop hook asks once per identical set of findings, so it cannot loop; it will ask again after the next change. The structural check is deliberately cheap (counts, not content); you remain responsible for the content being a faithful twin.

## Style

- Plain prose, tables for inventories, no marketing language. One idea per sentence.
- Every number has a source next to it. Every regulatory statement names the instrument and article.
- Verification markers: `[verified YYYY-MM-DD, source]` or `[unverified]`.
- Decision-log entries: date, decision, alternatives considered, reason, consequences.
- `STATUS.md` is short and current; history belongs in the decision log and the build plan.
- Dates in ISO format. Reference AgentCore docs by URL when stating behaviour.
