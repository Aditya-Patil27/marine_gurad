---
name: samudra-implementation
description: Implement a bounded assigned SamudraSense backend or integration task using existing modules, explicit acceptance checks and a review handoff.
---

Read `AGENTS.md`, `tasks/current.md` and the referenced contract. Confirm ASSIGNED or a documented revision, owner, write paths and dependencies. A queued PENDING task is not permission to start within a harness-only assignment.

1. Inspect dirty paths and the Codex baseline before editing. Use focused CodeGraph context for the task and source/impact only where needed; do not re-audit the repository.
2. Follow the brief's steps. Reuse FastAPI validation/session patterns, PostGIS, Celery and existing risk/fleet logic. Keep frontend ownership and existing contract fields intact. Read the Postgres skill before schema/SQL work; isolate optional heavyweight tools.
3. Implement the actual caller/pipeline connection specified by the brief. Preserve provenance/mode, UTC/coordinate units and bounded errors/retries. Missing data stays missing; no synthetic fallback disguised as real success.
4. If a required dependency is absent, record the exact criterion and evidence. Ask for missing local auth access without reading/printing secrets. Continue only independent authorized work. Do not change scope or invent architecture to evade the blocker.
5. Run the smallest meaningful correctness check. Use disposable migrated data for DB tests. Record skipped checks honestly; do not repeat passing tests without a relevant change. For repeated failures, report diagnosis and next action instead of looping.
6. Update only task-owned technical docs and the current task's implementation report. Return changed files, integration, dependencies/decisions, commands/results, data changes and outstanding issues through CLI as well. Mark COMPLETED when all scoped acceptance criteria have evidence, otherwise BLOCKED with the exact dependency. Codex reconciles state and assigns the next authorized task; do not expand scope or edit the master queue concurrently.
