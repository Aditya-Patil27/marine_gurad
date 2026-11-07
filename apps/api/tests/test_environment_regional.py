import unittest
from unittest.mock import patch
from fastapi import HTTPException

from app.api import environment


class EnvironmentRegionalTests(unittest.IsolatedAsyncioTestCase):
    def test_select_latest_observation_deterministic_and_tie_breaking(self):
        # Multiple candidates with distinct timestamps and identical timestamps with coordinates tie-break
        sample_values = [
            {"observed_at": "2026-10-18T00:00:00Z", "latitude": 8.5, "longitude": 78.5, "temperature_c": 28.0},
            {"observed_at": "2026-10-20T00:00:00Z", "latitude": 8.1, "longitude": 78.2, "temperature_c": 29.1},
            # Same timestamp, different coordinates to test tie-breaking:
            {"observed_at": "2026-10-20T00:00:00Z", "latitude": 8.3, "longitude": 78.4, "temperature_c": 29.5},
            {"observed_at": "2026-10-20T00:00:00Z", "latitude": 8.3, "longitude": 78.6, "temperature_c": 29.8},
            {"observed_at": "2026-10-19T00:00:00Z", "latitude": 8.9, "longitude": 78.9, "temperature_c": 30.0},
        ]
        winner = environment.select_latest_observation(sample_values)
        # Winner must be latest timestamp (2026-10-20), highest latitude (8.3), highest longitude (78.6)
        self.assertEqual(winner["observed_at"], "2026-10-20T00:00:00Z")
        self.assertEqual(winner["latitude"], 8.3)
        self.assertEqual(winner["longitude"], 78.6)
        self.assertEqual(winner["temperature_c"], 29.8)

    def test_select_latest_observation_rejects_empty_or_malformed(self):
        with self.assertRaises(ValueError):
            environment.select_latest_observation([])
        with self.assertRaises(ValueError):
            environment.select_latest_observation(None)
        with self.assertRaises(ValueError):
            environment.select_latest_observation([{"invalid": "item"}])
        with self.assertRaises(ValueError):
            environment.select_latest_observation([
                {"observed_at": None, "latitude": 8.0, "longitude": 78.0, "temperature_c": 29.0}
            ])
        with self.assertRaises(ValueError):
            environment.select_latest_observation([
                {"observed_at": "2026-10-20T00:00:00Z", "latitude": "invalid", "longitude": 78.0, "temperature_c": 29.0}
            ])

    def test_rejects_invalid_timestamp_nonfinite_and_bad_coordinates(self):
        valid = {"observed_at": "2026-10-20T00:00:00Z", "latitude": 8.0, "longitude": 78.0, "temperature_c": 29.0}
        for change in (
            {"observed_at": "not-a-date"}, {"observed_at": "2026-10-20T00:00:00"},
            {"latitude": 91}, {"longitude": -181}, {"temperature_c": float("nan")},
            {"latitude": float("inf")}, {"temperature_c": True},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                environment.select_latest_observation([{**valid, **change}])

    def test_latest_compares_actual_instants_across_timezones(self):
        values = [
            {"observed_at": "2026-10-20T01:00:00+02:00", "latitude": 8, "longitude": 78, "temperature_c": 28},
            {"observed_at": "2026-10-20T00:00:00Z", "latitude": 8, "longitude": 78, "temperature_c": 29},
        ]
        self.assertEqual(environment.select_latest_observation(values)["temperature_c"], 29)

    async def test_regional_environment_success_shape(self):
        mock_data = {
            "status": "available",
            "source": "Copernicus Marine Service",
            "product": "SST_GLO_SST_L3S_NRT_OBSERVATIONS_010_010",
            "dataset": "IFREMER-GLOB-SST-L3-NRT-OBS_FULL_TIME_SERIE",
            "dataset_version": "202211",
            "doi": "10.48670/moi-00164",
            "unit": "°C",
            "kind": "satellite_observation",
            "mode": "historical_subset",
            "values": [
                {"observed_at": "2026-10-18T00:00:00Z", "latitude": 8.5, "longitude": 78.1, "temperature_c": 30.5},
                {"observed_at": "2026-10-20T00:00:00Z", "latitude": 8.2, "longitude": 78.5, "temperature_c": 29.7},
            ],
        }
        with patch.object(environment, "load_satellite_observations", return_value=mock_data):
            res = await environment.regional_environment()

        # B's five required fields
        self.assertIn("variable", res)
        self.assertIn("value", res)
        self.assertIn("unit", res)
        self.assertIn("observed_at", res)
        self.assertIn("attribution", res)

        self.assertEqual(res["value"], 29.7)
        self.assertEqual(res["unit"], "°C")
        self.assertEqual(res["observed_at"], "2026-10-20T00:00:00Z")
        self.assertIn("Historical satellite-derived sea surface temperature", res["variable"])
        self.assertIn("Copernicus Marine Service", res["attribution"])

        # Explicit mode, status, and metadata
        self.assertEqual(res["status"], "available")
        self.assertEqual(res["mode"], "historical")
        self.assertEqual(res["location"], {"latitude": 8.2, "longitude": 78.5})
        self.assertIn("single grid cell", res["limitations"])

    async def test_regional_environment_missing_artifact_raises_503(self):
        with patch.object(environment, "load_satellite_observations", side_effect=HTTPException(status_code=503, detail="Prepared Copernicus observation subset unavailable")):
            with self.assertRaises(HTTPException) as ctx:
                await environment.regional_environment()
            self.assertEqual(ctx.exception.status_code, 503)

    async def test_regional_environment_empty_values_raises_503(self):
        mock_data = {
            "status": "available",
            "dataset": "IFREMER-GLOB-SST-L3-NRT-OBS_FULL_TIME_SERIE",
            "values": [],
        }
        with patch.object(environment, "load_satellite_observations", return_value=mock_data):
            with self.assertRaises(HTTPException) as ctx:
                await environment.regional_environment()
            self.assertEqual(ctx.exception.status_code, 503)
            self.assertIn("No valid observation", ctx.exception.detail)

    async def test_unexpected_unit_returns_503(self):
        data = {"unit": "K", "values": [{"observed_at": "2026-10-20T00:00:00Z", "latitude": 8, "longitude": 78, "temperature_c": 29}]}
        with patch.object(environment, "load_satellite_observations", return_value=data):
            with self.assertRaises(HTTPException) as ctx:
                await environment.regional_environment()
        self.assertEqual(ctx.exception.status_code, 503)
