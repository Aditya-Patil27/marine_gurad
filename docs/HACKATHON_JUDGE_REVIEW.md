# Hackathon judge review — 7 November 2026

Independent review requested by the user. This is an evidence-based desk review, not an official score or a fresh browser acceptance run.

## Rubric and verdict

Rubric source: [final product plan, section 8](FINAL_PRODUCT_PLAN.md), especially its 10 November judging gate. The retained gate calls for the climate problem, analytical method, implementation, expected impact, and feasibility/evidence. An original official scoring sheet and weights were not located in the reviewed material; the five dimensions below operationalize that retained guidance and do not invent official weights.

| Dimension | Verdict | Evidence and remaining gap |
|---|---|---|
| Climate problem and relevance | Convincing direction; evidence incomplete | The [storyboard](demo/storyboard.md) links coastal investigation to habitat resilience and explicitly separates expected effects from observed outcomes. External ecological facts still need citations; regional SST alone does not demonstrate climate adaptation. |
| Analytical method and innovation | Credible explainability; limited demonstrated novelty | Additive vessel screening rules, provenance labels, historical event evidence and report hashes are documented. The demonstrable method is rule-based screening. SAR association evaluation, environmental/activity prediction and measured weather triage remain incomplete; they cannot carry an AI-performance claim. |
| Working implementation | Substantial foundations; incomplete connected story | Recorded work includes local roles/CSRF, assessments, cases/revisions, approval, persistent alert APIs, source runs and historical SST/GFW exports. User-observed browser login/case creation is recorded on 6 November. Real event evidence remains separate from the replay assessment/case journey; backend lifecycle completion does not establish frontend integration. |
| Expected impact | Plausible pathway; unmeasured benefit | Source-labelled evidence could make analyst review more reliable. No measured review-time improvement, investigation quality, ecological benefit or prevented fishing is supplied. Storyboard measurement placeholders cannot be narrated as results. |
| Feasibility and reproducibility | Local demonstration plausible; fragile readiness | Docker stack and bounded replay are documented. [A-005](../tasks/completed/A-005.md) recorded 11 pre-flight checks passed and sign-in skipped, hence PARTIAL. Fixed 31 October–1 November replay ages out of the 168-hour window before 10 November. Durable image rebuilding, usable real tracks and source rights remain unresolved. |

Subjective readiness estimate: roughly **55–65% of the narrow judging demonstration**, and **30–40% of full F01–F14 v1**. These ranges reflect connected outcomes and missing capabilities, not task counts, test counts or measured engineering completion. The judging gate is not yet evidenced as passed. Quality is stronger in backend safeguards and truthful limitations than in integrated product delivery and empirical evaluation.

## Three highest-payoff integrations

1. **Complete one real-source evidence-to-export journey.** Select a historical GFW event, preserve its source ID and dates, show independently dated SST, and export the same traceable evidence. If a reviewed case is included, bind that source record explicitly; never manufacture a vessel track or transfer a replay score onto a real event.
2. **Connect existing investigation services to the screens.** Use stored alerts/triage and case status/history where needed for the selected story, preserving version conflicts and session identity. Demonstrate one alert/evidence/case/report transition, including its failure state. Avoid building another parallel backend subsystem.
3. **Make the Docker demonstration reproducible at a fixed replay time.** Preserve shared data and case history; remove dependence on a rolling window that expires before judging. Rebuild the prepared image, run one focused authenticated journey, then record review time and evidence completeness with sample size and limits. Use that run for the final video.

## Evidence boundaries and presentation corrections

- The 6 November pre-flight, earlier focused tests and user browser report are historical evidence. This review did not rerun tests, call providers, sign in, or inspect a live browser.
- [A-006D](../tasks/completed/A-006D.md) records zero valid positions from one live AIS subscription. This proves neither usable tracking nor absence of vessels.
- [A-004D](../tasks/completed/A-004D.md) records case transition APIs and audit rows. It does not claim their UI is connected.
- The existing video is a sample-data design walkthrough. Its SAR, weather-cleared alerts and spill visuals are not working-feature evidence.
- The storyboard still contains fixture-specific scores, a 24-hour statement, typed-reviewer wording and unresolved placeholders. Replace them with the actual selected journey before recording; do not narrate receiver outage as ruled out without evidence.
- Pre-cleanup README/harness claims that authentication was absent or A-001 was paused conflicted with later evidence; those claims were corrected during this review. Backend completion still does not imply browser delivery.
- Preserve historical task evidence, source permissions and limitations. Broad re-verification is lower value than closing these specific integration gaps.
