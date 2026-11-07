"""Focused checks for bounded historical window selection (A-005B).

The integration-style check uses fixed observation dates from the prepared
replay and a later clock. It reads through the real vessel, assessment and
report code paths with an in-memory DB shim, so it demonstrates that one
selected window is used consistently without mutating source timestamps or
touching the shared database.
"""
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.api import assessments, reports, vessels
from app.services import fleet

MMSI = 419007431
SOURCE = "local demo seed"
SOURCE_MODE = "replay"

# Fixed observations prepared for the demo. The clock below is later than the
# window, so the default rolling filter would no longer reach them.
OBSERVATIONS = [
    datetime(2026, 10, 31, 22, 0),
    datetime(2026, 10, 31, 22, 30),
    datetime(2026, 11, 1, 1, 0),
]
WINDOW_START = datetime(2026, 10, 31, 0, 0, tzinfo=timezone.utc)
WINDOW_END = datetime(2026, 11, 1, 23, 59, 59, tzinfo=timezone.utc)
LATER = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)
# Later than the newest fixture (2026-11-01T01:00Z) plus 168 hours.
EXPIRED = datetime(2026, 11, 10, 0, 0, tzinfo=timezone.utc)
EMPTY_START = datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc)
EMPTY_END = datetime(2026, 10, 2, 0, 0, tzinfo=timezone.utc)


class FakeDB:
    """Minimal DB shim for the three read/write paths under test."""

    def __init__(self, observations=None):
        self.observations = observations if observations is not None else OBSERVATIONS
        self.ping_params = None
        self.assessment_params = None
        self.report_params = None
        self.commits = 0

    def _rows(self, params):
        since = params["since"]
        since = since.astimezone(timezone.utc).replace(tzinfo=None) if since.tzinfo else since
        until = params.get("until")
        until = until.astimezone(timezone.utc).replace(tzinfo=None) if until and until.tzinfo else until
        mmsi = params.get("mmsi")
        rows = []
        for index, observed_at in enumerate(self.observations):
            if observed_at <= since:
                continue
            if until is not None and observed_at > until:
                continue
            if mmsi is not None and mmsi != MMSI:
                continue
            rows.append(SimpleNamespace(
                mmsi=MMSI,
                timestamp=observed_at,
                lat=8.90 + index * 0.001,
                lon=78.95 + index * 0.001,
                speed=0.8,
                course=94.0,
                vessel_name="SEA PEARL II",
                vessel_type="FISHING",
                length=23.4,
                source=SOURCE,
                source_mode=SOURCE_MODE,
            ))
        return rows

    def execute(self, statement, params=None):
        sql = str(statement)
        params = params or {}
        if "FROM vessel_tracks" in sql:
            self.ping_params = params
            return self._rows(params)
        if "marine_protected_areas" in sql:
            return []
        if "INSERT INTO vessel_assessments" in sql:
            self.assessment_params = params
            return []
        if "FROM vessel_assessments" in sql:
            if self.assessment_params is None:
                return SimpleNamespace(first=lambda: None)
            p = self.assessment_params
            row = SimpleNamespace(_mapping={
                "id": p["id"],
                "mmsi": p["mmsi"],
                "rule_version": p["rule_version"],
                "source_mode": p["source_mode"],
                "evaluated_at": p["evaluated_at"],
                "lookback_hours": p["lookback_hours"],
                "score": p["score"],
                "level": p["level"],
                "factors": json.loads(p["factors"]),
                "checks": json.loads(p["checks"]),
                "zone": json.loads(p["zone"]) if p["zone"] else None,
                "headline": p["headline"],
                "window_mode": p["window_mode"],
                "window_start": p["window_start"],
                "window_end": p["window_end"],
            })
            return SimpleNamespace(first=lambda: row)
        if "sar_detections" in sql:
            return []
        if "INSERT INTO incident_reports" in sql:
            self.report_params = params
            snapshot = json.loads(params["snapshot"])
            return SimpleNamespace(one=lambda: SimpleNamespace(_mapping={
                "id": 1,
                "mmsi": params["mmsi"],
                "snapshot": snapshot,
                "sha256": params["sha"],
                "created_at": "2026-11-07T12:00:00Z",
                "signed_at": None,
                "signed_by": None,
            }))
        return []

    def commit(self):
        self.commits += 1


def assert_window(value, mode="historical", hours=48):
    assert value["mode"] == mode
    assert value["start"] == "2026-10-31T00:00:00Z"
    assert value["end"] == "2026-11-01T23:59:59Z"
    assert value["hours"] == hours
    assert value["utc"] is True
    assert value["end_inclusive"] is True
    assert value["max_hours"] == fleet.MAX_WINDOW_HOURS


def test_vessel_evidence_uses_fixed_window_and_preserves_dates_and_labels():
    detail = vessels.get_vessel(
        MMSI,
        168,
        FakeDB(),
        window_start=WINDOW_START,
        window_end=WINDOW_END,
    )

    assert_window(detail["window"])
    assert [point["t"] for point in detail["track"]] == [
        "2026-10-31T22:00:00Z",
        "2026-10-31T22:30:00Z",
        "2026-11-01T01:00:00Z",
    ]
    assert detail["last_seen"] == "2026-11-01T01:00:00Z"
    assert detail["source"] == SOURCE
    assert detail["source_mode"] == SOURCE_MODE


def test_assessment_sync_uses_same_window_and_keeps_original_last_seen():
    db = FakeDB()
    result = assessments.sync_assessments(
        assessments.SyncRequest(
            mmsi=MMSI,
            window_start=WINDOW_START,
            window_end=WINDOW_END,
        ),
        db=db,
    )

    assert result.synced == 1
    assert_window(result.window)
    assert result.lookback_hours == 48
    assert result.source_mode == SOURCE_MODE
    assert db.assessment_params["last_seen"] == datetime(2026, 11, 1, 1, 0, tzinfo=timezone.utc)
    assert db.assessment_params["lookback_hours"] == 48
    assert db.assessment_params["source_mode"] == SOURCE_MODE
    assert db.assessment_params["window_mode"] == "historical"
    assert db.assessment_params["window_start"] == WINDOW_START
    assert db.assessment_params["window_end"] == WINDOW_END
    assert db.commits == 1


def test_report_uses_same_window_and_hashes_original_observation_dates():
    result = reports.create_report(
        reports.CreateReport(
            mmsi=MMSI,
            window_start=WINDOW_START,
            window_end=WINDOW_END,
        ),
        db=FakeDB(),
    )

    snapshot = result["snapshot"]
    assert_window(snapshot["window"])
    assert [point["t"] for point in snapshot["track"]] == [
        "2026-10-31T22:00:00Z",
        "2026-10-31T22:30:00Z",
        "2026-11-01T01:00:00Z",
    ]
    assert snapshot["last_seen"] == "2026-11-01T01:00:00Z"
    assert snapshot["source"] == SOURCE
    assert snapshot["source_mode"] == SOURCE_MODE
    assert result["integrity_ok"]


def test_matching_historical_assessment_report_hashes_both_windows():
    db = FakeDB()
    assessments.sync_assessments(
        assessments.SyncRequest(mmsi=MMSI, window_start=WINDOW_START, window_end=WINDOW_END),
        db=db,
    )
    aid = assessments.assessment_id(MMSI, assessments.RULE_VERSION, SOURCE_MODE)

    result = reports.create_report(
        reports.CreateReport(
            mmsi=MMSI,
            assessment_id=aid,
            window_start=WINDOW_START,
            window_end=WINDOW_END,
        ),
        db=db,
    )

    persisted = result["snapshot"]["persisted_assessment"]
    assert persisted["window_match"] is True
    assert persisted["window"]["start"] == "2026-10-31T00:00:00Z"
    assert persisted["window"]["end"] == "2026-11-01T23:59:59Z"
    assert persisted["report_window"]["start"] == persisted["window"]["start"]
    assert persisted["report_window"]["end"] == persisted["window"]["end"]
    assert result["integrity_ok"]
    assert db.report_params is not None


def test_same_duration_different_anchor_report_rejected_before_insert():
    db = FakeDB()
    assessments.sync_assessments(
        assessments.SyncRequest(mmsi=MMSI, window_start=WINDOW_START, window_end=WINDOW_END),
        db=db,
    )
    aid = assessments.assessment_id(MMSI, assessments.RULE_VERSION, SOURCE_MODE)
    shifted_start = WINDOW_START - timedelta(days=1)
    shifted_end = WINDOW_END - timedelta(days=1)

    with pytest.raises(HTTPException) as exc:
        reports.create_report(
            reports.CreateReport(
                mmsi=MMSI,
                assessment_id=aid,
                window_start=shifted_start,
                window_end=shifted_end,
            ),
            db=db,
        )

    assert exc.value.status_code == 409
    assert "different observation window" in exc.value.detail
    assert "no report was created" in exc.value.detail
    assert db.report_params is None


def test_resync_to_another_window_rejected_before_insert():
    db = FakeDB()
    assessments.sync_assessments(
        assessments.SyncRequest(mmsi=MMSI, window_start=WINDOW_START, window_end=WINDOW_END),
        db=db,
    )
    aid = assessments.assessment_id(MMSI, assessments.RULE_VERSION, SOURCE_MODE)
    # A later sync replaces the same stable row with different anchors that
    # still contain an observation, so the upsert actually runs.
    assessments.sync_assessments(
        assessments.SyncRequest(
            mmsi=MMSI,
            window_start=WINDOW_START + timedelta(days=1),
            window_end=WINDOW_END + timedelta(days=1),
        ),
        db=db,
    )

    with pytest.raises(HTTPException) as exc:
        reports.create_report(
            reports.CreateReport(
                mmsi=MMSI,
                assessment_id=aid,
                window_start=WINDOW_START,
                window_end=WINDOW_END,
            ),
            db=db,
        )

    assert exc.value.status_code == 409
    assert db.report_params is None


def test_legacy_assessment_without_anchors_rejected_before_insert():
    db = FakeDB()
    assessments.sync_assessments(
        assessments.SyncRequest(mmsi=MMSI, window_start=WINDOW_START, window_end=WINDOW_END),
        db=db,
    )
    aid = assessments.assessment_id(MMSI, assessments.RULE_VERSION, SOURCE_MODE)
    # Simulate a pre-013 row: duration exists, exact anchors are unknown.
    db.assessment_params["window_mode"] = None
    db.assessment_params["window_start"] = None
    db.assessment_params["window_end"] = None

    with pytest.raises(HTTPException) as exc:
        reports.create_report(
            reports.CreateReport(
                mmsi=MMSI,
                assessment_id=aid,
                window_start=WINDOW_START,
                window_end=WINDOW_END,
            ),
            db=db,
        )

    assert exc.value.status_code == 409
    assert "no stored observation window anchors" in exc.value.detail
    assert db.report_params is None


def test_expired_rolling_lookup_is_empty_but_fixed_historical_succeeds():
    assert EXPIRED > OBSERVATIONS[-1].replace(tzinfo=timezone.utc) + timedelta(hours=168)

    rolling_db = FakeDB()
    pings, explanation = fleet.score_vessel(rolling_db, MMSI, hours=168, now=EXPIRED)
    assert pings is None and explanation is None

    window = fleet.resolve_window(start=WINDOW_START, end=WINDOW_END, now=EXPIRED)
    with patch.object(fleet.risk_engine, "explain", return_value=SimpleNamespace()) as explain:
        historical_db = FakeDB()
        pings, _ = fleet.score_vessel(historical_db, MMSI, window=window)

    assert [ping.t for ping in pings] == OBSERVATIONS
    # The scoring clock stays at the selected window end, not the later wall clock.
    assert explain.call_args.args[3] == window.end


def test_rolling_window_semantics_are_unchanged():
    window = fleet.resolve_window(hours=168, now=LATER)
    assert window.mode == "rolling"
    assert window.hours == 168
    assert window.start == (LATER - timedelta(hours=168)).replace(tzinfo=None)
    assert window.end == LATER.replace(tzinfo=None)

    db = FakeDB()
    pings, explanation = fleet.score_vessel(db, MMSI, hours=168, now=LATER)
    assert pings and explanation is not None
    assert "until" not in db.ping_params


def test_missing_historical_data_stays_empty_and_unavailable():
    db = FakeDB()
    synced = assessments.sync_assessments(
        assessments.SyncRequest(
            mmsi=MMSI,
            window_start=EMPTY_START,
            window_end=EMPTY_END,
        ),
        db=db,
    )
    assert synced.synced == 0
    assert synced.window["mode"] == "historical"
    assert db.assessment_params is None

    with pytest.raises(HTTPException) as exc:
        vessels.get_vessel(
            MMSI,
            168,
            FakeDB(),
            window_start=EMPTY_START,
            window_end=EMPTY_END,
        )
    assert exc.value.status_code == 404
    assert "selected historical window" in exc.value.detail
    assert "2026-10-01T00:00:00Z" in exc.value.detail


@pytest.mark.parametrize(
    "start,end,message",
    [
        (WINDOW_START, None, "supplied together"),
        (None, WINDOW_END, "supplied together"),
        (WINDOW_END, WINDOW_START, "must be after"),
        (WINDOW_START, WINDOW_START + timedelta(hours=169), "must not exceed"),
        (datetime(2026, 10, 31, 0, 0), WINDOW_END, "explicit UTC offset"),
        (LATER - timedelta(hours=2), LATER + timedelta(hours=1), "future"),
    ],
)
def test_invalid_windows_fail_clearly(start, end, message):
    with pytest.raises(fleet.WindowSelectionError, match=message):
        fleet.resolve_window(hours=168, start=start, end=end, now=LATER)


def test_routes_reject_invalid_window_with_422():
    with pytest.raises(HTTPException) as vessel_exc:
        vessels.get_vessel(MMSI, 168, FakeDB(), window_start=WINDOW_START)
    assert vessel_exc.value.status_code == 422

    with pytest.raises(HTTPException) as assessment_exc:
        assessments.sync_assessments(
            assessments.SyncRequest(window_start=WINDOW_START),
            db=FakeDB(),
        )
    assert assessment_exc.value.status_code == 422

    with pytest.raises(HTTPException) as report_exc:
        reports.create_report(
            reports.CreateReport(
                mmsi=MMSI,
                window_start=WINDOW_END,
                window_end=WINDOW_START,
            ),
            db=FakeDB(),
        )
    assert report_exc.value.status_code == 422
