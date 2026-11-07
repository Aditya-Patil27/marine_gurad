"""Critical provenance checks on a migrated disposable database."""
import os
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api import assessments
from app.services import fleet

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="requires migrated disposable TEST_DATABASE_URL"
)

MMSIS = [910000001, 910000002, 910000003]


def _insert_track(db, mmsi, when, mode, source="integration test"):
    db.execute(
        text(
            """
            INSERT INTO vessel_tracks (mmsi, timestamp, location, source, source_mode)
            VALUES (:mmsi, :t, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), :source, :mode)
            """
        ),
        {"mmsi": mmsi, "t": when, "lon": 78.2, "lat": 8.1, "source": source, "mode": mode},
    )


def _cleanup(engine):
    with Session(engine) as db:
        db.execute(text("DELETE FROM vessel_assessments WHERE mmsi = ANY(:mmsi)"), {"mmsi": MMSIS})
        db.execute(text("DELETE FROM vessel_tracks WHERE mmsi = ANY(:mmsi)"), {"mmsi": MMSIS})
        db.commit()


def test_track_defaults_and_constraints_are_conservative():
    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    try:
        _cleanup(engine)
        with Session(engine) as db:
            # A legacy/implicit writer omits provenance: it must stay unknown.
            db.execute(
                text(
                    """
                    INSERT INTO vessel_tracks (mmsi, timestamp, location)
                    VALUES (:mmsi, :t, ST_SetSRID(ST_MakePoint(78.2, 8.1), 4326))
                    """
                ),
                {"mmsi": MMSIS[0], "t": datetime.utcnow()},
            )
            db.commit()
            row = db.execute(
                text("SELECT source, source_mode FROM vessel_tracks WHERE mmsi = :mmsi"),
                {"mmsi": MMSIS[0]},
            ).one()
            assert row.source == "unknown"
            assert row.source_mode == "unknown"

            with pytest.raises(IntegrityError):
                _insert_track(db, MMSIS[0], datetime.utcnow(), "believed-live")
            db.rollback()

            with pytest.raises(IntegrityError):
                db.execute(
                    text(
                        """
                        INSERT INTO vessel_assessments (id, mmsi, rule_version, source_mode,
                            evaluated_at, lookback_hours, score, level, factors, checks, created_at, updated_at)
                        VALUES ('00000000-0000-0000-0000-0000000000aa'::uuid, :mmsi, 'v1', 'varies', now(), 24, 0, 'low',
                            '[]'::jsonb, '[]'::jsonb, now(), now())
                        """
                    ),
                    {"mmsi": MMSIS[0]},
                )
            db.rollback()
    finally:
        _cleanup(engine)
        engine.dispose()


def test_assessment_mode_is_derived_from_track_provenance():
    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    now = datetime.utcnow()
    try:
        _cleanup(engine)
        with Session(engine) as db:
            _insert_track(db, MMSIS[0], now - timedelta(minutes=10), "synthetic")
            _insert_track(db, MMSIS[0], now - timedelta(minutes=5), "synthetic")

            _insert_track(db, MMSIS[1], now - timedelta(minutes=10), "unknown")
            _insert_track(db, MMSIS[1], now - timedelta(minutes=5), "unknown")

            _insert_track(db, MMSIS[2], now - timedelta(minutes=10), "synthetic")
            _insert_track(db, MMSIS[2], now - timedelta(minutes=5), "unknown")
            _insert_track(db, MMSIS[2], now - timedelta(minutes=2), "unknown")
            db.commit()

            pings = fleet.load_pings(db, now - timedelta(hours=1), mmsi=MMSIS[2])
            assert {p.source_mode for p in pings} == {"synthetic", "unknown"}
            assert all(p.source == "integration test" for p in pings)

            expected = {MMSIS[0]: "synthetic", MMSIS[1]: "unknown", MMSIS[2]: "mixed"}
            for mmsi, mode in expected.items():
                result = assessments.sync_assessments(
                    assessments.SyncRequest(lookback_hours=24, mmsi=mmsi), db=db
                )
                assert result.synced == 1
                assert result.source_mode == mode

            rows = db.execute(
                text("SELECT id, mmsi, source_mode FROM vessel_assessments WHERE mmsi = ANY(:mmsi)"),
                {"mmsi": MMSIS},
            ).all()
            stored = {row.mmsi: row for row in rows}
            assert {mmsi: row.source_mode for mmsi, row in stored.items()} == expected
            for mmsi, mode in expected.items():
                assert str(stored[mmsi].id) == str(
                    assessments.assessment_id(mmsi, assessments.RULE_VERSION, mode)
                )
    finally:
        _cleanup(engine)
        engine.dispose()
