# Team QuoteCraft: who owns what

EHL Grand Finale 2026 · Atira challenge "From RFQ to bid". Updated 10 Oct 2026, 20:58.

## Owners

| Role | Owner | Focus | Done when |
|---|---|---|---|
| Build lead + verification | Maria | Local runs, scoring against our reference answer, sandbox test runs, merging branches, OpenAI vs Qwen for fact extraction | A sandbox test run scores ≥ 60 in < 15 min |
| Builder 2: coverage | Puneetha | Why the bidder Q&A answers, the end reserves (technical release mail) and the metal index (price-index mail) stay unanswered; fixes in the prompts and `casefile.py` | All 5 positions priced in a local run |
| Builder 3: tests / QA | Vamshidhar | Calculator edge-case tests, the latent calculator bugs, the failing `test_browser_env` tests, fair-play check before every submit | Test suite green, latent bugs fixed |
| Pitch & story | Iga, Ravindra | Pitch skeleton, 2-minute story, likely jury questions; organiser questions (pitch format, submission cut-off time) | Draft ready for team review |

## Current priorities (19:15)

Baseline: **70.7** reproduced twice with the same answer (runs 8184b178, 3c3568bb); the same code also scored 29.1
(run 9c8fe292). So the work now is the last position **and** making good runs the normal case.

| # | What | Why | Owner |
|---|---|---|---|
| 1 | Position 01.01 omitted with "set size unknown" | ~28 points in the good runs (position 13 + total 5 + consistency 5 + index check 5) | 🟨 fixed by Vamshidhar in 2d96c95 (Q&A unit_is_set false positives); **Puneetha: verify, don't re-fix** |
| 2 | ~~Metal-index rate~~ → shared setup pool / bonus split in partial bids | The index was extracted correctly; the wrong surcharge came from the whole pool landing on the only priced member | ✅ Maria, d1db536 (option A: split over all known members) |
| 3 | Position 01.03 lead time 1 instead of 11 | Free stock was read from the physical total incl. blocked stock (95 instead of 29) | 🟨 fixed by Vamshidhar in 2d96c95 (free vs physical stock, with a code guard); pooled demand now counts all known positions (d1db536) |
| 4 | Submit agent stops right after the final submit click | After submitting, the run token is dead: the extra model calls fail and cost time | ✅ Maria, b7b4150 (confirmation read in code, no model turn after the click) |
| 5 | Reliability: one sandbox run at a time; repeat the same commit to measure variance | 70.7 vs 29.1 on the same code | Maria (coordination) |
| 6 | Calculator latent bugs, edge-case tests, leakage lint, fair-play checklist | Private-dataset safety, review safety | Vamshidhar |
| 7 | Pitch, cut-off time | | Iga, Ravindra |
| 8 | **ERP filing is the score driver**: ERP pages filed vs score on the same investigation code: 28 → 100 (2a95ffc9), 6 → 38.2 (2cdb6477), 2 → 10 (e3804980). Local tests start from a complete golden case file, so they never see this | Investigators must file every candidate (matching is code), and slow loops must be caught | 🟨 Maria, branch `maria/erp-loop-fixes` (8fda362): circle detection over 16 turns + investigator hint + "file every candidate" rule; 295 tests OK, golden exact; needs a sandbox run |
| 15 | **Routing fallback for a different split of facts** | v1's routing assumes materials in the ERP and keys in the mail; the private dataset may split them differently | 🟨 Maria, `maria/escalation` 279dad9: a routed question its agent left open (nothing still being read) is offered to every agent; 2 tests |
| 14 | **Bid form in fewer turns** (40-46 turns / 3.5-4.5 min in every clean 100) | The biggest fixed block of a run | 🟨 Maria, `maria/escalation` f1867df: a "steps" action does a whole form step across reloads in one turn, controls found by label, every step through the clerk's guard; 8 unit tests. Next: start agents during the context call (~25 s), file requirements first so ERP starts sooner (~30-60 s) |
| 13 | **Escalation for stuck agents** (separate branch `maria/escalation`, built on `maria/erp-loop-fixes`) | Gates, sliders, dead links cost minutes per run (25-29 turns on access checks, 134 clicks on one link). A model-driven second attempt instead of hard-coded rules | 🟨 Maria, ae31fb3: the 2nd time an agent circles it gets one turn with reasoning on and a screenshot, then idle as before; max 2 per agent; sanity plugin `escalation`; unit-tested, loop replay unchanged (18/18). Needs a real run to show its benefit. Optional next: OCR of scanned PDFs through the same multimodal model |
| 12 | **Browser failover** (8 of 36 runs: the clerk could not load the bid form; in 41a5de64, c3c4b1e8, 64397a5e the tender portal never loaded in its browser while the other browsers worked) | A dead tender portal at the end scores 0 whatever the bid | 🟨 Maria, branch `maria/erp-loop-fixes` 288c88c: from the 2nd renewal a tab moves to another browser and logs in again; unit-tested (302 OK); needs a sandbox run when the sandbox is healthy |
| 11 | **Idle investigators never woken** (run 024bd2ac: 15; same code scored 100 in fdb670b8) | An agent that goes idle while its questions are already open was never woken again | 🟨 Maria, branch `maria/erp-loop-fixes` 56c8b01, with a reproducing test (297 tests OK); needs a sandbox run |
| 10 | **Speed: stuck investigators** (100 run 74b22ceb took 19.3 of 20 min) | The tender-portal agent opened the same unchanged page 122× (~8 min); the investigation waits for every agent, so it ran to its time limit. Without the loop it would have ended around min 4-5 | 🟨 Maria, branch `maria/erp-loop-fixes` 76db483: a stuck investigator is sent idle (6 identical rounds, or circling after 2 hints) and woken by news; 296 tests OK; needs a sandbox run |
| 9 | Work on branches, not main | Pushing to main got in the way of the other builders | Everyone; merge to main only when agreed |

## Overfitting check: will it work on the private dataset? (11 Oct, unit tests only)

Every sandbox run (35) and the golden file are the public scenario, and the brief says the private dataset has
other websites, software, site names and content. "Golden check exact" only proves we did not break the public
case. What was checked on branch `maria/erp-loop-fixes` (not merged):

| Check | Result |
|---|---|
| Calculator rules on invented data | 148 rule-by-rule tests + a whole invented tender priced by hand, every field (`test_invented_tender.py`): **all match**. Low overfitting risk in pricing |
| Public names in the package | Only v1's question routing keyed on the site names "erp"/"mail". **Fixed (b9dddbb):** routing now uses the roles the model reads from the brief, names only as fallback; test with invented site names |
| Document formats (`test_document_formats.py`, invented files) | **5 of 7 failed:** XLSX rows lost, Office internals in the text, DOCX table cells run together, Windows-1252 CSV umlauts broken, file 3 archives deep not read. **Fixed (9c3081a)**, 7/7 pass |
| Still open | Scanned (image-only) PDFs: no OCR. Prompts and hints were written from public-scenario failures (no public values in them) |

## Where the cost goes (keep in mind for every change)

Measured on the branch's 100 run 2b8b5ca8 ($0.31): **199 calls sent 2.48 M input tokens, about 12,400 per call,
and only 36% were cached. Uncached input is about $0.24 of the $0.31; output is about $0.01.** Prices: input
$0.15/M, cached input $0.016/M, output $0.47/M.

So the cost is mostly every turn re-sending the whole page, the case file and the history, for every agent. Levers,
by expected payoff: (1) fewer turns (loops stopped), (2) smaller prompts (trim page text and history, show each
agent only its part of the case file), (3) more caching (keep the start of every prompt identical across turns),
(4) fewer agents (less fixed context per agent, but a more sequential, slower run). Measure locally before changing.

## Branch and bound, local (21:00 UTC, no sandbox runs while the organisers refresh)

**Bound 1: what decided each of the 29 sandbox runs** (`python tuning/run_report.py`): 8 clean, 4 agent loop,
4 website outage inside the sandbox, 13 model overload. All four fast 100s (9.6-10.8 min) are clean: the
investigation ended by itself in under 450 s and no agent repeated a thought more than 7 times. Many overload runs
also hide long loops (ERP 44x, 79x, 88x, 90x).

**Bound 2: replay of every recorded loop** (`python tuning/replay_loops.py <starter-kit dir>`): the 18 agent loops
from the logs are fed back into a code variant with a model that ignores every hint (worst case).

| Variant | Loops stopped | Loop turns allowed (of 1,259 recorded) |
|---|---|---|
| main 1fab415 | 3 / 18 | 1,116 |
| v1 (44a626ef, the promoted 9.6 min run) | 3 / 18 | 1,116 |
| **branch `maria/erp-loop-fixes` 5ee465a** | **18 / 18** | **158** |

v1 was fast because its routing prompt persuaded the model to stop, not because the code stops a loop. The branch
has v1's routing **and** the code that stops loops, and scored 100 in 10.3 min (2b8b5ca8). A new variant must
pass both bounds before it gets a sandbox run.

## The five 100 runs compared (20:20 UTC)

| Run | Who / code | Total | Investigation | Bid + TAN | Calls / cost | Model timeouts | Looping agent |
|---|---|---|---|---|---|---|---|
| 44a626ef | Vamshidhar, v1 | **9.6 min** | **319 s** | 254 s | 249 / $0.30 | 0 | none: every agent finished by itself |
| 2a95ffc9 | Vamshidhar, 2d330db | 12.4 min | 500 s | 243 s | 302 / $0.36 | 2 | none (erp 6×, mail 5×) |
| 39437db1 | Vamshidhar, a956103b | 15.3 min | 677 s (limit) | 239 s | 307 / $0.43 | 7 | tender portal 36× |
| fdb670b8 | Maria, branch c9186c3 | 16.2 min | 684 s (limit) | 289 s | 268 / $0.33 | 15 | tender portal 22×, never finished |
| 74b22ceb | Maria, main 1fab415 | 19.3 min | 676 s (limit) | 479 s | 394 / $0.47 | 0 | tender portal 122×, courier 10× |

**What decides the time is the investigation, and what decides the investigation is whether one agent loops.** Bid + TAN is
steady at ~4 min in every run except one (courier loop). The investigation waits for every agent, so a single looping
agent (almost always the tender portal, re-checking work it has already done) keeps it running to its ~680 s limit;
without a loop it ends after 5-8 min. Model timeouts add to it (more of them when many team runs are active).
So the speed work is: no agent may loop (branch `maria/erp-loop-fixes`: stuck agents are sent idle; v1's routing
tells agents to finish when their own questions are done).

## Score log (every sandbox run, newest first)

> ⚠️ **20:40-21:10 UTC: every run failed on infrastructure, whatever the code** (5 runs: Vamshidhar's 4 and Maria's 64397a5e, including the package that scored 100 at 20:24). Results from that window say nothing about the code.

> ⚠️ **Sandbox tender-portal outage (from ~20:00 UTC):** in c3c4b1e8, sub_e69b12d4 (bid entry) and sub_97fb152d the tender portal never loaded inside the sandbox (45 s timeouts, ERR_ABORTED), while the portals answered normally from outside and other runs at the same time reached them. Those 0s say nothing about the code. Worth reporting to the Atira organisers.


Updated after every run. Times in UTC (Berlin = UTC+2). Score = Atira's official quality (0-100).

**Who** = who started the run: only Maria and Vamshidhar run tests. Atira does not show it, so every run not started by Maria is Vamshidhar's.

| Started (UTC) | Run | Who | Code | Quality | Eligible | Time | Calls / cost | Main finding |
|---|---|---|---|---|---|---|---|---|
| 23:32 | run_9d813e7f (+3 more, one after another) | Maria | branch `maria/escalation` **a865a69** (= cc7f3f8 starter-kit): + routing fallback (279dad9), configurator cascade in one `steps` action and no clerk escalation (cc7f3f8) | running | | | | **Overnight reliability series** (`tuning/batch_runs.sh`, 4 test runs, never a submission). Results land in docs/runs/main_runs.tsv and are copied here afterwards |
| 23:13 | **run_bb0655a2** | Maria | branch `maria/escalation` **f1867df**: + "steps" action | **100** 🎉 | ✅ | 10.4 min | 237 / $0.26 | Clean: investigation 386 s, 0 timeouts. Clerk **37 turns / 241 s** (before: 40-46 / 207-284 s): it used `steps` 7× (bidder data, all amounts of each position, discount), all ran fine, but still did the configurator cascade (attribute → apply) one choice per turn. Next: have the cascade go into `steps` too. Side effect: the clerk got a "going in circles" hint while filling 5 similar positions (false positive) |
| 22:37 | **run_05d351d6** | Maria | branch `maria/escalation` **ae31fb3** | **100** 🎉 | ✅ | 11.7 min | 230 / $0.29 | Retry of 9f5d8f25. Clean: investigation 421 s, no open questions, 0 timeouts, longest repeat 4×. No agent got stuck, so **no escalated turn was needed**: this shows escalation does no harm, not yet what it adds |
| 22:37 | run_9f5d8f25 | Maria | branch `maria/escalation` **ae31fb3** | **– (platform failure, doesn't count)** | | 7.2 min | 80 / $0.07 | Atira: "The platform failed, not your agent system… started again automatically" |
| 22:48 | run_f2032d98 | Vamshidhar | ? | running | | | | |
| 22:37 | **run_67d30f66** | Maria | branch `maria/erp-loop-fixes` **9c3081a** | **100** 🎉 | ✅ | 12.5 min | 299 / $0.40 | Retry of 294db2ef. Clean: investigation 464 s, no open questions, 0 timeouts; one agent sent idle when stuck. **First sandbox 100 with role-based routing and Word/Excel/CSV reading** |
| 22:36 | run_294db2ef | Maria | branch `maria/erp-loop-fixes` **9c3081a** | **– (platform failure, doesn't count)** | | 7.5 min | 210 / $0.26 | Atira: "The platform failed, not your agent system". Until then strong: investigation ended by itself in **346 s with no open questions**, complete 5-position bid, halfway through the form |
| 22:33 | run_af92c314 | Vamshidhar | package 0cca498f | queued | | | | Automatic retry of 0634f300 |
| 22:33 | run_0634f300 | Vamshidhar | package 0cca498f | **– (platform failure, doesn't count)** | | | | Retried automatically |
| 21:59 | **sub_0af454da (SUBMISSION, Vamshidhar)** → run_0c9769e1 | Vamshidhar | `vamshidhar/reliable-calls` **on Maria's branch 288c88c** (browser failover) + uncommitted: 30 s call cap + backup request, changed-fact notice | **100** 🎉 | ✅ | **8.9 min** 🏆 | 239 / $0.33 | **Review passed ✅: the latest passed submission = our final package. Built on Maria's branch 288c88c.** Our fastest 100. Clean: investigation 295 s, 0 model timeouts, longest repeat 6× |
| 21:59 | run_c9f3431c | Vamshidhar | same as 0c9769e1 | – | | | 0 calls | **Platform failure** (Atira: "The platform failed, not your agent system"); does not count |
| 21:37 | **run_2807dc37** | Vamshidhar | package 2a5086da (no label) | **100** 🎉 | ✅ | 12.8 min | 205 / $0.27 | Clean: investigation 416 s, longest repeat 4×, 1 timeout |
| 21:36 | run_747dd4ad | Vamshidhar | package 2a5086da (same as 2807dc37) | **10** | ✅ | 15.3 min | 104 / $0.14 | **Outage**: 18 model calls without reply, 4 page loads timed out. Same package scored 100 a minute later |
| 20:53 | **sub_ce82715c (SUBMISSION, Vamshidhar)** → run_6baaba90 | Vamshidhar | **v1** (package 47e1f6ce, same as 44a626ef) | **100** 🎉 | ✅ | 11.0 min | 237 / $0.28 | Review **passed** ✅: the latest passed submission, i.e. **our final package**. **v1 reproduced: 2 of 2 clean runs at 100** (9.6 and 11.0 min) |
| 20:52 | run_143ae323 | Vamshidhar | package b760b15c (**same as his 100 submission 8618fad2**) | **10** | ✅ | 13.2 min | 117 / $0.12 | **Model overload**: 10 calls without reply, 3 pages not loading. Same package scored 100 at 20:24 |
| 20:50 | run_64397a5e | Maria | branch `maria/erp-loop-fixes` 9ba31c0 (same starter-kit as 5ee465a) | **0 (no answer)** | ❌ | 21.1 min | 51 / – | **Infrastructure, not code: the tender portal never loaded**, not even the first page (45 s timeout, reload ERR_ABORTED "frame was detached"), then 10 model calls without reply. The rest worked: customer portal filed revision + requirements in 60 s, mail filed discount + reserves; ERP correctly idle (material questions need the positions). Same tender-portal pattern as c3c4b1e8, 41a5de64 (v1!) and c4f64b7b; Vamshidhar's 6baaba90 at the same time was fine. Not a reproducibility result |
| 20:50 | run_c593918d | Vamshidhar | package bf40b0a3 | **0 (no answer)** | ❌ | 19.0 min | 48 / $0.04 | **Site outage**: 9 page loads timed out, 6 model calls without reply |
| 20:50 | run_cf7ab2ec | Vamshidhar | "5s navigation timeout refresh-reopen recovery" (d6998b83) | **0 (no answer)** | ❌ | 19.2 min | 125 / $0.14 | **Model overload**: 16 calls without reply |
| 20:41 | run_5f6f9d65 | Vamshidhar | package 05cf9d59 | **10** | ✅ | 13.7 min | 133 / $0.13 | **Model overload**: 13 calls without reply |
| 20:26 | **run_2b8b5ca8** | Maria | branch `maria/erp-loop-fixes` **5ee465a**: all fixes + v1's routing + goto hint, main's calculator | **100** 🎉 | ✅ | **10.3 min** | 244 / $0.31 | All 5 positions 13/13, signed. Investigation **402 s**, ended by itself with **no open questions**; longest repeat 7× (customer portal, then done); one agent sent idle when stuck; 0 model timeouts. **Fast like v1, with main's calculator guard: candidate for main** |
| ~20:30 (organisers) | **sub_2f274fd2 (SUBMISSION, promoted)** | Organisers | v1 test run 44a626ef | **100** 🎉 | ✅ | **9.6 min** | 249 / $0.30 | **Promoted by the organisers from test run 44a626ef** (after the sandbox outage). **Leaderboard: rank #3 → #4 by 22:00 UTC (another team passed us), 100, $0.30, 9:34** |
| 20:24 | **sub_8618fad2 (SUBMISSION, Vamshidhar)** → run_28a384ba | Vamshidhar | package b760b15c (no label) | **100** 🎉 | ✅ | **10.8 min** | 228 / $0.29 | Review **passed** ✅: the latest passed submission, i.e. **our final package now**. Vamshidhar: which code is it? |
| 20:23 | run_64e3f0cf | Vamshidhar | package c2d2ffe6 (no label) | **30.4** | ✅ | 13.4 min | 194 / $0.24 | |
| 20:03 | run_c3c4b1e8 | Maria | branch `maria/erp-loop-fixes` **c5a1733**: all fixes + v1's routing, main's calculator | **0 (failed, no answer)** | ❌ | 17.4 min | 95 / $0.11 | **The tender portal was unreachable inside the sandbox for the whole run** (every load hit the 45 s timeout, reloads aborted, fresh tabs too), so no positions and the clerk cannot reach the form. Not the agent logic: 0 model failures, no loops, investigation ended by itself at 622 s. Same portal hang as submission 2. The portals answer normally from outside. **Not a test of the fixes: rerun needed** |
| 20:11 | **sub_97fb152d (SUBMISSION 3)** → run_41a5de64 | Maria | **v1** exactly as it scored 100 in 9.6 min (44a626ef) | **0 (no answer)** | ❌ | 16.4 min | 86 / $0.08 | Review passed. **Tender portal unreachable inside the sandbox** (45 s timeouts, aborted loads; 0 model failures), so no positions and the clerk could not load the form. Mail, customer portal and ERP worked. Not v1's code. **v1 is now our final package** (latest submission that passed review); leaderboard keeps 38.2 |
| 20:06 | run_4b18d753 | Vamshidhar | package d6f25307 (no label) | **0 (no answer)** | ❌ | 25.0 min | 126 / $0.16 | **Model overload**: 11 model calls timed out, one clerk turn waited 248 s for the model, 1,775 s spent in only 137 calls. The investigation ran to its limit with most mail and material questions open; a partial bid (01.05 only) was worked out but the clerk got through only 6 steps of the form. Ran with 4-5 team runs active |
| 19:53 | run_39437db1 | Vamshidhar | package a956103b (no label) | **100** 🎉 | ✅ | 15.3 min | 307 / $0.43 | All 5 positions 13/13. Vamshidhar: which code is this? |
| 19:47 | **sub_e69b12d4 (SUBMISSION 2)** → run_c4f64b7b | Maria | **main 1fab415** (the 100 test run 74b22ceb, same checkout) | **0 (no answer)** | ❌ | 20.4 min | 218 / $0.25 | Review passed. **ERP agent looped 88× on "I need to wait for the specification…"** instead of going idle (no material filed, empty bid); then the tender portal hung (clicks over 45 s, reload aborted) and 10 model calls timed out (one clerk turn waited 247 s), so even the empty bid was never entered. Ran while 4 team runs were active. Both ERP failure modes are what `maria/erp-loop-fixes` targets |
| 19:45 | run_fdffdb58 | Vamshidhar | package 3f9ebd98 (58 files, no label; v1-like) | **10** | ✅ | 15.7 min | 329 / $0.39 | Signed, **empty bid**: the ERP agent **looped 134× on "click the F4 search link"** (the F4 link does not navigate; same trap as e3804980) and filed no material, so all 4 material questions stayed open. No model failures. Routing alone does not stop an ERP loop |
| 19:44 | run_0b6deda6 | Vamshidhar | `vamshidhar/changed-facts-and-language` on 4f3f572 + uncommitted changed-fact notice and language note | **44.9** | ✅ | 15.0 min | 166 / $0.20 | 01.01-01.03 priced (10.4/10.4/9.1), 01.04-01.05 missing: material A-4/A-5, data for HZ-2170 and the metal index still open. **9 model calls timed out** (1,809 s in calls for only 139 calls), so the investigation ran out of time |
| 19:43 | **run_44a626ef** | Vamshidhar | **v1** = local branch `codex/rfq-100-reliability` (58 files, not pushed): main + per-site question routing + label-based repeat detection, with an older calculator (no set-unit guard) | **100** 🎉 | ✅ | **9.6 min** 🏆 | 249 / $0.30 | **Our fastest 100.** Investigation took 319 s because every agent finished by itself (tender portal: done after 19 turns, "all remaining questions are for other websites"). In our slower 100s (74b22ceb, fdb670b8) the tender-portal agent never finished (122× the same page / 21× "Q&A complete, check page 7"), so the investigation ran to its limit (~680 s). The routing is what made every agent finish: ported to `maria/erp-loop-fixes` in c5a1733 |
| 19:32 | run_fdb670b8 | Maria (accidental 2nd run: a stopped runner was not fully killed) | branch `maria/erp-loop-fixes` c9186c3 (**same package hash as 024bd2ac**) | **100** 🎉 | ✅ | **16.2 min** | 268 / $0.33 | All 5 positions 13/13. **Same code scored 15 one minute earlier**: the difference is the idle-wake race below, which hit 024bd2ac and not this run |
| 19:31 | run_024bd2ac | Maria | branch `maria/erp-loop-fixes` c9186c3 | **15** | ✅ | 13.1 min | 110 / $0.13 | Signed, no positions. **Corrected diagnosis: our bug, not the model.** The requirements *were* filed (t+294-306), but the ERP agent had gone idle at t+301 "until the requirements are read" with its material questions already open. The idle hook woke agents only for questions *new* since they went idle, so it slept to the end. Fixed on the branch in 56c8b01 (wake when the awaited documents are read), with a test that reproduces it. Model timeouts (7× 120 s) made it slower but did not cause it |
| 19:20 | run_296397eb | Vamshidhar | package 1950838b (54 files) | 0 (failed) | ❌ | 19.8 min | 211 / $0.33 | No answer submitted. Who? Please add your name |
| 19:13 | run_74b22ceb | Maria | **main 1fab415** (= eb1a794 code: courier fixes, circle detection) | **100** 🎉 | ✅ | **19.3 min** ⚠️ | 394 / $0.47 | All 5 positions 13/13, signed. **The courier fixes saved it**: the first mail request came back without a code (123 s); on the second, the courier read the TAN, started re-verifying, and was **forced to finish by the circle detector** with the right code. But only 40 s to spare: investigation 676 s (tender portal 122 turns), clerk 352 s before asking for the TAN, two courier rounds ~4 min. **Speed is now the risk** |
| 18:55 | run_e3804980 | Maria | **main 33c04d7** (clean checkout) | **10** | ✅ | 13.1 min | 224 / $0.27 | Signed (TAN worked), but **empty bid**: the ERP agent filed only 2 pages. It searched blind for ~45 turns while waiting for the spec, then **rejected the right A-2 material for 46 turns** ("stroke 500, not 507": the customer portal's 507 predated the Q&A amendment; the case file said 500) and never filed it, so the calculator had nothing to match. Investigation code is identical to the 100 run (only submit.py differs): this is run-to-run variance. Fix on branch maria/erp-loop-fixes (8fda362) |
| 18:38 | **sub_4c6ef121 (SUBMISSION)** → run_2cdb6477 | Maria | **2d330db** (identical to the 100 package) | **38.2** | ✅ | 17.7 min | 435 / $0.69 | Review **passed** ✅. Same code as the 100 run, yet only 01.01 (10.4) and 01.05 (7.8) partly priced; 01.02-01.04 missing; total, consistency and index check 0. **100 vs 38.2 on identical code: reliability is the problem** |
| **18:18** | **run_2a95ffc9** | Vamshidhar | **2d330db** (main; verified file by file) | **100** 🎉 | ✅ | **12.4 min** | 302 / $0.36 | All 5 positions perfect, signed |
| 17:57 | run_73e5cf95 | Vamshidhar | pkg 2ede98ed | 0 (failed) | ❌ | 19.6 min | 254 / $0.31 | No answer submitted |
| 17:52 | run_7b2c0cf9 | Vamshidhar | pkg 363ab793 | – (cancelled) | ❌ | 7.6 min | 126 / $0.16 | Cancelled by Vamshidhar |
| 17:53 | run_a85be021 | Maria | main 7ef7411 (merge of the 98.7 branch + main's fixes) | **0 (unsigned)** | ❌ | 19.6 min | 269 / $0.37 | **The bid it entered scores 100/100 with the calibrated scorer** (all 5 positions incl. 01.03 lead time, total exact), but never signed: the courier rejected the real TAN mail because of a decoy "not sent" preview inside it, the clerk requested a second TAN (voids the first), deadline hit. Fixed in the next commit (courier judges by folder/header, no second TAN request before asking again) |
| 17:34 | run_faa680e1 | Vamshidhar | pkg 0a714bff | 0 (failed) | ❌ | 18.1 min | 219 / $0.45 | No answer submitted |
| 17:16 | run_1d8b1f72 | Vamshidhar | pkg 3e4e22e7 | – (failed) | ❌ | 19.7 min | 333 / $0.47 | No answer submitted within the time |
| **17:04** | **run_60233f96** | Vamshidhar | **b8f3228** (branch codex/robustness-runfix; verified file by file) | **98.7** 🎉 | ✅ | **10.1 min** | 245 / $0.33 | All 5 positions priced; only 01.03 lead time wrong (11.7/13). Total, index check, withdrawn check ✅ |
| 16:58 | run_23a00fcc | Vamshidhar | pkg 8f871985 | 22.8 | ✅ | 14.2 min | 229 / $0.38 | Only 01.01 partly priced (7.8); withdrawn check 0 |
| 16:26 | run_bde0fc31 | Vamshidhar | pkg ba54f05a | 27.8 | ✅ | 13.7 min | 316 / $0.58 | Only 01.05 priced |
| 15:55 | run_9c8fe292 | Vamshidhar | main 024f8b3 | 29.1 | ✅ | 13.9 min | 232 / $0.37 | Only 01.05 priced; whole setup pool on it (fixed in d1db536) |
| 15:55 | run_3c3568bb | Vamshidhar | main 024f8b3 | **70.7** | ✅ | 18.4 min | 278 / $0.38 | Same answer as run_8184b178 |
| 15:49 | run_8184b178 | Maria | main 030ccbc | **70.7** | ✅ | 16.6 min | 293 / $0.43 | 01.02, 01.04, 01.05 perfect; 01.03 lead time; 01.01 omitted ("set size unknown") |
| 15:31 | run_d38deaff | Vamshidhar | codex/robustness-validation | 10 | ✅ | 17.5 min | 436 / $0.61 | Supplier + ERP agents unfinished, empty bid |
| 15:20 | run_6da03229 | Maria | main 9106ce3 | 10 | ✅ | 13.4 min | 218 / $0.27 | First signed bid; tender tab broken, empty bid |
| 14:52 | run_54c78c38 | Maria | main aff64a9 | 0 | ❌ | 23 min | 355 / $0.55 | Never signed (courier on broken tab, investigation too long) |
| 14:31 | run_78004a51 | Maria | 7e7096b | – | ❌ | cancelled | 141 / $0.18 | Tender agent hung, run frozen |
| 12:20 | run_f06e3fcf | Vamshidhar | 37a4414 (script) | 100 | ✅ | 16 s | 0 / $0 | Fixed script, no model calls: **not submittable** (fair play) |

Leaderboard (19:00 UTC): isar-labs **100 in 6:22 / $0.09**, AdminRights 100 in 17:57, PolyETHylen 100 in 14:54, EliTUM 68.8. **Our first submission: 38.2.** Earlier (17:37 UTC): **isar-labs 100 in 7:19 min / $0.10**, AdminRights 100 in 17:57 / $0.24, Here for the Memes 53.8. Earlier leader: 21.5 (13:00, 14:34). **We have no submission yet.**

**Spread so far (model-directed agent):** **100** · 98.7 · 38.2 (submission) · 70.7 · 70.7 · 29.1 · 27.8 · 22.8 · 10 · 10 · 0 · 0 · 0 (failed/unsigned). Best and median are far apart.

**From now on:** `tuning/main_runner.sh` runs the current GitHub main in a clean checkout, one run at a time, and records each official result (docs/runs/main_runs.tsv), so reliability is measured per version, not just the best run.

**Local scorer:** calibrated on these official breakdowns, deviation 0.00 on all 8 scored runs (`tuning/calibrate.py`). Best and median are far apart: reliability is the main lever.

## Success levels

| Level | Criterion | Status (20:00) |
|---|---|---|
| 🟢 Minimum | Eligible signed bid (correct tender reference) on the public dataset | ✅ reached 17:34 (test run 6da03229: eligible, quality 10; the bid was signed but empty) |
| 🟡 Good | Quality ≥ 80 in a test run, run time < 12 min | ✅ **98.7 in 10.1 min** (run 60233f96, b8f3228), but not reliable yet (next runs 22.8, 0) |
| 🔵 Target | Quality ≥ 95, < 8 min, low cost (Qwen first), 3 test runs in a row without a crash | 🟨 **100** once (12.4 min) and 98.7 once; < 8 min not yet (board leader: 100 in 7:19); 3 in a row not yet |
| ⭐ Final-ready | Nothing layout-specific in the code; passes the AI review; clean README | 🟨 package scan clean before every test run; README describes the architecture; AI review not yet tried (no `atira submit` yet) |

## Milestones

Status: ⬜ open · 🟨 in progress · ✅ done · ⛔ blocked

| # | Milestone | Done when | Status |
|---|---|---|---|
| M0 | Setup | CLI, team, repo, Entire hooks, scouting of the four sites | ✅ |
| M1 | Walking skeleton | The agent logs into all 4 sites in parallel, reads the brief and **submits a signed bid** (even partial) in a test run, end to end | ✅ 17:34: signed and eligible in the sandbox (form ~2 min, signing code read in 8 s) |
| M2 | Facts collected | Every site agent files its facts into the case file; they match the facts checked by hand | 🟨 reached in run 60233f96 (all facts but the free stock behind one lead time); not yet in every run. Free stock and Q&A units fixed since (2d96c95, merged) |
| M3 | Calculator correct | All rules implemented and unit-tested; a complete bid from correct facts | ✅ 100/100 against our reference answer, also after every merge · latent edge cases open (Vamshidhar) |
| M4 | First full bid | Test run: quality ≥ 80, all positions filled, signed | ✅ 98.7: all 5 positions, signed (run 60233f96, 17:04 UTC) |
| M5 | Hardened | Quality ≥ 95, < 8 min, 3 clean runs in a row; time guard tested with a forced short deadline | 🟨 quality ≥ 95 once; robustness: timeouts, tab renewal, agent restart, coverage gate, evidence conflicts, sanity plugins. Open: reliability (3 in a row), speed (< 8 min) |
| M6 | Final freeze | Last `atira submit` passes review; README final; Entire checkpoints pushed; best-of-3 confirmed (already set) | 🟨 **first submission sent** (sub_4c6ef121 = 2d330db, measured 100), review pending; cut-off time still unknown |

## Timeline and approach (10 Oct, local time)

| Time | What happened | Lesson |
|---|---|---|
| 11:35–13:35 | Repo, Entire for all coding agents, starter kit, 4 browsers (Vamshidhar); scouting of all four sites (Maria) | Every site uses the same trap types: hidden decoys, invisible characters, popups, old records shown first |
| 14:00–14:20 | **Phase 1, brute force:** a fixed script scored 100 in a test run with **0 model calls** | Too easy to be allowed: fair play requires the model to decide. Never submitted |
| 15:05–15:34 | **Phase 2, model-directed refactor:** site agents + shared case file + deterministic calculator + submitter (Vamshidhar) | The architecture to build on |
| 15:30–16:20 | Reference answer computed twice (identical, later confirmed 100 by Atira); local scorer; calculator verified 100/100; local runs 25 → 15 → 30 | Measuring against a known answer turns guesses into a field-by-field to-do list |
| 16:00–16:20 | Fixes: mail access-check loop, failed extractions re-fileable, thinking off for navigation | Speed changes need a re-measure: one cut the extraction timeouts and lowered the score |
| 16:32 | Sandbox run 1: tender agent never took a step; run frozen; cancelled | One hung agent can freeze the whole run → timeouts everywhere |
| 16:52 | Sandbox run 2: quality 0, **never signed**: investigation used 14 min, the signing-code courier stuck on a broken tab | The form takes 2 min; time is lost before and after it → submit reserve, fresh courier tab |
| 17:21 | Sandbox run 3: **eligible, quality 10**, signed in 13.4 min, but **empty**: the tender tab failed for 10 min | A tab can break while the site is fine → automatic tab renewal |
| 17:30–17:50 | Validator, sanity plugins against invented values, Puneetha's Q&A fixes merged; a committed merge conflict found and repaired | Run every check after pulling, not only before |
| 17:31 | Vamshidhar's run of branch `codex/robustness-validation`: quality 10, 436 calls, 17.5 min (supplier and ERP agents unfinished, 0 positions priced) | Branch merged into main at 17:54 |
| **17:49** | **Sandbox run 4 (Puneetha's Q&A fixes + tab renewal + plugins, `030ccbc`): quality 70.7, eligible**, 16.6 min, $0.43. Positions 01.02, 01.04, 01.05 perfect, 01.03 one field off, 01.01 missing | The coverage fixes work; one position and the totals are what's left |
| 17:55 | Two sandbox runs of the new `main` started in parallel (Vamshidhar) | Parallel runs share the team's model limit and skew timing: **one test run at a time, coordinated by Maria** |

**Approach so far:** build the simplest end-to-end path first (signed bid), then measure every run against the known answer, fix the stage that loses the most points, and keep every fix generic, because the final runs on websites we have never seen.

## Pipeline stages

```
Brief -> 4 site agents in parallel -> case file (evidence) -> calculator -> validator -> submitter (+ TAN)
              page renderer + helpers                                         time guard
```

| Stage | Module | Done when | Status |
|---|---|---|---|
| Brief reader | `casefile.read_context` | Tender, scenario date, company, VAT id and authorised senders come from the run brief, never from code | ✅ |
| Page renderer | `browser_env.Tab.observe` | Pages read as a human sees them (labels, tooltips, collapsed sections, frames); hidden decoys and invisible characters dropped | ✅ all regression tests pass |
| Helpers | `browser_env`, `worker` actions | Popups, access checks (incl. several per page), errors, expired sessions, paging, file downloads, broken tabs | 🟨 access checks ✅, 45 s step timeouts ✅, tab renewal after 2 failed loads (new, under test) |
| Site agents | `agent.py` + `worker.Agent` | The model decides where to go; each agent finishes its site in < 5 min | 🟨 supplier, ERP, mail fast in the sandbox; tender portal unreliable; Q&A coverage fixes under test |
| Case file | `casefile.CaseFile` | Facts with provenance; exact reference, authorised sender, latest record no later than the scenario date | ✅ failed or empty extractions retried; Q&A cannot close without answers · open: ERP free stock, duplicate question ids |
| Calculator | `calculator.py` | All rules, Decimal, half-up, largest-remainder allocation; the model never does arithmetic | ✅ |
| Validator | `validate.check` | Schema, arithmetic, no extra or duplicate positions, bid / no_bid logic | ✅ (plugin `validator`) |
| Submitter | `submit.py` | Bid form filled from the brief's steps, TAN requested last, signed | ✅ signed in the sandbox (run 3); pre-submit review + typing guard added since |
| Time guard | `agent.py`, `worker.py` | A partial bid is still signed before 20 min | ✅ in practice: investigation stops with 8 min left; run 3 signed at 13.4 min · not yet tested with a forced short deadline |

## Sanity checks (plugins, `starter-kit/sanity.py`)

Plain-code checks against model hallucinations: no model calls, milliseconds of run time. Switch them per run with
`SANITY_CHECKS` (unset = every implemented check, `none`, or a comma list like `validator,typing_guard`), so the
same version can be compared with and without a check. The run log prints which checks are on.

| Plugin | Hooks into | Catches | Status |
|---|---|---|---|
| `validator` | the bid, before it is entered | duplicate or foreign positions, a total that is not the sum of the lines, broken lines | ✅ on |
| `typing_guard` | every value the bid clerk types | values from nowhere: an invented e-mail, a made-up price, a mistyped number | ✅ on |
| `no_guessed_mailbox` | bidder details for the clerk | an unknown mailbox address filled in by guessing | ✅ on |
| `coverage_gate` | before an agent closes a question | closing as absent after one search, or over a list stopped at its page limit | ✅ on (Vamshidhar) |
| `summary_check` | before the final signature | a review page that does not show reference, positions and total (waits, bounded; never blocks forever) | ✅ on (Vamshidhar) |
| `agent_restart` | an investigator that stops unfinished | step limit or loop while questions are open: one fresh restart (new tab, clean conversation) with ≥ 2 min left | ✅ on (32cd87e) |
| `grounding` | every extracted fact | numbers, keys and identifiers that do not occur as a whole token in the page they came from | ⚪ built, **off by default** until a run shows it helps (`SANITY_CHECKS=all`) |

Comparison runs (fill in): same commit, `SANITY_CHECKS=default` vs `none` → quality, time, blocked actions.

| Commit | Checks | Quality | Time | Blocked / repaired | Notes |
|---|---|---|---|---|---|
| | | | | | |

## Rules

- Branch off `main`, pull before you push, small commits, and put the measured effect in the commit message.
- **Nobody runs `atira submit` without Maria's go.** Our latest submission that passes review goes into the final, so no experimental submissions.
- **Only Maria starts sandbox test runs**, one at a time: all runs share the team's model limit (32 calls at once).
- Fair play: the model must choose navigation, searches and documents. No fixed click paths, no crawlers, and **no scenario values** (tender references, material numbers, keys, prices, logins) anywhere in `starter-kit/`, including tests and comments. Tests use invented values.
- Never `--no-verify`: Entire needs its git hooks to link sessions to commits. Start your coding agent inside the repo folder so its session is captured.

## Status

| Done | Next |
|---|---|
| Model-directed agent: site agents, shared case file, deterministic calculator, submitter | First sandbox test run of this version (running) |
| Calculator verified to the cent against our reference answer | First `atira submit` after the test run (go/no-go: Maria) |
| Mail access-check loop fixed; failed extractions are retried; timeout split for thinking / non-thinking calls | All 5 positions priced (Puneetha) |
| Local scorer and replay tool in `tuning/` | Edge-case tests and latent bugs (Vamshidhar) |
| Local runs: best 29.75 / 100 in ~14 min | OpenAI vs Qwen for extraction (Maria); pitch (Iga, Ravindra) |

## Useful commands

| What | Command |
|---|---|
| Free models locally (keep open) | `atira models proxy` |
| Scouting logins (PowerShell) | `atira scout --env \| Out-String \| Invoke-Expression` |
| Local run without submitting | `AGENT_SKIP_SUBMIT=1 HEADLESS=1 uv run --no-sync python agent.py` (in `starter-kit/`) |
| Save every agent turn / every filed page | `AGENT_TRACE=<dir>`, `AGENT_DOCS_DIR=<dir>` |
| Score an answer | `python tuning/scorer.py <answer.json> <reference.json>` (the reference answer is kept off the repo: ask Maria) |
| Tests | `uv run python -m unittest discover -s tests` (in `starter-kit/`) |
