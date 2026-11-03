# Round 3 — B-15: Draw map layers without waiting for basemap tiles

You implement owner B's work on SamudraSense. A lead reviews your work from the report you write in the last step. Do this story only. When the report is written, stop. Do not start another story.

~~~text
Task:        B-15 / F13
Owner:       B
Branch:      b/sprint. It is already checked out. Do not create or switch branches.
Base commit: b5bc8c26be0156cb44f90c321f01decb0223a41f
Write paths: apps/web/src/features/map/OceanMap.jsx
             apps/web/tests/OceanMap.test.jsx (new file)
             docs/demo/loop/REPORT.md (last step only)
Depends on:  nothing. The tests mock MapLibre, so no backend or browser is needed.
Outcome:     vessels and zones appear, and vessels can be clicked, while basemap tiles are slow or failing.
~~~

## The defect

`apps/web/src/features/map/OceanMap.jsx:123` adds every source, layer and click handler inside `m.on('load', ...)`. MapLibre fires `load` only after the basemap tiles have finished. While the tiles are slow, the map shows no vessels or zones and clicks do nothing, under a header that says "14 vessels". This lasted 30 s in the journey test.

## The change

Replace line 123 with these two lines. Leave the body of the handler as it is.

```js
// Not 'load': it waits for basemap tiles, and vessels must show while tiles are slow or failing
m.on('style.load', () => {
```

The lead tested this change in a browser with tiles that were held for 15 s, failed at once, and loaded normally, and with a `/map?vessel=` link. The vessel panel opened in every case.

## Required behaviour

| # | Situation | The map must |
|---|---|---|
| 1 | The style is ready and the tiles have not finished | Pass the vessels to the `vessels` source and the zones to the `zones` source |
| 2 | Same | Call `onSelect` with the vessel's MMSI when the officer clicks the `vessel-arrow` layer |
| 3 | Same, with a selected vessel | Pass its track to the `track` source and call `fitBounds` once |
| 4 | The tiles finish later, so `load` fires after `style.load` | Not add its sources or layers a second time |

## Limits

- Change only what this story needs. Do not reformat `OceanMap.jsx`, split it, or change its layers, colours or other effects.
- Do not change `MapPage.jsx`, `MapPage.test.jsx`, `api.js`, `App.jsx`, `fixtures.js`, `setup.js`, package files or lockfiles.
- Do not write in `apps/api/**`, `infra/**`, `docs/contracts/**`, `docs/DATA_MANIFEST.md`, `README.md` or `docs/FINAL_PRODUCT_PLAN.md`. If the story needs a change there, set STATUS to BLOCKED and say what it needs.
- Do not write in `docs/demo/loop/` except `REPORT.md`. Do not stage `docs/demo/loop/`.
- Other work may be in this working tree. Do not run `git checkout`, `git restore`, `git stash`, `git reset` or `git clean`. If a file you did not expect has changes, leave it and list it in the report.
- Stage files by exact path. Do not run `git add -A` or `git add .`. Do not push.
- If you change anything this prompt does not ask for, including test setup, list it in the report under "Changes beyond the story".

## Tests

Create `apps/web/tests/OceanMap.test.jsx` with one test for each row of the table. Use `seaPearl` and `seaPearlDetail` from `fixtures.js`, and render the default export of `@/features/map/OceanMap`.

jsdom has no WebGL, so mock `maplibre-gl` with `vi.mock`. The lead tried this approach, and it works:

- The module's default export is `{ Map, Marker, LngLatBounds }`, all fake classes. Use `vi.hoisted` to give the tests access to the fake map that the component creates.
- The fake `Map` stores handlers from `on(type, fn)` and `on(type, layers, fn)`. It fires an event only when a test tells it to, so a test can fire `style.load` without `load`.
- The fake `Map` also needs `touchZoomRotate.disableRotation`, `addImage`, `addSource`, `addLayer`, `getSource`, `setLayoutProperty`, `getCanvas`, `getContainer`, `fitBounds` and `remove`. `getSource` returns an object with a `setData` mock.
- `addSource` must throw if the source ID already exists, as real MapLibre does. Row 4 depends on this.
- `arrowImage()` calls `canvas.getContext('2d')`, which returns null in jsdom. In `beforeEach`, use `vi.spyOn(HTMLCanvasElement.prototype, 'getContext')` to return a stub with `beginPath`, `moveTo`, `lineTo`, `closePath`, `fill` and `getImageData`.
- Fire events inside `await act(async () => { ... })`, because the handler sets React state.

The tests for rows 1, 2 and 3 must fail with `load` on line 123. Row 4 passes with `load` and with `style.load`. It fails only if the setup runs on both events. The lead runs your tests against the old code and against a version that registers both events.

## Done when

1. Every row of the table has a test, and the tests pass.
2. `npm test` and `npm run build` exit 0 in `apps/web`.
3. The work is one commit on `b/sprint`. Use this subject and body:
   - Subject: `Draw map layers without waiting for basemap tiles (B-15)`
   - Body: `Vessels and zones now appear and respond to clicks while tiles are slow or failing.`
4. After the commit, in the repo root:
   - `git diff --check b5bc8c26be0156cb44f90c321f01decb0223a41f HEAD` exits 0.
   - `git status --short` shows only `?? docs/demo/loop/`.

## Last step: write the report

Write the report with your file-writing tool, as the last thing you do, to `docs/demo/loop/REPORT.md`. The lead's review starts when this file appears, so do not create it before the work is finished. If you cannot finish, still write it, with `STATUS: BLOCKED`.

Report only what you ran and saw. Copy the real numbers from the command output. If you did not run a check, write "not run".

After you write the report, do not save, format or edit any file.

~~~markdown
ROUND: 3
STORY: B-15
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
