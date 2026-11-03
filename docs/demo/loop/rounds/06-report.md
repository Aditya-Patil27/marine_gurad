ROUND: 6
STORY: B-05
STATUS: DONE
COMMIT: 5ee3732ce15a23e9ceaaa162cde0bd274ab07a74

## Changed files
apps/web/src/features/map/VesselPanel.jsx
apps/web/src/lib/format.js
apps/web/src/pages/Cases.jsx
apps/web/tests/Cases.test.jsx
apps/web/tests/Shell.test.jsx
apps/web/tests/VesselPanel.test.jsx
apps/web/tests/format.test.js

## Checks
| Command | Exit code | Passed | Failed | Skipped |
| npm --prefix apps/web test | 0 | 125 | 0 | 0 |
| npm --prefix apps/web run build | 0 | not run | not run | not run |
| git diff --check 1cca0529619a1fb984d9cde0fb832f5f25cf8128 HEAD | 0 | not run | not run | not run |

## git status --short
 M docs/demo/loop/STORIES.md
?? docs/demo/loop/NEXT_PROMPT.md
?? docs/demo/loop/rounds/05-prompt.md
?? docs/demo/loop/rounds/05-report.md

## Done-when items
1. Every row of the dateTimeIST table and of the three test tables has a test, and the tests pass: Met. format.test.js tests all 6 rows of dateTimeIST; Cases.test.jsx tests rows A-I; VesselPanel.test.jsx tests row J; Shell.test.jsx tests rows K and L. All 125 tests passed.
2. npm --prefix apps/web test and npm --prefix apps/web run build exit 0: Met. Both commands exited with code 0.
3. The work is one commit on b/sprint with the required subject and body: Met. Commit 5ee3732ce15a23e9ceaaa162cde0bd274ab07a74 on b/sprint.
4. git diff --check 1cca0529619a1fb984d9cde0fb832f5f25cf8128 HEAD exits 0, and git status --short lists nothing outside docs/demo/loop/: Met. diff --check exited 0 cleanly, and git status --short only shows files within docs/demo/loop/.

## Limitations and contract needs
none

## Changes beyond the story
none

## Unexpected changes
docs/demo/loop/STORIES.md
docs/demo/loop/rounds/05-prompt.md
docs/demo/loop/rounds/05-report.md
