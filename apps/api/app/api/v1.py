"""Small, truthful v1 contracts for investigation and workstation operations.

These endpoints compose existing evidence instead of adding a second risk engine.
Unavailable providers stay unavailable; no response turns missing coverage into
proof of deliberate behaviour.
"""
from __future__ import annotations

import json
import math
import shutil
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.auth import csrf_protect, require_analyst, require_viewer
from app.api.ocean import load_satellite_observations
from app.api.reports import digest
from app.api.sources import build_source_health
from app.api.weather import event_weather_context
from app.database import get_db
from app.config import settings
from app.schemas.user import UserResponse
from app.services import fleet

router = APIRouter()


def _utc(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _json(value, fallback):
    return value if isinstance(value, type(fallback)) else fallback


def _job(row) -> dict:
    item = dict(row._mapping if hasattr(row, "_mapping") else row)
    for key in ("created_at", "started_at", "finished_at"):
        item[key] = _utc(item.get(key))
    item["checkpoint"] = _json(item.get("checkpoint"), {})
    item["cancellable"] = item.get("state") in {"queued", "running"}
    return item


# ---------------------------------------------------------------------------
# Protected boundaries and rules
# ---------------------------------------------------------------------------


@router.get("/boundaries")
def boundaries(
    _viewer: UserResponse = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    rows = db.execute(text("""SELECT id, name, designation, iucn_category, country,
        ST_AsGeoJSON(boundary)::json AS geometry, publisher, boundary_version,
        effective_date, citation, permitted_use, restriction_description,
        restriction_activities, restriction_seasons,
        restriction_verification_status, data_mode
        FROM marine_protected_areas ORDER BY name, id""")).mappings()
    items = []
    for row in rows:
        items.append({
            "id": row["id"], "name": row["name"], "designation": row["designation"],
            "iucn_category": row["iucn_category"], "country": row["country"],
            "geometry": row["geometry"], "publisher": row["publisher"] or "unknown",
            "version": row["boundary_version"] or "unknown",
            "effective_date": row["effective_date"], "citation": row["citation"],
            "permitted_use": row["permitted_use"] or "unknown",
            "data_mode": row["data_mode"] or "unknown",
            "restriction": {
                "description": row["restriction_description"],
                "activities": _json(row["restriction_activities"], []),
                "seasons": _json(row["restriction_seasons"], []),
                "verification_status": row["restriction_verification_status"] or "unverified",
            },
        })
    return {
        "items": items,
        "limitations": (
            "Boundary presence and review buffers are not legal findings. A restriction is "
            "applicable only when its activity, season and verification status say so."
        ),
    }


# ---------------------------------------------------------------------------
# Alert review state and authored notes
# ---------------------------------------------------------------------------


class AlertReview(BaseModel):
    expected_version: int = Field(ge=0)
    state: Literal["new", "watch", "in_review", "closed"]
    assigned_to: str | None = Field(default=None, max_length=50)
    reason: str | None = Field(default=None, max_length=500)


class AlertNote(BaseModel):
    expected_version: int = Field(ge=0)
    note: str = Field(min_length=1, max_length=1000)

    @field_validator("note")
    @classmethod
    def strip_note(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("note cannot be blank")
        return value


def _alert_review_detail(db: Session, alert_id: UUID):
    row = db.execute(text("""SELECT id, reviewer_state, assigned_to, resolution_reason,
        clear_scenario, version, updated_at FROM alert_records WHERE id=:id"""),
                     {"id": str(alert_id)}).mappings().first()
    if row is None:
        raise HTTPException(404, "Alert not found")
    notes = db.execute(text("""SELECT id, author, note, created_at FROM alert_notes
        WHERE alert_id=:id ORDER BY created_at, id"""), {"id": str(alert_id)}).mappings()
    return {
        **dict(row),
        "clear_scenario": _json(row["clear_scenario"], {}),
        "notes": [{**dict(note), "created_at": _utc(note["created_at"])} for note in notes],
        "updated_at": _utc(row["updated_at"]),
        "limitation": "Review state records analyst workflow; it is not a determination of guilt.",
    }


@router.post("/alerts/stored/{alert_id}/review")
def review_alert(
    alert_id: UUID,
    payload: AlertReview,
    user: UserResponse = Depends(require_analyst),
    _csrf: None = Depends(csrf_protect),
    db: Session = Depends(get_db),
):
    row = db.execute(text("SELECT version,reviewer_state FROM alert_records WHERE id=:id FOR UPDATE"),
                     {"id": str(alert_id)}).first()
    if row is None:
        raise HTTPException(404, "Alert not found")
    if row.version != payload.expected_version:
        raise HTTPException(409, "Alert changed; reload before retrying")
    reason = (payload.reason or "").strip() or None
    if payload.state == "closed" and not reason:
        raise HTTPException(422, "Closing an alert requires a reason")
    if row.reviewer_state == "closed" and payload.state != "closed" and not reason:
        raise HTTPException(422, "Reopening a closed alert requires a reason")
    assignee = (payload.assigned_to or "").strip() or None
    now = datetime.now(timezone.utc)
    db.execute(text("""UPDATE alert_records SET reviewer_state=:state,
        assigned_to=:assignee, resolution_reason=:reason,
        version=version+1, updated_at=:now WHERE id=:id"""), {
        "state": payload.state, "assignee": assignee, "reason": reason,
        "now": now, "id": str(alert_id),
    })
    db.execute(text("""INSERT INTO alert_notes (alert_id, author, note, created_at)
        VALUES (:id, :actor, :note, :now)"""), {
        "id": str(alert_id), "actor": user.username,
        "note": reason or f"Review state changed to {payload.state}", "now": now,
    })
    db.commit()
    return _alert_review_detail(db, alert_id)


@router.post("/alerts/stored/{alert_id}/notes", status_code=201)
def add_alert_note(
    alert_id: UUID,
    payload: AlertNote,
    user: UserResponse = Depends(require_analyst),
    _csrf: None = Depends(csrf_protect),
    db: Session = Depends(get_db),
):
    row = db.execute(text("SELECT version FROM alert_records WHERE id=:id FOR UPDATE"),
                     {"id": str(alert_id)}).first()
    if row is None:
        raise HTTPException(404, "Alert not found")
    if row.version != payload.expected_version:
        raise HTTPException(409, "Alert changed; reload before retrying")
    now = datetime.now(timezone.utc)
    db.execute(text("INSERT INTO alert_notes (alert_id, author, note, created_at) VALUES (:id,:author,:note,:now)"),
               {"id": str(alert_id), "author": user.username, "note": payload.note, "now": now})
    db.execute(text("UPDATE alert_records SET version=version+1, updated_at=:now WHERE id=:id"),
               {"id": str(alert_id), "now": now})
    db.commit()
    return _alert_review_detail(db, alert_id)


# ---------------------------------------------------------------------------
# Time-aligned encounter graph and triage context
# ---------------------------------------------------------------------------


@router.get("/vessels/{mmsi}/encounters")
def encounter_graph(
    mmsi: int,
    hours: int = Query(48, ge=1, le=168),
    hops: int = Query(2, ge=1, le=2),
    max_nodes: int = Query(40, ge=2, le=100),
    max_edges: int = Query(80, ge=1, le=200),
    _viewer: UserResponse = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    end = db.execute(text("SELECT max(timestamp) FROM vessel_tracks WHERE mmsi=:mmsi"),
                     {"mmsi": mmsi}).scalar_one_or_none()
    if end is None:
        raise HTTPException(404, "No vessel observations")
    end = _utc(end)
    start = end - timedelta(hours=hours)
    # Pair only actual observations within five minutes and 500 m. Grouped edges
    # never interpolate across sparse gaps.
    rows = db.execute(text("""WITH pairs AS (
        SELECT LEAST(a.mmsi,b.mmsi) AS source_mmsi,
               GREATEST(a.mmsi,b.mmsi) AS target_mmsi,
               a.timestamp AS observed_at,
               ST_Distance(a.location::geography,b.location::geography) AS distance_m
        FROM vessel_tracks a JOIN vessel_tracks b
          ON a.mmsi < b.mmsi
         AND b.timestamp BETWEEN a.timestamp - interval '5 minutes' AND a.timestamp + interval '5 minutes'
         AND ST_DWithin(a.location::geography,b.location::geography,500)
        WHERE a.timestamp BETWEEN :start AND :end
          AND (a.mmsi=:root OR b.mmsi=:root)
    ) SELECT source_mmsi,target_mmsi,min(observed_at) overlap_start,
        max(observed_at) overlap_end,min(distance_m) distance_m,count(*) input_points
      FROM pairs GROUP BY source_mmsi,target_mmsi
      ORDER BY input_points DESC,distance_m LIMIT :limit"""),
      {"root": mmsi, "start": start, "end": end, "limit": max_edges}).mappings().all()
    # The second hop is bounded and derived only from first-hop MMSIs.
    first = sorted({int(r["source_mmsi"]) for r in rows} | {int(r["target_mmsi"]) for r in rows})
    if hops == 2 and len(first) > 1 and len(rows) < max_edges:
        more = db.execute(text("""WITH pairs AS (
          SELECT LEAST(a.mmsi,b.mmsi) source_mmsi,GREATEST(a.mmsi,b.mmsi) target_mmsi,
            a.timestamp observed_at,ST_Distance(a.location::geography,b.location::geography) distance_m
          FROM vessel_tracks a JOIN vessel_tracks b ON a.mmsi < b.mmsi
            AND b.timestamp BETWEEN a.timestamp-interval '5 minutes' AND a.timestamp+interval '5 minutes'
            AND ST_DWithin(a.location::geography,b.location::geography,500)
          WHERE a.timestamp BETWEEN :start AND :end AND (a.mmsi=ANY(:first) OR b.mmsi=ANY(:first))
        ) SELECT source_mmsi,target_mmsi,min(observed_at) overlap_start,max(observed_at) overlap_end,
          min(distance_m) distance_m,count(*) input_points FROM pairs
          GROUP BY source_mmsi,target_mmsi ORDER BY input_points DESC,distance_m LIMIT :limit"""),
          {"first": first, "start": start, "end": end, "limit": max_edges}).mappings().all()
        seen = {(r["source_mmsi"], r["target_mmsi"]) for r in rows}
        rows.extend(r for r in more if (r["source_mmsi"], r["target_mmsi"]) not in seen)
    rows = rows[:max_edges]
    node_ids = [mmsi]
    for row in rows:
        for value in (int(row["source_mmsi"]), int(row["target_mmsi"])):
            if value not in node_ids and len(node_ids) < max_nodes:
                node_ids.append(value)
    edges = []
    for row in rows:
        if int(row["source_mmsi"]) not in node_ids or int(row["target_mmsi"]) not in node_ids:
            continue
        seconds = max(0.0, (_utc(row["overlap_end"]) - _utc(row["overlap_start"])).total_seconds())
        edges.append({
            "source_mmsi": int(row["source_mmsi"]), "target_mmsi": int(row["target_mmsi"]),
            "distance_m": round(float(row["distance_m"]), 1),
            "duration_minutes": round(seconds / 60, 1),
            "overlap_start": _utc(row["overlap_start"]), "overlap_end": _utc(row["overlap_end"]),
            "input_points": int(row["input_points"]),
            "coverage_status": "sparse" if row["input_points"] < 3 else "observed",
        })
    return {
        "root_mmsi": mmsi, "window": {"start": start, "end": end},
        "nodes": [{"mmsi": value, "root": value == mmsi} for value in node_ids],
        "edges": edges,
        "limitations": "Edges use time-near observed points only. Proximity does not establish transfer, ownership or illegal activity.",
    }


@router.get("/triage/evidence/{mmsi}")
def triage_evidence(
    mmsi: int,
    hours: int = Query(48, ge=1, le=168),
    _viewer: UserResponse = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    pings, explanation = fleet.score_vessel(db, mmsi, hours)
    if explanation is None:
        raise HTTPException(404, "No vessel observations")
    weather = event_weather_context(db, mmsi)
    timestamps = sorted(_utc(p.timestamp) for p in pings)
    gaps = [(b - a).total_seconds() / 3600 for a, b in zip(timestamps, timestamps[1:])]
    coverage = {
        "status": "unknown",
        "nearby_observations": len(pings),
        "largest_observation_gap_hours": round(max(gaps), 2) if gaps else None,
        "receiver_outage_verified": False,
        "note": "Observation density is not a measured receiver coverage surface.",
    }
    clear = {
        "status": "review_only",
        "scenario": (
            "Reliable event-time coverage plus continuous, physically plausible positions could clear the AIS-gap contribution; "
            "protected-area observations and other factors remain separate."
        ),
        "computed_score": None,
    }
    return {
        "mmsi": mmsi, "window_hours": hours, "weather": weather, "coverage": coverage,
        "clear_scenario": clear,
        "score_unchanged": True,
        "limitations": "Weather and sparse coverage are review context only and never close or lower an alert automatically.",
    }


# ---------------------------------------------------------------------------
# Environmental baseline and bounded scan planning
# ---------------------------------------------------------------------------


def _ocean_cells():
    data = load_satellite_observations()
    values = []
    for item in data.get("values") or []:
        try:
            lat, lon, temp = float(item["latitude"]), float(item["longitude"]), float(item["temperature_c"])
            observed = datetime.fromisoformat(str(item["observed_at"]).replace("Z", "+00:00"))
        except (KeyError, TypeError, ValueError):
            continue
        if not all(map(math.isfinite, (lat, lon, temp))) or observed.tzinfo is None:
            continue
        values.append({"latitude": lat, "longitude": lon, "temperature_c": temp,
                       "observed_at": observed.astimezone(timezone.utc)})
    if not values:
        raise HTTPException(503, "Prepared environmental data unavailable")
    newest = max(v["observed_at"] for v in values)
    latest = [v for v in values if v["observed_at"] == newest]
    mean = sum(v["temperature_c"] for v in latest) / len(latest)
    cells = []
    for value in latest:
        anomaly = value["temperature_c"] - mean
        # No fishing-effort history is configured, so ranking is descriptive SST
        # anomaly only and explicitly not an illegal-activity forecast.
        cells.append({**value, "cell_id": f"{value['latitude']:.3f}:{value['longitude']:.3f}",
                      "environmental_anomaly_c": round(anomaly, 3),
                      "activity_score": None, "rank_factor": abs(anomaly)})
    cells.sort(key=lambda item: (-item["rank_factor"], item["cell_id"]))
    return data, newest, cells


@router.get("/ocean/baseline")
def ocean_baseline(_viewer: UserResponse = Depends(require_viewer)):
    data, newest, cells = _ocean_cells()
    return {
        "status": "descriptive_only", "mode": "historical", "observed_at": newest,
        "product": data.get("product"), "dataset": data.get("dataset"),
        "dataset_version": data.get("dataset_version"), "unit": data.get("unit"),
        "factors": ["absolute SST anomaly within the latest prepared grid"],
        "cells": cells,
        "evaluation": {"status": "blocked", "reason": "No time-aligned fishing-effort history is configured."},
        "limitations": "SST anomaly is environmental context, not an illegal-fishing prediction.",
    }


class ScanPlanRequest(BaseModel):
    budget: int = Field(default=10, ge=1, le=100)
    reserve_fraction: float = Field(default=0.2, ge=0.2, le=0.5)


@router.post("/ocean/scan-plans")
def create_scan_plan(
    payload: ScanPlanRequest,
    _analyst: UserResponse = Depends(require_analyst),
    _csrf: None = Depends(csrf_protect),
):
    _, newest, cells = _ocean_cells()
    count = min(payload.budget, len(cells))
    reserve = min(count, max(1, math.ceil(count * payload.reserve_fraction)))
    ranked = cells[:max(0, count - reserve)]
    remaining = [cell for cell in cells if cell not in ranked]
    stride = max(1, len(remaining) // reserve) if remaining else 1
    reserved = remaining[::stride][:reserve]
    return {
        "id": str(uuid4()), "status": "planned", "observed_at": newest,
        "budget": count, "ranked_cells": ranked, "reserved_coverage_cells": reserved,
        "reserve_fraction": payload.reserve_fraction,
        "limitations": "This prioritises existing cells for processing; it does not task a satellite or change its orbit.",
    }


# ---------------------------------------------------------------------------
# Source jobs, offline/cache/operations, delivery outbox, spill capability
# ---------------------------------------------------------------------------


@router.get("/sources/jobs")
def list_source_jobs(
    limit: int = Query(50, ge=1, le=100),
    _viewer: UserResponse = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    rows = db.execute(text("SELECT * FROM source_jobs ORDER BY created_at DESC LIMIT :limit"),
                      {"limit": limit})
    return {"items": [_job(row) for row in rows]}


@router.get("/sources/jobs/{job_id}")
def get_source_job(job_id: UUID, _viewer: UserResponse = Depends(require_viewer), db: Session = Depends(get_db)):
    row = db.execute(text("SELECT * FROM source_jobs WHERE id=:id"), {"id": str(job_id)}).first()
    if row is None:
        raise HTTPException(404, "Job not found")
    result = _job(row)
    result["quarantine"] = [dict(item._mapping) for item in db.execute(
        text("SELECT record_index,source_record_id,reason,record_summary,created_at FROM ingest_quarantine WHERE job_id=:id ORDER BY record_index"),
        {"id": str(job_id)})]
    return result


class CancelJob(BaseModel):
    expected_version: int = Field(ge=0)


@router.post("/sources/jobs/{job_id}/cancel")
def cancel_source_job(
    job_id: UUID, payload: CancelJob,
    _analyst: UserResponse = Depends(require_analyst),
    _csrf: None = Depends(csrf_protect), db: Session = Depends(get_db),
):
    row = db.execute(text("SELECT * FROM source_jobs WHERE id=:id FOR UPDATE"), {"id": str(job_id)}).first()
    if row is None:
        raise HTTPException(404, "Job not found")
    if row.version != payload.expected_version:
        raise HTTPException(409, "Job changed; reload before retrying")
    if row.state not in {"queued", "running"}:
        raise HTTPException(409, "Only queued or running jobs can be cancelled")
    now = datetime.now(timezone.utc)
    db.execute(text("UPDATE source_jobs SET state='cancelled',finished_at=:now,version=version+1 WHERE id=:id"),
               {"id": str(job_id), "now": now})
    db.commit()
    return get_source_job(job_id, _analyst, db)


@router.get("/operations/status")
def operations_status(_viewer: UserResponse = Depends(require_viewer), db: Session = Depends(get_db)):
    latest = db.execute(text("SELECT max(timestamp) FROM vessel_tracks")).scalar_one_or_none()
    queued = db.execute(text("SELECT count(*) FROM source_jobs WHERE state IN ('queued','running')")).scalar_one()
    try:
        usage = shutil.disk_usage("/")
        disk = {"status": "available", "free_bytes": usage.free, "total_bytes": usage.total}
    except OSError:
        disk = {"status": "unknown"}
    source_health = build_source_health(db)
    return {
        "mode": "offline" if settings.OFFLINE_MODE else "workstation",
        "remote_fetch_paused": settings.OFFLINE_MODE,
        "cache": {"latest_vessel_observation": _utc(latest), "environment": "prepared_historical_subset"},
        "queue": {"active_jobs": int(queued), "worker_status": "not_verified"},
        "disk": disk,
        "retention": {"status": "manual", "safeguard": "No automatic evidence deletion is enabled."},
        "backup": {"status": "not_verified", "restore_target": "separate database required"},
        "sources": source_health["sources"],
        "limitations": "This endpoint never exposes credentials. Worker and backup health require an explicit operational check.",
    }


class DeliveryRequest(BaseModel):
    expected_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    recipients: list[str] = Field(min_length=1, max_length=10)
    idempotency_key: str = Field(min_length=8, max_length=120)

    @field_validator("recipients")
    @classmethod
    def local_sink_only(cls, values: list[str]) -> list[str]:
        cleaned = []
        for value in values:
            address = value.strip().lower()
            if not address.endswith("@example.test") or "@" not in address:
                raise ValueError("v1 delivery is restricted to the local .test mail sink")
            if address not in cleaned:
                cleaned.append(address)
        return cleaned


def _delivery(row):
    raw = dict(row._mapping if hasattr(row, "_mapping") else row)
    item = {key: raw.get(key) for key in (
        "id", "report_id", "report_sha256", "recipients", "idempotency_key",
        "state", "attempts", "last_error", "requested_by", "created_at", "submitted_at",
    )}
    item["recipients"] = _json(item.get("recipients"), [])
    for key in ("created_at", "submitted_at"):
        item[key] = _utc(item.get(key))
    item["provider_meaning"] = "submitted means accepted by the configured local sink, not received or read"
    return item


@router.post("/reports/{report_id}/deliveries", status_code=201)
def queue_delivery(
    report_id: int, payload: DeliveryRequest,
    user: UserResponse = Depends(require_analyst),
    _csrf: None = Depends(csrf_protect), db: Session = Depends(get_db),
):
    report = db.execute(text("SELECT id,sha256,signed_at,snapshot FROM incident_reports WHERE id=:id"),
                        {"id": report_id}).first()
    if report is None:
        raise HTTPException(404, "Report not found")
    if report.signed_at is None:
        raise HTTPException(409, "Only an approved report version can be delivered")
    if report.sha256 != payload.expected_sha256:
        raise HTTPException(409, "Report changed; approve and submit the exact current hash")
    if digest(report.snapshot) != report.sha256:
        raise HTTPException(409, "Report integrity check failed")
    existing = db.execute(text("SELECT * FROM report_delivery_outbox WHERE idempotency_key=:key"),
                          {"key": payload.idempotency_key}).first()
    if existing is not None:
        if existing.report_id != report_id or existing.report_sha256 != payload.expected_sha256:
            raise HTTPException(409, "Idempotency key is already used for another report version")
        return _delivery(existing)
    row = db.execute(text("""INSERT INTO report_delivery_outbox
        (id,report_id,report_sha256,recipients,idempotency_key,state,attempts,requested_by)
        VALUES (:id,:report,:sha,CAST(:recipients AS jsonb),:key,'queued',0,:actor) RETURNING *"""), {
        "id": str(uuid4()), "report": report_id, "sha": payload.expected_sha256,
        "recipients": json.dumps(payload.recipients), "key": payload.idempotency_key,
        "actor": user.username,
    }).first()
    db.commit()
    return _delivery(row)


@router.get("/reports/{report_id}/deliveries")
def list_deliveries(report_id: int, _viewer: UserResponse = Depends(require_viewer), db: Session = Depends(get_db)):
    rows = db.execute(text("SELECT * FROM report_delivery_outbox WHERE report_id=:id ORDER BY created_at DESC"),
                      {"id": report_id})
    return {"items": [_delivery(row) for row in rows], "sink": "local_test_only"}


@router.post("/reports/deliveries/{delivery_id}/submit")
def submit_local_delivery(
    delivery_id: UUID,
    _analyst: UserResponse = Depends(require_analyst),
    _csrf: None = Depends(csrf_protect), db: Session = Depends(get_db),
):
    row = db.execute(text("""SELECT d.*,r.snapshot,r.sha256 AS current_sha256,r.signed_at
        FROM report_delivery_outbox d JOIN incident_reports r ON r.id=d.report_id
        WHERE d.id=:id FOR UPDATE OF d"""), {"id": str(delivery_id)}).first()
    if row is None:
        raise HTTPException(404, "Delivery not found")
    if row.state == "submitted":
        return _delivery(row)
    if row.state == "cancelled":
        raise HTTPException(409, "Cancelled delivery cannot be submitted")
    if row.attempts >= 3:
        raise HTTPException(409, "Delivery retry limit reached")
    if row.signed_at is None or row.current_sha256 != row.report_sha256:
        raise HTTPException(409, "Approved report version no longer matches the queued delivery")
    if digest(row.snapshot) != row.report_sha256:
        raise HTTPException(409, "Report integrity check failed")
    sink = Path(settings.DELIVERY_LOCAL_SINK_DIR).resolve()
    target = sink / f"{delivery_id}.json"
    envelope = {
        "delivery_id": str(delivery_id), "report_id": row.report_id,
        "report_sha256": row.report_sha256, "recipients": row.recipients,
        "transport": "local_file_sink", "snapshot": row.snapshot,
    }
    try:
        sink.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        try:
            with target.open("x", encoding="utf-8") as output:
                output.write(encoded)
        except FileExistsError:
            if target.read_text(encoding="utf-8") != encoded:
                raise OSError("Existing sink item does not match queued delivery")
        now = datetime.now(timezone.utc)
        db.execute(text("""UPDATE report_delivery_outbox SET state='submitted',attempts=attempts+1,
            submitted_at=:now,last_error=NULL WHERE id=:id"""), {"now": now, "id": str(delivery_id)})
        db.commit()
    except OSError as exc:
        message = " ".join(str(exc).split())[:300] or "Local delivery sink unavailable"
        db.execute(text("""UPDATE report_delivery_outbox SET state='failed',attempts=attempts+1,
            last_error=:error WHERE id=:id"""), {"error": message, "id": str(delivery_id)})
        db.commit()
        raise HTTPException(503, "Local delivery sink unavailable; queued report was not sent") from exc
    result = db.execute(text("SELECT * FROM report_delivery_outbox WHERE id=:id"),
                        {"id": str(delivery_id)}).first()
    return _delivery(result)


@router.get("/spill/capabilities")
def spill_capabilities(_viewer: UserResponse = Depends(require_viewer)):
    return {
        "status": "unavailable", "engine": "PyGNOME", "engine_version": None,
        "forcing": {"wind": "not_configured", "current": "not_configured"},
        "supported_modes": [],
        "reason": "PyGNOME and compatible wind/current forcing are not installed in the supported worker runtime.",
        "limitations": "No fallback trajectory is generated; missing current data is never treated as zero flow.",
    }


class SpillJobRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    release_at: datetime
    duration_hours: int = Field(default=24, ge=1, le=72)
    particle_count: int = Field(default=500, ge=100, le=5000)
    mode: Literal["real", "cached", "synthetic_training"]

    @field_validator("release_at")
    @classmethod
    def release_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("release_at must include a timezone")
        return value


@router.post("/spill/jobs")
def create_spill_job(
    _payload: SpillJobRequest,
    _analyst: UserResponse = Depends(require_analyst),
    _csrf: None = Depends(csrf_protect),
):
    raise HTTPException(503, detail=spill_capabilities(_analyst))


@router.get("/spill/jobs")
def list_spill_jobs(_viewer: UserResponse = Depends(require_viewer)):
    return {"items": [], "capability": spill_capabilities(_viewer)}


@router.get("/spill/jobs/{job_id}")
def get_spill_job(job_id: UUID, _viewer: UserResponse = Depends(require_viewer)):
    raise HTTPException(404, f"Spill job {job_id} does not exist; engine capability is unavailable")


@router.post("/spill/jobs/{job_id}/cancel")
def cancel_spill_job(
    job_id: UUID, _payload: CancelJob,
    _analyst: UserResponse = Depends(require_analyst),
    _csrf: None = Depends(csrf_protect),
):
    raise HTTPException(404, f"Spill job {job_id} does not exist; engine capability is unavailable")
