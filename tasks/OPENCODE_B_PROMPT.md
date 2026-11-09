# Prompt for OpenCode session B

You are User B's frontend/browser implementer for SamudraSense. The user authorizes successive phases through the existing full product scope. Read `tasks/PARALLEL_EXECUTION.md` and follow its ownership, execution loop, failure budget and coordination rules exactly. Then read AGENTS, PROGRESS and current. Continue after each passing phase without requesting another assignment. Stop on an unresolved acceptance failure, missing human decision/access, partner-owned defect or exhausted context budget; return the precise restart instruction. Do not launch another agent or session yourself.

Own `apps/web/**`, relevant `docs/design/**`, `docs/demo/**`, `tasks/B-005F.md` and `tasks/parallel/B-*`. Never edit API, migrations, contracts, infrastructure, datasets, credentials or Codex master state. The local frontend already includes B's `dde0c11`; preserve its tests, export precision fix and existing design. Keep the installed React/Vite stack and existing components. No Git writes, deployment, paid access or external messages.

Create `tasks/parallel/B-status.md` first. For each phase write a small B-owned brief/result. Read `tasks/parallel/A-status.md` at phase boundaries for a completed contract and stable backend runtime. Use B's disposable database/backend snapshot on 8002 and Vite on 5174 after checking availability. A's shared/development database is not browser-test data. Fixtures can validate controls while a contract is stable, but only actual API/browser evidence completes integration. Do not invent backend fields or substitute mock results for missing live/data gates.

## B0 — finish B-005F and the reviewed event journey

Implement `tasks/B-005F.md` completely using A-004F's existing contract. Reuse the selected GFW event notice, API helpers and report/case pages. For vessel 404 plus a selected event, offer an explicit event-only review action. Report creation sends `event_only: true` and exact event/page fields, with no assessment/window/weather fields; case creation sends `{report_id, title}` and already creates revision 1. Preserve the report ID on a known case failure, prevent double clicks and handle ambiguous network outcomes without blindly replaying a write. Keep the old assessment path intact.

Acceptance: focused B-005F and existing B-005 journey tests plus production build; actual historical GFW event → missing AIS → report → case revision 1 → stored evidence and export. Also exercise authenticated Approver review/sign-off and verify the exported hash outside the UI using server-preserved bytes. Display unavailable AIS/assessment, real source dates and all event limitations; no default zero score. Use a disposable authorized local account; never print credentials. A missing provider/browser/runtime prevents completion of the affected criterion. Record evidence in the task result and B-status.

## B1 — replay-aware alerts and consistent evidence

Requires A1's completed contract for historical alert sync/status. Connect existing stored alert/triage screens using identical selected bounds; keep any intentionally global stored-history list explicitly labelled. Keep map/detail/report modes and evidence identities consistent. Remove offence-implying screen labels. Preserve lifecycle/version conflicts, recorded reasons and clear missing-source states.

Acceptance: exact bounds and response identity tests, empty/late-response/409 cases, repeated sync without duplicated UI rows or reopening resolved alerts, actual browser replay sync on the stable A1 backend. A backend score/window mismatch is reported to A and blocks the affected phase, not hidden by frontend recomputation.

## B2 — roles, settings and accessibility foundation

The keyboard/viewport/loading/error/empty audit of existing pages can proceed while A1/A2 is pending; record that as a bounded independent slice. For account/admin/settings implementation, require A2's published contract. Reuse local login/session UI; render Viewer/Analyst/Approver/Admin abilities correctly, expired/disabled sessions, permission errors and first-run/admin setup if the API exposes it. Never put keys or provider secrets in the client. Preserve light/navy/periwinkle design and accessible focus/state labels.

Acceptance: role/error interactions against fixtures and API, keyboard completion of the main workflow, 1366×768/1920×1080 and tablet checks, no essential operation dependent only on color or hover. Hidden controls do not establish backend authorization; use A's denial results separately.

## B3 — complete case/report review and exports

Requires A3. Consume the protected single-report/export contract and preserve canonical bytes. Add required deterministic PDF/manifest downloads, evidence/source validation, draft revisions, reviewer sign-off and concurrency recovery through existing pages. Editing an approved report creates a new draft revision. Keep delivery status distinct from approval. Cover vessel and event-only cases; later unknown-object cases extend the same components after A5.

Acceptance: actual draft → review → approved export → new revision flow with role separation; missing references, tamper, stale version and unavailable report states; saved PDF readable and JSON/hash manifest verifies independently. No inference of authenticity from the checksum alone. Do not mark delivery complete here.

## B4 — source management and jobs

Requires A4. Connect existing source health/run APIs and new frozen job contracts: observed time, age, import success, errors, quota if reported, rights status, queue/progress/cancellation and bounded retry. Keep configured, unavailable, empty, stale, historical and live states separate. Add supported AOI/time/name/MMSI filters and source settings using server validation. Never display secrets or imply regional coverage from a working API key.

Acceptance: loading/empty/error/permission/stale states; browser source failure/recovery, job progress/cancel and duplicate-action prevention; actual returned data preserves provenance. No periodic aggressive polling or independent retry scheduler in the browser.

## B5 — boundary/SAR layers and unidentified cases

Requires A5's permitted fixtures and object/case contract. Add boundary version/rule/source panel and distinct proximity/restriction labels. Show SAR point/footprint, acquisition time, match candidates, ambiguity and insufficient coverage; real crop only if licensed/available. Provide unidentified-object detail and case creation without an MMSI through the new contract. Use existing map and case components.

Acceptance: actual permitted SAR sample → ambiguous/unmatched view → unidentified case/report, traceable references, invalid/missing image fallback and no fabricated vessel association. Label sample polygons and unverified restrictions. Tests cover multi-candidate, missing AIS, absent crop and non-vessel routes.

## B6 — linked evidence and reviewer decisions

Requires A6. Connect timeline, map/time selection, speed/position plots, weather/coverage, authored notes and bounded encounter graph. Each edge exposes its source records, time overlap, duration/distance and coverage. Wire assignee/Watch/In review/Closed/reopen with versioned notes/reasons. Display model estimates separately from observations and analyst findings; weather suggestions do not alter the behavioral score.

Acceptance: event click selects the right time/location; graph/filters respect server caps; keyboard accessible alternatives; sparse/unknown coverage and missing weather remain visible; real API reviewer changes survive reload and preserve actor/history; concurrent edits show actionable conflict.

## B7 — ocean conditions and baseline/scan results

Requires A7. Build the existing planned Ocean page against observed versus forecast outputs, source units/resolution/age, missing cells, factors and uncertainty. Display actual baseline comparisons and scan-budget controls; preserve descriptive-only/blocked evaluation states where reported. No illegal-fishing prediction or climate-change claim.

Acceptance: API-backed historical/forecast dates, missing/cloud masks and unit tests, actual evaluated baseline metrics rendered, scan-budget action respects constraints, export includes attribution. A fixture-only forecast page is not a completed real-data gate.

## B8 — spill scenario workflow

Requires A8's verified GNOME runtime/contract. Add georeferenced observation/input form, explicit forcing availability, parameter validation, queued/running/failed/complete/cancelled states and 6/12/24-hour map outputs/scrubber with affected coast/areas. Clearly label a planning scenario and distinguish ensemble extent from calibrated probability. Do not offer a run with unavailable required forcing or expose unvalidated oil detection.

Acceptance: browser reference scenario with recorded engine/input/seed metadata, validation/failure/cancellation paths and accessible time-step inspection. Real forcing is required for the real scenario gate; synthetic fixtures remain labelled tests.

## B9 — offline assets and delivery controls

Requires A9 and permitted offline regional map/assets. Package local map style/glyphs/sprites/fonts with attribution and rights; remove hidden remote dependencies from the offline path. Support browsing cached evidence, notes, draft/approval and export with visible cache age/validity and idempotent reconnect. Wire administrator-approved recipient selection and exact-version delivery consent only against A's local mail sink; show queued/submitted/failed distinctly from received/read.

Acceptance: actual networking-disabled prepared installation completes the case workflow; browser network audit proves assets local; reconnect does not duplicate changes; local sink delivery respects exact version/recipients and visible failure. No real email, provider purchase or unlicensed tile bundle. Missing rights stops the affected phase.

## B10 — release browser evidence and handover

After all prior integrations: run the release browser matrix for real/replay/synthetic/offline modes, roles, errors, stale states, viewports and keyboard. Exercise at least the suspicious-evidence, benign weather/sparse-coverage and spill stories without invented results. Have two human reviewers perform the documented tasks; record timings/mistakes and fixes. Human review cannot be supplied by an automated agent. Verify A's clean-install guide, user guide, provenance walkthrough and honest demo/video; remove stale claims and nonfunctional release navigation while retaining missing features as incomplete requirements in the record.

Acceptance: each F01–F14 user-facing criterion linked to actual evidence and A's backend result. Any missing required feature/reviewer/install criterion blocks full v1. Produce B-owned final handoff and proposed master-doc corrections for Codex; do not publish, tag, merge or send externally.

## CLI launch (from repository root, in B terminal)

```powershell
opencode run --agent build --model 'opencode/deepseek-v4.1-flash-free#high' --file tasks/OPENCODE_B_PROMPT.md 'Execute the B lane and shared parallel plan. Continue through eligible phases until a documented stop condition. Maintain only B-owned records.'
```
