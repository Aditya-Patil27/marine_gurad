# B2 — local accounts, deployment settings and role-aware errors

Status: UI AND FIXTURE SLICE COMPLETE — browser/API integration of the Administrator forms WAITING for an A2
runtime snapshot. Owner: B only. Updated 9 November 2026.

Allowed writes: `apps/web/**`, `tasks/parallel/B-*.md`, `tasks/parallel/B-status.md`.

## Bounded objective

Use A2's published contract (`docs/contracts/AUTH_API.md`, `tasks/parallel/A-A2.md`) to expose the existing
login/session UI, read-only source health, Administrator-only deployment settings and local-account management,
and role/error states without placing secrets in the client. Keep the existing design, keyboard operation and
text state labels. Do not claim backend authorization from hidden controls.

## Implementation

- `/settings` now renders `Operations` instead of the previous placeholder: read-only `GET /sources/health`
  cards, and Administrator-only `GET/PUT /admin/settings` plus `GET/POST /admin/users` and
  `PATCH /admin/users/{id}/active` through `adminApi`.
- `authApi.me()` decides the visible slice. A Viewer/Analyst/Approver sees source health and a statement that
  Administrator access is required; only `ADMINISTRATOR` triggers the settings and account requests.
- Settings fields map to the contract: organisation, named AOI, WGS84 `[[west, south], [east, north]]` bbox,
  IANA display timezone, alert threshold, report recipients and retention days. Server validation details are
  shown without discarding the edited values.
- Account management lists roles and active state, blocks self-deactivation in the UI, and creates users with
  any of `VIEWER`, `ANALYST`, `APPROVER` or `ADMINISTRATOR`. Passwords are cleared after creation and never
  read back; no provider keys, connection strings or secrets exist in the client.
- `401` renders a sign-in explanation; `403` on source health and `409` on self-deactivation get specific
  messages. Source/health wording keeps configured/not-checked distinct from reachable or covered.
- New Overview landing page and nav entry reuse existing endpoints only; no invented counts or scores.

## Contract note

`POST /admin/users` accepts one or more roles. The initial implementation omitted `APPROVER` from the role
checkboxes even though the contract makes analysis and approval separate duties. The checkbox set now includes
all four roles, with a focused assertion.

## Verification actually run

- `npx vitest run tests/Operations.test.jsx` — 8 passed.
- `npx vitest run tests/Operations.test.jsx tests/Overview.test.jsx tests/Shell.test.jsx tests/MapPage.test.jsx
  tests/Cases.test.jsx tests/B005FEventOnly.test.jsx` — 6 files, 131 passed.
- `npx vite build` — passed.
- Browser on Vite `5174` proxying A's 014 runtime at `8002`: signed in by keyboard as `b_analyst` (ANALYST), then
  Overview, Map, Alerts, Vessels, Reports, Cases, Spills and Operations were loaded at 1366x768, 1920x1080 and
  768x1024. Zero overflow, one `h1` per page, zero page exceptions, and the Operations page correctly withheld
  the Administrator forms. Screenshots and JSON are in `.agent-runs/parallel-B-b2/`.

## Limits / blocker

- A's stable B runtime is still `samudrasense-api:014-a1` at schema `014`. Migration `015` and `/api/v1/admin/*`
  are not present, so the Administrator settings/account forms were exercised only against fixtures. No live
  2015-era admin GET/PUT/POST, live-role denial or account-disable result is claimed.
- The 014 browser pass does establish the signed-in Analyst state, source-health rendering and a keyboard-only
  login against an actual API. It does not establish backend authorization; use A2's own 28 focused checks for
  that.
- First-run administration remains the CLI script `scripts/create_local_admin.py`; A2 exposes no UI endpoint for
  it, so the client does not invent one.
- The login throttle is bounded by design; no repeated credential attempts were made.

This slice is not marked fully COMPLETED because its stated browser/API criterion needs A2's runtime.

## Restart instruction

Read this file, `tasks/parallel/B-status.md` and `tasks/parallel/A-status.md`/`A-A2.md`. When A publishes a
stable snapshot at migration `015` or later on `8002` (or a fresh start recipe), start it with a disposable
database, create an Administrator locally, and browser-test: settings read/save, user creation with each role,
enable/disable, self-disable block, Viewer/Analyst/Approver denial text and expired/disabled session handling.
Then update this record and `B-status.md`. B3 still requires A3's `016` runtime for its browser gate.
