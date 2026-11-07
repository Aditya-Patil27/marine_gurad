"""Focused checks for persisted assessment mapping and access boundaries."""
import json
import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.api import assessments
from app.main import app
from app.services.risk_engine import Check, Explanation, Factor, Ping
from app.api.auth import get_current_user
from app.models.user import UserRole
from app.database import get_db


def test_sync_persists_actual_zone_factors_and_utc_timestamp():
    class DB:
        def __init__(self):
            self.params = []
            self.commits = 0

        def execute(self, statement, params):
            self.params.append(params)

        def commit(self):
            self.commits += 1

    db = DB()
    ping = Ping(123456789, datetime(2026, 1, 1, 6, tzinfo=timezone(timedelta(hours=2))), 8, 78)
    explanation = Explanation(
        mmsi=ping.mmsi, score=0.31, level="medium", threshold=0.6,
        factors=[Factor("ais_gap", "Gap", "A gap", 0.31, 0.31, {"hours": 6})],
        checks=[Check("weather", "Weather", "not_checked", "Unknown")],
        clear_if=None, zone={"name": "Park", "inside": True}, gaps=[], encounters=[],
    )
    with patch.object(assessments.fleet, "score_fleet", return_value=[([ping], explanation)]):
        for _ in range(2):
            result = assessments.sync_assessments(assessments.SyncRequest(), db=db)
    first, second = db.params
    assert first["id"] == second["id"]
    assert first["score"] == result.synced * 0.31
    assert json.loads(first["zone"]) == explanation.zone
    assert json.loads(first["factors"])[0]["evidence"] == {"hours": 6}
    assert first["last_seen"].hour == 4
    assert db.commits == 2


def test_anonymous_assessments_are_denied():
    with TestClient(app) as client:
        assert client.get("/api/v1/alerts/assessments").status_code == 401
        assert client.post("/api/v1/alerts/assessments/sync", json={}).status_code == 401


def test_sync_requires_analyst_and_csrf():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(roles=[UserRole.VIEWER])
    try:
        with TestClient(app) as client:
            assert client.post("/api/v1/alerts/assessments/sync", json={}).status_code == 403
            app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(roles=[UserRole.ANALYST])
            assert client.post("/api/v1/alerts/assessments/sync", json={}).status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="requires migrated disposable TEST_DATABASE_URL")
def test_database_upsert_reuses_id_and_serializes_real_gap():
    from app.services import risk_engine

    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    now = datetime.utcnow()
    ping = Ping(123456789, now - timedelta(minutes=30), 8.0, 78.0)
    latest = Ping(123456789, now, 9.0, 78.0)
    explanation = risk_engine.explain([ping, latest], [ping, latest], [], now)
    assert explanation.factors and isinstance(explanation.factors[0].evidence["from"], datetime)
    try:
        with Session(engine) as db, patch.object(assessments.fleet, "score_fleet", return_value=[([ping, latest], explanation)]):
            assessments.sync_assessments(assessments.SyncRequest(), db=db)
            first = db.execute(text("SELECT id, factors FROM vessel_assessments")).one()
            stored_window = db.execute(
                text("SELECT window_mode, window_start, window_end FROM vessel_assessments")
            ).one()
            assert stored_window.window_mode == "rolling"
            assert stored_window.window_start is not None and stored_window.window_end is not None
            assessments.sync_assessments(assessments.SyncRequest(), db=db)
            rows = db.execute(text("SELECT id, factors FROM vessel_assessments")).all()
            assert len(rows) == 1 and rows[0].id == first.id
            assert rows[0].factors[0]["evidence"]["from"].endswith("+00:00")
            app.dependency_overrides[get_db] = lambda: db
            app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(roles=[UserRole.VIEWER])
            try:
                with TestClient(app) as client:
                    response = client.get("/api/v1/alerts/assessments?limit=1&offset=0")
                    assert response.status_code == 200
                    body = response.json()
                    assert body["assessments"][0]["id"] == str(first.id)
                    assert body["assessments"][0]["window"]["mode"] == "rolling"
                    assert body["assessments"][0]["window"]["start"]
                    assert body["assessments"][0]["window"]["end"]
                    assert client.get("/api/v1/alerts/assessments?limit=101").status_code == 422
                    assert client.post("/api/v1/alerts/assessments/sync", json={}).status_code == 403
                    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(roles=[UserRole.ANALYST])
                    assert client.post("/api/v1/alerts/assessments/sync", json={}).status_code == 403
                    client.cookies.set("samudra_csrf", "test-csrf")
                    response = client.post("/api/v1/alerts/assessments/sync", json={}, headers={"X-CSRF-Token": "test-csrf"})
                    assert response.status_code == 200 and response.json()["synced"] == 1
                    assert db.execute(text("SELECT count(*) FROM vessel_assessments")).scalar() == 1
            finally:
                app.dependency_overrides.pop(get_db, None)
                app.dependency_overrides.pop(get_current_user, None)
    finally:
        engine.dispose()
