"""Report weather context uses event-time model data and remains optional."""
import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest

from app.api import reports, weather


class FakeDB:
    def execute(self, statement, parameters):
        if "SELECT" in str(statement):
            return []
        snapshot = json.loads(parameters["snapshot"])
        row = {"snapshot": snapshot, "sha256": parameters["sha"]}
        return SimpleNamespace(one=lambda: SimpleNamespace(_mapping=row))

    def commit(self):
        pass


GAP = {"hours": 6, "start": datetime(2026, 11, 4, 8, 35), "lat": 8.9, "lon": 78.9}


def _context_with_gap():
    return ([], SimpleNamespace(gaps=[GAP]))


def test_weather_is_opt_in_and_hash_binds_snapshot():
    context = {"status": "available", "wind_kn": 12, "retrieved_at": "2026-11-04T12:00:00+00:00"}
    with patch.object(reports, "get_vessel", return_value={"mmsi": 123456789}), patch.object(
        reports, "event_weather_context", return_value=context
    ) as fetch:
        default = reports.create_report(reports.CreateReport(mmsi=123456789), db=FakeDB())
        assert "weather_context" not in default["snapshot"]
        fetch.assert_not_called()
        result = reports.create_report(
            reports.CreateReport(mmsi=123456789, include_weather_context=True), db=FakeDB()
        )
    assert result["integrity_ok"]
    assert "may differ" in result["snapshot"]["weather_context"]["association"]
    result["snapshot"]["weather_context"]["wind_kn"] = 13
    assert reports.digest(result["snapshot"]) != result["sha256"]


def test_event_weather_preserves_gap_time_and_provider_time(monkeypatch):
    monkeypatch.setattr(weather.fleet, "score_vessel", lambda *args: _context_with_gap())

    class Response:
        def __init__(self, body):
            self.body = body

        def raise_for_status(self):
            pass

        def json(self):
            return self.body

    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get(self, url, params):
            key = params["hourly"]
            return Response({"hourly": {"time": ["2026-11-04T09:00"], key: [12 if key == "wind_speed_10m" else 1.2]}})

    monkeypatch.setattr(weather.httpx, "Client", Client)
    result = weather.event_weather_context(None, 123456789)
    assert result["status"] == "available"
    assert datetime.fromisoformat(result["event_time_utc"]) == GAP["start"].replace(tzinfo=timezone.utc)
    assert result["time_utc"] == "2026-11-04T09:00Z"
    assert result["wave_time_utc"] == "2026-11-04T09:00Z"
    assert result["latitude"] == GAP["lat"]


@pytest.mark.parametrize("case", ["offline", "no_gap"])
def test_report_snapshot_retains_missing_weather_state(monkeypatch, case):
    monkeypatch.setattr(reports, "get_vessel", lambda *args: {"mmsi": 123456789})
    explanation = SimpleNamespace(gaps=[GAP] if case == "offline" else [])
    monkeypatch.setattr(weather.fleet, "score_vessel", lambda *args: ([], explanation))

    class OfflineClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            raise httpx.ConnectError("offline")

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(weather.httpx, "Client", OfflineClient)
    result = reports.create_report(
        reports.CreateReport(mmsi=123456789, include_weather_context=True), db=FakeDB()
    )
    context = result["snapshot"]["weather_context"]
    assert result["integrity_ok"]
    assert context["status"] == ("unavailable" if case == "offline" else "not_checked")
    assert "wind_kn" not in context
    if case == "offline":
        assert context["latitude"] == GAP["lat"]
        assert datetime.fromisoformat(context["event_time_utc"]) == GAP["start"].replace(tzinfo=timezone.utc)
