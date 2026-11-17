# Domain primer for Kiro: trade surveillance (compact)

Detail and sources are in `docs/en/01-domain-primer.md`. This file is the working vocabulary.

## The obligation

- EU: Market Abuse Regulation (MAR), Regulation (EU) 596/2014. Art. 12 defines market manipulation; Art. 15 prohibits it; Art. 16(2) obliges "persons professionally arranging or executing transactions" (brokers, investment firms) to have effective systems to detect suspicious orders and transactions and to file a STOR (Suspicious Transaction and Order Report) with the national competent authority without delay. [verified 2026-11-02, EUR-Lex / CySEC / MFSA]
- Delegated Regulation (EU) 2016/957 sets the RTS: appropriate and proportionate systems, human analysis by trained staff, records of analysis including the decision *not* to report, retained five years and available to the regulator on request. [verified 2026-11-02, EUR-Lex recitals; five-year figure from FCA STOR update page; exact article number to re-check when citing]
- Delegated Regulation (EU) 2016/522 Annex II, Section 1 point 5(e): layering and spoofing = multiple or large orders away from the touch on one side to execute on the other, then removal of the orders never meant to execute; supplementary indicator 4(f) = high cancel or order-to-trade ratio. Amended by Delegated Regulation (EU) 2026/788 (OJ 16 July 2026, in force 5 August 2026): time frames may be shorter or longer than a session (points 1a, 4a, 10, aimed at illiquid names and algo trading), volume changes count as well as price (1a, 4a), pending orders and indirect exposure count for positions (2a), partial reversals count (5a); spoofing wording substantively unchanged. Also designates four share venues (Aquis, TP ICAP, Cboe Europe, Turquoise) for NCA order-data exchange under MAR Art. 25a. [verified 2026-11-02, OJ text]
- ESMA STOR report (Dec 2025): 5,981 STORs across the EEA in 2024, -8% y/y; 76% from investment firms, 85% shares, 57% insider dealing vs 41% manipulation; no breakdown by manipulation type; nothing on alert volumes or false positives. Cyprus ~180-190 STORs (chart reading), Greece under 15. [verified 2026-11-02]
- Algorithmic trading firms (including prop/HFT with no clients): MiFID II Art. 17 and RTS 6 (Delegated Regulation (EU) 2017/589) Art. 13 require monitoring of all trading through the firm's systems for signs of manipulation, with an automated surveillance system. [verified 2026-11-02, FCA Handbook technical standards]
- US: FINRA Rule 3110 (supervision) and exchange/FINRA cross-market surveillance; spoofing is explicitly illegal in futures under CEA 4c(a)(5)(C) (Dodd-Frank s.747) and prosecuted in securities under Exchange Act 9(a)(2)/10(b). [unverified in this session, from background knowledge]

## The behaviours

- **Spoofing**: place orders you intend to cancel on one side of the book to create a false impression of supply or demand, get a genuine order filled on the other side, cancel the spoof orders.
- **Layering**: spoofing with several orders at successive price levels on the same side, to fake depth.
- **Wash trade**: trading with yourself (or colluding) to create false volume. Out of scope.
- **Insider dealing**: trading on material non-public information. Out of scope.

## The analyst workflow

Detector raises alert -> L1 analyst triages (minutes per alert) -> close as false positive with written rationale, or escalate to L2 -> L2 investigates (hours to days: order book replay, trader interview, comms) -> close or file STOR. Every step is recorded because the regulator can ask for the reasoning behind any closure.

## The numbers that matter

- Alert false-positive rates in the industry are routinely above 90%; vendor and consultancy figures range from "more than half of alerts are low quality" to 99%+ (PwC 2019 survey as cited by NICE Actimize: ~40M alerts across 17 firms, 1 in 12,000 led to a STOR). Treat vendor numbers as marketing; cite the survey. [verified 2026-11-02 that these figures are published; not independently audited]
- The cost is analyst time and the risk is the missed true positive: a regulator fine or criminal case for an undetected spoofer dwarfs any efficiency gain. So the project metric is **safe close rate at 100% recall on true abuse**, never raw accuracy.

## What makes a spoofing alert a false positive (the discriminators the agent must check)

- Registered market maker with two-sided quoting obligations: constant cancel/replace is their job. Not an exemption: FCA v Walter (2017, £60,090), a bond market maker who posted best-bid quotes to pull tracking algorithms up, sold into them and cancelled [verified 2026-11-17, FCA Final Notice of 22 November 2017].
- Algorithmic re-pricing (pegged orders, VWAP slices): cancels follow mid-price moves, both sides, symmetrically.
- Risk-limit or kill-switch cancellation: all orders pulled at once, no opposite-side fill.
- Reaction to a news/event: cancellation coincides with a public event, many participants do the same.
- Iceberg replenishment and legitimate order modification.
- Fat finger followed by immediate cancel, no opposite-side benefit.
- Key tells for *true* spoofing: imbalance on one side, fill on the opposite side shortly before the cancels, repeated pattern, orders sized far above typical, placed away from the touch so they are unlikely to fill, trader profits from the price move.

## Vendors (so we don't claim a gap that isn't there)

NICE Actimize (SURVEIL-X), Nasdaq Trade Surveillance (formerly SMARTS), Eventus (Validus), SteelEye, Trading Technologies TT Score, Trillium Surveyor, b-next, Scila, Solidus Labs (crypto), Behavox (comms). Most sell detection and case management; agentic investigation of alerts is where newer "AI" features are appearing. [vendor list from background knowledge; verify before naming any in the presentation]
