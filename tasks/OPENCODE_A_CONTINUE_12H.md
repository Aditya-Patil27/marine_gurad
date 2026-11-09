# OpenCode product-demo implementation sprint

You are the frontend/product implementer for SamudraSense. Work from
`C:\Users\Adish\HelloCode\marine_gurad` and make the product concept visible
to a hackathon judge as quickly as possible. Do not pace work to fill a time
box. Finish each feature end to end, then immediately start the next one.

This prompt supersedes the earlier stabilization-first continuation. The goal
is a coherent product demo, not maximum backend coverage. Reuse the substantial
working backend and existing React design. Do not redesign the stack.

## Required operating rules

Read `AGENTS.md`, `tasks/current.md`, `tasks/parallel/A-A2.md`,
`tasks/parallel/A-A3.md`, `tasks/parallel/B-status.md` and the relevant API
contracts. Use CodeGraph once to inspect the named components before editing.
Follow the requested implement workflow in each feature slice:

1. Write focused failing tests for the visible behavior.
2. Implement the smallest complete feature using existing components and dependencies.
3. Make the focused tests pass and remove no existing behavior.
4. Continue immediately. Run the production build and one browser demo pass only after the complete bundle is implemented.

No TODOs, disabled teaser buttons, fake loading states or “coming soon” pages.
Do not stop midway through a feature. If one API-backed feature is blocked,
record the exact blocker and proceed to the next independent UI feature.

Own only `apps/web/**`, `docs/demo/**`, and `tasks/parallel/B-*`. Do not edit
the API, migrations, infrastructure, credentials, datasets, master planning
documents or Git state. Preserve all dirty/untracked work and the completed
B0/B1 journeys. Do not add a dependency unless the installed stack genuinely
cannot do the job.

## Product truth that must remain visible

- Historical/replay/synthetic/live/cached modes must never be conflated.
- A GFW event is an inferred historical event point, not a vessel track or proof of fishing/illegality.
- Missing AIS is unknown coverage, not proof that a vessel deliberately went dark.
- SHA-256 is an integrity checksum, not a digital signature.
- The spill feature below is an illustrative training scenario, not GNOME, calibrated probability or operational forecasting.
- Never invent API success, provider coverage, evidence, users or source dates.

## Existing backend capabilities to expose

- A2: `/api/v1/admin/settings`, `/api/v1/admin/users`, user activation and `/api/v1/sources/health` at migration 015.
- A3: `/api/v1/reports/{id}`, `/manifest`, `/export.pdf`, approval with optional `expected_sha256` at migration 016.
- Existing: vessels/map, alerts and lifecycle, cases, historical GFW events, prepared Copernicus regional SST, weather context and replay-window control.

If the frozen B backend on `:8002` is still schema 014, use the live isolated A
backend on `:8001` after confirming it reports migration 016. Do not migrate or
seed the shared `:8000` stack. Frontend work and fixture tests must not wait for
the frozen image.

## Feature 1 — product overview and guided judge journey

Create a polished `/overview` page and make it the default landing route. Keep
the map available from the rail. The overview must explain and link the actual
workflow in four judge-readable steps:

1. Detect — regional map, replay/live mode and sourced events.
2. Investigate — alerts, evidence factors and environmental context.
3. Act — cases, human review and traceable reports.
4. Prepare — source readiness, settings and spill planning scenarios.

Use concise cards with meaningful current counts/status only when returned by
existing endpoints; otherwise show “not loaded” or “unavailable,” never zero.
Include a prominent “Start investigation” link to the map and a “Demo path”
that tells the presenter exactly which screens to open next. Add the Overview
rail item without making the rail overflow at 768px height.

Acceptance: keyboard-accessible navigation, loading/error/empty states, links
to real routes, no placeholder copy, focused tests for the four stages and
unknown-count handling.

## Feature 2 — operations and settings instead of the Settings placeholder

Replace `NotBuiltYet` on `/settings` with one coherent Operations page.

- Every signed-in Viewer can see source-health cards from `/api/v1/sources/health`: Local replay, Copernicus SST, GFW, AISStream and Open-Meteo, with status, mode/availability, last-run metadata and limitations.
- Administrators additionally see and edit deployment settings and can list, create and activate/deactivate local users through A2. Do not expose password values after submission and do not allow self-deactivation in the UI.
- Non-admin users see a short truthful permission explanation, not a broken form. Handle 401/403, validation errors, conflicts and stale requests.
- Use the server-returned settings; do not embed keys or pretend “configured” means available/covered.

Acceptance: focused tests for Viewer, Administrator, forbidden, source-empty,
validation and account activation states. Real API browser check for source
health plus one admin settings read if an isolated admin session is available.

## Feature 3 — complete report review and export experience

Upgrade the existing Reports page using A3 without removing the current JSON/
text export behavior.

- Select one report and load `/reports/{id}` rather than extracting it from the bounded list.
- Show draft/approved state, reviewer identity/time, evidence basis, source references, limitations, checksum and integrity status in a readable review panel. Never render absent score as zero.
- Approver action sends `reviewed: true` with the displayed `expected_sha256`; a 409 must keep the draft and offer reload.
- Provide clear “Download reviewed PDF” and “Download verification manifest” actions. PDF remains unavailable until approval. Download response bytes without JSON transformation. Manifest copy/download must retain canonical JSON and explain the checksum threat model.
- Event-only and assessment-backed reports must both render without assuming fields belonging to the other basis.

Acceptance: focused tests for draft, approved PDF, event-only, assessment,
tamper/integrity failure, 401/403 and stale approval. Browser demo must load an
actual isolated report and exercise every available action without changing a
previously approved revision.

## Feature 4 — interactive spill-planning concept instead of the placeholder

Replace `/spills` with a complete client-side **Illustrative spill training
scenario**. This is intentionally a labelled concept demo until A8 delivers a
verified GNOME backend.

- Inputs: spill longitude/latitude within the Gulf of Mannar demo bounds, scenario start, wind direction, wind speed and a named material.
- On “Run illustrative scenario,” calculate a deterministic, bounded trajectory for 0/6/12/24 hours using a small pure function and display it in an accessible SVG plan view plus a time-step selector and summary cards.
- Clearly show all inputs, deterministic method, “synthetic training mode,” and the statement that output is not GNOME, probability, emergency guidance or a calibrated forecast. Do not call the result real environmental data.
- If the prepared SST endpoint is available, show it separately as dated regional context; failure must leave it unknown and must not alter the trajectory.
- Add one “Create investigation note” action that downloads a local JSON scenario summary containing inputs, outputs, mode and limitations. It must not create a backend case or claim dispatch.

Use existing CSS/lucide patterns and browser APIs; no map SDK or modelling
dependency is needed. Keep coordinates WGS84 longitude/latitude and timestamps
explicit UTC.

Acceptance: unit tests first for deterministic output, bounds, 6/12/24-hour
steps and JSON summary; component tests for validation, keyboard operation,
unknown SST and prominent synthetic/limitations labels. Browser pass runs one
scenario and saves a screenshot suitable for the demo-video plan.

## Feature 5 — presentation polish and demo-video handoff

After Features 1–4 pass focused tests:

- Remove every remaining visible “not built yet” route from release navigation.
- Ensure 1366×768 has no document-level horizontal overflow and all primary actions have visible focus and meaningful loading/error states.
- Run affected frontend tests, then the production build once.
- Run one browser journey: Overview → Map → Alert/Evidence → Case/Report → PDF or manifest → Operations → Spill scenario. Capture screenshots only at judge-visible milestones.
- Write `docs/demo/PRODUCT_DEMO_RUNBOOK.md`: a 3–4 minute narration with exact clicks, what is real/replay/synthetic on each screen, and a fallback route if a provider is unavailable. Do not claim features the browser pass did not reach.
- Update `tasks/parallel/B-status.md` and a new B-owned implementation record with changed files, exact checks/results, screenshots and honest limits.

## Finish condition

Finish the complete feature bundle as quickly as correctness allows. Return:

- visible features completed;
- files changed;
- focused tests and production build result;
- browser journey result and screenshot locations;
- exact remaining blocker, if any;
- the shortest recommended demo-video path.

Do not spend time on broad backend stabilization, clean-install benchmarking,
release-load testing, new ingestion infrastructure, external acquisition or a
full-suite rerun unrelated to changed frontend behavior.

## Launch with DeepSeek default effort

```powershell
opencode run --agent build --model 'opencode/deepseek-v4.1-flash-free' --file tasks/OPENCODE_A_CONTINUE_12H.md 'Implement this judge-facing product-demo bundle end to end. Use TDD for each feature, reuse existing APIs, continue immediately after each completed slice, and run the build/browser journey once at the end.'
```
