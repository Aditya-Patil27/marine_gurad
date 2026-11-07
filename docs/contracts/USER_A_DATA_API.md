# User A data endpoints for User B

Updated 7 November 2026. Prefix: `/api/v1`. These are local prototype endpoints. The report routes and the ingest/SAR/chat mutation routes require an authenticated cookie session and CSRF as described below; the other routes here remain unauthenticated reads. Error responses use `detail` and appropriate HTTP status; show errors and empty data explicitly.

Additive historical selection (A-005B): vessel list/detail, assessment sync and report creation accept an optional explicit bounded UTC window (`window_start`/`window_end`). See [the exact contract](HISTORICAL_WINDOW_API.md) for validation, the shared `window` response object and the B caller brief. Omitting both fields keeps the existing rolling behavior. Persisted assessments store their actual window anchors, and a historical report with a mismatched or legacy assessment is rejected with 409 before insertion.

## Satellite observations

`GET /ocean/observations` returns `status`, `source`, `product`, `dataset`, `dataset_version`, `doi`, `source_sha256`, `prepared_at`, `kind`, `mode`, `unit`, `limitations`, and `values`. Each value has `observed_at` (UTC), `latitude`, `longitude`, and `temperature_c`. This is a **historical satellite-derived** sample for 18–20 October 2026, not live conditions. A missing local artifact returns 503. Do not assume an observation exists for every cell.

`GET /environment/regional` provides the latest regional environmental reading for User B's environmental card on the map and evidence views (`formatEnvironmentalReading` in `apps/web/src/lib/environment.js`). It selects the single observation with the latest timestamp from the prepared Copernicus satellite dataset (breaking ties deterministically by latitude then longitude).

Response schema:
- `variable`: string (explicitly "Historical satellite-derived sea surface temperature (single grid cell)")
- `value`: number (e.g. 29.72)
- `unit`: string ("°C")
- `observed_at`: string UTC ISO8601 (e.g. "2026-10-20T00:00:00Z")
- `attribution`: string ("Copernicus Marine Service (DOI: 10.48670/moi-00164)")
- `status`: "available"
- `mode`: "historical"
- `kind`: "satellite_observation"
- `location`: {"latitude": 8.149999618530273, "longitude": 78.55000305175781}
- `dataset`: "IFREMER-GLOB-SST-L3-NRT-OBS_FULL_TIME_SERIE"
- `limitations`: string noting single grid cell, historical satellite origin, and absence of live forecasting.

If the prepared artifact is missing, unreadable, or contains no valid candidates, the endpoint returns an explicit HTTP 503; no fabricated values or weather fallbacks are returned. This is currently an unauthenticated read endpoint like other ocean endpoints. Note that User B's frontend branch (`origin/b/sprint`) remains unmerged and report authentication still requires B's login/CSRF integration.

`GET /ocean/temperature?latitude=8.8&longitude=78.9` returns modelled recent SST, which is a separate source from the observations. Show its `kind`, `retrieved_at`, grid coordinates, valid times and limitations.

## Regional events

`GET /gfw/events/regional?start_date=2024-01-01&end_date=2025-01-01&offset=0&limit=20` queries a fixed Gulf of Mannar box. End date is exclusive; maximum interval is 366 days and maximum page size 50. Response includes `source`, `dataset`, `retrieved_at`, `delivery`, `requested_region`, `requested_start`, `requested_end_exclusive`, `limitations`, and provider `data` containing `entries`, `total`, `offset`, `limit` and possibly `nextOffset`. Preserve provider IDs and dates. Events represent inferred apparent fishing, not proof of fishing or illegality. They are historical, not live AIS.

For a selected event in a particular returned page, use:

`GET /gfw/events/evidence?event_id=EVENT_ID&start_date=2024-01-01&end_date=2025-01-01&offset=0&limit=20&include_regional_ocean_context=true`

Use the same date range, offset and limit as the page containing the event. The response downloads JSON with `snapshot`, `sha256`, and `integrity_note`. Optional regional context retains its original dates and states that it may not coincide with the event. A 404 means the ID was not found on that page. A 503 means data access, quota or the requested local observation artifact is unavailable. A checksum is not authenticated approval or a digital signature.

`GET /gfw/status` returns provider quota headers last observed by this backend process, their observation time, `local_requests_last_30_minutes`, and limitations. Provider usage counters may lag by 30 minutes; multiple app processes do not share this state.

### GFW Vessel Tracks Status

Direct raw vessel track retrieval (`GET /v3/vessels/{vessel_id}/tracks`) was investigated under task A-003A on 4 November 2026. The endpoint requires a dataset parameter conforming to `tracks:*` (e.g. `public-global-all-tracks:latest`). Calls using the configured token return HTTP 403 Forbidden (`"You do not have permission to access this dataset [public-global-all-tracks:latest]"`). The configured account was denied access to the two tested track dataset names; that result does not establish permissions for every dataset or account. The existing app can separately use permitted aggregated layers or behavioural events, which are not tracks. As a result, no real vessel track adapter endpoint is currently exposed on `/gfw/tracks`. Synthetic vessel tracks in the local database remain separate demo fixtures.

### GFW SAR Detections Access Status

Point-level SAR evidence access was investigated under task A-003C on 4 November 2026. The tested Global Fishing Watch SAR presence dataset is `public-global-sar-presence:v5.0` (`type: "4wings:v1"`). It is a gridded/raster spatiotemporal layer representing detection counts/presence across zoom cells, not a verified discrete point detection feed. This does not establish that other GFW products or datasets lack point access. The Events API (`/v3/events`) explicitly rejects it as not an `events:*` dataset (`422 Unprocessable Entity`), and the tested 4Wings report request (`/v3/4wings/report`) returned HTTP 404 with upstream message: `"This feature is temporarily unavailable because of infrastructure constraints and an upstream data dependency issue."` Because `apps/api/app/api/sar.py` requires discrete WGS84 point locations, scene IDs, and timestamps, and rules strictly forbid fabricating point coordinates from aggregate raster cells, no real SAR detection adapter is connected to `/api/v1/sar/detections`. The endpoint remains available for manual/analyst submission of candidate external points.

## Vessel details and data limitations

`GET /vessels/{mmsi}` returns the score breakdown, factors, checks, track, and an additive `limitations` array.
Vessel list and detail responses now include `source` and `source_mode` for the latest position (and per track point in detail), copied from the stored `vessel_tracks` row. Values are `live`, `historical`, `replay`, `synthetic` or `unknown`; missing provenance is `unknown`, never inferred from a configured provider. Demo seeding labels its rows `synthetic` with source `local demo seed`.
Vessel list and detail accept optional `window_start`/`window_end` (ISO 8601 with `Z`/offset, both together, span ≤168 h) and return the shared `window` object. This selects stored observations without rewriting their timestamps or source labels; an empty historical window returns an empty list or `404`, never current data.
The limitations are structured as a list of `{key, label, detail}` objects directly compatible with User B's `DataLimitations` component in `apps/web/src/pages/Cases.jsx`:
- `source_mode`: Explains that provenance is stored per position but may be `unknown` or `mixed`, and that shore/satellite reception gaps are unknown rather than complete.
- `indicators_not_proof`: Clarifies that AIS gaps, loitering, and encounters are investigative indicators, not proof of intent, transshipment, or an offence.
- `boundaries`: States that demo marine protected area boundaries are indicative and official gazetted limits and rules must be separately verified.
- `heuristic_score`: Affirms that the rule-based score is an explainable heuristic, not a validated probability or legal determination.

When a new report is created via `POST /reports/`, the snapshot captures this `limitations` array before calculating the SHA-256 digest, binding the limitations into the evidence integrity check.

Note: User B's frontend branch (`origin/b/sprint`) remains unmerged; frontend rendering of limitations on evidence and report pages will take effect once B merges and integrates session cookies and CSRF headers for report creation and signing.

## Legacy alert projection

`GET /alerts/?limit=50&severity=HIGH` remains a public read and the existing field shape is unchanged. It is an ephemeral projection over the current generator output, not a persisted alert list: nothing is acknowledged, resolved or deduplicated in storage.

- `id` is a deterministic UUIDv5 of `(type, mmsi, mpa_id or mpa_name)`, so repeated reads of the same condition return the same ID.
- `timestamp` is the latest stored vessel position time, not request time. It is stable while that position remains the latest one.
- Generator rows are deduplicated by the same identity, keeping the highest severity/risk row.
- `metadata` carries track `source`/`source_mode` plus `persisted: false` and `lifecycle: "ephemeral_projection"` so callers cannot present it as a stored lifecycle record.
- Severity filtering, sorting and `limit` are unchanged.

Persistent alert status, acknowledgement/resolution and cross-read deduplication are delivered by the additive lifecycle routes below; the public projection itself remains ephemeral.

## Persistent alert lifecycle (A-003G)

`POST /alerts/sync` requires an Analyst or Administrator session and matching CSRF cookie/header. It runs the existing generator once, deduplicates rows by the same stable identity as `GET /alerts/` and upserts `alert_records`. The response reports `observed`, `created`, `updated`, `unchanged`, `skipped_resolved`, aggregate `source_mode` and UTC `synced_at`. A new condition becomes `open`; a re-observed `open`/`acknowledged` record refreshes its facts without losing status; a `resolved` record is never silently reopened and is counted as skipped. Repeated timestamps never move `last_observed_at` backwards.

`GET /alerts/stored?limit=50&offset=0&status=open&severity=HIGH&mmsi=419007431` requires a Viewer or higher session; `limit` is 1–100, `offset` is nonnegative and all filters are optional. It returns `alerts`, `total`, `offset`, `limit` and `limitation`, ordered by `last_observed_at` descending. `GET /alerts/stored/{id}` returns one record plus its append-only `events` history.

Each stored record includes its stable UUID (shared with the live projection of the same condition), type, severity, MMSI, MPA identifiers, title/description snapshot, first/last observation times, optional location, metadata, track `source`/`source_mode`, `status`, optimistic `version`, acknowledgement/resolution actor and timestamps, optional resolution note and UTC created/updated times. It is marked `persisted: true`, `lifecycle: "stored"`.

Lifecycle transitions require Analyst/Admin plus CSRF and body `{"expected_version": N}`:

- `POST /alerts/stored/{id}/acknowledge` — `open` → `acknowledged`.
- `POST /alerts/stored/{id}/resolve` — `open`/`acknowledged` → `resolved`; optional `note` up to 500 characters is trimmed and stored.
- `POST /alerts/stored/{id}/reopen` — `resolved` → `open`.

A stale `expected_version` or an invalid transition returns 409; an unknown alert returns 404. Every create/observation/transition is recorded in `alert_events` with `system` or the session username as actor. Migration `011` creates both tables and constraints. Status reflects analyst action only, and the records are screening artefacts for human review, not proof of illegal activity. The B frontend does not yet render these routes.

## Existing prototype report

`POST /reports/` accepts `{"mmsi": 123456789, "include_regional_ocean_context": true}`. The optional flag defaults to false. If requested but unavailable, creation returns 503. The regional observations are included in the hashed report snapshot with a non-association statement. This existing route requires a recent vessel already in the database; it does not import the GFW event.
It also accepts optional `window_start`/`window_end` with the same validation as vessel evidence. The hashed snapshot then contains the shared `window` object and preserves the stored observation dates and source labels. When `assessment_id` is supplied and the report selects a historical window, the persisted assessment anchors must match the report window exactly; a different window, same-duration different anchors, a re-synced row or a legacy row without anchors returns 409 before any report is inserted, with a safe retry instruction. On a match, `snapshot.persisted_assessment` contains the stored `window`, the `report_window` and `window_match: true`, and both windows are hashed.

Set `include_weather_context: true` to capture fresh weather for the latest qualifying AIS gap into `snapshot.weather_context` before hashing. The result is modelled context, not a direct observation or a risk adjustment. `event_time_utc` is the gap start; `time_utc` and `wave_time_utc` are the selected wind and wave model times, which can differ from the gap time. `retrieved_at`, source, location and limitations accompany available results. If the provider is unavailable, the snapshot records `unavailable` with the known gap time/location; if no gap qualifies it records `not_checked`. No weather values are invented. This is fetched when the report is created and may differ from weather displayed earlier. The flag defaults to false.

Authentication now applies to this report API (A-002A). Send the session cookie and the `X-CSRF-Token` header from `/auth/login`. `GET /reports/` requires Viewer; `POST /reports/` requires Analyst (or Administrator); `POST /reports/{id}/sign` requires Approver (or Administrator) and still requires `reviewed: true`. Anonymous calls return 401; insufficient roles or a missing/wrong CSRF token return 403. The sign request keeps `officer` for compatibility but ignores it: the returned and persisted `signed_by` is the authenticated username. This is authenticated local approval, not a digital signature, immutable revision or dispatch. The current frontend must add login/cookies and the CSRF header before it can create or sign reports.

## Mutating prototype endpoints

A-002B protects the remaining mutation routes with `require_analyst` followed by
`csrf_protect`. Analyst or Administrator is required; Viewer and Approver-only
cannot mutate. Anonymous calls return `401`; an insufficient role or a
missing/wrong `X-CSRF-Token` returns `403`. Denied requests perform no DB write,
rescore, job or provider/model call.

- `POST /ingest/ais` — AIS batch ingest and recent-fleet rescore; payload and
  response unchanged.
- `POST /ingest/satellite-image` — runs the configured pollution detector on an
  http(s) image URL; still `503` when the model is not loaded. The pollution
  worker is not validated by this change.
- `POST /sar/detections` — stores an external georeferenced detection and the
  nearest AIS ping within 2 km and 15 minutes as a **candidate**. Missing AIS
  coverage is unknown, not evidence of deliberate evasion.
- `POST /chat/message` — forwards to the assistant; denied requests never reach
  Gemini or its tools.
- `POST /chat/reset` — returns the existing reset acknowledgement; no server
  history is stored.

Reads on these routers remain public: `GET /sar/detections` and
`GET /chat/health`. Any client calling the mutations must send the session and
CSRF cookies (`credentials: "include"` when not using the Vite proxy) and echo
`samudra_csrf` as `X-CSRF-Token`.

## Live AIS snapshot

`GET /aisstream/snapshot` returns a short, non-persistent live sample in `positions`, with requested `bounds_lat_lon`, `captured_at`, `mode`, `delivery` and `limitations`. It does not use the database's synthetic demo vessels. An empty list only means no usable positions arrived during the sampling window; it is not a coverage measurement. Provider reception timestamps may be absent and are not exact vessel observation times.

## Historical event map

`GET /gfw/events/regional/geojson?start_date=2024-01-01&end_date=2024-02-01&offset=0&limit=20` returns one map-ready GeoJSON FeatureCollection from the same bounded GFW query and cache as `/gfw/events/regional`. Dates are UTC and the end date is exclusive. Each point uses GeoJSON longitude/latitude and carries `event_id`, event times, vessel ID/name/MMSI when supplied. The collection includes provider, dataset, retrieval time, `mode: historical`, pagination, upstream total and count of omitted invalid positions. Pass the same event ID, date range, offset and limit to `/gfw/events/evidence` for an evidence export. A point is an inferred event location, not a track, live vessel position, proof of fishing or proof of illegality. The frontend shows it as a separately labelled historical layer; browser verification remains pending.

## Persisted vessel assessments (A-004A)

`POST /alerts/assessments/sync` requires an Analyst or Administrator session and matching CSRF cookie/header. Optional JSON `lookback_hours` defaults to 24 and is bounded to 1–168; optional `mmsi` restricts evaluation to one vessel. It evaluates the current database fleet with the existing rule engine, then atomically upserts assessments. The response contains `synced`, UTC `evaluated_at`, `lookback_hours`, `rule_version`, `source_mode` and the shared `window` object. Optional `window_start`/`window_end` select one explicit bounded UTC historical window (both together, span ≤168 h); `synced: 0` means that window had no positions. Each persisted row stores the resolved `window_mode` and exact `window_start`/`window_end` anchors as well as the effective duration; the same bounds should be passed to vessel evidence and report creation.

`GET /alerts/assessments?limit=20&offset=0` requires a Viewer or higher session; `limit` is 1–100 and `offset` is nonnegative. Optional `mmsi` filters to one vessel. It returns `assessments`, `total`, `offset`, `limit`, `source_mode` and `limitation`. Each assessment includes a stable ID, vessel identifier, score, factors, checks, evaluation time, the additive `window` object and available position/context. Pre-migration rows return `window: null` because their anchors are unknown; they are never inferred. IDs are stable for the same MMSI, rule version and source mode. Scores are screening indicators, not findings of illegal conduct.

Source mode is derived from the stored track provenance for the evaluated window: a single recorded mode, `unknown` when nothing was recorded, or `mixed` when the vessel's positions disagree. It is never inferred from a configured provider or from the presence of data. `POST /ingest/ais` accepts optional batch-level `source` (up to 120 characters) and `source_mode`; omitted values are recorded as `source: "caller-supplied AIS ingest"` and `source_mode: "unknown"`. Sync does not delete vessels outside its lookback. The public `/alerts/` projection and the current B frontend are unchanged; persisted alert lifecycle is available separately at `/alerts/stored` but is not yet rendered by B. Migrations `007`, `010`, `011` and additive `013` create the assessment table, provenance constraints, alert-record lifecycle and window anchors. Disposable database verifications are available via `PYTHONPATH=/app python scripts/verify_assessments_disposable.py` and `PYTHONPATH=/app python scripts/verify_alert_lifecycle_disposable.py` in the API container; they require CREATE DATABASE privileges and remove only the uniquely named database each creates.

`POST /reports/` optionally accepts `assessment_id` (UUID). It must identify an assessment for the submitted `mmsi`, otherwise the API returns 404 and does not insert a report. The stored assessment fields are copied into `snapshot.persisted_assessment` before hashing, so subsequent assessment updates do not alter the report. For a historical report window, the persisted assessment anchors must match exactly; otherwise the API returns 409 and inserts no report. Vessel details are independently evaluated when the report is created and their scores can differ. Existing report clients can omit this field. This does not link a real source record or create a case/revision workflow.

## Investigation case API (initial backend slice)

## Investigation triage

`GET /triage/assessments?limit=20&offset=0&mmsi=419007431` requires Viewer or
higher. It is a read-only, paginated queue over persisted assessments. Each row
contains the assessment score, level and source mode; counts of stored alerts
by status; counts of open/closed cases; and a deterministic `review_state`:
`under_review` when an open case exists, `needs_review` for a HIGH assessment
or active HIGH alert, otherwise `monitor`. Response weather is always
`not_checked`; this endpoint never calls a provider and cannot lower risk based
on unavailable weather. Triage is a reviewer aid, not proof of illegal activity.

`POST /cases/` accepts `assessment_id` (UUID) and `title` and requires Analyst plus CSRF; the session supplies `created_by`. Case creation atomically appends an `opened` event. `GET /cases/` and `GET /cases/{id}` require Viewer. `POST /cases/{id}/revisions` requires Analyst plus CSRF and body `{ "report_id": 1, "expected_version": 0 }`. `POST /cases/{id}/close` and `/reopen` require Analyst plus CSRF and body `{ "expected_version": 0, "note": "optional" }`; they lock the case, reject stale versions or invalid transitions with 409, increment `version`, and derive the event actor from the session. Case detail returns revisions and an ordered `events` array. Cases and links are persisted by migration 008; status events by additive migration 012; report snapshots remain in `incident_reports`. A hash stored alongside its snapshot is not a digital signature.
