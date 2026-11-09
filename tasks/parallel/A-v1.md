# A v1 — connected backend product slice

Status: COMPLETED — 9 November 2026. Owner: A only.

## Implemented

- Migration 017 adds bounded import jobs/checkpoints/quarantine, AIS record
  identities/quality flags, alert reviewer state/assignee/notes/clear scenarios,
  protected-boundary/rule provenance, SAR candidate associations, unidentified
  SAR case links and a report delivery outbox.
- AIS import accepts at most 1,000 records, validates WGS84/time/AIS unknown
  codes, records late/out-of-order delivery, deduplicates source identities and
  preserves invalid record summaries in quarantine.
- Investigation routes expose versioned boundaries/rules, alert workflow,
  one/two-hop observed encounter graphs, weather/coverage triage, multi-candidate
  SAR association and SAR-object case creation without an invented MMSI.
- The prepared historical SST subset drives a truthful descriptive baseline and
  bounded scan plan with at least 20% non-ranked coverage. Missing effort history
  blocks evaluation rather than producing a forecast claim.
- Source job status/cancel, offline remote-fetch pause, cache/disk/worker/backup
  status and a persistent exact-hash local report sink are reachable through
  authenticated routes. Public recipients are not supported; the sink accepts
  only `.test` addresses and never claims receipt/read status.
- Spill capability is explicit but unavailable. PyGNOME and compatible
  wind/current forcing are absent, so execution is rejected and no toy or
  zero-current trajectory is returned.

## Changed A-owned paths

- `apps/api/alembic/versions/017_v1_operations.py`
- `apps/api/app/api/{ingest,sar,cases,alert_records,weather,ocean,sources,v1}.py`
- `apps/api/app/{config,main}.py`, `apps/api/app/models/vessel.py`
- `apps/api/tests/test_v1_contracts.py`, `apps/api/.env.example`
- `infra/docker-compose.yml`
- `docs/contracts/V1_OPERATIONS_API.md`, `docs/DATA_MANIFEST.md`

## Verification

- Isolated A database migrated from 016 to `017 (head)`; the shared database
  was not reset or seeded.
- `PYTHONPATH=/app python -m pytest -q tests/test_v1_contracts.py
  tests/test_report_gfw_evidence.py tests/test_alert_records_integration.py
  tests/test_report_authorization.py tests/test_report_exports.py`:
  **27 passed, 11 skipped** (the skips are database-gated fixtures).
- Restarted the isolated backend at `:8001`: `/health` and `/openapi.json`
  returned 200, with 68 v1 API paths exposed.
- Frontend and evaluation results are recorded in B-v1 and C-v1 respectively.

## External blockers and honest limits

- A real GNOME scenario needs an approved PyGNOME worker/runtime plus compatible
  wind/current/coastline forcing files for the event period.
- Real point SAR evidence needs a permitted point export/provider dataset and its
  licence reference; the configured GFW access has not supplied one.
- Real protected boundaries/rules need licensed geometry and verified local
  activity/season restrictions. Existing polygons remain visibly synthetic.
- Fishing-effort history, chlorophyll and currents were not acquired. The ocean
  surface is descriptive SST, not a promoted activity forecast.
- Backup/restore and worker liveness are reported `not_verified`; this feature
  pass did not claim an operational drill.
