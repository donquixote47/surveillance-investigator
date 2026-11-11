# 07 - Resuming work on this project

How to pick this project up in a fresh Kiro session, on this machine or another one, without losing anything. The live state is in `STATUS.md` (deployed resources, cost, next step) and `decision-log.md` (why things are the way they are); this page is the procedure.

## 1. What a new session must read first

Clone `https://github.com/donquixote47/surveillance-investigator` (private; `gh auth login` as donquixote47 first) and open the repository root as the Kiro workspace. Then, in this order:

1. `.kiro/steering/project-context.md` - the goal, scope, rules (region eu-west-2, synthetic data only, tags on every resource, bilingual docs, announce cost before deploys).
2. `.kiro/steering/challenge-and-verify.md` - Kiro does not agree by default; claims are checked against primary sources.
3. `docs/en/STATUS.md` - current phase, what is deployed (names and ARNs), cost to date, the next step.
4. `docs/en/05-build-plan.md` - the phase checklist; the first unchecked box is the work.
5. `docs/en/decision-log.md` - the last five entries at least.
6. `.kiro/steering/agentcore-gotchas.md` - verified behaviours and traps of AgentCore, Strands, the CLI and Claude 5.5 on Bedrock, each with the date it was verified.
7. For the mentor conversation: `docs/en/09-product-decisions.md` (the product and where AgentCore does the work) and `docs/en/08-broker-brief.md` (the logic as a surveillance team reads it).
8. Before changing anything: `docs/en/10-operations.md` (release cycle, promotion rule in practice, what to watch, the ranked backlog with measured gains).

The SessionStart hook (`.kiro/hooks/session-brief.json`) prints STATUS, the last decisions and recently changed files automatically.

## 2. Machine prerequisites

| Tool | Version used | Install |
|---|---|---|
| Python | 3.14.2 (pinned in `.python-version`) | python.org or `uv python install 3.14` |
| uv | 0.13.x | `curl -LsSf https://astral.sh/uv/install.sh \| sh` (upgrade: `uv self update`) |
| Node | 26.x (CDK warns, works) | nodejs.org |
| AWS CLI | 2.39+ | aws.amazon.com/cli |
| AWS CDK CLI | 2.1147+ (older refuses aws-cdk-lib 2.275's schema) | `npm install -g aws-cdk` |
| AgentCore CLI | 1.0.1 | `npm install -g @aws/agentcore` |
| TypeScript (in `agentcore/cdk`) | 7.0.x, installed by `npm install` there | the CLI runs the build itself |
| AWS credentials | account 384308066035, IAM user `ai-admin` or equivalent | `aws configure` |

Then:

```
uv sync --all-groups          # runtime, infra (aws-cdk-lib) and dev (pytest, ruff, moto) groups
uv run pytest                 # 38 tests, no AWS needed
uv run ruff check .
export JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=1
```

## 3. Secrets that are not in the repository

| Secret | Where | How to recreate |
|---|---|---|
| Analyst passwords (`l1.analyst`, `l2.reviewer`) and the pool/client ids | `~/.config/surv-investigator/analyst-credentials.env` (mode 600) | `aws cognito-idp admin-set-user-password --region eu-west-2 --user-pool-id eu-west-2_IHKd57XzK --username l1.analyst --password '<new>' --permanent` (same for `l2.reviewer`), then write the file with keys `SURV_USER_POOL_ID`, `SURV_CLIENT_ID`, `SURV_L1_USER`, `SURV_L1_PASSWORD`, `SURV_L2_USER`, `SURV_L2_PASSWORD`, `SURV_API_URL` |
| AWS credentials | `~/.aws/` | your own |

Nothing else is secret. Account id, pool id, client id, ARNs and URLs are identifiers and appear in `STATUS.md`.

## 4. What is deployed and how to touch it

See the table in `STATUS.md`. Two CloudFormation stacks in eu-west-2:

- `SurvFirm` (CDK Python, `infra/`): DynamoDB tables, S3 bucket, `surv-gateway-tools` and `surv-human-path` Lambdas, Cognito pool `surv-analysts`, HTTP API `surv-analyst-api`. Change: edit `infra/surv_firm/stack.py`, then `cd infra && cdk diff && cdk deploy`. The Lambda layer must exist first: `./infra/build_layer.sh` (not committed, 80 MB).
- `AgentCore-surv-default` (AgentCore CLI, `agentcore/agentcore.json` + `agentcore/cdk/`): Gateway `surv-investigator` with Lambda target `surv`, rate limits, Runtime `surv_investigator_l1`. Change: edit `agentcore/agentcore.json` or `app/surv_investigator_l1/`, then `agentcore deploy --region eu-west-2`. After any change to `src/tools/schema.py`, re-export the Gateway tool schema: `uv run python -c "import sys; sys.path.insert(0,'src'); from tools.schema import export; export('surv-tools.json')"` and deploy.

Every resource must carry `Project=agentcore-surveillance-investigator` and `auto-delete=no`. Audit: `uv run scripts/check_tags.py` (add `--fix` to tag what is missing). Resources the stacks do not tag (so far: the Gateway's workload identity) are caught by this script.

The data is already in DynamoDB (seed7, 1,961,720 items). To reload after a table rebuild: `uv run scripts/load_dynamodb.py data/synthetic/seed7` (about 12 minutes, about $3). To regenerate the dataset itself: `uv run scripts/build_dataset.py --seed 7 --sessions 20` (deterministic; the committed parquet files are the reference).

## 5. Everyday commands

```
uv run scripts/smoke_gateway.py -v                         # Gateway through MCP as l1.analyst
uv run scripts/investigate.py A-261006-0006 --reveal       # agent locally (model from here, tools via the Gateway)
uv run scripts/investigate.py A-261005-0002 --model eu.anthropic.claude-haiku-5-5 --reveal
uv run scripts/invoke_runtime.py A-261006-0006             # the deployed Runtime, as the UI will call it
uv run scripts/invoke_runtime.py A-261005-0002 --user L2 --mode stor_drafting
uv run scripts/replay_alert.py data/synthetic/seed7 --scenario S-SPOOF-5 --reveal   # read a tape by hand
uv run scripts/check_tags.py                               # tag audit
uv run scripts/policy_demo.py                              # demo steps 5-6: the Gateway denying shortcuts, by policy name
uv run scripts/validate_policies.py                        # the engine's findings for every file in policies/
uv run scripts/memory_admin.py list /desks/PROP-EQ/notes/   # Memory records; also ingest-procedures, seed-history, delete
uv run --group ui streamlit run ui/analyst_app.py          # analyst UI on http://127.0.0.1:8501 (loopback only)
python3 .kiro/hooks/scripts/docs-sync-check.py             # docs parity (empty output = clean)
```
Phase 5 (evaluation), in the order a run goes through; all run outputs under `evals/runs/<run_id>/` are committed:
```
uv run evals/run_dataset.py --sample 6 --tag pilot                     # six alerts through the Runtime as l1.analyst (~$1.2)
uv run evals/run_dataset.py --tag sonnet-vN --notes "..."              # all 167 alerts, ~57 min, ~$15 in Sonnet tokens with prompt caching (v14+; $31 before)
uv run evals/run_dataset.py --scenario F-ICE-1 S-SPOOF-5 --tag slice   # a slice; --no-memory hides recall_memory; --bundle <name> sends a config bundle
SURV_PROMPT_CACHE=off uv run evals/run_dataset.py --backend local ...   # the no-caching arm (local backend only; the Runtime reads its own env)
uv run evals/compare_runs.py evals/runs/<A> evals/runs/<B> --out ...   # paired comparison of two runs on their shared alerts
uv run evals/run_dataset.py --repeat 5 --alerts ... --tag variance    # run-to-run variance: per-alert stability, pseudo-run spread (~$8 for 21 x 5)
uv run scripts/span_turns.py --run evals/runs/<run_id> --alerts A-...  # per-turn timing of a session from its spans: model turns, tokens, tools
uv run evals/run_dataset.py --resume evals/runs/<run_id> --retry-errors # finish a cut run, re-run errored alerts
uv run evals/run_dataset.py --rescore evals/runs/<run_id>              # recompute results.md from the saved responses (free)
uv run evals/faithfulness.py evals/runs/<run_id>                       # numbers in evidence vs tool-result spans (free)
uv run evals/evaluate_sessions.py evals/runs/<run_id>                  # Correctness, GoalSuccessRate, Trajectory, rubric (~$25 for 167)
uv run evals/ingest_overrides.py --dry-run                             # analyst overrides in surv-cases -> labels/overrides.parquet
uv run evals/evaluators.py list|create|update rationale_rubric         # the custom judge (evals/evaluators/*.json)
uv run evals/recommend.py start evals/runs/<run_id>; ... get <id>      # Optimization recommendation against the rubric; read the .diff
uv run evals/bundles.py create <name> [--prompt-file f] [--model m]    # configuration bundle; evals/bundles.json is the local registry
uv run python -m detector.tune --out evals/runs/tune-seed7.md          # detector threshold grid (local, ~2.5 min)
```

Useful alert ids: `A-261006-0006` (S-SPOOF-1, true spoof), `A-261005-0002` (background market maker, false positive), `A-261006-0015` (S-SPOOF-5, the hard spoof the threshold baseline misses), `A-261015-0008` (F-NEWS-1, news-storm cancel). Labels: `data/synthetic/seed7/labels/labels.parquet` (never loaded anywhere the agent can reach).

## 6. Where things are

```
.kiro/steering/          Kiro's standing knowledge of the project (read first)
.kiro/hooks/             SessionStart brief, docs-sync nudge + Stop parity check, deploy guard
docs/en/, docs/el/       The documentation, English canonical, Greek twin, same structure
src/market_sim/          Limit-order-book simulator and scenario injection
src/detector/            The noisy spoofing/layering detector and labelling
src/tools/               Tool schema (Gateway), discriminators, DynamoDB access, Lambda handlers
infra/                   CDK Python stack for the firm's back end
agentcore/               AgentCore CLI project: agentcore.json, deployed state, TS CDK stack (rate limits live here)
app/surv_investigator_l1 The agent: report model, prompt, Strands agent + guard, Runtime entrypoint, tests
scripts/                 build_dataset, replay_alert, load_dynamodb, smoke_gateway, investigate, invoke_runtime, check_tags
ui/                      Analyst UI (Streamlit) and its Streamlit-free clients for Cognito, the human-path API, the Runtime, CloudWatch spans
data/synthetic/seed7     The dataset (committed) with labels
surv-tools.json          Gateway tool schema, generated from src/tools/schema.py
policies/, evals/        Phase 4 and 5 (empty so far)
```

## 7. Rules of engagement

- Docs change in the same turn as the code, English and Greek together; the Stop hook refuses to end a turn otherwise.
- Before any deploy or resource creation: say what it costs; the PreToolUse hook asks for confirmation.
- Stop Runtime and Code Interpreter sessions after runs (Runtime sessions here end with the invocation).
- Record every non-obvious decision in `decision-log.md` with alternatives and reason.
- Verify before asserting; write the verification date next to AgentCore facts in `agentcore-gotchas.md`.

## 8. Tearing down (end of project)

`cd infra && cdk destroy` removes the firm stack (tables, bucket with objects, Lambdas, pool, API). `agentcore destroy` (or deleting stack `AgentCore-surv-default`) removes the Gateway, rate limits and Runtime. Then delete the CloudWatch log groups under `/aws/bedrock-agentcore/runtimes/` and `/aws/lambda/surv-*`, and the `CDKToolkit` stack if nothing else uses it. Check with `scripts/check_tags.py` that nothing tagged with the project remains.
