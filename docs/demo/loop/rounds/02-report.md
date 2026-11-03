ROUND: 2
STORY: B-17
STATUS: DONE
COMMIT: b5bc8c26be0156cb44f90c321f01decb0223a41f

## Changed files
apps/web/src/pages/Cases.jsx
apps/web/tests/Cases.test.jsx

## Checks
| Command | Exit code | Passed | Failed | Skipped |
| npm test (in apps/web) | 0 | 73 | 0 | 0 |
| npm run build (in apps/web) | 0 | — | — | — |
| git diff --check d75ec823466d62b009a05da7fa134a32fc9276dd HEAD | 0 | — | — | — |

## git status --short
?? docs/demo/loop/

## Done-when items
1. Every row of the table has a test, and the tests pass: Met. Rows 1 to 6 have dedicated tests in `apps/web/tests/Cases.test.jsx`. Tests for rows 1, 2, and 3 were verified to fail on the old page and pass with the fix. All 14 tests in `Cases.test.jsx` (and all 73 tests in `apps/web`) pass.
2. `npm test` and `npm run build` exit 0 in `apps/web`: Met. `npm test` exited 0 (73 passed), and `npm run build` exited 0 (client built in 8.27s).
3. The work is one commit on `b/sprint`. Use this subject and body: Met. Committed with subject `Clear sign-off state when the report changes (B-17)` and body `Also announce a failed SAR request as an alert (B-01 follow-up).` at commit `b5bc8c26be0156cb44f90c321f01decb0223a41f`.
4. After the commit, in the repo root:
   - `git diff --check d75ec823466d62b009a05da7fa134a32fc9276dd HEAD` exits 0: Met. Exited 0 with no whitespace or formatting errors.
   - `git status --short` shows only `?? docs/demo/loop/`: Met. Output is exactly `?? docs/demo/loop/`.

## Limitations and contract needs
none

## Unexpected changes
none

