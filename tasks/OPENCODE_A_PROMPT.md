# Prompt for OpenCode session A

You are User A's backend/integration implementer for SamudraSense. The user authorizes successive phases through the existing full product scope. Read `tasks/PARALLEL_EXECUTION.md` and follow its ownership, execution loop, failure budget and coordination rules exactly. Then read AGENTS, PROGRESS and current. Do not stop after one passing phase: complete its record and continue to the next eligible phase. Stop on an unresolved acceptance failure, missing human decision/access, partner-owned defect or exhausted context budget; return the exact restart instruction. Do not launch another agent or session yourself.

Own `apps/api/**`, `infra/**`, `docs/contracts/**`, `docs/DATA_MANIFEST.md`, `docs/evaluation/**`, and `tasks/parallel/A-*`. Never edit frontend/B files or Codex master state. The existing dirty A-004F code and sanitized examples are the baseline, not unfinished work to reimplement. Keep the current stack and compatible contracts. No external sends, purchases, deployment, Git writes or secret disclosure.

Create `tasks/parallel/A-status.md` first. For each phase write a small A-owned brief/result, then implement and verify it. Contract readiness must include exact payloads, errors, auth/CSRF, data modes, original timestamps, migration head, focused results and a stable runtime identifier. Publish the completion marker last. Read B-status for concrete integration defects at boundaries.

## A0 — stable baseline for simultaneous work

Confirm local frontend includes `dde0c11` and working backend includes A-004F/migration 014. Capture the dirty baseline; reuse its recorded passing evidence. Prepare a stable local backend snapshot at 014 for B's isolated browser database on port 8002. Record how B starts it, migration command, non-secret health check, approved local account setup and schema/contract identifier. Your own development/test stack uses separate resources/port 8001. Do not restart or migrate the shared stack. Acceptance: the B snapshot starts and reports its schema/health against disposable data, with no credentials in logs or docs. If prerequisites are missing, record the exact blocker; do not silently bind to the shared DB.

## A1 — historical alerts and truthful status (A-003 follow-up)

Trace `alert_records.sync_alerts`, the legacy generator, shared fleet window selection, assessment identities and source health. Add compatible explicit historical bounds to stored-alert sync using the existing window validation. Preserve default behavior, deduplication, resolved states and lifecycle history; do not rewrite dates. Use source-derived data modes rather than configured-provider guesses. Replace unverified offence wording with screening language. Determine whether map/board/report evidence agrees and fix shared backend discrepancies rather than a UI workaround.

Acceptance: focused tests for exact-window selection, invalid/partial bounds, empty/expired rolling window, repeated sync without duplicates/reopening, late records and source-mode truth; disposable persistence test when SQL changes. Publish the exact request/response contract for B1, including whether the stored list is window-filtered or intentionally global. A window-scoped sync must not silently relabel the global list. No empty-provider result is a passing real-data gate.

## A2 — finish access control and identity/settings (A-002, F01)

Inventory actual mounted routes and existing protection. Finish legacy ingest, chat/tool, read, job, report/export and settings authorization using existing dependencies. Enforce Viewer/Analyst/Approver/Admin separation, CSRF on cookie-authenticated mutations, disabled-account/session expiry/revocation and bounded login attempts. Complete missing first-run/admin user and deployment-setting contracts required by F01; secrets never appear in responses. Keep provider/DB actions behind successful authentication. Do not silently change a role contract B already consumes; publish compatible changes first.

Acceptance: route/role matrix with explicit public exceptions; parametrized anonymous, insufficient-role and missing-CSRF tests plus allowed requests, expiry/disabled-account checks and no side-effect assertions. Existing login/report tests must still pass. Mark only verified routes protected; do not announce whole-API security before the complete inventory passes. Exposure of historical credentials requires owner-managed rotation; do not claim it completed.

## A3 — complete reviewed report/export guarantees (A-004/A-012, F09)

Reuse reports/cases; add a protected single-report retrieval/export path if missing so B need not extract text from a bounded list. Preserve canonical bytes/number representation and provide an independently checkable manifest. Complete required deterministic human-readable PDF, evidence references, draft revision/approval concurrency and source validation. Tampered, stale or unreferenced facts must block approval/export; existing signed revisions remain unchanged. Keep hashes described as checksums, with their actual threat model. No LLM dependency.

Acceptance: canonical byte/hash round trip including `59.0`, export after list pagination, tamper/missing-reference/stale-review rejection, role checks, duplicate/concurrent revision behavior and a readable PDF tied to the same report. Use disposable DB tests for changed persistence. Publish fixtures and contract; B owns browser completion. Keep optional delivery for A9.

## A4 — ingestion and source/job operations (A-006/A-013, F02/F12)

Finish bounded CSV/JSON/AIS/GFW ingestion using existing adapters, Redis pacing and Celery. Validate geography, UTC, AIS sentinels and size; preserve quality/provenance, quarantine invalid records, deduplicate reconnect/replay and persist bounded checkpoints. Add incremental job progress, cancellation, bounded retries/timeouts and source states using existing tables where possible. Complete metadata/retention-rights handling and source status distinctions. Do not repeat exhausted Gulf of Mannar AISStream probes or enable retention without rights.

Acceptance: same input twice and worker interruption/restart produce no duplicate observations/alerts, invalid records have reasons, rate-limit/error recovery is bounded, cancellation works and missing input is unknown. Exercise actual tasks against disposable DB/Redis. One permitted real sample is required for the real-ingestion gate; if absent, stop with the precise access/rights requirement. No paid provider or unrestricted download.

## A5 — boundaries and SAR/unknown-object evidence (A-007/A-009, F04/F05)

Verify licensed regional boundary/rule metadata and a permitted point SAR sample before acquisition. Preserve version, scene ID, acquisition/publication/ingestion times and confidence meaning. Keep presence, buffers and restrictions separate. Reuse the baseline association implementation, extend candidate/ambiguous/unmatched/insufficient states and allow unidentified detection cases without fabricated MMSIs. Publish additive object/case contracts before B5 begins. Do not convert heatmap aggregates into points or silently reinterpret the existing vessel-only case schema.

Acceptance: real sample provenance/rights; invalid geometry, edge/buffer/rule-unknown, duplicate scene, multiple candidates, missing AIS and time/distance tests; disposable migration and source-to-case round trip; association errors/unknowns recorded against a permitted reference. No full xView3, optional model training or guessed rights. Missing point access stops this phase.

## A6 — reviewer state, notes, weather and encounters (A-008, F03/F06/F07)

Finish versioned New/Watch/In review/Closed behavior, assignee, authored notes, resolution/reopen reasons and computed clearing scenarios using the existing lifecycle model. Preserve score separately from review priority. Add bounded time-aligned encounter queries (default 48h, at most two hops, node/edge caps) with distance/duration/coverage and source references. Reuse event-time weather snapshots; missing weather never clears an alert. No long encounter duration inferred across sparse gaps.

Acceptance: concurrency/actor/history tests, time-overlap/sparse-gap/cap tests, late corrections preserve earlier evidence, storms and absent weather cannot auto-close, graph edges trace to inputs. Publish real fixtures without conflating synthetic evaluation with field accuracy.

## A7 — environmental inputs and evaluated baselines (A-009/A-010, F08)

Acquire only permitted bounded SST/chlorophyll/effort inputs with source dates, availability times, quality masks, native resolution and units. Implement persistence/recent-effort and simple seasonal baselines, rolling blocked evaluation, factor explanations and budgeted existing-scene recommendations with 20% non-hotspot evaluation coverage. Compare against persistence, recent effort and uniform scanning. Do not infer illegality or satellite tasking.

Acceptance: reproducible manifest/transforms, no future-data leakage, missing/cloud mask tests, recorded held-out baseline metrics and budget constraints. Insufficient real history is a blocked forecast-evaluation gate; a descriptive layer does not satisfy it. No advanced ranker before required baseline completion.

## A8 — real GNOME scenario service (A-011, F10)

Use an isolated supported PyGNOME runtime and reference check before app integration. Require valid wind/current forcing and explicit input/default/version/seed metadata. Use existing jobs for bounded AOI, particles, duration, output size, cancellation and 6/12/24h outputs plus coastline/protected-area impact. Unknown forcing must not become zero flow. Include georeferenced manual pollution observations; unvalidated automated detection remains disabled.

Acceptance: constant/no-flow fixtures, reference reproducibility, valid real forcing, failure/cancel/resource-limit tests and contract usable by B8. Keep synthetic forcing confined to labelled tests/training. Missing runtime/forcing stops this phase; no fabricated trajectory replacement.

## A9 — offline operations, retention and optional delivery (A-012/A-013, F09/F11/F12)

Finish bounded cache validity, one scheduler, offline/production profiles and idempotent reconnect. Provide offline source/hash verification, backup/restore and explicit retention safeguards. Add approved-version/recipient delivery outbox only against a local mail sink, with stable idempotency, bounded retries and visible submission state. Approval of the exact revision/recipient set is required; no real external sending. Coordinate assets with B9 and keep secret configuration server-side.

Acceptance: networking-disabled cached case/approval/export path, expiry/reconnect tests, worker restart and duplicate-send tests, retention cannot delete referenced evidence, separate-DB restore verifies sample case hashes. Missing licensed assets is an incomplete joint offline gate even if backend tests pass.

## A10 — full release verification and handoff (P5/F14)

Only after prior required gates and corresponding B integrations pass: run the relevant isolated integration suite, clean build/install, measured resource/load checks, worker recovery, separate-DB backup restore and upgrade/rollback checks. Check release CORS/ports/default credentials/reload settings. Record exact hardware/sample sizes, licenses, reproducible installation commands and outstanding risks in A-owned docs/status. Require owner-confirmed credential rotation before release-ready status. Match every F01–F14 backend criterion; any missing required criterion blocks full v1. Prepare handoff facts for Codex's README/release updates; do not deploy, tag or push.

## CLI launch (from repository root, in A terminal)

```powershell
opencode run --agent build --model 'opencode/deepseek-v4.1-flash-free#high' --file tasks/OPENCODE_A_PROMPT.md 'Execute the A lane and shared parallel plan. Continue through eligible phases until a documented stop condition. Maintain only A-owned records.'
```
