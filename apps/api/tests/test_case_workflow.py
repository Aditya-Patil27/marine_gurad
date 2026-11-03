import asyncio
import os
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from app.api import reports, weather


def test_snapshot_digest_is_order_independent_and_detects_changes():
    first = {"mmsi": 123456789, "factors": [{"points": 0.31}], "track": []}
    reordered = {"track": [], "factors": [{"points": 0.31}], "mmsi": 123456789}
    assert reports.digest(first) == reports.digest(reordered)
    reordered["factors"][0]["points"] = 0.1
    assert reports.digest(first) != reports.digest(reordered)


def test_weather_does_not_downgrade_when_provider_fails(monkeypatch):
    now = datetime.utcnow()
    explanation = SimpleNamespace(gaps=[{"hours": 6, "start": now - timedelta(hours=6), "lat": 8.9, "lon": 78.9}])
    monkeypatch.setattr(weather.fleet, "score_vessel", lambda *args: ([], explanation))

    class BrokenClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def get(self, *args, **kwargs):
            import httpx
            raise httpx.ConnectError("offline")

    monkeypatch.setattr(weather.httpx, "AsyncClient", BrokenClient)
    result = asyncio.run(weather.vessel_weather(123456789, None))
    assert result["status"] == "unavailable"
    assert "no alert was downgraded" in result["reason"]


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="requires a migrated test database with demo data")
def test_report_snapshot_signoff_and_tamper_detection():
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session
    from app.database import get_db
    from app.main import app

    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(bind=connection, join_transaction_mode="create_savepoint")
        app.dependency_overrides[get_db] = lambda: session
        try:
            with TestClient(app) as client:
                response = client.post("/api/v1/reports/", json={"mmsi": 419007431})
                assert response.status_code == 201, response.text
                created = response.json()
                assert created["integrity_ok"] and created["snapshot"]["track"]
                vessel = created["snapshot"]
                detection = {"observed_at": vessel["last_seen"], "latitude": vessel["position"]["lat"],
                             "longitude": vessel["position"]["lon"], "source": "test fixture", "scene_id": "test-scene"}
                sar = client.post("/api/v1/sar/detections", json=detection)
                assert sar.status_code == 201, sar.text
                assert sar.json()["matched_mmsi"] == vessel["mmsi"]
                with_sar = client.post("/api/v1/reports/", json={"mmsi": vessel["mmsi"]})
                assert with_sar.status_code == 201
                assert with_sar.json()["snapshot"]["sar_candidates"][0]["scene_id"] == "test-scene"
                detection.update(latitude=0, longitude=0)
                unmatched = client.post("/api/v1/sar/detections", json=detection)
                assert unmatched.status_code == 201 and unmatched.json()["matched_mmsi"] is None
                report_id = created["id"]
                assert client.post(f"/api/v1/reports/{report_id}/sign", json={"officer": "", "reviewed": True}).status_code == 422
                assert client.post(f"/api/v1/reports/{report_id}/sign", json={"officer": "Reviewer", "reviewed": False}).status_code == 400
                signed = client.post(f"/api/v1/reports/{report_id}/sign", json={"officer": "Reviewer", "reviewed": True})
                assert signed.status_code == 200 and signed.json()["signed_by"] == "Reviewer"
                assert client.post(f"/api/v1/reports/{report_id}/sign", json={"officer": "Reviewer", "reviewed": True}).status_code == 409
                connection.execute(text("UPDATE incident_reports SET sha256 = :hash WHERE id = :id"), {"hash": "0" * 64, "id": report_id})
                assert not next(r for r in client.get("/api/v1/reports/").json() if r["id"] == report_id)["integrity_ok"]
        finally:
            app.dependency_overrides.clear()
            session.close()
            transaction.rollback()
            engine.dispose()
