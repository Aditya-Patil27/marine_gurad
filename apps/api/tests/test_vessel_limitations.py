from types import SimpleNamespace
from datetime import datetime, timezone
import json
import unittest
from unittest.mock import patch

from app.api import reports, vessels
from app.schemas.user import UserResponse, UserRole


class FakeDB:
    def __init__(self, sar_rows=None):
        self.sar_rows = sar_rows or []
        self.executed_statements = []

    def execute(self, statement, parameters=None):
        stmt_str = str(statement)
        self.executed_statements.append((stmt_str, parameters))
        if "SELECT" in stmt_str and "sar_detections" in stmt_str:
            return self.sar_rows
        if "INSERT INTO incident_reports" in stmt_str:
            snapshot = json.loads(parameters["snapshot"])
            return SimpleNamespace(
                one=lambda: SimpleNamespace(
                    _mapping={
                        "id": 1,
                        "mmsi": parameters["mmsi"],
                        "snapshot": snapshot,
                        "sha256": parameters["sha"],
                        "created_at": "2026-11-04T12:00:00Z",
                        "signed_at": None,
                        "signed_by": None,
                    }
                )
            )
        return []

    def commit(self):
        pass


class VesselLimitationsTests(unittest.TestCase):
    def test_report_calls_real_vessel_detail_before_hashing(self):
        ping = SimpleNamespace(mmsi=419007431, name="TEST", vessel_type="FISHING", length=20,
                               t=datetime(2026, 11, 4, 12), lat=8.9, lon=78.9, course=90, speed=1)
        explanation = SimpleNamespace(score=0.63, level="high", threshold=0.6, zone=None,
                                      factors=[], checks=[], clear_if={}, gaps=[], encounters=[])
        user = UserResponse(id="test-analyst-id", username="analyst_test", roles=[UserRole.ANALYST],
                            is_active=True, created_at=datetime.now(timezone.utc))
        with patch.object(vessels.fleet, "score_vessel", return_value=([ping], explanation)), \
             patch.object(vessels.risk_engine, "headline", return_value="Test"):
            result = reports.create_report(reports.CreateReport(mmsi=419007431), _analyst=user,
                                           _csrf=None, db=FakeDB())
        self.assertTrue(result["integrity_ok"])
        self.assertEqual(result["snapshot"]["limitations"], vessels.get_vessel_limitations())
        result["snapshot"]["limitations"][0]["detail"] = "altered"
        self.assertNotEqual(reports.digest(result["snapshot"]), result["sha256"])

    def test_vessel_limitations_returns_new_list_matching_b_shape(self):
        lim1 = vessels.get_vessel_limitations()
        lim2 = vessels.get_vessel_limitations()
        self.assertIsNot(lim1, lim2)
        self.assertEqual(len(lim1), 4)

        keys = [item["key"] for item in lim1]
        self.assertEqual(keys, ["source_mode", "indicators_not_proof", "boundaries", "heuristic_score"])

        for item in lim1:
            self.assertIn("key", item)
            self.assertIn("label", item)
            self.assertIn("detail", item)
            self.assertTrue(isinstance(item["key"], str) and item["key"])
            self.assertTrue(isinstance(item["label"], str) and item["label"])
            self.assertTrue(isinstance(item["detail"], str) and item["detail"])

    def test_get_vessel_includes_limitations_in_detail_response(self):
        fake_ping = SimpleNamespace(
            mmsi=419007431,
            name="SEA PEARL II",
            vessel_type="FISHING",
            length=23.4,
            t="2026-10-13T06:40:48",
            lat=8.9,
            lon=78.9,
            course=94.3,
            speed=0.8,
        )
        fake_exp = SimpleNamespace(
            score=0.63,
            level="high",
            threshold=0.6,
            zone={"name": "Gulf of Mannar", "relation": "inside", "distance_km": 0},
            factors=[],
            checks=[],
            clear_if={},
            gaps=[],
            encounters=[],
        )

        with patch.object(vessels.fleet, "score_vessel", return_value=([fake_ping], fake_exp)), \
             patch.object(vessels.fleet, "utcnow", return_value="2026-10-13T13:00:00Z"), \
             patch.object(vessels.risk_engine, "headline", return_value="Headline test"):
            detail = vessels.get_vessel(419007431, 24, db=FakeDB())

        self.assertIn("limitations", detail)
        self.assertEqual(len(detail["limitations"]), 4)
        self.assertEqual(detail["limitations"][0]["key"], "source_mode")
        self.assertIn("unknown", detail["limitations"][0]["detail"])

    def test_new_report_captures_limitations_in_hashed_snapshot(self):
        fake_detail = {
            "mmsi": 419007431,
            "name": "SEA PEARL II",
            "score": 0.63,
            "level": "high",
            "factors": [],
            "checks": [],
            "track": [],
            "limitations": vessels.get_vessel_limitations(),
        }
        mock_user = UserResponse(
            id="test-analyst-id",
            username="analyst_test",
            roles=[UserRole.ANALYST],
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        db = FakeDB()
        with patch.object(reports, "get_vessel", return_value=fake_detail):
            report_result = reports.create_report(
                request=reports.CreateReport(mmsi=419007431),
                _analyst=mock_user,
                _csrf=None,
                db=db,
            )

        # Report integrity matches
        self.assertTrue(report_result["integrity_ok"])
        self.assertIn("limitations", report_result["snapshot"])
        self.assertEqual(len(report_result["snapshot"]["limitations"]), 4)
        self.assertEqual(
            report_result["snapshot"]["limitations"][0]["key"],
            "source_mode",
        )

        # Verify that altering a limitation breaks the checksum
        tampered_snapshot = json.loads(json.dumps(report_result["snapshot"]))
        tampered_snapshot["limitations"][0]["detail"] = "Tampered detail"
        self.assertNotEqual(reports.digest(tampered_snapshot), report_result["sha256"])

        # Removing limitations also breaks the checksum
        del tampered_snapshot["limitations"]
        self.assertNotEqual(reports.digest(tampered_snapshot), report_result["sha256"])
