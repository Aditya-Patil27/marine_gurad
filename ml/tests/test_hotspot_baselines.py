import json
from pathlib import Path
import tempfile
import unittest

from ml.hotspot_baselines import (
    artifact_manifest,
    evaluate_sst_persistence,
    evaluate_activity,
    load_activity_dataset,
)


FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_effort_history.json"


class HotspotBaselineTests(unittest.TestCase):
    def test_rolling_evaluation_is_budgeted_reserved_and_explicitly_synthetic(self):
        data = load_activity_dataset(FIXTURE)

        report = evaluate_activity(
            data,
            scan_budget=2,
            min_history_days=2,
            min_evaluation_folds=2,
        )

        self.assertEqual(report["gate"]["status"], "blocked")
        self.assertIn("not a permitted", " ".join(report["gate"]["blockers"]))
        self.assertEqual(len(report["folds"]), 2)
        for fold in report["folds"]:
            self.assertTrue(fold["leakage_audit"]["passed"])
            for baseline, result in fold["baselines"].items():
                self.assertEqual(result["selected_cell_count"], 2)
                expected_reserve = 0 if baseline == "uniform" else 1
                self.assertEqual(result["non_hotspot_reserved_count"], expected_reserve)

    def test_late_input_and_cloud_mask_do_not_enter_prediction_history(self):
        data = load_activity_dataset(FIXTURE)
        data = json.loads(json.dumps(data))
        data["records"].append({
            "cell_id": "c6",
            "observed_at": "2026-01-02T00:00:00Z",
            "available_at": "2026-01-04T12:00:00Z",
            "effort_hours": 999.0,
            "quality": "valid",
        })

        report = evaluate_activity(data, scan_budget=2, min_history_days=2, min_evaluation_folds=1)

        first_fold = report["folds"][0]
        self.assertEqual(first_fold["target_start"], "2026-01-03T00:00:00Z")
        self.assertEqual(first_fold["history_record_count"], 4)
        self.assertEqual(first_fold["target_record_count"], 2)
        self.assertTrue(first_fold["leakage_audit"]["passed"])

    def test_report_and_manifest_are_reproducible(self):
        data = load_activity_dataset(FIXTURE)
        first = evaluate_activity(data, scan_budget=2, min_history_days=2, min_evaluation_folds=1)
        second = evaluate_activity(data, scan_budget=2, min_history_days=2, min_evaluation_folds=1)
        self.assertEqual(first, second)

        with tempfile.TemporaryDirectory() as temp_dir:
            copied = Path(temp_dir) / "input.json"
            copied.write_bytes(FIXTURE.read_bytes())
            self.assertEqual(
                artifact_manifest(copied, first)["evaluation_sha256"],
                artifact_manifest(copied, second)["evaluation_sha256"],
            )

    def test_prepared_sst_without_availability_history_is_descriptive_only(self):
        summary = evaluate_sst_persistence({
            "source": "example",
            "product": "sst",
            "dataset": "example-v1",
            "mode": "historical_subset",
            "unit": "degC",
            "values": [
                {"observed_at": "2026-01-01T00:00:00Z", "latitude": 8.0, "longitude": 78.0, "temperature_c": 29.0},
                {"observed_at": "2026-01-02T00:00:00Z", "latitude": 8.0, "longitude": 78.0, "temperature_c": 29.2},
            ],
        })
        self.assertEqual(summary["status"], "blocked")
        self.assertIn("availability times", " ".join(summary["blockers"]))

    def test_sst_persistence_uses_only_values_available_before_prediction(self):
        summary = evaluate_sst_persistence({
            "source": "synthetic test fixture",
            "product": "sst",
            "dataset": "fixture-v1",
            "mode": "synthetic",
            "unit": "degC",
            "values": [
                {"observed_at": "2026-01-01T00:00:00Z", "available_at": "2026-01-02T06:00:00Z", "latitude": 8.0, "longitude": 78.0, "temperature_c": 29.0},
                {"observed_at": "2026-01-02T00:00:00Z", "available_at": "2026-01-03T06:00:00Z", "latitude": 8.0, "longitude": 78.0, "temperature_c": 40.0},
                {"observed_at": "2026-01-03T00:00:00Z", "available_at": "2026-01-03T06:00:00Z", "latitude": 8.0, "longitude": 78.0, "temperature_c": 30.0},
            ],
        }, min_pairs=1)
        self.assertEqual(summary["status"], "blocked")
        self.assertEqual(summary["pair_count"], 1)
        self.assertEqual(summary["pairs"][0]["predicted_temperature_c"], 29.0)
        self.assertEqual(summary["mae_c"], 1.0)
        self.assertTrue(summary["leakage_audit_passed"])

    def test_invalid_or_masked_values_cannot_be_presented_as_valid_effort(self):
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cloud = next(record for record in data["records"] if record["quality"] == "cloud")
        cloud["effort_hours"] = 10.0
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bad.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "masked effort_hours must be null"):
                load_activity_dataset(path)


if __name__ == "__main__":
    unittest.main()
