# 10 - Λειτουργία και βελτίωση του προϊόντος

Πώς τρέχει ο investigator μετά την alpha, πώς μια αλλαγή γίνεται release, τι παρακολουθούμε και πού βρίσκεται το μετρημένο περιθώριο βελτίωσης. Γράφτηκε 2026-11-08 με βάση το τότε promoted configuration (Runtime v12, run `20261106T1126-sonnet-v3`)· η ενότητα 5 ενημερώθηκε 2026-11-10 με το μετρημένο αποτέλεσμα του iteration 3 (Runtime v14, run `20261110T1833-sonnet-v4`). Οι αριθμοί προέρχονται από το `04-synthetic-data-and-evaluation.md` ενότητα 4.6 και από την ανάλυση spans στην ενότητα 4 παρακάτω.

## 1. Από την alpha στο pilot, με τη σειρά

1. **Παγώνουμε το regression set.** Το `seed7` (167 alerts) μένει ως έχει· κάθε αλλαγή συγκρίνεται με το τελευταίο promoted run πάνω σε αυτό. Έγινε 2026-11-11: δεύτερο set, `seed8` (seed 8, ημερομηνίες Νοεμβρίου, detector K = 4 από το tuning report, 100 alerts, φορτωμένο δίπλα στο seed7), πάνω στο οποίο δεν ρυθμίστηκε καμία configuration· η promoted configuration σε αυτό: gate 0 από 24, τα δέκα scenarios που ορίζει το standard 76 από 76, safe close 86.8% σε μίξη με 24% οριακές περιπτώσεις (92.7% επαναζυγισμένο στη μίξη του seed7), οι διαφωνίες στα ίδια τέσσερα αόριστα scenarios πλέον ένα F-RISK-1 (data doc 4.6). Το harness αρνείται promotion verdict ανάμεσα σε datasets· `--rescore` και `--resume` παίρνουν το dataset του ίδιου του run.
2. **Μετράμε το run-to-run variance.** Έγινε 2026-11-11 (`evals/run_dataset.py --repeat 5`, 21 alerts x 5, 34 λεπτά, $7.94· data doc 4.6): 18 από 21 alerts σταθερά, κανένα alert πραγματικής κατάχρησης δεν έκλεισε ποτέ, τα τρία ασταθή είναι ένα F-FAT-1, ένα F-NEWS-1 και το επίπεδο ESCALATE/DRAFT_STOR σε ένα S-LAYER-1, όλα σε confidence 0.60-0.72. Σε κλίμακα πλήρους συνόλου ο θόρυβος στο safe close rate είναι περίπου 0.9 μονάδες (μία τυπική απόκλιση), άρα η ανοχή δύο μονάδων του promotion rule είναι περίπου δύο τυπικές αποκλίσεις. Επαναλαμβάνεται μετά από κάθε αλλαγή στο standard ή στο model, γιατί ο θόρυβος κάθεται ακριβώς στα alerts που το standard αφήνει ανοιχτά.
3. **Αποφασίζουμε τα τρία ανοιχτά scenarios.** Το F-STOP-1 (0/6) είναι ερώτημα για το standard της firm, όχι για κώδικα: μια μονόπλευρη μεγάλη εντολή που ακυρώνεται μετά από ζημιογόνο exit κλείνει στο Level 1, δεδομένου του MAR Art. 15 για τις απόπειρες; Τα F-NEWS-1 (2/4) και S-SPOOF-2 (1/3) είναι υποψήφια για το iteration 3 (ενότητα 5).
4. **Pilot σε labelled alerts πελάτη.** Το harness τρέχει πάνω στα δεδομένα της firm με το δικό της procedure text· το gate είναι το acceptance criterion. Μέχρι τότε κάθε αριθμός είναι synthetic και το λέμε.
5. **Ρυθμίζουμε τα δύο production items** που έμειναν ανοιχτά στην alpha: retention στα log groups (πέντε χρόνια, ή export σε S3 με cold-storage lifecycle) και access control στα log groups ίσο με αυτό των tables (broker brief ενότητα 7).

## 2. Πώς μια αλλαγή γίνεται release

Ο promotion rule (data doc 4.4) είναι η διαδικασία· το Runtime endpoint alias είναι ο μηχανισμός release.

```
αλλαγή: tool field | πρόταση στο standard της firm | prompt | model | dependency
  -> pytest + ruff τοπικά (51 tests, ~30 s)
  -> deploy στο DEFAULT endpoint (το pinned alias δεν μετακινείται)
  -> evals/run_dataset.py στο frozen set, --compare με το τελευταίο promoted run (~1 h, ~$31)
  -> promotion rule: το gate κρατά· safe close όχι κάτω > 2 pts· faithfulness όχι κάτω·
     κανένα scenario που το προηγούμενο run έκλεινε >= 2 φορές και >= 25% δεν πέφτει στο 0%
  -> PASS: faithfulness (δωρεάν)· judged pass για ουσιαστικές αλλαγές (~$25)·
           εγγραφή στο decision-log· μετακίνηση του alias (demo / prod) στη νέα version
  -> FAIL: fix ή revert· το alias δεν μετακινήθηκε ποτέ, οι χρήστες δεν είδαν τίποτα
```

**Deploy δεν είναι release.** Κάθε `agentcore deploy` δημιουργεί νέα Runtime version πίσω από το `DEFAULT`. Release είναι η μετακίνηση του alias: ορίζουμε το `endpoints.<alias>.version` στο `agentcore/agentcore.json` και τρέχουμε `agentcore deploy`· rollback είναι η ίδια αλλαγή με το προηγούμενο N. Το `add runtime-endpoint` του CLI δημιουργεί alias και αρνείται υπάρχον όνομα (επαληθεύτηκε 2026-11-10 στη μετακίνηση του `demo` v12 -> v14), και το deploy που μετακινεί alias κόβει επίσης νέα version με αμετάβλητο κώδικα πίσω από το `DEFAULT`, άρα να περιμένεις το `DEFAULT` μία version μπροστά από το released alias. Χωρίς downtime, χωρίς αλλαγή κώδικα στο released alias μέχρι να το μετακινήσεις.

**Το standard της firm χρειάζεται την ίδια πειθαρχία.** Επειδή το `get_procedures` το διαβάζει σε run time, μια αλλαγή εφαρμόζεται στην επόμενη investigation χωρίς deploy. Η αλλαγή γίνεται σε staging table ή Memory namespace, τρέχει το harness, μετά promote· αλλιώς το compliance αλλάζει μια πρόταση την Τρίτη και το override rate κινείται την Τετάρτη χωρίς τίποτα στο log να λέει γιατί.

**Cadence.**

| Πότε | Τι |
|---|---|
| Ανά αλλαγή | harness στο frozen set, promotion rule, εγγραφή στο decision-log |
| Εβδομαδιαία | `evals/ingest_overrides.py` (τα overrides γίνονται test cases)· έλεγχος Policy denials ανά rule και του no-proposal count |
| Μηνιαία | judged pass (τάση rubric)· έλεγχος dependencies (το `agentcore/.cache/<runtime>/staging/*.dist-info` είναι αυτό που παίρνει πραγματικά το Runtime)· κόστος ανά alert |
| Τριμηνιαία | `python -m detector.tune` στα συσσωρευμένα labelled alerts· review του standard με το compliance· νέο model release αξιολογείται ως configuration bundle (το Opus arm είναι το template) |
| Μετά από αλλαγή στο standard ή στο model | variance run (`--repeat 5` στα οριακά alerts, ~$8): η ζώνη θορύβου κινείται ακριβώς με αυτά τα δύο, και η ανοχή προώθησης διαβάζεται απέναντί της |

## 3. Τι παρακολουθούμε

| Σήμα | Πηγή | Τι σημαίνει μια κίνηση |
|---|---|---|
| **Gate** (πραγματική abuse που προτάθηκε CLOSE_FP) | harness, ανά run | Οτιδήποτε πάνω από μηδέν δεν βγαίνει. Δεν υπάρχει online έκδοση· χρειάζεται labelled set. Κράτησε σε 6 πλήρη runs και σε όλες τις 35 επαναλήψεις πραγματικής κατάχρησης του variance run. |
| **Run-to-run θόρυβος** στο safe close rate | run με `--repeat`, μετά από αλλαγή στο standard ή στο model | Περίπου 0.9 μονάδες (μία sd) στις 2026-11-11. Διαφορά δύο runs κάτω από δύο μονάδες δεν είναι εύρημα· νέο ασταθές alert έξω από F-FAT-1 / F-NEWS-1 / F-STOP-1 / επίπεδο layering είναι. |
| **Override rate**, συνολικά και ανά scenario / desk / analyst | `surv-cases` (`override` flag), εβδομαδιαία | Ανεβαίνει: ο agent χειροτέρεψε ή εμφανίστηκε νέο pattern. Πολύ ανομοιόμορφο ανά analyst: κάποιος δεν διαβάζει, ή κάποιος εφαρμόζει διαφορετικό standard· και τα δύο είναι findings για το compliance. |
| **Safe close rate** | harness | Ο βασικός αριθμός, αναφέρεται μόνο μαζί με το gate. |
| **Evidence faithfulness** | `evals/faithfulness.py`, δωρεάν | Κάτω από 99%: άλλαξε το model ή τα tool outputs. |
| **No-proposal rate** | cases χωρίς `proposed_*` μετά από run | Πάνω από μηδέν: ο agent σταματά πριν προτείνει (το rejected recommendation το έκανε στο 100%). |
| **Guard rejections** | `rejections` στα responses | Λάθη σε ονόματα πεδίων (14% στο v3, ενότητα 4) κοστίζουν πλήρες rewrite του report το καθένα. |
| **Policy denials ανά rule** | Gateway log· metrics `AWS/Bedrock-AgentCore` | Πρέπει να είναι περίπου μηδέν για τον ίδιο τον agent. Ανεβαίνουν: το model άλλαξε συμπεριφορά, ή κάποιος καλεί το Gateway με δικό του client. |
| **Latency p50/p95, tokens, κόστος ανά alert** | harness, spans | Ανεβαίνουν χωρίς δική μας αλλαγή: νέο model snapshot πίσω από το inference profile, ή μεγαλύτερα tool outputs. |
| **429 / 424 / 5xx** | harness errors, Gateway log | Συστάδες: rate limits πολύ σφιχτά για την ομάδα, ή availability. |
| **Rubric mean και distribution** | judged pass, μηνιαία | Ποιότητα συλλογισμού. Πέφτει ενώ το agreement κρατά: τα reports αδυνατίζουν πριν από τις αποφάσεις. |
| **Memory size, extraction lag, recall latency** | Memory API, spans | Records που μεγαλώνουν χωρίς όριο: χρειάζεται TTL policy. |
| **Dependency drift** | staging dist-info σε κάθε deploy | Το Runtime bundle επιλύει διαφορετικές versions από το workstation (mcp 1.30 vs 2.3 έσπασε το v11). |

Δύο πράγματα μετατρέπουν αυτόν τον πίνακα από scripts σε operations: ένα **online evaluation config** (το rubric σε δείγμα 10-20% των live sessions, που δίνει την τάση ποιότητας χωρίς labelled set και είναι η προϋπόθεση για Gateway A/B test) και ένα **dashboard** με τις πρώτες πέντε γραμμές. Μέρες δουλειάς, όχι εβδομάδες· κανένα από τα δύο δεν είναι στην alpha.

## 4. Πού πάει ο χρόνος και τα tokens (μετρημένο, 2026-11-08)

Δύο v3 sessions, span προς span (`A-261006-0006`, spoof, 24 s· `A-261005-0003`, market maker, 38 s):

| Βήμα | Spoof | Market maker |
|---|---|---|
| model turn -> `get_alert` | 1.0 s | 1.0 s |
| model turn -> `get_procedures` + `recall_memory` | 1.7 s | 1.6 s |
| model turn -> τα έξι evidence tools, ζητούνται **σε ένα turn** | 3.0 s | 3.1 s |
| τα έξι tools, εκτελούνται sequentially | 1.3 s | 1.4 s |
| model turn: γράφει το report, καλεί `propose_disposition` | 11.7 s (1,875 out tokens) | 12.3 s |
| ο guard απορρίπτει το report (`ruled_out` αντί για `ruled_out_by`), το model το ξαναγράφει | - | **10.4 s** |
| model turn: τελική σύνοψη | 3.3 s | 4.3 s |
| **model / tools** | **20.7 s / 3.2 s** | **32.7 s / 4.8 s** |

Ευρήματα:

- **Ο χρόνος είναι στο model (85%), όχι στα tools (15%).** Το model ζητά ήδη και τα έξι evidence tools σε ένα turn· η concurrent εκτέλεσή τους αντί για sequential θα εξοικονομούσε περίπου ένα δευτερόλεπτο, όχι τα δέκα που εκτιμήθηκαν αρχικά.
- **Ένα λάθος σε όνομα πεδίου κοστίζει πλήρες rewrite στο 14% των sessions.** Σε 24 από τα 167 v3 sessions το model έγραψε `ruled_out` εκεί που το schema λέει `ruled_out_by`· ο guard απέρριψε το report και το model το έγραψε ξανά: +8.6 s και +32k input tokens σε αυτά τα sessions (μέσος όρος 35.7 s / 104k tokens έναντι 27.1 s / 72k χωρίς). Ένα schema alias που δέχεται και τα δύο ονόματα το εξαλείφει.
- **Τα input tokens είναι το ίδιο prefix που ξαναδιαβάζεται πέντε ή έξι φορές.** 77k input tokens ανά alert σε περίπου έξι model turns, το καθένα ξαναδιαβάζει το system prompt, τα tool definitions και όλα τα προηγούμενα αποτελέσματα. Το Bedrock prompt caching εφαρμόζεται: το Claude Sonnet 5.5 (και Haiku, Opus 5.5) υποστηρίζουν explicit caching στο Bedrock με ελάχιστο 512 tokens, τέσσερα checkpoints, TTL 5 λεπτών, σε `system`, `messages` και `tools`, πλέον "automatic caching" που μετακινεί ένα checkpoint προς τα εμπρός όσο μεγαλώνει η συνομιλία [Bedrock user guide, prompt caching, διαβάστηκε 2026-11-08]. Το Strands 1.63 το υλοποιεί με ένα argument, `BedrockModel(cache_config=CacheConfig(strategy="auto"))`, που βάζει cache points στο τέλος του system prompt, στα tools και στο τελευταίο user message. Εκτιμώμενο αποτέλεσμα: 55-65% λιγότερο input cost (τα cache reads σε κλάσμα της τιμής input· τα writes έχουν premium) και 2-4 s λιγότερο latency. Ένας κίνδυνος που μετριέται, δεν υποτίθεται: το `eu.` inference profile δρομολογεί σε επτά Regions και η cache ζει στον server που την έγραψε· ο user guide λέει ότι το cross-region inference "may lead to increased cache writes".
- **Το turn που γράφει το report είναι το μεγαλύτερο μεμονωμένο κόστος** (12 s, 1,800 output tokens με adaptive thinking). Ο μόνος μοχλός είναι το `effort` (medium -> low) ως configuration-bundle A/B, με το rubric να παρακολουθεί την ποιότητα.

## 5. Backlog, ομαδοποιημένο και με σειρά προτεραιότητας

**Iteration 3 (έγινε 2026-11-10, run `20261110T1833-sonnet-v4`, Runtime v14): latency και κόστος, χαμηλός κίνδυνος.** Εκτίμηση έναντι μέτρησης:

| Αλλαγή | Εκτίμηση | Μέτρηση (167 alerts, paired με v3) |
|---|---|---|
| Δίπλωμα του `ruled_out` στο `ruled_out_by` στο report model | -1.2 s μέσος όρος, -6% tokens, 14% λιγότερα guard rejections | rejections **24 -> 1** (το ένα που έμεινε είναι report σταλμένο ως string)· p95 38.0 -> 35.6 s· output tokens -8%· μέσος χρόνος αμετάβλητος |
| `CacheConfig` στο Bedrock model (system prompt, tools, τελευταίο user message) | -55-65% input cost, -2-4 s | **-51% κόστος model** ($31.26 -> $15.25· $0.187 -> $0.091 ανά alert)· 72.7% των prompt tokens από cache, 27.3% γραμμένα, 11 σε πλήρη τιμή· **0 s** εξοικονόμηση |
| `ConcurrentToolExecutor` για τα evidence tools | -1 s | δεν έγινε· το μετρημένο ταβάνι είναι ~1 s |
| `get_case_context` (alert + procedures + memory σε ένα tool) | -3 s, -8-15% tokens | δεν έγινε· design doc ενότητα 7 |
| `effort` low ως bundle | ίσως -5 s | έγινε ως iteration 4 (παρακάτω): **0 s**, -10% output tokens, 0 από 30 αποφάσεις άλλαξαν· το turn του report είναι γράψιμο, όχι σκέψη |

Τρία μαθήματα από τη μέτρηση. Η cache εξοικονομεί χρήματα, όχι χρόνο: το Bedrock εξακολουθεί να επεξεργάζεται το cached prefix, φθηνότερα, και ο χρόνος εξόδου του model είναι το latency. Ένα alias πεδίου σε model με `extra="forbid"` πρέπει να χειρίζεται το model να στέλνει **και τα δύο** ονόματα ταυτόχρονα (φάνηκε στο v13 στο πρώτο smoke test, κάτι που ένα απλό pydantic `AliasChoices` δεν καλύπτει· ένας `model_validator(mode="before")` το καλύπτει). Και το Bedrock αναφέρει `inputTokens` χωρίς τα cached tokens, άρα μια μετρική tokens ή κόστους που διαβάζει μόνο αυτό το πεδίο δείχνει πτώση 99.98%· το `metrics.py` προσθέτει πίσω τα `cacheReadInputTokens` και `cacheWriteInputTokens` ως `prompt_total`, και η γραμμή κόστους τιμολογεί τα reads στο 0.1x και τα writes στο 1.25x της τιμής input (συντηρητικά· η σελίδα τιμών ανακοίνωσε χαμηλότερη τιμή read για το Sonnet 5.5 από 2026-10-07 που δεν έχει ακόμη διαβαστεί από τη σελίδα). Τέσσερις από τις 167 dispositions κινήθηκαν (τρεις προς το label, μία μακριά), κάτι που καμία από τις δύο αλλαγές δεν μπορεί να προκαλέσει· το variance run την επόμενη μέρα (σημείο 2 στην ενότητα 1) μέτρησε αυτόν τον θόρυβο στις περίπου 0.9 μονάδες, και τα τέσσερα flips κάθονται μέσα του.

**Iteration 4 (2026-11-11): `effort` low, μετρήθηκε και απορρίφθηκε με $3.** Bundle `surv_effort_low` (το prompt του κώδικα, Sonnet 5.5, `effort: low`· `evals/bundles.json`), χωρίς deploy, slice 30 alerts στο Runtime έναντι των ίδιων 30 alerts του v4 (`evals/runs/compare-v4-effort-low.md`): **0 από 30 dispositions άλλαξαν**, p50 27.8 s έναντι 26.9 s, p95 30.5 έναντι 32.9, output tokens -10% (2,843 έναντι 3,172), κόστος -2%. Τα spans εξηγούν γιατί (`scripts/span_turns.py`, η ανά-turn εικόνα της ενότητας 4 ως εντολή): το turn του report είναι 9.6-10.9 s και 1,580-1,830 output tokens και στις δύο ρυθμίσεις, και το `gen_ai.choice` του φέρει 3,300-3,800 χαρακτήρες input του `propose_disposition` και κενό reasoning text. **Τα 10 δευτερόλεπτα είναι το model που γράφει το report, όχι που το σκέφτεται.** Το `effort` δεν έχει τίποτα να κόψει· το πλήρες run και το judged pass ($45) δεν ξοδεύτηκαν. Δύο συνέπειες. Ο μόνος μοχλός που μένει για το latency είναι το μέγεθος του report (εννέα evidence items, οκτώ explanations με verdicts και evidence ids, summary, window, what-would-change-my-mind), και αυτό είναι απόφαση προϊόντος για το compliance (P3, regulator-grade report), όχι ρύθμιση. Και το `effort` high είναι απίθανο να αγοράσει κάτι στις αποφάσεις: οι συστηματικές διαφωνίες είναι σταθερές με συνεπή συλλογισμό («το standard δεν μου δίνει λόγο να κλείσω»), και το Opus arm έκανε ήδη την πιο ακριβή έκδοση της ίδιας ερώτησης. Το ένα τεστ που θα μπορούσε ακόμη να δείξει κάτι είναι `effort` high στο υποσύνολο variance (21 x 5, ~$12): αν τα τρία ασταθή alerts γίνουν 5/5, περισσότερο thinking αγοράζει σταθερότητα και το κόστος του σε χρόνο μετριέται· αν όχι, το ερώτημα κλείνει. Backlog, όχι επόμενο.

**Ποιότητα αποφάσεων (μετρημένα κενά).**
- F-STOP-1 0/6: ερώτημα για το standard πρώτα. Αν "close", ένα πεδίο `loss_making_exit` (adverse move + αρνητικό round trip + χωρίς reversion, που υπάρχουν ξεχωριστά) και μια πρόταση· αν "escalate", αλλάζει το label.
- F-NEWS-1 2/4: ο agent δεν δέχεται «η πώληση ήταν hedge» χωρίς στοιχεία. Ένα πεδίο για τον χρόνο από την πώληση έως τα news, και το hedge ονομασμένο στο standard.
- S-SPOOF-2 1/3: το escalation standard λέει «επαναλαμβάνεται» χωρίς αριθμό· `repetitions_in_session >= 3` ρητά.
- Ποιότητα report (rubric 0.61): οι χαμηλότερες εξηγήσεις του judge είναι συγκεκριμένες (παράγωγοι χρόνοι λάθος, indicators που ταιριάζουν χαλαρά). Μια πρόταση στις οδηγίες του report: χρόνοι και διαφορές όπως τα επιστρέφουν τα tools.

**Resilience.** Το 429 retry είναι μέσα (v12). Επόμενο: Bedrock throttling και model timeouts, που δεν έχουν εμφανιστεί ακόμη σε αυτόν τον όγκο. Το harness τρέχει από laptop· για πελάτη γίνεται scheduled job στο account.

**Security.** Έγινε 2026-11-11: το `tests/test_agent_tools_boundary.py` ελέγχει ότι ο agent χτίζεται με ακριβώς μία πηγή tools (τον Gateway MCP client, με το bearer token του analyst και το policy session header), χωρίς direct tools, και χωρίς import βιβλιοθήκης tools ή HTTP client στο package του agent· αποτυγχάνει σε δεύτερο tool (ελέγχθηκε προσθέτοντας ένα). Είναι η προειδοποίηση του broker brief ενότητα 2b ως κώδικας. Ανοιχτό ακόμη: retention και log access (ενότητα 1, σημείο 5).

**Operations.** Online evaluation config και dashboard (ενότητα 3). Overnight pre-investigation ως επιλογή (product doc roadmap). Το UI είναι reference· ο πελάτης ενσωματώνει τις κλήσεις στο δικό του case tool.

**Scope.** Ένας δεύτερος τύπος abuse (wash trades ή marking the close): νέοι discriminators και παράγραφοι standard πάνω στην ίδια αρχιτεκτονική, που είναι η απόδειξη ότι αυτό είναι platform και όχι ένα scenario.

## 6. Τι δεν είναι αυτό το έγγραφο

Δεν είναι runbook για incidents (δεν έχει συμβεί κανένα πέρα από τα δύο που καταγράφει ο resume guide) και δεν είναι capacity plan: ένας analyst τρέχει δύο investigations ταυτόχρονα μέσα στα rate limits, και μια firm με μεγαλύτερη ουρά διαστασιολογεί τα limits και το Runtime από τον δικό της όγκο.
