# Execution roadmap

Updated 7 November 2026. [FINAL_PRODUCT_PLAN.md](docs/FINAL_PRODUCT_PLAN.md) retains F01?F14 requirements, ownership and original deadlines (18:00 IST). [PROGRESS.md](PROGRESS.md) is current status; [backlog](tasks/backlog.md) retains task IDs and evidence. Do not use the count of backend subtasks as product completion.

## Next work, in outcome order

1. **Browser replay integration: B-005.** A-005B and its report-association correction are complete with reported migration 013 and focused evidence. Connect one visible historical preset across fleet list, map/detail, assessment and case/report calls; include bounded 409 recovery and the actual browser journey. Brief: tasks/B-005.md. Do not revisit completed backend window work. Address the pre-flight's rolling freshness assumption when packaging the prepared demo; preserve all original observation dates.
2. **Real evidence to export: B caller integration.** A-004E now binds a selected historical GFW event and independently dated SST context into the authenticated hashed report/case path. B must connect that contract to one traceable reviewed browser journey, preserving provider IDs, exact page bounds, original dates, modes and limitations. Do not turn events into tracks or combine unrelated timestamps into a claimed causal observation.
3. **Existing backend to screens: B-003A, then case actions.** Consume stored alert/triage APIs and render lifecycle/provenance; wire acknowledge/resolve/reopen and case close/reopen with expected versions, role handling and reload after 409. Source health should expose unknown/empty/stale states. These APIs already exist; do not build parallel versions. B owns web changes; coordinate a separate brief/worktree.
4. **Prepared judging run: B-002 with A-005 support.** One browser journey plus sourced export; record missing-data behavior and actual timing/sample size. Successful targeted checks are reused. Rebuild the API image once access permits and confirm the prepared setup without deleting volumes. Judge reviews the resulting journey against the documented criteria.
5. **Remaining full product:** complete legacy route protection, permitted real ingestion/jobs and SAR (A-002/A-006/A-007); then time-aligned environmental inputs/triage (A-008/A-009), backtest (A-010), GNOME (A-011), offline/integrity/delivery/scheduling (A-012/A-013), and paired B screens. Only begin dependency-ready slices.

The first two items serve the existing judging gate. Lifecycle UI is valuable but must not displace the real-source story or truthful labels before 10 November. No optional model training, infrastructure rewrite or new documentation audit is a prerequisite.

## Gates retained

| Deadline | Gate | Current state |
|---|---|---|
| 4 Nov | P1 access, identity, contracts and source model | Partial; original missed requirements remain open |
| 10 Nov | P2 reproducible real-data story, dates/attribution, traceable export/video | Partial; replay and historical layers exist but the complete journey is unverified |
| 20 Nov | P3 real evidence, SAR association, triage and environmental inputs | Partial backend slices; data/integration gaps remain |
| 2 Dec | P4 all F01?F14 reachable, backtest, spill and offline workflows | Pending |
| 11 Dec | P5 measured, reproducible and reviewed release | Pending |

Re-estimate remaining capacity on 11 November. The original plan's 230 person-hours for P1?P4 exceeds the 72-hour judging sprint; the sprint is a bounded demo, not full v1. Pilot review 8 January 2027, freeze 15 January, finale 20?21 January remain planning dates subject to event confirmation.

## Execution contract

Codex prepares a short brief with one observable outcome, allowed files, exact caller integration and critical acceptance checks. DeepSeek V4.1 Flash on OpenCode implements it end to end and marks COMPLETED when those criteria have evidence. Codex reconciles state and assigns the next authorized task; no duplicate acceptance suite. External blockers receive one bounded diagnosis and a restart condition, then work moves to independent integration.

Preserve A/B ownership, existing dirty work and Docker data. Database checks use isolated migrated databases. B-005 is ready for the frontend owner; no process was launched during backend closeout. See [harness](docs/AGENT_HARNESS.md) and [judge review](docs/HACKATHON_JUDGE_REVIEW.md).
