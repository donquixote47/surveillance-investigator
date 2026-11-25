# Trade Surveillance Alert Investigator on Amazon Bedrock AgentCore

A Level-1 trade-surveillance analyst agent. It takes a spoofing or layering alert that a deterministic detector has raised, gathers the evidence through governed tools, writes an auditable investigation report and proposes a disposition. A human records the decision. The agent cannot: it has no tool, no IAM permission and no token for recording, and AgentCore Policy at the Gateway denies any tool outside the twelve it is given.

Built as George's project for the AWS AI/ML TFC (Agentic AI learning path). Two goals in equal measure: solve a real problem for brokers and trading firms, and learn Amazon Bedrock AgentCore in depth. All data is synthetic, from the project's own order-book simulator.

Documentation is bilingual: `docs/en/` (canonical) and `docs/el/` (Greek twin). Τα ελληνικά κείμενα είναι στο `docs/el/`.

## Where it stands

| Item | Value |
|---|---|
| Release | `v0.4.1-alpha` (2026-11-19). The running system is the one released as `v0.4.0-alpha` (2026-11-18); `v0.4.1-alpha` adds measurements and two corrections to the evaluation harness, with nothing deployed |
| Live system | eu-west-2. Runtime version 20 behind both endpoints (`demo`, `DEFAULT`); a Gateway with one Lambda target and twelve tools; a Policy Engine in `ENFORCE` with nine policies; Memory; two per-analyst rate limits. Two CloudFormation stacks, `SurvFirm` (the mock back end) and `AgentCore-surv-default`. Full table in `docs/en/STATUS.md` |
| Build plan | Phases 0 to 5 complete: setup, simulator and dataset, back end and Gateway, agent on Runtime, Policy and Memory, evaluation and learning loop. Phase 6 (slides, a timed rehearsal) is not done; the demo script and a speaker's guide exist (`docs/en/03-solution-design.md` section 12, `docs/en/12-presenter-guide.md`) |
| Stack | Python 3.14 (uv), Strands Agents (1.65 in the Runtime bundle), Claude Sonnet 5.5 through the `eu.` inference profile, AgentCore CLI 1.0.2 (`agentcore/agentcore.json`), AWS CDK in Python for the mock back end |
| Data | Three synthetic datasets, committed and loaded in DynamoDB: `seed7` (167 alerts, 28 of them real abuse; the regression set), `seed8` (100 alerts, 24 real abuse; never tuned against), `seed9` (48 alerts; a focused set on registered market makers) |
| Cost | About $615 of AWS spend to date at list prices, nearly all of it model and judge tokens. No third-party cost. Every resource carries the tags `Project` and `auto-delete=no` (`scripts/check_tags.py`) |

## What was measured

On Runtime version 20, the released one, with the agent on Claude Sonnet 5.5. Every number is on synthetic data.

| Dataset | Real abuse proposed for closing | False positives closed | Note |
|---|---|---|---|
| `seed7`, 167 alerts | 0 of 28 | 95.7% (133 of 139) on the release run, 94.2% (131 of 139) on a second run | the difference is inside the measured run-to-run noise |
| `seed8`, 100 alerts nothing was tuned against | 0 of 24 | 90.8% (69 of 76) | a mix with more boundary cases |
| `seed9`, 48 alerts | 0 of 12 | 36 of 36 | the registered market maker who spoofs escalated 12 of 12; his innocent twin closed 12 of 12 |

- The detector's own threshold rules, on the same 167 alerts of `seed7`, close as many false positives (133) and would close 6 of the 28 real cases.
- Repeated investigations: 26 alerts, five times each. 22 gave the same disposition every time, and none of the 35 investigations of real cases was proposed for closing.
- Evidence faithfulness: 99.9% of the numbers in the reports (3,936 of 3,940 on the release run) appear in a tool output of the same session.
- Judges (AgentCore Evaluations, on the second `seed7` run): Correctness 0.92, GoalSuccessRate 0.93, tool trajectory 1.00, report-quality rubric 0.61.
- About 24 seconds (median) and $0.09 of model tokens per alert.
- A coded promotion rule gates every change: no real case proposed for closing, the share of false positives closed not down by more than 2 points, no steadily closed scenario falling to zero, faithfulness at least 99%.

Detail, run by run: `docs/en/04-synthetic-data-and-evaluation.md` section 4.6. Every run's output is under `evals/runs/`.

## What is not built, and the limits

- Synthetic data only, from one simulator. Nothing here says a regulator accepts it, and analyst time saved has not been measured.
- One abuse type (spoofing and layering), one asset class, one venue.
- Code Interpreter (charts in the report) was designed and not built. The A/B test through the Gateway was not run: the one Optimization recommendation was rejected by the offline promotion rule first.
- No online evaluation, no dashboard, no slides.
- Two scenarios the agent closes only now and then (a loss-making exit, a reaction to news) are followed alert by alert in the repeat run and are not judged by the promotion rule.
- A transitive dependency of the Runtime bundle has an open advisory (`opentelemetry-api` 1.45.1, GHSA-mf5v-w3w3-f6cg, moderate). It is fixed in 1.45.2, which the AWS OpenTelemetry distro does not yet allow.

## The problem in one paragraph

Every broker, investment firm and algorithmic trading firm in the EU must monitor its order flow for market manipulation and report suspicious orders and transactions (MAR Art. 16(2); RTS 6 Art. 13 for algorithmic traders). Rule-based detectors are tuned for recall and so raise many alerts, most of them on legitimate activity: market making, algorithmic re-pricing, risk cuts, reactions to news. Each alert must still be reviewed by a trained person and the reasoning behind each closure kept for the regulator. At a mid-sized firm that is a small compliance team working a queue every morning, repeating the same evidence-gathering steps per alert. The cost is analyst time; the risk is the true case buried among false positives. Detail in `docs/en/01-domain-primer.md` and `docs/en/02-problem-statement.md`.

## What the agent does

1. Reads an alert and the raw order and trade events around it from a mock surveillance back end.
2. Has the order book reconstructed and the discriminators computed by deterministic tools (size against depth, distance from the touch, cancel ratio and timing, fills on each side, cancel symmetry, price move, repetitions), reads the trader's profile and alert history, checks market events in the window, and recalls prior analyst decisions from Memory.
3. Writes an investigation report in the vocabulary of the regulation's indicators, citing every piece of evidence it used, listing the legitimate explanations it considered and what ruled each one out.
4. Proposes one disposition: close as false positive, escalate to Level 2, or draft a STOR narrative. The analyst records the decision, on a separate API the agent cannot reach.

Every tool call goes through AgentCore Gateway, where Policy decides deterministically whether the call is allowed given what the agent has already done in the session.

## AgentCore capabilities exercised

| Capability | Role in this project |
|---|---|
| Runtime | Hosts the Strands agent as an HTTP agent, one session per alert, with the analyst's own JWT passed through; the `demo` endpoint is pinned to the released version |
| Gateway | Exposes the back end's Lambda as twelve MCP tools under target `surv`; inbound JWT; per-analyst rate limits |
| Identity | Cognito JWT inbound auth; L1 and L2 analyst groups; a separate API and a separate app client for recording decisions, so the token the agent holds cannot record one |
| Policy (Dogwood/Cedar) | Nine policies in `ENFORCE`, six of them over the session: the evidence must have answered for this alert before a proposal, the trader's history before a close, one proposal per alert, a STOR draft only after a proposal for one and only for Level 2, a cap on order-event pulls |
| Memory | Analyst decisions and feedback per trader, desk and instrument; the firm's written procedures |
| Code Interpreter | Designed for charts in the report; **not built** (the deterministic metrics stayed in Lambda; `docs/en/09-product-decisions.md` section 4) |
| Observability | Traces of every step plus the Gateway's policy decision logs: the record of why |
| Evaluations | Built-in ground-truth evaluators (Correctness, GoalSuccessRate, tool trajectory) and one custom rubric, over the labelled datasets; the project's own harness computes the gate (no real case proposed for closing), the share of false positives closed and the override rate |
| Optimization | A prompt recommendation from traces and configuration bundles, promoted only through the deterministic gate (the governed learning loop). The recommendation was rejected by that gate on an offline replay, so the A/B test through the Gateway was **not run** |
| A2A, Registry | Stretch; not built |

The twelve tools and the nine policies in plain words: `docs/en/13-tools-and-policies.md`.

## Repository layout

```
.kiro/steering/     Always-on project knowledge for Kiro (read these first)
.kiro/hooks/        Session brief, docs-sync, deploy cost guard
.claude/            The same standing instructions for Claude Code: CLAUDE.md and rules/ (identical copies of .kiro/steering/)
docs/en/            Scope, domain primer, problem statement, design, data and evaluation, build plan, operations, decisions, STATUS
docs/el/            Greek twins of the above
src/market_sim/     Limit-order-book simulator with scenario injection
src/detector/       The deliberately noisy spoofing/layering detector
src/tools/          Tool implementations (Lambda handlers and the pure discriminator functions)
app/surv_investigator_l1/  The agent: report model, system prompt, Strands agent + guard, Runtime entrypoint. This folder, whole, is the Runtime bundle
app/tests/          The agent's tests, beside its folder and not inside it
agentcore/          AgentCore CLI project: agentcore.json, deployed state, CDK stack with the Gateway rate limits
infra/              CDK app for the mock back end (Lambda, DynamoDB, S3, Cognito, HTTP API)
policies/           Nine policy files, one rule each: three plain Cedar, six over the session (.dw)
data/synthetic/     seed7, seed8 and seed9 with labels (committed, about 60 MB)
surv-tools.json     Gateway tool schema, generated from src/tools/schema.py
evals/              Evaluation harness, evaluators and bundles; every run's output under evals/runs/
scripts/            Dataset build and load, alert replay, Gateway smoke test, local and Runtime invocation, policy demo and validation, case reset, throttling report, dependency lock, tag audit
ui/                 Analyst UI (Streamlit, loopback) and its clients: Cognito login, human-path API, Runtime, CloudWatch spans
```

## Quick start (local, no AWS)

```
uv sync --all-groups
uv run pytest                                                  # 159 tests: order book, detector, scenarios, discriminators, tools on moto DynamoDB, policies, report and guard, Runtime bundle, metrics, faithfulness, throttling report, analyst screen
uv run scripts/build_dataset.py --seed 7 --sessions 20 --catalogue 1 --out /tmp/seed7   # ~20 s; rebuilds seed7 from its seed, beside the committed copy
uv run scripts/replay_alert.py data/synthetic/seed7 --random 3 --reveal                 # read three alerts' tapes by hand, with their labels
```

The rebuild gives the committed rows in every table (checked 2026-11-25). The files are not byte-identical: the Parquet writer's version and the manifest's timings differ, and `labels/discriminators` carries two columns the discriminator tool has gained since the set was frozen. Without `--out` the command writes over `data/synthetic/seed7`.

## Against the deployed stack

These need AWS credentials for the project's account and the local credentials file.

```
uv run scripts/smoke_gateway.py -v                             # read-only: the 11 tools a Level-1 analyst sees, through the Gateway
uv run scripts/policy_demo.py                                  # the Gateway refusing shortcuts, by policy name; no model call
uv run scripts/investigate.py A-261006-0006 --reveal           # the agent run locally against the Gateway (about $0.10; writes a proposal on the alert)
uv run scripts/invoke_runtime.py A-261006-0006                 # the deployed Runtime with the analyst's token (about $0.10; writes a proposal on the alert)
uv run --group ui streamlit run ui/analyst_app.py              # the analyst screen on http://127.0.0.1:8501
```

Analyst passwords are not in the repo (`~/.config/surv-investigator/analyst-credentials.env`). Resuming on a fresh machine or session, and how the two stacks are deployed: `docs/en/07-resume.md`.

The deployed stack is the author's. Its identifiers (account id, resource ids, the API's address) are in this repository; they are not credentials. Every endpoint needs a token from the project's Cognito user pool, and the pool does not allow self sign-up. Deploying into another account has not been tried: the policy files and the AgentCore project's state name this deployment's Gateway.

## Working on this project with Kiro

Open this folder as the workspace root so the steering files and hooks load. The SessionStart hook prints `docs/en/STATUS.md` and recent changes. A PostToolUse hook fires after every file write and tells Kiro which documents to update, in both `docs/en` and `docs/el`, for the code or doc that changed (tool contracts, policy set, scenario catalogue, STATUS, decision log, or the language twin). A Stop hook checks at the end of each turn that sources are not newer than the docs and that every English document has a Greek twin with matching structure, and asks for a fix if not. The PreToolUse hook asks for confirmation before commands that create billable AWS resources. Kiro is instructed (`.kiro/steering/challenge-and-verify.md`) not to agree by default and to verify claims from primary sources.

## Working on this project with Claude Code

The same standing instructions load from `.claude/rules/` (five files, byte-identical to `.kiro/steering/`), and `.claude/CLAUDE.md` says how to read them there: the Kiro hooks do not run under Claude Code, so the session brief, the docs update, the docs-sync check and the confirmation before a billable AWS command are done by hand. `python3 .kiro/hooks/scripts/docs-sync-check.py` checks three things: sources not newer than the docs, English and Greek twins with the same structure, and the two copies of the instructions identical. Change a rule on one side and copy it to the other.

## Documents

- `docs/en/00-scope.md` what is in, what is out, what was planned and not built, why surveillance and not sanctions
- `docs/en/01-domain-primer.md` market abuse, spoofing and layering, how surveillance works, regulation, vendors
- `docs/en/02-problem-statement.md` the business problem, the buyer, why an agent, the metric
- `docs/en/03-solution-design.md` architecture, AgentCore mapping, tool contracts, policies, memory, demo script, anticipated questions
- `docs/en/04-synthetic-data-and-evaluation.md` simulator, scenario catalogue, labels, detector, evaluation harness, every run's result
- `docs/en/05-build-plan.md` phases with milestones and cost notes
- `docs/en/06-learning-resources.md` reading path
- `docs/en/07-resume.md` how to resume work in a new session or on a new machine
- `docs/en/08-broker-brief.md` the logic for a broker's surveillance team: what the agent does, the standard it applies, what it cannot do, the audit record, the numbers
- `docs/en/09-product-decisions.md` every product decision with its reason, where AgentCore does the work, cost to run, proof points, limitations, roadmap
- `docs/en/10-operations.md` how the product is run after the alpha: release cycle, what to watch, measured time and token breakdown, ranked backlog
- `docs/en/11-market-landscape.md` who else puts AI on surveillance alerts (Robinhood, Nasdaq, NICE, Eventus, eflow, SteelEye, Solidus, FIS, AWS samples), whether there is a direct competitor, who the customer is, the prospect checklist, what to borrow
- `docs/en/12-presenter-guide.md` for the speaker: the story in plain words, the seven domain ideas needed to tell it, what to say at each demo step, the numbers to know, hard questions with honest answers, what not to claim
- `docs/en/13-tools-and-policies.md` one page in plain words: the twelve Gateway tools, the nine AgentCore policies, and the controls that are not policies
- `docs/en/glossary.md`, `docs/en/decision-log.md` (every decision with its alternatives, and every claim that was later corrected), `docs/en/STATUS.md`

## Releases

Six tags, each with what was built and measured at that point: `v0.1.0-alpha` (2026-11-07) to `v0.4.1-alpha` (2026-11-19). The last three carry release notes on GitHub.
