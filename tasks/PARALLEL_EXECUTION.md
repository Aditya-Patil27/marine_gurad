# Two-session execution plan — 8 November 2026

The user authorizes A and B to implement successive eligible phases through the existing F01–F14 scope, stopping on a failed acceptance gate or required human intervention. This replaces the one-current-slice scheduling restriction for this run only. It does not authorize deployment, paid access, external messages, secret rotation, history rewriting or expanding the product.

## Starting point

Local `ap` was fast-forwarded to B's `dde0c11` on 8 November; all pre-existing dirty and untracked file hashes were preserved. A-004F and migration 014 are implemented but uncommitted. B-005F has no implementation yet. No OpenCode session has been launched by Codex. Both prompts below are intended for two fresh sessions in this exact checkout; do not start them in a clean checkout that lacks these changes.

The existing backend and frontend are the baseline. Today prioritizes the reviewed event journey, replay correctness, access control, truthful source status and reproducible demonstration. Later phases retain the full product scope and original deadlines; they are not promises of same-day completion. Optional models are excluded until all required gates pass.

## Ownership and concurrency

| Writer | Allowed paths |
|---|---|
| A | `apps/api/**`, `infra/**`, `docs/contracts/**`, `docs/DATA_MANIFEST.md`, `docs/evaluation/**`, `tasks/parallel/A-*`, `.agent-runs/parallel-A-*` |
| B | `apps/web/**`, `docs/design/**`, `docs/demo/**`, `tasks/B-005F.md`, `tasks/parallel/B-*`, `.agent-runs/parallel-B-*` |
| Codex after both stop | Master state: AGENTS, PLAN, PROGRESS, DECISIONS, README, ARCHITECTURE, backlog, current and this plan |

This is an explicit same-checkout exception to the usual separate-worktree preference: disjoint writers and no concurrent Git mutations. Neither session stages, commits, merges, switches branches, stashes, resets, pushes or changes global configuration. Neither edits the other owner's files, even to fix a failing integration. Read the partner's handoff, report the defect in your own status, and stop the affected phase. Preserve inherited changes, including the sanitized `.env.example`; never print secrets or raw sensitive diffs. Do not spawn additional agents.

Use separate test databases, containers, networks and ports. A owns schema changes and shared runtime configuration. Never reset/seed the shared database, delete shared volumes or run automatic migrations against it while the other session is testing. A uses an isolated development/test stack; B's browser checks use a separately migrated disposable database and a stable backend snapshot supplied by A. Reserve backend ports 8001 for A and 8002 for B, frontend 5174 for B if free; check before binding. Do not stop a process you did not start.

A publishes a stable backend snapshot/runtime recipe and its schema/contract version before changing APIs B is testing. A may assemble a local image or ignored snapshot from the current working code, including uncommitted A-004F; no live source mount that changes under B. B may start that supplied snapshot with its own disposable database. Configuration/credentials stay local; report only non-secret identifiers. If this runtime cannot be prepared, B can complete unit work but must leave the real-browser criterion incomplete.

## Shared execution loop (both prompts require this)

1. Read AGENTS, PROGRESS, current, this plan and your prompt. Capture HEAD, dirty path inventory and task-owned baseline hashes under your ignored run directory without logging credentials. Use the configured Ponytail rules and relevant project skills. Use CodeGraph for structure; do not repeat whole-repository exploration.
2. Create your own `tasks/parallel/A-status.md` or `B-status.md`. Only its named owner writes it. Record phase, state, changed paths, test evidence, published contract/runtime version, dependencies, blocker and exact restart instruction. Read the partner's status at phase boundaries, not in a polling loop. Never write a shared progress file.
3. Before a phase, read only its relevant F requirements from `docs/FINAL_PRODUCT_PLAN.md`. Write a bounded phase brief in your `tasks/parallel/A-<phase>.md` or `B-<phase>.md`: outcome, allowed paths, callers, dependency versions and exact acceptance checks. Split a large phase into connected slices there; do not drop requirements. Freeze request/response examples before parallel caller work.
4. Implement the smallest complete slice. Reuse existing stack, helpers and dependencies. Preserve source modes, permissions, UTC semantics and missing-data behavior. A loads the Postgres skill before database changes and the dataset skill before acquisition. Never fabricate missing records, rights, evaluation, provider availability or browser results.
5. Run focused checks once. Routine failures can be diagnosed and fixed within scope, with at most two fix/retest attempts per failing gate. After that, or immediately for missing essential credentials/rights, destructive action, scope choice or partner-owned defect, record BLOCKED/FAILED and stop your session. No endless retry or skipping a failed phase to claim progress elsewhere.
6. Mark the slice/phase COMPLETED only when all its acceptance checks have evidence. Publish your status with concrete contract changes and fixtures. Continue immediately to the next eligible phase without asking for approval or waiting for a Codex audit. Passing backend tests do not establish integrated UI completion.
7. A phase whose partner dependency has not landed is WAITING, not failed. Choose the next explicitly listed independent phase if any; retain the waiting gate. If none is ready, stop with the exact dependency. Do not invent a contract or treat fixture-only UI as integrated. A failure or human blocker stops the session, even if other optional work exists.
8. Keep context bounded. At a phase boundary record a compact restart handoff; if the next phase cannot fit the provider request/context budget, stop with READY_TO_RESUME and the exact next phase. Do not continue an oversized session. Session prompts do not provide an external restart watchdog: process exit/quota failure requires restarting from the saved status.

## Phase dependencies through full completion

| Phase | A backend/integration | B interface/evidence | Gate |
|---|---|---|---|
| 0 | Preserve A-004F; publish stable 014 runtime | Implement B-005F | Existing event-only contract; real reviewed browser journey |
| 1 | Replay-aware stored alerts, provenance/status | Replay alert caller after A1; role/error UX | Same window, score/source identity, no duplicate lifecycle records |
| 2 | Complete route authorization and account/settings gaps | Auth/roles/settings against A2; early accessibility work can proceed independently | Role/CSRF denial matrix and browser permission states |
| 3 | Report detail, verification/export and approval/revision gaps | Full report review, PDF/manifest and draft/revision UX | Traceable facts, tamper/stale rejection, authenticated approval |
| 4 | Incremental ingestion/jobs/source operations | Source status, job actions and configuration | Bounded inputs, idempotent replay/restart, visible failures |
| 5 | Licensed boundaries and point SAR, unknown-object cases | Boundary source panel, SAR ambiguity and unknown-object journey | Permitted real samples; no invented MMSI/points |
| 6 | Review decisions, notes, time-aligned encounters/weather | Linked evidence timeline/graph and reviewer actions | Traceable inputs, sparse-gap tests, actor/version history |
| 7 | Environmental inputs, baselines/backtest/scan budgets | Ocean/forecast/scan screens | Time-separated real-data evaluation, dates/units/uncertainty |
| 8 | GNOME runtime, forcing, bounded scenario jobs | Spill form, cancellation, time steps and affected areas | Reproducible reference plus real forcing; no toy replacement |
| 9 | Offline cache/scheduler, verifier, retention, delivery outbox | Licensed offline map/assets, offline workflow and delivery UI | Offline case/export; local mail sink; safe reconnect |
| 10 | Security/resource/recovery/install release checks | Viewports/accessibility/reviewer/demo/install acceptance | Every F01–F14 criterion evidenced or explicitly incomplete |

Follow each lane's detailed prompt for ordering within this map. Backend F05/F09 may require generalizing beyond MMSI; that is later scoped work, not a claim made by A-004F. GNOME or data-rights failures are real gates. Do not relabel a limited judging demo as full v1.

## Launch

Open two fresh OpenCode sessions in `C:\Users\Adish\HelloCode\marine_gurad`, using the existing `opencode/deepseek-v4.1-flash-free#high` selection. Paste the corresponding prompt file, or use the CLI commands in those files in two separate terminals. Never use the interrupted historical session or unspecified `--continue`. These commands launch work only when the user runs them. No auto-push is included.
