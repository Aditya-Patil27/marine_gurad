# B2 brief — independent accessibility / viewport / state audit

Status: COMPLETED (bounded independent slice only; account/admin/settings work waits for A2).

Allowed writes: `apps/web/**`, `tasks/parallel/B-*.md`, `tasks/parallel/B-status.md`.

Scope: existing pages only — Map, Alerts, Vessels, Reports, Cases, Settings placeholder. Check loading/empty/
error visibility, keyboard operation of navigation and login, visible focus, non-colour state labels, and
1366×768 / 1920×1080 / tablet layouts. No dependency, no visual redesign, no backend contract assumption.
Out of scope until A2: role/account/settings implementation, permission-denial rendering against the API,
first-run/admin setup.

Acceptance for this slice: screenshots and a machine-readable audit at the three viewports; a keyboard-only
login and navigation pass; concrete defects found are fixed with focused tests or recorded as blocked. This
does not complete B2.

## Result - 8 November 2026

The Overview, Map, Alerts, Vessels, Reports, Cases, Spills and Operations (route `/settings`) pages were
exercised at 1366x768, 1920x1080 and 768x1024 against B's isolated runtime, signed out and then signed in as
an Analyst. None produced document-level horizontal overflow. Loading/empty/authentication-error states
remained visible, and no page exception was captured. The audit's single unnamed-control count on Map is a
harness false positive: the vessel search is named by its enclosing label (`Search vessels`) and its existing
role/name test passes.

Keyboard evidence covered the complete main rail tab order, visible 2 px focus on all eight sampled controls,
Enter activation of Reports, and a keyboard-only analyst login. The login was revalidated on 9 November as
`b_analyst` against A's 014 runtime; the older screenshot is kept only as a visual capture. States use text
labels in addition to colour; the inspected tablet Map, Alerts and Operations screens retained visible controls
and readable state/error text.

One defect was demonstrated: Map had no page heading. `apps/web/src/pages/MapPage.jsx` now renders an
`sr-only` `h1` (`Vessel map`); the focused assertion is in `apps/web/tests/MapPage.test.jsx`. The heading is
visually hidden, so the viewport screenshots and overflow audit remain representative. Account/admin/settings,
role-specific permission states and API denial rendering remain outside this independent slice and require A2.

### Evidence

- Machine-readable audit and screenshots: `.agent-runs/parallel-B-b2/a11y-audit.json` (signed in) and
  `a11y-audit-signed-out.json` (signed out), with adjacent PNG files.
- Audit summary: zero overflowing pages at all three viewports in both states; all eight pages had one `h1`;
  8/8 sampled controls had visible focus; keyboard navigation opened `/reports`; keyboard-only sign-in as
  `b_analyst` passed; zero captured page exceptions.
- `npx vitest run tests/Shell.test.jsx tests/MapPage.test.jsx tests/Cases.test.jsx tests/NotBuiltYet.test.jsx`
  passed 4 files and 119 tests after the Map heading assertion was added.
- An initial npm wrapper invocation rejected an unsupported forwarded `--run` flag before starting tests; the
  direct Vitest command above is the recorded check.

Limits: the signed-in pass used an Analyst account on A's 014 runtime. Administrator forms were not browser
tested because no A2 (015) runtime has been published for B; their fixture coverage is in
`tasks/parallel/B2-accounts-settings.md`. The signed-out pass correctly displayed authentication errors. This
does not establish backend authorization, role correctness or completion of the account/admin/settings slice.
The older keyboard-login screenshot predates the Analyst revalidation.
Repeated authentication attempts stopped after the successful keyboard-login capture because the backend
throttle is bounded by design.
