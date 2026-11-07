"""Focused checks for the judging replay verifier helpers (no database or network)."""
import unittest
from datetime import datetime, timedelta, timezone

from scripts.verify_judging_replay import (
    MAX_LOOKBACK_HOURS,
    expected_demo_mmsis,
    geojson_shape_errors,
    stale_after_error,
)

NOW = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)


def feature(lon=78.9, lat=8.8, event_id="event-1"):
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": {"event_id": event_id},
    }


def collection(features):
    return {"type": "FeatureCollection", "mode": "historical", "features": features}


class ReplayFreshnessTests(unittest.TestCase):
    def test_recent_position_passes(self):
        self.assertIsNone(stale_after_error(NOW - timedelta(hours=1), NOW))

    def test_naive_utc_timestamp_is_accepted(self):
        latest = (NOW - timedelta(hours=2)).replace(tzinfo=None)
        self.assertIsNone(stale_after_error(latest, NOW))

    def test_stale_position_fails_with_reseed_instruction(self):
        message = stale_after_error(NOW - timedelta(hours=MAX_LOOKBACK_HOURS + 5), NOW)
        self.assertIn("outside", message)
        self.assertIn("seed_demo.py", message)

    def test_missing_position_fails(self):
        self.assertIn("No replay positions", stale_after_error(None, NOW))


class GeoJsonShapeTests(unittest.TestCase):
    def test_valid_point_collection(self):
        self.assertEqual(geojson_shape_errors(collection([feature(), feature(79.1, 8.5)])), [])

    def test_empty_collection_is_valid_but_has_no_points(self):
        self.assertEqual(geojson_shape_errors(collection([])), [])

    def test_non_point_geometry_is_rejected(self):
        payload = collection([{"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[78, 8]]}}])
        self.assertTrue(any("Point" in error for error in geojson_shape_errors(payload)))

    def test_wrong_mode_is_rejected(self):
        payload = collection([feature()])
        payload["mode"] = "live"
        self.assertTrue(any("historical" in error for error in geojson_shape_errors(payload)))

    def test_out_of_range_wgs84_is_rejected(self):
        payload = collection([feature(lon=200, lat=8)])
        self.assertTrue(any("WGS84" in error for error in geojson_shape_errors(payload)))

    def test_missing_event_id_is_rejected(self):
        payload = collection([feature(event_id=None)])
        self.assertTrue(any("event_id" in error for error in geojson_shape_errors(payload)))


class DemoVocabularyTests(unittest.TestCase):
    def test_seed_still_defines_fourteen_replay_vessels(self):
        mmsis = expected_demo_mmsis()
        self.assertEqual(len(mmsis), 14)
        self.assertIn(419007431, mmsis)  # Sea Pearl II


if __name__ == "__main__":
    unittest.main()
