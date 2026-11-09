# A session status

Owner: A only. State: READY_TO_RESUME — A2 complete; next phase is A3.
Queue: `tasks/OPENCODE_A_PROMPT.md`; rules: `tasks/PARALLEL_EXECUTION.md`.
Baseline: local app at `dde0c11` plus inherited dirty A-004F/migration 014; current B snapshot image `samudrasense-api:014-a1`.

## Phases this run

| Phase | State | Record |
|---|---|---|
| A0 stable 014 runtime for B | COMPLETED | `tasks/parallel/A-A0.md` |
| A1 replay-aware stored alerts / truthful status | COMPLETED | `tasks/parallel/A-A1.md` |
| A2 route authorization + identity/settings | COMPLETED | `tasks/parallel/A-A2.md` |
| A3 report/export guarantees | TODO | — |
| A4 ingestion/jobs/sources | TODO | — |
| A5 boundaries + point SAR / unknown objects | TODO | — |
| A6 reviewer state / encounters / weather | TODO | — |
| A7 environmental inputs + baselines | TODO | — |
| A8 GNOME scenario service | TODO | — |
| A9 offline/retention/optional delivery | TODO | — |
| A10 release verification | TODO | — |

## Runtime identifiers (non-secret)

- B snapshot: image `samudrasense-api:014-a1` (`sha256:e097af2fae08…`), schema `014 (head)`, contracts A-004F and A1.
- B backend `http://localhost:8002`; A backend `http://localhost:8001`; separate Postgres `5433`/`5434`, Redis `6380`/`6381`.
- B start/migration/health/account recipe: `tasks/parallel/A-A0.md`.
- Shared stack at `:8000` was not restarted, migrated or seeded.

## A1 evidence / contract

- Focused unit/API checks: 27 passed.
- Disposable migrated PostGIS checks: 4 passed; database removed afterward.
- B1 contract: optional exact bounds on `POST /alerts/sync`; response includes the resolved `window` and `stored_scope: "global"`. Stored lifecycle reads remain global.
- Record: `tasks/parallel/A-A1.md`.

## A2 evidence / contract

- Every mounted application route outside root/health/docs/login has an
  identity dependency; read-only data routes require Viewer.
- Administrator user and persistent deployment-settings APIs are at
  `/api/v1/admin`; mutation calls require CSRF. Migration head is now `015`.
- Focused disposable authorization/admin checks: 28 passed; migration
  downgrade/upgrade round trip passed; database removed afterward.
- Record: `tasks/parallel/A-A2.md`.

## A3 verification hold

A3 is complete: `tasks/parallel/A-A3.md` records migration `016`, 12 focused
container checks and 17 disposable-database checks. The disposable database was
dropped; the shared stack was not touched. A4 is the next backend phase.

## Blockers / restart

A3 is complete and A4 is next. Restart instruction: read this file and
`tasks/parallel/A-A3.md`, then create the bounded A4 brief. B may integrate
A2 account/settings contracts, but the current stable B image is the A1
snapshot at schema 014 and must be refreshed/migrated before browser-testing A2.
