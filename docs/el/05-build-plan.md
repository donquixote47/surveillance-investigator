# 05 - Σχέδιο υλοποίησης

Οι φάσεις είναι διατεταγμένες έτσι ώστε καθεμία να τελειώνει με κάτι που μπορεί να παρουσιαστεί σε demo και ώστε το κόστος AWS να έρχεται όσο πιο αργά γίνεται. Οι Φάσεις 0-1 δεν κοστίζουν τίποτα στο AWS. Τσεκάρετε τα ορόσημα εδώ και ενημερώστε το `STATUS.md` όταν αλλάζει φάση.

## Φάση 0 - Προετοιμασία και επαλήθευση (χωρίς κόστος AWS)

Στόχος: να ξέρουμε ότι η εργαλειοθήκη δουλεύει και ότι κάθε δυνατότητα του AgentCore που σχεδιάζουμε να χρησιμοποιήσουμε υπάρχει σήμερα στο eu-west-2.

- [x] `uv python pin 3.14` (Python 3.14.2 του συστήματος), `pyproject.toml` με strands-agents, strands-agents-tools, bedrock-agentcore, boto3, pandas, pyarrow, numpy, pydantic· dev group ruff, pytest, mypy. Το `uv sync` επιλύει και τα imports δουλεύουν στο 3.14.2 (2026-11-02: strands-agents 1.63.0, bedrock-agentcore 1.25.2, boto3 1.43.123, pandas 3.1.0, pyarrow 26.0.0). Οι στόχοι ανάπτυξης ταιριάζουν: το runtime `python3.14` της Lambda είναι GA και το AgentCore Runtime δέχεται `PYTHON_3_14`.
- [x] Εγκατάσταση του `agentcore` CLI (Node): `npm install -g @aws/agentcore`, έκδοση 1.0.1. Το `agentcore add` καλύπτει runtime, runtime-endpoint, gateway, gateway-target, gateway-connector, policy-engine, policy, credentials, memory, evaluator, online-eval, config-bundle, payment-manager. Καταγράφηκε στο `agentcore-gotchas.md`.
- [x] Επαλήθευση διαθεσιμότητας στο eu-west-2 (Λονδίνο): κλήσεις `list-*` μόνο ανάγνωσης στο `bedrock-agentcore-control` επιτυγχάνουν για agent runtimes, gateways, memories, policy engines, code interpreters, evaluators και browsers (2026-11-02). Η συμπεριφορά των temporal (χρονικά εξαρτώμενων) policies επαληθεύεται από τα docs· ζωντανός έλεγχος στη Φάση 4.
- [x] Πρόσβαση σε μοντέλα Bedrock: τα `eu.anthropic.claude-haiku-5-5` (βρόχοι ανάπτυξης) και `eu.anthropic.claude-sonnet-5-5` (προεπιλεγμένος agent) απαντούν σε κλήση `converse` ενός token από το eu-west-2 (2026-11-02)· το `eu.anthropic.claude-opus-5-5` είναι διαθέσιμο και αποτελεί το arm σύγκρισης της Φάσης 5 και τον κριτή του σκεπτικού. Τα inference profiles `eu.` δρομολογούν σε επτά περιοχές της ΕΕ, μαζί με το Λονδίνο.
- [x] Ανάγνωση του Delegated Regulation (EU) 2026/788 (κείμενο OJ μέσω της Υπηρεσίας Εκδόσεων· το ίδιο το EUR-Lex είναι πίσω από έλεγχο bot) και της έκθεσης της ESMA για τα STOR (Suspicious Transaction and Order Reports, αναφορές ύποπτων συναλλαγών και εντολών προς τον regulator) (2026-11-02). Η ενότητα 3.2 του primer έχει τον παρονομαστή STOR του ΕΟΧ και η ενότητα 4.1 τις ακριβείς αλλαγές του Annex II: η διατύπωση για το spoofing ουσιαστικά αμετάβλητη, νέα τα χρονικά πλαίσια και οι ενδείξεις όγκου.
- [x] Απόφαση: CDK Python για το mock back end σε δικό του stack (`infra/`), `agentcore.json` (έργο του AgentCore CLI) για Runtime, Gateway, targets, Policy Engine, Memory και evaluators. Καταγράφηκε στο `decision-log.md`.

Έξοδος (επιτεύχθηκε 2026-11-02): το `STATUS.md` λέει Φάση 1· το αρχείο gotchas έχει ενότητες «verified» με ημερομηνία για το CLI, το Optimization και τους ελέγχους control plane στο eu-west-2.

## Φάση 1 - Simulator, detector, dataset με ετικέτες (χωρίς κόστος AWS)

Στόχος: ένα αναπαραγώγιμο dataset (σύνολο δεδομένων) από alerts (ειδοποιήσεις προς διερεύνηση) με ground truth (βεβαιωμένη αλήθεια για κάθε περίπτωση), εκτελέσιμο τοπικά.

- [x] `src/market_sim/`: order book (βιβλίο εντολών) με προτεραιότητα τιμής-χρόνου, self-trade prevention (αποτροπή συναλλαγής ενός trader με τον εαυτό του), εντολές iceberg και pegged, BBO (best bid and offer, η καλύτερη τιμή αγοράς και πώλησης) πριν από κάθε γεγονός καταγεγραμμένο στη ροή των γεγονότων· πυρήνας διακριτών γεγονότων· αγορά υποβάθρου με 2 market makers, 12 noise traders, 3 value traders, ένα agency desk, ένα algo desk και 3 θεσμικούς αντισυμβαλλόμενους· `order_events`, `trades`, `traders`, `market_events`, `instrument_stats` ως parquet (στηλοειδής μορφή αρχείου δεδομένων). Μία ημέρα συνεδρίασης σε 0.6 s. (2026-11-02)
- [x] Εισαγωγή σεναρίων για όλα τα 6 S- και 9 F- σενάρια (`src/market_sim/scenarios.py`), καθένα επαληθευμένο ότι ενεργοποιεί τον detector· `manifest.json` (αρχείο περιγραφής περιεχομένου) με seed (αρχική τιμή της γεννήτριας τυχαίων αριθμών, για αναπαραγωγιμότητα), εκδόσεις γεννήτριας και detector, παραμέτρους, πλήθη. (2026-11-02)
- [x] `src/detector/`: ο «θορυβώδης» κανόνας με δύο triggers (συνθήκες ενεργοποίησης) για spoofing/layering (ψευδείς εντολές που τοποθετούνται για να ακυρωθούν, σε ένα ή σε πολλά επίπεδα τιμής) (`rule.py`, K ρυθμισμένο στο 3.25), απόδοση ετικετών (`labels.py`), threshold baseline (βασική γραμμή σύγκρισης με απλά κατώφλια) (`baseline.py`)· γράφει `alerts`. (2026-11-02)
- [x] `src/tools/discriminators.py`: 27 ντετερμινιστικά πεδία ως καθαρή συνάρτηση, με unit tests σε χειροποίητες ακολουθίες γεγονότων (ο ίδιος κώδικας που θα καλεί η Lambda). (2026-11-02)
- [x] Threshold baseline και τα αποτελέσματά του: ακατέργαστο safe close (ποσοστό ασφαλούς κλεισίματος) 96%, αλλά το gate (ο αυστηρός όρος αποδοχής) απέτυχε σε 6 από τα 7 alerts του S-SPOOF-5, άρα αναφέρεται n/a. Καταγράφηκε στο `data/synthetic/seed7/report.md`. (2026-11-02)
- [x] Έλεγχος με το χέρι 10-15 alerts μαζί με τον Γιώργο: 17 alerts σε τρεις γύρους (2026-11-02). Ο γύρος 1 βρήκε το F-SPOOFLIKE-HARD-1 να αγοράζει αντί να πουλάει και το `reversion_ticks` να μετρά την επίδραση της δικής του market εντολής του trader· ο γύρος 2 βρήκε το F-ICE-1 χωρίς εκτελέσεις στο iceberg και προφίλ desk με τυπικό μέγεθος που δεν ταίριαζε με τα quotes τους. Όλα διορθώθηκαν στη γεννήτρια ή στις μετρικές, οι ετικέτες αμετάβλητες. Ο γύρος 3 ξαναδιάβασε ένα alert από καθένα από τα πέντε σενάρια που άλλαξαν, στο ανακατασκευασμένο dataset: και τα πέντε ταιριάζουν με τις ετικέτες τους (έγγραφο δεδομένων, ενότητα 2.4).
- [x] Script αναπαραγωγής του βιβλίου εντολών (book replay) `scripts/replay_alert.py`: τα γεγονότα του trader γύρω από το παράθυρο με το BBO πριν από κάθε γεγονός, οι discriminators (διακριτικοί δείκτες), η απόφαση του baseline και (με `--reveal`) η ετικέτα. (2026-11-02)
- [x] 23 unit και end-to-end tests (`uv run pytest`)· `ruff check` και `ruff format` καθαρά.

Έξοδος (επιτεύχθηκε 2026-11-02): το `uv run scripts/build_dataset.py --seed 7 --sessions 20` παράγει 167 alerts σε 15 s (28 TRUE_ABUSE = 17%, 87 εισηγμένα false positives, δηλαδή ψευδώς θετικά, 52 alerts market maker υποβάθρου)· το recall (ανάκληση: ποσοστό της πραγματικής κατάχρησης που εντοπίζεται) του detector στην εισηγμένη κατάχρηση είναι 100%, το precision (ακρίβεια: ποσοστό των alerts που είναι πραγματική κατάχρηση) 17%· υπάρχει πίνακας αποτελεσμάτων του baseline και αποτυγχάνει στο gate μόνο στο S-SPOOF-5· 17 alerts ελέγχθηκαν με το χέρι σε τρεις γύρους.

Στιγμή demo: εμφάνιση ενός εισηγμένου spoof και ενός false positive (ψευδώς θετικού alert) από market maker δίπλα-δίπλα στο book replay.

## Φάση 2 - Back end και Gateway (μικρό κόστος AWS)

Στόχος: τα εργαλεία υπάρχουν ως Lambdas πίσω από ένα AgentCore Gateway με έλεγχο ταυτότητας Cognito, καλέσιμα από έναν MCP client (MCP: το πρωτόκολλο με το οποίο ο agent ανακαλύπτει και καλεί εργαλεία).

- [x] Εφαρμογή CDK στο `infra/` (`app.py`, `surv_firm/stack.py`, κάνει synth χωρίς σφάλματα): οκτώ πίνακες DynamoDB, bucket S3, μία Lambda για όλα τα tools του Gateway (`surv-gateway-tools`, Python 3.14 arm64, layer με pandas+numpy από το `infra/build_layer.sh`), η Lambda της ανθρώπινης διαδρομής πίσω από HTTP API με Cognito JWT authoriser, user pool με ομάδες L1/L2 και δύο χρήστες. Tags `Project` και `auto-remove=no` σε όλη την εφαρμογή.
- [x] Script φόρτωσης `scripts/load_dynamodb.py` (parquet του dataset -> DynamoDB· τα labels δεν φορτώνονται ποτέ· το dry run μετρά 1.961.720 items για το seed7). Η κατασκευή κλειδιών στο `src/tools/ddb_items.py`.
- [x] Tests: το `src/tools/tests/test_gateway_tools.py` τρέχει κάθε tool σε ένα DynamoDB του moto φορτωμένο μέσω του ίδιου `ddb_items`· οι discriminators που υπολογίζονται μέσω DynamoDB ισούνται με τις τιμές της πλευράς των labels για ένα alert πραγματικής κατάχρησης, και η διαδρομή πρότασης δεν θέτει ποτέ `recorded_disposition`. 30 tests περνούν.
- [x] `scripts/check_tags.py`: απαριθμεί κάθε πόρο του project (Tagging API και control plane του AgentCore) και σημειώνει όσους λείπει το `auto-remove=no`· το `--fix` τα προσθέτει.
- [x] `cdk bootstrap` και `cdk deploy SurvFirm` στο eu-west-2 (75 s, 44 πόροι)· κωδικοί Cognito ορισμένοι με `admin-set-user-password --permanent`, φυλάσσονται στο `~/.config/surv-investigator/`· το seed7 φορτώθηκε (1.961.720 items, ~12 λεπτά στα 2.500-3.500 items/s μετά από ανακάτεμα των items στα partitions του `by_date`).
- [x] Gateway `surv-investigator` μέσω `agentcore add gateway` + `agentcore add gateway-target` + `agentcore deploy` (stack `AgentCore-surv-default`)· το target `surv` είναι η Lambda με τα 11 inline σχήματα από το `surv-tools.json` (εξάγεται από το `src/tools/schema.py`)· εισερχόμενο `CUSTOM_JWT` με `allowedClients` = ο client του UI αναλυτή· ο ρόλος του Gateway μπορεί να καλέσει μόνο την `surv-gateway-tools`.
- [x] Smoke test `scripts/smoke_gateway.py` (MCP streamable HTTP, access token του Cognito ως L1): το `tools/list` επιστρέφει 11 tools `surv___*`· τα `get_alert`, `compute_discriminators` (3,6 s κρύα εκκίνηση), `get_trader_profile`, `get_instrument_stats`, `get_procedures` απαντούν όλα· οι 13 αριθμητικοί discriminators για το A-261006-0006 ισούνται με τις τιμές της πλευράς των labels· χωρίς token και με πλαστό token επιστρέφεται 401.
- [x] Όρια ρυθμού κλήσεων ανά χρήστη στο Gateway: `per-analyst-requests` (60/λεπτό στο `$.context.jwt.sub`) και `per-analyst-writes` (3/λεπτό ανά αναλυτή στα `propose_disposition` και `draft_stor_narrative`), δηλωμένα ως `CfnGatewayRateLimit` στο stack AgentCore. Επαληθεύτηκε: το `rate: 0` μπλοκάρει, το `toolName` και το `$.context.jwt.sub` επιλύονται και τα δύο, περιθώριο έκρηξης 15-20 κλήσεων μετρημένο στο 1/λεπτό (έγγραφο σχεδίασης, ενότητα 8).

Έξοδος: όλα τα εργαλεία ανάγνωσης και το `propose_disposition` καλέσιμα μέσω του Gateway· το `record_disposition` καλέσιμο μόνο από την ανθρώπινη διαδρομή.

Σημείωση κόστους (Pricing API, Europe (London), 2026-11-03): εγγραφές DynamoDB on-demand $0,7423 ανά εκατομμύριο WRU, αναγνώσεις $0,1487 ανά εκατομμύριο RRU, αποθήκευση $0,29715 ανά GB-μήνα μετά τα πρώτα 25 GB. Η φόρτωση του seed7 είναι περίπου 1,96 M items πλέον του αντιγράφου του ευρετηρίου `by_date` για 1,82 M γεγονότα εντολών, περίπου 3,9 M WRU, δηλαδή περίπου $3 εφάπαξ· η αποθήκευση είναι μέσα στα δωρεάν 25 GB. Lambda, Cognito Essentials και το HTTP API είναι εντός free tier σε όγκο demo. Η τιμολόγηση του Gateway πρέπει να ελεγχθεί στη σελίδα τιμολόγησης και να σημειωθεί στο `STATUS.md`.

## Φάση 3 - Agent στο Runtime (μικρό κόστος AWS)

Στόχος: ο agent Strands (το framework με το οποίο γράφεται ο agent) διερευνά ένα alert από την αρχή μέχρι το τέλος, πρώτα τοπικά και μετά στο Runtime.

- [x] `app/surv_investigator_l1/` (η σύμβαση του CLI, βλ. ημερολόγιο αποφάσεων): `report.py` (αυστηρό InvestigationReport), `prompt.py` (system prompt ως δεδομένα· οι διαδικασίες διαβάζονται με `get_procedures` στην αρχή κάθε εκτέλεσης, δεν ενσωματώνονται), `investigator.py` (agent Strands, `MCPClient` προς το Gateway με το token του αναλυτή, `SequentialToolExecutor`, hook `InvestigationGuard`), `main.py` (entrypoint του Runtime: payload `{alert_id, mode, instruction}`, token από την προωθημένη κεφαλίδα `Authorization`). 8 tests.
- [x] Τοπικές εκτελέσεις μέσω `scripts/investigate.py` (μοντέλο από αυτό το μηχάνημα, tools μέσω του αναπτυγμένου Gateway). Πρώτα τέσσερα alerts: A-261006-0006 S-SPOOF-1 -> ESCALATE (σωστό, Haiku και Sonnet)· A-261005-0002 market maker -> Haiku ESCALATE με 0,6 (ασφαλές αλλά λάθος), Sonnet CLOSE_FP με 0,72 (σωστό)· A-261006-0015 S-SPOOF-5 -> ESCALATE (σωστό: το alert που το threshold baseline έβγαζε λάθος)· A-261015-0008 F-NEWS-1 -> ESCALATE με 0,6 (ασφαλές αλλά λάθος: το μοντέλο είδε την είδηση 142 ms πριν το cancel και πάλι δεν έκλεισε). 27-57 s και 34-100k tokens εισόδου ανά διερεύνηση.
- [x] Deploy στο Runtime `surv_default_surv_investigator_l1` (direct code deploy, Python 3.14, `opentelemetry-instrument main.py`, εισερχόμενο CUSTOM_JWT με το pool των αναλυτών, `Authorization` στην allowlist). Το `scripts/invoke_runtime.py` το καλεί με απλό HTTPS και το token του αναλυτή: A-261006-0006 -> ESCALATE σε 35 s· η πρόταση φαίνεται μέσω του API της ανθρώπινης διαδρομής με τα πραγματικά `tool_calls`· token L1 που ζητά `stor_drafting` απορρίπτεται. 35 spans ανά εκτέλεση στο log group του Runtime (stream `spans`), κάθε κλήση tool δικό της span, `surv.alert_id` στα spans του agent.
- [ ] Ελάχιστο UI αναλυτή (Streamlit ή CLI): σύνδεση, ουρά, εκτέλεση διερεύνησης, προβολή έκθεσης και συνδέσμου προς το trace (ίχνος εκτέλεσης), καταγραφή disposition (απόφασης επί του alert) μέσω της ανθρώπινης διαδρομής.
- [ ] Εκτέλεση των τριών demo alerts (A, B, C) από την αρχή μέχρι το τέλος.

Έξοδος: τα βήματα 1-4 του demo δουλεύουν. Το session τερματίζεται μετά από κάθε εκτέλεση.

## Φάση 4 - Policy και Memory (μικρό κόστος AWS)

Στόχος: οι ντετερμινιστικοί έλεγχοι και ο βρόχος μάθησης.

- [ ] Policy Engine συνδεδεμένος στο Gateway σε κατάσταση `LOG_ONLY`· policies 01-08 ως αρχεία `.cedar`· ανάγνωση των logs αποφάσεων· μετάβαση σε `ACTIVE`.
- [ ] Το βήμα 5 του demo αναπαραγώγιμο: ένα prompt που προσπαθεί να παρακάμψει τη διαδικασία απορρίπτεται και ο agent ανακάμπτει.
- [ ] Πόρος Memory με το σχήμα namespaces· η ανθρώπινη διαδρομή γράφει γεγονότα disposition και ανατροφοδότηση· ο agent ανακτά μετά το `get_alert`.
- [ ] Εισαγωγή του εγγράφου διαδικασιών στο `/procedures`.
- [ ] Επανεκτέλεση του demo alert B για να φανεί το `memory_used`.
- [ ] Το βήμα 7 του demo αναπαραγώγιμο: καταγραφή override στο alert D ως L2 με σημείωση· το alert E (ίδιο desk, επόμενη μέρα) παραθέτει τη διόρθωση στο `memory_used` και προτείνει CLOSE_FP.

Έξοδος: τα βήματα 5-7 του demo δουλεύουν· τα logs αποφάσεων του Policy είναι ορατά· η επίδραση της memory και μια διόρθωση αναλυτή είναι ορατές σε μια έκθεση.

## Φάση 5 - Πλαίσιο αξιολόγησης και βρόχος μάθησης (μέτριο κόστος AWS: δύο ή τρεις πλήρεις εκτελέσεις του dataset σε μοντέλο κατηγορίας Sonnet)

Στόχος: ο πίνακας μετρικών, και αποδείξεις ότι ο agent βελτιώνεται με ελεγχόμενο τρόπο.

- [ ] `evals/run_dataset.py` σύμφωνα με την ενότητα 4 του εγγράφου δεδομένων· αρχεία ground truth παραγόμενα από τα `labels`.
- [ ] Προσαρμοσμένος evaluator (αξιολογητής) για το rubric (κλίμακα βαθμολόγησης με ρητά κριτήρια) της αιτιολόγησης.
- [ ] Πλήρης εκτέλεση στο σταθερό seed· αποτελέσματα και έκθεση παλινδρόμησης· σύγκριση με το threshold baseline και με το «κλιμάκωση όλων».
- [ ] Ανάλυση ανά σενάριο· διόρθωση του F-σεναρίου με τη χειρότερη αποτυχία μέσω αλλαγής εργαλείου ή prompt· επανεκτέλεση· καταγραφή της απόφασης προώθησης.
- [ ] Εκτέλεση με και χωρίς Memory για να ποσοτικοποιηθεί η επίδρασή της στο safe close rate, στο override rate, στα S-SPOOF-4 και F-MM-1 (έγγραφο δεδομένων, ενότητα 4.5.1).
- [ ] `evals/ingest_overrides.py`: τα overrides από τον πίνακα `cases` γίνονται επισημασμένες περιπτώσεις σημασμένες με την εκτέλεσή τους (ενότητα 4.5.2).
- [ ] Επανάληψη Optimization: configuration bundle v1 από το τρέχον prompt· πρόταση με στόχο τον evaluator του σκεπτικού· bundle v2· A/B v1 έναντι v2 μέσω του Gateway σε επανάληψη του dataset· κανόνας προώθησης offline· καταχώριση στο decision log (ενότητα 4.5.3).
- [ ] `src/detector/tune.py`: έκθεση επαναρύθμισης κατωφλίων, παλιά έναντι νέα (ενότητα 4.5.4). Εφαρμόζεται μόνο στο επόμενο build του dataset.
- [ ] Arm σύγκρισης μοντέλων: Opus 5.5 έναντι Sonnet 5.5 ως αλλαγή configuration bundle, ίδιο prompt και seed· gate, safe close rate, override rate στα δύσκολα σενάρια (F-SPOOFLIKE-HARD-1, S-SPOOF-3, S-SPOOF-4), rubric, κόστος και latency ανά alert· απόφαση προώθησης στο log (έγγραφο δεδομένων, ενότητα 4.3).

Έξοδος: ο πίνακας του βήματος 8 του demo υπάρχει με gate (αυστηρός όρος αποδοχής) = 0 missed και με τάση του override rate σε τουλάχιστον δύο εκτελέσεις· μία επανάληψη Optimization τεκμηριωμένη από την αρχή ως το τέλος. Αν το gate αποτύχει, ο πίνακας το λέει και το επόμενο βήμα είναι η διόρθωση, όχι η παρουσίαση.

Σημείωση κόστους: μία εκτέλεση ~150 alerts με 8-12 κλήσεις εργαλείων το καθένα σε μοντέλο κατηγορίας Sonnet είναι το μεγαλύτερο μεμονωμένο κόστος του έργου, και αυτή η φάση χρειάζεται δύο ή τρεις τέτοιες εκτελέσεις (baseline, Memory on/off, A/B). Εκτιμήστε το πριν την εκτέλεση και καταγράψτε το πραγματικό στο `STATUS.md`. Χρησιμοποιήστε μοντέλο κατηγορίας Haiku για τις επαναλήψεις.

## Φάση 6 - Παρουσίαση

- [ ] Διαφάνειες από τα έγγραφα: πρόβλημα (ενότητες 2-3 του primer), σχεδίαση (αρχιτεκτονική), demo, αξιολόγηση, ειλικρινείς περιορισμοί, επόμενα βήματα.
- [ ] Καρφίτσωμα ενός endpoint `demo` του Runtime στην αξιολογημένη έκδοση.
- [ ] Πρόβα του σεναρίου demo με χρονομέτρηση· προετοιμασία απαντήσεων στις αναμενόμενες ερωτήσεις.
- [ ] Ελληνική και αγγλική έκδοση της παρουσίασης, αν ο mentor προτιμά ελληνικά.

## Επεκτάσεις (μετά τη Φάση 6)

- Ροή υποβάθρου από ABIDES (ερευνητικός προσομοιωτής αγοράς με πολλούς agents) με τη δική μας εισαγωγή σεναρίων από πάνω.
- Agent αναθεωρητής L2 μέσω A2A (πρωτόκολλο επικοινωνίας agent προς agent) που αμφισβητεί την έκθεση του L1.
- Online αξιολόγηση σε ζωντανή κίνηση με δεύτερη επανάληψη Optimization.
- Λεπτό plug-in για sanctions (έλεγχο κυρώσεων) που επαναχρησιμοποιεί τον πυρήνα.

## Κανόνες κόστους (όλες οι φάσεις)

- Μόνο eu-west-2· tag `Project=agentcore-surveillance-investigator`.
- Τερματισμός των sessions του Runtime και του Code Interpreter μετά από κάθε εκτέλεση.
- Haiku 5.5 για ανάπτυξη· Sonnet 5.5 ως προεπιλεγμένος agent για demo και εκτελέσεις αξιολόγησης· Opus 5.5 μόνο για το arm σύγκρισης μοντέλων της Φάσης 5 και ως κριτής του σκεπτικού. Πρόχειρες τιμές λίστας: Haiku $0.10/$0.50, Sonnet $2/$10, Opus $4/$20 ανά εκατομμύριο tokens in/out, άρα μια εκτέλεση 150 alerts κοστίζει περίπου $22 σε Sonnet και $45 σε Opus [unverified against the Bedrock pricing page].
- Καταγραφή κάθε χρεώσιμου πόρου στο `STATUS.md` με σημείωση κόστους· διαγραφή όλων μετά την παρουσίαση, εκτός από τον κώδικα και τα έγγραφα.
