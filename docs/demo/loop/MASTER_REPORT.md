# Run 2026-11-04 13:51 IST

## Final state
HEAD: 40ce53d449f08dde44950576b10e1174d18e05f9
Tests: 164 passed, 0 failed, 0 skipped
Build: exit code 0
git status --short:
 M docs/demo/loop/STORIES.md
?? docs/demo/loop/MASTER_PROMPT.md
graphify: exit code 0, output path: apps/web/src/graphify-out

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
- Added at final check: no `limitations` field exists anywhere in `apps/api`. B-09 assumes `limitations` on the vessel detail and report snapshot, as a list of strings or `{ key, label, detail }`. Until A adds it, Evidence and the report read "Data limitations not reported".

## Not checked
- Real browser interaction at 1366×768 and 1920×1080 (deferred to B-14 once real stack is running).
- Docker stack startup with contracts and real backend endpoints (gate before B-10 blocked awaiting A's 6 Nov delivery).

## Blockers
- Gate before B-10 condition failed: `docs/contracts/` does not exist in working tree, endpoints do not exist in `apps/api`. Therefore B-10, B-11, B-12, B-13, and B-14 are marked `blocked: needs A's 6 Nov delivery`.
- B-07 and B-08 regional environmental endpoint `/api/v1/environment/regional` is not present in `apps/api`; UI components and tests are built against fixtures with consolidated schema in `apps/web/src/lib/environment.js`.

## Final check by Claude, 2026-11-04
Checked at HEAD 9951426. The fixes below are uncommitted.

### Run results that held
- Clean copy of HEAD: 164 tests passed, build exit 0.
- No existing test assertion was changed by the run. Write paths stayed in owner B's areas.
- Gate and blocked marks are correct: `docs/contracts/` and the environment endpoint do not exist.
- The transcript did not show runs for these break rows: Evidence and report raw names, crash on missing checks or limitations, and the Evidence context link. They were re-run and all were caught.

### Defects fixed
| Defect | Fix | Proof |
|---|---|---|
| A late sign-off success on report 1 was dropped if report 2 was open, so report 1 looked unsigned and re-signing returned 409. MASTER_PROMPT's wording caused this. | `sign()` always refreshes the list | New test in `Cases.test.jsx` |
| The panel's context link closed the vessel panel | Link keeps `?vessel=` | New test in `MapPage.test.jsx`; browser: panel stays open |
| A failed draft error carried over to the next vessel | `key={selected}` on `VesselPanel` | New test in `MapPage.test.jsx` |
| The environmental card covered the track timeline by 158 px when showing a value | Card capped at 340 px | Browser at 1366×768 and 1920×1080: no overlap |
| Limitations objects printed as raw JSON, and the markup was duplicated | `DataLimitations` helper in `Cases.jsx` | Existing tests |
| Storyboard overclaimed: "immutable", "tamper-evident", an unmeasured review-time reduction, and a storm-shelter conclusion the API says it cannot prove | `docs/demo/storyboard.md` rewritten, with a "Before recording" list | Read against the plan and API text |

### Existing tests changed
Two assertions in `VesselPanel.test.jsx`, on purpose: the B-08 link is now `/map?vessel=419007431#environmental-context`.

### Final state
- Working tree: 167 tests passed, 0 failed.
- Build: exit 0, in a scratch copy with the same sources apart from the blank lines below.
- Browser: mocked API only, in the scratch copy. Fonts returned 403 there because `node_modules` is a junction, so font rendering was not checked.

### Still open
- B-07, B-08 and B-09 limitations are done on fixtures only. Real data shows "Environmental data not available" and "Data limitations not reported".
- Until A's endpoint exists, the map requests `/environment/regional` every 10 minutes and logs a 404. The route name is an assumption; the plan names no route.
- A draft report still in flight for vessel A opens its report even if the officer has moved to vessel B.
- At 1100 px wide with a vessel open, the state legend overlaps the environmental card by 3 px. This is outside the target screen sizes.
- `environment.js`, `useOnline.js` and the old `storyboard.md` had one uncommitted blank line added at the end, not listed in this report's Final state. They are harmless.
- `apps/web/src/graphify-out/` is untracked and not ignored. Do not stage it.

### Not checked
The real API stack and Docker.
