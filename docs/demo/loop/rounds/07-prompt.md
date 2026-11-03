# Round 7 — B-16a: Correct the wording on alerts, evidence and placeholders

You implement owner B's work on SamudraSense. A lead reviews your work from the report you write in the last step. Do this story only. When the report is written, stop. Do not start another story.

~~~text
Task:        B-16a / F13
Owner:       B
Branch:      b/sprint. It is already checked out. Do not create or switch branches.
Base commit: 5ee3732ce15a23e9ceaaa162cde0bd274ab07a74
Write paths: apps/web/src/lib/format.js
             apps/web/src/pages/Cases.jsx
             apps/web/src/pages/NotBuiltYet.jsx
             apps/web/tests/format.test.js
             apps/web/tests/Cases.test.jsx
             apps/web/tests/NotBuiltYet.test.jsx (new file)
             docs/demo/loop/REPORT.md (last step only)
Depends on:  none
Outcome:     the alerts, evidence, report and placeholder screens say only what is true, and they do not contradict themselves.
~~~

## The defect

1. The Spills and Settings placeholders promise the 10 Nov prototype. These screens are not in that prototype.
2. The Alerts intro says "Weather and review status are not yet automated." Evidence already shows weather. The plan says weather is context and does not change the score.
3. Alerts and Evidence print raw AIS names, such as `SEA PEARL II went dark` and `HAI FENG 818`. The report's factor rows do the same.
4. Evidence prints `1 gaps · 1 encounters` and `2.47 h`. The same encounter reads `2 h 28 m` on the map.
5. A line can name a source and also say it is missing: `Source: Open-Meteo forecast/model data · Weather data: Source not reported`, and `Sentinel-1 · … · SAR data: Source not reported`. The source is known. What is missing is the data mode.
6. The last review found two test gaps. See rows N and O.

## The change

### 1. `NotBuiltYet.jsx`

The line at `NotBuiltYet.jsx:12` becomes exactly:

`This screen is designed but not built yet.`

### 2. Add `modeLabel` to `format.js`

Add and export `modeLabel(record)`. Build it on `sourceLabel`, so that `sourceLabel` stays the only code that reads `data_mode`. Do not change `sourceLabel`.

| Input | `modeLabel` output |
|---|---|
| `{ data_mode: 'live' }` | `Live data` |
| `{ data_mode: 'historical' }` | `Historical data` |
| `{ data_mode: 'cached' }` | `Cached data` |
| `{ data_mode: 'synthetic' }` | `Synthetic data` |
| `{}`, `null`, `undefined`, `{ data_mode: null }` | `Mode not reported` |
| `{ data_mode: 'realtime' }`, `{ data_mode: 'constructor' }` | `Mode not reported` |

### 3. `Cases.jsx`

| Place | Now | After |
|---|---|---|
| `Cases.jsx:17`, Alerts intro | `Current risk signals from the last 24 hours. Weather and review status are not yet automated.` | `Current risk signals from the last 24 hours. Weather does not change these scores. Open a vessel to see its weather, and Reports to see review status.` |
| `Cases.jsx:23`, Alerts row | `{v.headline}` | The headline with display names, using `withDisplayNames(v.headline, data.vessels)` |
| `Cases.jsx:90`, Evidence factors | `{f.label}`, `{f.detail}` | Both with display names. The names list is `[detail, ...detail.encounters]`. |
| `Cases.jsx:93`, Evidence weather | See the weather table below | |
| `Cases.jsx:98`, Evidence counts | `3 AIS positions · 1 gaps · 1 encounters` | Singular for 1, plural for all other numbers: `3 AIS positions · 1 gap · 1 encounter`, `1 AIS position · 2 gaps · 0 encounters` |
| `Cases.jsx:99`, Evidence encounter | `{e.name} · closest {e.closest_m} m · {e.hours} h` | `{vesselName(e)} · closest {e.closest_m} m · {hoursLabel(e.hours)}`, such as `Hai Feng 818 · closest 371 m · 2 h 28 m` |
| `Cases.jsx:106`, Evidence SAR | `SAR data: {sourceLabel(d)}` | `SAR data: {modeLabel(d)}` |
| `Cases.jsx:158`, report factors | `{f.label}`, `{f.detail}` | Both with display names. The names list is `[selected.snapshot, ...(selected.snapshot.encounters ?? [])]`, because an older snapshot can have no `encounters`. |
| `Cases.jsx:159`, report SAR | `SAR data: {sourceLabel(d)}` | `SAR data: {modeLabel(d)}` |
| `Cases.jsx:160`, report summary | `({…track.length} AIS positions)` | Same singular and plural rule: `(1 AIS position)`, `(3 AIS positions)` |

Weather line, for `weather.status === 'available'`. Only the part after the time changes. Keep the note at the end, as it is now.

| `source` | `data_mode` | The line reads |
|---|---|---|
| `Open-Meteo forecast/model data` | missing | `Source: Open-Meteo forecast/model data · Weather data: Mode not reported` |
| `INCOIS WRF-Chem` | `historical` | `Source: INCOIS WRF-Chem · Weather data: Historical data` |
| missing | missing | `Source not reported · Weather data: Mode not reported` |

The text `Source: Source not reported` must never appear.

## Limits

- Change only what this story needs. Do not reformat files or change other wording.
- Leave these as they are:
  - `AIS data: {sourceLabel(...)}` on Evidence and the report, because no AIS source is named on that line;
  - the raw JSON under "View source snapshot", because it is the stored record;
  - factor text that the API writes, such as `6.4 h so far`. Do not parse or rewrite durations inside API text. The lead will raise this with owner A.
- `App.jsx`, `Shell.jsx`, `MapPage.jsx` and `VesselPanel.jsx` are not write paths. The next round covers them.
- Do not change `api.js`, `usePolling.js`, `fixtures.js`, `setup.js`, package files or lockfiles. In tests, build a variant with a spread, such as `{ ...seaPearlDetail, gaps: [] }`.
- Do not write in `apps/api/**`, `infra/**`, `docs/contracts/**`, `docs/DATA_MANIFEST.md`, `README.md` or `docs/FINAL_PRODUCT_PLAN.md`. If the story needs a change there, set STATUS to BLOCKED and say what it needs.
- Do not write in `docs/demo/loop/` except `REPORT.md`. Do not stage anything in `docs/demo/loop/`.
- Do not change the assertions of existing tests, with these three exceptions in `Cases.test.jsx`. This story changes their text on purpose:
  - line 432: expect `/Source not reported · Weather data: Mode not reported/`;
  - line 433: remove it, because the new line 432 covers it;
  - line 504: expect `/SAR data: Mode not reported/`.
  You may reword the titles of those two tests, and you may add `AlertsPage` to the import on line 4. If any other existing test fails because of this story, stop and report it.
- Other work may be in this working tree. If a file you did not expect has changes, leave it and list it in the report.
- Stage files by exact path. Do not push.
- If you change anything this prompt does not ask for, including test setup, list it in the report under "Changes beyond the story".

## Tests

Write the tests before the change, and run them to see them fail. Add one test for each row. Each test must fail without the change, except rows N and O, which guard behaviour that is already correct.

In `apps/web/tests/format.test.js`, add one test for each row of the `modeLabel` table, using exact output.

Create `apps/web/tests/NotBuiltYet.test.jsx`. In `apps/web/tests/Cases.test.jsx`, check the rendered text. `seaPearlDetail` has 3 track points, 1 gap and 1 encounter (`HAI FENG 818`, `closest_m: 371`, `hours: 2.47`).

| # | File | Situation | Expected |
|---|---|---|---|
| A | NotBuiltYet | Placeholder renders with a title | Contains `This screen is designed but not built yet.`, and does not contain `Nov` or `prototype` |
| B | Cases | Alerts opens | Contains `Weather does not change these scores`, and does not contain `not yet automated` |
| C | Cases | Alerts opens with the `fleet` fixture | Contains `Sea Pearl II went dark for 6.4 h`, and does not contain `SEA PEARL II` |
| D | Cases | Evidence opens | Contains `Met Hai Feng 818`, and the page text does not contain `HAI FENG 818` |
| E | Cases | Evidence opens | Contains `3 AIS positions · 1 gap · 1 encounter` |
| F | Cases | Evidence with 1 track point, 2 gaps and no encounters | Contains `1 AIS position · 2 gaps · 0 encounters` |
| G | Cases | Evidence opens | Contains `Hai Feng 818 · closest 371 m · 2 h 28 m` |
| H | Cases | Encounter with `name: null` | The row starts `MMSI 412440918 · closest`, and the page still draws |
| I | Cases | Weather available, with `source: 'Open-Meteo forecast/model data'` and no mode | Contains `Source: Open-Meteo forecast/model data · Weather data: Mode not reported`, and the weather line does not contain `Source not reported` |
| J | Cases | Weather available, with no source and no mode | Contains `Source not reported · Weather data: Mode not reported`, and does not contain `Source: Source` |
| K | Cases | Evidence with a SAR match with `source: 'Sentinel-1'` and no mode | Contains `SAR data: Mode not reported`, and the SAR line does not contain `Source not reported` |
| L | Cases | Report opens | The factor row contains `Met Hai Feng 818`. Check the row only, because the snapshot JSON stays raw. |
| M | Cases | Report whose snapshot has no `encounters`, and a report with 1 track point | The page still draws. The second shows `View source snapshot (1 AIS position)`. |
| N | Cases | Evidence opens, and report opens | Neither page text contains `IST IST` |
| O | format.test | `dateTimeIST('2026-13-45T00:00:00Z')` | `Time not reported`, with no exception |

The lead runs your tests against broken versions, including one that adds `IST` twice on Evidence, one that shows a raw encounter name, one that always prints plurals, one that uses the old duration, and one that uses `sourceLabel` on a SAR line.

## Done when

1. Every row of the `modeLabel` table and of the test table has a test, and the tests pass.
2. `npm --prefix apps/web test` and `npm --prefix apps/web run build` exit 0.
3. The work is one commit on `b/sprint`. Use this subject and body:
   - Subject: `Correct the wording on alerts, evidence and placeholders (B-16a)`
   - Body: `Screens use display names, singular counts and one duration format. A named source with no data mode now reads Mode not reported.`
4. After the commit, in the repo root:
   - `git diff --check 5ee3732ce15a23e9ceaaa162cde0bd274ab07a74 HEAD` exits 0.
   - `git status --short` lists nothing outside `docs/demo/loop/`. The loop files are tracked, so `docs/demo/loop/` entries such as `NEXT_PROMPT.md`, `STORIES.md` and files in `rounds/` are expected there. Leave them alone.

## Last step: write the report

Write the report with your file-writing tool, as the last thing you do, to `docs/demo/loop/REPORT.md`. The lead's review starts when this file appears, so do not create it before the work is finished. If you cannot finish, still write it, with `STATUS: BLOCKED`.

Report only what you ran and saw. Copy the real numbers from the command output. If you did not run a check, write "not run".

After you write the report, do not save, format or edit any file.

~~~markdown
ROUND: 7
STORY: B-16a
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
