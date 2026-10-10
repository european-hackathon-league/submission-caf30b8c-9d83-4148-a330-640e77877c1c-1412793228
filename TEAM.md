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

## Score log (every sandbox run, newest first)

Updated after every run. Times in UTC (Berlin = UTC+2). Score = Atira's official quality (0-100).

| Started (UTC) | Run | Who | Code | Quality | Eligible | Time | Calls / cost | Main finding |
|---|---|---|---|---|---|---|---|---|
| 18:55 | run_e3804980 | Maria | **main 33c04d7** (clean checkout) | **10** | ✅ | 13.1 min | 224 / $0.27 | Signed (TAN worked), but **empty bid**: ERP found only 2 of 5 materials and no prices. The ERP agent spent ~45 turns waiting for the spec, then **looped 46 turns** on "HZ-2170 has stroke 500, not 507" (A-2 is 500 in the case file; 507 was misread). The loop repeats every ~6 turns, so even eb1a794's circle detector (1- or 2-turn repeats) would miss it |
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
