# Current v1 handoff

Updated 9 November 2026. Branch: `ap`.

The integrated v1 implementation is complete and its focused automated checks
have passed. The current owner records are:

- A/backend: `tasks/parallel/A-v1.md`
- B/frontend: `tasks/parallel/B-v1.md` and `tasks/parallel/B-status.md`
- C/evaluation: `tasks/parallel/C-v1.md`

## Verified implementation

- The isolated A database migrated from 016 to `017 (head)`; the shared
  database was neither reset nor seeded.
- Backend focused checks: 27 passed, 11 skipped (database-gated fixtures).
- Frontend checks: 17 files / 221 tests passed; production build completed.
- ML baseline checks: 6 tests passed; synthetic CLI produced two folds and
  truthfully reported its real-data gate `blocked`.
- The isolated API at `:8001` returned 200 for `/health` and `/openapi.json`
  after restart, exposing 68 versioned API paths.

## What A completed

A owns the v1 backend: migration 017, bounded idempotent AIS import and
quarantine, alert review state, protected-boundary provenance, SAR ambiguity
and unidentified-object cases, evidence graph/weather/coverage triage,
descriptive SST scan planning, operational source jobs/status, exact-hash
local report delivery and an explicit unavailable spill capability contract.

## What B completed

B owns the professional operational frontend: Overview, Ocean, SAR, alerts,
evidence, Operations, reports/delivery and spill capability/job screens. The
active product contains no presenter/demo-plan UI and no client-side synthetic
spill trajectory. It represents unavailable external capabilities as unknown or
unavailable.

## Remaining human/external gates

- One recorded browser journey against the isolated 017 stack for the final
  demo video.
- PyGNOME plus compatible wind/current/coastline forcing for real spill runs.
- Permitted point SAR, licensed verified boundaries/rules, and bounded
  availability-aware effort/chlorophyll/current history for empirical claims.
- Rotate/revoke historical provider values that were previously exposed in
  Git history; `.env.example` itself is sanitized.

Do not claim live coverage, legal conclusions, a real spill forecast, external
delivery receipt or empirical hotspot accuracy without those gates.
