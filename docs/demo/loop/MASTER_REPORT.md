# Run 2026-11-04 13:51 IST

## Final state
HEAD: 40ce53d449f08dde44950576b10e1174d18e05f9
Tests: 164 passed, 0 failed, 0 skipped
Build: exit code 0
git status --short:
 M docs/demo/loop/STORIES.md
?? docs/demo/loop/MASTER_PROMPT.md
graphify: pending step 4

## Stories
| ID | Status | Commit | Changed files |
|---|---|---|---|
| B-16b | done | fedc063 | apps/web/src/features/map/VesselPanel.jsx, apps/web/src/pages/Cases.jsx, apps/web/src/lib/useOnline.js, apps/web/src/components/Shell.jsx, apps/web/src/pages/MapPage.jsx, apps/web/tests/VesselPanel.test.jsx, apps/web/tests/Cases.test.jsx, apps/web/tests/MapPage.test.jsx |
| B-06 | done | 1cdc277 | docs/demo/storyboard.md |
| H-01 | you | - | - |
| H-04 | you | - | - |
| B-07 | blocked: needs A's endpoint | c6c510c | apps/web/src/lib/environment.js, apps/web/src/lib/api.js, apps/web/src/pages/MapPage.jsx, apps/web/tests/fixtures.js, apps/web/tests/MapPage.test.jsx |
| B-08 | blocked: needs A's endpoint | d03d087 | apps/web/src/features/map/VesselPanel.jsx, apps/web/src/pages/Cases.jsx, apps/web/src/pages/MapPage.jsx, apps/web/tests/VesselPanel.test.jsx, apps/web/tests/Cases.test.jsx |
| B-09 | done | 40ce53d | apps/web/src/pages/Cases.jsx, apps/web/tests/Cases.test.jsx |
| B-10 | blocked: needs A's 6 Nov delivery | - | - |
| B-11 | blocked: needs A's 6 Nov delivery | - | - |
| B-12 | blocked: needs A's 6 Nov delivery | - | - |
| B-13 | blocked: needs A's 6 Nov delivery | - | - |
| H-02 | you | - | - |
| B-14 | blocked: needs A's 6 Nov delivery | - | - |
| H-03 | you | - | - |

## Break check
| Story | Break | Caught or survived |
|---|---|---|
| B-16b | Double click calls reportsApi.create twice | Caught |
| B-16b | Report creation error shows alert and does not navigate | Caught |
| B-16b | Sign-off error on report 1 shows on report 2 if officer switched | Caught |
| B-16b | Offline banner with live data keeps green status dot on map | Caught |
| B-16b | Raw AIS vessel name remains in factor detail | Caught |
| B-07 | Remove unit from environmental reading | Caught |
| B-07 | Remove date from environmental reading | Caught |
| B-07 | Remove attribution from environmental reading | Caught |
| B-07 | Service failure displays environmental value anyway | Caught |
| B-08 | Remove regional ocean context link from vessel panel / evidence | Caught |
| B-08 | Remove date from regional ocean context link | Caught |
| B-08 | Use causal phrase ("caused by") in context link | Caught |
| B-09 | Remove data limitations on Evidence | Caught |
| B-09 | Remove data limitations on Report | Caught |
| B-09 | Remove checks on Report | Caught |
| B-09 | Remove indicators disclaimer line on Report | Caught |
| B-09 | Crash on missing checks in detail/snapshot | Caught |

## Existing tests changed
none

## Changes beyond the stories
none

## For the user to raise with owner A
- Assumed field names for H-01 (regional environmental endpoint):
  - `variable`: string (e.g., "Sea surface temperature")
  - `value`: number (e.g., 29.4)
  - `unit`: string (e.g., "°C")
  - `observed_at`: ISO 8601 UTC timestamp string (e.g., "2026-10-13T06:00:00Z")
  - `attribution`: string (e.g., "Copernicus Marine Service")
- Missing endpoints in `apps/api`:
  - `GET /api/v1/environment/regional` (needed for B-07 and B-08)
  - JSON export endpoint described in F09 (needed for B-11)
- Missing contracts: `docs/contracts/` directory does not exist in the working tree.
- API text formatting: Durations inside API-generated strings (e.g., "6.4 h so far") vs formatted duration displays on map/timeline ("6 h 22 m").
- API check consistency (H-04): Risk check states "No marine weather feed is connected yet" directly above active weather observations.

## Not checked
- Real browser interaction at 1366×768 and 1920×1080 (deferred to B-14 once real stack is running).
- Docker stack startup with contracts and real backend endpoints (gate before B-10 blocked awaiting A's 6 Nov delivery).

## Blockers
- Gate before B-10 condition failed: `docs/contracts/` does not exist in working tree, endpoints do not exist in `apps/api`. Therefore B-10, B-11, B-12, B-13, and B-14 are marked `blocked: needs A's 6 Nov delivery`.
- B-07 and B-08 regional environmental endpoint `/api/v1/environment/regional` is not present in `apps/api`; UI components and tests are built against fixtures with consolidated schema in `apps/web/src/lib/environment.js`.
