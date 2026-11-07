import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from app.api import reports


class FakeDB:
    def execute(self, statement, parameters):
        if "SELECT" in str(statement):
            return []
        snapshot = json.loads(parameters["snapshot"])
        return SimpleNamespace(one=lambda: SimpleNamespace(_mapping={"snapshot": snapshot, "sha256": parameters["sha"]}))

    def commit(self):
        pass


class ReportOceanTests(unittest.TestCase):
    def test_context_is_opt_in_and_bound_to_digest(self):
        context = {"status": "available", "values": [{"temperature_c": 28.0}], "dataset": "sample"}
        with patch.object(reports, "get_vessel", return_value={"mmsi": 123456789}), patch.object(reports, "load_satellite_observations", return_value=context):
            result = reports.create_report(reports.CreateReport(mmsi=123456789, include_regional_ocean_context=True), db=FakeDB())
        self.assertTrue(result["integrity_ok"])
        self.assertIn("not necessarily concurrent", result["snapshot"]["regional_ocean_context"]["association"])
        result["snapshot"]["regional_ocean_context"]["values"][0]["temperature_c"] = 29
        self.assertNotEqual(reports.digest(result["snapshot"]), result["sha256"])

    def test_missing_requested_context_stops_report_creation(self):
        with patch.object(reports, "get_vessel", return_value={"mmsi": 123456789}), patch.object(reports, "load_satellite_observations", side_effect=HTTPException(503)):
            with self.assertRaises(HTTPException):
                reports.create_report(reports.CreateReport(mmsi=123456789, include_regional_ocean_context=True), db=FakeDB())
