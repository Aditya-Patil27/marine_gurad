ROUND: 1
STORY: B-01
STATUS: DONE
COMMIT: d75ec823466d62b009a05da7fa134a32fc9276dd

## Changed files
apps/web/src/pages/Cases.jsx
apps/web/tests/Cases.test.jsx

## Checks
| Command | Exit code | Passed | Failed | Skipped |
| npm test (in apps/web) | 0 | 67 | 0 | 0 |
| npm run build (in apps/web) | 0 | — | — | — |
| git diff --check | 0 | — | — | — |

## Done-when items
1. Every row of the table has a test, and the tests pass: Met. All 8 rows of the required behaviour table have dedicated tests in `apps/web/tests/Cases.test.jsx` (including retry assertions verifying requests repeat and data renders on retry success); all 8 tests pass (67/67 passed in `apps/web`).
2. These commands exit 0: `npm test` and `npm run build` in `apps/web`, and `git diff --check` in the repo root: Met. `npm test` exited 0 (67 passed), `npm run build` exited 0 (built client in 7.86s), and `git diff --check` exited 0 with no errors.
3. The work is committed to `b/sprint` with the message `Show failed evidence requests as failures (B-01)`: Met. Committed to `b/sprint` with SHA `d75ec823466d62b009a05da7fa134a32fc9276dd`.

## Limitations and contract needs
Owner A contract needs and findings (H-04):
1. The API checks list returns "No marine weather feed is connected yet, so storm sheltering can't be ruled out." directly above a live Open-Meteo reading on the Evidence screen.
2. Report snapshots store no weather data, so a signed report loses what the officer saw.

## Unexpected changes
none

