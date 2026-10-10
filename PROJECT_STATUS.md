# QuoteCraft RFQ-to-Bid — status snapshot

**Snapshot:** 10 October 2026. This document accompanies the implementation checkpoint on `main`; it is a handoff
record, not an assertion that the challenge submission is finished.

## What is implemented

- `starter-kit/agent.py` coordinates four site agents (tender portal, supplier portal, ERP, and mail) and keeps the
  navigation decisions model-directed at runtime.
- `worker.py`, `browser_env.py`, and `llm.py` provide accessible-page observations, bounded actions, downloads,
  frames, dialogs, log-in handling, retries, and Qwen-proxy calls without site-specific selectors or click paths.
- `casefile.py` turns pages chosen by the agents into typed evidence and exposes the remaining research questions.
- `calculator.py` applies the tender's commercial rules with exact `Decimal` arithmetic and explicit rounding.
- `submit.py` delegates bid-form completion and TAN retrieval to model-directed agents and records the tender receipt.
- The package is configured for the challenge's four-browser limit in `starter-kit/agent.json`. The README documents
  the architecture, local harness, environment switches, and fair-play boundary.
- The committed tests cover calculation rules, entry-point plumbing, and submission behaviour. This checkpoint adds
  `tests/test_browser_env.py` and 25 local fixtures for browser observation/action edge cases.

## Deliberately pending work

1. Make the new browser regression suite green. Two targeted failures were reproduced on this snapshot:
   - remote `Load more` collection currently causes messages to appear more than once in the returned/retained
     evidence;
   - closing the question dialog is not reliably reflected as closed by the page observation.
2. Decide whether to integrate `tools/submit-batch-action.patch`. It is intentionally stored as an **unapplied**
   proposal for reload-safe multi-action bid-form entry; it needs review, tests, and then either application or
   removal in a later focused commit.
3. Run the complete unit suite after the two regressions are fixed, then exercise a public non-submitting run and
   the official `atira test-run` flow. Verify a genuine form submission, TAN lookup, receipt capture, timeout
   behaviour, and results on unseen layouts.
4. Keep improving evidence quality and recovery behaviour based on those runs, without adding scenario-specific
   values, selectors, URLs, credentials, or fallback answers.

## Acceptance target

The project is ready only when it can independently research an unseen tender across the allowed four browsers,
derive an eligible bid from collected evidence, submit and sign it through an unseen tender portal, and pass the
official RFQ evaluation while respecting the challenge's fair-play rules.
