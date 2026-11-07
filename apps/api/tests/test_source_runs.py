"""Focused, no-network checks for the protected bounded source-run trigger.

Provider adapters and persistence are patched: these tests assert the route
authorization order, bounded request shapes, run outcome mapping and that no
credential or raw provider payload is written to metadata.
"""
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from app.api import auth as auth_api
from app.api import sources
from app.database import get_db
from app.models.user import UserRole
from app.schemas.user import UserResponse

ROLE_MAP = {
    "viewer1": [UserRole.VIEWER],
    "analyst1": [UserRole.ANALYST],
    "admin1": [UserRole.ADMINISTRATOR],
}

AIS_BODY = {"provider": "aisstream", "max_positions": 10, "duration_seconds": 3}
GFW_BODY = {
    "provider": "gfw",
    "start_date": (date(2026, 10, 1)).isoformat(),
    "end_date": (date(2026, 10, 15)).isoformat(),
    "offset": 0,
    "limit": 20,
}


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
    app.include_router(sources.router, prefix="/api/v1/sources")
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


def _recorded(insert_mock):
    assert insert_mock.call_count == 1
    return insert_mock.call_args.kwargs


def _fake_run(_db=None, **kwargs):
    return {
        key: (value.isoformat() if isinstance(value, datetime) else value)
        for key, value in {"id": 1, **kwargs}.items()
    }


@pytest.fixture
def insert_run():
    with patch.object(sources.run_store, "insert_run", side_effect=_fake_run) as mock:
        yield mock


def test_route_requires_analyst_then_csrf():
    from app.main import app

    route = next(
        item
        for item in app.routes
        if getattr(item, "path", None) == "/api/v1/sources/runs" and "POST" in item.methods
    )
    dependencies = [dependency.call for dependency in route.dependant.dependencies]
    assert dependencies[0] is auth_api.require_analyst
    assert dependencies[1] is auth_api.csrf_protect


def test_denies_before_any_provider_call_or_write(insert_run):
    collect = AsyncMock()
    fetch = AsyncMock()
    with (
        patch.object(sources.aisstream, "collect_snapshot", collect),
        patch.object(sources.gfw, "fetch_regional_events", fetch),
        TestClient(_build_app()) as client,
    ):
        assert client.post("/api/v1/sources/runs", json=AIS_BODY).status_code == 401
        for user in ("viewer1",):
            denied = client.post(
                "/api/v1/sources/runs", json=AIS_BODY,
                headers=_headers(user, "token"), cookies=_cookies("token"),
            )
            assert denied.status_code == 403
        assert client.post(
            "/api/v1/sources/runs", json=AIS_BODY,
            headers=_headers("analyst1"), cookies=_cookies("token"),
        ).status_code == 403
        assert client.post(
            "/api/v1/sources/runs", json=AIS_BODY,
            headers=_headers("analyst1", "wrong"), cookies=_cookies("token"),
        ).status_code == 403

    collect.assert_not_awaited()
    fetch.assert_not_awaited()
    insert_run.assert_not_called()


@pytest.mark.parametrize("user", ["analyst1", "admin1"])
def test_ais_success_persists_safe_metadata(user, insert_run):
    result = {
        "status": "available", "delivery": "live",
        "captured_at": "2026-11-06T12:00:00+00:00",
        "positions": [{"mmsi": 123456789, "latitude": 8.1, "longitude": 78.2}],
    }
    collect = AsyncMock(return_value=result)
    with (
        patch.object(sources.aisstream, "collect_snapshot", collect),
        TestClient(_build_app()) as client,
    ):
        response = client.post(
            "/api/v1/sources/runs", json=AIS_BODY,
            headers=_headers(user, "token"), cookies=_cookies("token"),
        )

    assert response.status_code == 200, response.text
    collect.assert_awaited_once_with(max_positions=10, duration_seconds=3, use_cache=False)
    kwargs = _recorded(insert_run)
    assert kwargs["provider"] == "aisstream"
    assert kwargs["operation"] == "ais_snapshot"
    assert kwargs["mode"] == "live"
    assert kwargs["status"] == "succeeded"
    assert kwargs["position_count"] == 1
    assert kwargs.get("event_count") is None
    assert kwargs["request_count"] == 1
    assert kwargs.get("error_category") is None
    assert kwargs["triggered_by"] == user
    assert "api_key" not in str(kwargs).lower()


def test_ais_opt_in_persistence_writes_only_validated_snapshot_positions(insert_run):
    result = {
        "status": "available", "delivery": "live",
        "captured_at": "2026-11-07T12:00:00+00:00",
        "positions": [{"mmsi": 123456789, "latitude": 8.1, "longitude": 78.2}],
    }
    persist = MagicMock(return_value=1)
    body = {**AIS_BODY, "persist_positions": True}
    with (
        patch.object(sources.aisstream, "collect_snapshot", AsyncMock(return_value=result)),
        patch.object(sources, "persist_live_ais_positions", persist),
        patch.object(sources.settings, "AISSTREAM_PERSIST_ENABLED", True),
        TestClient(_build_app()) as client,
    ):
        response = client.post(
            "/api/v1/sources/runs", json=body,
            headers=_headers("analyst1", "token"), cookies=_cookies("token"),
        )

    assert response.status_code == 200, response.text
    persist.assert_called_once()
    assert _recorded(insert_run)["checkpoint"]["persisted_positions"] == 1


def test_ais_default_run_never_persists_positions(insert_run):
    result = {"status": "available", "delivery": "live", "positions": []}
    persist = MagicMock()
    with (
        patch.object(sources.aisstream, "collect_snapshot", AsyncMock(return_value=result)),
        patch.object(sources, "persist_live_ais_positions", persist),
        TestClient(_build_app()) as client,
    ):
        response = client.post(
            "/api/v1/sources/runs", json=AIS_BODY,
            headers=_headers("analyst1", "token"), cookies=_cookies("token"),
        )

    assert response.status_code == 200
    persist.assert_not_called()


def test_ais_persistence_requires_explicit_retention_flag(insert_run):
    result = {"status": "available", "delivery": "live", "positions": [{"mmsi": 123456789}]}
    persist = MagicMock()
    with (
        patch.object(sources.aisstream, "collect_snapshot", AsyncMock(return_value=result)),
        patch.object(sources, "persist_live_ais_positions", persist),
        patch.object(sources.settings, "AISSTREAM_PERSIST_ENABLED", False),
        TestClient(_build_app()) as client,
    ):
        response = client.post(
            "/api/v1/sources/runs", json={**AIS_BODY, "persist_positions": True},
            headers=_headers("analyst1", "token"), cookies=_cookies("token"),
        )

    assert response.status_code == 200
    assert _recorded(insert_run)["status"] == "rejected"
    persist.assert_not_called()


def test_ais_empty_sample_is_empty_not_coverage(insert_run):
    result = {"status": "available", "delivery": "live", "positions": []}
    with (
        patch.object(sources.aisstream, "collect_snapshot", AsyncMock(return_value=result)),
        TestClient(_build_app()) as client,
    ):
        response = client.post(
            "/api/v1/sources/runs", json=AIS_BODY,
            headers=_headers("analyst1", "token"), cookies=_cookies("token"),
        )

    assert response.status_code == 200
    kwargs = _recorded(insert_run)
    assert kwargs["status"] == "empty"
    assert kwargs["position_count"] == 0


def test_ais_unavailable_is_recorded_without_provider_detail(insert_run):
    with (
        patch.object(
            sources.aisstream, "collect_snapshot",
            AsyncMock(side_effect=HTTPException(503, "AISStream credentials are not configured")),
        ),
        TestClient(_build_app()) as client,
    ):
        response = client.post(
            "/api/v1/sources/runs", json=AIS_BODY,
            headers=_headers("analyst1", "token"), cookies=_cookies("token"),
        )

    assert response.status_code == 200
    kwargs = _recorded(insert_run)
    assert kwargs["status"] == "unavailable"
    assert kwargs["error_category"] == "config"
    assert kwargs["position_count"] == 0


def test_gfw_success_uses_historical_mode_and_ignores_cache(insert_run):
    result = {
        "delivery": "live", "retrieved_at": "2026-11-06T12:00:00+00:00",
        "data": {"entries": [{"id": "event-1"}, {"id": "event-2"}], "total": 2},
    }
    fetch = AsyncMock(return_value=result)
    with (
        patch.object(sources.gfw, "fetch_regional_events", fetch),
        TestClient(_build_app()) as client,
    ):
        response = client.post(
            "/api/v1/sources/runs", json=GFW_BODY,
            headers=_headers("analyst1", "token"), cookies=_cookies("token"),
        )

    assert response.status_code == 200, response.text
    fetch.assert_awaited_once_with(date(2026, 10, 1), date(2026, 10, 15), 0, 20, use_cache=False)
    kwargs = _recorded(insert_run)
    assert kwargs["provider"] == "gfw"
    assert kwargs["operation"] == "gfw_regional_events"
    assert kwargs["mode"] == "historical"
    assert kwargs["status"] == "succeeded"
    assert kwargs["event_count"] == 2
    assert kwargs.get("position_count") is None
    assert kwargs["checkpoint"]["end_date_exclusive"] == "2026-10-15"


def test_gfw_empty_page_is_empty(insert_run):
    result = {"delivery": "live", "data": {"entries": [], "total": 0}}
    with (
        patch.object(sources.gfw, "fetch_regional_events", AsyncMock(return_value=result)),
        TestClient(_build_app()) as client,
    ):
        response = client.post(
            "/api/v1/sources/runs", json=GFW_BODY,
            headers=_headers("analyst1", "token"), cookies=_cookies("token"),
        )

    assert response.status_code == 200
    assert _recorded(insert_run)["status"] == "empty"


def test_unexpected_exception_is_failed_not_success(insert_run):
    with (
        patch.object(
            sources.gfw, "fetch_regional_events",
            AsyncMock(side_effect=RuntimeError("secret provider payload")),
        ),
        TestClient(_build_app()) as client,
    ):
        response = client.post(
            "/api/v1/sources/runs", json=GFW_BODY,
            headers=_headers("analyst1", "token"), cookies=_cookies("token"),
        )

    assert response.status_code == 200
    kwargs = _recorded(insert_run)
    assert kwargs["status"] == "failed"
    assert kwargs["error_category"] == "unknown"
    assert "secret provider payload" not in str(kwargs)


def test_gfw_provider_failure_is_unavailable(insert_run):
    with (
        patch.object(
            sources.gfw, "fetch_regional_events",
            AsyncMock(side_effect=HTTPException(503, "Global Fishing Watch quota is low; retry later")),
        ),
        TestClient(_build_app()) as client,
    ):
        response = client.post(
            "/api/v1/sources/runs", json=GFW_BODY,
            headers=_headers("analyst1", "token"), cookies=_cookies("token"),
        )

    assert response.status_code == 200
    kwargs = _recorded(insert_run)
    assert kwargs["status"] == "unavailable"
    assert kwargs["error_category"] == "quota"
    assert kwargs["event_count"] == 0


def test_gfw_window_over_31_days_is_rejected_before_provider_call(insert_run):
    fetch = AsyncMock()
    body = {
        "provider": "gfw",
        "start_date": "2026-09-01",
        "end_date": "2026-10-15",
        "offset": 0,
        "limit": 20,
    }
    with (
        patch.object(sources.gfw, "fetch_regional_events", fetch),
        TestClient(_build_app()) as client,
    ):
        response = client.post(
            "/api/v1/sources/runs", json=body,
            headers=_headers("analyst1", "token"), cookies=_cookies("token"),
        )

    assert response.status_code == 422
    fetch.assert_not_awaited()
    kwargs = _recorded(insert_run)
    assert kwargs["status"] == "rejected"
    assert kwargs["request_count"] == 0
    assert kwargs["error_category"] == "validation"


def test_health_embeds_last_run_but_stays_read_only():
    run = {"id": 7, "status": "empty", "started_at": "2026-11-06T12:00:00+00:00"}
    with (
        patch.object(sources, "prepared_sst_health", return_value={"status": "unavailable"}),
        patch.object(sources, "gfw_health", wraps=sources.gfw_health) as gfw_health,
        patch.object(sources, "aisstream_health", wraps=sources.aisstream_health) as ais_health,
        patch.object(sources, "open_meteo_health", return_value={"status": "not_checked"}),
        patch.object(sources, "replay_health", return_value={"status": "empty"}),
    ):
        result = sources.build_source_health(
            MagicMock(), datetime.now(timezone.utc),
            runs={"gfw": run, "aisstream": None},
        )

    assert result["external_calls"] is False
    assert result["writes"] is False
    assert gfw_health.call_args.args == (run,)
    assert ais_health.call_args.args == (None,)
