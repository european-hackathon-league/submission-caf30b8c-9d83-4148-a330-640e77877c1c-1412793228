"""Checks the local scorer against Atira's official scores.

Every sandbox run's record (GET /v1/runs/<run_id>, saved as JSON) holds the submitted answer and the official
quality. This script scores each saved answer locally and reports the difference, so the scorer stays calibrated
as new runs come in. The run records and the reference answer hold scenario values: they live in the local-only
docs/ folder, never in the repo.

Usage: python tuning/calibrate.py <reference.json> <folder with run records>
"""
from __future__ import annotations

import glob
import json
import os
import sys

from scorer import score


def main(reference: str, folder: str) -> int:
    golden = json.load(open(reference, encoding="utf-8"))
    worst = 0.0
    for path in sorted(glob.glob(os.path.join(folder, "*.json"))):
        record = json.load(open(path, encoding="utf-8"))
        answer, official = record.get("answer"), (record.get("score") or {}).get("quality")
        if not answer or official is None:
            continue
        local = float(score(answer, golden).quality)
        worst = max(worst, abs(local - official))
        print(f"{os.path.basename(path)[:-5]:<24} official {official:>6}  local {local:6.2f}  diff {local - official:+6.2f}")
    print(f"max deviation {worst:.2f}")
    return 0 if worst < 0.01 else 1


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
