---
name: samudra-handoff
description: Record SamudraSense implementation evidence, blockers and review handoff while keeping canonical project state concise and consistent.
---

Use `docs/AGENT_HARNESS.md` and the current task's report fields. A bounded task is COMPLETED when its acceptance criteria have evidence; a separate Codex audit is optional. Distinguish backend completion from a still-disconnected browser journey.

1. List exactly what changed and every modified file, separating inherited dirty changes from the current task. State actual integration/callers and remaining disconnected paths.
2. Record dataset changes with the canonical manifest entry; credentials never enter the report. Distinguish acquired, processed and integrated states. Keep rights, dates, modes and unknowns visible.
3. Record verification commands, results/skips and date; separate current execution from prior evidence. Do not call a skipped disposable-DB test or a provider subscription with zero positions a passing feature.
4. Note technical decisions with reasons and conflicts with accepted decisions. OpenCode proposes these in its task result/owned docs; Codex updates `DECISIONS.md` after review. Do not silently reopen settled architecture.
5. OpenCode updates only assigned technical docs and current result/status, then returns the report through CLI. Include blockers, the exact missing user action when needed and whether the task is implemented or blocked. Do not edit Codex's master queue/state concurrently.
6. Codex inspects diffs/integration and records concrete defects without repeating passing checks or holding completed work in an audit queue. Archive completed briefs, update `PROGRESS.md` and backlog, and reconcile relevant plan/README changes. Keep original deadlines and incomplete gates honest. Prepare one bounded next brief with explicit dependencies; never continue feature development during a harness-only assignment.
