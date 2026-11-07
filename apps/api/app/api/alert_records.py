"""Persist derived alert conditions and record an auditable review lifecycle.

``POST /alerts/sync`` runs the existing generator once, deduplicates its rows by
the stable A-003F identity and upserts ``alert_records``. Reads expose stored
lifecycle; the legacy ``GET /alerts/`` projection is unchanged.

Semantics kept deliberately conservative:

* Resolved alerts are never silently reopened by a later sync.
* Observation timestamps never move backwards.
* Every lifecycle change is appended to ``alert_events`` with the acting user.
* A record is a screening artefact for human review, not proof of illegal activity.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.alerts import (
    AlertGenerator,
    alert_context,
    alert_description,
    alert_id,
    alert_identity,
    alert_location,
    alert_title,
    deduplicate_alerts,
    severity_label,
)
from app.api.auth import csrf_protect, require_analyst, require_viewer
from app.database import get_db
from app.schemas.user import UserResponse

router = APIRouter()

STATUSES = ("open", "acknowledged", "resolved")
SOURCE_MODES = ("live", "historical", "replay", "synthetic", "unknown")
SEVERITIES = ("HIGH", "MEDIUM", "LOW")

LIFECYCLE_LIMITATION = (
    "Stored alerts are rule-based screening records for human review, not proof of "
    "illegal activity. Status reflects analyst action only. Source provenance may be "
    "unknown, and receiver coverage is not verified."
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def as_utc(value: Optional[datetime]) -> datetime:
    """Interpret a naive database/generator time as UTC; never guess another zone."""
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def zone_key(alert: dict) -> str:
    zone = alert.get("mpa_id") or alert.get("mpa_name") or ""
    return str(zone)[:200]


def mode_or_none(alert: dict) -> Optional[str]:
    mode = alert.get("source_mode")
    return mode if mode in SOURCE_MODES else None


def _source_or_none(alert: dict) -> Optional[str]:
    value = alert.get("source")
    if value is None:
        return None
    return str(value)[:120]


def summary_mode(modes) -> str:
    distinct = {mode for mode in modes if mode}
    if not distinct:
        return "unknown"
    if len(distinct) == 1:
        return distinct.pop()
    return "mixed"


def record_to_dict(row) -> dict:
    mapping = row._mapping
    location = {}
    if mapping["location_lat"] is not None and mapping["location_lon"] is not None:
        location = {"lat": mapping["location_lat"], "lon": mapping["location_lon"]}
    return {
        "id": str(mapping["id"]),
        "type": mapping["type"],
        "severity": mapping["severity"],
        "mmsi": mapping["mmsi"],
        "mpa_id": mapping["mpa_id"],
        "mpa_name": mapping["mpa_name"],
        "title": mapping["title"],
        "description": mapping["description"],
        "first_observed_at": as_utc(mapping["first_observed_at"]),
        "last_observed_at": as_utc(mapping["last_observed_at"]),
        "location": location,
        "metadata": mapping["metadata"] or {},
        "source": mapping["source"],
        "source_mode": mapping["source_mode"],
        "status": mapping["status"],
        "version": mapping["version"],
        "acknowledged_by": mapping["acknowledged_by"],
        "acknowledged_at": (
            as_utc(mapping["acknowledged_at"]) if mapping["acknowledged_at"] else None
        ),
        "resolved_by": mapping["resolved_by"],
        "resolved_at": as_utc(mapping["resolved_at"]) if mapping["resolved_at"] else None,
        "resolution_note": mapping["resolution_note"],
        "created_at": as_utc(mapping["created_at"]),
        "updated_at": as_utc(mapping["updated_at"]),
        "persisted": True,
        "lifecycle": "stored",
    }


def _append_event(
    db: Session,
    alert_id_value,
    event: str,
    actor: str,
    note: Optional[str],
    at: datetime,
) -> None:
    db.execute(
        text(
            """INSERT INTO alert_events (alert_id, event, actor, note, created_at)
               VALUES (:alert_id, :event, :actor, :note, :at)"""
        ),
        {
            "alert_id": str(alert_id_value),
            "event": event,
            "actor": actor,
            "note": note,
            "at": at,
        },
    )


def _fetch_detail(db: Session, alert_id_value) -> dict:
    row = db.execute(
        text("SELECT * FROM alert_records WHERE id = :id"), {"id": str(alert_id_value)}
    ).first()
    if row is None:
        raise HTTPException(404, "Alert not found")
    result = record_to_dict(row)
    events = db.execute(
        text(
            """SELECT event, actor, note, created_at FROM alert_events
               WHERE alert_id = :id ORDER BY created_at, id"""
        ),
        {"id": str(alert_id_value)},
    )
    result["events"] = [
        {
            "event": event.event,
            "actor": event.actor,
            "note": event.note,
            "at": as_utc(event.created_at),
        }
        for event in events
    ]
    return result


def _lock_record(db: Session, alert_id_value):
    row = db.execute(
        text("SELECT * FROM alert_records WHERE id = :id FOR UPDATE"),
        {"id": str(alert_id_value)},
    ).first()
    if row is None:
        raise HTTPException(404, "Alert not found")
    return row


def _require_version(row, expected_version: int) -> None:
    if row.version != expected_version:
        raise HTTPException(409, "Alert changed; reload before retrying")


def _validate_status_filter(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized not in STATUSES:
        raise HTTPException(422, "status must be open, acknowledged or resolved")
    return normalized


def _validate_severity_filter(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip().upper()
    if normalized not in SEVERITIES:
        raise HTTPException(422, "severity must be HIGH, MEDIUM or LOW")
    return normalized


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class SyncResponse(BaseModel):
    observed: int
    created: int
    updated: int
    unchanged: int
    skipped_resolved: int
    source_mode: str
    synced_at: datetime


class TransitionRequest(BaseModel):
    expected_version: int = Field(ge=0)


class ResolveRequest(TransitionRequest):
    note: Optional[str] = Field(default=None, max_length=500)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/sync", response_model=SyncResponse)
def sync_alerts(
    _analyst: UserResponse = Depends(require_analyst),
    _csrf: None = Depends(csrf_protect),
    db: Session = Depends(get_db),
) -> SyncResponse:
    """Persist the current deduplicated generator output, preserving lifecycle."""
    raw_alerts = AlertGenerator(db).check_mpa_violations()
    grouped = deduplicate_alerts(raw_alerts)

    now = datetime.now(timezone.utc)
    created = updated = unchanged = skipped_resolved = 0
    modes = set()

    for alert in grouped.values():
        record_id = alert_id(alert)
        key = zone_key(alert)
        severity = severity_label(alert)
        observed = as_utc(alert.get("timestamp"))
        location = alert_location(alert)
        mode = mode_or_none(alert)
        source = _source_or_none(alert)
        metadata = alert_context(alert)
        metadata.update({"persisted": True, "lifecycle": "stored"})
        metadata_json = json.dumps(metadata, default=str)
        params = {
            "id": record_id,
            "type": str(alert["type"])[:50],
            "severity": severity,
            "mmsi": int(alert["mmsi"]),
            "zone_key": key,
            "mpa_id": alert.get("mpa_id"),
            "mpa_name": alert.get("mpa_name"),
            "title": (alert_title(alert) or f"{alert['type']} alert")[:300],
            "description": alert_description(alert),
            "observed": observed,
            "lat": location.get("lat"),
            "lon": location.get("lon"),
            "metadata": metadata_json,
            "source": source,
            "source_mode": mode,
            "now": now,
        }
        inserted = db.execute(
            text(
                """INSERT INTO alert_records (
                       id, type, severity, mmsi, zone_key, mpa_id, mpa_name,
                       title, description, first_observed_at, last_observed_at,
                       location_lat, location_lon, metadata, source, source_mode,
                       status, version, created_at, updated_at)
                   VALUES (
                       :id, :type, :severity, :mmsi, :zone_key, :mpa_id, :mpa_name,
                       :title, :description, :observed, :observed,
                       :lat, :lon, CAST(:metadata AS jsonb), :source, :source_mode,
                       'open', 0, :now, :now)
                   ON CONFLICT (type, mmsi, zone_key) DO NOTHING
                   RETURNING id"""
            ),
            params,
        ).first()

        if inserted is not None:
            _append_event(db, record_id, "created", "system", None, now)
            created += 1
            modes.add(mode)
            continue

        existing = db.execute(
            text(
                """SELECT status, last_observed_at, severity
                   FROM alert_records
                   WHERE type = :type AND mmsi = :mmsi AND zone_key = :zone_key
                   FOR UPDATE"""
            ),
            {"type": params["type"], "mmsi": params["mmsi"], "zone_key": key},
        ).first()

        if existing is None:
            # Defensive: the conflicting row vanished between statements.
            unchanged += 1
            continue
        if existing.status == "resolved":
            skipped_resolved += 1
            continue

        advanced = observed > as_utc(existing.last_observed_at) or severity != existing.severity
        db.execute(
            text(
                """UPDATE alert_records SET
                       severity = :severity,
                       title = :title,
                       description = :description,
                       mpa_id = :mpa_id,
                       mpa_name = :mpa_name,
                       first_observed_at = LEAST(first_observed_at, :observed),
                       last_observed_at = GREATEST(last_observed_at, :observed),
                       location_lat = :lat,
                       location_lon = :lon,
                       metadata = CAST(:metadata AS jsonb),
                       source = :source,
                       source_mode = :source_mode,
                       updated_at = :now
                   WHERE id = :id"""
            ),
            params,
        )
        if advanced:
            _append_event(db, record_id, "observed", "system", None, now)
            updated += 1
        else:
            unchanged += 1
        modes.add(mode)

    db.commit()
    return SyncResponse(
        observed=len(grouped),
        created=created,
        updated=updated,
        unchanged=unchanged,
        skipped_resolved=skipped_resolved,
        source_mode=summary_mode(modes),
        synced_at=now,
    )


@router.get("/stored")
def list_stored_alerts(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status_filter: Optional[str] = Query(None, alias="status"),
    severity: Optional[str] = Query(None),
    mmsi: Optional[int] = Query(None, ge=100000000, le=999999999),
    _viewer: UserResponse = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    filters = []
    params = {}
    normalized_status = _validate_status_filter(status_filter)
    normalized_severity = _validate_severity_filter(severity)
    if normalized_status is not None:
        filters.append("status = :status")
        params["status"] = normalized_status
    if normalized_severity is not None:
        filters.append("severity = :severity")
        params["severity"] = normalized_severity
    if mmsi is not None:
        filters.append("mmsi = :mmsi")
        params["mmsi"] = mmsi
    where = f"WHERE {' AND '.join(filters)}" if filters else ""

    rows = db.execute(
        text(
            f"""SELECT * FROM alert_records {where}
                ORDER BY last_observed_at DESC, id
                LIMIT :limit OFFSET :offset"""
        ),
        {**params, "limit": limit, "offset": offset},
    )
    total = db.execute(
        text(f"SELECT count(*) FROM alert_records {where}"), params
    ).scalar_one()
    return {
        "alerts": [record_to_dict(row) for row in rows],
        "total": int(total),
        "offset": offset,
        "limit": limit,
        "limitation": LIFECYCLE_LIMITATION,
    }


@router.get("/stored/{alert_id}")
def get_stored_alert(
    alert_id: UUID,
    _viewer: UserResponse = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    return _fetch_detail(db, alert_id)


@router.post("/stored/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: UUID,
    payload: TransitionRequest,
    user: UserResponse = Depends(require_analyst),
    _csrf: None = Depends(csrf_protect),
    db: Session = Depends(get_db),
):
    row = _lock_record(db, alert_id)
    _require_version(row, payload.expected_version)
    if row.status != "open":
        raise HTTPException(409, "Only open alerts can be acknowledged")

    now = datetime.now(timezone.utc)
    db.execute(
        text(
            """UPDATE alert_records SET
                   status = 'acknowledged',
                   acknowledged_by = :actor,
                   acknowledged_at = :now,
                   version = version + 1,
                   updated_at = :now
               WHERE id = :id"""
        ),
        {"actor": user.username, "now": now, "id": str(alert_id)},
    )
    _append_event(db, alert_id, "acknowledged", user.username, None, now)
    db.commit()
    return _fetch_detail(db, alert_id)


@router.post("/stored/{alert_id}/resolve")
def resolve_alert(
    alert_id: UUID,
    payload: ResolveRequest,
    user: UserResponse = Depends(require_analyst),
    _csrf: None = Depends(csrf_protect),
    db: Session = Depends(get_db),
):
    row = _lock_record(db, alert_id)
    _require_version(row, payload.expected_version)
    if row.status not in ("open", "acknowledged"):
        raise HTTPException(409, "Only open or acknowledged alerts can be resolved")

    note = (payload.note or "").strip() or None
    now = datetime.now(timezone.utc)
    db.execute(
        text(
            """UPDATE alert_records SET
                   status = 'resolved',
                   resolved_by = :actor,
                   resolved_at = :now,
                   resolution_note = :note,
                   version = version + 1,
                   updated_at = :now
               WHERE id = :id"""
        ),
        {"actor": user.username, "now": now, "note": note, "id": str(alert_id)},
    )
    _append_event(db, alert_id, "resolved", user.username, note, now)
    db.commit()
    return _fetch_detail(db, alert_id)


@router.post("/stored/{alert_id}/reopen")
def reopen_alert(
    alert_id: UUID,
    payload: TransitionRequest,
    user: UserResponse = Depends(require_analyst),
    _csrf: None = Depends(csrf_protect),
    db: Session = Depends(get_db),
):
    row = _lock_record(db, alert_id)
    _require_version(row, payload.expected_version)
    if row.status != "resolved":
        raise HTTPException(409, "Only resolved alerts can be reopened")

    now = datetime.now(timezone.utc)
    db.execute(
        text(
            """UPDATE alert_records SET
                   status = 'open',
                   version = version + 1,
                   updated_at = :now
               WHERE id = :id"""
        ),
        {"now": now, "id": str(alert_id)},
    )
    _append_event(db, alert_id, "reopened", user.username, None, now)
    db.commit()
    return _fetch_detail(db, alert_id)
