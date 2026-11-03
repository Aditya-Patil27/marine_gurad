# Round 6 — B-05: Show the date and timezone on every evidence time

You implement owner B's work on SamudraSense. A lead reviews your work from the report you write in the last step. Do this story only. When the report is written, stop. Do not start another story.

~~~text
Task:        B-05 / F13
Owner:       B
Branch:      b/sprint. It is already checked out. Do not create or switch branches.
Base commit: 1cca0529619a1fb984d9cde0fb832f5f25cf8128
Write paths: apps/web/src/lib/format.js
             apps/web/src/pages/Cases.jsx
             apps/web/src/features/map/VesselPanel.jsx
             apps/web/tests/format.test.js
             apps/web/tests/Cases.test.jsx
             apps/web/tests/VesselPanel.test.jsx
             apps/web/tests/Shell.test.jsx
             docs/demo/loop/REPORT.md (last step only)
Depends on:  none
Outcome:     an officer can read the date and timezone of every time on the evidence and report screens, and can tell repeat snapshots of one vessel apart in the report list.
~~~

## The defect

1. `timeIST` shows only the time, so Evidence and the vessel panel show "Last observed 12:10 IST" with no date.
2. Evidence and Reports print raw API strings, such as `2026-10-13T06:40:48Z` and `2026-10-13T06:40:48+00:00`.
3. Report list rows show `#1 · Sea Pearl II` only. Two snapshots of one vessel differ only by number.

## The change

### 1. Add `dateTimeIST` to `format.js`

Add and export a new helper, `dateTimeIST(iso)`. Do not change `timeIST`: the map pill, the attention card, the banner and the track timeline still use it.

| Input | Output |
|---|---|
| `'2026-10-13T06:40:48Z'` | `13 Oct 2026, 12:10 IST` |
| `'2026-10-13T06:40:48+00:00'` | `13 Oct 2026, 12:10 IST` |
| `'2026-11-03T18:30:00Z'` | `4 Nov 2026, 00:00 IST` (the date moves to IST) |
| `null`, `undefined`, `''` | `Time not reported` |
| `'not a date'` | `Time not reported`, with no exception |
| `'2026-10-13T06:40:48'` (no `Z` and no offset) | `Time not reported` |

The last row matters. `new Date` reads a string with no offset as browser local time, so it can show the wrong hour. Accept only a string that ends in `Z` or an offset such as `+00:00` or `+0530`. Never guess a timezone.

### 2. Use it at these places

| Place | Now | After |
|---|---|---|
| `Cases.jsx:86`, Evidence | `Last observed {timeIST(detail.last_seen)} IST` | `Last observed {dateTimeIST(detail.last_seen)}` |
| `Cases.jsx:93`, Evidence weather | `at ${weather.time_utc}` | `at ${dateTimeIST(weather.time_utc)}` |
| `Cases.jsx:154`, report | `Last observed {selected.snapshot.last_seen}` | `Last observed {dateTimeIST(selected.snapshot.last_seen)}` |
| `Cases.jsx:159`, report SAR line | `{d.observed_at}` | `{dateTimeIST(d.observed_at)}` |
| `Cases.jsx:163`, sign-off | `at {selected.signed_at}` | `at {dateTimeIST(selected.signed_at)}` |
| `VesselPanel.jsx:91` | `Last position {timeIST(detail.last_seen)} IST` | `Last position {dateTimeIST(detail.last_seen)}` |

The helper adds `IST` itself, so the result must never read `IST IST`. Remove the `timeIST` import from a file that no longer uses it.

### 3. Add a date and status to report list rows

In `Cases.jsx:148`, keep `#{r.id} · {vesselName(r.snapshot)}` and add a second line inside the same link:

```jsx
<span className="block text-[13px] text-muted">{dateTimeIST(r.created_at)} · {r.signed_at ? 'Signed' : 'Awaiting review'}</span>
```

The API returns `created_at` on each report (`SELECT *` from `incident_reports`, and the column is `NOT NULL`).

## Limits

- Change only what this story needs. Do not reformat files or change other wording.
- Leave these as they are:
  - the raw JSON under "View source snapshot", because it is the stored record;
  - time-only labels in `MapPage.jsx`, `AttentionCard.jsx`, `Shell.jsx`, `TrackTimeline.jsx` and `OceanMap.jsx`.
- In `Shell.test.jsx`, add only the test listed below. Do not change `Shell.jsx`.
- Do not change `api.js`, `usePolling.js`, `fixtures.js`, `setup.js`, package files or lockfiles. In tests, build a variant with a spread, such as `{ ...sampleReport, created_at: '2026-10-13T06:40:48Z' }`.
- Do not write in `apps/api/**`, `infra/**`, `docs/contracts/**`, `docs/DATA_MANIFEST.md`, `README.md` or `docs/FINAL_PRODUCT_PLAN.md`. If the story needs a change there, set STATUS to BLOCKED and say what it needs.
- Do not write in `docs/demo/loop/` except `REPORT.md`. Do not stage anything in `docs/demo/loop/`.
- Do not change the assertions of existing tests. If an existing test fails because of this story, stop and report it.
- Other work may be in this working tree. If a file you did not expect has changes, leave it and list it in the report.
- Stage files by exact path. Do not push.
- If you change anything this prompt does not ask for, including test setup, list it in the report under "Changes beyond the story".

## Tests

Write the tests before the change, and run them to see them fail. Add one test for each row. Each test must fail without the change.

In `apps/web/tests/format.test.js`, add one test for each row of the `dateTimeIST` table above, using exact output.

In `apps/web/tests/Cases.test.jsx`, check the rendered text. The `seaPearlDetail` fixture has `last_seen: '2026-10-13T06:40:48Z'`, which is `13 Oct 2026, 12:10 IST`.

| # | Situation | Expected |
|---|---|---|
| A | Evidence opens | Contains `Last observed 13 Oct 2026, 12:10 IST` |
| B | Evidence weather is available with `time_utc: '2026-10-13T06:40:48Z'` | Contains `at 13 Oct 2026, 12:10 IST` and does not contain `2026-10-13T06:40:48Z` |
| C | Report opens | Contains `Last observed 13 Oct 2026, 12:10 IST` and, outside the closed source snapshot, no raw `last_seen` string |
| D | Report has a SAR candidate with `observed_at: '2026-10-13T06:40:48+00:00'` | The SAR line contains `13 Oct 2026, 12:10 IST` and does not contain `+00:00` |
| E | Report is signed with `signed_at: '2026-11-03T10:00:00Z'` | Contains `Signed by Officer Rao at 3 Nov 2026, 15:30 IST` |
| F | Two reports of one vessel with different `created_at` values | Their list links show different dates |
| G | Unsigned report with `created_at` | Its list link contains `13 Oct 2026, 12:10 IST · Awaiting review` |
| H | Signed report with `created_at` | Its list link contains `· Signed` |
| I | Report with no `created_at` | Its list link contains `Time not reported · Awaiting review`, and the page still draws |

In `apps/web/tests/VesselPanel.test.jsx`:

| # | Situation | Expected |
|---|---|---|
| J | Panel opens with `seaPearlDetail` | Contains `Last position 13 Oct 2026, 12:10 IST`, and does not contain `IST IST` |

In `apps/web/tests/Shell.test.jsx`, a test gap from the last round:

| # | Situation | Expected |
|---|---|---|
| K | Banner rows that warn: offline with data, offline with no data, API error with no data | Banner class contains `pill-amber` |
| L | Banner rows that do not warn: checking the data source, and data mode shown | Banner class does not contain `pill-amber` |

`apps/web/tests/MapPage.test.jsx` is not a write path, so the row "API error with data" is not in K. The lead checked it in a browser.

Row K and L tests must fail if the banner loses its warning style.

The lead runs your tests against broken versions, including one that adds `IST` twice, one that reads a time with no offset as local time, one that shows the time without the date, one that uses the raw string on the signed line, and one that drops the warning style.

## Done when

1. Every row of the `dateTimeIST` table and of the three test tables has a test, and the tests pass.
2. `npm --prefix apps/web test` and `npm --prefix apps/web run build` exit 0.
3. The work is one commit on `b/sprint`. Use this subject and body:
   - Subject: `Show the date and timezone on every evidence time (B-05)`
   - Body: `Report rows show a date and status so repeat snapshots can be told apart. A time that is missing or has no offset reads Time not reported.`
4. After the commit, in the repo root:
   - `git diff --check 1cca0529619a1fb984d9cde0fb832f5f25cf8128 HEAD` exits 0.
   - `git status --short` lists nothing outside `docs/demo/loop/`. The loop files are tracked, so `docs/demo/loop/` entries such as `NEXT_PROMPT.md`, `STORIES.md` and files in `rounds/` are expected there. Leave them alone.

## Last step: write the report

Write the report with your file-writing tool, as the last thing you do, to `docs/demo/loop/REPORT.md`. The lead's review starts when this file appears, so do not create it before the work is finished. If you cannot finish, still write it, with `STATUS: BLOCKED`.

Report only what you ran and saw. Copy the real numbers from the command output. If you did not run a check, write "not run".

After you write the report, do not save, format or edit any file.

~~~markdown
ROUND: 6
STORY: B-05
STATUS: DONE or BLOCKED
COMMIT: full SHA, or none

## Changed files
One path per line.

## Checks
| Command | Exit code | Passed | Failed | Skipped |

## git status --short
Paste the output, run after the commit.

## Done-when items
For each numbered item: met or not met, and the evidence.

## Limitations and contract needs
Anything that does not work yet, or that owner A must change. Write "none" if there is nothing.

## Changes beyond the story
Anything you changed that this prompt did not ask for, and why. Write "none" if there is nothing.

## Unexpected changes
Files with changes you did not make. Write "none" if there are none.

## Blocker
The exact error and what you tried. Delete this section if STATUS is DONE.
~~~
