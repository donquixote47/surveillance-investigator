# 01 - Domain primer: trade surveillance for market abuse

This is the long version, written for someone who works with brokers and trading firms but has not sat in a compliance team. Sources are given inline. Statements marked `[unverified]` come from background knowledge and must be checked before they go into the presentation.

## 1. What "market abuse" means

Market abuse is the umbrella term regulators use for two families of behaviour:

- **Insider dealing**: trading, or inducing others to trade, on the basis of material information that is not yet public.
- **Market manipulation**: acting in a way that gives false or misleading signals about the supply, demand or price of a financial instrument, or secures the price at an artificial level, or uses deception.

Both are prohibited for everyone, not only for regulated firms. What *is* specific to regulated firms is the obligation to look for it in their own and their clients' order flow and to report it. That obligation is what trade surveillance exists to meet.

## 2. The behaviours, in order-book terms

A quick model of a lit equity market: a **limit order book** holds resting buy orders (bids) and sell orders (asks) at different price levels. The best bid and best ask are the **touch**; the difference is the **spread**. A **market order** or an aggressive limit order crosses the spread and trades against resting orders. Participants can **cancel** or **modify** resting orders at any time. A broker sees every order event (new, modify, cancel, fill) for its own traders and its clients, each stamped with a trader or client identifier, a timestamp and the order's price, size and side.

### 2.1 Spoofing

A trader wants to buy 2,000 shares at a good price. He places a large sell order (say 20,000 shares) a few ticks above the best ask, where it is unlikely to be hit. Other participants and their algorithms see the heavy sell interest, expect the price to fall, and some lower their bids or sell. The trader's genuine 2,000-share buy order on the other side fills at the lower price. He then cancels the 20,000-share sell order, which was never meant to trade.

The tells, which the detector and the agent both look for:

- A large order (relative to the book depth or the trader's usual size) on one side.
- Placed away from the touch, so it is unlikely to execute.
- A fill for the same trader on the **opposite** side shortly afterwards.
- Cancellation of the large order shortly after the opposite-side fill.
- Price moved in the direction the large order suggested, then reverted.
- The pattern repeats.

### 2.2 Layering

Same intent, more elaborate: several orders at successive price levels on the same side (five orders of 4,000 at ask+1, +2, +3, +4, +5) to make the depth look heavy across the whole side, rather than at one level. Detection logic is the same with "aggregate resting size on one side" instead of "one large order". Regulators treat layering as a form of spoofing; the EU's indicators list describes the placing of orders with no intention to execute them as an indicator of false or misleading signals [verified 2026-11-02, Delegated Regulation (EU) 2016/522 Annex II, confirmed by European Parliament answer P9_RE(2019)003021 that spoofing is specified there].

### 2.3 Behaviours that look like spoofing and are not

This is the heart of the project. A detector that only sees "big order, opposite fill, cancel" raises alerts on all of these:

| Legitimate behaviour | Why it triggers the detector | How an analyst tells it apart |
|---|---|---|
| **Market making** | A market maker quotes both sides continuously and cancels/replaces thousands of times a day as the mid moves. | The trader is a registered market maker on this instrument; quotes are two-sided and symmetric; cancels follow mid-price moves rather than own fills; order sizes are typical. |
| **Algorithmic re-pricing** (pegged orders, VWAP or TWAP slices) | The algo cancels and re-submits as the reference price moves. | Cancels are symmetric across sides and correlated with mid moves; the algo's parent order explains the child orders; no opposite-side fill benefits from the cancel. |
| **Risk-limit or kill-switch cancellation** | All resting orders are pulled at once. | Cancels hit every instrument and both sides simultaneously; no opposite-side fill precedes them; the firm's risk system logs the trigger. |
| **Reaction to news or an event** | Many participants cancel at the same moment. | The cancel coincides with a public event (earnings, macro print, trading halt); the whole book thins, not only this trader. |
| **Iceberg or reserve orders** | The visible tip refreshes repeatedly, which looks like cancel/replace. | The venue flags the order type; the refreshes are same price, same side, same size. |
| **Order modification after a partial fill** | The trader reduces size or moves price after a partial. | The order was partially executed; the modification is consistent with completing the order, not avoiding it. |
| **Fat finger** | A mistaken large order is cancelled seconds later. | One-off, no opposite-side fill, often followed by a corrected order of the intended size. |
| **Momentum trader stopped out** | Large orders placed and pulled as the market turns. | No opposite-side fills that benefit; the trader loses on the move rather than gaining. |

Each row is a scenario in our synthetic dataset (`04-synthetic-data-and-evaluation.md`).

### 2.4 Other abuse types (out of scope, for orientation)

- **Wash trading**: trading with oneself or a collaborator to inflate volume.
- **Marking the close**: trading at the end of the session to move the closing price.
- **Front running**: trading ahead of a known client order.
- **Momentum ignition**: aggressive trading to start a price move others follow, then reversing.
- **Quote stuffing**: flooding the book with orders to slow down competitors' systems.
- **Insider dealing** and **unlawful disclosure**.

## 3. How surveillance works in a broker or trading firm today

### 3.1 The pipeline

1. **Data capture.** Order and trade events from the OMS/EMS and from venue drop copies are stored with full lifecycle (new, modify, cancel, fill), typically at microsecond or nanosecond timestamps for electronic trading. Regulations require order record-keeping anyway (EU MiFIR Art. 25 and RTS 24; US CAT) [unverified for exact articles].
2. **Detection.** A surveillance platform runs rule-based scenarios overnight or intraday: "spoofing", "layering", "wash trade", "marking the close", "insider dealing around news", and so on. Each scenario has thresholds (minimum size, time windows, ratios). Vendors: NICE Actimize SURVEIL-X, Nasdaq Trade Surveillance (formerly SMARTS), Eventus Validus, SteelEye, Trading Technologies TT Score, Trillium Surveyor, b-next, Scila, Solidus Labs for crypto. [vendor list from background knowledge; verify before naming in the presentation]
3. **Alert queue.** Each hit becomes an alert in a case-management tool with the triggering orders, the trader, the instrument and the scenario.
4. **Level-1 review.** An analyst opens the alert, looks at the order book around it, the trader's role and history, any news, and decides within minutes: close as false positive with a written rationale, or escalate.
5. **Level-2 investigation.** A senior analyst or the compliance officer replays the book, pulls communications, may interview the trader, and decides: close, internal action, or report.
6. **Reporting.** In the EU the report is a **STOR** to the national competent authority (CySEC, HCMC, FCA, BaFin, AMF, etc.). In the US, FINRA and the exchanges run their own surveillance and firms refer matters or respond to inquiries [unverified for the precise US mechanics].
7. **Records.** The analysis behind every closure, including the decision not to report, is kept and can be requested by the regulator.

### 3.2 The volume problem

Alert volumes are large and most alerts are false positives. Published figures, with the caveat that several come from vendors selling a fix:

- A PwC 2019 market-abuse surveillance survey, as summarised by NICE Actimize, reported about 40 million trade and communications alerts across 17 institutions, of which roughly one in 12,000 led to a STOR [verified 2026-11-02 that NICE Actimize publishes this summary; the PwC source document was not retrieved]. Content rephrased for licensing compliance.
- A 2025 Eventus / Datos Insights survey of 20 banks and broker-dealers found about 70% of respondents had false-positive rates above 25% [verified 2026-11-02, reported by The Full FX]. Note that this is a much lower number than the vendor marketing figures, which suggests the definition of "false positive" varies.
- A 2023 Markets Media piece reported more than half of surveillance executives saying more than half of their alerts were low quality [verified 2026-11-02, marketsmedia.com].
- ESMA's Report on STORs (19 December 2025, ESMA74-268544963-1554) gives the denominator: EEA NCAs received 5,981 STORs in 2024 (6,763 notifications including non-STOR inputs), 8% fewer than in 2023. Investment firms filed 76% of them; 85% concerned shares; 57% alleged insider dealing and 41% market manipulation, with no breakdown by manipulation type. Germany received 30% and France 16%. Cyprus is prominent in cross-border forwarding: 33% of STORs forwarded both to other NCAs and to third-country authorities came from CySEC. Visually from Figure 1, Cyprus received roughly 180-190 STORs and Greece under 15; those two numbers are chart readings, not printed figures. The report says nothing about alert volumes, false positives, STOR quality or automated surveillance. [verified 2026-11-02, report pp. 4, 7-10, 16, 18, 20, 23, 25]

Set the two sides next to each other: tens of millions of alerts a year at a handful of large institutions, against about six thousand STORs a year across the whole EEA. Whatever the exact false-positive rate, the funnel from alert to report is extremely narrow, and every stage of it is human work.

The honest summary for the presentation: false-positive rates vary by firm and by scenario, are consistently reported as the dominant cost of surveillance, and the figures in the 95-99% range are typical of rule-based spoofing and layering scenarios at larger firms. Quote the surveys and the ESMA denominator, not the brochures.

### 3.3 The asymmetry

Closing a false positive saves minutes. Missing a true positive can cost a firm a regulatory fine, a criminal case for the trader, and the firm's licence. Reference cases from US enforcement, all from background knowledge and to be verified before citing: Michael Coscia (first criminal spoofing conviction, 2015, Panther Energy); Navinder Sarao (spoofing in E-mini S&P futures, charged 2015); JPMorgan's 2020 settlement of about $920 million for precious-metals and Treasuries spoofing. These are why no compliance officer accepts a tool that optimises accuracy. They accept a tool that never closes a true case and saves time on the rest. That ordering defines our metric (`02-problem-statement.md`).

## 4. The regulation, with the articles that matter to this project

### 4.1 EU

| Instrument | What it says | Relevance |
|---|---|---|
| Regulation (EU) 596/2014 (MAR), Art. 12 | Defines market manipulation, including giving false or misleading signals as to supply, demand or price. | Spoofing and layering fall here. |
| MAR Art. 15 | Prohibits market manipulation and attempts. | |
| MAR Art. 16(2) | Persons professionally arranging or executing transactions must establish and maintain effective arrangements, systems and procedures to detect and report suspicious orders and transactions, and notify the competent authority without delay. [verified 2026-11-02, EUR-Lex; CySEC and MFSA circulars] | This is the obligation our users are meeting. "Orders" matters: cancelled orders count, not only trades. |
| Delegated Regulation (EU) 2016/957 (RTS on Art. 16) | Systems must be appropriate and proportionate to the business; include human analysis by appropriately trained staff; records of the analysis and of the reasons for submitting or not submitting a STOR must be kept and provided to the regulator on request. The FCA's STOR guidance states records are kept for five years. [verified 2026-11-02 recitals on EUR-Lex and FCA page; exact article numbers to confirm when citing] | This is why the agent's report and the policy decision logs are the product, not a by-product. "Human analysis" is why the agent proposes and a human disposes. |
| Delegated Regulation (EU) 2016/522, Art. 4 and Annex II | Non-exhaustive indicators of manipulative behaviour. Section 1 point 5(e) describes layering and spoofing in so many words: multiple or large orders away from the touch on one side of the book to execute on the other side, then removal of the orders that were never meant to execute; point 4(f) adds the supplementary indicator of a high cancelled-order or order-to-trade ratio. [verified 2026-11-02, OJ text] | The indicators are the vocabulary the agent's report should use: "orders away from the touch", "no intention to be executed", "order-to-trade ratio" map directly onto `compute_discriminators`. |
| Delegated Regulation (EU) 2026/788 (OJ L, 16 July 2026; in force 5 August 2026), amending 2016/522 | Recital 3: updated for supervisory experience and algorithmic trading. Annex I adds to Annex II of 2016/522: indicators may be assessed over time frames shorter or longer than a day or session, "particularly relevant" for less liquid instruments and algorithmic trading (new points 1a, 4a, 10); significant changes in *volume*, not only price, count for Indicators A(a) and A(d) (1a, 4a); a significant position may include pending orders, and indirect exposure through margin calls or debt covenants counts for A(b) (2a); position reversals may span a set of closely linked instruments (4a); price reversals may be partial (5a). Point 5(e) on layering and spoofing is re-enacted with the same substance and a corrected cross-reference to 4(f). Article 10a and Annex III designate four share-trading venues with a significant cross-border dimension for order-data exchange between NCAs under MAR Art. 25a (Aquis Exchange Europe, TP ICAP Europe, Cboe Europe, Turquoise Europe), shares first by 5 June 2026, bonds and futures by 5 June 2028. [verified 2026-11-02, OJ text via the Publications Office] | Three consequences for our design. The detector's 60-second sliding window is one legitimate time frame among several; the agent's report should state the window it used and, for illiquid names, consider a multi-session view (point 10). Volume-based indicators and partial reversals belong in `compute_discriminators` (`reversion_ticks` already allows partial). Spoofing is substantively unchanged, so the project is not chasing a moving target. A mentor who asks "what changed in July 2026?" gets a precise answer. |
| Directive 2014/65/EU (MiFID II), Art. 17 | Investment firms engaged in algorithmic trading must have effective systems and risk controls. | Brings prop and HFT firms with no clients into scope. |
| Delegated Regulation (EU) 2017/589 (RTS 6), Art. 13 | A firm engaged in algorithmic trading must monitor all trading activity through its systems, including clients', for signs of potential market manipulation under MAR Art. 12, with an automated surveillance system. [verified 2026-11-02, FCA Handbook technical standards text] | The explicit automated-surveillance requirement for George's HFT customers. |

The UK retains MAR as "UK MAR" with the same Article 16 structure and the FCA as recipient of STORs [verified 2026-11-02, FCA page].

### 4.2 US

- **FINRA Rule 3110 (Supervision)** requires member firms to have a supervisory system, including review of transactions, reasonably designed to achieve compliance with securities laws. FINRA and the exchanges also run cross-market surveillance themselves. [unverified in this session]
- **Securities Exchange Act s.9(a)(2) and s.10(b) / Rule 10b-5** are the anti-manipulation provisions used in equity spoofing cases. [unverified]
- **Commodity Exchange Act s.4c(a)(5)(C)**, added by Dodd-Frank s.747, makes spoofing explicitly unlawful in futures and is the basis of the CFTC and DOJ cases above. [unverified]

For the presentation, the EU framework is enough and is the one George's customers in Cyprus, Greece and the wider EU operate under. The US references show the problem is global.

## 5. Who does this work and what they want

| Role | What they do with an alert | What they want from a tool |
|---|---|---|
| L1 surveillance analyst | Triage 20-100+ alerts a day. Close false positives with a one-paragraph rationale; escalate the rest. | The evidence pre-assembled; a draft rationale they can edit; no surprises in the audit. |
| L2 analyst / compliance officer | Deep investigation of escalations; decides on STORs; owns the regulator relationship. | Confidence that nothing real was closed at L1; a clean record of why each closure happened; fewer bad escalations. |
| Head of compliance / MLRO | Owns the control; signs off on the surveillance framework; answers the regulator. | Defensible process; model-risk documentation; evidence that the tool cannot act alone. |
| Trader / desk head | Subject of alerts. | Fewer interruptions for obviously legitimate activity. |
| Regulator (NCA) | Receives STORs; inspects the framework; asks for the reasoning behind closures. | Records, consistency, human accountability. |

A tool is bought by the head of compliance, used by L1, and judged by L2 and the regulator. The agent therefore writes for L2 and the regulator, even though L1 clicks the buttons.

## 6. Vocabulary check

See `glossary.md`. The terms most worth knowing cold for the presentation: order book, touch, spread, depth, order-to-trade ratio, cancel ratio, resting order, aggressive order, fill, partial fill, market maker, pegged order, parent/child order, iceberg, STOR, NCA, MAR, RTS 6, false positive, true positive, recall, disposition, Level 1 / Level 2, four-eyes.
