# B1 - replay-aware stored alerts

Status: COMPLETED. Owner: B only. Started 8 November 2026; completed 9 November 2026.

## Outcome

Connect the existing stored-alert sync control to A1's selected-window contract. Historical replay sends the
exact shared UTC anchors and rolling mode sends its explicit 168-hour lookback. The server-resolved window is
shown after sync, while the stored lifecycle list remains plainly labelled as global history.

## Allowed paths and dependencies

- Writes: `apps/web/**`, this record and `tasks/parallel/B-status.md`.
- Frozen dependency: A1 contract in `tasks/parallel/A-A1.md`; stable isolated backend image
  `samudrasense-api:014-a1` on port 8002, schema 014.
- Preserve B0 event-only review and completed B2 audit. No backend, infrastructure, credential or master-doc edits.

## Callers and compatibility

- `alertsApi.sync` accepts the selected replay window and posts A1's existing request body.
- `StoredAlerts` receives the shared selection, retains global list/filter/lifecycle behavior, and reloads rather
  than merging rows after sync or conflict.
- Existing acknowledge/resolve/reopen version handling and the assessment-backed alert cards remain unchanged.

## Acceptance checks

- Focused tests prove exact historical anchors, explicit rolling lookback, response-window/global-scope text,
  empty sync, late/repeated reload without duplicate UI rows, resolved records staying resolved, and 409 reload.
- Existing B0/lifecycle regression tests and production build pass.
- Actual browser verification against the stable A1 runtime exercises historical sync, repeated sync/global
  list behavior and visible source/window identity. A backend mismatch is recorded and blocks completion.

## Implementation and preserved work

- `apps/web/src/lib/api.js`: adopted the interrupted B1 caller, which posts exact `window_start` / `window_end`
  anchors with the calculated lookback for replay and `{ lookback_hours: 168 }` for rolling.
- `apps/web/src/pages/Cases.jsx`: adopted the shared-selection wiring, screening wording and explicit global-history
  label. Finished the rolling result message by showing the server-returned bounds as well as its duration.
  Kept lifecycle writes and the status filter disabled through the reload so an in-flight reload cannot be
  overtaken by another sync or captured against a changed filter. Sync/conflict results reload the authoritative
  list; no client-side merging or lifecycle inference was added.
- `apps/web/tests/Lifecycle.test.jsx`: retained the interrupted B1 request/summary/empty/repeat/resolved checks;
  added delayed-reload control and sync-409 reload checks and the rolling returned-bounds assertion.
- Inherited B0 event-only changes in the same files and `tests/B005FEventOnly.test.jsx` were preserved.
  No backend, infrastructure, master-document or dataset file changed.

## Verification actually run - 9 November 2026

- From `apps/web`, `npm test -- tests/Lifecycle.test.jsx tests/B005FEventOnly.test.jsx tests/B005Journey.test.jsx tests/Cases.test.jsx`
  -> **4 files, 81 tests passed**. This covers real `api.js` request bodies, exact replay anchors, rolling lookback,
  returned historical/rolling window text, source/global scope, empty sync, delayed and repeated reloads,
  resolved-state preservation, sync/lifecycle 409 and the existing event-only/assessment-backed B0 journeys.
- `npm run build` -> **passed**, 1,985 modules transformed; production assets generated.
- `git diff --check -- apps/web` -> **passed**.
- Docker Desktop was initially stopped. Started it and the existing isolated B compose backend; verified image
  `samudrasense-api:014-a1` and Alembic `014 (head)`. No shared stack was started, reset, seeded or migrated.
- Started Vite on `:5174` with `API_PROXY_TARGET=http://127.0.0.1:8002`. `npm run dev -- --port ...` was rejected
  by local npm flag parsing; using `node node_modules/vite/bin/vite.js --port 5174 --strictPort` worked.
- Real headless Edge/CDP check: `node apps/web/.agent-runs/b1-resume/browser-check.mjs` -> **passed**.
  A local analyst was created through the existing auth service only in isolated `samudrasense_b` after verifying
  that database identity; its password was passed privately through stdin, never printed or added to source.
  Login succeeded. Two historical syncs sent exactly `2026-10-30T00:00:00Z` to `2026-11-02T00:00:00Z` with
  `lookback_hours: 72`; rolling sent only `lookback_hours: 168`. All returned zero observed/created/updated rows,
  unknown source and global scope. Both historical summaries displayed the selected bounds; rolling displayed
  the server-resolved 168-hour bounds. The global list remained empty with no duplicate rows or page exceptions.
- Ignored evidence under `apps/web/.agent-runs/b1-resume/`: `browser-check.mjs`, `browser-evidence.json`,
  `historical-sync.png`, `rolling-sync.png`. The historical screenshot was visually inspected.
  The initial browser harness stalled around login reload; a fresh tab with the established session and bounded
  CDP command timeouts completed the recorded check. No application fix was required for that harness issue.

## Limits and handoff

The browser used an empty isolated database: nonempty late-observation/resolved lifecycle behavior is covered
by the focused frontend tests and A1's recorded disposable-PostGIS checks, not newly claimed browser evidence.
No live provider acquisition, coverage claim or full-suite/release audit was performed. Dataset changes: none.
No backend score/window mismatch was observed. B1 has no remaining blocker; further B2 work needs A2's published
contract and its own assignment. The isolated backend `:8002` and Vite `:5174` remain available for review.
