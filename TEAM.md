# Team QuoteCraft: who owns what

EHL Grand Finale 2026 · Atira challenge "From RFQ to bid". Updated 10 Oct 2026, 18:30.

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

## Success levels

| Level | Criterion | Status (18:15) |
|---|---|---|
| 🟢 Minimum | Eligible signed bid (correct tender reference) on the public dataset | ✅ reached 17:34 (test run 6da03229: eligible, quality 10; the bid was signed but empty) |
| 🟡 Good | Quality ≥ 80 in a test run, run time < 12 min | 🟨 **best sandbox 70.7** (run 8184b178, 16.6 min, $0.43): 4 of 5 positions perfect · missing: position 01.01 (~28 pts incl. total + index check), one lead time |
| 🔵 Target | Quality ≥ 95, < 8 min, low cost (Qwen first), 3 test runs in a row without a crash | ⬜ |
| ⭐ Final-ready | Nothing layout-specific in the code; passes the AI review; clean README | 🟨 package scan clean before every test run; README describes the architecture; AI review not yet tried (no `atira submit` yet) |

## Milestones

Status: ⬜ open · 🟨 in progress · ✅ done · ⛔ blocked

| # | Milestone | Done when | Status |
|---|---|---|---|
| M0 | Setup | CLI, team, repo, Entire hooks, scouting of the four sites | ✅ |
| M1 | Walking skeleton | The agent logs into all 4 sites in parallel, reads the brief and **submits a signed bid** (even partial) in a test run, end to end | ✅ 17:34: signed and eligible in the sandbox (form ~2 min, signing code read in 8 s) |
| M2 | Facts collected | Every site agent files its facts into the case file; they match the facts checked by hand | 🟨 nearly: run 8184b178 read positions, Q&A (withdrawn-answer check ✅), discount, materials, prices for 4 of 5 positions. Open: whatever blocks position 01.01, the shared-stock lead time of 01.03, ERP free stock, mailbox address. Sandbox access varies between runs |
| M3 | Calculator correct | All rules implemented and unit-tested; a complete bid from correct facts | ✅ 100/100 against our reference answer, also after every merge · latent edge cases open (Vamshidhar) |
| M4 | First full bid | Test run: quality ≥ 80, all positions filled, signed | 🟨 70.7 with 4 of 5 positions; one position away |
| M5 | Hardened | Quality ≥ 95, < 8 min, 3 clean runs in a row; time guard tested with a forced short deadline | 🟨 robustness parts done: timeouts, tab renewal, submit reserve; quality and speed not yet |
| M6 | Final freeze | Last `atira submit` passes review; README final; Entire checkpoints pushed; best-of-3 confirmed (already set) | ⬜ cut-off time still unknown |

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
| `validator` | the bid, before it is entered | duplicate or foreign positions, a total that is not the sum of the lines, broken lines | ✅ |
| `typing_guard` | every value the bid clerk types | values from nowhere: an invented e-mail, a made-up price, a mistyped number | ✅ |
| `no_guessed_mailbox` | bidder details for the clerk | an unknown mailbox address filled in by guessing (the clerk asks the mailbox colleague instead) | ✅ |
| `grounding` | every extracted fact | numbers, keys and identifiers not present in the page they were extracted from | ⬜ planned |
| `summary_check` | before the final signature | the portal's summary disagreeing with the bid sheet | ⬜ planned |

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
