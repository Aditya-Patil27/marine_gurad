"""Focused, no-network checks for the read-only source health contract."""
import json
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi import HTTPException

from app.api import gfw, sources

NOW = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)


class _Result:
    def __init__(self, row):
        self._row = row

    def mappings(self):
        return self

    def one(self):
        return self._row


class _Db:
    def __init__(self, row):
        self._row = row

    def execute(self, *_args, **_kwargs):
        return _Result(self._row)


def db_row(positions=678, vessels=14, latest=None, source_modes=None):
    return {"positions": positions, "vessels": vessels, "latest": latest,
            "source_modes": ["unknown"] if source_modes is None else source_modes}


def sst_artifact():
    return {
        "source": "Copernicus Marine Service",
        "dataset": "IFREMER-GLOB-SST-L3-NRT-OBS_FULL_TIME_SERIE",
        "dataset_version": "202211",
        "doi": "10.48670/moi-00164",
        "unit": "°C",
        "kind": "satellite_observation",
        "values": [
            {"observed_at": "2026-10-18T00:00:00Z", "latitude": 8.1, "longitude": 78.2, "temperature_c": 29.1},
            {"observed_at": "2026-10-20T00:00:00Z", "latitude": 8.2, "longitude": 78.5, "temperature_c": 29.72},
        ],
    }


class ReplayHealthTests(unittest.TestCase):
    def test_fresh_local_records(self):
        result = sources.replay_health(_Db(db_row(latest=NOW - timedelta(hours=2))), NOW)
        self.assertEqual(result["status"], "available")
        self.assertEqual(result["positions"], 678)
        self.assertEqual(result["vessels"], 14)
        self.assertEqual(result["source_mode"], "unknown")
        self.assertAlmostEqual(result["age_hours"], 2.0)

    def test_naive_database_timestamp_is_treated_as_utc(self):
        latest = (NOW - timedelta(hours=3)).replace(tzinfo=None)
        result = sources.replay_health(_Db(db_row(latest=latest)), NOW)
        self.assertEqual(result["status"], "available")

    def test_stale_records_are_not_available(self):
        result = sources.replay_health(_Db(db_row(latest=NOW - timedelta(hours=200))), NOW)
        self.assertEqual(result["status"], "stale")
        self.assertGreater(result["age_hours"], 168)

    def test_empty_database_is_empty_not_available(self):
        result = sources.replay_health(_Db(db_row(positions=0, vessels=0, latest=None)), NOW)
        self.assertEqual(result["status"], "empty")
        self.assertIsNone(result["latest_observed_at"])


class PreparedSstHealthTests(unittest.TestCase):
    def test_available_subset_reports_historical_mode_and_latest_value(self):
        result = sources.prepared_sst_health(loader=sst_artifact)
        self.assertEqual(result["status"], "available")
        self.assertEqual(result["mode"], "historical")
        self.assertEqual(result["value"], 29.72)
        self.assertEqual(result["unit"], "°C")
        self.assertEqual(result["latest_observed_at"], "2026-10-20T00:00:00Z")
        self.assertIn("10.48670/moi-00164", result["attribution"])

    def test_missing_subset_is_unavailable_without_substituting_a_value(self):
        def missing():
            raise HTTPException(503, "Prepared Copernicus observation subset unavailable")

        result = sources.prepared_sst_health(loader=missing)
        self.assertEqual(result["status"], "unavailable")
        self.assertNotIn("value", result)

    def test_empty_values_are_unavailable(self):
        artifact = {**sst_artifact(), "values": []}
        self.assertEqual(sources.prepared_sst_health(loader=lambda: artifact)["status"], "unavailable")


class ConfiguredSourceTests(unittest.TestCase):
    def test_gfw_configured_is_not_availability(self):
        with patch.object(
            sources.gfw,
            "provider_health",
            return_value={"provider": "Global Fishing Watch", "configured": True, "rate_limits": {}},
        ):
            result = sources.gfw_health()
        self.assertEqual(result["status"], "configured")
        self.assertEqual(result["availability"], "not_checked")
        self.assertNotIn("token", json.dumps(result).lower())

    def test_gfw_unconfigured(self):
        with patch.object(
            sources.gfw, "provider_health", return_value={"configured": False, "rate_limits": {}}
        ):
            self.assertEqual(sources.gfw_health()["status"], "not_configured")

    def test_aisstream_reports_unknown_coverage(self):
        with patch.object(sources.settings, "AISSTREAM_API_KEY", ""):
            result = sources.aisstream_health()
        self.assertEqual(result["status"], "not_configured")
        self.assertEqual(result["coverage"], "unknown")

    def test_aisstream_configured_still_unknown_coverage(self):
        with patch.object(sources.settings, "AISSTREAM_API_KEY", "present"):
            result = sources.aisstream_health()
        self.assertEqual(result["status"], "configured")
        self.assertEqual(result["coverage"], "unknown")
        self.assertNotIn("present", json.dumps(result))


class CombinedHealthTests(unittest.TestCase):
    def test_combined_shape_declares_no_calls_or_writes(self):
        with patch.object(sources, "prepared_sst_health", return_value={"status": "unavailable"}), \
             patch.object(sources, "gfw_health", return_value={"status": "not_configured"}), \
             patch.object(sources, "aisstream_health", return_value={"status": "not_configured"}), \
             patch.object(sources, "open_meteo_health", return_value={"status": "not_checked"}):
            result = sources.build_source_health(_Db(db_row(latest=NOW)), NOW, runs={})

        self.assertEqual(result["checked_at"], NOW.isoformat())
        self.assertFalse(result["external_calls"])
        self.assertFalse(result["writes"])
        self.assertEqual(
            set(result["sources"]),
            {"local_vessel_records", "copernicus_sst", "global_fishing_watch", "aisstream", "open_meteo_marine"},
        )


class GfwStatusCompatibilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_status_route_uses_shared_provider_health(self):
        snapshot = {
            "provider": "Global Fishing Watch",
            "configured": False,
            "rate_limits": {},
            "rate_limits_observed_at": None,
            "local_requests_last_30_minutes": 0,
            "limitations": "per process",
        }
        with patch.object(gfw, "provider_health", return_value=snapshot):
            self.assertEqual(await gfw.status(), snapshot)


if __name__ == "__main__":
    unittest.main()
