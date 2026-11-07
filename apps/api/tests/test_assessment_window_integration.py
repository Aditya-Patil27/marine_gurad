"""Real sync-to-report window association on a migrated disposable database.

The in-memory shim in ``test_historical_window.py`` proves route logic; this
check proves that the persisted anchors survive a real upsert and that report
creation rejects mismatches before insertion. It never touches the shared DB:
it requires ``TEST_DATABASE_URL`` to name a migrated disposable database.
"""
import os
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.api import assessments, reports

MMSI = 999000001
SOURCE_MODE = "replay"
WINDOW_START = datetime(2026, 10, 31, 0, 0, tzinfo=timezone.utc)
WINDOW_END = datetime(2026, 11, 1, 23, 59, 59, tzinfo=timezone.utc)
OBSERVATIONS = [
    datetime(2026, 10, 31, 22, 0, tzinfo=timezone.utc),
    datetime(2026, 10, 31, 22, 30, tzinfo=timezone.utc),
    datetime(2026, 11, 1, 1, 0, tzinfo=timezone.utc),
]


def _seed_tracks(db: Session) -> None:
    db.execute(text("DELETE FROM incident_reports WHERE mmsi = :mmsi"), {"mmsi": MMSI})
    db.execute(text("DELETE FROM vessel_assessments WHERE mmsi = :mmsi"), {"mmsi": MMSI})
    db.execute(text("DELETE FROM vessel_tracks WHERE mmsi = :mmsi"), {"mmsi": MMSI})
    for index, observed_at in enumerate(OBSERVATIONS):
        db.execute(
            text(
                """
                INSERT INTO vessel_tracks (
                    mmsi, location, timestamp, speed, course,
                    vessel_name, length, source, source_mode
                ) VALUES (
                    :mmsi,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326),
                    :observed_at, 0.8, 94.0,
                    'WINDOW TEST', 23.4, 'focused test fixture', :source_mode
                )
                """
            ),
            {
                "mmsi": MMSI,
                "lon": 78.95 + index * 0.001,
                "lat": 8.90 + index * 0.001,
                "observed_at": observed_at,
                "source_mode": SOURCE_MODE,
            },
        )
    db.commit()


def _cleanup(engine) -> None:
    with Session(engine) as db:
        db.execute(text("DELETE FROM incident_reports WHERE mmsi = :mmsi"), {"mmsi": MMSI})
        db.execute(text("DELETE FROM vessel_assessments WHERE mmsi = :mmsi"), {"mmsi": MMSI})
        db.execute(text("DELETE FROM vessel_tracks WHERE mmsi = :mmsi"), {"mmsi": MMSI})
        db.commit()


def _report_count(db: Session) -> int:
    return db.execute(
        text("SELECT count(*) FROM incident_reports WHERE mmsi = :mmsi"),
        {"mmsi": MMSI},
    ).scalar()


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="requires migrated disposable TEST_DATABASE_URL",
)
def test_real_sync_to_report_binds_exact_window_and_rejects_mismatch():
    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    try:
        with Session(engine) as db:
            _seed_tracks(db)

            synced = assessments.sync_assessments(
                assessments.SyncRequest(
                    mmsi=MMSI,
                    window_start=WINDOW_START,
                    window_end=WINDOW_END,
                ),
                db=db,
            )
            assert synced.synced == 1
            row = db.execute(
                text(
                    """
                    SELECT id, window_mode, window_start, window_end, lookback_hours
                    FROM vessel_assessments WHERE mmsi = :mmsi
                    """
                ),
                {"mmsi": MMSI},
            ).one()
            assert row.window_mode == "historical"
            assert row.window_start == WINDOW_START
            assert row.window_end == WINDOW_END
            assert row.lookback_hours == 48
            assessment_id = row.id

            result = reports.create_report(
                reports.CreateReport(
                    mmsi=MMSI,
                    assessment_id=assessment_id,
                    window_start=WINDOW_START,
                    window_end=WINDOW_END,
                ),
                db=db,
            )
            persisted = result["snapshot"]["persisted_assessment"]
            assert persisted["window_match"] is True
            assert persisted["window"]["start"] == "2026-10-31T00:00:00Z"
            assert persisted["window"]["end"] == "2026-11-01T23:59:59Z"
            assert persisted["report_window"]["start"] == persisted["window"]["start"]
            assert persisted["report_window"]["end"] == persisted["window"]["end"]
            assert result["integrity_ok"]
            assert _report_count(db) == 1

            # Same duration, different anchors.
            shifted_start = WINDOW_START - timedelta(days=1)
            shifted_end = WINDOW_END - timedelta(days=1)
            with pytest.raises(HTTPException) as mismatch:
                reports.create_report(
                    reports.CreateReport(
                        mmsi=MMSI,
                        assessment_id=assessment_id,
                        window_start=shifted_start,
                        window_end=shifted_end,
                    ),
                    db=db,
                )
            assert mismatch.value.status_code == 409
            assert "different observation window" in mismatch.value.detail
            assert _report_count(db) == 1

            # A later sync replaces the same stable row with different anchors.
            assessments.sync_assessments(
                assessments.SyncRequest(
                    mmsi=MMSI,
                    window_start=shifted_start,
                    window_end=shifted_end,
                ),
                db=db,
            )
            with pytest.raises(HTTPException) as resynced:
                reports.create_report(
                    reports.CreateReport(
                        mmsi=MMSI,
                        assessment_id=assessment_id,
                        window_start=WINDOW_START,
                        window_end=WINDOW_END,
                    ),
                    db=db,
                )
            assert resynced.value.status_code == 409
            assert _report_count(db) == 1

            # Legacy row: duration retained, exact anchors unknown.
            db.execute(
                text(
                    """
                    UPDATE vessel_assessments
                    SET window_mode = NULL, window_start = NULL, window_end = NULL
                    WHERE id = :id
                    """
                ),
                {"id": assessment_id},
            )
            db.commit()
            with pytest.raises(HTTPException) as legacy:
                reports.create_report(
                    reports.CreateReport(
                        mmsi=MMSI,
                        assessment_id=assessment_id,
                        window_start=WINDOW_START,
                        window_end=WINDOW_END,
                    ),
                    db=db,
                )
            assert legacy.value.status_code == 409
            assert "no stored observation window anchors" in legacy.value.detail
            assert _report_count(db) == 1
    finally:
        _cleanup(engine)
        engine.dispose()
