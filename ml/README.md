# SamudraSense ML and evaluation

This directory contains the transparent hotspot baselines required by F08. It
does not contain a trained hotspot model or establish forecast accuracy.

## Implemented baseline evaluator

`hotspot_baselines.py` provides:

- persistence (latest available effort per cell), recent-effort (seven-day
  available effort), and uniform scan baselines;
- expanding, time-separated daily folds whose feature records must have both
  `observed_at < prediction_at` and `available_at <= prediction_at`;
- an exact fixed cell budget, with at least 20% (rounded up) selected outside
  the top-budget hotspot set for persistence and recent-effort rankings;
- captured-effort and detected/missed-active-cell metrics;
- SST persistence MAE when enough per-observation availability history exists;
- the actual score factors for every selected cell; and
- stable input, configuration and evaluation checksums.

The interchange format is versioned in
`tests/fixtures/synthetic_effort_history.json`. Each input declares its source,
mode, permissions and grid resolution. Masked/cloud values must be null; they
are never converted into zero observations. Synthetic/replay input can exercise
the software but cannot open the real-evaluation gate.

## Commands (not yet executed for this change)

Focused checks:

```text
python -m unittest ml.tests.test_hotspot_baselines
```

Reproducible synthetic software exercise plus the existing prepared SST slice:

```text
python -m ml.run_hotspot_evaluation \
  ml/tests/fixtures/synthetic_effort_history.json \
  --budget 2 \
  --sst apps/api/data/copernicus/gulf_mannar_sst_20261018_20.json \
  --min-history-days 2 \
  --min-folds 2 \
  --output-dir .artifacts/hotspot-synthetic
```

This command will intentionally report a blocked gate because its activity
fixture is synthetic and the SST subset is descriptive. Replace only the first
argument with a permitted historical effort export that follows the same schema
and use the default 7-day history/3-fold minimum for an evaluable run.

See [the baseline and data card](../docs/evaluation/HOTSPOT_BASELINES.md) and
[the current gate](../docs/evaluation/hotspot-current-status.json).
