"""Exact-window alert generation against a migrated disposable database (A1).

Requires ``TEST_DATABASE_URL``. Proves the generator reads only rows inside the
selected UTC span and keeps the legacy rolling scan when no window is given.
"""
import os
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.services.alert_generator import AlertGenerator
from app.services.fleet import FleetWindow

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="requires migrated disposable TEST_DATABASE_URL",
)

MMSI_INSIDE = 920000301
MMSI_OUTSIDE = 920000302
MPA_NAME = "A1 window integration MPA"
POLY = "POLYGON((78.85 8.85, 78.95 8.85, 78.95 8.95, 78.85 8.95, 78.85 8.85))"

WINDOW = FleetWindow(
    "historical", datetime(2026, 10, 31), datetime(2026, 11, 2), 48
)


def _utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


TRACKS = [
    # Before the exclusive start; must not be selected.
    (MMSI_INSIDE, _utc(2026, 10, 30, 23, 0)),
    # Latest inside the window for the inside vessel.
    (MMSI_INSIDE, _utc(2026, 10, 31, 22, 0)),
    # After the inclusive end; must not be selected.
    (MMSI_INSIDE, _utc(2026, 11, 2, 0, 30)),
    # Another vessel only outside the window.
    (MMSI_OUTSIDE, _utc(2026, 11, 2, 0, 30)),
]


def _cleanup(engine):
    with Session(engine) as db:
        db.execute(
            text("DELETE FROM vessel_tracks WHERE mmsi = ANY(:mmsis)"),
            {"mmsis": [MMSI_INSIDE, MMSI_OUTSIDE]},
        )
        db.execute(
            text("DELETE FROM marine_protected_areas WHERE name = :name"),
            {"name": MPA_NAME},
        )
        db.commit()


def test_generator_selects_only_the_explicit_window():
    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    try:
        _cleanup(engine)
        with Session(engine) as db:
            db.execute(
                text(
                    "INSERT INTO marine_protected_areas (name, boundary) "
                    "VALUES (:name, ST_GeomFromText(:poly, 4326))"
                ),
                {"name": MPA_NAME, "poly": POLY},
            )
            for mmsi, observed in TRACKS:
                db.execute(
                    text(
                        "INSERT INTO vessel_tracks "
                        "(mmsi, timestamp, location, risk_score, source, source_mode) "
                        "VALUES (:mmsi, :at, ST_SetSRID(ST_MakePoint(78.9, 8.9), 4326), "
                        "0.9, 'A1 integration test', 'synthetic')"
                    ),
                    {"mmsi": mmsi, "at": observed},
                )
            db.commit()

            generated = AlertGenerator(db).check_mpa_violations(window=WINDOW)
            assert [alert["mmsi"] for alert in generated] == [MMSI_INSIDE]
            assert generated[0]["type"] == "MPA_VIOLATION"
            assert generated[0]["timestamp"].replace(tzinfo=None) == datetime(2026, 10, 31, 22, 0)
            assert generated[0]["source_mode"] == "synthetic"
            assert generated[0]["source"] == "A1 integration test"

            # Without a window the legacy last-hour scan returns nothing for these
            # old stored observations instead of falling back to another span.
            assert AlertGenerator(db).check_mpa_violations() == []
    finally:
        _cleanup(engine)
        engine.dispose()
