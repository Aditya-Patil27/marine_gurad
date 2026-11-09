"""Focused contract checks for the additive v1 operational surfaces."""
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.api.ingest import AISBatch, AISRecord
from app.api.sar import Detection
from app.api.v1 import DeliveryRequest, ScanPlanRequest, SpillJobRequest, spill_capabilities


def ais_record(**changes):
    values = {
        "mmsi": 419000001,
        "latitude": 8.8,
        "longitude": 78.9,
        "timestamp": datetime(2026, 11, 9, tzinfo=timezone.utc),
    }
    values.update(changes)
    return AISRecord(**values)


def test_ais_batch_is_bounded_and_accepts_caller_record_identity():
    record = ais_record(source_record_id="provider-sequence-1")
    assert AISBatch(records=[record], source="fixture", source_mode="replay").records[0].source_record_id == "provider-sequence-1"
    with pytest.raises(ValidationError):
        AISBatch(records=[])
    with pytest.raises(ValidationError):
        AISBatch(records=[record] * 1001)


def test_sar_contract_requires_timezone_and_preserves_unknown_coverage():
    with pytest.raises(ValidationError):
        Detection(observed_at=datetime(2026, 11, 9), latitude=8.8, longitude=78.9,
                  source="permitted export", scene_id="scene-1")
    item = Detection(observed_at=datetime(2026, 11, 9, tzinfo=timezone.utc),
                     latitude=8.8, longitude=78.9, source="permitted export", scene_id="scene-1")
    assert item.coverage_status == "unknown"


def test_delivery_is_local_sink_only_and_idempotency_key_is_bounded():
    request = DeliveryRequest(expected_sha256="a" * 64, recipients=["reviewer@example.test"],
                              idempotency_key="report-9-v1")
    assert request.recipients == ["reviewer@example.test"]
    with pytest.raises(ValidationError):
        DeliveryRequest(expected_sha256="a" * 64, recipients=["person@example.com"],
                        idempotency_key="report-9-v1")


def test_scan_reserve_and_spill_bounds_are_explicit():
    assert ScanPlanRequest(budget=10).reserve_fraction == 0.2
    with pytest.raises(ValidationError):
        ScanPlanRequest(budget=10, reserve_fraction=0.1)
    with pytest.raises(ValidationError):
        SpillJobRequest(latitude=8.8, longitude=78.9,
                        release_at=datetime(2026, 11, 9, tzinfo=timezone.utc),
                        duration_hours=100, particle_count=500, mode="real")
    capability = spill_capabilities(None)
    assert capability["status"] == "unavailable"
    assert capability["forcing"]["current"] == "not_configured"
