# Source health API contract

Added 6 November 2026; extended the same day with a protected bounded manual-run
route and persisted last-run metadata. The health read remains read-only. This is
an operational status view, not a live-provider probe and not a security or
coverage claim.

## Endpoint

`GET /api/v1/sources/health`

No request body, no query parameters, no authentication dependency. The route is
a public read like the other existing read routes; that is not a claim that the
whole API is protected.

The handler makes **no external HTTP request**, **no database write** and
**no migration/seed**. It reads local database rows, the prepared Copernicus
JSON artifact, in-memory GFW status and configuration booleans. GFW pacing
status may read the existing local Redis key namespace; it never calls a
provider.

## Response

```json
{
  "checked_at": "2026-11-06T07:32:39.953336+00:00",
  "external_calls": false,
  "writes": false,
  "sources": {
    "local_vessel_records": {
      "source": "local vessel records",
      "kind": "local_replay_or_import",
      "status": "available | stale | empty",
      "positions": 678,
      "vessels": 14,
      "latest_observed_at": "2026-11-01T09:00:41+00:00",
      "age_hours": 118.5,
      "lookback_hours": 168,
      "source_mode": "unknown",
      "limitations": "..."
    },
    "copernicus_sst": {
      "source": "Copernicus Marine Service",
      "status": "available | unavailable",
      "mode": "historical",
      "dataset": "IFREMER-GLOB-SST-L3-NRT-OBS_FULL_TIME_SERIE",
      "dataset_version": "202211",
      "doi": "10.48670/moi-00164",
      "latest_observed_at": "2026-10-20T00:00:00Z",
      "value": 29.72,
      "unit": "°C",
      "attribution": "Copernicus Marine Service (DOI: ...)",
      "limitations": "..."
    },
    "global_fishing_watch": {
      "provider": "Global Fishing Watch",
      "configured": true,
      "status": "configured | not_configured",
      "availability": "not_checked",
      "rate_limits": {},
      "rate_limits_observed_at": null,
      "local_requests_last_30_minutes": 0,
      "pacing": {
        "backend": "redis | local",
        "shared": true,
        "degraded": false,
        "redis_configured": true,
        "window_seconds": 60,
        "max_requests": 60
      },
      "last_run": null,
      "last_run_note": "Last-run status is historical, persisted metadata only; ...",
      "limitations": "..."
    },
    "aisstream": {
      "source": "AISStream",
      "status": "configured | not_configured",
      "availability": "not_checked",
      "coverage": "unknown",
      "last_run": null,
      "last_run_note": "Last-run status is historical, persisted metadata only; ...",
      "limitations": "..."
    },
    "open_meteo_marine": {
      "source": "Open-Meteo Marine",
      "status": "not_checked",
      "availability": "not_checked",
      "kind": "modelled_marine_data",
      "limitations": "..."
    }
  },
  "limitations": "..."
}
```

Timestamps are UTC ISO-8601 with an offset. `checked_at` is when this local
snapshot was built, not when a provider was contacted.

`last_run` is the latest persisted run for that provider, or `null`. It is a
historical checkpoint written by `POST /sources/runs`, not a live probe. A
`last_run.status` of `succeeded` or `empty` does not upgrade `availability` from
`not_checked`.

## Bounded manual run

`POST /api/v1/sources/runs`

Requires an authenticated Analyst session (Administrator implies Analyst) and a
CSRF cookie/header pair, using the existing session contract. It runs exactly one
bounded provider operation and persists safe metadata in `source_runs`. It
never calls GFW tracks or point SAR paths, never reuses the AIS/GFW read cache,
and never writes a raw provider payload or credential.

Request bodies are discriminated by `provider`:

```json
{"provider": "aisstream", "max_positions": 30, "duration_seconds": 12, "persist_positions": false}
```

`max_positions` is 1–30 and `duration_seconds` is 1–12. The run invokes the same
bounded live snapshot adapter as `GET /aisstream/snapshot` but with cache reuse
disabled. A confirmed subscription with zero positions is `empty`; a missing
key, connection failure or unconfirmed subscription is `unavailable`.

`persist_positions` defaults to `false`. When explicitly `true`, the route can
write only the normalized bounded snapshot points to `vessel_tracks`, labelled
`source: "AISStream bounded live snapshot"` and `source_mode: "live"`. This
requires the local opt-in `AISSTREAM_PERSIST_ENABLED=true`, which must be set
only after the account holder has confirmed provider retention rights. Without
that flag, the provider call is recorded as a `rejected` run and no position is
written. Stored time is provider reception time when supplied, or snapshot
capture time when it is not; neither is asserted to be vessel-sent time. Raw
provider messages and credentials are never stored in `source_runs`.

```json
{
  "provider": "gfw",
  "start_date": "2026-10-01",
  "end_date": "2026-10-15",
  "offset": 0,
  "limit": 20
}
```

The manual GFW run queries only the already-approved historical
`public-global-fishing-events:latest` regional event page. The date range is
1–31 days with an exclusive end date, `offset` is 0–10000 and `limit` is 1–50.
A range outside 1–31 days is `rejected` before any provider request and returns
HTTP 422 with the persisted run. Provider errors return HTTP 200 with an
`unavailable` or `failed` run so the caller can display the recorded outcome.

Response (HTTP 200):

```json
{
  "run": {
    "id": 1,
    "provider": "aisstream | gfw",
    "operation": "ais_snapshot | gfw_regional_events",
    "status": "succeeded | empty | unavailable | failed | rejected",
    "mode": "live | historical",
    "started_at": "2026-11-06T12:00:00+00:00",
    "finished_at": "2026-11-06T12:00:12+00:00",
    "request_count": 1,
    "position_count": 3,
    "event_count": null,
    "error_category": null,
    "error_message": null,
    "checkpoint": {"...": "bounded run parameters and delivery only"},
    "triggered_by": "analyst-username"
  },
  "result": {"...": "the bounded provider result, or null on failure"}
}
```

`position_count` is set only for AIS runs and `event_count` only for GFW runs.
`request_count` counts bounded operation attempts issued by the run; provider
internal retries are not counted separately. `error_category` is one of
`config`, `auth`, `quota`, `network`, `provider`, `validation`, `timeout` or
`unknown`, and `error_message` is a short operator-safe summary (maximum 200
characters). The table stores no raw events, positions, tokens or headers.

## Status semantics

- `available`: the local evidence needed to serve this source exists and, for
  local vessel records, is inside the 168-hour look-back.
- `stale`: rows exist but the newest position is older than the look-back.
- `empty`: no local vessel rows exist.
- `configured`: credentials/configuration are present. It never means the
  provider is reachable, authorised for a dataset, or has coverage.
- `not_configured`: the relevant credential/configuration is absent.
- `not_checked`: no availability probe was performed by this endpoint.
- `unavailable`: a required local artifact is missing, malformed or empty.

Run statuses recorded by `POST /sources/runs`:

- `succeeded`: the bounded operation returned at least one AIS position or GFW
  event.
- `empty`: the bounded operation completed but returned no positions/events.
  This is a valid outcome, not proof of absence or coverage.
- `unavailable`: configuration, authentication, quota, network or provider
  access prevented the operation.
- `failed`: an unexpected adapter exception was caught and recorded without the
  raw exception text.
- `rejected`: local validation refused the request before any provider call.

GFW `rate_limits` is the last observed header snapshot for that backend
process. It resets on restart, is not shared across processes and can lag the
provider. AISStream `coverage: unknown` is deliberate: a key or prior
subscription is not position coverage. Open-Meteo values are model output, not
observations.

GFW `pacing` reports the last observed pacing transport. `backend: redis` means
the rolling 60-second request window and 429 cooldown are shared with other
processes using the existing Redis service. `backend: local` means the last
operation used process-local state; `degraded: true` means Redis was unavailable
and the fallback is active. Shared pacing is a soft operational guard, not proof
of account-wide provider quota compliance. The response never includes the Redis
URL or credentials.

## Safety requirements

- Never add a token, password, connection string or `.env` value to this
  response. Configuration is exposed only as a boolean.
- Do not upgrade `configured` to `available` without a bounded, explicitly
  labelled provider request.
- Do not drop `limitations` or `source_mode`; the console must be able to show
  that local replay data has no verified provider provenance.
- Keep the health route read-only. The manual run route is the only part of this
  contract that calls a provider, and it is explicitly authenticated, CSRF
  protected and bounded.
- Never store or return raw provider payloads, credentials, tokens, headers or
  unbounded exception text in run records.

## Verification

- Focused tests: `apps/api/tests/test_source_health.py`,
  `apps/api/tests/test_source_runs.py`,
  `apps/api/tests/test_source_runs_integration.py` and
  `apps/api/tests/test_provider_pacing.py`.
- Disposable migration/write check:
  `python scripts/verify_source_runs_disposable.py` with `PYTHONPATH=/app` in the
  backend container. It creates, migrates, tests and drops a uniquely named DB.
- Shared-pacing smoke: instantiate `GfwPacer` with a unique test prefix, verify
  the third request is refused at `max_requests=2`, confirm `backend: redis`,
  then delete the test keys. No provider call is made.
- Live smoke: `curl http://127.0.0.1:8000/api/v1/sources/health` and check the
  local record count, SST mode/value, `external_calls: false`, `writes: false`
  and `last_run: null` or a persisted run.
- Existing `/api/v1/gfw/status` keeps its previous fields through the shared
  `provider_health()` helper.
