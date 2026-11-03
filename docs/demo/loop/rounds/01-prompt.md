# Round 1 — B-01: Show failed requests as failures

You implement owner B's work on SamudraSense. A lead reviews your work from the report you write in the last step. Do this story only. When the report is written, stop. Do not start another story.

~~~text
Task:        B-01 / F13
Owner:       B
Branch:      b/sprint. Run `git switch b/sprint`. If it does not exist, run `git switch -c b/sprint`.
Write paths: apps/web/src/pages/Cases.jsx
             apps/web/tests/Cases.test.jsx (new)
             docs/demo/loop/REPORT.md (last step only)
Depends on:  nothing. The tests mock the API, so no backend is needed.
Outcome:     an officer can tell "we looked and found nothing" from "we could not look",
             and a rejected sign-off does not take the screen down.
~~~

The plan requires this: "Distinguish unknown from false and missing from zero" (docs/FINAL_PRODUCT_PLAN.md section 6). Section F13 requires error and partial-data states on every page.

## The four defects

All four are in `apps/web/src/pages/Cases.jsx`.

1. **SAR failure reads as a clean result.** Line 42 catches a failed request with `setDetections([])`. Line 68 then shows "No candidate SAR detection recorded for this vessel."
2. **A network failure reads as a missing vessel.** Line 40 shows "Could not load this vessel in the last 24 hours." for every failure.
3. **An unknown report ID shows a different report.** Line 81 falls back with `|| reports?.[0]`. So `/reports?id=999` shows the first report and its sign-off form, and an officer could sign the wrong report.
4. **A rejected sign-off crashes the screen.** Line 86 passes the API's `detail` to `setError`. For a 422, `detail` is an array. Line 90 renders it, React throws, and the error boundary replaces the screen with "This screen stopped working". A 121-character officer name causes this, because the API limit is 120.

## Required behaviour

| Situation | The page must show |
|---|---|
| SAR request fails | "SAR detections didn't load, so a match can't be ruled out." and a "Try again" button that repeats only the SAR request. It must not show "No candidate". |
| SAR request succeeds with no match for this vessel | The existing "No candidate SAR detection recorded for this vessel." |
| Vessel request returns 404 | "No positions for MMSI {mmsi} in the last 24 h." and no "Try again" button |
| Vessel request fails any other way | "Can't reach the API, so this vessel's evidence didn't load." and a "Try again" button that repeats the vessel request |
| `/reports?id=` names a report that is not in the list | "Report #{id} was not found." It must not show another report's evidence or sign-off form. The list of reports stays visible, so the officer can pick one. |
| `/reports` with no `id` | The first report, as it does now |
| Sign-off is rejected and `detail` is not a string (a 422) | The report stays on screen with "The API rejected this sign-off. Check the officer name and try again." The officer can correct the name and sign. |
| Sign-off is rejected and `detail` is a string | That string, as it does now |

Use the existing `isNotFound` helper from `apps/web/src/lib/api.js`. `apps/web/src/features/map/VesselPanel.jsx` lines 43-56 show the same pattern. Use the existing `btn` and `btn-primary` classes.

## Limits

- Change only the logic these defects need. Do not reformat `Cases.jsx`, split it, or restyle it.
- Do not change `api.js`, `App.jsx`, package files or lockfiles.
- Do not write in `apps/api/**`, `infra/**`, `docs/contracts/**`, `docs/DATA_MANIFEST.md`, `README.md` or `docs/FINAL_PRODUCT_PLAN.md`. If the story needs a change there, set STATUS to BLOCKED and say what it needs.
- Do not write in `docs/demo/loop/` except `REPORT.md`.
- Other work may be in this working tree. Do not run `git checkout`, `git restore`, `git stash`, `git reset` or `git clean`. If a file you did not expect has changes, leave it and list it in the report.
- Stage files by exact path. Do not run `git add -A` or `git add .`. Do not push.

## Tests

Add `apps/web/tests/Cases.test.jsx`. Follow the setup in `apps/web/tests/VesselPanel.test.jsx` and the data in `apps/web/tests/fixtures.js`. Add one test for each row of the table. For each "Try again" row, also test that clicking the button repeats the request and that the page shows the data when the second attempt succeeds. `httpError` in `fixtures.js` has no response body, so build the rejected sign-off errors inside `Cases.test.jsx`. Do not edit `fixtures.js`.

## Done when

1. Every row of the table has a test, and the tests pass.
2. These commands exit 0: `npm test` and `npm run build` in `apps/web`, and `git diff --check` in the repo root.
3. The work is committed to `b/sprint` with the message `Show failed evidence requests as failures (B-01)`.

## Last step: write the report

Write the report with your file-writing tool, as the last thing you do, to `docs/demo/loop/REPORT.md`. The lead's review starts when this file appears, so do not create it before the work is finished. If you cannot finish, still write it, with `STATUS: BLOCKED`.

Report only what you ran and saw. Copy the real numbers from the command output. If you did not run a check, write "not run".

~~~markdown
ROUND: 1
STORY: B-01
STATUS: DONE or BLOCKED
COMMIT: full SHA, or none

## Changed files
One path per line.

## Checks
| Command | Exit code | Passed | Failed | Skipped |

## Done-when items
For each numbered item: met or not met, and the evidence.

## Limitations and contract needs
Anything that does not work yet, or that owner A must change. Write "none" if there is nothing.

## Unexpected changes
Files with changes you did not make. Write "none" if there are none.

## Blocker
The exact error and what you tried. Delete this section if STATUS is DONE.
~~~
