# Bounded historical observation window (A-005B)

> Correction, 7 November (A-005B-R1): persisted assessments now store the
> resolved window mode and exact start/end anchors (additive migration 013).
> Historical report creation with `assessment_id` rejects a mismatched or
> legacy assessment with HTTP 409 before inserting the report.

Added 7 November 2026. This is an **additive** contract for the existing
vessel, assessment and report routes. It lets a caller select one explicit,
bounded UTC window over stored observations so the prepared 31 October–1
November replay remains inspectable after it ages out of the rolling
seven-day look-back. It does not change stored observation timestamps, reseed
data or change scoring rules. Migration 013 adds nullable window-anchor
columns to persisted assessments.

## Shared window object

Every response that accepts a window returns the same `window` object:

```json
{
  "mode": "historical",
  "start": "2026-10-30T00:00:00Z",
  "end": "2026-11-02T00:00:00Z",
  "hours": 72,
  "max_hours": 168,
  "utc": true,
  "end_inclusive": true,
  "timestamps": "original stored observation timestamps are preserved"
}
```

- `mode` is `historical` when both explicit bounds are supplied, otherwise
  `rolling`.
- `start` is exclusive and `end` is inclusive, matching the existing
  `timestamp > since` query plus an explicit upper bound.
- `hours` is the requested rolling look-back or the ceiling of the historical
  span in hours.
- Observation timestamps in `track`, `last_seen`, factors, assessments and
  report snapshots are the **stored** values, not request time. Source and
  `source_mode` labels are copied from the stored rows unchanged.

## Routes and fields

### `GET /api/v1/vessels/`

Existing `hours` (1–168, default 168) remains. Add optional query parameters:

- `window_start` — ISO 8601 timestamp with an explicit UTC offset or `Z`.
- `window_end` — ISO 8601 timestamp with an explicit UTC offset or `Z`.

Both must be supplied together. When supplied, `hours` is ignored. The
response adds `window`; `vessels` is empty when the selected window contains no
stored positions.

### `GET /api/v1/vessels/{mmsi}`

Same two optional query parameters and the same `window` response field.
When the window is empty the route returns `404` with a message naming the
selected historical window; it never substitutes current positions.

### `POST /api/v1/alerts/assessments/sync`

Existing body fields and Analyst + CSRF requirements remain. Add optional body
fields:

```json
{
  "lookback_hours": 168,
  "mmsi": 419007431,
  "window_start": "2026-10-30T00:00:00Z",
  "window_end": "2026-11-02T00:00:00Z"
}
```

The response adds `window`; `lookback_hours` is the effective window span.
`synced: 0` means the selected window contained no positions. Persisted
assessment rows keep the existing deterministic ID and store the resolved
`window_mode` plus the exact `window_start`/`window_end` anchors alongside the
effective `lookback_hours`, so the row carries the window it was actually
evaluated over. `GET /alerts/assessments` returns the same additive `window`
object. Pre-013 rows return `window: null` because their anchors are unknown;
they are never inferred from `lookback_hours` or `evaluated_at`.

### `POST /api/v1/reports/`

Existing body fields and Analyst + CSRF requirements remain. Add optional body
fields `window_start` and `window_end` with the same validation. The report
snapshot contains the vessel evaluation's `window` object and preserves the
stored observation dates and source labels.

When `assessment_id` is also supplied and the report selects a historical
window, the API compares the persisted assessment anchors with the actual
report window before inserting anything. Exact start/end equality is required:
a different window, the same duration with different anchors, a rolling
assessment, a row re-synced to another window, or a legacy row without anchors
returns HTTP `409` and creates no report. The detail gives the safe retry:
re-run `POST /api/v1/alerts/assessments/sync` with the same `window_start` and
`window_end`, select the refreshed `assessment_id`, then create the report
again. On a match, `snapshot.persisted_assessment` contains `window` (the
stored assessment window), `report_window` (the report window) and
`window_match: true`; both windows are part of the hashed snapshot. Reports
without `assessment_id`, and rolling reports without window parameters, keep
their existing behavior.

## Validation

All three paths use the shared `fleet.resolve_window` helper and fail with
HTTP `422` and a clear `detail` when:

- only one of `window_start`/`window_end` is supplied;
- either bound lacks an explicit UTC offset (a naive timestamp is rejected);
- `window_end` is not after `window_start`;
- the span exceeds 168 hours;
- `window_end` is in the future.

`hours` outside 1–168 on the rolling path also fails. FastAPI's normal
timestamp parsing errors remain `422`.

## Semantics and limits

- A historical window is evaluated with the **window end** as the scoring
  clock, so a later wall clock does not manufacture an open AIS gap. This
  preserves the risk engine's existing naive-UTC boundary semantics.
- The default (no window parameters) path keeps the existing rolling
  `hours` behavior and response fields; existing callers need no change.
- Missing historical data stays visibly missing: empty vessel lists, `synced:
  0`, or `404` for a vessel detail. There is no synthetic fallback and no
  timestamp rewrite.
- A historical assessment/report association is server-enforced on exact
  persisted anchors. A report cannot silently attach an assessment evaluated
  over another window, and the caller's resend cannot override stored metadata.
- Legacy assessment rows have unknown anchors (`window: null`) and cannot be
  attached to a historical report until they are re-synced with explicit
  bounds.
- A window is a selection over stored rows only. It is not a claim of live
  coverage, completeness or data freshness.
- Report and assessment mutations still require the existing session cookie
  and `X-CSRF-Token`; this change does not alter authentication.

## Example: prepared replay

```http
GET /api/v1/vessels/419007431?window_start=2026-10-30T00:00:00Z&window_end=2026-11-02T00:00:00Z
```

Observed read-only on 7 November 2026: `window.mode` was `historical`, the
track ran from `2026-10-31T21:00:41Z` to `2026-11-01T02:48:41Z`, and the
stored `source`/`source_mode` remained `unknown`/`unknown`. The same request
without window parameters returned `window.mode: "rolling"` with the same
observations while they were still inside 168 hours.

## B caller brief (separate from A)

Also available as a standalone [B caller brief](A005B_B_CALLER_BRIEF.md).
B owns `apps/web/**` and the browser journey. A does not edit those files.

1. Add one visible historical-window control or fixed replay preset that
   produces `window_start` and `window_end` in UTC (`Z` suffix).
2. Pass the **same two values** to, in order:
   - `GET /api/v1/vessels/` for the shared fleet list and map markers;
   - `GET /api/v1/vessels/{mmsi}` for evidence and map detail;
   - `POST /api/v1/alerts/assessments/sync` before selecting an assessment;
   - `POST /api/v1/reports/` with the selected `assessment_id`.
3. Render `window.mode`, `window.start` and `window.end` near the evidence
   dates so the analyst can see this is a historical selection, not live
   data. Keep the existing source/mode labels and observation dates.
4. Show empty/404/`synced: 0` states as "no observations in this window";
   do not fall back to rolling data silently.
5. If report creation returns `409` for a mismatched or legacy assessment,
   show the detail and the safe retry: re-sync with the same bounds, select
   the refreshed `assessment_id`, then create the report again. No report was
   created by the failed request.
6. Keep the existing session cookie and `X-CSRF-Token` handling for the
   assessment and report mutations.
7. Do not add a default historical window to ordinary live views; omit the
   parameters to keep rolling behavior.
