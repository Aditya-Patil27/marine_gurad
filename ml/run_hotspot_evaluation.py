"""Write a reproducible baseline report and checksum manifest.

Usage:
    python -m ml.run_hotspot_evaluation INPUT.json --budget 5 --output-dir out \
        --sst apps/api/data/copernicus/gulf_mannar_sst_20261018_20.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ml.hotspot_baselines import (
    artifact_manifest,
    evaluate_sst_persistence,
    evaluate_activity,
    load_activity_dataset,
    report_sha256,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("activity", type=Path)
    parser.add_argument("--budget", type=int, required=True, help="Fixed number of cells scanned per fold")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--sst", type=Path, help="Optional prepared SST JSON for descriptive readiness")
    parser.add_argument("--lookback-days", type=int, default=7)
    parser.add_argument("--min-history-days", type=int, default=7)
    parser.add_argument("--min-folds", type=int, default=3)
    args = parser.parse_args()

    activity = load_activity_dataset(args.activity)
    report = evaluate_activity(
        activity,
        scan_budget=args.budget,
        lookback_days=args.lookback_days,
        min_history_days=args.min_history_days,
        min_evaluation_folds=args.min_folds,
    )
    if args.sst:
        with args.sst.open(encoding="utf-8") as source:
            report["condition_evaluation"] = evaluate_sst_persistence(json.load(source))
        report["evaluation_sha256"] = report_sha256(report)
    manifest = artifact_manifest(args.activity, report, sst_path=args.sst)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "hotspot-evaluation.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.output_dir / "artifact-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"gate={report['gate']['status']} folds={len(report['folds'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
