# ml

Reserved for dataset preparation, evaluation and model cards. This directory does not establish that a trained SAR detector or hotspot ranker exists. User C owns it only when explicitly allocated; otherwise User A owns the plan's small baseline tasks.

Existing model-loading code is in `apps/api/app/services/`. Trained weights are not committed or validated by the current audit. The pollution YOLO path is not the planned optional Ai2 SAR adapter; LSTM has a linear fallback. See [architecture](../ARCHITECTURE.md), [decisions](../DECISIONS.md) and [data manifest](../docs/DATA_MANIFEST.md). Do not download full xView3 splits or begin model training without a bounded task.
