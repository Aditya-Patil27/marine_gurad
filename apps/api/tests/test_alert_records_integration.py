"""Durable alert-record checks against a migrated disposable database.

Requires ``TEST_DATABASE_URL``. Never uses the shared development database.
"""
import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api import alert_records, alerts

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="requires migrated disposable TEST_DATABASE_URL",
)

MMSIS = [920000001, 920000002]
BASE = datetime(2026, 11, 6, 10, 30)


def _make_row(**overrides):
    row = {
        "type": "MPA_VIOLATION",
        "severity": "high",
        "mmsi": MMSIS[0],
        "mpa_id": 7,
        "mpa_name": "Integration MPA",
        "risk_score": 0.7,
        "lat": 8.9,
        "lon": 78.9,
        "distance_km": 0,
        "estimated_time": "Currently inside",
        "timestamp": BASE,
        "source": "integration test",
        "source_mode": "synthetic",
        "vessel_type": "FISHING",
    }
    row.update(overrides)
    return row


def _sync(db, rows, payload=None):
    class Generator:
        def __init__(self, _db):
            pass

        def check_mpa_violations(self, window=None):
            return [dict(row) for row in rows]

    user = SimpleNamespace(username="analyst1")
    with patch.object(alert_records, "AlertGenerator", Generator):
        return alert_records.sync_alerts(payload=payload, _analyst=user, _csrf=None, db=db)


def _cleanup(engine):
    with Session(engine) as db:
        db.execute(
            text("DELETE FROM alert_records WHERE mmsi = ANY(:mmsi)"), {"mmsi": MMSIS + [920000009]}
        )
        db.commit()


def _record(db, record_id):
    return db.execute(
        text("SELECT * FROM alert_records WHERE id = :id"), {"id": str(record_id)}
    ).one()


def _event_count(db, record_id):
    return db.execute(
        text("SELECT count(*) FROM alert_events WHERE alert_id = :id"),
        {"id": str(record_id)},
    ).scalar_one()


def test_alert_record_constraints_are_bounded():
    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    try:
        _cleanup(engine)
        with Session(engine) as db:
            insert = text(
                """INSERT INTO alert_records (
                       id, type, severity, mmsi, zone_key, title, description,
                       first_observed_at, last_observed_at, location_lat, location_lon,
                       metadata, source, source_mode, status, version)
                   VALUES (
                       :id, 'MPA_VIOLATION', :severity, :mmsi, :zone, 'T', 'D',
                       :at, :at, :lat, :lon, '{}'::jsonb, 'integration test', :mode,
                       :status, 0)"""
            )
            with pytest.raises(IntegrityError):
                db.execute(insert, {
                    "id": str(uuid4()), "severity": "CRITICAL", "mmsi": MMSIS[0],
                    "zone": "7", "at": BASE, "lat": 8.9, "lon": 78.9,
                    "mode": "synthetic", "status": "open",
                })
            db.rollback()

            with pytest.raises(IntegrityError):
                db.execute(insert, {
                    "id": str(uuid4()), "severity": "HIGH", "mmsi": MMSIS[0],
                    "zone": "7", "at": BASE, "lat": 8.9, "lon": 78.9,
                    "mode": "believed-live", "status": "open",
                })
            db.rollback()

            with pytest.raises(IntegrityError):
                db.execute(insert, {
                    "id": str(uuid4()), "severity": "HIGH", "mmsi": MMSIS[0],
                    "zone": "7", "at": BASE, "lat": 8.9, "lon": None,
                    "mode": "synthetic", "status": "open",
                })
            db.rollback()

            with pytest.raises(IntegrityError):
                db.execute(insert, {
                    "id": str(uuid4()), "severity": "HIGH", "mmsi": MMSIS[0],
                    "zone": "7", "at": BASE, "lat": 91, "lon": 78.9,
                    "mode": "synthetic", "status": "open",
                })
            db.rollback()

            with pytest.raises(IntegrityError):
                db.execute(insert, {
                    "id": str(uuid4()), "severity": "HIGH", "mmsi": MMSIS[0],
                    "zone": "7", "at": BASE, "lat": 8.9, "lon": 78.9,
                    "mode": "synthetic", "status": "closed",
                })
            db.rollback()
    finally:
        _cleanup(engine)
        engine.dispose()


def test_window_scoped_sync_preserves_global_records_and_accepts_late_observations():
    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    payload = alert_records.SyncRequest(
        window_start=datetime(2026, 10, 31, tzinfo=timezone.utc),
        window_end=datetime(2026, 11, 2, tzinfo=timezone.utc),
    )
    try:
        _cleanup(engine)
        with Session(engine) as db:
            first = _sync(db, [_make_row(timestamp=datetime(2026, 11, 1, 9, 0))], payload)
            assert first.created == 1
            assert first.window["mode"] == "historical"
            assert first.window["start"] == "2026-10-31T00:00:00Z"
            assert first.stored_scope == "global"
            record_id = str(alerts.alert_id(_make_row()))
            stored = _record(db, record_id)
            assert stored.first_observed_at.replace(tzinfo=None) == datetime(2026, 11, 1, 9, 0)
            assert stored.last_observed_at.replace(tzinfo=None) == datetime(2026, 11, 1, 9, 0)
            assert _event_count(db, record_id) == 1

            # A late record inside the same window extends the first observation
            # backwards without moving the last observation or duplicating the row.
            late = _make_row(timestamp=datetime(2026, 10, 31, 22, 0))
            second = _sync(db, [late], payload)
            assert second.created == 0
            assert second.updated == 1
            extended = _record(db, record_id)
            assert extended.first_observed_at.replace(tzinfo=None) == datetime(2026, 10, 31, 22, 0)
            assert extended.last_observed_at.replace(tzinfo=None) == datetime(2026, 11, 1, 9, 0)

            repeated = _sync(db, [late], payload)
            assert repeated.unchanged == 1
            assert repeated.updated == 0
            assert _event_count(db, record_id) == 2

            user = SimpleNamespace(username="analyst1")
            alert_records.resolve_alert(
                UUID(record_id),
                alert_records.ResolveRequest(expected_version=0, note="checked"),
                user=user, _csrf=None, db=db,
            )
            after_resolve = _sync(db, [_make_row(timestamp=datetime(2026, 11, 1, 12, 0))], payload)
            assert after_resolve.skipped_resolved == 1
            assert _record(db, record_id).status == "resolved"
    finally:
        _cleanup(engine)
        engine.dispose()


def test_sync_dedup_idempotency_and_lifecycle():
    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    try:
        _cleanup(engine)
        user = SimpleNamespace(username="analyst1")
        duplicate = _make_row(severity="critical", risk_score=0.9)
        other = _make_row(
            mmsi=MMSIS[1], mpa_id=8, mpa_name="Second MPA", severity="medium",
            risk_score=0.4, source_mode="unknown",
        )

        with Session(engine) as db:
            first = _sync(db, [duplicate, _make_row(), other])
            assert first.observed == 2
            assert first.created == 2
            assert first.updated == 0
            assert first.unchanged == 0
            assert first.skipped_resolved == 0
            assert first.source_mode == "mixed"
            assert first.synced_at.tzinfo is not None

            record_id = str(alerts.alert_id(duplicate))
            stored = _record(db, record_id)
            assert stored.status == "open"
            assert stored.version == 0
            assert stored.severity == "HIGH"
            assert stored.source == "integration test"
            assert stored.source_mode == "synthetic"
            assert stored.metadata["risk_score"] == 0.9
            assert stored.metadata["persisted"] is True
            assert stored.first_observed_at.replace(tzinfo=None) == BASE
            assert _event_count(db, record_id) == 1

            # A repeated sync does not create duplicates or bump the version.
            second = _sync(db, [duplicate, _make_row(), other])
            assert second.created == 0
            assert second.updated == 0
            assert second.unchanged == 2
            assert _record(db, record_id).version == 0
            assert _event_count(db, record_id) == 1

            # A newer observation advances last_observed_at and appends one event.
            newer = dict(duplicate, timestamp=BASE + timedelta(hours=1))
            third = _sync(db, [newer, other])
            assert third.updated == 1
            assert third.unchanged == 1
            advanced = _record(db, record_id)
            assert advanced.last_observed_at.replace(tzinfo=None) == BASE + timedelta(hours=1)
            assert _event_count(db, record_id) == 2

            acknowledged = alert_records.acknowledge_alert(
                UUID(record_id), alert_records.TransitionRequest(expected_version=0),
                user=user, _csrf=None, db=db,
            )
            assert acknowledged["status"] == "acknowledged"
            assert acknowledged["version"] == 1
            assert acknowledged["acknowledged_by"] == "analyst1"
            assert [event["event"] for event in acknowledged["events"]][-1] == "acknowledged"

            # Status survives a later sync of the same condition.
            preserved = _sync(db, [newer, other])
            assert preserved.created == 0
            assert preserved.updated == 0
            assert _record(db, record_id).status == "acknowledged"

            with pytest.raises(Exception) as stale:
                alert_records.acknowledge_alert(
                    UUID(record_id), alert_records.TransitionRequest(expected_version=0),
                    user=user, _csrf=None, db=db,
                )
            assert getattr(stale.value, "status_code", None) == 409

            resolved = alert_records.resolve_alert(
                UUID(record_id),
                alert_records.ResolveRequest(expected_version=1, note="  Reviewed by analyst  "),
                user=user, _csrf=None, db=db,
            )
            assert resolved["status"] == "resolved"
            assert resolved["version"] == 2
            assert resolved["resolved_by"] == "analyst1"
            assert resolved["resolution_note"] == "Reviewed by analyst"

            # A resolved alert is never silently reopened by sync.
            latest = dict(duplicate, timestamp=BASE + timedelta(hours=2))
            skipped = _sync(db, [latest, other])
            assert skipped.skipped_resolved == 1
            assert skipped.unchanged == 1
            still_resolved = _record(db, record_id)
            assert still_resolved.status == "resolved"
            assert still_resolved.last_observed_at.replace(tzinfo=None) == BASE + timedelta(hours=1)

            reopened = alert_records.reopen_alert(
                UUID(record_id), alert_records.TransitionRequest(expected_version=2),
                user=user, _csrf=None, db=db,
            )
            assert reopened["status"] == "open"
            assert reopened["version"] == 3
            assert [event["event"] for event in reopened["events"]][-1] == "reopened"

            after_reopen = _sync(db, [dict(duplicate, timestamp=BASE + timedelta(hours=3)), other])
            assert after_reopen.created == 0
            assert after_reopen.updated == 1

            filtered = alert_records.list_stored_alerts(
                limit=10, offset=0, status_filter="open", severity="HIGH",
                mmsi=MMSIS[0], _viewer=user, db=db,
            )
            assert filtered["total"] == 1
            assert filtered["alerts"][0]["id"] == record_id
            assert filtered["limitation"]

            detail = alert_records.get_stored_alert(UUID(record_id), _viewer=user, db=db)
            assert detail["events"][0]["event"] == "created"
            assert len(detail["events"]) >= 5
    finally:
        _cleanup(engine)
        engine.dispose()
