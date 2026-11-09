# C-v1 — transparent hotspot baselines and evaluation

Owner: C
Feature IDs: F08, F14
Status: **COMPLETED — 9 November 2026**

## Outcome

Implemented a dependency-free, availability-aware rolling evaluator for
persistence, recent-effort and uniform scan baselines. It enforces an exact scan
budget, reserves at least 20% of persistence/recent-effort selections outside
the top-budget hotspot cells, records factor explanations and produces stable
evaluation/input/configuration checksums.

The existing prepared Copernicus SST artifact is consumed as descriptive input
without copying or relabelling it. Its three-day history and missing
per-observation availability timestamps explicitly block condition-forecast
evaluation. Synthetic/replay activity can exercise the pipeline but cannot pass
the real-data gate.

## Files owned by this task

- `ml/hotspot_baselines.py`
- `ml/run_hotspot_evaluation.py`
- `ml/tests/test_hotspot_baselines.py`
- `ml/tests/fixtures/synthetic_effort_history.json`
- `ml/README.md`
- `docs/evaluation/HOTSPOT_BASELINES.md`
- `docs/evaluation/hotspot-current-status.json`
- `tasks/parallel/C-v1.md`

## Acceptance coverage

- [x] Persistence, seven-day recent-effort and uniform baselines are explicit.
- [x] Rolling folds use only earlier observations available by prediction time.
- [x] Missing/cloud/invalid effort is excluded rather than imputed.
- [x] Fixed budget and rounded-up 20% non-hotspot coverage are enforced.
- [x] Captured effort and active-cell detected/missed metrics are exported.
- [x] Availability-aware SST persistence MAE is implemented and honestly blocked on the current slice.
- [x] Selected cells include their actual score factors and coverage slot.
- [x] Exact input/configuration/evaluation SHA-256 values are reproducible.
- [x] Synthetic/replay and real evaluation modes remain distinct.
- [x] Current insufficient-history gate is explicit; no accuracy is claimed.
- [x] Focused tests and reproduction CLI are present.
- [x] Focused tests and CLI exercise executed: 6 tests passed; the synthetic
  CLI produced 2 folds and correctly reported the empirical gate `blocked`.

## Deferred verification commands

```text
python -m unittest ml.tests.test_hotspot_baselines
python -m ml.run_hotspot_evaluation ml/tests/fixtures/synthetic_effort_history.json --budget 2 --sst apps/api/data/copernicus/gulf_mannar_sst_20261018_20.json --min-history-days 2 --min-folds 2 --output-dir .artifacts/hotspot-synthetic
```

## Blocked empirical gate

A real activity backtest needs a bounded, permitted historical Gulf of Mannar
effort export with cell ID, observation time, availability time, effort hours,
quality mask, grid resolution and verified permissions. Longer availability-
aware SST/chlorophyll history is separately needed for environmental forecast
metrics. No external API/account is required for the implementation or the
synthetic software exercise, so implementation continued without registration.
