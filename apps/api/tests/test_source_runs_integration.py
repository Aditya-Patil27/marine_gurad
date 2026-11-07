"""Critical source-run persistence checks on a migrated disposable database."""
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api import auth as auth_api
from app.api import sources
from app.database import get_db
from app.models.user import UserRole
from app.schemas.user import UserResponse
from app.services import source_runs

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="requires migrated disposable TEST_DATABASE_URL"
)

START = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)
FINISH = START + timedelta(seconds=12)


def _analyst(request: Request) -> UserResponse:
    return UserResponse(
        id="00000000-0000-0000-0000-000000000001",
        username="analyst",
        is_active=True,
        created_at=START,
        roles=[UserRole.ANALYST],
    )


def _app(engine):
    app = FastAPI()
    app.include_router(sources.router, prefix="/api/v1/sources")

    def override_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[auth_api.get_current_user] = _analyst
    return app


def test_roundtrip_latest_run_and_constraints():
    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    try:
        with Session(engine) as db:
            ais = source_runs.insert_run(
                db,
                provider="aisstream",
                operation="ais_snapshot",
                status="succeeded",
                mode="live",
                started_at=START,
                finished_at=FINISH,
                request_count=1,
                position_count=2,
                checkpoint={"bounds_lat_lon": [[7.5, 77.0], [10.5, 81.0]]},
                triggered_by="analyst",
            )
            assert ais["position_count"] == 2
            assert ais["event_count"] is None
            assert ais["checkpoint"]["bounds_lat_lon"][0] == [7.5, 77.0]

            gfw = source_runs.insert_run(
                db,
                provider="gfw",
                operation="gfw_regional_events",
                status="empty",
                mode="historical",
                started_at=START + timedelta(minutes=1),
                finished_at=FINISH + timedelta(minutes=1),
                request_count=1,
                event_count=0,
                checkpoint={"start_date": "2026-10-01", "end_date_exclusive": "2026-10-15"},
                triggered_by="analyst",
            )
            assert gfw["event_count"] == 0

            latest = source_runs.latest_runs(db)
            assert latest["aisstream"]["id"] == ais["id"]
            assert latest["gfw"]["id"] == gfw["id"]
            assert "api_key" not in str(latest).lower()
            assert latest["aisstream"]["started_at"].endswith("+00:00")

            with pytest.raises(IntegrityError):
                source_runs.insert_run(
                    db,
                    provider="aisstream",
                    operation="ais_snapshot",
                    status="succeeded",
                    mode="live",
                    started_at=START,
                    finished_at=FINISH,
                    request_count=1,
                    position_count=1,
                    event_count=1,
                    triggered_by="analyst",
                )
            db.rollback()
    finally:
        engine.dispose()


def test_endpoint_persists_run_and_health_exposes_it():
    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    result = {
        "status": "available", "delivery": "live",
        "captured_at": "2026-11-06T12:00:00+00:00",
        "positions": [{"mmsi": 123456789, "latitude": 8.1, "longitude": 78.2}],
    }
    try:
        with patch.object(sources.aisstream, "collect_snapshot", AsyncMock(return_value=result)):
            with TestClient(_app(engine)) as client:
                response = client.post(
                    "/api/v1/sources/runs",
                    json={"provider": "aisstream", "max_positions": 5, "duration_seconds": 2},
                    headers={auth_api.CSRF_HEADER: "token"},
                    cookies={auth_api.CSRF_COOKIE: "token"},
                )
                assert response.status_code == 200, response.text
                run = response.json()["run"]
                assert run["status"] == "succeeded"
                assert run["position_count"] == 1

                health = client.get("/api/v1/sources/health")
                assert health.status_code == 200
                body = health.json()
                assert body["external_calls"] is False
                assert body["writes"] is False
                assert body["sources"]["aisstream"]["last_run"]["id"] == run["id"]
                assert body["sources"]["aisstream"]["availability"] == "not_checked"

        with Session(engine) as db:
            stored = source_runs.latest_runs(db)["aisstream"]
            assert stored["id"] == run["id"]
            assert stored["checkpoint"]["max_positions"] == 5
            assert "api_key" not in str(stored).lower()
    finally:
        with Session(engine) as db:
            db.execute(text("DELETE FROM source_runs WHERE triggered_by = 'analyst'"))
            db.commit()
        engine.dispose()


def test_rejected_window_is_persisted_and_returns_422():
    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    fetch = AsyncMock()
    try:
        with patch.object(sources.gfw, "fetch_regional_events", fetch):
            with TestClient(_app(engine)) as client:
                response = client.post(
                    "/api/v1/sources/runs",
                    json={
                        "provider": "gfw",
                        "start_date": "2026-09-01",
                        "end_date": "2026-10-15",
                        "offset": 0,
                        "limit": 20,
                    },
                    headers={auth_api.CSRF_HEADER: "token"},
                    cookies={auth_api.CSRF_COOKIE: "token"},
                )
                assert response.status_code == 422, response.text
                assert response.json()["detail"]["run"]["status"] == "rejected"
        fetch.assert_not_awaited()
        with Session(engine) as db:
            stored = source_runs.latest_runs(db).get("gfw")
            assert stored["status"] == "rejected"
            assert stored["request_count"] == 0
            assert stored["error_category"] == "validation"
    finally:
        with Session(engine) as db:
            db.execute(text("DELETE FROM source_runs WHERE triggered_by = 'analyst'"))
            db.commit()
        engine.dispose()


def test_provider_failure_is_recorded_without_secret_or_payload():
    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    try:
        with patch.object(
            sources.gfw, "fetch_regional_events",
            AsyncMock(side_effect=HTTPException(503, "Global Fishing Watch token is not configured")),
        ):
            with TestClient(_app(engine)) as client:
                response = client.post(
                    "/api/v1/sources/runs",
                    json={
                        "provider": "gfw",
                        "start_date": "2026-10-01",
                        "end_date": "2026-10-15",
                    },
                    headers={auth_api.CSRF_HEADER: "token"},
                    cookies={auth_api.CSRF_COOKIE: "token"},
                )
        assert response.status_code == 200
        run = response.json()["run"]
        assert run["status"] == "unavailable"
        assert run["error_category"] == "config"
        assert run["event_count"] == 0
        assert len(run["error_message"]) <= source_runs.MAX_ERROR_MESSAGE
        assert "entries" not in str(run["checkpoint"]).lower()
        with Session(engine) as db:
            stored = source_runs.latest_runs(db).get("gfw")
            assert "entries" not in stored["checkpoint"]
    finally:
        with Session(engine) as db:
            db.execute(text("DELETE FROM source_runs WHERE triggered_by = 'analyst'"))
            db.commit()
        engine.dispose()
