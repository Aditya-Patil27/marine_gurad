"""Focused, no-network checks for truthful vessel provenance labelling."""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from app.api import assessments, auth as auth_api, ingest, vessels
from app.database import get_db
from app.models.user import UserRole
from app.schemas.user import UserResponse

NOW = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)
RECORD = {
    "mmsi": 123456789,
    "latitude": 8.1,
    "longitude": 78.2,
    "timestamp": "2026-11-06T11:55:00Z",
}


def _ping(mode, source="test"):
    return SimpleNamespace(mmsi=123456789, t=NOW, lat=8.0, lon=78.0, speed=1.0,
                           course=90.0, name="TEST", vessel_type="FISHING", length=20.0,
                           source=source, source_mode=mode)


class _DB:
    def __init__(self):
        self.added = []
        self.commits = 0

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commits += 1


def _analyst(request: Request) -> UserResponse:
    if not request.headers.get("X-Test-User"):
        raise HTTPException(401, "Not authenticated")
    return UserResponse(
        id="00000000-0000-0000-0000-000000000001",
        username="analyst1",
        is_active=True,
        created_at=NOW,
        roles=[UserRole.ANALYST],
    )


def _app(db):
    app = FastAPI()
    app.include_router(ingest.router, prefix="/api/v1/ingest")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[auth_api.get_current_user] = _analyst
    return app


def _post(client, body):
    return client.post(
        "/api/v1/ingest/ais",
        json=body,
        headers={auth_api.CSRF_HEADER: "token", "X-Test-User": "analyst1"},
        cookies={auth_api.CSRF_COOKIE: "token"},
    )


def test_derive_source_mode_single_unknown_and_mixed():
    assert assessments.derive_source_mode([_ping("synthetic"), _ping("synthetic")]) == "synthetic"
    assert assessments.derive_source_mode([_ping(None)]) == "unknown"
    assert assessments.derive_source_mode([]) == "unknown"
    assert assessments.derive_source_mode([_ping("synthetic"), _ping("unknown")]) == "mixed"


def test_response_mode_is_mixed_only_when_page_disagrees():
    assert assessments._response_source_mode([]) == "unknown"
    assert assessments._response_source_mode(["unknown", "unknown"]) == "unknown"
    assert assessments._response_source_mode(["synthetic", "synthetic"]) == "synthetic"
    assert assessments._response_source_mode(["synthetic", "unknown"]) == "mixed"


def test_ingest_defaults_to_caller_supplied_and_unknown():
    db = _DB()
    with patch.object(ingest, "rescore_all", return_value=0), TestClient(_app(db)) as client:
        response = _post(client, {"records": [RECORD]})
    assert response.status_code == 200, response.text
    assert len(db.added) == 1
    track = db.added[0]
    assert track.source == "caller-supplied AIS ingest"
    assert track.source_mode == "unknown"


def test_ingest_preserves_declared_provenance():
    db = _DB()
    body = {"records": [RECORD], "source": "unit-test fixture feed", "source_mode": "synthetic"}
    with patch.object(ingest, "rescore_all", return_value=0), TestClient(_app(db)) as client:
        response = _post(client, body)
    assert response.status_code == 200, response.text
    track = db.added[0]
    assert track.source == "unit-test fixture feed"
    assert track.source_mode == "synthetic"


def test_ingest_rejects_unknown_mode_vocabulary_before_write():
    db = _DB()
    body = {"records": [RECORD], "source_mode": "believed-live"}
    with patch.object(ingest, "rescore_all", return_value=0), TestClient(_app(db)) as client:
        response = _post(client, body)
    assert response.status_code == 422
    assert db.added == []


def test_ingest_still_requires_analyst_and_csrf():
    db = _DB()
    with patch.object(ingest, "rescore_all", return_value=0), TestClient(_app(db)) as client:
        assert client.post("/api/v1/ingest/ais", json={"records": [RECORD]}).status_code == 401


def test_vessel_summary_exposes_provenance_without_upgrading_unknown():
    ping = _ping("synthetic", source="local demo seed")
    explanation = SimpleNamespace(score=0.2, level="low", factors=[])
    with patch.object(vessels.risk_engine, "headline", return_value="Test"):
        summary = vessels._summary([ping], explanation)
    assert summary["source"] == "local demo seed"
    assert summary["source_mode"] == "synthetic"

    legacy = SimpleNamespace(mmsi=1, name="LEGACY", vessel_type=None, length=None, t=NOW,
                             lat=8.0, lon=78.0, course=None, speed=None)
    with patch.object(vessels.risk_engine, "headline", return_value="Test"):
        summary = vessels._summary([legacy], explanation)
    assert summary["source"] is None
    assert summary["source_mode"] is None
