ROUND: 5
STORY: B-04
STATUS: DONE
COMMIT: 1cca0529619a1fb984d9cde0fb832f5f25cf8128

## Changed files
apps/web/src/components/Shell.jsx
apps/web/src/pages/MapPage.jsx
apps/web/tests/Shell.test.jsx
apps/web/tests/MapPage.test.jsx

## Checks
| Command | Exit code | Passed | Failed | Skipped |
| npm --prefix apps/web test | 0 | 107 | 0 | 0 |
| npm --prefix apps/web run build | 0 | — | — | — |
| git diff --check 56d017a2ec4cc440f4cbc5625a59441bf986a016 HEAD | 0 | — | — | — |

## git status --short
 M docs/demo/loop/STORIES.md
?? docs/demo/loop/NEXT_PROMPT.md

## Done-when items
1. Met. Shell.test.jsx includes tests for rows A-I (data-mode banner states, offline transitions, boundary isolation) and MapPage.test.jsx includes tests for rows J-O (banner recovery across polling intervals, status dot colors for live, faint, and API errors). All 107 tests across 9 test files passed.
2. Met. `npm --prefix apps/web test` exited 0 (107 tests passed). `npm --prefix apps/web run build` exited 0 with all assets compiled.
3. Met. Created commit 1cca0529619a1fb984d9cde0fb832f5f25cf8128 on `b/sprint` with subject `Show one data-mode banner on every screen (B-04)` and body `Offline and API failure states never read as live. The map status dot is green only for live data.`.
4. Met. `git diff --check 56d017a2ec4cc440f4cbc5625a59441bf986a016 HEAD` exited 0 without errors. `git status --short` lists nothing outside `docs/demo/loop/`.

## Limitations and contract needs
none

## Changes beyond the story
none

## Unexpected changes
none
