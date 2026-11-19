# 12 - Presenter's guide

Written for George as the speaker: someone who knows AWS and his customers, and who has not worked in a compliance team. It gives the story in plain words, the little of the domain that is needed to tell it, what to show and what to say while showing it, the numbers to know by heart, the questions a mentor will ask with honest answers, and what not to claim. Everything here is taken from the other documents; where a number appears, the document that owns it is named. Written 2026-11-16.

## 1. The story in one minute

Say this first, in your own words.

Every broker has to watch its own order flow for market manipulation and report what looks suspicious. The watching is done by simple rules, and simple rules raise many alarms, most of them about perfectly normal trading. A trained person must still read every alarm and write down why it was closed, because the regulator can ask. That is slow, repetitive work, and the real case can be buried among the false ones.

This project is an AI analyst for that first reading. It takes one alarm, gathers the evidence the way a junior analyst would, writes the report, and proposes what to do. It cannot decide: a person reads the report and records the decision. The interesting part is not that an AI writes a report. It is that the platform, Amazon Bedrock AgentCore, lets a compliance team control what the AI may do, see everything it did, and prove it is still good after every change.

On a test set of 167 alarms, 28 of them real, it proposed to close about 95 of every 100 false alarms (133 of 139 in the latest run) and none of the real ones.

## 2. The domain, as much as you need

Seven ideas. If you can explain these to a friend, you can present the project.

| Idea | In plain words | Why it matters here |
|---|---|---|
| Order book | The exchange's list of everyone's offers to buy and to sell a share, sorted by price. The best buying price and the best selling price are called the touch. | Everything the agent looks at is a line in this list: an order placed, changed, cancelled or executed. |
| Spoofing | Showing a large order you never mean to trade, to make others think the price is about to move; trading the other way at the better price that results; then removing the large order. Layering is the same with several orders at several prices. | This is the one kind of abuse the project investigates. |
| False alarm (false positive) | An alarm about normal trading. A simple rule sees "large order, trade on the other side, cancel" and cannot tell a trick from a job. | Most alarms are false. Closing them correctly and quickly is the work. |
| Market maker | A firm that offers to buy and to sell all day and earns the small gap between the two prices. It cancels and replaces its offers thousands of times a day as the price moves. | The biggest source of false alarms. Its normal work looks like spoofing to a simple rule. |
| Level 1 and Level 2 | Level 1 is the analyst who reads every alarm first and closes it or passes it up. Level 2 is the senior person who investigates what was passed up and decides whether to report. | The agent does Level 1's reading. People at both levels keep the decisions. |
| STOR | Suspicious Transaction and Order Report: what a firm sends to its national regulator when it suspects abuse. | The agent can prepare the text of one for Level 2. Nothing is ever sent by the system. |
| The rule the firm is under | A firm must have systems to detect and report suspicious orders (Market Abuse Regulation, Regulation (EU) 596/2014, Art. 16(2)), with human analysis and records of why each alarm was or was not reported (Delegated Regulation (EU) 2016/957). | "Human analysis" is why the agent only proposes. "Records" is why every step it takes is kept. |

Two analogies that work with a non-specialist audience, to be given as analogies:

- Spoofing is like putting a "huge clearance, everything must go" sign in a shop window with no intention of selling, so that the shop next door drops its prices, buying from that shop, and taking the sign down.
- A market maker is the currency exchange booth at an airport: it will always buy and always sell, at two prices, and it changes the board all day. Nobody thinks the booth is cheating because the board changes.

What makes one alarm a false alarm and another a real case is in `01-domain-primer.md` section 2.3: eight ordinary behaviours that look like spoofing, each with how an analyst tells it apart. Read that table twice; it is the heart of the project.

## 3. What to show, and what to say while showing it

The full script with timings is `03-solution-design.md` section 12 (about 15 minutes). This table is the same demo as a speaker sees it.

| Step | What you do | What you say | What it proves |
|---|---|---|---|
| 1 | Log in to the analyst screen as the Level-1 user; open a day's queue. | "This is what an analyst sees in the morning: the alarms the detector raised overnight." | It is a real working queue, not a slide. |
| 2 | Open a real spoofing case and press Investigate. | "It reads the alarm, the firm's own written rules, the orders, the trader's profile, the news, and then writes." Read out one line of the report: the size of the order against the market, the trade the other way, the cancel a fraction of a second later. | The agent finds the pattern and explains it in the regulation's own terms. It proposes to escalate. |
| 3 | Open the trace of that run. | "Every step it took is recorded, and every number in the report can be found in what a tool returned." | Auditability: nothing in the report is the model's memory. |
| 4 | Open a market-maker alarm; Investigate; record the decision yourself with a note. | "It proposes to close, and says why. I record the decision. It cannot." | The human decides. |
| 5 | Open the news case, where the agent escalates and the analyst closes. Record the close with a note. | "Here I disagree with it. My correction is stored, and it is flagged as an override." | Disagreement is expected, recorded and measured. |
| 6 | Run the policy demonstration script. | "Now I try to make it cheat: propose before looking, propose after a lookup that failed, close without the history, propose twice. The platform refuses, and names the rule that refused." | The controls are outside the AI. It cannot talk its way past them. |
| 7 | Open a later alarm on the same desk. | "A week later, the same desk. It recalls my correction, checks it against today's orders, and proposes to close." | It learns from people, in the open. |
| 8 | Show the evaluation table. | The numbers of section 4. | It is measured, and it is measured again after every change. |
| 9 | Architecture and what comes next. | One sentence per AgentCore service: what objection of a compliance officer it answers (`09-product-decisions.md` section 4). | Why this platform. |

Since the changes of 2026-11-16 a decision is recorded once and the agent does not investigate an alarm that already has one. The alarms used in steps 4 and 5 were recorded during rehearsals, so they must be reopened before each run of the demo:

```
uv run scripts/reset_cases.py --alerts A-261005-0003 A-261016-0003 --include-recorded --apply
```

That gives two new things to show, if there is time: record a decision twice and see the second refused; log in as Level 2 and replace a decision with a reason, with the earlier decision still shown on the case.

## 4. The numbers to know by heart

All from run `20261118T1204-sonnet-v7`, the released version (Runtime v20, `v0.4.0-alpha`), unless said otherwise (`04-synthetic-data-and-evaluation.md` section 4.6; `STATUS.md`).

| Number | What it means | The caveat to say with it |
|---|---|---|
| 167 alarms, 28 real | The test set: 28 cases of real abuse that we injected, 139 false alarms. | The data is simulated. We know the truth because we wrote it. |
| 0 of 28 | Real cases the agent proposed to close. This is the gate: if it is not zero, nothing else is reported. | Held in every full run, eight so far, and in 105 repeated investigations of the real cases (35 on each of three versions, the released one included). It is a test result, not a guarantee. |
| 95.7% (133 of 139) | False alarms it proposed to close. | Four full runs in three days closed 131, 132, 133 and 131, the last two on the same version: the difference is inside the measured noise, so say "about 95 in 100". On a second, harder set it never saw (100 alarms), the released version closed 90.8% (69 of 76), with 0 of 24 real cases closed; an earlier version closed 88.2%, and the two alarms of difference are inside the noise. |
| 4.8% against 7.2% | How often a person would have to correct it, against the simple rules. | A second run of the same version gave 6.6%: the difference is three borderline alarms. The simple rules close about as many alarms, 133, and six of them are real spoofers. That is the comparison that matters. |
| 99.9% of 3,940 | Numbers in its reports that can be traced to a tool's output. | The four that cannot are two ratios and two time differences that it derived. |
| 25 seconds, about $0.09 | Time and model cost for one alarm. | List prices assumed for the model; see the cost note in `STATUS.md`. |
| 79.9% to 95.0% | How the close rate improved over four measured runs. The three runs since then (94.2%, 95.0%, 95.7%) each moved it by one alarm, with the gate held every time. | The improvement came from better numbers in the tools and clearer sentences in the firm's rules, not from prompt tricks. The last three steps were hardening, not tuning. |
| 12 of 12, and 12 of 12 | The market maker who really spoofs was escalated every time; his innocent twin, built to look the same, was closed every time. | A separate, focused set of 48 alarms, measured on the released version and on the one before with the same 48 answers. On the earlier version it was repeated three more times on the 24 alarms of the pair, with the same answer every time. The simple rules closed all twelve spoofers. Never mix these numbers into the 167-alarm figures. |

If you remember one sentence: "It closed about 95 of every 100 false alarms and none of the 28 real ones; the simple rules closed about as many false alarms and six real spoofers."

## 5. The words you will be asked about

| Word | One line |
|---|---|
| Alert | One alarm: one rule fired on one trader, one share, one short window of time. |
| Disposition | The decision on an alert: close as a false alarm, escalate to Level 2, or prepare a report. |
| Escalate | Pass the alert to the senior analyst. It is the safe answer when in doubt. |
| Override | The person recorded something other than what the agent proposed. |
| Gate | Our hard test: no real case may be proposed for closing. |
| Safe close rate | The share of false alarms the agent proposes to close, reported only when the gate holds. |
| Discriminators | The numbers that tell a trick from a job: how big the order was against the market, how far from the best price, how soon it was cancelled after the trade the other way, whether the price moved and came back. Computed by code, never by the model. |
| The firm's standard | The firm's own written rules for when an alarm may be closed. The agent reads them at every run and applies them. |
| Policy | The rules the platform enforces on every action of the agent, whatever the agent was told. |
| Trace | The complete record of one investigation: each step, each input, each output. |
| Memory | What analysts decided and wrote before, recalled at the next investigation. It informs; it never decides. |
| Proposal | What the agent writes. Only a person's decision closes anything. |

Longer definitions are in `glossary.md`.

## 6. Hard questions, honest answers

| Question | Answer |
|---|---|
| Is the data real? | No. It is a simulated market with cases we injected, which is the only way to know the truth for every alarm. The first run on a firm's own alarms is the test that counts, and the same harness runs it. |
| What stops it from closing a real case? | Nothing stops a wrong proposal; that is what the test measures and why a person decides. What stops it from recording a decision is that it has no such tool, the platform refuses any tool not on its list, the function behind its tools has no permission to write a decision, and the login it works under is not accepted by the system that records decisions. |
| Why an AI and not better rules? | We built the better rules too, as a comparison. They close a few more alarms and six real spoofers. Rules cannot weigh context or write the reasoning the regulator reads. The numbers still come from code; the AI sequences, interprets and writes. |
| Does it learn on its own? | No, and it must not. The model does not change. It recalls what analysts decided; its weak spots are measured; any change to its instructions is tested on the full set and released only if no real case is closed. |
| Is it the same every time? | No. We measured it, three times. On the released version: 22 alarms five times each, 17 always the same, and no real case ever closed. The ones that flip are the borderline false alarms, and two real layering cases that move between "escalate" and "prepare a report", never towards closing. Two full runs of the released version differ on 3 of 167 alarms. A difference under two points between two runs means nothing. Our own pass/fail rule tripped over this once: it failed the released version against itself, because one borderline group of six alarms closed two in the morning and none in the afternoon. The rule now judges a group only when the agent closes it nearly always, and the borderline groups are read from the repeat run. |
| Why does it send some harmless cases up? | Because in a short window a failed spoof and a trader cutting a loss look the same, and attempts are reportable (Market Abuse Regulation Art. 15). It errs on the safe side. Whether a firm wants those closed is the firm's rule to write. |
| Would a regulator accept it? | We do not claim that. The design is meant to be defensible: a person decides, every step is recorded, the records can be re-run. Whether a given regulator accepts reasoning drafted by an AI is the compliance officer's question. |
| Why AgentCore and not a Lambda calling a model? | Because the hard part is control, not text. One gateway every action passes through, rules enforced there, the analyst's identity on every call, a full trace, and a measured path for change. Each of those would otherwise be built by hand. |
| What is not built? | Charts in the report (Code Interpreter), live monitoring of quality and a dashboard, and a second kind of abuse. Say so before being asked. |
| What did a review find? | On 2026-11-16 the project was reviewed and hardened: a recorded decision could be silently overwritten, and the agent could write a new report under a closed case; both are now refused. The permission that keeps the agent from recording decisions moved from our code to the platform's access rules. And a harder case was added to the tests: a market maker who really does spoof. The full test set was then run again: no real case closed, and one alarm moved. On 2026-11-17 two more gaps were closed on the live system: a lookup that failed used to count as having looked, and the login the agent works under could have been used to record a decision. The platform now refuses both, and a sample of 29 alarms run afterwards gave the same proposal on every one. On 2026-11-18 the agent's software was locked to exact versions, so that what was measured is what runs, and the full test set was run again on it. The same day a rate limit that kept interrupting our test runs was traced to its cause: the test harness ran two investigations at once as one analyst, and the platform allows one analyst three proposals a minute. The limit stayed. The harness now uses one analyst for each investigation in flight, and the agent waits for the limit instead of failing. |
| What about that harder case? | The simple rules close it every time. The agent escalated it 12 times out of 12, and closed 12 out of 12 of an innocent twin we built to look the same: the same market maker placing an equally large order that really trades. It tells them apart from the record of that one order, not from who the trader is. We ran the pair three more times and the answer did not change once. It is twelve cases of each, and the plain form of the trick; say that too. |
| What does it cost to run? | About ten cents of model cost and half a minute per alarm; a thousand alarms a month is roughly a hundred dollars, plus a few dollars of platform. The saving is the analyst's time. |

## 7. What not to claim

- That it detects abuse. It investigates alarms a detector already raised.
- That it is approved by, or acceptable to, any regulator.
- That the numbers hold on real data. They are on simulated data, and that is said every time a number is shown.
- That it replaces the analyst. It replaces the gathering and the first draft; the decision and the signature stay with a person.
- That it never makes mistakes. It escalates some harmless cases, and its answer on a borderline case can differ between runs.
- Anything marked `[unverified]` in the documents: the United States references, the exact article numbers in Delegated Regulation (EU) 2016/957, and vendors' current features (`STATUS.md`, open verification items).

## 8. If something goes wrong on the day

| What happens | What to do | What to say |
|---|---|---|
| "This alert is decided" and no Investigate button | The alarm was recorded in a rehearsal. Run the reset command of section 3 and reload. | "A decision is written once. I have just shown you that by accident." |
| The screen opens on an empty queue | Today has no alarms in the test data: it is a weekend, or a day after 27 November 2026. Pick a day from the list; the demo's alarms are on October days. | "The screen opens on today, like a real queue. Our test data stops in November." |
| The agent proposes something different from the rehearsal | Carry on. | "It is not identical every time. We measured how often that happens and on which cases, and no real case was ever closed." |
| An investigation takes over a minute or fails | Open an alarm that already has a report, or the saved results in `evals/runs/`. | "One investigation is behaviour. The run over the whole set is the measurement." |
| The login fails | The passwords are in `~/.config/surv-investigator/analyst-credentials.env`, outside the repository. | Nothing; switch to the saved results while you fix it. |
| A question you cannot answer | Do not guess. | "I do not know; I will check it against the source." The project's rule is that every claim is verified. |

Keep the laptop open and on power during the demo and during any long run: closing the lid pauses everything.

## 9. Before the day

- Read `01-domain-primer.md` sections 2 and 3, and `08-broker-brief.md` sections 1 to 5. Two hours.
- Read three alarms by hand, to see what the agent sees: `uv run scripts/replay_alert.py data/synthetic/seed7 --random 3 --reveal`.
- Rehearse the demo once against the `demo` endpoint with a timer, then reset the demo alarms (section 3).
- Check `STATUS.md` for what is live on that day, and say which version you are showing.
- Decide in advance which two hard questions of section 6 you would rather raise yourself than be asked.

## 10. What is live and what is not

The numbers of section 4 belong to what is live: Runtime v20, behind both the `demo` and the `DEFAULT` endpoints since 2026-11-18 (`v0.4.0-alpha`), measured that day on the full test set (run `20261118T1204-sonnet-v7`); the demo's first alarm gave the demo script's proposal on it. v20 is the agent of `v0.3.0-alpha` (Runtime v17, 2026-11-16) with three hardening changes and no change to its instructions: its software is locked to exact versions, so that it can be rebuilt identically; its own check on evidence is as strict as the platform's; and it waits when the platform's rate limit pushes back, instead of failing. The released version was then measured a second time on the full test set, on 110 repeated investigations, and by the automatic judges (2026-11-18). The second, harder test set and the market maker who spoofs (a separate, focused set of 48 alarms, `seed9`; its numbers are quoted on their own) were measured on v17 and again on the released version on 2026-11-19 (runs `20261119T1101-seed8-v20` and `20261119T1125-seed9-v20`); only the three repetitions of the market-maker pair are from v17. On 2026-11-17 two control gaps were closed on the live system: the platform's rules now require each lookup to have answered for the alarm, and recording takes a login the agent never holds. `STATUS.md` says what is live on the day.
