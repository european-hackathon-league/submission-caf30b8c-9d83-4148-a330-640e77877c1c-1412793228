# Team QuoteCraft: who owns what

EHL Grand Finale 2026 · Atira challenge "From RFQ to bid". Updated 10 Oct 2026, 16:45.

## Owners

| Role | Owner | Focus | Done when |
|---|---|---|---|
| Build lead + verification | Maria | Local runs, scoring against our reference answer, sandbox test runs, merging branches, OpenAI vs Qwen for fact extraction | A sandbox test run scores ≥ 60 in < 15 min |
| Builder 2: coverage | Puneetha | Why the bidder Q&A answers, the end reserves (technical release mail) and the metal index (price-index mail) stay unanswered; fixes in the prompts and `casefile.py` | All 5 positions priced in a local run |
| Builder 3: tests / QA | Vamshidhar | Calculator edge-case tests, the latent calculator bugs, the failing `test_browser_env` tests, fair-play check before every submit | Test suite green, latent bugs fixed |
| Pitch & story | Iga, Ravindra | Pitch skeleton, 2-minute story, likely jury questions; organiser questions (pitch format, submission cut-off time) | Draft ready for team review |

## Success levels

| Level | Criterion | Status (16:50) |
|---|---|---|
| 🟢 Minimum | Eligible signed bid (correct tender reference) on the public dataset | 🟨 first test run of the model-directed agent is running |
| 🟡 Good | Quality ≥ 80 in a test run, run time < 12 min | ⬜ best local run 29.75 in ~14 min |
| 🔵 Target | Quality ≥ 95, < 8 min, low cost (Qwen first), 3 test runs in a row without a crash | ⬜ |
| ⭐ Final-ready | Nothing layout-specific in the code; passes the AI review; clean README | 🟨 package scan clean, README describes the architecture; AI review not yet tried |

## Milestones

Status: ⬜ open · 🟨 in progress · ✅ done · ⛔ blocked

| # | Milestone | Done when | Status |
|---|---|---|---|
| M0 | Setup | CLI, team, repo, Entire hooks, scouting of the four sites | ✅ |
| M1 | Walking skeleton | The agent logs into all 4 sites in parallel, reads the brief and **submits a signed bid** (even partial) in a test run, end to end | 🟨 local runs reach a bid; the signed submission is being tested in the sandbox now |
| M2 | Facts collected | Every site agent files its facts into the case file; they match the facts checked by hand | 🟨 positions, revisions, requirements, materials, prices, discount ✅ · bidder Q&A answers, end reserves, metal index ⬜ (Puneetha) |
| M3 | Calculator correct | All rules implemented and unit-tested; a complete bid from correct facts | ✅ 100/100 against our reference answer, rule-by-rule test suite · latent edge cases open (Vamshidhar) |
| M4 | First full bid | Test run: quality ≥ 80, all positions filled, signed | ⬜ |
| M5 | Hardened | Quality ≥ 95, < 8 min, 3 clean runs in a row; time guard tested with a forced short deadline | ⬜ |
| M6 | Final freeze | Last `atira submit` passes review; README final; Entire checkpoints pushed; best-of-3 confirmed (already set) | ⬜ |

**Approach:** Phase 1, a brute-force solution, is done (it scored 100 in a test run but as a fixed script with 0 model calls, so it is **not submittable** under fair play and was never submitted). **Phase 2, the model-directed solution, is in progress** (M1–M5).

## Pipeline stages

```
Brief -> 4 site agents in parallel -> case file (evidence) -> calculator -> validator -> submitter (+ TAN)
              page renderer + helpers                                         time guard
```

| Stage | Module | Done when | Status |
|---|---|---|---|
| Brief reader | `casefile.read_context` | Tender, scenario date, company, VAT id and authorised senders come from the run brief, never from code | ✅ |
| Page renderer | `browser_env.Tab.observe` | Pages read as a human sees them (labels, tooltips, collapsed sections, frames); hidden decoys and invisible characters dropped | 🟨 works on all four sites; 8 regression tests in `test_browser_env.py` fail |
| Helpers | `browser_env`, `worker` actions | Popups, access checks (incl. several per page), errors, expired sessions, paging, file downloads | 🟨 mail access-check loop fixed; section toggles clickable |
| Site agents | `agent.py` + `worker.Agent` | The model decides where to go; each agent finishes its site in < 5 min | 🟨 ~14 min for all four; Q&A coverage open |
| Case file | `casefile.CaseFile` | Facts with provenance; exact reference, authorised sender, latest record no later than the scenario date | ✅ picks the right records on our reference data; failed extractions are now retried |
| Calculator | `calculator.py` | All rules, Decimal, half-up, largest-remainder allocation; the model never does arithmetic | ✅ |
| Validator | none yet | Schema, arithmetic consistency, no extra or duplicate positions, bid / no_bid logic, before submitting | ⬜ not built |
| Submitter | `submit.py` | Bid form filled from the brief's steps, TAN requested last, signed | 🟨 under test in the sandbox now |
| Time guard | `agent.py` (`hard_stop`, `submit_reserve`) | Unfinished positions omitted and the bid still signed before 20 min | 🟨 budget exists; not tested with a forced short deadline |

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
