# V1 operations API contract

All paths are below `/api/v1`. Reads require Viewer; mutations require Analyst
or Administrator plus the session CSRF token. Timestamps are UTC. Missing
provider data is `unknown`/`unavailable`, never a negative finding.

## Investigation

- `GET /boundaries` returns GeoJSON boundary versions, publisher/citation/use
  metadata and separately verified restriction rules. Existing local polygons
  are labelled `synthetic`, `unversioned` and `unverified` by migration 017.
- Stored alerts include `reviewer_state` (`new`, `watch`, `in_review`, `closed`),
  `assigned_to`, `resolution_reason`, `clear_scenario` and authored `notes`.
  `POST /alerts/stored/{id}/review` and `/notes` require `expected_version`.
- `POST /sar/detections` stores a permitted point and all AIS candidates within
  the baseline 2 km/15 minute window. It returns `matched`, `ambiguous`,
  `unmatched` or `insufficient_coverage`; unknown coverage is never called an
  unmatched vessel. `GET /sar/detections/{id}` returns candidates and explicit
  image availability.
- `POST /cases/` accepts exactly one of `assessment_id`, event-only `report_id`
  or `sar_detection_id`. Unidentified/ambiguous SAR cases have no invented MMSI.
- `GET /vessels/{mmsi}/encounters` returns a bounded one/two-hop graph from
  actual time-near observations. Sparse inputs cannot gain duration by
  interpolation.
- `GET /triage/evidence/{mmsi}` aligns event-time weather and observation-density
  context. It never changes risk or closes an alert.

## Planning and operations

- `GET /ocean/baseline` exposes the prepared historical SST grid as a
  descriptive persistence baseline. Activity evaluation remains blocked until
  time-aligned effort history exists. `POST /ocean/scan-plans` reserves at least
  20% of its bounded budget for non-ranked coverage and does not task satellites.
- `/sources/jobs` exposes stable import job IDs, progress/checkpoints,
  quarantine and optimistic cancellation. `/ingest/ais` accepts 1–1000 records,
  deduplicates source record IDs, records late/out-of-order flags and quarantines
  invalid records without inventing movement.
- `GET /operations/status` reports cached-data age, job depth, disk state and
  honest unknown worker/backup checks. `OFFLINE_MODE=true` pauses remote source,
  weather and uncached marine requests while local investigation remains usable.
- An approved exact report hash can be queued once with
  `POST /reports/{id}/deliveries`. V1 accepts only reserved `@example.test`
  recipients. `POST /reports/deliveries/{delivery_id}/submit` writes one
  canonical envelope to the persistent local file sink. `submitted` does not
  mean received or read; retry is capped at three attempts.
- `GET /spill/capabilities` currently returns `unavailable`. `POST /spill/jobs`
  returns 503 because PyGNOME and compatible wind/current forcing are absent.
  No toy trajectory or silent zero-current fallback is produced.
