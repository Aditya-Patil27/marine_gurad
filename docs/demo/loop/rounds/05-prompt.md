# Round 5 — B-04: Show one data-mode banner on every screen

You implement owner B's work on SamudraSense. A lead reviews your work from the report you write in the last step. Do this story only. When the report is written, stop. Do not start another story.

~~~text
Task:        B-04 / F13
Owner:       B
Branch:      b/sprint. It is already checked out. Do not create or switch branches.
Base commit: 56d017a2ec4cc440f4cbc5625a59441bf986a016
Write paths: apps/web/src/components/Shell.jsx
             apps/web/src/pages/MapPage.jsx
             apps/web/tests/Shell.test.jsx
             apps/web/tests/MapPage.test.jsx
             docs/demo/loop/REPORT.md (last step only)
Depends on:  B-03, which added sourceLabel to apps/web/src/lib/format.js. The API has no data-mode field yet, so today the banner reads "Data mode: Source not reported". That is the correct result.
Outcome:     every screen says what kind of data it is showing, including when the console is offline or cannot reach the API, and nothing reads as live unless the data says it is live.
~~~

## The defect

1. No screen says whether its data is live, historical, cached or synthetic. The only overall signal is the status pill on the map.
2. The dot in that pill (`MapPage.jsx:150`) is green whenever the last request worked, and also while it says "Connecting…". Seeded demo vessels therefore sit under a green dot.
3. When the browser is offline, or the API stops answering, only the map says so. Other screens show nothing.

## The change

### 1. Add a banner to `Shell.jsx`

Add a `DataModeBanner` component in `Shell.jsx`. It takes the `fleet` object that `Shell` already has and shows exactly one of these lines. Use the first row that applies.

| # | State | Text | Style |
|---|---|---|---|
| 1 | Browser offline, `fleet.data` present | `Offline · last sync {timeIST(fleet.updatedAt)} IST · Live AIS and new satellite data need a connection.` | warning |
| 2 | Browser offline, no `fleet.data` | `Offline · nothing synced yet · Live AIS and new satellite data need a connection.` | warning |
| 3 | `fleet.error`, `fleet.data` present | `Can't reach the API · last sync {timeIST(fleet.updatedAt)} IST · Showing the last data received, not live.` | warning |
| 4 | `fleet.error`, no `fleet.data` | `Can't reach the API · no data loaded yet` | warning |
| 5 | No `fleet.data` and no error | `Checking the data source…` | neutral |
| 6 | `fleet.data` present and no error | `Data mode: {sourceLabel(fleet.data)}` | neutral |

Rows 1 and 3 must not say "Live data", even when `fleet.data.data_mode` is `live`.

Banner markup:

```jsx
<div role="region" aria-label="Data mode" aria-live="polite" className={`border-b border-line px-4 py-1.5 text-[13px] ${warning ? 'pill-amber' : 'bg-white text-muted'}`}>
```

Do not use `role="status"`. The existing `MapPage` tests call `screen.getByRole('status')` and expect only the map pill to match.

Track the browser state with `useSyncExternalStore`, subscribing to the window's `online` and `offline` events and reading `navigator.onLine`.

### 2. Change the Shell layout

Keep the rail. Wrap `main` so the banner sits above the page, in the right-hand column only:

```jsx
<div className="flex min-h-0 min-w-0 flex-col">
  <DataModeBanner fleet={fleet} />
  <main className="relative min-h-0 min-w-0 flex-1">
    {/* the existing PageBoundary, unchanged */}
  </main>
</div>
```

Pages use `h-full`, and the map uses `absolute inset-0`. The lead checks in a browser that the map still fills its area and that long pages still scroll.

### 3. Fix the map pill's dot in `MapPage.jsx`

Keep the pill's text. Change only the dot's colour class:

| State | Class |
|---|---|
| `fleet.error` | `bg-risk-red` |
| `sourceLabel(fleet.data) === 'Live data'` | `bg-risk-green` |
| Anything else, including while connecting | `bg-faint` |

## Limits

- Change only what this story needs. Do not reformat files or change other wording.
- Do not read `data_mode` directly. Call `sourceLabel`.
- Do not pause polling when offline, and do not add new API calls.
- Do not change how `timeIST` works. B-05 handles dates.
- Do not change `api.js`, `format.js`, `usePolling.js`, `fixtures.js`, `setup.js`, package files or lockfiles. In tests, build a variant with a spread, such as `{ ...fleet, data_mode: 'live' }`.
- Do not write in `apps/api/**`, `infra/**`, `docs/contracts/**`, `docs/DATA_MANIFEST.md`, `README.md` or `docs/FINAL_PRODUCT_PLAN.md`. If the story needs a change there, set STATUS to BLOCKED and say what it needs.
- Do not write in `docs/demo/loop/` except `REPORT.md`. Do not stage anything in `docs/demo/loop/`.
- Do not change the assertions of existing tests. If an existing test fails because of this story, stop and report it.
- Other work may be in this working tree. If a file you did not expect has changes, leave it and list it in the report.
- Stage files by exact path. Do not push.
- If you change anything this prompt does not ask for, including test setup, list it in the report under "Changes beyond the story".

## Tests

Write the tests before the change, and run them to see them fail. Add one test for each row. Each test must fail without the change.

Find the banner with `screen.getByRole('region', { name: 'Data mode' })` and check its `textContent`.

To simulate offline, use `vi.spyOn(window.navigator, 'onLine', 'get').mockReturnValue(false)` before `open`. To change state after the page is open, change the spy's return value, then call `window.dispatchEvent(new Event('offline'))` or `new Event('online')` inside `act`. `Shell.test.jsx` already restores mocks after each test.

In `apps/web/tests/Shell.test.jsx`:

| # | Situation | Expected banner |
|---|---|---|
| A | Fleet has no `data_mode` | Exactly `Data mode: Source not reported` |
| B | Fleet has `data_mode: 'live'` | Exactly `Data mode: Live data` |
| C | Fleet has `data_mode: 'synthetic'` | Exactly `Data mode: Synthetic data` |
| D | Fleet has `data_mode: 'live'`, browser offline | Starts `Offline · last sync`, says `need a connection`, and does not contain `Live data` |
| E | Fleet request never answers, browser offline | Starts `Offline · nothing synced yet` |
| F | Fleet request rejects with no data | Exactly `Can't reach the API · no data loaded yet` |
| G | Fleet request never answers, browser online | Exactly `Checking the data source…` |
| H | Page open and online, then the browser goes offline, then back online | Changes to `Offline ·`, then back to `Data mode:` |
| I | A page that fails to draw | The banner is still there, as well as the "This screen stopped working" alert |

In `apps/web/tests/MapPage.test.jsx`, which has fake timers and `settle`:

| # | Situation | Expected |
|---|---|---|
| J | Fleet with `data_mode: 'live'` loaded, then a refresh fails (`settle(30000)`) | Banner starts `Can't reach the API · last sync 18:33 IST` and does not contain `Live data` |
| K | Continuing from J, the API answers again (`settle(30000)`) | Banner is back to `Data mode: Live data` |
| L | Fleet has no `data_mode` | The pill's dot has class `bg-faint`, not `bg-risk-green` |
| M | Fleet has `data_mode: 'live'` | The pill's dot has class `bg-risk-green` |
| N | Fleet request rejects | The pill's dot has class `bg-risk-red` |
| O | Fleet request never answers | The pill's dot has class `bg-faint`, not `bg-risk-green` |

Find the dot with `screen.getByRole('status').querySelector('[aria-hidden="true"]')`.

The lead runs your tests against broken versions, including one that shows "Live data" while offline, one that keeps the old always-green dot, and one that takes the banner out of the shell.

## Done when

1. Every row of both test tables has a test, and the tests pass.
2. `npm --prefix apps/web test` and `npm --prefix apps/web run build` exit 0.
3. The work is one commit on `b/sprint`. Use this subject and body:
   - Subject: `Show one data-mode banner on every screen (B-04)`
   - Body: `Offline and API failure states never read as live. The map status dot is green only for live data.`
4. After the commit, in the repo root:
   - `git diff --check 56d017a2ec4cc440f4cbc5625a59441bf986a016 HEAD` exits 0.
   - `git status --short` lists nothing outside `docs/demo/loop/`. The loop files are now tracked, so `docs/demo/loop/` entries such as `NEXT_PROMPT.md` and `STORIES.md` are expected there. Leave them alone.

## Last step: write the report

Write the report with your file-writing tool, as the last thing you do, to `docs/demo/loop/REPORT.md`. The lead's review starts when this file appears, so do not create it before the work is finished. If you cannot finish, still write it, with `STATUS: BLOCKED`.

Report only what you ran and saw. Copy the real numbers from the command output. If you did not run a check, write "not run".

After you write the report, do not save, format or edit any file.

~~~markdown
ROUND: 5
STORY: B-04
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
