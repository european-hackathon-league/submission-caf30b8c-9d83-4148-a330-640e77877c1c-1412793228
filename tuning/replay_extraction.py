"""Replays the fact extraction on documents a run filed, to compare models without driving any browser.

A local run with AGENT_DOCS_DIR=<folder> saves every filed document. This script feeds the same documents to the
same extraction prompt (casefile.CaseFile) with the provider chosen in EXTRACT_PROVIDER (qwen | openai, plus
OPENAI_MODEL), and reports time per document, failures, and the resulting case file. Two replays of the same folder
with different providers are a like-for-like comparison of speed and of the facts extracted.

Usage (from the repo root, with the model variables set, e.g. after `atira scout --env`):
    EXTRACT_PROVIDER=qwen   uv run --project starter-kit --no-sync python tuning/replay_extraction.py <docs> <brief.md> <out.json>
    EXTRACT_PROVIDER=openai OPENAI_MODEL=<model> uv run ... tuning/replay_extraction.py <docs> <brief.md> <out.json>
"""

from __future__ import annotations

import asyncio
import glob
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "starter-kit"))

import llm  # noqa: E402
from casefile import CaseFile, read_context  # noqa: E402


async def replay(folder: str, brief_path: str, out_path: str, concurrency: int) -> None:
    brief = open(brief_path, encoding="utf-8").read()
    case = CaseFile(brief, await read_context(brief))
    documents = [json.load(open(path, encoding="utf-8")) for path in sorted(glob.glob(os.path.join(folder, "*.json")))]
    gate = asyncio.Semaphore(concurrency)
    timings: list[dict] = []

    async def one(doc: dict) -> None:
        async with gate:
            failed_before = llm.STATS["failed"]
            started = time.monotonic()
            await case._extract(doc["kind"], doc["text"], doc["source"], doc["agent"])
            timings.append({"kind": doc["kind"], "source": doc["source"][-60:], "seconds": round(time.monotonic() - started, 1),
                            "failed_attempts": llm.STATS["failed"] - failed_before})

    started = time.monotonic()
    await asyncio.gather(*(one(doc) for doc in documents))
    wall = time.monotonic() - started
    report = {"provider": os.environ.get("EXTRACT_PROVIDER", "qwen"), "model": os.environ.get("OPENAI_MODEL") or "qwen",
              "documents": len(documents), "wall_seconds": round(wall, 1), "llm": llm.summary(),
              "timings": sorted(timings, key=lambda t: -t["seconds"]), "case_file": json.loads(case.dump())}
    with open(out_path, "w", encoding="utf-8") as out:
        json.dump(report, out, ensure_ascii=False, indent=1)
    slowest = report["timings"][0] if timings else {}
    print(f"{report['provider']}/{report['model']}: {len(documents)} documents in {wall:.0f} s; "
          f"slowest {slowest.get('seconds')} s ({slowest.get('kind')}); {llm.summary()}")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(2)
    asyncio.run(replay(sys.argv[1], sys.argv[2], sys.argv[3], int(os.environ.get("REPLAY_CONCURRENCY", "8"))))
