# QuoteCraft — from RFQ to bid

A team of model-directed agents that reads a tender across four business websites it has never seen, works out the
bid the rules call for, and enters and signs it in the tender portal.

## How it works

```
task brief ──► model reads it: tender, scenario date, authorized senders
                    │
   ┌────────────────┼──────────────────┬─────────────────┐
   ▼                ▼                  ▼                 ▼
 agent            agent              agent             agent        one per website, each in its own browser:
 tender portal    supplier portal    ERP               webmail      the model picks every click, search and page
   │  keep          │  keep            │  keep           │  keep
   └────────────────┴───────┬──────────┴─────────────────┘
                            ▼
                     shared case file        a model call turns each filed page into typed facts;
                            │                the brief's rules yield the open questions all agents see
                            ▼
                      calculator.py          the bid rules as exact Decimal arithmetic
                            ▼
                     submission agent        fills the bid form it finds; the mail agent fetches the TAN
```

1. **Read the brief.** One model call extracts the tender reference, the scenario date, the bidder and which
   mailbox the rules authorize for which kind of record.
2. **Investigate in parallel.** One agent per website (`worker.Agent`). Each turn it sees its page as accessible
   text with numbered controls (`browser_env.Tab`), plus the case file and its open questions, and answers with
   actions: log in, click, fill, select, search, page through a list, download a file, or `keep` the page as
   evidence. Nothing in the code knows a URL, a selector or a click path of any website.
3. **File facts.** `keep` hands the page to a second model call that extracts typed records (positions, Q&A
   answers, revisions, requirements, materials, price conditions, mail records). `casefile.CaseFile` merges them
   and derives what is still unknown: a catalogue group found in the specification becomes an ERP question, a key
   in a Q&A answer becomes a mailbox question, and so on. Agents finish when their website has nothing left to add.
4. **Calculate.** `calculator.calculate_bid` applies the bid rules of the brief: latest clarification, withdrawn
   answers, scoped amendments, usable travel, sets to pieces, price scales, FX, conditional discount, condition
   clauses, shared stock, delivery commitments, cartons, pooled setup, project bonus, rounding. A position that
   lacks evidence is left out rather than guessed.
5. **Submit.** `submit.submit_bid` gives the bid to an agent on the tender portal, which fills whatever bid form
   it finds, asks a mail agent for the signing TAN and confirms the receipt.

## What is model and what is code

| The model decides | Code does |
| --- | --- |
| where to go, what to search for, which record or document matters | renders the page, carries out the chosen action |
| how to pass a popup, access check, login or error page | retries a server error, re-reads the page |
| which page is evidence and of what kind | pages through a list the model chose, reads a file it chose |
| what a page says (extraction into typed facts) | parses numbers and dates, checks sender, reference and date |
| when a search is complete or a record does not exist | arithmetic, rounding, allocation |
| how to fill and sign the bid form | — |

No scenario value (reference, material, price, key, login, TAN) appears anywhere in the package.

## Files

| File | What it does |
| --- | --- |
| `agent.py` | Entry point: reads the run, starts the site agents, calculates, hands the bid to the submission agent |
| `worker.py` | The agent loop: page text in, the model's actions out |
| `browser_env.py` | A tab as accessible text (labels, descriptions, tooltips, frames, collapsed sections) and the actions on it |
| `casefile.py` | Evidence to typed facts, open questions, calculator inputs |
| `calculator.py` | The bid rules as Decimal arithmetic |
| `submit.py` | Bid entry and signing |
| `llm.py` | The hosted Qwen through the run's metering proxy: JSON replies, retries, a concurrency cap |
| `run.py`, `browsers.py`, `models.py` | The starter kit's plumbing: the run contract, the run's browsers, the hosted models |
| `agent.json` | Setup (`uv sync`), run command, four browsers, the hosted `qwen` |
| `tests/` | The calculator rule by rule, the page rendering against local fixtures, the plumbing against fakes |

## Running it

In the sandbox the platform sets everything (`CHALLENGE_API_URL`, `CHALLENGE_RUN_TOKEN`, `CDP_URLS`, `QWEN_*`):

```sh
atira test-run . --challenge rfq
```

On your machine, against the public websites with the scouting logins (nothing counts), with `atira models proxy`
running in another terminal:

```sh
python ../tools/local_run.py --no-submit
```

Switches: `AGENT_SKIP_SUBMIT=1` stops before the bid form, `AGENT_SITES=a,b` starts only those site agents,
`AGENT_MAX_STEPS` caps an agent's turns, `AGENT_DUMP=<file>` writes the case file as JSON.

```sh
uv run python -m unittest discover tests
```
