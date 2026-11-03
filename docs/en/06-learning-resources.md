# 06 - Learning resources

Ordered reading path. Primary sources first; vendor material last and read as marketing. Links were checked to exist on 2026-11-02 unless marked.

## A. The regulation (read the articles, not summaries)

1. Regulation (EU) 596/2014 (MAR): Art. 12 (manipulation), 15 (prohibition), 16 (prevention and detection). https://eur-lex.europa.eu/eli/reg/2014/596/oj
2. Commission Delegated Regulation (EU) 2016/957: the RTS on arrangements, systems and procedures, and the STOR template in the Annex. Read Article 2 and 3 in full. https://eur-lex.europa.eu/eli/reg_del/2016/957/oj
3. Commission Delegated Regulation (EU) 2016/522, Art. 4 and Annex II: indicators of manipulative behaviour. http://data.europa.eu/eli/reg_del/2016/522/2021-01-01 (consolidated)
4. Commission Delegated Regulation (EU) 2026/788 amending 2016/522 (indicators, cross-border order data). https://eur-lex.europa.eu/eli/reg_del/2026/788/oj/eng (EUR-Lex sits behind a bot challenge for scripted access; the Publications Office Cellar serves the same OJ text at http://publications.europa.eu/resource/celex/32026R0788) [read 2026-11-02; summarised in primer 4.1]
5. Commission Delegated Regulation (EU) 2017/589 (RTS 6), Art. 13: monitoring for market manipulation in algorithmic trading firms. https://eur-lex.europa.eu/eli/reg_del/2017/589/oj/eng ; the FCA Handbook rendering is easier to navigate: https://handbook.fca.org.uk/technical-standards/s119c1039/s119c1039s371
6. ESMA, Report on Suspicious Transaction and Order Reports (December 2025). https://www.esma.europa.eu/sites/default/files/2025-12/ESMA74-268544963-1554_Report_on_Suspicious_Transaction_and_Order_Reports__STORs_.pdf [read 2026-11-02; numbers in primer 3.2]
7. National regulators' STOR pages, useful for the practical view: CySEC circular on MAR prevention and detection (search cysec.gov.cy for "STOR"); Central Bank of Ireland https://www.centralbank.ie/regulation/industry-market-sectors/securities-markets/market-abuse-regulation/suspicious-transaction-reports ; FCA https://www.fca.org.uk/markets/market-abuse/how-report-suspected-market-abuse-firm-or-trading-venue
8. FCA Market Watch newsletters (search "Market Watch" on fca.org.uk): periodic findings on surveillance effectiveness, alert calibration, and STOR quality. [unverified which issues are most relevant; skim the last ten]
9. US context: FINRA Rule 3110; CFTC and DOJ spoofing cases (Coscia 2015; Sarao 2015; JPMorgan 2020). [unverified links; search the regulator sites]

## B. How surveillance works and why alerts are noisy

10. PwC, "RegTech: the future of market abuse surveillance" (2018). https://www.pwc.com/us/en/financial-services/regulatory-services/publications/assets/pwc-regtech-market-abuse-surveillance.pdf
11. The Full FX summary of the Eventus / Datos Insights 2025 survey on alert fatigue. https://thefullfx.com/survey-sees-compliance-alert-fatigue/
12. Markets Media, "Trade Surveillance: Technology, Staffing Constraints Are Challenges" (2023). https://www.marketsmedia.com/trade-surveillance-technology-staffing-constraints-are-challenges/
13. NICE Actimize blog citing the PwC 2019 survey (vendor; use for the citation, not the conclusions). https://www.niceactimize.com/blog/winning-the-compliance-battle-on-multiple-fronts-tackling-market-abuse-and-false-positives
14. Vendor product pages, to understand the incumbent feature set before claiming a gap: NICE Actimize SURVEIL-X, Nasdaq Trade Surveillance, Eventus Validus, SteelEye, TT Score, Trillium Surveyor. [search each; not linked to avoid stale URLs]

## C. Market microstructure, enough to build the simulator

15. Any introduction to limit order books: the Wikipedia article "Order book" and "Market maker" are enough to start; then skim the ABIDES wiki pages on the exchange agent and the RMSC03 configuration, which describe a working simulated market. https://github.com/abides-sim/abides/wiki/RMSC03
16. ABIDES repositories: https://github.com/jpmorganchase/abides-jpmc-public and the ABIDES-Gym paper https://arxiv.org/abs/2110.14771 . Read for the agent population design; adopt only in the stretch phase.
17. For the spoofing mechanics in regulators' words: the CFTC and DOJ press releases in the Coscia and Sarao cases describe the order patterns concretely. [unverified links]

## D. AgentCore

18. Developer guide home and release notes. https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/ and https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/release-notes.html
19. Overview of services (read first). https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html
20. Policy: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy.html ; temporal policies https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-temporal.html ; authoring https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-temporal-authoring.html ; examples https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/example-policies-temporal.html ; sessions and identity propagation https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-session-based-temporal.html ; LOG_ONLY testing https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-test-a-policy.html
21. Dogwood language: https://dogwood-policy.github.io/dogwood/index.html and https://github.com/dogwood-policy/dogwood ; Cedar https://www.cedarpolicy.com
22. Gateway with Policy: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/use-gateway-with-policy.html
23. Memory: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html
24. Evaluations: ground truth https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/ground-truth-evaluations.html ; on-demand https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/on-demand-evaluations.html ; dataset runner https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/dataset-evaluations-on-demand.html ; built-in evaluators https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/built-in-evaluators-overview.html ; custom evaluators https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/custom-evaluators.html
25. Code Interpreter: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/code-interpreter-tool.html ; pre-installed libraries https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/code-interpreter-preinstalled-libraries.html
26. Runtime: direct code deployment for Python https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-code-deploy-python.html ; CLI getting started https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-cli.html
27. Samples: https://github.com/awslabs/amazon-bedrock-agentcore-samples (evaluation tutorials under `01-features/06-observe-evaluate-optimize-your-agent/02-evaluate`; policy workshop under `06-workshops`).
28. Strands Agents docs: https://strandsagents.com/latest/
29. AgentCore CLI: https://github.com/aws/agentcore-cli
30. In Kiro: the `aws-agentcore` power (doc search and control plane) and the `strands` power. Prefer these over model memory for anything about the service.

## E. How to use this list

- Phase 0: A1-A6, D18-D20, D24.
- Phase 1: C15-C16, B10-B12.
- Phase 2-4: D20-D26 as needed, D27 for working code.
- Before the presentation: A7-A8, B13-B14 to make sure the competitive claims are current.
