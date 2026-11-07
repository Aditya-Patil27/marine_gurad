"""Mutation authorization for ingest, SAR and chat routes (A-002B).

These are no-database tests: the routers run against an in-memory DB stand-in
and a fake session user, so no provider, job or shared database is touched.
They assert that every mutation requires Analyst (Administrator implies it) and
a matching CSRF token, in that dependency order, before any business logic.
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from app.api import auth as auth_api
from app.api import chat, ingest, sar
from app.database import get_db
from app.models.user import UserRole
from app.schemas.user import UserResponse

ROLE_MAP = {
    "viewer1": [UserRole.VIEWER],
    "analyst1": [UserRole.ANALYST],
    "approver1": [UserRole.APPROVER],
    "admin1": [UserRole.ADMINISTRATOR],
}

AIS_BODY = {
    "records": [
        {
            "mmsi": 123456789,
            "latitude": 8.9,
            "longitude": 78.9,
            "timestamp": "2026-11-04T00:00:00Z",
        }
    ]
}
SATELLITE_BODY = {
    "image_url": "https://example.test/scene.png",
    "latitude": 8.9,
    "longitude": 78.9,
}
SAR_BODY = {
    "observed_at": "2026-11-04T00:00:00Z",
    "latitude": 8.9,
    "longitude": 78.9,
    "source": "fixture",
    "scene_id": "scene-1",
}
CHAT_BODY = {"message": "hello"}
RESET_BODY = {}

MUTATIONS = [
    ("/api/v1/ingest/ais", AIS_BODY),
    ("/api/v1/ingest/satellite-image", SATELLITE_BODY),
    ("/api/v1/sar/detections", SAR_BODY),
    ("/api/v1/chat/message", CHAT_BODY),
    ("/api/v1/chat/reset", RESET_BODY),
]


class _Row:
    def __init__(self, mapping):
        self._mapping = mapping


class _Result:
    def __init__(self, row):
        self._row = row

    def first(self):
        return self._row

    def one(self):
        return self._row


class _FakeDB:
    """Records every DB interaction so denied requests can be proven inert."""

    def __init__(self):
        self.calls = []
        self.added = []

    def add(self, obj):
        self.calls.append("add")
        self.added.append(obj)

    def commit(self):
        self.calls.append("commit")

    def rollback(self):
        self.calls.append("rollback")

    def execute(self, statement, parameters=None):
        self.calls.append("execute")
        if str(statement).lstrip().upper().startswith("SELECT"):
            return _Result(None)
        return _Result(
            _Row(
                {
                    "id": 1,
                    "observed_at": parameters["observed"],
                    "latitude": parameters["lat"],
                    "longitude": parameters["lon"],
                    "source": parameters["source"],
                    "scene_id": parameters["scene"],
                    "confidence": parameters["confidence"],
                    "matched_mmsi": None,
                    "match_distance_m": None,
                    "match_time_seconds": None,
                }
            )
        )


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


def _build_app(db):
    app = FastAPI()
    app.include_router(ingest.router, prefix="/api/v1/ingest")
    app.include_router(sar.router, prefix="/api/v1/sar")
    app.include_router(chat.router, prefix="/api/v1/chat")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[auth_api.get_current_user] = _fake_current_user
    return app


def _headers(user=None, token=None):
    value = {"X-Test-User": user} if user else {}
    if token:
        value[auth_api.CSRF_HEADER] = token
    return value


def _cookies(token=None):
    return {auth_api.CSRF_COOKIE: token} if token else {}


def _route_dependencies(method, path):
    from app.main import app

    route = next(
        item
        for item in app.routes
        if getattr(item, "path", None) == path and method in item.methods
    )
    return [dependency.call for dependency in route.dependant.dependencies]


def test_identity_dependencies_resolve_before_csrf():
    for path, _body in MUTATIONS:
        dependencies = _route_dependencies("POST", path)
        assert dependencies[0] is auth_api.require_analyst, path
        assert dependencies[1] is auth_api.csrf_protect, path


def test_mutation_routes_deny_without_business_side_effects():
    db = _FakeDB()
    app = _build_app(db)
    rescore = MagicMock()
    detector_cls = MagicMock()
    process = AsyncMock()

    with (
        patch.object(ingest, "rescore_all", rescore),
        patch.object(ingest, "PollutionDetector", detector_cls),
        patch.object(chat.mia, "process_message", process),
        TestClient(app) as client,
    ):
        for path, body in MUTATIONS:
            anonymous = client.post(path, json=body)
            assert anonymous.status_code == 401, (path, anonymous.text)

            for user in ("viewer1", "approver1"):
                denied = client.post(
                    path,
                    json=body,
                    headers=_headers(user, "token"),
                    cookies=_cookies("token"),
                )
                assert denied.status_code == 403, (path, user, denied.text)

            # Missing header, mismatched header and mismatched cookie are all 403.
            assert client.post(
                path, json=body, headers=_headers("analyst1"), cookies=_cookies("token")
            ).status_code == 403
            assert client.post(
                path,
                json=body,
                headers=_headers("analyst1", "wrong"),
                cookies=_cookies("token"),
            ).status_code == 403
            assert client.post(
                path,
                json=body,
                headers=_headers("analyst1", "token"),
                cookies=_cookies("wrong"),
            ).status_code == 403

    assert db.calls == []
    assert db.added == []
    rescore.assert_not_called()
    detector_cls.assert_not_called()
    process.assert_not_called()


def test_mutation_routes_admit_analyst_and_administrator():
    for user in ("analyst1", "admin1"):
        db = _FakeDB()
        app = _build_app(db)
        detector = MagicMock()
        detector.model = object()
        detector.detect_sync.return_value = []
        rescore = MagicMock(return_value=0)
        process = AsyncMock(
            return_value={
                "response": "ok",
                "tool_calls": [],
                "data_confidence": 50,
                "sources": [],
            }
        )

        with (
            patch.object(ingest, "rescore_all", rescore),
            patch.object(ingest, "PollutionDetector", return_value=detector),
            patch.object(chat.mia, "process_message", process),
            TestClient(app) as client,
        ):
            kwargs = {
                "headers": _headers(user, "token"),
                "cookies": _cookies("token"),
            }

            ais = client.post("/api/v1/ingest/ais", json=AIS_BODY, **kwargs)
            assert ais.status_code == 200, (user, ais.text)
            assert ais.json() == {
                "status": "success",
                "inserted": 1,
                "rescored": 0,
                "total": 1,
            }
            assert rescore.called

            satellite = client.post(
                "/api/v1/ingest/satellite-image", json=SATELLITE_BODY, **kwargs
            )
            assert satellite.status_code == 200, (user, satellite.text)
            assert satellite.json()["saved"] == 0

            detection = client.post(
                "/api/v1/sar/detections", json=SAR_BODY, **kwargs
            )
            assert detection.status_code == 201, (user, detection.text)
            assert (
                detection.json()["interpretation"]
                == "No nearby AIS candidate; coverage unknown"
            )

            message = client.post("/api/v1/chat/message", json=CHAT_BODY, **kwargs)
            assert message.status_code == 200, (user, message.text)
            assert message.json()["response"] == "ok"

            reset = client.post("/api/v1/chat/reset", json=RESET_BODY, **kwargs)
            assert reset.status_code == 200, (user, reset.text)
            assert reset.json()["status"] == "success"

            assert "add" in db.calls and "commit" in db.calls
            assert process.await_count == 1
