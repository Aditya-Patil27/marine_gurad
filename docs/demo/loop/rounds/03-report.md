ROUND: 3
STORY: B-15
STATUS: DONE
COMMIT: f2a81ca4529e5c9f7c9a57d0d3673f5913b92427

## Changed files
apps/web/src/features/map/OceanMap.jsx
apps/web/tests/OceanMap.test.jsx

## Checks
| Command | Exit code | Passed | Failed | Skipped |
| npm --prefix apps/web test | 0 | 77 | 0 | 0 |
| npm --prefix apps/web test -- OceanMap.test.jsx | 0 | 4 | 0 | 0 |
| npm --prefix apps/web run build | 0 | not run | not run | not run |

## git status --short
?? docs/demo/loop/

## Done-when items
1. Met. Every row of the table has a test in [OceanMap.test.jsx](file:///C:/Users/app27/Downloads/indradhanu/marine_gurad/apps/web/tests/OceanMap.test.jsx), and all tests pass. Rows 1, 2, and 3 failed when tested against `load` on line 123, while row 4 passed. With `style.load`, all 4 tests pass.
2. Met. `npm --prefix apps/web test` exited 0 (8 test files passed, 77 tests passed), and `npm --prefix apps/web run build` exited 0 (1980 modules transformed, built in 15.04s).
3. Met. The work is one commit on `b/sprint`: `f2a81ca4529e5c9f7c9a57d0d3673f5913b92427` with subject `Draw map layers without waiting for basemap tiles (B-15)` and body `Vessels and zones now appear and respond to clicks while tiles are slow or failing.`.
4. Met. `git diff --check b5bc8c26be0156cb44f90c321f01decb0223a41f HEAD` exited 0 with no whitespace or syntax errors, and `git status --short` shows only `?? docs/demo/loop/`.

## Limitations and contract needs
none

## Changes beyond the story
none

## Unexpected changes
none
