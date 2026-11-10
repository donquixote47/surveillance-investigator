# 10 - Λειτουργία και βελτίωση του προϊόντος

Πώς τρέχει ο investigator μετά την alpha, πώς μια αλλαγή γίνεται release, τι παρακολουθούμε και πού βρίσκεται το μετρημένο περιθώριο βελτίωσης. Γράφτηκε 2026-11-08 με βάση το promoted configuration (Runtime v12, run `20261106T1126-sonnet-v3`). Οι αριθμοί προέρχονται από το `04-synthetic-data-and-evaluation.md` ενότητα 4.6 και από την ανάλυση spans στην ενότητα 4 παρακάτω.

## 1. Από την alpha στο pilot, με τη σειρά

1. **Παγώνουμε το regression set.** Το `seed7` (167 alerts) μένει ως έχει· κάθε αλλαγή συγκρίνεται με το τελευταίο promoted run πάνω σε αυτό. Φτιάχνουμε ένα δεύτερο set (`seed8`, detector K = 4 από το tuning report) πάνω στο οποίο δεν έχει γίνει tuning καμίας configuration, για να μετράμε generalisation και όχι μόνο regression.
2. **Μετράμε το run-to-run variance.** Το ίδιο alert πέντε φορές, για είκοσι alerts (δύο ώρες, περίπου $10). Ξέρουμε ότι ο agent δεν είναι deterministic (το alert E άλλαξε απάντηση από μέρα σε μέρα)· δεν ξέρουμε κατά πόσο. Χωρίς αυτόν τον αριθμό, μια διαφορά μίας ή δύο μονάδων μεταξύ runs δεν μπορεί να ονομαστεί αλλαγή.
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

**Deploy δεν είναι release.** Κάθε `agentcore deploy` δημιουργεί νέα Runtime version πίσω από το `DEFAULT`. Release είναι το `agentcore add runtime-endpoint --version N` στο alias· rollback είναι η ίδια εντολή με το προηγούμενο N. Χωρίς downtime, χωρίς redeploy.

**Το standard της firm χρειάζεται την ίδια πειθαρχία.** Επειδή το `get_procedures` το διαβάζει σε run time, μια αλλαγή εφαρμόζεται στην επόμενη investigation χωρίς deploy. Η αλλαγή γίνεται σε staging table ή Memory namespace, τρέχει το harness, μετά promote· αλλιώς το compliance αλλάζει μια πρόταση την Τρίτη και το override rate κινείται την Τετάρτη χωρίς τίποτα στο log να λέει γιατί.

**Cadence.**

| Πότε | Τι |
|---|---|
| Ανά αλλαγή | harness στο frozen set, promotion rule, εγγραφή στο decision-log |
| Εβδομαδιαία | `evals/ingest_overrides.py` (τα overrides γίνονται test cases)· έλεγχος Policy denials ανά rule και του no-proposal count |
| Μηνιαία | judged pass (τάση rubric)· έλεγχος dependencies (το `agentcore/.cache/<runtime>/staging/*.dist-info` είναι αυτό που παίρνει πραγματικά το Runtime)· κόστος ανά alert |
| Τριμηνιαία | `python -m detector.tune` στα συσσωρευμένα labelled alerts· review του standard με το compliance· νέο model release αξιολογείται ως configuration bundle (το Opus arm είναι το template) |

## 3. Τι παρακολουθούμε

| Σήμα | Πηγή | Τι σημαίνει μια κίνηση |
|---|---|---|
| **Gate** (πραγματική abuse που προτάθηκε CLOSE_FP) | harness, ανά run | Οτιδήποτε πάνω από μηδέν δεν βγαίνει. Δεν υπάρχει online έκδοση· χρειάζεται labelled set. |
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

**Iteration 3 (επόμενο): latency και κόστος, χαμηλός κίνδυνος.**

| Αλλαγή | Εκτιμώμενο όφελος | Κίνδυνος | Μετριέται με |
|---|---|---|---|
| Schema alias `ruled_out` -> `ruled_out_by` | -1.2 s μέσος όρος, -6% tokens, 14% λιγότερα guard rejections | κανένας | harness, πλήθος rejections |
| `cache_config=CacheConfig(strategy="auto")` | -55-65% input cost, -2-4 s | cache hit rate στο cross-region profile | harness· `cacheReadInputTokens` στα spans |
| `ConcurrentToolExecutor` για τα evidence tools | -1 s | temporal policies υπό concurrent requests | harness, Policy denials |
| `get_case_context` (alert + procedures + memory σε ένα tool) | -3 s, -8-15% tokens | χάνεται το στοχευμένο memory query του agent και ο ξεχωριστός διακόπτης memory | harness, memory on/off arm |
| `effort` low ως bundle | ίσως -5 s | ποιότητα report | rubric + harness |

Πλάνο: τα δύο πρώτα σε branch, slice 30 alerts τοπικά, μετά πλήρες run v4 υπό τον promotion rule.

**Ποιότητα αποφάσεων (μετρημένα κενά).**
- F-STOP-1 0/6: ερώτημα για το standard πρώτα. Αν "close", ένα πεδίο `loss_making_exit` (adverse move + αρνητικό round trip + χωρίς reversion, που υπάρχουν ξεχωριστά) και μια πρόταση· αν "escalate", αλλάζει το label.
- F-NEWS-1 2/4: ο agent δεν δέχεται «η πώληση ήταν hedge» χωρίς στοιχεία. Ένα πεδίο για τον χρόνο από την πώληση έως τα news, και το hedge ονομασμένο στο standard.
- S-SPOOF-2 1/3: το escalation standard λέει «επαναλαμβάνεται» χωρίς αριθμό· `repetitions_in_session >= 3` ρητά.
- Ποιότητα report (rubric 0.61): οι χαμηλότερες εξηγήσεις του judge είναι συγκεκριμένες (παράγωγοι χρόνοι λάθος, indicators που ταιριάζουν χαλαρά). Μια πρόταση στις οδηγίες του report: χρόνοι και διαφορές όπως τα επιστρέφουν τα tools.

**Resilience.** Το 429 retry είναι μέσα (v12). Επόμενο: Bedrock throttling και model timeouts, που δεν έχουν εμφανιστεί ακόμη σε αυτόν τον όγκο. Το harness τρέχει από laptop· για πελάτη γίνεται scheduled job στο account.

**Security.** Ένα unit test ότι τα tools του agent είναι ακριβώς ο ένας MCP client προς το Gateway και τίποτα άλλο: η προειδοποίηση του broker brief ενότητα 2b (ένα generic HTTP tool θα έδινε στον agent τη δυνατότητα να καταγράφει) ως κώδικας. Retention και log access (ενότητα 1, σημείο 5).

**Operations.** Online evaluation config και dashboard (ενότητα 3). Overnight pre-investigation ως επιλογή (product doc roadmap). Το UI είναι reference· ο πελάτης ενσωματώνει τις κλήσεις στο δικό του case tool.

**Scope.** Ένας δεύτερος τύπος abuse (wash trades ή marking the close): νέοι discriminators και παράγραφοι standard πάνω στην ίδια αρχιτεκτονική, που είναι η απόδειξη ότι αυτό είναι platform και όχι ένα scenario.

## 6. Τι δεν είναι αυτό το έγγραφο

Δεν είναι runbook για incidents (δεν έχει συμβεί κανένα πέρα από τα δύο που καταγράφει ο resume guide) και δεν είναι capacity plan: ένας analyst τρέχει δύο investigations ταυτόχρονα μέσα στα rate limits, και μια firm με μεγαλύτερη ουρά διαστασιολογεί τα limits και το Runtime από τον δικό της όγκο.
