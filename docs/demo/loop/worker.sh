#!/usr/bin/env bash
# One round of the loop: Antigravity reads NEXT_PROMPT.md, works, writes REPORT.md, exits.
# The lead starts this as a background job. Its exit wakes the lead, so no paste is needed.
#
#   worker.sh                  start the round in NEXT_PROMPT.md
#   worker.sh <conversation>   continue a run that stopped on a refused command
#
# WORKER_ROOT overrides the repo (trial runs). WORKER_LOGS overrides the log folder.
set -u

LOOP="$(cd "$(dirname "$0")" && pwd)"
ROOT="${WORKER_ROOT:-$(cd "$LOOP/../../.." && pwd)}"
LOGS="${WORKER_LOGS:-${TMPDIR:-/tmp}/samudrasense-worker}"
AGY="$HOME/.gemini/bin/agy.exe"
SETTINGS="$LOOP/worker-settings.json"
REPORT="docs/demo/loop/REPORT.md"
PROMPT_FILE="docs/demo/loop/NEXT_PROMPT.md"
CONVERSATION="${1:-}"

refuse() { echo "WORKER_REFUSED $1"; exit 2; }

cd "$ROOT" || refuse "no repo at $ROOT"
[ -x "$AGY" ] || refuse "agy not found at $AGY"
[ -f "$PROMPT_FILE" ] || refuse "no $PROMPT_FILE"
[ "$(git branch --show-current)" = "b/sprint" ] || refuse "branch is not b/sprint"
[ ! -e "$REPORT" ] || refuse "$REPORT exists, so the last round is not closed"

if [ -z "$CONVERSATION" ]; then
  # A finished or chat-pasted round moves HEAD, so this also stops a round running twice.
  BASE="$(sed -n 's/^Base commit: *//p' "$PROMPT_FILE" | head -n 1 | tr -d '[:space:]')"
  [ -n "$BASE" ] || refuse "no Base commit line in $PROMPT_FILE"
  [ "$(git rev-parse HEAD)" = "$BASE" ] || refuse "HEAD is not the round's base commit $BASE"
fi

RULES='You run unattended. No person can answer you or approve anything.

Shell rules. run_command always runs in the repo root and has no working-directory setting. Only the forms below are allowed. Any other command ends your run at once, with no report.
  In apps/web, run the tests:           npm --prefix apps/web test
  In apps/web, run one test file:       npm --prefix apps/web test -- <test file>
  In apps/web, run the build:           npm --prefix apps/web run build
  Read git state:                       git status, git log, git diff, git show, git rev-parse
  Stage one file:                       git add <exact path>
  Commit:                               git commit -m "subject" -m "body"
Run no other command, not even to check the shell, list files or read files. Run one command at a time. Do not chain commands with && or ; and do not use | or >. Copy command output into your report by hand.

Tools. To read, search and write files, use your file tools. Stay inside this repo. Do not use the browser, the web, MCP, subagents, schedules or messages.

If a command fails, read its output and fix the cause. If a command is refused, do not try another way to do the same thing. If you need something these rules do not allow, write docs/demo/loop/REPORT.md with STATUS: BLOCKED, say what you need, and stop.'

if [ -n "$CONVERSATION" ]; then
  TEXT="$RULES

Your last command was refused, or your run stopped early. Continue the work in $PROMPT_FILE from where you stopped. Do not run the refused command again."
  RESUME=(--conversation "$CONVERSATION")
else
  TEXT="$RULES

Now read $PROMPT_FILE and carry it out exactly."
  RESUME=()
fi

mkdir -p "$LOGS"
STAMP="$(date +%H%M%S)-$$"
STREAM="$LOGS/run-$STAMP.stream"
ERRORS="$LOGS/run-$STAMP.err"

# --print-timeout returns partial output with exit 0, so the status below matters more
# than the exit code. The outer timeout is the backstop if agy itself hangs.
timeout 2700 "$AGY" -p "$TEXT" "${RESUME[@]}" \
  --settings "$SETTINGS" \
  --print-timeout 40m \
  --output-format stream-json \
  --log-file "$LOGS/run-$STAMP.log" \
  > "$STREAM" 2> "$ERRORS" < /dev/null
CODE=$?

echo "WORKER_EXIT code=$CODE"
node - "$STREAM" <<'NODE'
const fs = require('fs')
const events = fs.readFileSync(process.argv[2], 'utf8').split('\n').filter(Boolean)
  .flatMap((line) => { try { return [JSON.parse(line)] } catch { return [] } })
const counts = {}
const commands = []
for (const { event, step_update: step } of events) {
  if (event !== 'step_update' || step.step_type !== 'tool') continue
  if (step.state !== 'DONE' && step.state !== 'ERROR') continue
  counts[step.tool_name] = (counts[step.tool_name] || 0) + 1
  if (step.tool_name === 'run_command') {
    const command = String(step.tool_info?.parameters?.CommandLine || '').replace(/\s+/g, ' ').slice(0, 160)
    // A refused command can also end as DONE, with no output at all.
    const label = step.state === 'ERROR' ? 'REFUSED/FAILED' : step.tool_info?.output ? 'ran' : 'NO OUTPUT'
    commands.push(`${label}: ${command}`)
  }
}
const result = events.find((e) => e.event === 'result')?.result
console.log(`STATUS ${result?.status ?? 'no result event'}`)
console.log(`CONVERSATION ${result?.conversation_id ?? events[0]?.conversation_id ?? 'unknown'}`)
console.log(`SECONDS ${Math.round(result?.duration_seconds ?? 0)}`)
console.log(`DENIED ${JSON.stringify(result?.denied_actions ?? [])}`)
console.log(`TOOLS ${Object.entries(counts).map(([k, v]) => `${k}=${v}`).join(' ') || 'none'}`)
commands.forEach((c) => console.log(c))
NODE
echo "STDERR $(grep -v '^$' "$ERRORS" | cut -c1-240 | head -n 3)"
if [ -s "$REPORT" ]; then echo "REPORT yes"; else echo "REPORT no"; fi
echo "HEAD $(git rev-parse HEAD)"
echo "STREAM $STREAM"
git status --short
