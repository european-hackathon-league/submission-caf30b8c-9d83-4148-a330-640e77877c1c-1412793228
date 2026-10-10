"""Classifies every sandbox run by what decided it, from the local run records and logs.

    python tuning/run_report.py [docs/runs]

Reads docs/runs/official/<run>.json (Atira's run record) and docs/runs/logs/<run>.full.json (the run's log chunks),
both local only. For each run it reports the score and time, where the time went, and one verdict:

    outage    a website did not load inside the sandbox (45 s page reads, aborted loads)
    overload  the model timed out repeatedly (>= 5 calls without a reply)
    loop      an agent repeated the same thought many times (>= 15) or never finished
    clean     none of the above

Infrastructure verdicts (outage, overload) say nothing about the code; branch and bound compares code variants on
the other runs only. Holds no scenario values.
"""
from __future__ import annotations

import collections
import json
import os
import re
import sys

TURN = re.compile(r"\[([a-z-]+)(?::[a-z]+)? \d+ t\+")


def analyse(record: dict, chunks: list[dict]) -> dict:
    text = [chunk.get("text", "") for chunk in chunks]
    score = record.get("score") or {}
    started, finished = record.get("started_at"), record.get("finished_at")
    turns: dict[str, list[str]] = collections.defaultdict(list)
    for line in text:
        match = TURN.match(line)
        if match:
            thought = line.split(") ", 1)[-1].split(" | ")[0]
            turns[match.group(1)].append(" ".join(thought.lower().split())[:70])
    repeats = {agent: collections.Counter(thoughts).most_common(1)[0][1] for agent, thoughts in turns.items() if thoughts}
    unfinished = [m.group(1) for line in text for m in [re.match(r'\[([a-z-]+)\] finished: \{"done": false', line)] if m]
    investigation = next((int(m.group(1)) for line in text for m in [re.match(r"Investigation took (\d+) s", line)] if m), None)
    timeouts = sum(1 for line in text if line.startswith("[llm]") and "no reply" in line)
    slow_pages = sum(1 for line in text if "read 45.0s" in line or "ERR_ABORTED" in line)
    worst = max(repeats.items(), key=lambda item: item[1], default=("-", 0))
    if slow_pages >= 4:
        verdict = "outage"
    elif timeouts >= 5:
        verdict = "overload"
    elif worst[1] >= 15 or unfinished:
        verdict = "loop"
    else:
        verdict = "clean"
    return {
        "run": record.get("run_id", "?")[4:12], "kind": record.get("kind"),
        "package": (record.get("package") or {}).get("sha256", "")[:8],
        "label": ((record.get("package") or {}).get("label") or "")[:40],
        "quality": score.get("quality"), "minutes": round((finished - started) / 60000, 1) if started and finished else None,
        "calls": record.get("calls"), "investigation_s": investigation, "timeouts": timeouts, "slow_pages": slow_pages,
        "worst_repeat": f"{worst[0]} {worst[1]}x", "unfinished": ",".join(unfinished), "verdict": verdict,
    }


def main(root: str) -> None:
    rows = []
    for name in sorted(os.listdir(os.path.join(root, "official"))):
        log = os.path.join(root, "logs", name.replace(".json", ".full.json"))
        if not name.startswith("run_") or not os.path.exists(log):
            continue
        record = json.load(open(os.path.join(root, "official", name), encoding="utf-8"))
        if not record.get("finished_at"):
            continue
        rows.append(analyse(record, json.load(open(log, encoding="utf-8"))))
    rows.sort(key=lambda row: (row["verdict"], -(row["quality"] or 0), row["minutes"] or 99))
    columns = ["run", "package", "quality", "minutes", "calls", "investigation_s", "timeouts", "slow_pages",
               "worst_repeat", "unfinished", "verdict", "label"]
    print(" | ".join(columns))
    for row in rows:
        print(" | ".join(str(row[column]) if row[column] not in (None, "") else "-" for column in columns))
    counts = collections.Counter(row["verdict"] for row in rows)
    print("\n" + ", ".join(f"{verdict}: {count}" for verdict, count in sorted(counts.items())))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "runs"))
