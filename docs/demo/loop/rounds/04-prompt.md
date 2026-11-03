# Round 4 — B-03: Label where each piece of evidence came from

You implement owner B's work on SamudraSense. A lead reviews your work from the report you write in the last step. Do this story only. When the report is written, stop. Do not start another story.

~~~text
Task:        B-03 / F02, F13, plus one test follow-up from B-15
Owner:       B
Branch:      b/sprint. It is already checked out. Do not create or switch branches.
Base commit: f2a81ca4529e5c9f7c9a57d0d3673f5913b92427
Write paths: apps/web/src/lib/format.js
             apps/web/src/features/map/VesselPanel.jsx
             apps/web/src/pages/Cases.jsx
             apps/web/tests/format.test.js (new file)
             apps/web/tests/VesselPanel.test.jsx
             apps/web/tests/Cases.test.jsx
             apps/web/tests/OceanMap.test.jsx
             docs/demo/loop/REPORT.md (last step only)
Depends on:  nothing. The API has no data-mode field yet, so today every AIS label reads "Source not reported". That is the correct result.
Outcome:     an officer can see whether each source is live, historical, cached or synthetic, and a missing source is never shown as live.
~~~

## The defect

The product must always show whether data is live, historical, cached or synthetic. Today the vessel panel, evidence page and report view show no such label. The evidence page also drops the `source` and `note` that the weather API returns: `apps/web/src/pages/Cases.jsx:92` prints "Model estimate; review manually." instead.

## The change

### 1. Add one helper to `apps/web/src/lib/format.js`

```js
const DATA_MODES = {
  live: 'Live data',
  historical: 'Historical data',
  cached: 'Cached data',
  synthetic: 'Synthetic data',
}

/** Never guess: a missing or unknown mode must not read as live. Only this helper reads `data_mode`, so a contract rename is one line. */
export const sourceLabel = (record) =>
  Object.hasOwn(DATA_MODES, record?.data_mode ?? '') ? DATA_MODES[record.data_mode] : 'Source not reported'
```

No other file reads `data_mode`. All views call `sourceLabel`.

### 2. Show the labels

| # | Where | Show |
|---|---|---|
| 1 | `VesselPanel.jsx`, in a new `div` directly after the "Last position" line, with the same classes | `AIS data: {sourceLabel(detail)}` |
| 2 | `EvidencePage` in `Cases.jsx`, in a new `<p className="mb-2 text-muted">` directly after the "MMSI … Last observed" line | `AIS data: {sourceLabel(detail)}` |
| 3 | `EvidencePage`, in the weather line when `weather.status === 'available'` | Keep `{wind_kn} kn wind, {wave_m} m waves at {time_utc}.` Replace "Model estimate; review manually." with: `Source: {weather.source}, if the field is missing "Source not reported"`, then `Weather data: {sourceLabel(weather)}`, then `{weather.note}` if it is present |
| 4 | `EvidencePage`, in each SAR candidate line | Add `SAR data: {sourceLabel(d)}` before "Candidate match, not confirmed identity." |
| 5 | `ReportsPage` in `Cases.jsx`, directly after the "Values below come from…" paragraph, in a `<p className="text-muted">` | `AIS data: {sourceLabel(selected.snapshot)}` |
| 6 | `ReportsPage`, in each SAR candidate line | Add `SAR data: {sourceLabel(d)}` before "Identity not confirmed." |

Weather that is `unavailable` or `not_checked` still shows `weather.reason` only, with no label.

### 3. Tighten the B-15 map test

The lead's review found that the test for row 3 in `apps/web/tests/OceanMap.test.jsx` still passes if the map sends an empty track. In the test named `passes its track to the track source and calls fitBounds once…`, replace the `expect(trackSource.setData)` assertion with one that checks the points:

```js
const sent = trackSource.setData.mock.calls.at(-1)[0]
expect(sent.features[0].geometry.coordinates).toEqual(seaPearlDetail.track.map((p) => [p.lon, p.lat]))
```

## Limits

- Change only what this story needs. Do not reformat files, split `Cases.jsx`, or change other wording. Raw times stay as they are; B-05 handles them.
- Do not add a global banner. B-04 does that.
- Do not change `api.js`, `fixtures.js`, `setup.js`, package files or lockfiles. In tests, build a variant with a spread, such as `{ ...seaPearlDetail, data_mode: 'cached' }`.
- Do not write in `apps/api/**`, `infra/**`, `docs/contracts/**`, `docs/DATA_MANIFEST.md`, `README.md` or `docs/FINAL_PRODUCT_PLAN.md`. If the story needs a change there, set STATUS to BLOCKED and say what it needs.
- Do not write in `docs/demo/loop/` except `REPORT.md`. Do not stage `docs/demo/loop/`.
- Do not change the assertions of existing tests, except the one named in section 3. If an existing test fails because of this story, stop and report it.
- Other work may be in this working tree. If a file you did not expect has changes, leave it and list it in the report.
- Stage files by exact path. Do not push.
- If you change anything this prompt does not ask for, including test setup, list it in the report under "Changes beyond the story".

## Tests

Write the tests before the change, and run them to see them fail.

In `apps/web/tests/format.test.js`, test `sourceLabel`:

| Input | Label |
|---|---|
| `{ data_mode: 'live' }` | `Live data` |
| `{ data_mode: 'historical' }` | `Historical data` |
| `{ data_mode: 'cached' }` | `Cached data` |
| `{ data_mode: 'synthetic' }` | `Synthetic data` |
| `{}`, `null`, `undefined`, `{ data_mode: null }` | `Source not reported` |
| `{ data_mode: 'LIVE' }`, `{ data_mode: 'realtime' }`, `{ data_mode: 'constructor' }` | `Source not reported` |

In `VesselPanel.test.jsx` and `Cases.test.jsx`, add one test for each of these. In `Cases.test.jsx`, use the existing `openEvidence` and `openReports` helpers. Each test must fail without the change.

| # | Situation | Expected |
|---|---|---|
| A | Vessel panel, `seaPearlDetail` | "AIS data: Source not reported" |
| B | Vessel panel, `data_mode: 'cached'` | "AIS data: Cached data", and no "Live data" |
| C | Evidence, vessel with no `data_mode` | "AIS data: Source not reported" |
| D | Evidence, weather available with `source`, `note` and `data_mode: 'historical'` | The source text, the note text and "Weather data: Historical data" |
| E | Evidence, weather available with no `source`, `note` or `data_mode` | "Source: Source not reported" and "Weather data: Source not reported". The page must not show "undefined". |
| F | Evidence, weather `unavailable` | The reason, and no "Weather data:" |
| G | Evidence, a SAR candidate for this vessel with `data_mode: 'synthetic'` | "SAR data: Synthetic data" and "Candidate match, not confirmed identity." |
| H | Report, snapshot with `data_mode: 'cached'` | "AIS data: Cached data" |
| I | Report, snapshot with a SAR candidate and no `data_mode` | "SAR data: Source not reported" and "Identity not confirmed." |

Match text so that a test fails if the label is missing. The lead runs your tests against broken versions, including one that returns "Live data" for a missing mode and one that drops the weather note.

## Done when

1. Every row of both test tables has a test, and the tests pass.
2. `npm --prefix apps/web test` and `npm --prefix apps/web run build` exit 0.
3. The work is one commit on `b/sprint`. Use this subject and body:
   - Subject: `Label where each piece of evidence came from (B-03)`
   - Body: `A missing or unknown source is never shown as live. Evidence now shows the source and note the weather API returns. Also makes the B-15 track test check the track's points.`
4. After the commit, in the repo root:
   - `git diff --check f2a81ca4529e5c9f7c9a57d0d3673f5913b92427 HEAD` exits 0.
   - `git status --short` shows only `?? docs/demo/loop/`.

## Last step: write the report

Write the report with your file-writing tool, as the last thing you do, to `docs/demo/loop/REPORT.md`. The lead's review starts when this file appears, so do not create it before the work is finished. If you cannot finish, still write it, with `STATUS: BLOCKED`.

Report only what you ran and saw. Copy the real numbers from the command output. If you did not run a check, write "not run".

After you write the report, do not save, format or edit any file.

~~~markdown
ROUND: 4
STORY: B-03
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
