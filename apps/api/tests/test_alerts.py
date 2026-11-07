"""Focused checks for the stable, deduplicated legacy alert projection."""
from datetime import datetime, timezone
from unittest.mock import patch

from app.api import alerts

OBSERVED = datetime(2026, 11, 6, 10, 30, tzinfo=timezone.utc)


def _row(**overrides):
    base = {
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
        "timestamp": OBSERVED,
        "source": "local demo seed",
        "source_mode": "synthetic",
        "vessel_type": "FISHING",
    }
    base.update(overrides)
    return base


def _run(rows, severity=None, limit=50):
    class Generator:
        def __init__(self, _db):
            pass

        def check_mpa_violations(self):
            return [dict(row) for row in rows]

    with patch.object(alerts, "AlertGenerator", Generator):
        return alerts.get_alerts(limit=limit, severity=severity, db=None)


def test_ids_and_timestamps_are_stable_across_reads():
    first = _run([_row()])
    second = _run([_row()])
    assert first[0]["id"] == second[0]["id"]
    assert first[0]["timestamp"] == OBSERVED
    assert first[0]["timestamp"] == second[0]["timestamp"]


def test_different_vessel_or_zone_gets_a_different_id():
    ids = {item["id"] for item in _run([
        _row(),
        _row(mmsi=419007432),
        _row(mpa_id=8, mpa_name="Another park"),
    ])}
    assert len(ids) == 3


def test_duplicate_rows_collapse_and_keep_highest_severity():
    result = _run([
        _row(severity="medium", risk_score=0.4),
        _row(severity="critical", risk_score=0.72),
    ])
    assert len(result) == 1
    assert result[0]["severity"] == "HIGH"
    assert result[0]["metadata"]["risk_score"] == 0.72


def test_provenance_and_ephemeral_lifecycle_are_explicit():
    result = _run([_row()])
    metadata = result[0]["metadata"]
    assert metadata["source"] == "local demo seed"
    assert metadata["source_mode"] == "synthetic"
    assert metadata["persisted"] is False
    assert metadata["lifecycle"] == "ephemeral_projection"


def test_severity_filter_and_limit_are_preserved():
    rows = [
        _row(mmsi=419007431),
        _row(mmsi=419007432, type="MPA_APPROACH", severity="medium", risk_score=0.35),
    ]
    high = _run(rows, severity="HIGH")
    assert len(high) == 1
    assert high[0]["type"] == "MPA_VIOLATION"
    assert len(_run(rows, limit=1)) == 1


def test_response_keeps_existing_shape():
    item = _run([_row()])[0]
    assert set(item) == {"id", "type", "severity", "title", "description", "timestamp", "location", "metadata"}
    assert item["location"] == {"lat": 8.9, "lon": 78.9}
    assert item["metadata"]["mpa_name"] == "Gulf of Mannar"
