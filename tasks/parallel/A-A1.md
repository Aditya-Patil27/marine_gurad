# A1 — replay-aware stored alerts and truthful status

Status: COMPLETED — 8 November 2026. Owner: A only.

## Outcome

`POST /alerts/sync` now accepts the shared optional replay window while preserving the bodyless rolling last-hour call. Historical generation selects the latest vessel observation and its prediction history strictly inside the requested UTC span. The persisted alert list remains global and the response says so explicitly. Stored source mode comes from the selected observation, late evidence extends the first observation without duplicating the record, and resolved alerts remain resolved.

Protected-area titles and descriptions now use screening language. Presence, proximity and predicted approach remain reviewer indicators and are not described as confirmed violations or proof of illegal activity.

## Changed paths

- `apps/api/app/api/alert_records.py` — optional bounded sync request, resolved window/global-scope response, historical generator call and late-observation lifecycle handling.
- `apps/api/app/api/alerts.py` — screening titles and limitations.
- `apps/api/app/services/alert_generator.py` — exact-window vessel/history queries with unchanged legacy rolling scan.
- `apps/api/tests/test_alert_window_sync.py` — validation, empty/source-mode and wording checks.
- `apps/api/tests/test_alert_window_integration.py` — migrated PostGIS exact-window and legacy-scan proof.
- `apps/api/tests/test_alert_records_integration.py` — global lifecycle, late record, repeat sync and resolved-state checks.
- `docs/contracts/USER_A_DATA_API.md` — exact A1 request/response and stored-scope semantics for B1.

No migration, dataset, provider call or configuration change was needed.

## Contract for B1

- Existing call: `POST /api/v1/alerts/sync` with no body scans the rolling last hour.
- Replay call: `POST /api/v1/alerts/sync` with `{ "lookback_hours": 72, "window_start": "2026-10-31T00:00:00Z", "window_end": "2026-11-02T00:00:00Z" }`.
- Bounds use the existing fleet rules: both or neither, explicit UTC offset, end after start, span at most 168 hours and no future end. Invalid selection is 422 before generator/database work.
- Response adds `window` and `stored_scope: "global"`. `observed: 0` is a valid empty selected window. `GET /alerts/stored` remains the global lifecycle list and must not be labelled as window-filtered.
- Repeating the same condition does not duplicate a row or reopen a resolved alert. `source_mode` is derived from stored observations.

## Verification actually run

- Focused container checks: `python -m pytest tests/test_alert_window_sync.py tests/test_alerts.py tests/test_alert_records.py -q` → **27 passed**. This includes an explicit rolling-lookback regression check so a body containing only `lookback_hours` cannot silently fall back to one hour.
- A uniquely named database `a1_verify_20261108` was created only on isolated `samudrasense_postgres_a`, migrated from empty through `014`, and used with `TEST_DATABASE_URL`.
- Disposable PostGIS checks: `python -m pytest tests/test_alert_records_integration.py tests/test_alert_window_integration.py -q` → **4 passed**.
- The first disposable run exposed an invalid subquery alias and a missing test UTC import; the second exposed that late evidence was stored but not counted/evented as an update. The shared root causes were fixed, then the focused set passed.
- The disposable database was force-dropped after the passing run. Shared database/container data was not reset or seeded.

## Stable B runtime refresh

After A1 review, the source-frozen image `samudrasense-api:014-a1` (`sha256:e097af2fae08…`) replaced the pre-A1 backend on the isolated B stack. `samudrasense_backend_b` serves `http://localhost:8002`, reports healthy, and is at Alembic `014 (head)`. The B Postgres/Redis containers and volume were retained; the separate empty B database migrated normally to 014. The shared stack was not restarted, migrated or seeded. Start or restore this exact runtime with `docker compose -f infra/docker-compose.parallel-b.yml up -d backend`.

## Limits

No browser/B1 caller check was run; B owns that integration. The global stored list has no observation-window filter by design; the selected window is recorded on the sync response, not persisted as a new alert-list scope. No live source or regional coverage claim was made.
