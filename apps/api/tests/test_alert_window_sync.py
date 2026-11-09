"""Focused checks for window-scoped stored-alert sync and screening wording (A1).

No database or provider is touched here; the SQL itself is exercised by the
disposable integration test.
"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api import alert_records, alerts
from app.services.fleet import FleetWindow

START = datetime(2026, 10, 31, 0, 0, tzinfo=timezone.utc)
END = datetime(2026, 11, 2, 0, 0, tzinfo=timezone.utc)
ANALYST = SimpleNamespace(username="analyst1")


def _row(**overrides):
    row = {
        "type": "MPA_VIOLATION",
        "severity": "critical",
        "mmsi": 419007431,
        "mpa_id": 7,
        "mpa_name": "Gulf of Mannar",
        "risk_score": 0.72,
        "lat": 8.9,
        "lon": 78.9,
        "distance_km": 0,
        "estimated_time": "Currently inside",
        "timestamp": datetime(2026, 11, 1, 9, 0),
        "source": "local demo seed",
        "source_mode": "synthetic",
        "vessel_type": "FISHING",
    }
    row.update(overrides)
    return row


class RecordingGenerator:
    windows = []
    rows = []

    def __init__(self, _db):
        pass

    def check_mpa_violations(self, window=None):
        type(self).windows.append(window)
        return [dict(row) for row in type(self).rows]


def _sync(db=None, payload=None):
    RecordingGenerator.windows = []
    with patch.object(alert_records, "AlertGenerator", RecordingGenerator):
        return alert_records.sync_alerts(
            payload=payload, _analyst=ANALYST, _csrf=None, db=db or MagicMock()
        )


def test_default_sync_keeps_legacy_last_hour_and_rolling_window():
    RecordingGenerator.rows = []
    response = _sync()
    assert RecordingGenerator.windows == [None]
    assert response.window["mode"] == "rolling"
    assert response.window["hours"] == 1
    assert response.observed == 0
    assert response.source_mode == "unknown"
    assert response.stored_scope == "global"


def test_historical_sync_passes_the_exact_window_and_echoes_it():
    RecordingGenerator.rows = []
    response = _sync(payload=alert_records.SyncRequest(
        lookback_hours=72, window_start=START, window_end=END,
    ))
    assert len(RecordingGenerator.windows) == 1
    window = RecordingGenerator.windows[0]
    assert isinstance(window, FleetWindow)
    assert window.mode == "historical"
    assert window.start == START.replace(tzinfo=None)
    assert window.end == END.replace(tzinfo=None)
    assert response.window["start"] == "2026-10-31T00:00:00Z"
    assert response.window["end"] == "2026-11-02T00:00:00Z"
    assert response.stored_scope == "global"


def test_explicit_rolling_lookback_is_passed_to_the_generator():
    RecordingGenerator.rows = []
    response = _sync(payload=alert_records.SyncRequest(lookback_hours=72))
    assert len(RecordingGenerator.windows) == 1
    window = RecordingGenerator.windows[0]
    assert isinstance(window, FleetWindow)
    assert window.mode == "rolling"
    assert window.hours == 72
    assert response.window["hours"] == 72


@pytest.mark.parametrize(
    "payload, message",
    [
        (alert_records.SyncRequest(window_start=START), "supplied together"),
        (alert_records.SyncRequest(
            window_start=datetime(2026, 10, 31), window_end=END,
        ), "explicit UTC offset"),
        (alert_records.SyncRequest(window_start=END, window_end=START), "after window_start"),
        (alert_records.SyncRequest(
            window_start=START, window_end=START + timedelta(hours=169),
        ), "must not exceed"),
        (alert_records.SyncRequest(
            window_start=datetime.now(timezone.utc) - timedelta(hours=1),
            window_end=datetime.now(timezone.utc) + timedelta(hours=1),
        ), "must not be in the future"),
        (alert_records.SyncRequest(lookback_hours=0), "lookback_hours"),
    ],
)
def test_invalid_or_partial_bounds_fail_before_the_generator(payload, message):
    RecordingGenerator.rows = []
    db = MagicMock()
    with pytest.raises(HTTPException) as error:
        _sync(db=db, payload=payload)
    assert error.value.status_code == 422
    assert message in error.value.detail
    assert RecordingGenerator.windows == []
    db.execute.assert_not_called()


def test_empty_window_is_a_zero_result_not_an_error():
    RecordingGenerator.rows = []
    response = _sync(payload=alert_records.SyncRequest(
        window_start=datetime(2026, 10, 1, tzinfo=timezone.utc),
        window_end=datetime(2026, 10, 2, tzinfo=timezone.utc),
    ))
    assert response.observed == 0
    assert response.created == 0
    assert response.window["mode"] == "historical"


def test_source_mode_comes_from_the_stored_row_not_provider_configuration():
    RecordingGenerator.rows = [_row(source_mode="synthetic")]
    db = MagicMock()
    db.execute.return_value.first.return_value = SimpleNamespace()
    response = _sync(db=db, payload=alert_records.SyncRequest(
        window_start=START, window_end=END,
    ))
    insert_params = db.execute.call_args_list[0].args[1]
    assert insert_params["source_mode"] == "synthetic"
    assert response.source_mode == "synthetic"

    RecordingGenerator.rows = [_row(source_mode=None)]
    db = MagicMock()
    db.execute.return_value.first.return_value = SimpleNamespace()
    response = _sync(db=db)
    insert_params = db.execute.call_args_list[0].args[1]
    assert insert_params["source_mode"] is None
    assert response.source_mode == "unknown"


def test_titles_and_descriptions_use_screening_language():
    violation = alerts.alert_title(_row())
    assert "Violation" not in violation
    assert "screening" in violation.lower()

    description = alerts.alert_description(_row())
    assert "not proof of illegal activity" in description
    assert "currently inside" not in description.lower()

    predicted = alerts.alert_description(_row(
        type="MPA_APPROACH_PREDICTED", severity="high", distance_km=4.2,
        estimated_time="2.0 hours",
    ))
    assert "not a confirmed course" in predicted
    assert "proof of illegal activity" in predicted

    approach = alerts.alert_description(_row(type="MPA_APPROACH", severity="medium", distance_km=4.2))
    assert "not proof of illegal activity" in approach
