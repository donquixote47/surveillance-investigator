# Glossary

## Markets and order books

| Term | Meaning |
|---|---|
| Limit order book (LOB) | The venue's list of resting buy (bid) and sell (ask) limit orders, grouped by price level. |
| Touch / best bid and offer (BBO) | The highest bid and lowest ask. |
| Spread | Best ask minus best bid. |
| Depth | Total resting size at a price level or across the top N levels of a side. |
| Tick | Minimum price increment. |
| Resting (passive) order | A limit order sitting in the book waiting to be hit. |
| Aggressive (marketable) order | An order that crosses the spread and executes immediately against resting orders. |
| Fill / partial fill | Execution of all / part of an order. |
| Cancel / modify | Removing / changing a resting order. |
| Order-to-trade ratio (OTR) | Orders (new + modify + cancel events) divided by trades, for a trader over a period. High OTR is normal for market makers and algos, suspicious for others. |
| Cancel ratio | Cancelled size divided by submitted size. |
| Cancel latency | Time from order placement (or from an opposite-side fill) to its cancellation. |
| Market maker | A participant who quotes both sides continuously, often with a venue registration and obligations; constant cancel/replace is their normal behaviour. |
| Pegged order | An order whose price follows a reference (mid, best bid); re-priced automatically, which produces cancel/replace events. |
| Parent / child order | An algorithm's large order (parent) sliced into smaller orders (children) over time, e.g. VWAP, TWAP. |
| Iceberg / reserve order | An order showing only part of its size; the visible tip is replenished as it fills. |
| Drop copy | A real-time copy of a firm's order and execution messages from the venue, used for surveillance and risk. |
| OMS / EMS | Order / execution management systems inside the firm. |
| ADV | Average daily volume. |

## Market abuse

| Term | Meaning |
|---|---|
| Market abuse | Insider dealing, unlawful disclosure and market manipulation (EU MAR). |
| Market manipulation | Giving false or misleading signals about supply, demand or price; securing an artificial price; deception (MAR Art. 12). |
| Spoofing | Placing orders intended to be cancelled to create a false impression of interest, profiting from the opposite side. |
| Layering | Spoofing with multiple orders at successive price levels on one side. |
| Wash trade | Trading with oneself or a collaborator to create false volume. |
| Marking the close | Trading to influence the closing price. |
| Momentum ignition | Trading to start a price move that others follow, then reversing. |
| Quote stuffing | Flooding the book to slow others down. |
| Front running | Trading ahead of a known client order. |
| Insider dealing | Trading on material non-public information. |
| Indicators of manipulative behaviour | The non-exhaustive list in Delegated Regulation (EU) 2016/522 Annex II that surveillance scenarios and STORs reference. |

## Regulation and compliance

| Term | Meaning |
|---|---|
| MAR | Market Abuse Regulation, Regulation (EU) 596/2014. UK MAR is the retained UK version. |
| MiFID II / MiFIR | Directive 2014/65/EU and Regulation (EU) 600/2014 on markets in financial instruments. Art. 17 MiFID II covers algorithmic trading. |
| RTS | Regulatory Technical Standards: delegated regulations that fill in the detail of a directive or regulation. RTS 6 = Delegated Regulation (EU) 2017/589. |
| PPAET | Person professionally arranging or executing transactions: the MAR Art. 16(2) term covering brokers and investment firms. |
| NCA | National competent authority: the national regulator (CySEC, HCMC, FCA, BaFin, AMF, CBI...). |
| ESMA | European Securities and Markets Authority. |
| STOR | Suspicious Transaction and Order Report, filed to the NCA under MAR Art. 16 using the template in 2016/957. |
| Surveillance scenario | A detector rule for one abuse pattern (spoofing, layering, wash trade...). |
| Alert | One hit of a scenario on one trader/instrument/window, queued for review. |
| Disposition | The decision on an alert: close as false positive, escalate, report. |
| Level 1 / Level 2 (L1 / L2) | First-line triage analyst / senior investigator or compliance officer. |
| Four-eyes | A decision requiring two different people. |
| False positive (FP) | An alert on legitimate activity. |
| True positive (TP) | An alert on actual abuse. |
| Recall | Share of actual abuse that is detected (or, in our metric, not closed). |
| Precision | Share of alerts (or of a disposition class) that are actual abuse. |
| Safe close rate | Our primary metric: share of false-positive alerts the agent proposes to close, reported only when recall on true abuse is 100%. |
| Model risk management (MRM) | The governance function that validates models and, increasingly, AI tools before use in a control. |
| FINRA | US self-regulatory organisation for broker-dealers. Rule 3110 is the supervision rule. |
| CFTC | US futures regulator; spoofing in futures is explicitly unlawful under the Commodity Exchange Act. |

## AgentCore and agents

| Term | Meaning |
|---|---|
| Runtime | Managed, isolated (microVM) hosting for agents; sessions, versions, endpoints. |
| Gateway | Exposes Lambdas, APIs and MCP servers as MCP tools to agents; enforces inbound auth; attaches Policy. |
| Target | A set of tools behind a Gateway; tools are named `target___tool`. |
| MCP | Model Context Protocol, the tool-calling protocol agents and Gateway speak. |
| A2A | Agent-to-agent protocol, for one agent calling another. |
| Identity | Workload identities for agents, inbound/outbound auth, credential providers (Cognito, OAuth2, API keys). |
| Policy / Policy Engine | Deterministic rules (Dogwood, Cedar-compatible) evaluated on every Gateway tool call; deny by default; LOG_ONLY or ACTIVE. |
| Temporal policy | A policy whose decision depends on earlier events in the same session (prerequisites, caps, cool-downs). |
| Cedar / Dogwood | Cedar is AWS's open-source authorization language; Dogwood extends it with temporal conditions. |
| Memory | Short-term (events) and long-term (extracted records) memory with strategies (semantic, summary, episodic, user preference, custom) and namespaces. |
| Code Interpreter | Sandboxed code execution sessions for agents. |
| Observability | OpenTelemetry traces and metrics in CloudWatch, with policy decision logs. |
| Evaluations | Scoring of sessions, traces and spans with built-in or custom evaluators, with optional ground truth. |
| Optimization | Recommendations and A/B testing of prompts and tool descriptions, built on Evaluations. |
| Strands Agents | AWS's open-source Python agent framework used here. |
| Trajectory | The sequence of tool calls an agent made in a session. |
| Ground truth | The known correct answer for an evaluation case. |
| Evidence faithfulness | Our check that every fact in the report comes from a tool output. |
