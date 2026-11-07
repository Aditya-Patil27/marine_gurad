"""Focused no-network checks for persistent alert records and lifecycle wiring."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from app.api import alert_records
from app.api import auth as auth_api
from app.database import get_db
from app.models.user import UserRole
from app.schemas.user import UserResponse

ROLE_MAP = {
    "viewer1": [UserRole.VIEWER],
    "analyst1": [UserRole.ANALYST],
    "admin1": [UserRole.ADMINISTRATOR],
}
ALERT_ID = "b2c3d4e5-f6a7-8901-bcde-f12345678901"


def _fake_current_user(request: Request) -> UserResponse:
    username = request.headers.get("X-Test-User")
    if not username:
        raise HTTPException(401, "Not authenticated")
    return UserResponse(
        id="00000000-0000-0000-0000-000000000001",
        username=username,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        roles=ROLE_MAP[username],
    )


def _build_app():
    app = FastAPI()
    app.include_router(alert_records.router, prefix="/api/v1/alerts")
    app.dependency_overrides[get_db] = lambda: MagicMock()
    app.dependency_overrides[auth_api.get_current_user] = _fake_current_user
    return app


def _headers(user="analyst1", token=None):
    value = {"X-Test-User": user} if user else {}
    if token:
        value[auth_api.CSRF_HEADER] = token
    return value


def _cookies(token=None):
    return {auth_api.CSRF_COOKIE: token} if token else {}


def test_as_utc_treats_naive_as_utc_and_never_guesses_elsewhere():
    naive = datetime(2026, 11, 6, 10, 30)
    assert alert_records.as_utc(naive) == datetime(2026, 11, 6, 10, 30, tzinfo=timezone.utc)
    shifted = datetime(2026, 11, 6, 12, 30, tzinfo=timezone(timedelta(hours=2)))
    assert alert_records.as_utc(shifted) == datetime(2026, 11, 6, 10, 30, tzinfo=timezone.utc)


def test_zone_and_mode_helpers_stay_conservative():
    assert alert_records.zone_key({"mpa_id": 7, "mpa_name": "x"}) == "7"
    assert alert_records.zone_key({"mpa_name": "Gulf of Mannar"}) == "Gulf of Mannar"
    assert alert_records.zone_key({}) == ""
    assert alert_records.mode_or_none({"source_mode": "synthetic"}) == "synthetic"
    assert alert_records.mode_or_none({"source_mode": "believed-live"}) is None
    assert alert_records.mode_or_none({}) is None
    assert alert_records.summary_mode([]) == "unknown"
    assert alert_records.summary_mode(["synthetic", "synthetic"]) == "synthetic"
    assert alert_records.summary_mode(["synthetic", "unknown"]) == "mixed"


def test_record_mapping_keeps_location_optional_and_marks_persisted():
    now = datetime(2026, 11, 6, 10, 30, tzinfo=timezone.utc)
    mapping = {
        "id": ALERT_ID,
        "type": "MPA_VIOLATION",
        "severity": "HIGH",
        "mmsi": 419007431,
        "mpa_id": 7,
        "mpa_name": "Gulf of Mannar",
        "title": "Title",
        "description": "Description",
        "first_observed_at": now,
        "last_observed_at": now,
        "location_lat": None,
        "location_lon": None,
        "metadata": {},
        "source": "local demo seed",
        "source_mode": "synthetic",
        "status": "open",
        "version": 0,
        "acknowledged_by": None,
        "acknowledged_at": None,
        "resolved_by": None,
        "resolved_at": None,
        "resolution_note": None,
        "created_at": now,
        "updated_at": now,
    }
    result = alert_records.record_to_dict(SimpleNamespace(_mapping=mapping))
    assert result["location"] == {}
    assert result["persisted"] is True
    assert result["lifecycle"] == "stored"
    assert result["id"] == ALERT_ID


def test_route_dependencies_require_analyst_then_csrf_for_mutations():
    from app.main import app

    paths = [
        "/api/v1/alerts/sync",
        "/api/v1/alerts/stored/{alert_id}/acknowledge",
        "/api/v1/alerts/stored/{alert_id}/resolve",
        "/api/v1/alerts/stored/{alert_id}/reopen",
    ]
    for path in paths:
        route = next(
            item
            for item in app.routes
            if getattr(item, "path", None) == path and "POST" in item.methods
        )
        dependencies = [dependency.call for dependency in route.dependant.dependencies]
        assert dependencies[0] is auth_api.require_analyst, path
        assert dependencies[1] is auth_api.csrf_protect, path


def test_read_routes_require_viewer():
    from app.main import app

    for path in ("/api/v1/alerts/stored", "/api/v1/alerts/stored/{alert_id}"):
        route = next(
            item
            for item in app.routes
            if getattr(item, "path", None) == path and "GET" in item.methods
        )
        dependencies = [dependency.call for dependency in route.dependant.dependencies]
        assert auth_api.require_viewer in dependencies, path


def test_sync_denial_happens_before_generator_or_database():
    generator = MagicMock()
    db = MagicMock()
    app = _build_app()
    app.dependency_overrides[get_db] = lambda: db
    with patch.object(alert_records, "AlertGenerator", generator), TestClient(app) as client:
        assert client.post("/api/v1/alerts/sync").status_code == 401
        assert client.post(
            "/api/v1/alerts/sync",
            headers=_headers("viewer1", "token"),
            cookies=_cookies("token"),
        ).status_code == 403
        assert client.post(
            "/api/v1/alerts/sync",
            headers=_headers("analyst1"),
            cookies=_cookies("token"),
        ).status_code == 403
    generator.assert_not_called()
    db.execute.assert_not_called()


def test_transition_denials_happen_before_database():
    db = MagicMock()
    app = _build_app()
    app.dependency_overrides[get_db] = lambda: db
    body = {"expected_version": 0}
    with TestClient(app) as client:
        for suffix in ("acknowledge", "resolve", "reopen"):
            path = f"/api/v1/alerts/stored/{ALERT_ID}/{suffix}"
            assert client.post(path, json=body).status_code == 401
            assert client.post(
                path, json=body,
                headers=_headers("viewer1", "token"), cookies=_cookies("token"),
            ).status_code == 403
            assert client.post(
                path, json=body,
                headers=_headers("analyst1"), cookies=_cookies("token"),
            ).status_code == 403
    db.execute.assert_not_called()


def test_filter_validation_rejects_unknown_vocabulary_before_query():
    with pytest.raises(HTTPException) as status_error:
        alert_records.list_stored_alerts(
            limit=10, offset=0, status_filter="closed", severity=None, mmsi=None,
            _viewer=None, db=MagicMock(),
        )
    assert status_error.value.status_code == 422

    with pytest.raises(HTTPException) as severity_error:
        alert_records.list_stored_alerts(
            limit=10, offset=0, status_filter=None, severity="CRITICAL", mmsi=None,
            _viewer=None, db=MagicMock(),
        )
    assert severity_error.value.status_code == 422


def test_stale_version_raises_conflict_without_update():
    row = SimpleNamespace(version=2, status="open", last_observed_at=datetime.now(timezone.utc))
    with pytest.raises(HTTPException) as error:
        alert_records._require_version(row, 1)
    assert error.value.status_code == 409
