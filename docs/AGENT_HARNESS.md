# Codex / OpenCode execution

Updated 7 November 2026. Codex orchestrates; OpenCode implements connected slices using the user's selected **DeepSeek V4.1 Flash**. Installed CLI observed today: `opencode v2.2.6`; local model listing includes `opencode/deepseek-v4.1-flash` and `opencode/deepseek-v4.1-flash-free`. The existing explicit selector is `opencode/deepseek-v4.1-flash-free#high`; listing establishes availability in the catalogue, not successful inference/quota. No model call was made in this cleanup. Do not substitute providers silently.

## Per-task loop

1. Read AGENTS.md, PROGRESS.md and tasks/current.md. Load only task-relevant contracts, policy sections and skills. Use focused CodeGraph queries for structure.
2. Codex captures branch/HEAD, dirty paths and task-file baseline under ignored `.agent-runs/<run-id>/`; prepare exact write scope, caller integration and acceptance criteria. Preserve existing untracked work. One writer per file; B-owned files require a B assignment.
3. Assign one connected slice. OpenCode implements the caller-to-output behavior, updates its technical docs, runs only focused critical checks, and returns changed paths/results/limits. A new API without its required caller is incomplete.
4. Mark COMPLETED when the bounded acceptance criteria have evidence; otherwise BLOCKED with exact cause/restart condition. Codex inspects actual changes/output and resolves concrete defects; a separate audit queue is not a completion gate. Archive the brief and reconcile concise master state.
5. Continue eligible work only within authorized implementation scope. A context/harness-only request ends with the next feature brief PENDING. Do not repeat passing suites or provider probes without a relevant change or new evidence.

## Invocation

From the repository root, after assignment (not for a PENDING brief):

```powershell
$runId = 'TASK-ID-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff')
$runDir = Join-Path '.agent-runs' $runId
New-Item -ItemType Directory -Path $runDir -ErrorAction Stop | Out-Null
git status --short | Set-Content (Join-Path $runDir 'status-before.txt')
git diff --stat | Set-Content (Join-Path $runDir 'diff-before.txt')
& opencode run --agent build --model 'opencode/deepseek-v4.1-flash-free#high' --format json --file tasks/current.md 'Implement the assigned connected slice. Follow AGENTS.md; preserve existing work. Run focused critical checks once, update task result and return evidence. Do not edit outside allowed paths.' 2>&1 |
    Tee-Object -FilePath (Join-Path $runDir 'output.jsonl')
$runExit = $LASTEXITCODE
Set-Content (Join-Path $runDir 'exit-code.txt') -Value $runExit
```

Hold the process handle; inspect exit/errors and actual file changes. Exit zero alone is not completion. Before retrying an interrupted task, verify its session is inactive and inspect partial edits. Use the recorded exact session only when it fits the request budget; never `--continue` into an unknown session. Do not stop the shared OpenCode service, change global permissions or add blanket auto-approval. Keep raw transcripts ignored and credentials out of output.

## Context and failure budget

Use a fresh task-specific session. Limit individual reads explicitly; automatic compaction and tool-output caps are not hard provider TPM guarantees. Estimate the complete request, including system/tool schemas and output allowance, against the selected provider's actual limits. Old Groq 8,000-TPM failures are historical, not a DeepSeek prerequisite. The existing `a001-lean` profile/Groq output override in opencode.jsonc is legacy configuration; the command above selects `build` and DeepSeek explicitly. Do not use that A-001 profile for general work or change unrelated provider settings.

Do not rerun skill-discovery/model-health probes before every task. One bounded diagnosis per repeated external failure; record the actual error and move to independent work. Never turn empty provider data or skipped tests into success. Keep all acceptance criteria in the brief even when implementation must be split.

## Completion evidence

Record outcome, actual callers, changed paths, dataset/provenance changes (or none), commands/results/skips, unresolved limits and next dependency. Retain detailed evidence in task records; PROGRESS.md contains only current state and links. Disposable migrated DBs for database tests; never seed/reset the shared DB or delete Docker volumes. The independent hackathon judge assesses product evidence; it is not a second code-acceptance gate.
