# B3 — product-demo surface and review/export UI

Status: SUPERSEDED BY `B-v1.md`. Owner: B only.

## Product-facing result

- `/overview` is the default landing page and presents the actual Detect →
  Investigate → Act → Prepare journey with loaded-or-unknown operational counts.
- `/settings` is now Operations: source readiness for signed-in users plus
  administrator-only deployment settings and local-account controls.
- Reports now use the protected detail/manifest/PDF routes, show evidence basis
  and source limitations, and send the displayed checksum as the approval guard.
- This record described the earlier product-demo bundle. The current spill
  screen uses the backend capability/job contract and disables submission when
  PyGNOME/forcing are unavailable; it does not simulate a trajectory.
- The rail exposes the operational v1 screens; no release-navigation route
  leads to `NotBuiltYet`.

## Changed B-owned paths

- `apps/web/src/App.jsx`, `components/Shell.jsx`, `lib/api.js`, `lib/spill.js`
- `apps/web/src/pages/Overview.jsx`, `Operations.jsx`, `SpillPage.jsx`, `Cases.jsx`
- `apps/web/tests/Overview.test.jsx`, `Operations.test.jsx`,
  `ReportsReview.test.jsx`, `SpillPage.test.jsx`, `spill.test.js`
- `docs/demo/PRODUCT_DEMO_RUNBOOK.md`

## Verification — 9 November 2026

```text
npm test -- tests/Overview.test.jsx tests/Operations.test.jsx \
  tests/ReportsReview.test.jsx tests/spill.test.js tests/SpillPage.test.jsx \
  tests/Shell.test.jsx tests/MapPage.test.jsx tests/Cases.test.jsx \
  tests/B005FEventOnly.test.jsx tests/Lifecycle.test.jsx
```

Result: **10 files, 158 tests passed**.

`npm run build` passed: 1,988 modules transformed.

## Supersession note

See `tasks/parallel/B-v1.md` for the consolidated frontend implementation and
combined verification status. This historical record must not be used to claim
a synthetic spill forecast.
