ROUND: 4
STORY: B-03
STATUS: DONE
COMMIT: 908cb06dcfd875a7174bd6eadae3ccabfd5bd078

## Changed files
apps/web/src/features/map/VesselPanel.jsx
apps/web/src/lib/format.js
apps/web/src/pages/Cases.jsx
apps/web/tests/Cases.test.jsx
apps/web/tests/OceanMap.test.jsx
apps/web/tests/VesselPanel.test.jsx
apps/web/tests/format.test.js

## Checks
| Command | Exit code | Passed | Failed | Skipped |
| npm --prefix apps/web test | 0 | 92 | 0 | 0 |
| npm --prefix apps/web run build | 0 | not run | not run | not run |
| git diff --check f2a81ca4529e5c9f7c9a57d0d3673f5913b92427 HEAD | 0 | not run | not run | not run |

## git status --short
?? docs/demo/loop/

## Done-when items
1. Met. All rows of both test tables are covered in apps/web/tests/format.test.js (6 tests), apps/web/tests/VesselPanel.test.jsx (tests A and B), and apps/web/tests/Cases.test.jsx (tests C through I). Tests were run before implementation and observed failing (14 failed), and all pass after implementation (92 passed across 9 test files). The B-15 OceanMap test assertion was tightened to verify coordinates.
2. Met. npm --prefix apps/web test exited 0 with 9 passed test files and 92 passed tests. npm --prefix apps/web run build exited 0 with built client in production mode.
3. Met. Single commit 908cb06dcfd875a7174bd6eadae3ccabfd5bd078 on branch b/sprint with subject "Label where each piece of evidence came from (B-03)" and body "A missing or unknown source is never shown as live. Evidence now shows the source and note the weather API returns. Also makes the B-15 track test check the track's points.".
4. Met. git diff --check f2a81ca4529e5c9f7c9a57d0d3673f5913b92427 HEAD exited 0 with no whitespace errors. git status --short shows only ?? docs/demo/loop/.

## Limitations and contract needs
none

## Changes beyond the story
none

## Unexpected changes
none
