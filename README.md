# Trade Surveillance Alert Investigator on Amazon Bedrock AgentCore

A Level-1 trade-surveillance analyst agent that investigates spoofing and layering alerts raised by a deterministic detector, gathers evidence through governed tools, writes an auditable investigation report and proposes a disposition. A human records the disposition; the agent never can, and AgentCore Policy enforces that at the Gateway.

Built as George's TFC Artificial Intelligence and Machine Learning project (Agentic AI learning path), to be presented to a mentor. Two goals in equal measure: solve a real problem for brokers and trading firms, and learn Amazon Bedrock AgentCore in depth.

Repository: `https://github.com/donquixote47/surveillance-investigator` (private). Documentation is bilingual: `docs/en/` (canonical) and `docs/el/` (Greek twin). Τα ελληνικά κείμενα είναι στο `docs/el/`.

## Status

| Item | Value |
|---|---|
| Phase | 5 complete (2026-11-07) with iterations 3 and 4, the variance run and the seed8 generalisation run (2026-11-10/11); the review hardening released 2026-11-16 as `v0.3.0-alpha` (record integrity, IAM limit on the agent's write, proposal provenance, per-order facts for large orders): Runtime v17 on `demo`, run `20261116T1828-sonnet-v5` passes the promotion rule (gate 0 of 28, safe close 94.2%). Next: Phase 6 (slides, rehearsal). Measured 2026-11-17 on the focused dataset `seed9` (48 alerts): the registered market maker who spoofs (S-SPOOF-6) escalated 12 of 12, his innocent twin (F-MM-LARGE-1) closed 12 of 12, and both the same on three repetitions. See `docs/en/STATUS.md` and `docs/en/05-build-plan.md` |
| Region | eu-west-2 |
| Stack | Python 3.14 (uv), Strands Agents 1.63, Claude Sonnet 5.5 (eu. inference profile), AgentCore CLI 1.0.2 (`agentcore.json` for AgentCore resources), AWS CDK (Python) for the mock back end |
| Cost rule | Zero third-party cost. AWS cost is not a constraint but is announced before every deploy and tracked in STATUS; every resource carries `Project` and `auto-delete=no` tags (`scripts/check_tags.py`) |
| Deployed resources | eu-west-2: stack `SurvFirm` (DynamoDB, Lambdas, Cognito, HTTP API), stack `AgentCore-surv-default` (Gateway + rate limits, Runtime); full table in `docs/en/STATUS.md`. Dataset `data/synthetic/seed7` (committed): 167 alerts, 17% true abuse, loaded in DynamoDB |

## The problem in one paragraph

Every broker, investment firm and algorithmic trading firm in the EU must monitor its order flow for market manipulation and report suspicious orders and transactions (MAR Art. 16(2); RTS 6 Art. 13 for algorithmic traders). Rule-based detectors are tuned for recall and so raise many alerts, most of them on legitimate activity: market making, algorithmic re-pricing, risk cuts, reactions to news. Each alert must still be reviewed by a trained person and the reasoning behind each closure kept for the regulator. At a mid-sized firm that is a small compliance team working a queue every morning, repeating the same evidence-gathering steps per alert. The cost is analyst time; the risk is the true case buried among false positives. Detail in `docs/en/01-domain-primer.md` and `docs/en/02-problem-statement.md`.

## What the agent does

1. Pulls an alert and the raw order and trade events around it from a mock surveillance back end.
2. Reconstructs the order book, computes the discriminators deterministically (order-to-trade ratio, cancel latency, size vs depth, opposite-side fills, cancel symmetry), reads the trader's profile and alert history, checks market events in the window, and recalls prior analyst decisions from Memory.
3. Writes an investigation report in the vocabulary of the regulation's indicators, citing every piece of evidence it used, listing the legitimate explanations it considered and how it ruled them out.
4. Proposes one disposition: close as false positive, escalate to Level 2, or draft a STOR narrative. The analyst records the decision.

Every tool call goes through AgentCore Gateway, where Policy decides deterministically whether the call is allowed given what the agent has already done in the session.

## AgentCore capabilities exercised

| Capability | Role in this project |
|---|---|
| Runtime | Hosts the Strands agent; one session per alert |
| Gateway | Exposes the back end's Lambda tools as MCP under target `surv`; per-user rate limits |
| Identity | Cognito JWT inbound auth; L1 and L2 analyst groups; separate human path for recording dispositions |
| Policy (Dogwood/Cedar, temporal) | Evidence before proposal, one proposal per alert, no disposition recording, STOR drafting only for L2 |
| Memory | Analyst dispositions and feedback per trader and instrument; ingested procedures |
| Code Interpreter | Designed for charts in the report; **not built** (the deterministic metrics stayed in Lambda; `docs/en/09-product-decisions.md` section 4) |
| Observability | Traces plus policy decision logs: the regulator's "why" |
| Evaluations | Ground-truth and custom evaluators over a labelled synthetic dataset; our harness computes the gate (0 missed true cases), the safe close rate and the override rate |
| Optimization | Prompt recommendations from traces, configuration bundles, A/B through the Gateway; promoted only through the deterministic gate (the governed learning loop) |
| A2A, Registry | Stretch |

## Repository layout

```
.kiro/steering/     Always-on project knowledge for Kiro (read these first)
.kiro/hooks/        Session brief, docs-sync, deploy cost guard
.claude/            The same standing instructions for Claude Code: CLAUDE.md and rules/ (identical copies of .kiro/steering/)
docs/en/            Scope, domain primer, problem statement, design, data and evaluation, build plan, resources, glossary, decisions, STATUS
docs/el/            Greek twins of the above
src/market_sim/     Limit-order-book simulator with scenario injection
src/detector/       The deliberately noisy spoofing/layering detector
src/tools/          Tool implementations (Lambda handlers and the pure discriminator functions)
app/surv_investigator_l1/  The agent: report model, system prompt, Strands agent + guard, Runtime entrypoint, tests
agentcore/          AgentCore CLI project: agentcore.json, deployed state, CDK stack with the Gateway rate limits
infra/              CDK app for the mock back end (Lambda, DynamoDB, S3, Cognito, HTTP API)
policies/           Cedar/Dogwood policy files, one rule each (Phase 4)
data/synthetic/     seed7 dataset with labels (committed, 23 MB, deterministic)
surv-tools.json     Gateway tool schema, generated from src/tools/schema.py
evals/              Evaluation harness, ground-truth files, run outputs (Phase 5)
scripts/            build_dataset, replay_alert, load_dynamodb, smoke_gateway, investigate, invoke_runtime, check_tags
ui/                 Analyst UI (Streamlit, loopback) and its clients: Cognito login, human-path API, Runtime, CloudWatch spans
```

## Quick start (local, no AWS)

```
uv sync --all-groups
uv run pytest                                                  # 107 tests: book, detector, scenarios, discriminators, tools on moto DynamoDB, report guard, metrics
uv run scripts/build_dataset.py --seed 7 --sessions 20 --catalogue 1   # ~30 s; regenerates data/synthetic/seed7 exactly (catalogue 1 = the scenarios it was built from)
uv run scripts/replay_alert.py data/synthetic/seed7 --random 3 --reveal
```

## Against the deployed stack

```
uv run scripts/smoke_gateway.py -v                             # the 11 tools through the Gateway as l1.analyst
uv run scripts/investigate.py A-261006-0006 --reveal           # run the agent locally against the Gateway
uv run scripts/invoke_runtime.py A-261006-0006                 # invoke the deployed Runtime with the analyst's token
```
Analyst passwords are not in the repo (`~/.config/surv-investigator/analyst-credentials.env`). Resuming on a fresh machine or session: `docs/en/07-resume.md`.

## Working on this project with Kiro

Open this folder as the workspace root so the steering files and hooks load. The SessionStart hook prints `docs/en/STATUS.md` and recent changes. A PostToolUse hook fires after every file write and tells Kiro which documents to update, in both `docs/en` and `docs/el`, for the code or doc that changed (tool contracts, policy set, scenario catalogue, STATUS, decision log, or the language twin). A Stop hook checks at the end of each turn that sources are not newer than the docs and that every English document has a Greek twin with matching structure, and asks for a fix if not. The PreToolUse hook asks for confirmation before commands that create billable AWS resources. Kiro is instructed (`.kiro/steering/challenge-and-verify.md`) not to agree by default and to verify claims from primary sources.

## Working on this project with Claude Code

The same standing instructions load from `.claude/rules/` (five files, byte-identical to `.kiro/steering/`), and `.claude/CLAUDE.md` says how to read them there: the Kiro hooks do not run under Claude Code, so the session brief, the docs update, the docs-sync check and the confirmation before a billable AWS command are done by hand. `python3 .kiro/hooks/scripts/docs-sync-check.py` checks three things: sources not newer than the docs, English and Greek twins with the same structure, and the two copies of the instructions identical. Change a rule on one side and copy it to the other.

## Documents

- `docs/en/00-scope.md` what is in, what is out, why surveillance and not sanctions
- `docs/en/01-domain-primer.md` market abuse, spoofing and layering, how surveillance works, regulation, vendors
- `docs/en/02-problem-statement.md` the business problem, the buyer, why an agent, the metric
- `docs/en/03-solution-design.md` architecture, AgentCore mapping, tool contracts, policies, memory, demo script, anticipated questions
- `docs/en/04-synthetic-data-and-evaluation.md` simulator, scenario catalogue, labels, detector, evaluation harness
- `docs/en/05-build-plan.md` phases with milestones and cost notes
- `docs/en/06-learning-resources.md` reading path
- `docs/en/07-resume.md` how to resume work in a new session or on a new machine
- `docs/en/08-broker-brief.md` the logic for a broker's surveillance team: what the agent does, the standard it applies, what it cannot do, the audit record, the numbers
- `docs/en/09-product-decisions.md` every product decision with its reason, where AgentCore does the work, cost to run, proof points, limitations, roadmap
- `docs/en/10-operations.md` how the product is run after the alpha: release cycle, what to watch, measured time and token breakdown, ranked backlog
- `docs/en/11-market-landscape.md` who else puts AI on surveillance alerts (Robinhood, Nasdaq, NICE, Eventus, eflow, SteelEye, Solidus, FIS, AWS samples), whether there is a direct competitor, who the customer is, the prospect checklist, what to borrow
- `docs/en/12-presenter-guide.md` for the speaker: the story in plain words, the seven domain ideas needed to tell it, what to say at each demo step, the numbers to know, hard questions with honest answers, what not to claim
- `docs/en/13-tools-and-policies.md` one page in plain words: the twelve Gateway tools, the nine AgentCore policies, and the controls that are not policies
- `docs/en/glossary.md`, `docs/en/decision-log.md`, `docs/en/STATUS.md`
