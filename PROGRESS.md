# Current execution state

Updated 7 November 2026. Branch `ap`; commit count is not completion evidence.

## Product and completion

Goal: a Gulf of Mannar analyst moves from source-labelled activity through explainable evidence to a reviewed case and traceable export. Full v1 requires F01?F14 in [the product specification](docs/FINAL_PRODUCT_PLAN.md); a working endpoint does not complete a feature.

The prototype has a substantial backend foundation and a partial browser journey. It is not feature-complete or release-ready. P1/P2 gates remain incomplete; P3 is partial; P4/P5 remain pending. No measured percentage or validated accuracy is available. See [judge review](docs/HACKATHON_JUDGE_REVIEW.md) and [execution order](PLAN.md).

## Delivered, with bounded evidence

| Area | Implemented | Remaining integration |
|---|---|---|
| Identity | Local cookie sessions, Argon2id, Analyst/Approver separation, CSRF on protected mutations; browser login previously user-confirmed | Remaining legacy route protection; durable clean image build |
| Evidence | Explainable vessel risk, persisted assessments, provenance/modes, event-time weather snapshots | Real observation-to-assessment/case linkage; weather snapshot UI |
| Cases/reports | Hashed snapshots, session-derived sign-off, case/revision links, versioned close/reopen and audit events | UI status actions; transactional initial creation; complete source-bound export/delivery |
| Alerts/triage | Stable legacy IDs, stored lifecycle/events, authenticated read-only assessment triage | Alert screen still reads vessel scores; no stored-lifecycle or triage API client |
| Sources | Historical GFW event layer/export, one historical Copernicus SST cell, health/run metadata, shared Redis pacing | Incremental jobs, useful permitted AIS sample, coverage, point SAR |
| Browser | Map, source labels, local sign-in, vessel evidence, reports and case/revision screen | End-to-end judged journey, source/status operations, placeholder routes |

A-001, A-002A/B, A-003B/D/E/F/G, A-004A/B/C/D, A-005, A-006A/B/C/D, A-008A and A-H04 have bounded completion evidence. See [task records](tasks/completed/) and [backlog](tasks/backlog.md), rather than repeating test transcripts here. Completion of those slices does not complete their parent product features.

A-004E is also complete with supplied focused evidence. It reuses the existing GFW canonical export and report/case integrity path to bind one re-fetched historical event, with optional independently dated SST context, into a hashed report snapshot. No migration was needed. The browser caller and an actual real-event reviewed journey remain incomplete.

## Current observations versus historical checks

- GitHub checked directly on 7 November: `b/sprint` remains at `abc1d43a2911f440172e601009ea93fcc695fa6a` (latest commit dated 4 November, 14:30:53 IST, "Record API key status"). This matches the previously known/local remote-tracking tip; no new branch-tip work is visible. No merge or checkout was performed.
- Observed during the 7 November context review: all five Docker services running; PostGIS and Redis healthy; frontend HTTP 200. `alembic current` reports `012 (head)`.
- Source inspection: `AlertsPage` calls `vesselsApi.list(168)`; web client has no stored-alert, triage, case-close/reopen or source-health calls. GFW event display remains separate from replay cases.
- Historical evidence: browser login/case creation was user-confirmed on 6 November; focused backend checks and frontend builds are recorded per task. They were not rerun for this documentation review.
- A-005B delivers bounded historical selection and scoring across vessel, assessment sync and report calls. The browser still uses the rolling 168-hour window, which expires before judging. B must propagate the selected bounds to fleet list/detail, sync and reports. No timestamps were rewritten.
- Last recorded API image rebuild failed on package-download timeout; a durable rebuild remains unverified. Container uptime does not establish clean-install reproducibility.

## Data/access limits

GFW events are historical locations, not vessel tracks. SST is a historical single-cell sample, not a forecast. Existing replay tracks have `unknown` provenance; newly seeded demo data is `synthetic`. A bounded AIS subscription returned zero valid positions; persistence remains disabled pending retention-rights confirmation. Tested GFW track/SAR paths are blocked; other products are unverified. See [data manifest](docs/DATA_MANIFEST.md).

SAR association evaluation, licensed boundaries, hotspot backtest, GNOME, offline operation, delivery, resource measurements and release gates are unfinished. No public API security, live coverage, illegal-activity detection accuracy or measured climate impact claim is supported.

## Historical replay backend - completed

A-005B and [A-005B-R1](tasks/completed/A-005B-R1.md) are complete based on the supplied implementation evidence. Migration 013 persists nullable exact assessment anchors; historical report creation rejects mismatched/legacy windows before insertion and hashes matching windows. The user reports 19 focused tests, one disposable-DB integration test and four assessment tests passed, and development DB upgraded to 013. No repeat suite was run during closeout. Legacy anchors remain unknown. Next: [B-005 browser integration](tasks/B-005.md), including fleet list, detail, sync, reports and bounded 409 recovery. The prepared replay pre-flight still has a rolling freshness assumption to resolve when packaging the demo.

## Execution

Codex orchestrates; OpenCode uses user-selected DeepSeek V4.1 Flash. One connected slice per brief, one focused check set, then completion with evidence. Optional audit does not hold completed work in a review queue. Historical replay backend is complete; [current handoff](tasks/current.md) points B to the complete browser integration. No implementation process was launched during this closeout. Reuse focused evidence; proceed to the next connected outcome. [Harness](docs/AGENT_HARNESS.md) defines invocation and limits.

Context cleanup: status/plan/harness reduced from 5,562 to 1,761 words (68%). Historical evidence retained; stale README, policy, skill and architecture claims reconciled. Local before-edit backups are in ignored `.agent-runs/context-cleanup-2026-11-07/`. Automatic approval review blocked cache deletion; caches remain. No application source, datasets or Docker volumes changed.

B-005 execution correction: the A-titled OpenCode session received the frontend prompt and edited 12 frontend files. Codex interrupted it on the user's accidental-run report; it is inactive with no queued prompts. Partial changes and a recovery copy are preserved, with details in tasks/B-005.md. Browser completion remains unclaimed; A must not automatically resume that frontend session.

GitHub handoff published: `ap` and `handoff/b-005` include the authenticated investigation backend, migrations through 013, contracts, task records and the preserved partial B-005 frontend checkpoint. B's existing `b/sprint` remains at `abc1d43` and was not overwritten. The frontend production build passed and the development database reports Alembic `013 (head)`. B still needs to complete and verify the browser journey in its own checkout.
