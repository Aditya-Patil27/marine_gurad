# Master prompt: owner B's remaining stories

You implement owner B's work on SamudraSense from start to finish. No lead reviews you between stories. A lead checks everything once at the end, from the code and from `docs/demo/loop/MASTER_REPORT.md`, so the report must be exact.

This prompt can be run more than once. On every run, start at "Start of run".

## Start of run

1. Confirm the branch is `b/sprint`. If it is not, stop. Do not create or switch branches.
2. Run `git status --short`. Changes in `docs/demo/loop/` and an untracked `graphify-out/` are expected. If anything else has changes, stop and report it. A later step can only be trusted from a clean start.
3. Read these:
   - `docs/demo/loop/STORIES.md`: the ledger, including the review notes.
   - `docs/FINAL_PRODUCT_PLAN.md`: section 1, the F-numbers each story names in section 4, sections 6 and 7, and section 11.
   - `docs/demo/loop/MASTER_REPORT.md`, if it exists.
4. Work through the stories below in order. Skip any that `STORIES.md` marks `done`.

## Rules for every story

**Scope**
- Do one story at a time, and only what it says. Do not refactor or reformat.
- Never do the stories marked `you` in `STORIES.md`. They need a person: H-01, H-02, H-03, H-04.

**Write paths**
- You may write only in `apps/web/**` and `docs/demo/**`.
- Never write in `apps/api/**`, `infra/**`, `docs/contracts/**`, `docs/DATA_MANIFEST.md`, `README.md` or `docs/FINAL_PRODUCT_PLAN.md`. These belong to owner A. You may read them.
- Do not change `package.json` or lockfiles.
- If a story needs a change in A's files, mark it `blocked`, write what it needs in the report, and move to the next story that does not depend on it.

**Honesty in the product**
- A signal is an indicator, not proof of an offence. Weather and environmental values are context: they never change a risk score, and the screen never implies they caused anything.
- Missing data reads as missing, such as "Source not reported". It never reads as live or as a clean result.
- Never put a made-up value on a production screen. A fixture may be used only in tests.
- Keep secrets out of code, logs, screenshots and examples. Do not open `.env` files or anything in `~/.gemini`.

**Tests**
- Run tests with `npm --prefix apps/web test` and the build with `npm --prefix apps/web run build`, from the repo root.
- Write each test first and watch it fail. A test that guards behaviour that is already correct is allowed, and the story says when.
- Check exact rendered text or behaviour, not only that something rendered.
- Do not change an existing test's assertions, unless the story changes that text on purpose. List each one you change in the report.
- A detail mock needs `generated_at`. Build variants of `seaPearlDetail` from `apps/web/tests/fixtures.js` with a spread. Do not edit `fixtures.js` except to add new exports.

**Break check, because no one reviews between stories**
- Before committing a story with code, take each behaviour in the story, break it in the source, and run its test file to confirm a test fails. Then undo the break by editing the line back.
- Report each one as caught or survived. If a break survives, add the missing test and repeat.
- Never use `git checkout`, `git restore`, `git stash`, `git reset` or `git clean`. Confirm with `git diff` that no break is left in the code.

**Commits**
- Commit each story once, on `b/sprint`, after tests and build exit 0.
- Stage files by exact path. Never use `git add .` or `git add -A`. Never stage `graphify-out/`.
- Write a plain subject that says what changed and ends with the story ID, such as `Give Draft report its own action (B-16b)`. Add a one- or two-sentence body. Do not add a `Co-Authored-By` line.
- Keep `STORIES.md` and `MASTER_REPORT.md` out of the story's commit. See "Final step".
- Never push, merge, rebase, amend or open a pull request. The user does those.

**When to stop**
- If a story still fails after two honest attempts, stop the whole run, because half-done work in the tree would contaminate the next story. Leave the work uncommitted, write the exact error in the report, and go to "Final step".
- If a story's dependency is missing, mark the story `blocked` and go on. Do not stop.
- Report only what you ran and saw. Write "not run" for anything you did not run.

## Stories

### B-16b: behaviour fixes

Read the code first, because line numbers can move.

1. **Draft report gets its own action.** In `apps/web/src/features/map/VesselPanel.jsx`, "Open evidence" and "Draft report" go to the same place. "Draft report" must create a report and open it, as Evidence's `createReport` does in `apps/web/src/pages/Cases.jsx`: call `reportsApi.create(mmsi)`, then go to `/reports?id=<new id>`. While the request is pending, the button is disabled, so a double click creates one report. On failure, show the error in the panel and stay there. "Open evidence" does not change.
2. **A late sign-off rejection stays with its report.** In `ReportsPage.sign()` in `Cases.jsx`, the result is applied after the `await`, even if the officer has opened another report by then. Discard the outcome, both error and success, for a report that is no longer selected. A rejection that arrives while its own report is open still shows.
3. **The map pill's dot is not green while offline.** `MapPage.jsx` keeps the dot green under Shell's amber "Offline" banner. Move Shell's online check (`subscribeOnline`, `getOnlineSnapshot`, `useSyncExternalStore`) into a shared hook at `apps/web/src/lib/useOnline.js`, and use it in both files. Dot order: `fleet.error` red, then offline grey (`bg-faint`), then the current rule. Shell's behaviour does not change.
4. **Test gap, guarding correct behaviour.** Add a test for a factor `detail` that contains a raw AIS name, such as `HAI FENG 818`, on Evidence and on the report. The factor row shows `Hai Feng 818`. On the report, check the row only, because the snapshot JSON stays raw.

Tests and breaks to cover:
- Draft report calls create once on a double click, navigates to the new ID, and shows the error without navigating on failure. Break: send it to the vessel link.
- A rejection arriving after the officer opens report #2 does not appear on #2. A rejection arriving on #1 still appears. Break: remove the check.
- Dot is green online with live data, grey offline with live data, and red offline with `fleet.error`. Break: remove the offline branch.
- Factor `detail` on Evidence and on the report. Breaks: print `f.detail` raw in each.

### B-06: storyboard

Write `docs/demo/storyboard.md` with two parts:
1. A problem statement.
2. A video storyboard, in a table of scene, screen shown, what is said, and how long it runs.

Use only what is true in `docs/FINAL_PRODUCT_PLAN.md` section 8, the judging gate, and the current screens. The walkthrough is climate-centred. It states whether each source is live, historical, cached or synthetic. It calls the risk engine rule-based. It describes climate impact as an expected pathway, not an observed outcome. Do not invent numbers: where a measurement does not exist yet, write `[measure at B-13]`. Mark a scene `[depends on A]` if its screen does not exist yet. No break check for this story.

### B-07: map environmental value (F08)

The map shows one dated regional environmental value with units and attribution.

- First look in `apps/api` and `apps/web/src/lib/api.js` for an endpoint that already supplies such a value.
- If one exists, use it, and show the value, unit, date with a labelled timezone, and source attribution. When it is missing or fails, show "Environmental data not available", never a guess.
- If none exists, build the display and its tests against a test fixture, keep every field name in one place, and show the "not available" state on the production screen. Mark the story `blocked: needs A's endpoint` in `STORIES.md`, commit what works, and write the field names you assumed in the report for H-01.

Breaks: remove the unit, date or attribution, and make a failure show a value.

### B-08: link to that value (F07, F08)

The vessel panel and Evidence link to the B-07 value. The wording states context only: no "caused by", "because of" or similar. If B-07 is `blocked`, do only what works without the endpoint and mark this one `blocked` with the same reason.

Breaks: remove the link, and remove the date from it.

### B-09: limitations and report checks (F03, F09, F13)

Evidence shows the data limitations beside the rule factors. The report view also shows `checks` and the line that these are indicators, not proof of an offence. `Cases.jsx` omits both from the report today. Handle a snapshot with no `checks` or no limitations: an older snapshot must still draw, and it says they are not reported.

Breaks: remove each one, and crash on a missing `checks`.

### Gate before B-10

Continue only if all of these are true:
- `docs/contracts/` exists in this working tree.
- The endpoints it describes exist in `apps/api` in this tree.
- The Docker stack starts, using a disposable compose project name. Never run `docker compose down -v` on a project you did not create.

If any is false, mark B-10, B-11, B-12, B-13 and B-14 `blocked: needs A's 6 Nov delivery`, and go to "Final step". This is the expected result until A delivers, and it is not a failure. Do not fake A's endpoints to get past it.

### B-10: real endpoints

The journey runs on A's real endpoints instead of fixtures: map, panel, alerts, evidence, report, sign-off. Field names follow `docs/contracts/`, including the placeholder `data_mode` from B-03, which H-01 may rename. Update the tests that assume old names, and list each one in the report.

### B-11: report sources and export (F09)

The report view links each fact to its source and exports sourced JSON, using A's export.

### B-12: failure and replay tests (F13)

Tests cover missing sources, real-data replay, and weather that the backend itself reports as `unavailable`.

### B-13: measurements (F14)

Record review time and evidence completeness on the available cases, with sample size and limits. Measure real runs only. Then fill any `[measure at B-13]` in the storyboard.

### B-14: production check (F13)

Run the full journey from a production build on the prepared setup, and fix presentation problems at 1366×768 and 1920×1080. Check the time-only labels on map tags, the track timeline and the banner, which B-05 left on purpose. Save screenshots outside the repo and give their paths in the report.

## Final step

1. Update `docs/demo/loop/STORIES.md`: set each story you handled to `done (short SHA)` or `blocked: reason`.
2. Write `docs/demo/loop/MASTER_REPORT.md`, adding to it if it exists, using the template below.
3. Commit those two files together with the subject `Record the master prompt run`. If `docs/demo/loop/MASTER_PROMPT.md` is untracked, include it as well.
4. From the repo root, run `graphify update apps/web/src`. It needs no LLM. Do not stage what it writes. Put its exit code and the output path in the report by editing the report without committing again. If the command fails, write the error and continue.
5. Stop. Do not start anything else.

~~~markdown
# Run <date and time>

## Final state
HEAD: full SHA
Tests: passed / failed / skipped, copied from the last run
Build: exit code
git status --short: pasted
graphify: exit code and output path

## Stories
| ID | Status | Commit | Changed files |

## Break check
| Story | Break | Caught or survived |

## Existing tests changed
Which ones and why, or "none".

## Changes beyond the stories
What and why, or "none".

## For the user to raise with owner A
Field names assumed, missing endpoints, wrong API text. "none" if nothing.

## Not checked
Anything you could not run, such as a browser. Be specific.

## Blockers
The exact error and what you tried, or "none".
~~~
