# Round 2 — B-17: Keep sign-off state with its report

You implement owner B's work on SamudraSense. A lead reviews your work from the report you write in the last step. Do this story only. When the report is written, stop. Do not start another story.

~~~text
Task:        B-17 / F13, plus two follow-ups from B-01
Owner:       B
Branch:      b/sprint. Run `git switch b/sprint` if you are on another branch. Do not create a branch.
Base commit: d75ec823466d62b009a05da7fa134a32fc9276dd
Write paths: apps/web/src/pages/Cases.jsx
             apps/web/tests/Cases.test.jsx
             docs/demo/loop/REPORT.md (last step only)
Depends on:  nothing. The tests mock the API, so no backend is needed.
Outcome:     an officer can record sign-off only on a report they ticked as reviewed,
             and an error from one report does not appear on another.
~~~

## The defect

`ReportsPage` in `apps/web/src/pages/Cases.jsx` keeps `reviewed` and `error` (lines 116-117) when the officer opens another report, because the component stays mounted.

To reproduce: tick "I reviewed the evidence and source snapshot." on report #1, type a name, then click report #2 in the list. The box is still ticked on #2, and "Record sign-off" is enabled on a report the officer never opened. An error from a rejected sign-off on #1 also stays on screen over #2.

## Required behaviour

| # | Situation | The page must |
|---|---|---|
| 1 | Officer ticks the box on report #1, then opens report #2 | Show the box unticked on #2. "Record sign-off" is disabled, even with a name typed. |
| 2 | Officer ticks the box on #1, opens #2, then returns to #1 | Show the box unticked on #1. The earlier tick does not come back. |
| 3 | Sign-off on #1 is rejected, then the officer opens #2 | Not show the rejection message on #2. |
| 4 | Officer types a name on #1, then opens #2 | Keep the name. It is the same officer, and the tick is the confirmation for each report. |
| 5 | Sign-off on a report is rejected and the officer stays on that report | Keep the message, the name and the tick, as it does now. |
| 6 | `/reports?id=2` | Show report #2 and its form. Signing calls `reportsApi.sign` with ID 2. |

An effect keyed on the selected report is enough. The lead tested this line after `useEffect(() => { refresh() }, [])`, and it meets all six rows:

```js
useEffect(() => { setReviewed(false); setError('') }, [selected?.id])
```

## Two follow-ups from B-01

1. **Announce the SAR failure.** The message at `Cases.jsx:102` has no `role="alert"`, unlike the other failure messages on this page. Add it. In the SAR failure test in `Cases.test.jsx`, change the assertion on that message to use `getByRole('alert')`.
2. **Remove a stray blank line.** `apps/web/tests/Cases.test.jsx` has one extra blank line at the end of the file. It is not committed, so `git status` shows this file as modified before you start. This is expected. Remove the line by editing the file.

## Limits

- Change only what this story needs. Do not reformat `Cases.jsx`, split it, or restyle it.
- Do not change `api.js`, `App.jsx`, `fixtures.js`, package files or lockfiles.
- Do not write in `apps/api/**`, `infra/**`, `docs/contracts/**`, `docs/DATA_MANIFEST.md`, `README.md` or `docs/FINAL_PRODUCT_PLAN.md`. If the story needs a change there, set STATUS to BLOCKED and say what it needs.
- Do not write in `docs/demo/loop/` except `REPORT.md`. Do not stage `docs/demo/loop/`.
- Other work may be in this working tree. Do not run `git checkout`, `git restore`, `git stash`, `git reset` or `git clean`. If a file you did not expect has changes, leave it and list it in the report.
- Stage files by exact path. Do not run `git add -A` or `git add .`. Do not push.

## Tests

Add one test for each row of the table to `apps/web/tests/Cases.test.jsx`. Reuse `sampleReport`, `sampleReport2` and `openReports`. Build the rejected sign-off error the same way the existing 422 test does. To open another report, click its link in the list.

The tests for rows 1, 2 and 3 must fail without your change. Rows 4, 5 and 6 protect behaviour that already works, so they pass with or without it. The lead runs your tests against the old page to check this.

## Done when

1. Every row of the table has a test, and the tests pass.
2. `npm test` and `npm run build` exit 0 in `apps/web`.
3. The work is one commit on `b/sprint`. Use this subject and body:
   - Subject: `Clear sign-off state when the report changes (B-17)`
   - Body: `Also announce a failed SAR request as an alert (B-01 follow-up).`
4. After the commit, in the repo root:
   - `git diff --check d75ec823466d62b009a05da7fa134a32fc9276dd HEAD` exits 0.
   - `git status --short` shows only `?? docs/demo/loop/`.

## Last step: write the report

Write the report with your file-writing tool, as the last thing you do, to `docs/demo/loop/REPORT.md`. The lead's review starts when this file appears, so do not create it before the work is finished. If you cannot finish, still write it, with `STATUS: BLOCKED`.

Report only what you ran and saw. Copy the real numbers from the command output. If you did not run a check, write "not run".

After you write the report, do not save, format or edit any file.

~~~markdown
ROUND: 2
STORY: B-17
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

## Unexpected changes
Files with changes you did not make. Write "none" if there are none. Do not list the stray blank line in `Cases.test.jsx`.

## Blocker
The exact error and what you tried. Delete this section if STATUS is DONE.
~~~
