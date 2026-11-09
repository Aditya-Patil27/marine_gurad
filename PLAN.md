# Execution roadmap

Updated 8 November 2026. [FINAL_PRODUCT_PLAN.md](docs/FINAL_PRODUCT_PLAN.md) retains F01?F14 requirements, ownership and original deadlines (18:00 IST). [PROGRESS.md](PROGRESS.md) is current status; [backlog](tasks/backlog.md) retains task IDs and evidence. Do not use the count of backend subtasks as product completion.

## Next work, in outcome order

Execution overlay, 8 November: the user authorized [parallel A/B phase queues](tasks/PARALLEL_EXECUTION.md) through the existing full-product scope. Each session records its own results and continues after passing acceptance gates; failed gates or human dependencies stop the affected session. A starts replay correctness/security while B starts B-005F. Original deadlines and F01–F14 completion requirements remain unchanged.

1. **Event-only browser caller: B-005F.** A-004F is complete through migration 014. Connect its explicit report → case sequence and record one real historical GFW event review/export. Preserve provider IDs, exact page bounds, original dates, modes and limitations. Do not turn events into tracks or combine unrelated timestamps into a causal observation. Brief: tasks/B-005F.md.
2. **Prepared judging run: B-002 with A-005 support.** Reuse the completed synthetic replay and lifecycle/export checks plus the B-005F source-bound journey, then record missing-data behavior and actual timing/sample size. Rebuild the API image once access permits without deleting volumes.
3. **Replay alert correctness.** Make stored-alert sync honor the selected historical window and replace offence-implying wording with screening language; then update the existing B screen caller. Keep this separate from B-005F.
4. **Remaining full product:** complete legacy route protection, permitted real ingestion/jobs and SAR (A-002/A-006/A-007); then time-aligned environmental inputs/triage (A-008/A-009), backtest (A-010), GNOME (A-011), offline/integrity/delivery/scheduling (A-012/A-013), and paired B screens. Only begin dependency-ready slices.

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

Preserve A/B ownership, existing dirty work and Docker data. Database checks use isolated migrated databases. A-004F is complete; the two execution prompts are ready but no session was launched. The parallel plan supplies the explicit multi-phase scheduling exception to the [harness](docs/AGENT_HARNESS.md). See also [judge review](docs/HACKATHON_JUDGE_REVIEW.md).
