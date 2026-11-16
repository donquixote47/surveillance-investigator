# Trade Surveillance Alert Investigator on AgentCore

The project's standing instructions are in `.claude/rules/` and load with every session, for subagents too:

| File | What it holds |
|---|---|
| `rules/project-context.md` | What the project is, the hard constraints, stack and conventions, how to work with George |
| `rules/challenge-and-verify.md` | Do not agree by default; verify every claim from a primary source; the `[verified ...]` / `[unverified]` markers |
| `rules/docs-maintenance.md` | Bilingual docs (`docs/en` canonical, `docs/el` twin), what to update when, style |
| `rules/domain-primer.md` | Compact domain knowledge: market abuse, spoofing and layering, the regulation |
| `rules/agentcore-gotchas.md` | AgentCore behaviours verified by doing, with dates; re-check before asserting |

They are copies of `.kiro/steering/`, made on 2026-11-16 when the project moved from Kiro to Claude Code. The two
sets are kept byte-identical so the project works under either tool: change a rule in one, copy it to the other.
`python3 .kiro/hooks/scripts/docs-sync-check.py` reports any difference.

## Reading the rules under Claude Code

The rules were written for Kiro. Three things they rely on do not exist here:

- **"Kiro" is you.** Where a rule says what Kiro does or must do, it applies to you.
- **The Kiro hooks do not run** (`.kiro/hooks/`). Do by hand what they did:
  - at the start of a session, read `docs/en/STATUS.md` and the last entries of `docs/en/decision-log.md`
    (`bash .kiro/hooks/scripts/session-brief.sh` prints the same brief the SessionStart hook printed);
  - after changing source, policies, infra, evals, scripts or a document, update the documents the table in
    `rules/docs-maintenance.md` names, in English and in Greek, in the same turn;
  - before ending a turn that changed source or documents, run `python3 .kiro/hooks/scripts/docs-sync-check.py`.
    It prints nothing when the documents are in sync; otherwise it prints what to fix;
  - before any command that creates or changes billable AWS resources (`agentcore deploy`, `cdk deploy`,
    `aws ... create-*` / `update-*`, an `invoke-agent-runtime`, a paid evaluation run), state the cost and what it
    changes, and wait for George's go-ahead. The tools Lambda has no alias: `cdk deploy SurvFirm` changes what the
    released `demo` endpoint calls as soon as it finishes.
- **The `aws-agentcore` power** (`search_agentcore_docs`, `fetch_agentcore_doc`) is a Kiro tool. Read the AgentCore
  developer guide and API reference on docs.aws.amazon.com instead and cite the page; if a claim cannot be checked
  in the session, mark it `[unverified]` where it is written.

## Checks before saying a change is done

```
uv run pytest
uv run ruff check . && uv run ruff format --check .
python3 .kiro/hooks/scripts/docs-sync-check.py
```
