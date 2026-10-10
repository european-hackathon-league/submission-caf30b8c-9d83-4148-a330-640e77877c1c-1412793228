#!/usr/bin/env bash
# Several sandbox test runs of one branch, one after another (never a submission), for a reliability series.
#
#   REF=origin/<branch> RUNS=4 bash tuning/batch_runs.sh
#
# Each run goes through the main runner (official record to docs/runs/official, one line in docs/runs/main_runs.tsv);
# its log is saved to docs/runs/logs, and the run report is printed at the end. Holds no scenario values.
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO" || exit 1
RUNS="${RUNS:-4}"
REF="${REF:-origin/main}"
A="$LOCALAPPDATA/atira/bin/atira.cmd"
cp tuning/main_runner.sh tuning/.runner_batch.sh  # a private copy: editing the runner must not break a running batch
for number in $(seq 1 "$RUNS"); do
  for _ in $(seq 1 30); do  # Atira allows 3 queued test runs per team: wait for a free place
    [ "$("$A" status 2>&1 | grep -cE " queued")" -lt 3 ] && break
    sleep 60
  done
  echo "=== batch run $number of $RUNS on $REF ($(date -u +%H:%M) UTC)"
  out=$(NOWAIT=1 REF="$REF" bash tuning/.runner_batch.sh 2>&1)
  echo "$out" | tail -2
  run=$(echo "$out" | grep -o "run_[0-9a-f]\{16\}" | head -1)
  [ -n "$run" ] || continue
  token=$("$A" token)
  python -I - "$run" "$token" <<'PYEOF'
import json, sys, urllib.request
run, token = sys.argv[1], sys.argv[2]
cursor, chunks = 0, []
for _ in range(400):
    request = urllib.request.Request(f"https://ehl-challenge.atira.ai/v1/runs/{run}/logs?after={cursor}", headers={"x-api-key": token})
    try:
        page = json.load(urllib.request.urlopen(request, timeout=60))
    except Exception:
        break
    if not page.get("chunks") or page.get("cursor") == cursor:
        break
    chunks += page["chunks"]
    cursor = page["cursor"]
json.dump(chunks, open(f"docs/runs/logs/{run}.full.json", "w", encoding="utf-8"), ensure_ascii=False)
PYEOF
done
echo "=== run report"
python -B tuning/run_report.py | head -1
python -B tuning/run_report.py | tail -n +2 | sort -t'|' -k1,1 | grep -Ff <(grep -o "run_[0-9a-f]\{8\}" docs/runs/main_runs.tsv | sed 's/run_//' | tail -"$RUNS") || true
