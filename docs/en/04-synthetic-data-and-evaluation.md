# 04 - Synthetic data, detector and evaluation

## 1. Why synthetic, and what it costs us

We have no legal or ethical way to use real order data from George's customers, and public tick data with trader identifiers does not exist. A simulator gives us three things real data would not: ground truth (we know which alerts are abuse because we injected it), controllable scenario mix, and freedom to publish. It costs us realism: a mentor or a customer will rightly say "your market is not a real market". The honest answer is that the agent's job is to reason about evidence, and the evidence types (order lifecycle, trader role, events) are the same; realism of price dynamics matters less than realism of the *patterns* the detector catches. ABIDES is the stretch path to more realistic background flow.

## 2. Simulator design (`src/market_sim/`)

A small discrete-event limit-order-book simulator in Python. Deliberately simple; the point is scenario injection, not market microstructure research.

### 2.1 Background market

- One instrument per run (`SYN.A`), tick size 0.01, opening price 100.00, session 09:00-17:30 simulated time, nanosecond timestamps. One session day takes about 0.6 s to simulate and produces about 90,000 order events.
- Fundamental price: Ornstein-Uhlenbeck random walk in ticks, stepped once per second, with a 3-8 tick jump at `MACRO_PRINT` or `NEWS` events.
- Order book (`src/market_sim/book.py`): price-time priority, limit, market, pegged and iceberg orders, modify with and without loss of priority, self-trade prevention (an incoming order that would trade against the same trader's resting order is cancelled for its remainder), and an event tape that records the best bid and ask *immediately before* every event. That BBO is what lets the tools compute "distance from the touch at placement" without replaying the book.
- Participant population (`src/market_sim/agents.py`), none of whom manipulate:
  - `T-MM-01`, `T-MM-02`: market makers. Two-sided quotes at fair value ±2 ticks, fair value = fundamental plus a private bias plus a skew for a *strong* top-of-book imbalance (dead zone 0.30, up to 2 ticks). Re-quote by cancel/replace when the target mid moves a tick, replace a quote that was filled, pull both quotes on a market event and re-quote wider for 30 s. Registered on the instrument. The imbalance skew is what makes a spoof "work": a large resting order on one side moves the quotes 1-2 ticks the spoofer's way, and they come back when it is cancelled.
  - `T-NOISE-01..12`: retail-style flow, Poisson arrivals (0.6/s) of small limit orders 0-4 ticks behind the touch that expire after an exponential lifetime (mean 25 s), 25% market orders; 60% of resting orders are pulled within 200 ms of a market event (the cancel storm).
  - `T-VAL-01..03`: value traders that trade toward the fundamental when the mid is 2+ ticks away.
  - `T-AGY-01`: agency desk routing client orders (1.5/min, 200-1,500 shares) with a client parent id, mostly passive at the touch, unfilled remainders time out.
  - `T-ALGO-01`: two-sided agency algo desk running TWAP parents whose `PEGGED` children sit at the same-side touch and are re-pegged (cancel/replace) when it moves.
  - `T-INST-01..03`: institutional counterparties that act only when a scenario script needs someone to hit a quote; they never rest orders, so self-trade prevention cannot swallow a scripted trade.
- Output per session: `order_events`, `trades`, `traders`, `market_events`, `instrument_stats` (ADV, average spread, average top-5 depth per side, tick size), plus `injections` and `cases_history` fixtures.

### 2.2 Scenario injection

Each scenario is a scripted sequence by one trader at a chosen time, with its label. Volumes are expressed relative to the instrument's average depth so the scenarios scale with the background.

| Id | Label | Script | What the detector sees |
|---|---|---|---|
| S-SPOOF-1 | TRUE_ABUSE | PROP trader places one large order (8-15× top-5 depth) 2-4 ticks away from the touch on a random side; waits 1.5-3.5 s for the market makers to skew; trades the other side with a market order sized like a normal participant's (10-20% of the spoof, capped at 0.8× depth); cancels the large order 100-500 ms after the fill. | Classic spoof. |
| S-SPOOF-2 | TRUE_ABUSE | Same, repeated 3-6 times 60-150 s apart. | Repeated spoof; one alert (cooldown), `repetitions_in_session` 3-6. |
| S-LAYER-1 | TRUE_ABUSE | Five orders at successive levels on one side, aggregate 10× depth; opposite-side market order; all layers cancelled within 1 s. | Layering. |
| S-SPOOF-3 | TRUE_ABUSE | S-SPOOF-1 by a trader whose profile says MARKET_MAKER, registered on `SYN.B`, not on `SYN.A`. | Spoofing with a misleading profile. |
| S-SPOOF-4 | TRUE_ABUSE | S-SPOOF-1 by an ALGO-desk trader with six prior CLOSE_FP dispositions in `cases_history` ("pegged execution algo; cancels symmetric"). | Spoofing against memory bias. |
| S-SPOOF-5 | TRUE_ABUSE | Spoof placed two ticks away; 100-250 ms after the spoofer trades the other side, an institutional sweep hits the resting order for 15-30% before he can pull it; the remainder is cancelled 300-800 ms after his trade. | Messy spoof: the resting order was partially executed, which is the tell most heuristics trust. |
| F-MM-1 | FALSE_POSITIVE | Registered market maker quotes both sides one tick inside the touch at 1.2× depth, re-quotes every 1.5-3 s for 90 s; three institutional market orders hit its quotes. | Symmetric cancels; role explains. |
| F-ALGO-1 | FALSE_POSITIVE | Agency algo desk works a buy parent and a sell parent at once; `PEGGED` children at 1.0× depth re-pegged every 2-4 s for 120 s; counterparties fill both sides. | Parent/child structure; symmetry. |
| F-RISK-1 | FALSE_POSITIVE | PROP trader works three large bids (2.0× depth each) and a small ask; a counterparty lifts the ask; one second later the kill switch cancels everything; `risk_limit_events` records it. | Simultaneous all-side cancel; risk event. |
| F-NEWS-1 | FALSE_POSITIVE | Two large bids (2.8× depth each); a small hedge ask lifted 2.5-4 s before issuer `NEWS`; the trader and most of the market cancel within 200 ms of the news. | Market-wide cancel storm; event explains. |
| F-ICE-1 | FALSE_POSITIVE | Agency `ICEBERG` buy for client A (8× depth, 0.3× depth visible) one tick inside the touch when the spread allows; three institutional sells of 1.0× depth sweep the bid level and execute against the tip; a sale for client B lifted by a counterparty; client A pulls the order. | Order type, partial executions on the iceberg, different parent ids. |
| F-PARTIAL-1 | FALSE_POSITIVE | Large buy (5× depth) one tick inside the touch, two large partial executions, a small hedge ask lifted, then a `MODIFY` cutting the order to an 8% residual; the residual later completes. | Modification after partial; consistent intent. |
| F-FAT-1 | FALSE_POSITIVE | PROP trader enters 10× the intended size one tick behind the touch, cancels within 0.8-2 s, re-enters the right size; no opposite fill. | `LARGE_QUICK_CANCEL` trigger; one-off, no benefit. |
| F-STOP-1 | FALSE_POSITIVE | Momentum trader buys 0.5× depth at market, adds three bids of 1.8× depth 5-7 ticks behind; the fundamental drops 3 ticks; he sells 0.5× depth at market (a loss; if the market has gapped down onto his own bid he pulls that bid first, as self-trade prevention would otherwise block the sale) and cancels the rest 600 ms later. | Price moved against the resting side; round trip closed at a loss; nothing to revert. |
| F-SPOOFLIKE-HARD-1 | FALSE_POSITIVE | Registered market maker long inventory: 1.5× depth asks one tick *inside* the touch (first in queue), re-priced down with the drifting fundamental every 3 s for 90 s; 0.3× depth bids one tick *behind* the touch; institutional buyers lift his ask every 11 s and one seller hits his bid. | The hard negative: one-sided cancels, high OTR, but same-side executions dominate (he is *selling* into the move), and the price does not snap back after his cancels. |

Third-party actions inside a script (a counterparty hitting a quote, an adverse move of the fundamental) are part of the scenario's world, not the trader's conduct. Scenario traders are named `T-X<mmdd>-<nn>` and act only during their script; every other alert in the dataset comes from the background population and is labelled `BACKGROUND`. The desk scenarios (F-MM-1, F-ALGO-1, F-SPOOFLIKE-HARD-1) set the trader's `typical_order_size` to the size they actually quote, so "typical for the desk" in their labels is true of the profile; the PROP scenarios keep a modest typical size, because working ten times your usual size is itself something an analyst notices.

Mix per dataset build: about 15-20% TRUE_ABUSE, the rest FALSE_POSITIVE weighted toward F-MM-1 and F-ALGO-1, because that is what real queues look like. Sampling is Poisson per session (1.3 TRUE and 4.0 FALSE injections expected), weights within each class as in `SCENARIOS` in `src/market_sim/scenarios.py`. Random seeds are fixed and recorded so a dataset build is reproducible. **First build (seed 7, 20 sessions, 2026-11-02, after the hand-check fixes below):** 167 alerts, 28 TRUE_ABUSE (17%), 87 injected FALSE_POSITIVE, 52 BACKGROUND (all market makers), detector recall on injected abuse 100%, 0 missed injections, 1.82 million order events, 24 MB of parquet, built in 15 s.

### 2.3 Labels

`labels` are stored separately from everything the Gateway can reach: `<dataset>/labels/` locally, never loaded into DynamoDB. Each label: `alert_id`, `truth`, `injected_scenario` (a catalogue id, or `BACKGROUND` for an alert the background population caused), `expected_disposition` (TRUE_ABUSE -> ESCALATE or DRAFT_STOR, both count as correct for the gate; FALSE_POSITIVE -> CLOSE_FP), `key_discriminators` (which facts should appear in a correct report), `expected_tools` (minimum tool set; every CLOSE_FP expects `get_trader_alert_history`, per policy 04), `notes`, `trader_role`. An alert is attributed to an injection when the same trader, instrument and date match and the alert window overlaps the script's time span padded by the detector's W and C. The same directory holds `injections.parquet`, `discriminators.parquet` (the tool's output for every alert, for offline analysis) and `baseline.parquet` (the threshold baseline's decision and rule per alert).

Note on expected disposition for true abuse: the gate counts both ESCALATE and DRAFT_STOR as correct, because an L1 analyst who escalates a real case has done the job. DRAFT_STOR vs ESCALATE is a secondary precision metric, not a gate.

### 2.4 Hand-check, round 1 (2026-11-02)

George replayed five alerts (`scripts/replay_alert.py --random 3 --reveal`, then S-SPOOF-5 and F-SPOOFLIKE-HARD-1). Three matched their labels and taught the right lesson: F-STOP-1's adverse price move, S-SPOOF-3's misleading profile, F-ALGO-1's pegged two-sided children. Two did not, and both were defects in the generator or the metric, not in the labels:

1. **F-SPOOFLIKE-HARD-1 contradicted its own label.** The label said the market maker was selling inventory; the tape showed 206 shares sold and 5,381 bought. His asks joined the back of the queue at the touch and never traded, while his bids improved the touch and were hit constantly. Fixed by putting the asks one tick inside the touch and the bids one tick behind. The discriminators now read same-side 11,000-17,500 vs opposite 0-800.
2. **`reversion_ticks` was measured from the cancel**, so a stopped-out trader's own market sale, which depresses the mid for a moment, made the book's recovery look like a spoof snapping back (F-STOP-1 showed reversion 1.0 while its label said "no reversion"). Fixed: the post-cancel move is measured from the mid *before* the trader's opposite-side execution, and `reversion_ticks` reports only how much of a *favourable* pre-trade move was undone (0 when there was none). A `round_trip_ticks` field (SELL VWAP minus BUY VWAP inside the window) was added so a stop-out's loss is a number, not an inference; the baseline's R7 uses it.

Two realism fixes came out of the same session: scripted market orders are now at most 0.5× depth (a 1.0× order swept the whole visible book), and `market_wide_cancels_1s_before_first_cancel` counts distinct traders rather than cancel events (a re-quoting market maker produced five cancels on its own and tripped the baseline's R4 on a true layering case). S-SPOOF-5 was also re-ordered so the third-party sweep lands just *after* the spoofer's own trade, which is what "caught in the book" means. 

**Round 2 (seven alerts: F-MM-1, two background market makers, two F-ALGO-1, F-ICE-1, F-NEWS-1).** Six matched their labels. F-ICE-1 did not: the label promised partial executions on the iceberg and the tape showed none, because the spread was one tick, the iceberg could not improve the bid, it joined the back of the queue, and the three scripted sells of 0.25× depth never reached it. Fixed by sizing the scripted sells at 1.0× depth so they sweep the level; all nine F-ICE-1 alerts now show 2,990-12,197 shares executed on the iceberg. The same pass found a profile inconsistency: F-MM-1's label said "quote size typical for the desk" while the profile said 900 and the quotes were about 3,100; the desk scenarios now write their quoted size into the profile. Twelve alerts read by a human in total, three defects found, all three in the generator or a metric, none in a label's intent. Baseline raw safe close after the fixes: 96%, gate still failed on S-SPOOF-5 only.

**Round 3, confirmation (one alert from each of the five changed scenarios).** All five tapes match their labels: six tip-sized partial executions on the F-ICE-1 iceberg before client B's sale; F-MM-1's profile size equal to its quote; F-SPOOFLIKE-HARD-1 selling 8,234 against 404 bought while walking its asks down eight levels, with no reversion; F-STOP-1 losing 5.9 ticks on the round trip; S-SPOOF-5 hit by the third-party sweep 242 ms after the spoofer's own trade and cancelled 535 ms later. Two caveats for the agent's prompt rather than defects: (1) `price_move_ticks` loses its meaning when `same_side_fill_qty` is large, because a trader who executes on the resting side moved the price by trading, not by resting (the hard negative shows +4.0 for that reason); (2) a spoofer's genuine market order can sweep up to the level of his own resting order when the book between is thin, which is poor execution but not a label problem. Seventeen alerts read by a human in total; Phase 1 closed.

## 3. Detector (`src/detector/`)

A rule-based scenario, written to be noisy on purpose, since realistic alert quality is the premise. Two triggers, evaluated per date, instrument and trader (`src/detector/rule.py`, version `spoof-naive-v1`):

```
trigger 1, OPPOSITE_FILL_CANCEL: for each execution of the trader on side X at time tf, Y = other side
  gross_Y  = size of all non-market orders the trader SUBMITTED on Y in [tf - W, tf]        (W = 60 s)
  if gross_Y >= K * avg_depth_top5                                                           (K = 3.25)
     and resting_Y(tf) > 0
     and cancelled_Y in [tf, tf + C] >= P% of resting_Y(tf)                                  (C = 5 s, P = 70)
  then candidate alert, window [tf - W, tf + C]

trigger 2, LARGE_QUICK_CANCEL: for each non-market order of size q >= K2 * avg_depth_top5     (K2 = 6)
  if cancelled on that side within C2 of placement >= P% of q                                (C2 = 10 s)
  then candidate alert, window [t_new - 5 s, t_new + C2]        (no opposite fill needed: attempts count)

MODIFY size reductions count as cancellations. Market orders never count as resting size.
Candidates whose windows overlap merge into one alert (union window, stronger trigger kept);
otherwise one alert per trader and instrument per 15-minute cooldown.
scenario = LAYERING if the trader had >= 3 distinct resting price levels on Y at tf, else SPOOFING.
```

Three deliberate naiveties make it noisy in the way firms describe. It measures *gross submitted* size, so an active quoter who re-quotes twenty times a minute looks like one huge order. It checks neither the trader's role nor whether the cancels were two-sided, nor whether a market event or a risk cut explains them, nor whether the resting orders were executing. And its window is one fixed 60 s (Delegated Regulation (EU) 2026/788 point 10 says indicators may be assessed over shorter or longer frames; the agent's report states the window it used). K was set at 3.25 so that the background market makers trip it about twice a day: at 3.0 they fired up to ten times a day, at 4.0 almost never. Every alert carries the detector version and the parameter set as JSON.

A **threshold baseline** (`src/detector/baseline.py`) is also built from `compute_discriminators` output, the trader profile and the market events, with nine if/then rules an analyst would write first: R1 registered market maker with cancel symmetry ≥ 0.6, R2 pegged children with parents and symmetry ≥ 0.6, R3 risk event in the window, R4 market event in the window or ≥ 5 other traders' cancels in the second before ours, R5 the resting orders were genuinely executing (iceberg with executions, or ≥ 15% of gross executed), R6 large quick cancel with no opposite fill and no repetition, R7 price moved ≥ 0.5 ticks against the resting side or the trader closed his round trip ≥ 1 tick below where he bought (with no favourable move); otherwise R8 DRAFT_STOR if ≥ 3 cycles, R9 ESCALATE. Not tuned on the labels. The agent is evaluated against it on the same dataset, so the presentation can show what the LLM adds, if anything.

**First-build result for the baseline (seed 7):** raw safe close rate 96%, but it proposes CLOSE_FP for 6 of the 7 S-SPOOF-5 alerts through R5 ("the resting order was genuinely executing"), so it fails the gate and its safe close rate is reported as n/a. It closes every F-STOP-1 (R7) and none of the F-SPOOFLIKE-HARD-1 (the only false positive it cannot explain). That is the finding the agent has to beat: a partially executed spoof defeats the obvious heuristic, and only a reading of the whole sequence (a third party hit the order *before* the trader traded the other side, then everything was pulled) separates it from F-PARTIAL-1.

## 4. Evaluation harness (`evals/`)

### 4.1 What AgentCore Evaluations gives us

Per session or trace scores from built-in evaluators with ground truth [verified 2026-11-02, devguide "Ground truth evaluations"]:

- `Builtin.Correctness` with `expectedResponse` : the expected disposition and key discriminators as text.
- `Builtin.GoalSuccessRate` with `assertions` : e.g. "The report considers and rules out market making, citing the trader profile." "The report does not state any numeric value that is absent from tool outputs." "The agent did not propose a disposition before calling compute_discriminators."
- `Builtin.TrajectoryInOrderMatch` with `expectedTrajectory` : `get_alert` -> evidence tools -> `propose_disposition`, extra tools allowed.
- A custom trace-level evaluator with the rationale rubric (clarity for L2, indicator vocabulary, explanations considered, consistency of disposition with evidence) using `{assistant_turn}` and `{expected_response}`.

Prerequisites: agent on Runtime with Observability and CloudWatch Transaction Search on; 2-5 minutes between invocation and evaluation for telemetry ingestion.

### 4.2 What we compute ourselves

AgentCore Evaluations scores cases; it does not know our gate. `evals/run_dataset.py`:

1. Builds or loads a dataset (seeded).
2. Invokes the agent once per alert (one Runtime session per alert; session id recorded), via `OnDemandEvaluationDatasetRunner` or direct invoke plus CLI evaluation.
3. Pulls the proposed disposition from the `cases` table (what the agent actually wrote), not from the LLM's chat text.
4. Joins with `labels`.
5. Computes:
   - **Gate:** `missed_true = count(truth == TRUE_ABUSE and proposed == CLOSE_FP)`. Must be 0.
   - **Safe close rate:** `count(truth == FALSE_POSITIVE and proposed == CLOSE_FP) / count(truth == FALSE_POSITIVE)`. Reported only if gate holds; otherwise "n/a (gate failed: k missed)".
   - **Escalation precision:** share of ESCALATE/DRAFT_STOR proposals that are TRUE_ABUSE.
   - **Strong-call precision:** share of DRAFT_STOR proposals that are TRUE_ABUSE.
   - **Evidence faithfulness:** programmatic check that every number in `report.evidence[].fact` appears in a tool output span for that session.
   - **Override rate:** share of proposals the recording analyst changed. In the synthetic harness the "analyst" is the label, so override rate = 1 - agreement with the label; in production it is the real analyst's decision from the `cases` table. Tracked across runs as the learning signal (design doc section 11).
   - **Rubric mean** from the custom evaluator; **assertion pass rate** from GoalSuccessRate; **trajectory pass rate**.
   - **Per-scenario breakdown** (which F-scenarios the agent fails to close; which S-scenarios it under-calls).
   - Latency p50/p95 and token cost per alert.
6. Writes `evals/runs/<timestamp>/results.md` and a JSON, and compares to the previous run (regression report).

### 4.3 Baselines to report alongside

- Threshold baseline (section 3) on the same dataset.
- "Escalate everything": safe close rate 0%, gate trivially holds. Shows the floor.
- Optionally a no-memory agent run, to show memory's contribution and its risk (S-SPOOF-4).
- Model arm: the same prompt and seed on Opus 5.5 and on Sonnet 5.5 (a configuration-bundle change, nothing else). Both must hold the gate; the comparison is on safe close rate and override rate for the hard scenarios, rubric, cost and latency per alert. Whichever way it comes out is a finding: either governance and deterministic tools carry the result on the smaller model, or the harder judgement calls need the larger one. The rationale rubric is judged by Opus 5.5 so that the judge is not the agent's own model when Sonnet is the agent; when Opus is the agent, the rubric is read as secondary and the deterministic checks carry the decision.

### 4.4 Promotion rule

A prompt, tool or policy change is accepted only if, on the fixed evaluation seed: gate holds, safe close rate does not drop by more than 2 points, evidence faithfulness stays at 100%, and no new scenario regresses to 0% close. Recorded in `decision-log.md` with the run id. The same rule applies to configuration bundles produced by AgentCore Optimization: a recommendation that wins its A/B test on the online evaluators is still promoted only after it passes this offline check on the fixed seed.

### 4.5 Measuring the learning loop

The four mechanisms in design doc section 11 are measured as follows:

1. **Case-based recall (Memory):** run the fixed seed twice, with and without Memory retrieval, after seeding Memory with the dispositions of a first pass. Report safe close rate, override rate and the S-SPOOF-4 outcome for both. Memory must raise the first two and must not change the gate.
2. **Dataset growth from overrides:** `evals/ingest_overrides.py` converts every override in `cases` into a labelled case (truth = the analyst's recorded disposition mapped to TRUE_ABUSE or FALSE_POSITIVE, `key_discriminators` = the analyst's note). New cases are tagged with the run they came from, so later runs can report close rate on "cases the agent previously got wrong".
3. **Optimization:** one iteration in Phase 5: generate a recommendation against the rationale evaluator, create bundle v2, A/B v1 vs v2 on a replay of the dataset through the Gateway, then run the promotion rule offline. Report both the online A/B result and the offline table.
4. **Threshold re-tuning:** `src/detector/tune.py` grid-searches K, P, C on the labelled dataset and reports detector precision at 100% recall on injected abuse, old vs new. Applied only to the next dataset build, never retroactively.

Override rate is the headline number for "is it getting better": it is what an analyst feels day to day and what a head of compliance can read without a glossary.

## 5. Dataset hygiene

- Seeds and generator version in every dataset's manifest.
- Labels never pass through the Gateway, never appear in Memory, never appear in prompts.
- Trader and instrument names are synthetic and obviously so (e.g. `T-0042`, `SYN.A`).
- Keep a small hand-checked subset (10-15 alerts) that George reviews himself, to make sure the labels mean what we think they mean. This is also the best way to learn the domain.
