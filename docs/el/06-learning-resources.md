# 06 - Πηγές μελέτης

Διαδρομή ανάγνωσης με σειρά. Πρώτα οι πρωτογενείς πηγές· το υλικό των προμηθευτών τελευταίο, και διαβάζεται ως marketing. Οι σύνδεσμοι ελέγχθηκαν ότι υπάρχουν στις 2026-11-02, εκτός αν σημειώνεται διαφορετικά.

## A. Η νομοθεσία (διαβάστε τα άρθρα, όχι περιλήψεις)

1. Regulation (EU) 596/2014 (MAR, ο Κανονισμός για την κατάχρηση αγοράς): Άρθρα 12 (χειραγώγηση), 15 (απαγόρευση), 16 (πρόληψη και εντοπισμός). https://eur-lex.europa.eu/eli/reg/2014/596/oj
2. Commission Delegated Regulation (EU) 2016/957: τα RTS (ρυθμιστικά τεχνικά πρότυπα) για τις ρυθμίσεις, τα συστήματα και τις διαδικασίες, και το υπόδειγμα STOR (Suspicious Transaction and Order Report, αναφορά ύποπτων συναλλαγών και εντολών) στο Παράρτημα. Διαβάστε πλήρως τα Άρθρα 2 και 3. https://eur-lex.europa.eu/eli/reg_del/2016/957/oj
3. Commission Delegated Regulation (EU) 2016/522, Άρθρο 4 και Παράρτημα II: δείκτες χειραγωγικής συμπεριφοράς. http://data.europa.eu/eli/reg_del/2016/522/2021-01-01 (ενοποιημένο κείμενο)
4. Commission Delegated Regulation (EU) 2026/788 που τροποποιεί τον 2016/522 (δείκτες, διασυνοριακά δεδομένα εντολών). https://eur-lex.europa.eu/eli/reg_del/2026/788/oj/eng (το EUR-Lex είναι πίσω από έλεγχο bot για αυτοματοποιημένη πρόσβαση· το Cellar της Υπηρεσίας Εκδόσεων σερβίρει το ίδιο κείμενο OJ στο http://publications.europa.eu/resource/celex/32026R0788) [read 2026-11-02; summarised in primer 4.1]
5. Commission Delegated Regulation (EU) 2017/589 (RTS 6), Άρθρο 13: παρακολούθηση για χειραγώγηση αγοράς σε εταιρείες αλγοριθμικών συναλλαγών. https://eur-lex.europa.eu/eli/reg_del/2017/589/oj/eng ; η απόδοση στο FCA Handbook είναι πιο εύκολη στην πλοήγηση: https://handbook.fca.org.uk/technical-standards/s119c1039/s119c1039s371
6. ESMA (Ευρωπαϊκή Αρχή Κινητών Αξιών και Αγορών), Έκθεση για τις αναφορές ύποπτων συναλλαγών και εντολών (Δεκέμβριος 2025). https://www.esma.europa.eu/sites/default/files/2025-12/ESMA74-268544963-1554_Report_on_Suspicious_Transaction_and_Order_Reports__STORs_.pdf [read 2026-11-02; numbers in primer 3.2]
7. Σελίδες εθνικών regulators (εποπτικών αρχών) για τα STOR, χρήσιμες για την πρακτική πλευρά: εγκύκλιος της CySEC για την πρόληψη και τον εντοπισμό κατά MAR (αναζητήστε «STOR» στο cysec.gov.cy)· Central Bank of Ireland https://www.centralbank.ie/regulation/industry-market-sectors/securities-markets/market-abuse-regulation/suspicious-transaction-reports ; FCA https://www.fca.org.uk/markets/market-abuse/how-report-suspected-market-abuse-firm-or-trading-venue
8. Ενημερωτικά δελτία Market Watch της FCA (αναζητήστε «Market Watch» στο fca.org.uk): περιοδικά ευρήματα για την αποτελεσματικότητα της surveillance (εποπτείας συναλλαγών), τη ρύθμιση των alerts και την ποιότητα των STOR. [unverified which issues are most relevant; skim the last ten]
9. Αμερικανικό πλαίσιο: FINRA Rule 3110· υποθέσεις spoofing της CFTC και του DOJ (Coscia 2015· Sarao 2015· JPMorgan 2020). [unverified links; search the regulator sites]

## B. Πώς δουλεύει η surveillance και γιατί τα alerts είναι θορυβώδη

10. PwC, "RegTech: the future of market abuse surveillance" (2018). https://www.pwc.com/us/en/financial-services/regulatory-services/publications/assets/pwc-regtech-market-abuse-surveillance.pdf
11. Η περίληψη του The Full FX για την έρευνα Eventus / Datos Insights 2025 σχετικά με την κόπωση από alerts. https://thefullfx.com/survey-sees-compliance-alert-fatigue/
12. Markets Media, "Trade Surveillance: Technology, Staffing Constraints Are Challenges" (2023). https://www.marketsmedia.com/trade-surveillance-technology-staffing-constraints-are-challenges/
13. Άρθρο blog της NICE Actimize που παραθέτει την έρευνα PwC 2019 (προμηθευτής· χρησιμοποιήστε το για την παραπομπή, όχι για τα συμπεράσματα). https://www.niceactimize.com/blog/winning-the-compliance-battle-on-multiple-fronts-tackling-market-abuse-and-false-positives
14. Σελίδες προϊόντων προμηθευτών, για να κατανοήσετε το σύνολο δυνατοτήτων των υφιστάμενων λύσεων πριν ισχυριστείτε ότι υπάρχει κενό: NICE Actimize SURVEIL-X, Nasdaq Trade Surveillance, Eventus Validus, SteelEye, TT Score, Trillium Surveyor. [search each; not linked to avoid stale URLs]

## C. Μικροδομή της αγοράς, όσο χρειάζεται για να χτίσουμε τον simulator

15. Οποιαδήποτε εισαγωγή στα limit order books (βιβλία οριακών εντολών): τα άρθρα της Wikipedia "Order book" και "Market maker" αρκούν για αρχή· μετά ξεφυλλίστε τις σελίδες wiki του ABIDES για τον exchange agent και τη ρύθμιση RMSC03, που περιγράφουν μια λειτουργική προσομοιωμένη αγορά. https://github.com/abides-sim/abides/wiki/RMSC03
16. Αποθετήρια ABIDES: https://github.com/jpmorganchase/abides-jpmc-public και η δημοσίευση ABIDES-Gym https://arxiv.org/abs/2110.14771 . Διαβάστε τα για τη σχεδίαση του πληθυσμού των agents· υιοθετήστε τα μόνο στη φάση επεκτάσεων.
17. Για τη μηχανική του spoofing με τα λόγια των regulators: τα δελτία τύπου της CFTC και του DOJ στις υποθέσεις Coscia και Sarao περιγράφουν συγκεκριμένα τα μοτίβα εντολών. [unverified links]

## D. AgentCore

18. Αρχική σελίδα του developer guide και σημειώσεις εκδόσεων. https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/ και https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/release-notes.html
19. Επισκόπηση των υπηρεσιών (διαβάστε την πρώτη). https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html
20. Policy (κανόνες πολιτικής που επιβάλλονται ντετερμινιστικά στις κλήσεις εργαλείων): https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy.html ; temporal policies (χρονικά εξαρτώμενοι κανόνες) https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-temporal.html ; συγγραφή https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-temporal-authoring.html ; παραδείγματα https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/example-policies-temporal.html ; sessions και διάδοση ταυτότητας https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-session-based-temporal.html ; δοκιμή σε LOG_ONLY https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-test-a-policy.html
21. Γλώσσα Dogwood: https://dogwood-policy.github.io/dogwood/index.html και https://github.com/dogwood-policy/dogwood ; Cedar https://www.cedarpolicy.com
22. Gateway (πύλη εργαλείων) με Policy: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/use-gateway-with-policy.html
23. Memory (μνήμη του agent): https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html
24. Evaluations (αξιολογήσεις): ground truth https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/ground-truth-evaluations.html ; on-demand https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/on-demand-evaluations.html ; dataset runner https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/dataset-evaluations-on-demand.html ; ενσωματωμένοι evaluators (αξιολογητές) https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/built-in-evaluators-overview.html ; προσαρμοσμένοι evaluators https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/custom-evaluators.html
25. Code Interpreter (εκτέλεση κώδικα σε απομονωμένο περιβάλλον): https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/code-interpreter-tool.html ; προεγκατεστημένες βιβλιοθήκες https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/code-interpreter-preinstalled-libraries.html
26. Runtime (περιβάλλον εκτέλεσης του agent): άμεση ανάπτυξη κώδικα για Python https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-code-deploy-python.html ; ξεκίνημα με το CLI https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-cli.html
27. Δείγματα κώδικα: https://github.com/awslabs/amazon-bedrock-agentcore-samples (οδηγοί αξιολόγησης στο `01-features/06-observe-evaluate-optimize-your-agent/02-evaluate`· workshop για Policy στο `06-workshops`).
28. Τεκμηρίωση Strands Agents (το framework με το οποίο γράφεται ο agent): https://strandsagents.com/latest/
29. AgentCore CLI: https://github.com/aws/agentcore-cli
30. Μέσα στο Kiro: το power `aws-agentcore` (αναζήτηση τεκμηρίωσης και control plane) και το power `strands`. Προτιμήστε τα από τη μνήμη του μοντέλου για οτιδήποτε αφορά την υπηρεσία.

## E. Πώς να χρησιμοποιήσετε αυτή τη λίστα

- Φάση 0: A1-A6, D18-D20, D24.
- Φάση 1: C15-C16, B10-B12.
- Φάσεις 2-4: D20-D26 κατά περίπτωση, D27 για λειτουργικό κώδικα.
- Πριν την παρουσίαση: A7-A8, B13-B14, για να βεβαιωθείτε ότι οι ισχυρισμοί για τον ανταγωνισμό είναι επίκαιροι.
