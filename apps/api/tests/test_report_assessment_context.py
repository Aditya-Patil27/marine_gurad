"""An explicitly selected assessment is included in the hashed snapshot."""
import json
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from app.api import reports


def test_report_captures_selected_assessment_and_detects_changes():
    aid = uuid4()
    class DB:
        def execute(self, statement, params):
            sql = str(statement)
            if "FROM vessel_assessments" in sql:
                row = SimpleNamespace(_mapping={"id": aid, "mmsi": params["mmsi"], "score": 0.31,
                    "lookback_hours": 168, "window_mode": None, "window_start": None,
                    "window_end": None,
                    "evaluated_at": datetime(2026, 1, 1, tzinfo=timezone.utc), "factors": []})
                return SimpleNamespace(first=lambda: row)
            if "sar_detections" in sql:
                return []
            snapshot = json.loads(params["snapshot"])
            return SimpleNamespace(one=lambda: SimpleNamespace(_mapping={"snapshot": snapshot, "sha256": params["sha"]}))
        def commit(self):
            pass
    with patch.object(reports, "get_vessel", return_value={"mmsi": 123456789}):
        result = reports.create_report(reports.CreateReport(mmsi=123456789, assessment_id=aid), db=DB())
    assessment = result["snapshot"]["persisted_assessment"]
    assert assessment["id"] == str(aid) and assessment["score"] == 0.31
    assert result["integrity_ok"]
    assessment["score"] = 0.9
    assert reports.digest(result["snapshot"]) != result["sha256"]


def test_unknown_or_wrong_vessel_assessment_fails_before_report_insert():
    class DB:
        def execute(self, statement, params):
            assert "FROM vessel_assessments" in str(statement)
            return SimpleNamespace(first=lambda: None)
    with patch.object(reports, "get_vessel", return_value={"mmsi": 123456789}):
        with pytest.raises(HTTPException) as exc:
            reports.create_report(reports.CreateReport(mmsi=123456789, assessment_id=uuid4()), db=DB())
    assert exc.value.status_code == 404
