# B v1 — operational product frontend

Owner: B only. Status: **COMPLETED — 9 November 2026**.

## Delivered

- Professional operational Overview driven by real API summaries; no presenter,
  walkthrough or demo-plan language in the active application.
- Ocean conditions and bounded scan planning, with dated observations and an
  explicit descriptive-only baseline.
- SAR intake, explicit ambiguous/unmatched identity, cited boundary context and
  unidentified-object case creation.
- Alert reviewer/assignee/reason/note/clear workflow; evidence weather,
  coverage and encounter-network context.
- Operations source jobs, cancellation and cache/worker/storage/backup state;
  report exact-hash delivery state.
- Spill capability and job screen. It makes no client-side trajectory fallback
  and disables submission when the backend reports PyGNOME/forcing unavailable.

## Changed B-owned paths

`apps/web/src/{App.jsx,components/Shell.jsx,lib/api.js,pages/{Overview,OceanPage,DetectionsPage,SpillPage,Operations,Cases}.jsx}`
and focused `apps/web/tests/*` coverage for those surfaces.

## Verification handoff

The isolated backend migrated through 017 and exposed the v1 OpenAPI surface.
Frontend verification passed: **17 test files / 221 tests** and the production
build completed with **1,989 modules transformed**. Two stale generic-status
test assertions were made specific after the new accessible status regions were
added; application behaviour did not change.

One recorded browser journey against an isolated 017 database remains a demo
production task, not an implementation blocker. Do not claim provider
connectivity, a spill forecast or delivery to a real recipient.

## External limits surfaced in the UI

The UI is complete without an external registration. Real GNOME execution
needs PyGNOME plus compatible forcing; real point SAR, verified boundaries/rules
and historical effort/chlorophyll/current data remain backend data gates.
