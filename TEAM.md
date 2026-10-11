# Team QuoteCraft: who owns what

EHL Grand Finale 2026 · Atira challenge "From RFQ to bid". Updated 11 Oct 2026, 04:00 UTC (06:00 Berlin).

## Where we stand (11 Oct, after the sprints; scrum-master analysis 07:40 UTC + later results)

| | |
|---|---|
| **Final package** | still **sub_902fc357 = f851d41** (100 on public, $0.176, 6:15; leaderboard **#10**). It **scores 0 on eval B** (and its predecessor 0 on eval A). Resubmitting cannot cost rank (best submission holds the place); only the private run gains |
| **Best-tested candidates** | **8c44dad**: evals A 100/100, B 100/100, public 2/2 at 100. **ccf5612**: public 100/100 (6.5 and 8 min), eval A 100, eval B 0 = eval bug (TAN mail dated today) + clerk gaps, rerun on the fixed eval pending. **c47a3ce**: public 100 (10 min), eval A 100 |
| **Newest head** | `maria/cost` **991689d** = sprints A-E (ERP walk learning, paged filing + done gate, mail checklist, `path` action, context gates + token budget 1.1 M). In test |
| **Running sprints** | **F** mail coverage (every prescribed subject searched; mail questions routed firmly; FX early) · **G** clerk: skip the rest of a turn after a refused action, "submitted" only with the portal's confirmation, replay learns "no certificate" as a placeholder |
| **Test runs ordered** | public: ccf5612, 8c44dad, 991689d (one each, then a second each); evals: 991689d A/B, ccf5612 B on the fixed eval (variant B redeployed 11 Oct: TAN mail dated on the scenario date) |
| **Decision for Maria + Vamshidhar** | resubmit **8c44dad** now (insurance), then the best of ccf5612 / 991689d+F+G once proven (≥3 valid public runs with ≥2 at 100 and evals A and B at 100) |

### Status of the problems

| Problem | Status |
|---|---|
| Clerk loops on the bid form | ✅ closed in practice: 0 clerk misses in the runs since 8c44dad (form replay, stays-in-step, refused-button block) |
| Final package fails the evals | 🟥 code fixed (1d0ecea, 8c44dad), package not: needs a resubmit |
| Mail coverage (72e78b8e 42.1, 65a5d83b 38.2: Technikfreigabe/Devisenfixing never searched, reserve questions bounced) | 🟨 8d82ad6 (checklist) merged; Sprint F running |
| Paged spec, only the last page filed (dafda06b 29.1) | 🟨 28d06f9 merged, in test |
| Signing with an empty code / "submitted" without confirmation (eval B) | 🟨 Sprint G running |
| Tokens per run 1.6-2.1 M vs target 1.1 M | 🟨 991689d (gates + budget) in test; mail access check relocks (~23 mail turns, ~0.3 M tokens) and `path` unused (0×) are next |
| run_0eac78c0 "running" > 45 min | platform hang: report to the organisers |

### Backlog (scrum master, prioritised)

| P | Task | Done when |
|---|---|---|
| P0 | **Insurance resubmit 8c44dad** (Maria's go) | newer sub_ passed review is the latest |
| P0 | Merge F and G, test the head (public ×3, evals A/B) | ≥2 of 3 public at 100, A and B at 100 → **second resubmit** (Maria's go) |
| P1 | Process: find the cut-off time; last resubmit ≥ 60 min before the end; no test runs of eval-failing packages near the end (a promoted test run becomes the final); align with Vamshidhar (`opencode/batch-nudge` restores the f851d41 package) | rule agreed |
| P1 | README: current design and how each helper maps to rule 11 (elegance, AI review) | README updated |
| P1 | Mail access check relocking: fewer turns per unlock | mail ≤ 30 turns |
| P1 | Eval variant C: the full rule set on invented pages | candidate ≥ 90 |
| P1 | Pitch (Iga, Ravindra) | draft reviewed |
| P2 | Agents start during the context call; `FULL_TURNS=0` measured; OCR for scanned PDFs | measured |

### Do not redo (rejected, with reasons)
Global call cap (costs quality; the clerk turn reserve is the safe form) · ERP route compiler / local parsers (rule 11, other software) · code ranking and opening mails (the model must choose documents) · scripted submission state machine · the fixed script (37a4414) · model-written shorter brief (28% shorter, +12 s) · planning around prompt caching (unreliable) · one extraction call per domain (5% of tokens) · flat 8 s timeout · manual `fill_positions` relying on the model · resubmitting main (d72deb8) or the f851d41 line.

## Earlier overview (11 Oct, 04:00 UTC; superseded by the section above)

| | |
|---|---|
| **Final package** (latest passed submission) | **sub_902fc357** = test run a176359f promoted by the organisers = `maria/cost` **f851d41** (100 on public, $0.176, 6:15). Has the first eval fixes (f4e04d2, 568b228) but **not** d6d6979 (requirements without pressure are matched), the revision-id fix or the clerk turn reserve: its predecessor 8d1f0b5 scored 0 on eval A. **1d0ecea has all of them** |
| **Leaderboard** | **#7**, 100, $0.164, 8:21. Ranking between equal quality = **cost × time** (fits every pair on the board): we are at 1.37; #6 AdminRights 1.16, #5 EliTUM 1.11, #4 error404 0.83. The top three are at 0.03-0.25 |
| **Promotions** | The organisers promote our better test runs to submissions themselves (44a626ef, then 1b83cba3 + 9902e32b, then 4876a0ad). **A test run can become our final package**: only test code we would be happy to see in the final |
| **Branches** | `maria/escalation` (all robustness fixes + clerk fixes, last dba5e72) → `maria/cost` (+ cost cuts, last 8e19c98). Neither merged to main; main (d72deb8) has none of these fixes |
| **Winners** | Picked on the private dataset first, then public, then elegance. Robustness first, then cost × time |

### Evals (new, 11 Oct 04:40 UTC)

The organisers added **evals**: our own invented worlds (up to 4 sites, a brief, the one correct answer), hosted by
Atira, on which we can run new code **or our past submissions**. Their note: **"most teams regressed on quality on
the private dataset"**, so this is the closest we get to testing for it. CLI upgraded (`atira upgrade`).

| Eval | What | Runs |
|---|---|---|
| `quotecraft-variant-a` (ev_4e00776148892811, private; `evals/variant-a` on branch `maria/evals`) | The organisers' starter world: four simple sites, invented data, positions 10/20/30, fewer rules (no pressure, no catalogue group), a superseded spec revision, a quantity change **by mail**, a blocked material | **Final package: 0, 0. d9bb4e5: 0, 0.** All facts found, but the calculator matched **no material**: the spec states no pressure and `matches()` required equal pressure. Also the mail's quantity change was ignored (only Q&A counted) and a plain "Bestand 40 Stk" was not taken as free stock. **Fixed in f4e04d2** (escalation) / 8d1f0b5 (cost); 8d1f0b5 (first fix): **0, 0**: matching still skipped (see fix line); a7ed41c running → **a7ed41c: 100, 100** ✅ (2.4 and 4.1 min, $0.06-0.07); **1d0ecea: 100** ✅; **8c44dad (form replay): 100** (5.2 min, $0.07); **07e33b9: 0, timed out at 20 min** (no answer): the Qwen model did not answer 9 calls within 120 s (customer-portal 3, erp 1, submit 5: the clerk's first turn took 245 s), so the clerk was still on position 30 at the limit. Bid itself complete (3 positions). Mostly model latency, not logic; **d07e558: 100** (4.2 min, $0.08); **ccf5612: 100** (7.8 min, $0.08); **c47a3ce: 100** (3.4 min, $0.07); **991689d: 80** (3.3 min, $0.04): position 30 quantity 20 instead of the mail's change. With the lean prompts the mail agent ran only 6 turns: filed the discount and finished ("No open questions remain"), never opened the quantity-change mail; case file "Q&A answers on file: none", OPEN QUESTIONS LEFT: clarifications. 7 gate changes, no TOKEN BUDGET |
| `quotecraft-variant-b` (private; `evals/variant-b`) | Harder, in the private dataset's direction: other site names (`beschaffung`, `lieferantenportal`, `warenwirtschaft`, `postfach`), discount approval in the ERP (not mail), quantity change as an amendment notice on the buyer portal ("1.040 Stück"), ERP record over three tabs, a draft spec revision, reference with a slash (AZ-2027/0815), positions 1.1/1.2/2.1 | **Final package: 0.** Navigation was fine (all articles, the approval and the notice were found and filed in 149 s), but: (1) no pressure in the spec → no match (as A); (2) the change notice was filed among the revisions as "current" and **became the governing revision**; (3) its quantity change was lost; (4) the ERP's approval register was filed as mail and **extracted as nothing** (discount 0). **Fixed in 568b228** (escalation) / **f851d41** (cost). d9bb4e5 and 8d1f0b5 also running on it → d9bb4e5: 0, 0; 8d1f0b5: 0, 0; **a7ed41c: 0, 0** but closer (quantity 1.040 now right). Left: (1) revisions filed as "Revision 2", requirements as "2" → no governing requirements (**agent bug, fixing**); (2) the eval's brief has no scenario date, so the November approvals count as future-dated (**eval bug**, brief gets a scenario date); (3) one run hit the clerk's 120-step cap (fixed in b57394a) → **1d0ecea: 0, 0 but the agent's answer was exactly the expected one**: the eval site's sign step broke on the slash in the reference (URL-encoded), so no answer reached the platform (**eval bug**, reference changed to AZ-2027-0815, redeployed 05:27). Rerun on the fixed eval: **final package f851d41: 0**; **1d0ecea: 100, 100** ✅ (mean 7.8 min, $0.11); **8c44dad (form replay): 100** (4.8 min, $0.09); **07e33b9: 0** (7.3 min, $0.10): the ERP agent filed only the three Konditionen pages, never an article record or Bestand → no Material in the case file → all positions omitted, yet it reported done and no open question flagged it; **d07e558: 100** (7.1 min, $0.09); **ccf5612: 0, no answer** (6.3 min, $0.15): the investigation and the bid were complete (3 positions, total 110.033,60), but **signing failed**: (1) the eval's TAN mail is dated 11.10.2026 (real today) while the scenario and the other mails are Nov 2026, so the courier took it for an old TAN, never opened it and was forced to finish with an empty answer (twice, 15 turns each); (2) the clerk then typed the mail's *date* "11.10.2026" as TAN (blocked by the guard) **and the same turn's `finalize` still clicked "Angebot verbindlich abgeben"**; (3) code logged `submitted: true` although the page still showed step 8 with no "eingegangen" → run ended without an answer. d07e558's 100 on this eval was luck: its courier had opened the mail and its forced finish carried the code. Eval artefact (TAN date) + two code gaps (finalize after a blocked fill; submitted without confirmation); **c47a3ce: 0, no answer** (4.7 min, $0.08), same signing failure: the courier opened the TAN mail, again took it for old ("dated 11.10.2026 … seems old compared to the other emails (up to 5.11.2026)"), reloaded 13× and its forced finish **invented the answer "TAN-1"**; the clerk typed "TAN-1", finalize clicked, page stayed on step 8, code logged `submitted: true` → no answer. Bid itself complete again ; 991689d (old eval): 0 (TAN again). **Eval redeployed 08:05 (evv_260d0440, TAN mail on the scenario date)**: 991689d and ccf5612 rerun → **991689d: 0** (3.4 min, /usr/bin/bash.06): signing now works ("eingegangen"), but **the ERP agent quit at turn 2**: "There are no open questions assigned to me yet … [done]" (lean prompt, 2 calls, 6k tokens) → no articles, no stock, no prices, and the ERP's Freigaben (discount 4 %) never read; postfach searched 38 turns for a discount mail and closed it as absent → bid with no positions, discount 0. Regression of the context gates (749728f); ccf5612 rerun running |
| next: `variant-c` | Our hand-priced invented tender (`test_invented_tender.py`) as a world: the full rule set on new pages | ⬜ |

Commands: `atira eval run <slug> --package submission|test|<dir> --repeats 1-3`, `atira eval runs <slug>`.
Limits: 10 evals per team, 12 eval runs an hour; up to 12 test + eval runs at a time. Model calls are now ~2.2×
faster and up to 64 Qwen calls can run at once.

**Fix line for the evals:** f4e04d2 (pressure optional in matching, quantity change by mail, plain stock figure) → 568b228 (approval registers, change notices, governing revision) → **d6d6979** (a requirement without a pressure is matched at all: 8d1f0b5 still scored 0 on variant A because the calculator skipped such requirements as incomplete; with the fixes before it, quantity 20→24, stock and discount were already right) on `maria/escalation`; merged into `maria/cost` = **a7ed41c**. All tests pass (incl. an end-to-end test from filed facts to the bid), golden check exact. **a7ed41c running on variant A ×2 and variant B ×2 (05:02 UTC).**

**Since then:** a7ed41c scores **100 on variant A** (from 0) and 100 on public-1 (a176359f, f851d41). New: **b57394a** (cost) / clerk turn reserve on escalation. Next: revision-id normalisation + variant B brief with a scenario date, then both evals again. **Done (05:16 UTC):** revision ids compared loosely ("Revision 2" = "2"), commit ce0d803 on escalation, merged → `maria/cost` **1d0ecea**; variant B's brief got a scenario date (new eval version). Running: 1d0ecea on variant B ×2 and variant A ×1. **05:50 UTC: platform failure** took down every running run (public and eval); public runs were retried by Atira, the two eval runs of 8c44dad restarted by Maria (75e4eb18 on A, 4cfdb597 on B).

**Cost picture (11 Oct 06:30 UTC, leaderboard #9, $0.176 × 6:15):** in 472732d2 the fixed prompt part of every call (brief ~2.8k + instructions + actions ≈ 6k tokens) × 236 calls is **≈ 65% of all input**. So cost = calls × fixed prompt. Order: (1) confirm the automatic form replay (~−15%), (2) role-specific slimmer system prompts (~−20-30%), (3) ERP really using `file_each` with paths (~−10-20%). Target ≈ $0.08-0.10.

### Open problems

> 🚨 **P0 (11 Oct 04:50): on our own evals the final package scores 0** (variant A: 2 of 2; variant B: first run). Cause in A: public-1 assumptions in the matching and extraction (see Evals). The organisers say most teams regressed on the private dataset; this is likely ours. Fix f4e04d2 in test. **The final package should be replaced once the fixed code passes the evals and a sandbox run.**


| # | Problem | Status |
|---|---|---|
| P1 | **Clerk loops on the bid form** (d3ca14df, 8a2e1426, 012496d3: all 0). Root cause found: the `steps` chain reported the form's "position added" notice as an error, the clerk entered the position again, the form refused; the omit cap of fc54a43 then turned the refused omit into a loop | 🟨 dba5e72: notice reported neutrally, "a saved position may empty its fields: go on", one more omit after each circle hint. 3 sandbox runs running (7dbf1540, bf29711e, 608c82d7) |
| P2 | **Sandbox infrastructure**: tender-portal / mail outages, platform failures, model overload (8a2e1426 mail down, d8fdffff platform failure) | Not ours. Browser failover (288c88c) helps when only one browser is affected |
| P3 | **Cost**: ERP is 46% of all input tokens (828k of 1.8M in 4876a0ad, ~14k per call); prompt caching is unreliable (local probe: identical prompts mostly 0 cached) | 🟨 history cut done (9105e5e, $0.31 → $0.16); page-text trimming next |
| P4 | **Time**: investigation 220-370 s, form + TAN 160-280 s | ⬜ start agents during the context call, ERP sooner |
| P5 | Scanned PDFs (no OCR) on the private dataset | ⬜ optional |

### Next tasks

| Task | Owner | Status |
|---|---|---|
| Confirm the clerk fix dba5e72 in the sandbox (3 runs) | Maria | 🟨 running |
| Trimming: measured on local traces, the old history (not the page text) is what fills ERP calls → history cap 41cfde5, 2 sandbox runs | Maria | 🟨 running |
| Decide the final package: resubmit `maria/cost` with dba5e72 once confirmed (or let a promoted run replace it) | **Maria + Vamshidhar** | ⬜ needs the go |
| Speed: agents start during the context call; ERP starts sooner | Maria | ⬜ |
| Pitch: story of the architecture, the fair-play design, the cost × time work | Iga, Ravindra | ⬜ |

## Owners

| Role | Owner | Focus | Done when |
|---|---|---|---|
| Build lead + verification | Maria | Local runs, scoring against our reference answer, sandbox test runs, merging branches, OpenAI vs Qwen for fact extraction | A sandbox test run scores ≥ 60 in < 15 min |
| Builder 2: coverage | Puneetha | Why the bidder Q&A answers, the end reserves (technical release mail) and the metal index (price-index mail) stay unanswered; fixes in the prompts and `casefile.py` | All 5 positions priced in a local run |
| Builder 3: tests / QA | Vamshidhar | Calculator edge-case tests, the latent calculator bugs, the failing `test_browser_env` tests, fair-play check before every submit | Test suite green, latent bugs fixed |
| Pitch & story | Iga, Ravindra | Pitch skeleton, 2-minute story, likely jury questions; organiser questions (pitch format, submission cut-off time) | Draft ready for team review |

## Priorities (since 10 Oct 19:15; statuses updated 11 Oct 04:00 UTC)

| # | What | Status (11 Oct) |
|---|---|---|
| 22 | **Navigation circuit breaker** (78 s click, 45 s reads, 4 min mail recovery) | 🟨 Maria, `maria/escalation` a7d8e75 → `maria/cost` **5055459**: goto waits ≤ 8 s for the server to answer (one retry at once), ≤ 12 s for the page to build and counts a slow-building page as opened; page reads 20 s (was 45); a read timeout is recovered by code (address once more, then a fresh tab) before the model is asked; a failed goto counts twice toward a new tab. 6 tests. Local check on the real sites running |
| 21 | **Form replay** (clerk 35-100 turns, loops) | 🟨 Maria: 289d657 `fill_positions` (manual) → the model never called it (eval B, 10b8b777, 359201e8) → **automatic** (escalation 31e5feb / `maria/cost` **3fb4ac7**): when a `steps` chain has entered a position and the form moves on, code learns the template from it (typed values → placeholders; a value shared by two fields resolved by the model in one short call) and enters the remaining positions. 7 more tests (one model turn for three positions). Public runs of 3fb4ac7 running → 3fb4ac7: did not fire (clerk without steps) → **67fe67e: learns from any clerk action** (selects, fills, clicks, steps; labels read from the page), public runs running; **67fe67e: fired in both runs; e3b7aa43 clerk 9 turns** ✅ |
| 25 | **Clerk stays in step** (63f3be2e: wrong position's values, a refused button pressed 10×) | ✅ 07e33b9: every clerk turn names the position the form shows with its values; a button the form refuses twice in a step is blocked until the form moves on. 2 tests |
| 26 | **Slimmer prompts** (fixed prompt ≈ 65% of input) | ✅ 29f883f / 07e33b9: no credentials in any prompt; investigators without the brief's submission section and the steps action (~−600 tokens per investigator call). 4 tests |
| 23 | **A renewed tab reopens the page the agent was on** (not the home page; a person would reopen the same page) | ✅ escalation / `maria/cost` 67fe67e; home page only as fallback; another browser: home, login, back to the page. 3 tests |
| 24 | **Spec read page by page but only the last page filed** (dafda06b: 29.1) | ⬜ the `collect` of an embedded paged document stopped after page 1; the coverage gate did not catch the requirements question being closed with 4 of 5 missing |
| 20 | **file_each: fewer turns per record** (ERP 58-85 turns, ~12 per material) | 🟨 Maria, `maria/cost`: 020c64d (100, $0.26; used 4×, ERP unchanged) → 65d5b98 (links from the page the model saw) → 492399c (tabs as click paths) → d9bb4e5 (+ 47eb5ef); 2 runs of d9bb4e5 going |
| 19 | **History trimming** (measured: ERP pages are small, ~4.3k characters; old history is half of each ERP call) | 🟨 Maria, `maria/cost` 41cfde5: ERP calls ~25% smaller, but the two runs were not cheaper overall (more turns, slower investigation); keep watching |
| 18 | **Cost: one past page in full instead of two** (`FULL_TURNS`, `maria/cost` 9105e5e) + input tokens per agent in the run summary | ✅ $0.31 → **$0.16** at 100 (4876a0ad, promoted to sub_973a02b5). Brief guide tried and dropped (only 28% shorter, +12 s) |
| 17 | **Clerk omit cascade / omit loop** (8a2e1426, 012496d3) | 🟨 fc54a43 (start the stuck position over, omit cap) → dba5e72 (neutral notice, omit allowance per circle); in test |
| 10-16 | Stuck investigators, idle-wake, browser failover, escalation, `steps`, routing fallback | ✅ in the sandbox: `maria/escalation` scored 100 in 8 of 10 valid runs (both 0s were clerk loops, P1); fastest 6.3 min (9902e32b) |

Earlier list (10 Oct, 19:15):

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
| 16 | **Clerk must never loop to its step cap** (run d3ca14df: 0, never signed) | A signed partial bid keeps its points; an unsigned one scores 0 | 🟨 Maria, `maria/escalation` ed69d43: `steps` stops at a new error message after a press; the clerk escalates on a strict loop (not on the per-position pattern); its loop hint says fix the shown error or omit that position (rule 9) and sign. 3 tests. Loop replay: 18/19 (the clerk loop gets hints, a hint-ignoring model would still loop) |
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
| Changed-data review (11 Oct, night) | No public-scenario words in the package code or prompts (portal labels, rule names). Units outside the known list fall back to the model's own set/piece flag. Money values carry a format tag from extraction; German dimensions in amendments were already read correctly. **Found and fixed (dd8127d): a whole number written "1.250" or "1,250" (quantity, stroke, carton, weeks) was read as 1**; public-1 never had such values. Routing by role with a fallback when facts are split differently (279dad9) |
| Still open | Scanned (image-only) PDFs: no OCR. Prompts and hints were written from public-scenario failures (no public values in them) |

## External bottleneck review of f851d41, checked against our data (11 Oct, 05:40 UTC)

Checked on the good run a176359f (f851d41, now the final package): 100, 374 s, 192 calls, $0.176.

| Review's point | Our data | Verdict |
|---|---|---|
| Long navigation timeouts (45 s step, 20 s navigation) | Only 3 of ~180 actions took > 15 s (one 78 s tender-portal fill); long waits dominate only in sandbox outage runs | **Partly agree.** 8 s would also cut slow but working pages (10-20 s ERP loads seen). Test separately: e.g. 20 s per step + one quick tab renewal |
| Repeated extraction calls | 42 extract calls but 82k tokens = **5%** of input | **Low payoff**; one call per domain would also mix records (risk on private data) |
| Completed agents repeating "done" | 1-2 "done" per agent in the whole run | **Not supported by the data** |
| Sequential mail searches → one search + local filtering | Mail 25 turns, 290k tokens (18%) | **Reject the deterministic part** (fair play: the model chooses searches and documents). Rule-safe: one model search + `file_each` on the hits |
| Page-by-page ERP → deterministic loop with local parsing | ERP 46 turns, 466k tokens (**28%**, the largest share) | **Agree on the target, reject the method**: local parsers break on other ERP software. Rule-safe lever: get ERP to use `file_each` with paths (d9bb4e5+); it does not yet |
| Scripted submission | Clerk 36 turns, 361k tokens (22%) here; 16 turns in the best runs | **Reject scripting** (fair play, other bid forms). Lever: make the clerk use `steps` reliably (here it did not) |
| Global 10-12 call cap | Runs need 150-200 calls | **Reject**: cuts the investigation short, costs quality (first criterion, and the private run) |
| History cost | 10-turn cap active | Partly addressed; the bigger fixed block is the system prompt (~6k tokens per call) |

**What the review leaves out:** it covers cost and runtime only. The evals show the bigger risk is **quality on other
worlds**: f851d41 lacks d6d6979 (requirements without pressure: eval A 0 → 100), the revision-id fix and the clerk turn
reserve. The "11:11 rehearsal, $0.2507" is not one of Maria's runs (Vamshidhar's? please add it to the score log with
its package).

**Priorities from here:** (1) confirm 1d0ecea on both evals and public-1, then replace the final package (Maria +
Vamshidhar's go); (2) ERP `file_each` with paths and the clerk's `steps` used reliably (cost and time within fair play);
(3) timeout tuning as its own measured experiment.

### Second suggestion set: "deterministic fast path, LLM only for exceptions" (checked 11 Oct, 05:50 UTC)

The deciding rule is the brief's **rule 11**: *"A language model must choose navigation targets, searches and relevant
documents from observations at runtime and make the important decisions. Helpers **may** extract a selected page,
parse a selected document, paginate a model-selected result set, calculate, validate, retry and fill forms. They
**must not** autonomously discover and traverse the websites to assemble the complete task evidence before
model-directed investigation."* And: *"hardcoded answers, fixed scripts and crawlers are rejected"* by the review. The
private run uses **other software, layout, navigation and site names**.

| Suggestion | Allowed by rule 11? | Works on the private sites? | Verdict |
|---|---|---|---|
| Navigation circuit breaker (commit → selector → direct URL once → renew tab once) | Yes (retry) | Yes, if generic | **Do, measured.** We already renew tabs; add a short commit wait + one direct-URL retry. Not a flat 8 s |
| One extraction call per domain (collect, dedupe, batch) | Yes (extract selected pages) | Mostly | **Low payoff**: extraction is 5% of input tokens; batching mixes records and loses per-page provenance. Maybe later for time |
| Mail: one broad search, local index, code ranks and opens the winners | Search yes; **code choosing which messages count = "important decisions"** | Ranking rules are public-1 rules | **Partly**: the model makes one broad search and files the hits with `file_each` (allowed: model-selected result set). The authority ranking already runs in code *after* filing (calculator) |
| ERP route compiler (`/mm03`, `/vk13`, `/mmbe` loops, local table parsers) | **No**: fixed routes = fixed script / crawler | **No**: other ERP software | **Reject.** The allowed version is `file_each` with paths: the model walks one material, code replays the model's path for the others (492399c). Needs a prompt example so ERP actually uses it |
| Scripted submission state machine from bid JSON | "fill forms" is allowed, a fixed per-form state machine is not, and it breaks on another bid form | No | **Reject the fixed machine.** We have the allowed version: `steps` (label-addressed, every step through the guard) + validation before signing |
| Remove completed agents from the scheduler | Yes | Yes | **Not needed**: 1-2 "done" per agent per run (measured) |
| Global budget (25 calls, later 8-12) | Yes | n/a | **Reject the hard cap**: our runs need 150-200 calls; a cap cuts the investigation and loses quality (first criterion). The clerk turn reserve (b615337) is the safe form of a budget |
| State ledger + latest snapshot only | Yes | Yes | **Partly done**: the case file *is* the ledger; history capped at 10 turns. Next step possible: `FULL_TURNS=0` (only the newest page), measured |
| Model ladder (small model for routine steps) | Yes | Yes | **Not available**: only Qwen and Clef (Clef dearer per input token) |
| Stable-prefix caching | Yes | Yes | **Measured unreliable** on this provider (identical prompts mostly 0 cached); our prefixes are already stable |

**Bottom line:** the proposed target architecture (deterministic collectors → one planning call → scripted submission)
is what rule 11 forbids and what the private run would break. Our design is the allowed one: the model navigates and
chooses, helpers extract, paginate, replay a model-chosen path, calculate, validate and fill. **Next allowed levers:**
(1) ERP actually using `file_each` with paths, (2) the clerk using `steps` every time, (3) navigation circuit breaker,
each measured separately (quality, time, calls, uncached tokens, cost).

### Feedback on 1d0ecea (runs 1470dade: 100, 221 calls; 49f7be51: 0, 294 calls), checked 11 Oct 05:55 UTC

1d0ecea was the **generalisation** fix (evals A and B 0 → 100, public-1 100 in 2 of 3), not a cost change; the feedback
is about runtime and cost.

| Point | Where we are |
|---|---|
| Slow navigation / recovery (78 s click, 45 s reads, tab renewal) | **Agreed, next to build**: circuit breaker (short commit wait, one direct-URL retry, earlier tab renewal) |
| Mail / courier failed (4 min, no answer) | In 49f7be51 the **mail site failed in the sandbox** (ERR_ABORTED, 45 s reads). Circuit breaker + earlier courier tab renewal is our part |
| Submission model-directed, one failure | Failure = clerk add-line loop + mail outage. **8c44dad: form replay** (one position by hand, code fills the rest; ~35-100 → ~10 clerk turns, no loop). Running on public ×2 and both evals |
| ERP 60 calls | Agreed. `file_each` with paths exists but the model does not use it for ERP yet → worked example in the prompt next |
| Extraction 46 calls | One per distinct document; ~5% of tokens. Low priority |
| Repeated "done" | Measured 1-2 per agent per run: not a problem |
| Global 10-12 call cap | Not done on purpose: costs quality, fits only a scripted design rule 11 forbids; the clerk turn reserve is the safe form |
| History / 1.4 M tokens | Partly addressed; the big fixed block is the system prompt per call, so fewer calls (`file_each`, form replay) is the bigger lever |

## Where the cost goes (keep in mind for every change)

Measured on the branch's 100 run 2b8b5ca8 ($0.31): **199 calls sent 2.48 M input tokens, about 12,400 per call,
and only 36% were cached. Uncached input is about $0.24 of the $0.31; output is about $0.01.** Prices: input
$0.15/M, cached input $0.016/M, output $0.47/M.

So the cost is mostly every turn re-sending the whole page, the case file and the history, for every agent. Levers,
by expected payoff: (1) fewer turns (loops stopped), (2) smaller prompts (trim page text and history, show each
agent only its part of the case file), (3) more caching (keep the start of every prompt identical across turns),
(4) fewer agents (less fixed context per agent, but a more sequential, slower run). Measure locally before changing.

**Update 11 Oct, 04:00 UTC:**
- **Caching cannot be planned for.** Probe through the local proxy: the same prompt sent 4× in a row was cached 0, 0,
  5,888 and 1,600 tokens; a growing conversation hit only now and then. So lever (3) is out; only fewer input
  tokens count.
- **Ranking = cost × time** between equal quality, so 10% less cost is worth as much as 10% less time.
- **Measured per agent** (run summary now shows input tokens per caller; run 4876a0ad, 1.8 M input in all):
  ERP **828k (46%)**, mail 313k, tender portal 205k, customer portal 192k, clerk 165k, extraction only 76k,
  courier 13k. The brief is ~2.8k tokens per call (the investigators' system prompt ~6k in all).
- **Done:** one past page in full instead of two (9105e5e): **$0.31 → $0.16** at 100. Tried and dropped: a
  model-written shorter brief for the investigators (only 28% shorter, +12 s, risk of losing a rule).
- **Next:** trim the page text (ERP pages up to 14k characters per turn), then fewer ERP turns.

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
| 08:08 | run_fbaac569 | Maria | `maria/cost` **ccf5612** (rerun; named "maria/cost ccf5612") | running | | | | Comparison run (team lead) |
| 08:08 | run_680b48a9 | Maria | `8c44dad` (rerun of the 05:47 code: form replay `fill_positions`, before the clerk/mail/paging changes; named "maria/cost 8c44dad") | running | | | | Comparison run (team lead) |
| 08:01 | run_73af7b9c | Maria | `maria/cost` **991689d** (+ context gates: lean investigator prompts, more context only on trouble; token budget 1.1 M) | running | | | | Public check 2 |
| 08:01 | run_0cd32dc4 | Maria | `maria/cost` **991689d** (+ context gates: lean investigator prompts, more context only on trouble; token budget 1.1 M) | running | | | | Public check 1 |
| 07:45 | **run_10def205** | Vamshidhar | package a8cf1138 (no label) | **0** | ❌ | 15 min | 484 / $0.44 | No answer submitted (exited without submitting); customer-portal re-filed the spec 7× ("case file shows A-2 stroke as 482 but the document shows 489") |
| 07:44 | **run_ccf0bf4d** | Maria | `maria/cost` **c47a3ce** (+ investigators' `path` action: a label chain across page loads in one turn) | **100** | ✅ | 7.5 min | 186 / **$0.18** | Clean: clerk 16 turns, replay 3×; input 1.55 M (ERP 531k, mail 321k, tender 252k, customer 200k) |
| 07:32 | **run_6d30dbd4** | Maria | `maria/cost` **ccf5612** (+ mail checklist with subject word and sender; paged documents: file every page, collect past a dud control, no done while own question open) | **100** | ✅ | 8 min | 244 / $0.30 | All agents done on their own; clerk 20 turns, replay 4×. Mail 987k of 2.61 M input: ~23 of 68 mail turns spent re-unlocking the access check (slider + checkbox) that keeps relocking. Replay learned certification as the literal "Keine" (not `{certification}`) |
| 07:32 | **run_faa828e4** | Maria | `maria/cost` **c47a3ce** (+ investigators' `path` action: a label chain across page loads in one turn) | **100** | ✅ | 10 min | 264 / $0.32 | `path` action never used (0×). Replay after 01.04 learned certification as the literal "Keine" → stopped at 01.02 (EN 1493) after 7 of 29 steps; clerk then refilled 01.02 four times ("fields were cleared again", "Position hinzufügen keeps failing") until it pressed Weiter: clerk 30 turns. Mail 942k input |
| 07:31 | **run_38884a95** | Vamshidhar | package c2e031f3 (no label) | **0** | ❌ | 17 min | 395 / $0.50 | Investigation complete (no open questions), but the clerk hit its 120-step cap without a confirmation (at 120 it had entered 3 of 5 positions and was only requesting the TAN) |
| 07:25 | **run_74e84e70** | Maria | `maria/cost` **ccf5612** (+ mail checklist with subject word and sender; paged documents: file every page, collect past a dud control, no done while own question open) | **100** | ✅ | **6.5 min** | 225 / $0.26 | Clean: investigation 259 s, every agent done on its own (no loop stop), clerk 17 turns, replay fired 3×. Input 2.23 M: ERP 643k, mail 549k, tender 496k, customer 251k |
| 07:21 | **run_72e78b8e** | Maria | `maria/cost` **d07e558** (+ ERP record walk learned and offered as a ready `file_each`) | **42.1** | ✅ | 7 min | 234 / $0.24 | **Mail agent skipped Technikfreigabe and Devisenfixing** (two of the brief's six authorized subjects): it walked discount → Konditionsregeln → tariffs → Terminfreigabe → Rüstpools → Projektbonus → Preisindizes, then at mail 55 refused the open questions reserve:A-2/A-4 ("Technikfreigabe records from the customer-portal, not the mail site") and finished; ERP 65 bounced them back ("belong to the mail site"). No reserves → A-2 (482 usable travel) and A-4 (576) matched no material → 01.02-01.04 omitted; no FX either (no question was ever raised for FX-6282, since the USD materials were never selected). Also: mail lost 2 min to one 123 s model call (mail 14) and ~10 turns to the locked list. No site outage. Same code scored 100 in run_b7ec0ad8, where the mail agent filed Devisenfixing/Technikfreigabe in its first archive pass. Addressed by ccf5612 (mail checklist with subject word + sender), being tested |
| 07:15 | **run_b7ec0ad8** | Maria | `maria/cost` **d07e558** (+ ERP record walk learned and offered as a ready `file_each`) | **100** | ✅ | 8 min | 219 / $0.21 | Clean: all agents done on their own (no loop stop), clerk 21 turns, replay fired 3× (after 01.02, 01.05, 01.01). Input 1.83 M: ERP 594k, tender 358k, mail 265k, customer 262k, extract 112k |
| 05:36 | **run_76dc3099** | Maria | `maria/cost` **1d0ecea** (all eval fixes; named "maria/cost 1d0ecea") | **100** | ✅ | 8 min | 237 / $0.24 | Public check 4 |
| 06:57 | run_0eac78c0 | Maria | `maria/cost` **07e33b9** (+ clerk stays in step, slimmer prompts) | **still running after 38 min** (platform shows no end) | | | 334 / $0.36 so far | Investigation already weak: tender-portal `collect`ed the 6 Q&A pages twice but never filed them, then paged by hand (stopped at step 71; only answers 8149/8150/8154 filed → 01.01 qty 24, 01.05 110 pcs, no condition groups); mail stopped at step 122 (all records filed in the end). Fixed in ccf5612 (paged documents) |
| 06:56 | **run_65a5d83b** | Maria | `maria/cost` **07e33b9** (+ clerk stays in step, slimmer prompts) | **38.2** | ✅ | 10 min | 267 / $0.26 | **Mail agent loop**: searched only the archive (`VG-2027-7093 Rabatt`, never the inbox), then from turn 18 to 102 cycled keyword searches ("Freigabe", "Wochen", "TZ", "Zylinder"…, each "The search hint says delivery commitments need article numbers") until the repeat breaker stopped it at step 102 (mail 1.17 M of 2.43 M input). Never filed Terminfreigabe (TZ-*), Technikfreigabe (end reserves → A-2/A-4 usable travel) or Preisindizes (MET-4607) → 01.02-01.04 omitted (no material), 01.01/01.05 mispriced. Clerk 17 turns, replay fired after 01.05 |
| 06:29 | **run_e3b7aa43** | Maria | `maria/cost` **67fe67e** (+ replay learns from any clerk action; renewed tab reopens the same page) | **100** | ✅ | 14 min | 233 / $0.26 | **Replay worked: clerk 9 turns for the whole bid** (fired after 01.04, entered the rest). 14 min from a slow sandbox (53 s fills, 20 s reads) |
| 06:28 | **run_63f3be2e** | Maria | `maria/cost` **67fe67e** (+ replay learns from any clerk action; renewed tab reopens the same page) | **100** | ✅ | 11 min | 264 / $0.28 | Clerk 41 turns: it typed 01.01's values into the form showing 01.04, then pressed "Position hinzufügen" **10× (refused each time)** until escalation; the replay learned a polluted template and stopped safely. Signing clean. **Fixed in 07e33b9** (each turn names the shown position and its values; a button refused twice in a step is blocked) |
| 06:26 | **run_5af8899c** | Vamshidhar | package 6ed190b6 (no label) | **100** | ✅ | 11 min | 267 / $0.28 | |
| 06:13 | run_dafda06b | Maria | `maria/cost` **3fb4ac7** (= circuit breaker 5055459 + **automatic form replay**: after the first position, code learns the template and enters the rest without being asked) | **29.1** | ✅ | 9 min | 266 / $0.26 | Signed, but only 01.05 priced: the customer-portal agent paged the spec's embedded document page by page and read A-1…A-5, yet **filed only the last page** (A-5); `collect` had stopped after page 1 and nothing caught it (old weakness, not today's changes). Replay did not fire (no `steps`) |
| 06:12 | **run_472732d2** | Maria | `maria/cost` **3fb4ac7** (= circuit breaker 5055459 + **automatic form replay**: after the first position, code learns the template and enters the rest without being asked) | **100** | ✅ | **6 min** | 236 / $0.23 | **Replay did not fire**: the clerk used single selects/clicks, never `steps`, and the trigger listened only to `steps` (41 clerk turns) → fixed in 67fe67e. Input: ERP 665k, clerk 428k, mail 412k, tender 290k, customer 228k, extract 75k of 2.13 M |
| 05:48 | run_34a51556 → retry **run_359201e8** | Maria | `maria/cost` **8c44dad** (+ **form replay** `fill_positions`: one position by hand, code fills the rest) | **100** (retry) | ✅ | 12 min | 224 / $0.23 | Clerk 17 turns, **fill_positions never called** (steps per position) |
| 05:47 | run_4b369143 → retry **run_10b8b777** | Maria | `maria/cost` **8c44dad** (+ **form replay** `fill_positions`: one position by hand, code fills the rest) | **100** (retry) | ✅ | 9 min | 208 / $0.21 | Clerk 21 turns, **fill_positions never called**: the model does not use the replay by itself → made automatic in 3fb4ac7 |
| 05:36 | run_e585d778 → retry **run_415c1867** | Maria | `maria/cost` **1d0ecea** (all eval fixes; named "maria/cost 1d0ecea") | **100** (retry) | ✅ | 13 min | 231 / $0.24 | Public check 3 (e585d778 lost to the 05:50 platform failure). **1d0ecea: 4 of 5 valid public runs at 100** |
| 05:19 | **run_1470dade** | Maria | `maria/cost` **1d0ecea** (all eval fixes: pressure optional, mail quantity changes, plain stock, approval registers, change notices, revision ids; clerk turn reserve) | **100** | ✅ | ~12 min | 221 / $0.24 | Public check 2: no regression on public-1 |
| 05:12 | **run_f402181d** | Vamshidhar | package 35eb499d = `maria/escalation` **fc54a43** | **100** | ✅ | 10 min | 249 / $0.29 | |
| 04:55 | **sub_902fc357 (SUBMISSION, promoted by the organisers)** | Organisers | test run a176359f = `maria/cost` **f851d41** (package 2c82a7bf) | **100** | ✅ | 6:15 | 192 / $0.176 | **Now our final package.** Leaderboard: #7, $0.176, 6:15 |
| 05:19 | run_49f7be51 | Maria | `maria/cost` **1d0ecea** (all eval fixes: pressure optional, mail quantity changes, plain stock, approval registers, change notices, revision ids; clerk turn reserve) | **0 (never signed)** | ❌ | 20 min | 294 / $0.28 | Investigation fine (438 s). **Clerk loop on 01.02 again**: fill → "Position hinzufügen" → fields cleared → Weiter → "complete the configuration" → … ~90 turns; the new **turn reserve worked** (moved on at ~turn 95, TAN at turn 103), but then the **mail site failed in the sandbox** (45 s reads, ERR_ABORTED): the courier could not fetch the code twice (~140 s each), time ran out. Clean runs never press "Position hinzufügen" |
| 04:55 | **run_a176359f** | Maria | `maria/cost` **f851d41** (+ generalisation fixes from the evals: f4e04d2, 568b228) | **100** | ✅ | **6 min** | 192 / **$0.18** | No regression on public-1 from the eval fixes |
| 04:54 | run_15a3aaf9 | Maria | `maria/cost` **f851d41** (+ generalisation fixes from the evals: f4e04d2, 568b228) | **0 (never signed)** | ❌ | 11.5 min | 327 / $0.35 | Bid complete and correct (investigation 208 s), but the clerk cycled 4 steps on 01.02 (choose, fill, "Position hinzufügen", "not possible", Weiter, "complete the configuration") into its **120-step cap** before time was short. **Fixed in b57394a:** with 25 turns left the clerk is told to leave out what is not entered and sign |
| 04:33 | **run_33e5cab1** | Maria | `maria/cost` **d9bb4e5** (+ `file_each` tabs as click paths 492399c, links from the page the model saw 65d5b98, extra form position may be omitted 47eb5ef) | **100** | ✅ | ~10 min | 244 / $0.26 | |
| 04:32 | **run_19e4b85e** | Maria | `maria/cost` **d9bb4e5** (+ `file_each` tabs as click paths 492399c, links from the page the model saw 65d5b98, extra form position may be omitted 47eb5ef) | **100** | ✅ | ~11 min | 224 / $0.23 | After the Atira restart (503s 04:30) |
| 04:29 | run_b7dcf384 → retry run_a5fca6aa | Vamshidhar | package 4c39b4d5 "fast-parallel 03f9ce1: 5 ERP + 5 mail tabs, mail records ahead, ends when nothing open (on maria/cost)" | b7dcf384: **– (platform failure)**; retry running | | | | Atira restarted it automatically |
| 04:23 | run_dbdb6d49 | Maria | `maria/cost` **020c64d** (+ `file_each`: the model names several records of a list, code opens and files each and its tabs) | **– (platform failure, doesn't count)** | | 8.2 min | 214 / $0.23 | Atira restarted (503s from ~04:30) |
| 04:20 | **run_91982a40** | Maria | `maria/cost` **020c64d** (+ `file_each`: the model names several records of a list, code opens and files each and its tabs) | **100** | ✅ | 8.2 min | 273 / $0.26 | file_each used 4×, but ERP still 64 turns (its facts sit behind click paths → 492399c). Clerk did not use `steps` this time: 40 turns (one choice per turn), form fine in 132 s but 416k tokens. Input per agent: ERP 781k, mail 467k, clerk 416k, customer portal 336k, tender portal 284k |
| 04:05 | run_9ac58b69 | Maria | `maria/cost` **41cfde5** (+ clerk fix dba5e72 + last 10 turns of history kept, older ones shrink to their thought) | **0 (never signed)** | ❌ | 19.9 min | 275 / $0.30 | Investigation 642 s (mail search loop 10×, ERP 89 turns); then the signing code took 176 s and time ran out. Also: the omit cap refused to leave out an extra form position that is not on the bid sheet → fixed in **47eb5ef** |
| 04:03 | **run_3bf52944** | Maria | `maria/cost` **41cfde5** (+ clerk fix dba5e72 + last 10 turns of history kept, older ones shrink to their thought) | **100** | ✅ | 14 min | 218 / $0.22 | ERP ~10.8k tokens per call (before ~14.3k), but slower: investigation 616 s; mail 36 turns. Clerk fix fine (20 turns, no loop) |
| 04:03 | **run_8a46eb9c** | Vamshidhar | package 0cca498f = main **d72deb8** (rerun of b3f1b38f) | **100** | ✅ | 9 min | 274 / $0.33 | |
| 03:58 | run_b3f1b38f | Vamshidhar | package 0cca498f = main **d72deb8** (ERP candidate audit) | **– (platform failure, doesn't count)** | | 3 min | 175 / $0.23 | Platform failure at 04:02 |
| 03:35 | **sub_973a02b5 (SUBMISSION, promoted by the organisers)** | Organisers | test run 4876a0ad = `maria/cost` **9105e5e** (package 4c5ab3f4) | **100** | ✅ | 8.4 min | 184 / **$0.164** | **Now our final package** (latest passed submission). ⚠️ Same package as 012496d3, which scored 0 (clerk omit loop). Leaderboard 04:00 UTC: **#7**, $0.164, 8:21 |
| 03:53 | run_608c82d7 | Maria | `maria/cost` **8e19c98** (= 9105e5e + clerk fix dba5e72) | **– (platform failure, doesn't count)** | | 8.7 min | 211 / $0.21 | Atira "The platform failed" at 04:02, same minute as bf29711e and b3f1b38f; not retried |
| 03:52 | run_bf29711e | Maria | `maria/cost` **8e19c98** (= 9105e5e + clerk fix dba5e72) | **– (platform failure, doesn't count)** | | 10 min | 246 / $0.24 | Platform failure at 04:02. Until then the clerk fix worked: "Position 01.04 is added. I'll click Weiter" |
| 03:52 | **run_7dbf1540** | Maria | `maria/escalation` **dba5e72** (clerk fix on top of fc54a43) | **100** 🎉 | ✅ | 9.0 min | 221 / $0.25 | Clerk fix holds: signed, no loop |
| 03:35 | **run_4876a0ad** | Maria | `maria/cost` **9105e5e** (one past page in full instead of two; input tokens per agent in the summary) | **100** 🎉 | ✅ | 8.4 min | 184 / **$0.16** 💰 | Clean. **Input 1.8 M tokens (before 2.3-2.6 M), cost $0.16 (before $0.27-0.31)**; 49% cached this time (luck: caching is unreliable). Input per agent: **ERP 828k (46%)**, mail 313k, tender portal 205k, customer portal 192k, clerk 165k, extraction only 76k. Investigation 372 s (slower than the last two) |
| 03:32 | run_012496d3 | Maria | `maria/cost` **9105e5e** (one past page in full instead of two; input tokens per agent in the summary) | **0 (never signed)** | ❌ | 13.5 min | 309 / $0.31 | **Clerk bug from fc54a43 (also in our final package!):** the `steps` chain ended with "Position hinzufügen" and reported the page's new notice as something to fix; the clerk re-entered the same position, got stuck, used its one allowed omit on 01.02, then got stuck on 01.05 and **looped on the refused omit** until its step cap. Fixed in **dba5e72** (notice reported neutrally, "a saved position may empty its fields: go on", one more omit after each circle hint) |
| 03:02 | **sub_ccfe5b8f + sub_debd95a5 (SUBMISSIONS, promoted by the organisers)** | Organisers | test runs 9902e32b and 1b83cba3 = **fc54a43** (package 35eb499d) | **100** 🎉 | ✅ | 6.3 / 6.6 min | $0.31 / $0.27 | **Our final package is now fc54a43** (latest passed submission: sub_ccfe5b8f), i.e. `maria/escalation` with all branch fixes. **Leaderboard 03:35 UTC: rank #7, 100, $0.2748, 6:33** (Plite and EliTUM passed us: 1:32/$0.075 and 6:48/$0.163) |
| 03:02 | **run_9902e32b** | Maria | `maria/escalation` **fc54a43** (stuck position started over; only that one may be left out) | **100** 🎉 | ✅ | **6.3 min** 🏆 | 203 / $0.31 | Check 2 of 2: clean, investigation 217 s, 0 model timeouts. **Clerk 16 turns, ~160 s** form + TAN (before ~281 s), 6 `steps` actions, no loop, so the new omit guard did not need to fire (it is covered by unit tests). **Our fastest runs so far** |
| 03:02 | **run_1b83cba3** | Maria | `maria/escalation` **fc54a43** (stuck position started over; only that one may be left out) | **100** 🎉 | ✅ | **6.6 min** 🏆 | 189 / $0.27 | Check 1 of 2: clean, investigation 230 s, 0 model timeouts. **Clerk 16 turns, ~160 s** form + TAN (before ~281 s), 6 `steps` actions, no loop, so the new omit guard did not need to fire (it is covered by unit tests). **Our fastest runs so far** |
| 02:31 | run_8a2e1426 | Maria | `maria/escalation` **ed69d43** (clerk fix), 2nd check | **0 (never signed)** | ❌ | 20.4 min | 277 / $0.45 | Investigation fine (494 s, full 5-position bid, total right). **Two failures:** (1) **Our clerk bug:** position 01.04 went in fine, then for 01.02 the `steps` chain ended by pressing "Position hinzufügen" (the clean run 11adf2a5 never pressed it and went on with "Weiter"); the form then showed empty fields with "Diese Aktion ist in diesem Schritt nicht möglich" / "Bitte eine ganze Stückzahl eingeben", and the clerk circled 45 turns (fill → add → empty again, the same pattern as d3ca14df). Escalation fired once and rightly tried "Weiter", then the loop went on. The ed69d43 hint ("omit this one position") then made it **omit all 5 positions**, not just 01.02. (2) **Mail site outage in the sandbox** (45 s reads, ERR_ABORTED): the courier never saw the TAN mail, so the bid could not be signed anyway. **Lesson: ed69d43 is 1 of 2 valid runs at 100; the omit hint must be limited to one position, and the clerk must not press an "add another line" button after a position is filled** |
| 02:04 | **run_9c58092c** | Vamshidhar | package 1a6b63bc = `reliable-calls` on 288c88c (same as sub_0af454da) | **100** | ✅ | **9.3 min** | 232 / $0.32 | |
| 01:44-02:02 | run_434f08ed, run_431c4c97, run_b26bc7fe | Vamshidhar | packages e24568e0, 6b73b434, 745cb392 (no label) | **0 (crashed at start)** | ❌ | 0 min | 0 | `llm.py` builds an OpenAI client without `OPENAI_API_KEY`: "Missing credentials", exit code 1. A packaging/config problem in those variants, not the agent |
| 01:13 | **run_8e3e2dbc** | Vamshidhar | package b9a8c712 (no label; holds an empty `QuoteCraft-sub_optimized.tar.gz`) | **100** | ✅ | 10.3 min | 254 / $0.37 | |
| 00:27 | **run_ce5fbf59** | Vamshidhar | package 1a6b63bc = `reliable-calls` on 288c88c | **100** | ✅ | 15.6 min | 266 / $0.38 | |
| 23:04 | **sub_232a217b (SUBMISSION, Vamshidhar)** → run_25c79e7b | Vamshidhar | **main d72deb8** "audit every ERP material candidate" (package 0cca498f, files identical to the commit) | **100** 🎉 | ✅ | 13.8 min | 264 / $0.34 | **Review passed ✅. Submitted 25 s after sub_26819801, so this is the latest passed submission = OUR FINAL PACKAGE NOW.** ⚠️ main is on the 1fab415 line: it has **none** of the branch fixes (idle-wake, browser failover, role routing, formats, `steps`, clerk loop fix, 30 s call cap) |
| 23:04 | **sub_26819801 (SUBMISSION, Vamshidhar)** → run_f6714218 | Vamshidhar | package 1a6b63bc = `reliable-calls` on 288c88c (same as sub_0af454da) | **100** 🎉 | ✅ | **9.1 min** | 237 / $0.31 | Review passed. **Our leaderboard entry: rank #6 at 02:30 UTC, 100, $0.3094, 9:04** |
| 22:48 | **run_f2032d98** | Vamshidhar | package 1a6b63bc = `reliable-calls` on 288c88c | **100** | ✅ | 12.3 min | 276 / $0.35 | |
| 00:45 | run_d8fdffff | Maria | `maria/escalation` **ed69d43** | **– (platform failure, doesn't count)** | | | 0 calls | Atira: "The platform failed, not your agent system" |
| 00:34 | **run_11adf2a5** | Maria | `maria/escalation` **ed69d43** (clerk fix) | **100** 🎉 | ✅ | **9.3 min** | 208 / $0.30 | Clean, investigation 278 s. **Clerk 24 turns** (before 37-46), 8 `steps` actions; no loop, no escalation needed. Form + TAN still ~281 s: fewer model turns, but each chain waits for every page reload |
| 00:18 | **run_e1e2eb81** | Maria | `maria/escalation` **dd8127d** | **100** 🎉 | ✅ | **9.4 min** | 225 / $0.30 | Series 4/4. Clean, investigation 397 s |
| 00:03 | **run_d247703d** | Maria | `maria/escalation` **dd8127d** | **100** | ✅ | 14.6 min | 215 / $0.34 | Series 3/4. 4 model timeouts slowed the investigation (651 s) |
| 23:44 | run_d3ca14df | Maria | `maria/escalation` **dd8127d** | **0 (never signed)** | ❌ | 18.8 min | 304 / $0.52 | Series 2/4. Investigation fine (284 s, full bid). **Clerk looped 95 turns** on "fill the position, add it, fields empty again" until its 120-step cap: the form rejected the position, but the `steps` chain reported success, and escalation had been switched off for the clerk in cc7f3f8. **Our fault; fixed in ed69d43** |
| 23:32 | **run_9d813e7f** | Maria | `maria/escalation` **a865a69** | **100** 🎉 | ✅ | 10.3 min | 244 / $0.31 | Series 1/4. Clean, investigation 346 s |
| 23:13 | **run_bb0655a2** | Maria | branch `maria/escalation` **f1867df**: + "steps" action | **100** 🎉 | ✅ | 10.4 min | 237 / $0.26 | Clean: investigation 386 s, 0 timeouts. Clerk **37 turns / 241 s** (before: 40-46 / 207-284 s): it used `steps` 7× (bidder data, all amounts of each position, discount), all ran fine, but still did the configurator cascade (attribute → apply) one choice per turn. Next: have the cascade go into `steps` too. Side effect: the clerk got a "going in circles" hint while filling 5 similar positions (false positive) |
| 22:37 | **run_05d351d6** | Maria | branch `maria/escalation` **ae31fb3** | **100** 🎉 | ✅ | 11.7 min | 230 / $0.29 | Retry of 9f5d8f25. Clean: investigation 421 s, no open questions, 0 timeouts, longest repeat 4×. No agent got stuck, so **no escalated turn was needed**: this shows escalation does no harm, not yet what it adds |
| 22:37 | run_9f5d8f25 | Maria | branch `maria/escalation` **ae31fb3** | **– (platform failure, doesn't count)** | | 7.2 min | 80 / $0.07 | Atira: "The platform failed, not your agent system… started again automatically" |
| 22:37 | **run_67d30f66** | Maria | branch `maria/erp-loop-fixes` **9c3081a** | **100** 🎉 | ✅ | 12.5 min | 299 / $0.40 | Retry of 294db2ef. Clean: investigation 464 s, no open questions, 0 timeouts; one agent sent idle when stuck. **First sandbox 100 with role-based routing and Word/Excel/CSV reading** |
| 22:36 | run_294db2ef | Maria | branch `maria/erp-loop-fixes` **9c3081a** | **– (platform failure, doesn't count)** | | 7.5 min | 210 / $0.26 | Atira: "The platform failed, not your agent system". Until then strong: investigation ended by itself in **346 s with no open questions**, complete 5-position bid, halfway through the form |
| 22:33 | **run_af92c314** | Vamshidhar | package 0cca498f = main d72deb8 "candidate audit + full paging" | **100** | ✅ | 14.9 min | 298 / $0.41 | Automatic retry of 0634f300 |
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
| 🔵 Target | Quality ≥ 95, < 8 min, low cost (Qwen first), 3 test runs in a row without a crash | 🟨 (11 Oct) **100 many times**; < 8 min reached (6.3 and 6.6 min, fc54a43); 3 in a row reached (e.g. 11adf2a5 → 1b83cba3 → 9902e32b, on clean infrastructure); low cost $0.16 (9105e5e). Open: the clerk-loop 0s (P1) |
| ⭐ Final-ready | Nothing layout-specific in the code; passes the AI review; clean README | 🟨 every submission passed the AI review; package scan clean before every run; overfitting checks with invented data (see below). Open: README refresh for the final |

## Milestones

Status: ⬜ open · 🟨 in progress · ✅ done · ⛔ blocked

| # | Milestone | Done when | Status |
|---|---|---|---|
| M0 | Setup | CLI, team, repo, Entire hooks, scouting of the four sites | ✅ |
| M1 | Walking skeleton | The agent logs into all 4 sites in parallel, reads the brief and **submits a signed bid** (even partial) in a test run, end to end | ✅ 17:34: signed and eligible in the sandbox (form ~2 min, signing code read in 8 s) |
| M2 | Facts collected | Every site agent files its facts into the case file; they match the facts checked by hand | 🟨 reached in run 60233f96 (all facts but the free stock behind one lead time); not yet in every run. Free stock and Q&A units fixed since (2d96c95, merged) |
| M3 | Calculator correct | All rules implemented and unit-tested; a complete bid from correct facts | ✅ 100/100 against our reference answer, also after every merge · latent edge cases open (Vamshidhar) |
| M4 | First full bid | Test run: quality ≥ 80, all positions filled, signed | ✅ 98.7: all 5 positions, signed (run 60233f96, 17:04 UTC) |
| M5 | Hardened | Quality ≥ 95, < 8 min, 3 clean runs in a row; time guard tested with a forced short deadline | 🟨 (11 Oct) quality 100, < 8 min and 3 clean in a row all reached on `maria/escalation`; robustness fixes 10-16 confirmed. Open: clerk loop P1 (fix dba5e72 in test) |
| M6 | Final freeze | Last `atira submit` passes review; README final; Entire checkpoints pushed; best-of-3 confirmed (already set) | 🟨 (11 Oct) 13 submissions, all passed review; final package now sub_973a02b5 (`maria/cost` 9105e5e, known clerk-loop risk). Open: resubmit with dba5e72 once confirmed (Maria + Vamshidhar); cut-off time still unknown |

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
- **Name every test and eval run after its branch and commit**, e.g. `maria/cost 1d0ecea` (`atira run name <run> "<branch> <commit>"`; eval runs: `--label`). Maria's runner does it automatically; earlier runs were named after the fact (11 Oct, 05:45 UTC).
- **Only Maria and Vamshidhar start sandbox test runs** (at most 3 queued per team). Every run goes into the score log the moment it is sent. **A test run that scores better can be promoted to a submission by the organisers, so it may become the final package.**
- Fair play: the model must choose navigation, searches and documents. No fixed click paths, no crawlers, and **no scenario values** (tender references, material numbers, keys, prices, logins) anywhere in `starter-kit/`, including tests and comments. Tests use invented values.
- Never `--no-verify`: Entire needs its git hooks to link sessions to commits. Start your coding agent inside the repo folder so its session is captured.

## Status (11 Oct, 04:00 UTC)

| Done | Next |
|---|---|
| Model-directed agent (site agents, shared case file, deterministic calculator, clerk + courier), 100 on the public data many times | Confirm the clerk fix dba5e72 (3 runs going) |
| Robustness: stuck/idle investigators, browser failover, escalation, routing by role + fallback, document formats, number formats | Resubmit with dba5e72 once confirmed (Maria + Vamshidhar decide) |
| Speed: `steps` action, bid form 16 turns / ~160 s; best run 6.3 min | Agents start during the context call; ERP sooner |
| Cost: $0.31 → $0.16 (history cut); input tokens per agent in every run summary | Page-text trimming, then fewer ERP turns |
| Overfitting checks with invented data (calculator, site names, formats, number formats) | OCR for scanned PDFs (optional); README for the final; pitch (Iga, Ravindra) |

## Useful commands

| What | Command |
|---|---|
| Free models locally (keep open) | `atira models proxy` |
| Scouting logins (PowerShell) | `atira scout --env \| Out-String \| Invoke-Expression` |
| Local run without submitting | `AGENT_SKIP_SUBMIT=1 HEADLESS=1 uv run --no-sync python agent.py` (in `starter-kit/`) |
| Save every agent turn / every filed page | `AGENT_TRACE=<dir>`, `AGENT_DOCS_DIR=<dir>` |
| Score an answer | `python tuning/scorer.py <answer.json> <reference.json>` (the reference answer is kept off the repo: ask Maria) |
| Tests | `uv run python -m unittest discover -s tests` (in `starter-kit/`) |
