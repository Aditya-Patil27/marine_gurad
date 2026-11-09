# Hotspot baseline and data card

Status: implemented, verification deferred to the combined v1 check. Current
real forecast-evaluation gate: **blocked**.

## Intended use and claim boundary

The evaluator ranks regional grid cells for review under a fixed scan budget.
It is a transparent fishing-effort prioritisation aid. Historical effort is not
illegal-fishing ground truth, the recommendation does not task a satellite, and
environmental anomalies are not folded into an illegality score.

No learned ranker is enabled. The product should continue to show these
baselines until a later, held-out result supports replacing them.

## Baselines

| Baseline | Score available at prediction time | Purpose |
|---|---|---|
| Persistence | Latest valid effort value for the cell | Tests whether the last observed activity persists |
| Recent effort | Sum of valid effort over the previous seven days | Transparent activity-density ranking |
| Uniform scan | Equal score, deterministic rotating cell sample | Measures what an unprioritised scan budget captures |

Persistence and recent-effort plans allocate `ceil(budget × 0.20)` cells from
outside the top-budget hotspot set. This makes blind-spot coverage explicit and
keeps the total selected cells exactly equal to the configured budget. Uniform
scanning is already non-hotspot-directed and uses the full budget as its
comparison sample.

Each selected cell includes the score, coverage slot, latest available effort,
latest observation time, recent effort, recent observation count and lookback.
The output reports captured effort, capture rate, active cells detected and
active cells missed. These metrics describe the supplied data only.

For SST, the evaluator also implements a cell-level persistence forecast: the
most recent earlier temperature that was available by the target observation
time. It reports Celsius MAE and the exact source/target pairs, and blocks the
metric when fewer than seven availability-aware pairs exist.

## Temporal evaluation and leakage controls

Evaluation uses expanding daily folds. For a target day beginning at time `T`:

- feature observations must have `observed_at < T`;
- feature records must have `available_at <= T`;
- target effort is read only from the later target day;
- cloud, missing and invalid records are excluded, not imputed; and
- every fold records the latest feature observation and availability time plus
  a leakage audit result.

At least seven distinct history days and three evaluable target folds are the
default minimum. A real run also requires mode `historical`, `recorded` or
`live`, plus a non-empty permission statement. Synthetic and replay runs remain
blocked even if their software metrics are calculable.

## Current data readiness

The existing prepared Copernicus artifact
`apps/api/data/copernicus/gulf_mannar_sst_20261018_20.json` is reused directly;
it is not copied into this area. It contains 28 valid gridded values across only
18–20 October 2026. It does not contain per-observation availability timestamps,
chlorophyll, or fishing effort. It is therefore suitable for a descriptive SST
layer but not for an availability-aware condition MAE or activity backtest.

The existing vessel replay is useful for the investigation demonstration, but
invented vessel tracks are not fishing-effort ground truth and are not promoted
to a real evaluation dataset. The versioned synthetic effort fixture under
`ml/tests/fixtures/` tests the pipeline while keeping synthetic evidence
separate.

Opening the real evaluation gate requires a bounded, permitted Gulf of Mannar
effort export with cell IDs, observation times, source availability times,
effort hours, quality flags, grid resolution, source identity and verified
permissions. Chlorophyll or longer SST history is separately required before
claiming environmental forecast evaluation. No external account is required to
finish or exercise the implementation itself.

## Reproduction artifacts

`python -m ml.run_hotspot_evaluation` writes:

- `hotspot-evaluation.json`: configuration, gate, fold audits, baseline
  metrics, explanations and the latest budgeted recommendations; and
- `artifact-manifest.json`: SHA-256 checksums for exact activity/SST inputs,
  evaluator configuration and evaluation output.

The output contains no wall-clock generation field, so identical inputs and
configuration produce identical metrics and checksums. Commands are recorded in
`ml/README.md`. They have intentionally not been run in this implementation
pass; the parent v1 verification owns execution and result recording.

## Known failure modes

- Sparse days or cells can make capture rates unstable; the gate reports the
  fold count rather than presenting a small sample as accuracy.
- Delayed source publication reduces available history and can block folds.
- A scan budget equal to the entire grid cannot measure non-hotspot blind spots
  and is rejected.
- Missing/cloud measurements remain unknown; the evaluator does not interpolate
  them.
- Distribution shifts, provider coverage gaps and effort-detection bias are not
  corrected by these baselines.
