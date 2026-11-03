ROUND: 7
STORY: B-16a
STATUS: DONE
COMMIT: aefb7514bc32a1d474d1e9bec60ca48f27eaa3a6

## Changed files
apps/web/src/lib/format.js
apps/web/src/pages/Cases.jsx
apps/web/src/pages/NotBuiltYet.jsx
apps/web/tests/Cases.test.jsx
apps/web/tests/NotBuiltYet.test.jsx
apps/web/tests/format.test.js

## Checks
| Command | Exit code | Passed | Failed | Skipped |
| npm --prefix apps/web test | 0 | 146 | 0 | 0 |
| npm --prefix apps/web run build | 0 | not run | not run | not run |
| git diff --check 5ee3732ce15a23e9ceaaa162cde0bd274ab07a74 HEAD | 0 | not run | not run | not run |

## git status --short
 M docs/demo/loop/STORIES.md
?? docs/demo/loop/NEXT_PROMPT.md
?? docs/demo/loop/rounds/05-prompt.md
?? docs/demo/loop/rounds/05-report.md
?? docs/demo/loop/rounds/06-prompt.md
?? docs/demo/loop/rounds/06-report.md

## Done-when items
1. Every row of the modeLabel table and of the test table has a test, and the tests pass: Met. format.test.js tests all 6 rows of modeLabel and row O; NotBuiltYet.test.jsx tests row A; Cases.test.jsx tests rows B through N. All 146 tests passed.
2. npm --prefix apps/web test and npm --prefix apps/web run build exit 0: Met. Both commands exited with code 0.
3. The work is one commit on b/sprint with the required subject and body: Met. Commit aefb7514bc32a1d474d1e9bec60ca48f27eaa3a6 on b/sprint.
4. git diff --check 5ee3732ce15a23e9ceaaa162cde0bd274ab07a74 HEAD exits 0, and git status --short lists nothing outside docs/demo/loop/: Met. diff --check exited 0 cleanly, and git status --short lists only tracked/untracked loop files in docs/demo/loop/.

## Limitations and contract needs
none

## Changes beyond the story
none

## Unexpected changes
docs/demo/loop/STORIES.md
docs/demo/loop/rounds/05-prompt.md
docs/demo/loop/rounds/05-report.md
docs/demo/loop/rounds/06-prompt.md
docs/demo/loop/rounds/06-report.md
