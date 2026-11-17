# 13 - Gateway tools and AgentCore policies at a glance

One page, in plain words: every tool the agent can call, and every rule the platform enforces on those calls. Written 2026-11-17 from the deployed files, `surv-tools.json` and `policies/`. The full contracts are in `03-solution-design.md`, section 4 (tool contracts) and section 6 (policy set). When a tool or a policy changes, both documents change.

## 1. Gateway tools (12)

All twelve sit behind one Gateway target, `surv`, so the agent sees them as `surv___<name>` (three underscores). Ten only read. Two write, and neither of them records a decision.

| # | Tool | Kind | What it does |
|---|---|---|---|
| 1 | `get_alert` | read | Returns the alert the detector raised: trader, instrument, trigger, time window. The start of every investigation. |
| 2 | `get_procedures` | read | Returns the firm's written rules: its definition of spoofing and layering, when an alert may be closed, when it must be escalated. |
| 3 | `recall_memory` | read | Returns what analysts recorded before about this trader, the desk and the instrument, from AgentCore Memory. The decision recorded on the alert under investigation is left out. |
| 4 | `get_order_events` | read | Returns the trader's raw orders in the window: placed, changed, cancelled, executed. |
| 5 | `reconstruct_book` | read | Shows what the market looked like at a moment: the best prices and the resting depth, with the trader's orders apart from everyone else's. |
| 6 | `compute_discriminators` | read | Computes the numbers that tell a trick from a job: size against the market, distance from the best price, cancel timing, price move. Each large order is also measured on its own (`large_orders`). |
| 7 | `get_trader_profile` | read | Returns who the trader is: role, desk, market-making registrations, typical order size, risk-system events in the window. |
| 8 | `get_trader_alert_history` | read | Returns the trader's earlier alerts and how analysts decided them. Prior alerts only. |
| 9 | `get_market_events` | read | Returns public events around the window: news, scheduled data releases, halts, auctions. |
| 10 | `get_instrument_stats` | read | Returns what "large" and "far" mean for this share on this day: average volume, spread and depth. |
| 11 | `propose_disposition` | write | Stores the agent's proposal and its report on the case. Closes nothing. Refused on an alert a person has already decided. |
| 12 | `draft_stor_narrative` | write | Drafts the text of a Suspicious Transaction and Order Report from a recorded proposal, for Level 2 to edit, sign or discard. Nothing is sent. |

There is no tool that records a decision. Recording is a separate API that takes a person's login. A Level-1 login sees eleven of the twelve tools, because policy 07 hides `draft_stor_narrative` from it; a Level-2 login sees all twelve.

## 2. AgentCore policies (9)

One policy engine, attached to the Gateway in enforce mode. A call is allowed only if a permit applies and no forbid overrides it: what is not permitted is denied, and a forbid always wins. A refusal names the policy that refused.

Two kinds. A plain policy looks at who is calling and which tool. A policy over the session also looks back at what was already called in the same investigation.

| Policy | File | Kind | What it enforces |
|---|---|---|---|
| 01 | `01-permit-read-tools.cedar` | plain | Any logged-in analyst may call the ten read tools. |
| 02 | `02-forbid-unknown-tools.cedar` | plain | Any tool outside the twelve is forbidden for everyone. A tool that records a decision would be denied even if someone added it. |
| 03a | `03a-evidence-before-proposal.dw` | over the session | A proposal is allowed only after the alert was read, its orders pulled and its numbers computed, all for that same alert. |
| 03b | `03b-profile-and-market-before-proposal.dw` | over the session | A proposal is refused until the trader's profile and the market events were looked up. |
| 04 | `04-history-before-close.dw` | over the session | A proposal to close is refused until the trader's alert history was looked up. |
| 05 | `05-stor-after-proposal.dw` | over the session | A report may be drafted only after a proposal to draft one, for the same alert. |
| 06 | `06-one-proposal-per-alert.dw` | over the session | A second proposal for the same alert in the same session is refused. |
| 07 | `07-stor-drafting-requires-l2.cedar` | plain | Only Level 2 may draft a report. |
| 08 | `08-cap-event-pulls.dw` | over the session | At most six pulls of order events in a session, to bound cost and loops. |

Policies 03a, 03b and 04 are the platform's form of "look before you propose". Policies 06 and 08 count within one session, and the caller names the session, so a new session starts the count again: they shape behaviour and are not a security boundary on their own.

## 3. Controls that are not on these lists

The policies are one layer. Four others matter when someone asks what stops the agent.

- **The Gateway's rate limits.** 60 requests a minute per analyst, and 3 writes a minute per analyst on the two write tools (`STATUS.md`, deployed resources).
- **The tools Lambda's access rights.** The function behind the tools may update only the proposal fields of a case. It cannot write a decision, and it cannot replace or delete a case (`08-broker-brief.md`, section 2b).
- **The recording API.** A decision is recorded once, by a person; only Level 2 can supersede it, and the earlier decision stays on the case.
- **The agent's own guard.** It holds a proposal back until the evidence tools returned a result for this alert. This matters because a tool call that returns an error still counts as a completed call for policies 03a, 03b and 04 (`10-operations.md`, section 5).
