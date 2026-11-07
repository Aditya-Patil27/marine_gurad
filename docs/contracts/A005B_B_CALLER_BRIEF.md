# B caller brief — bounded historical window (A-005B)

> Correction, 7 November (A-005B-R1): assessments now persist their actual
> window anchors. A historical report with a mismatched or legacy assessment
> returns HTTP 409 before insertion. B must refresh and re-sync the assessment
> before retrying; its stable UUID may remain unchanged.

Owner: B. A does not edit `apps/web/**`. The exact request/response contract
and validation rules are in [HISTORICAL_WINDOW_API.md](HISTORICAL_WINDOW_API.md).

## What B needs to do

1. Add one visible historical-window control (or fixed replay preset) that
   produces `window_start` and `window_end` as ISO 8601 UTC strings with `Z`.
   The prepared replay is 31 October–1 November 2026; a useful bounded preset
   is `2026-10-30T00:00:00Z` to `2026-11-02T00:00:00Z`.
2. Pass the **same two values** to, in order:
   - `GET /api/v1/vessels/?window_start=...&window_end=...` for the shared
     fleet list, map markers and vessel selection; retain the selection across
     navigation so these do not keep using the expiring rolling default;
   - `GET /api/v1/vessels/{mmsi}?window_start=...&window_end=...` for evidence
     and map detail;
   - `POST /api/v1/alerts/assessments/sync` with `window_start`/`window_end`
     in the JSON body before selecting an assessment;
   - `POST /api/v1/reports/` with the same body fields and the selected
     `assessment_id`.
3. Render `window.mode`, `window.start` and `window.end` next to the evidence
   dates. Keep the existing `source`/`source_mode` labels and original
   observation timestamps; do not relabel historical replay as live.
4. Show empty list, `404` and `synced: 0` as "no observations in this window".
   Do not silently fall back to rolling data.
5. If `POST /api/v1/reports/` returns `409` because the selected assessment was
   evaluated over a different window, was re-synced, or is a legacy row without
   anchors, no report was created. Show the detail, re-sync with the **same**
   bounds, select the refreshed `assessment_id`, then create the report again.
   The stable UUID may be unchanged after re-sync. Reload the assessment and
   verify its stored window matches before retrying; do not blindly loop on 409.
6. Keep the existing session cookie and `X-CSRF-Token` handling for assessment
   sync and report creation. No auth behavior changes are required.
7. Omit both window fields on ordinary live views to preserve the existing
   rolling `hours` behavior.

## Out of scope for B

Do not change stored observation timestamps, reseed the shared database, or
add a default historical window to live views. The backend now persists and
verifies the assessment window anchors, but B still owns keeping the selected
bounds consistent across the list, detail, sync and report calls.
