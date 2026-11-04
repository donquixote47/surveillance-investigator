# STATUS

| Item | Value |
|---|---|
| Phase | 4 complete (2026-11-05): Policy Engine enforced, Memory with recall through the Gateway, demo steps 5-7 reproducible. Next: Phase 5 (evaluation harness over the 167 alerts, Evaluations, Optimization). Phase 3 complete (2026-11-03): agent on Runtime, analyst UI (Streamlit), demo alerts A/B/C run and recorded. Next: Phase 4 (policies, Memory, Code Interpreter). Phase 2 deployed 2026-11-03: SurvFirm stack, seed7 in DynamoDB, Gateway `surv-investigator` with Lambda target `surv`, smoke test through MCP with an L1 token passed, per-analyst rate limits active and probed. **Phase 2 complete.** (Phase 1 completed 2026-11-02; see `05-build-plan.md`) |
| Repository | `https://github.com/donquixote47/surveillance-investigator` (private), branch `main`; local clone `shared/tam-work/projects/agentcore-surveillance-investigator` |
| Region | eu-west-2 |
| Stack | Python 3.14.2 (uv 0.13.7), Strands Agents 1.63.0, strands-agents-tools 0.8.12, bedrock-agentcore 1.25.3, boto3 1.43.123, pandas 3.1.0, pyarrow 26.0.1, AgentCore CLI 1.0.1 (`@aws/agentcore`), `@aws/agentcore-cdk` 1.0.1, AWS CDK CLI 2.1147.0 with aws-cdk-lib 2.275.0 (Python stack and the CLI's TypeScript stack, TypeScript 7.0.2); moto 5.2.5; Streamlit 1.66.1. All at registry latest on 2026-11-03; floors in `pyproject.toml` pinned to these tested versions |
| Models | `eu.anthropic.claude-haiku-5-5` (dev), `eu.anthropic.claude-sonnet-5-5` (default agent), `eu.anthropic.claude-opus-5-5` (Phase 5 comparison arm and rationale judge); Haiku and Sonnet access confirmed from eu-west-2 2026-11-02 |
| Deployed AWS resources | See the table below (two CloudFormation stacks, 1 Gateway, all tagged; `scripts/check_tags.py` clean) |
| Dataset | `data/synthetic/seed7` (20 sessions 2026-10-05..30): 167 alerts, 28 TRUE_ABUSE (17%), 52 background, 1.82 M order events, recall on injected abuse 100%, 0 missed injections; `report.md` and `manifest.json` inside |
| Last evaluation run | Agent, hand-picked alerts (not the evaluation set): after Memory and the clarified closure standard, demo B CLOSE_FP, E (F-NEWS-1) CLOSE_FP citing the analyst's correction, five true-abuse alerts all ESCALATE (one S-SPOOF-2 expected DRAFT_STOR, safe). Before: 6 of 8 matched, both misses F-NEWS-1 escalated. Haiku 5.5 escalated the market maker Sonnet closed. Threshold baseline: raw safe close 96%, gate failed (6 of 7 S-SPOOF-5 alerts proposed CLOSE_FP via R5), reported n/a |
| Cost to date | About $8: $3.2 Phase 2 plus about 12 investigations (Sonnet about 35k input / 3k output tokens each ≈ $0.10; Haiku runs cents) and Runtime seconds.  DynamoDB writes for seed7 (≈4.2 M WRU incl. GSI and the duplicate partial load) plus a few dozen Lambda, Cognito and Gateway calls; model calls still under $0.01 |

## Next step

Phase 5: `evals/run_dataset.py` over all 167 alerts with the gate and safe close rate (data doc §4), ground-truth files from `labels`, Evaluations (built-in Correctness/GoalSuccess/Trajectory on the Runtime sessions and a custom rationale rubric), then Optimization recommendations and an A/B through the Gateway, promoted only through the gate.

## Deployed resources

| Resource | Name / ARN | Created | Cost note |
|---|---|---|---|
| SurvFirm CloudFormation stack | `arn:aws:cloudformation:eu-west-2:384308066035:stack/SurvFirm/bf9300e0-d76f-11f1-a926-0afff58e77e5` (44 resources) | 2026-11-03 | idle $0; `cdk destroy` removes everything (RemovalPolicy DESTROY) |
| DynamoDB tables | `surv-order-events` (GSI `by_date`), `surv-trades`, `surv-traders`, `surv-market-events`, `surv-instrument-stats`, `surv-alerts` (GSI `by_date`), `surv-cases-history`, `surv-cases` (GSI `by_trader`) | 2026-11-03 | on-demand; seed7 loaded: 1,961,720 items (about 213k duplicate writes from an interrupted first run) ≈ $3.1 once; storage inside free 25 GB |
| S3 bucket | `surv-firm-data-384308066035-eu-west-2` | 2026-11-03 | empty; $0 |
| Lambda | `surv-gateway-tools` (python3.14 arm64, 1024 MB, layer `surv-pandas-py314-arm64`), `surv-human-path` (512 MB) | 2026-11-03 | free tier |
| Cognito | pool `surv-analysts` (`eu-west-2_IHKd57XzK`), client `surv-analyst-ui` (`5e6f4bsbkg0u7gqbep0118olnq`), users `l1.analyst` (L1), `l2.reviewer` (L2); passwords in `~/.config/surv-investigator/analyst-credentials.env` (not in the repo) | 2026-11-03 | Essentials, 2 MAU, $0 |
| HTTP API | `surv-analyst-api` `https://5tk8hm8w4m.execute-api.eu-west-2.amazonaws.com` (JWT authoriser on all routes; 401 without token, verified) | 2026-11-03 | free tier |
| CDKToolkit bootstrap stack | `CDKToolkit` in eu-west-2 (assets bucket `cdk-hnb659fds-assets-384308066035-eu-west-2`) | 2026-11-03 | $0 idle |
| AgentCore Gateway | `surv-default-surv-investigator` (`surv-default-surv-investigator-gsq1ismkrw`), URL `https://surv-default-surv-investigator-gsq1ismkrw.gateway.bedrock-agentcore.eu-west-2.amazonaws.com`, CUSTOM_JWT from the pool, exceptionLevel DEBUG, in stack `AgentCore-surv-default` | 2026-11-03 | $5 per million InvokeTool calls (pricing page, 2026-11-03) |
| Gateway target | `surv` (`B191VDQHAI`), Lambda `surv-gateway-tools`, 11 tools from `surv-tools.json`; Gateway role may invoke only this function | 2026-11-03 | included above |
| AgentCore Memory | `surv_default_investigator_memory-38ATWRDsvk`, SEMANTIC strategy `analyst_knowledge` (`/traders/{actorId}/notes/`), 90-day event expiry; namespaces `/traders/*/notes/`, `/desks/*/notes/`, `/instruments/*/notes/`, `/procedures/`; written by `surv-human-path` and `scripts/memory_admin.py`, read by `surv-gateway-tools` (`recall_memory`) | 2026-11-05 | per record stored and per retrieve request (pricing page); about 45 records |
| Policy Engine | `surv_default_investigator_pe` (`surv_default_investigator_pe-rmckq8ojd0`), attached to the Gateway in `ENFORCE`, nine policies ACTIVE (p01-p08 incl. p03a/p03b), in stack `AgentCore-surv-default` | 2026-11-04 | $0.000025 per authorization request |
| Gateway logs and traces | delivery sources `<gateway id>-logs` -> log group `/aws/vendedlogs/bedrock-agentcore/surv-default-surv-investigator-gsq1ismkrw` (30-day retention), `<gateway id>-traces` -> X-Ray | 2026-11-04 | CloudWatch Logs ingestion, cents |
| Gateway rate limits | `per-analyst-requests` (60/min per `$.context.jwt.sub`), `per-analyst-writes` (3/min per analyst on `propose_disposition` and `draft_stor_narrative`), both ACTIVE, in stack `AgentCore-surv-default` | 2026-11-03 | free |
| AgentCore Runtime | `surv_default_surv_investigator_l1` (`arn:aws:bedrock-agentcore:eu-west-2:384308066035:runtime/surv_default_surv_investigator_l1-lrnjCN5vBp`), v8 (v1 2026-11-03; v2 dependency upgrade; v6 2026-11-04 policy session header; v8 2026-11-05 recall_memory in the prompt), PYTHON_3_14 direct code deploy, HTTP, CUSTOM_JWT (analyst pool), `Authorization` allowlisted, env `SURV_GATEWAY_URL`, `SURV_MODEL_ID`; log group `/aws/bedrock-agentcore/runtimes/surv_default_surv_investigator_l1-lrnjCN5vBp-DEFAULT` | 2026-11-03 | billed per active session second; sessions end when the invocation returns (no idle UI session kept open) |
| Gateway workload identity | `surv-default-surv-investigator-gsq1ismkrw` (auto-created; tagged by hand, the stack did not tag it) | 2026-11-03 | $0 through Gateway |

## Open verification items (from the docs)

- Exact article numbers in Delegated Regulation (EU) 2016/957 for human analysis and record-keeping (five years).
- US references (FINRA 3110, Exchange Act 9(a)(2)/10(b), CEA 4c(a)(5)(C), Coscia/Sarao/JPMorgan cases).
- Current vendor feature sets (agentic investigation features) before the presentation.
- AgentCore Gateway, Policy and Optimization pricing.
- Live behaviour of temporal policies and of Lambda-target output schemas (Phase 4).
