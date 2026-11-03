#!/usr/bin/env bash
# Exits when the implementer has finished writing the report, or at the time limit.
# Run from the repo root as a background job, so the exit wakes the reviewing session.
# Usage: bash docs/demo/loop/watch.sh [report_path] [max_seconds] [settle_seconds]
report="${1:-docs/demo/loop/REPORT.md}"
max="${2:-7200}"
settle="${3:-15}" # the file must stop changing for this long, so a half-written report is not read

start=$(date +%s)
while :; do
  now=$(date +%s)
  if [ -s "$report" ] && [ $((now - $(stat -c %Y "$report"))) -ge "$settle" ]; then
    echo "READY $report"
    exit 0
  fi
  if [ $((now - start)) -ge "$max" ]; then
    echo "TIMEOUT no report after ${max}s"
    exit 0
  fi
  sleep 5
done
