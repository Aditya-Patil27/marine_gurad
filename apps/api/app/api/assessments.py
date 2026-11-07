"""Vessel assessment persistence for the alert workflow (A-004A).

POST /assessments/sync  — Analyst + CSRF: score fleet, upsert assessments.
GET  /assessments       — Viewer: paginated read of persisted assessments.

Rule versioning: stable "v1" string; bump when MAX_POINTS changes.
Source mode: derived from stored track provenance; ``unknown`` when no record
carries a mode and ``mixed`` when a vessel's window disagrees. Never inferred.
IDs: uuid5-deterministic so repeated sync keeps the same PK (idempotent).
Never auto-delete assessments that fall outside the current query window.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.auth import csrf_protect, require_analyst, require_viewer
from app.database import get_db
from app.schemas.user import UserResponse
from app.services import fleet

router = APIRouter()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RULE_VERSION: str = "v1"
DEFAULT_SOURCE_MODE: str = "unknown"
PROVENANCE_MODES = ("live", "historical", "replay", "synthetic", "unknown")
ASSESSMENT_MODES = PROVENANCE_MODES + ("mixed",)
LOOKBACK_HOURS: int = 24

# Deterministic namespace for uuid5 — fixed so IDs survive server restarts.
_UUID_NS = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")

ASSESSMENT_LIMITATION = (
    "Assessments are rule-based screening indicators, not proof of illegal activity. "
    "Source mode is derived from stored track provenance; 'unknown' means it was not "
    "recorded and 'mixed' means the window disagrees, so receiver coverage remains "
    "unverified. Human review is required before any enforcement action."
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def derive_source_mode(pings) -> str:
    """Return one mode for a vessel window, or ``mixed`` when they disagree.

    Missing provenance is ``unknown``; a mode is never inferred from a provider
    being configured or from the shape of the data.
    """
    modes = {getattr(ping, "source_mode", None) or DEFAULT_SOURCE_MODE for ping in pings}
    if not modes:
        return DEFAULT_SOURCE_MODE
    if len(modes) == 1:
        return modes.pop()
    return "mixed"


def _response_source_mode(modes) -> str:
    distinct = {mode for mode in modes if mode}
    if not distinct:
        return DEFAULT_SOURCE_MODE
    if len(distinct) == 1:
        return distinct.pop()
    return "mixed"


def assessment_id(mmsi: int, rule_version: str, source_mode: str) -> uuid.UUID:
    """Return a stable, deterministic UUID for the (mmsi, rule_version, source_mode) triple."""
    return uuid.uuid5(_UUID_NS, f"{mmsi}:{rule_version}:{source_mode}")


def _factor_dict(f) -> Dict[str, Any]:
    return {
        "key": f.key,
        "label": f.label,
        "detail": f.detail,
        "points": f.points,
        "max_points": f.max_points,
        "evidence": f.evidence if isinstance(f.evidence, dict) else {},
    }


def _check_dict(c) -> Dict[str, Any]:
    return {"key": c.key, "label": c.label, "status": c.status, "detail": c.detail}


def _utc_datetime(value: datetime) -> str:
    """Risk engine timestamps are naive UTC; preserve offsets when supplied."""
    return (value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)).isoformat()


def _zone_dict(z) -> Optional[Dict[str, Any]]:
    if z is None:
        return None
    return dict(z)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class SyncRequest(BaseModel):
    lookback_hours: int = LOOKBACK_HOURS
    mmsi: Optional[int] = None
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None


class SyncResponse(BaseModel):
    synced: int
    evaluated_at: str
    rule_version: str
    source_mode: str
    lookback_hours: int
    window: Dict[str, Any]


class AssessmentItem(BaseModel):
    id: str
    mmsi: int
    vessel_name: Optional[str]
    vessel_type: Optional[str]
    score: float
    level: str
    rule_version: str
    source_mode: str
    evaluated_at: str
    lookback_hours: int
    factors: List[Dict[str, Any]]
    checks: List[Dict[str, Any]]
    zone: Optional[Dict[str, Any]]
    headline: Optional[str]
    last_seen: Optional[str]
    last_position: Optional[Dict[str, Any]]
    window: Optional[Dict[str, Any]]


class AssessmentsResponse(BaseModel):
    assessments: List[AssessmentItem]
    total: int
    offset: int
    limit: int
    source_mode: str
    limitation: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/assessments/sync", response_model=SyncResponse, status_code=status.HTTP_200_OK)
def sync_assessments(
    payload: SyncRequest = SyncRequest(),
    _analyst: UserResponse = Depends(require_analyst),
    _csrf: None = Depends(csrf_protect),
    db: Session = Depends(get_db),
) -> SyncResponse:
    """Score the active fleet and upsert stable assessments.

    Existing assessments not seen in this window are retained — never deleted.
    Repeated calls are idempotent; UUIDs are stable across syncs.
    Source mode is derived from the stored tracks; never inferred from a
    configured provider or from the fact that data exists.

    ``window_start``/``window_end`` select one explicit bounded UTC
    historical window. Without them the existing rolling look-back applies.
    The same window can then be supplied to ``GET /vessels/{mmsi}`` and
    ``POST /reports/`` so evidence, assessment and report agree.
    """
    try:
        window = fleet.resolve_window(
            hours=payload.lookback_hours,
            start=payload.window_start,
            end=payload.window_end,
        )
    except fleet.WindowSelectionError as exc:
        raise HTTPException(422, str(exc)) from exc
    hours = window.hours
    if payload.mmsi is not None and not 100000000 <= payload.mmsi <= 999999999:
        raise HTTPException(422, "MMSI must be a nine-digit identifier")
    if payload.mmsi is None:
        results = fleet.score_fleet(db, window=window)
    else:
        own, explanation = fleet.score_vessel(db, payload.mmsi, window=window)
        results = [(own, explanation)] if own and explanation else []

    now_utc = datetime.now(timezone.utc)
    evaluated_at_iso = now_utc.isoformat()
    synced = 0
    synced_modes = set()

    for pings, exp in results:
        last_ping = pings[-1]
        mode = derive_source_mode(pings)
        synced_modes.add(mode)
        aid = assessment_id(last_ping.mmsi, RULE_VERSION, mode)

        factors_json = json.dumps(jsonable_encoder([_factor_dict(f) for f in exp.factors], custom_encoder={datetime: _utc_datetime}))
        checks_json = json.dumps(jsonable_encoder([_check_dict(c) for c in exp.checks], custom_encoder={datetime: _utc_datetime}))
        zone_json = json.dumps(_zone_dict(exp.zone))

        last_position_json = json.dumps(
            {"lat": last_ping.lat, "lon": last_ping.lon}
            if last_ping.lat is not None and last_ping.lon is not None
            else None
        )

        last_seen_val = (last_ping.t.replace(tzinfo=timezone.utc) if last_ping.t.tzinfo is None
                         else last_ping.t.astimezone(timezone.utc)) if last_ping.t else None

        db.execute(
            text(
                """
                INSERT INTO vessel_assessments (
                    id, mmsi, rule_version, source_mode,
                    evaluated_at, lookback_hours,
                    window_mode, window_start, window_end,
                    score, level,
                    factors, checks, zone, headline,
                    vessel_name, vessel_type, length,
                    last_seen, last_position,
                    created_at, updated_at
                ) VALUES (
                    :id, :mmsi, :rule_version, :source_mode,
                    :evaluated_at, :lookback_hours,
                    :window_mode, :window_start, :window_end,
                    :score, :level,
                    CAST(:factors AS jsonb), CAST(:checks AS jsonb),
                    CAST(:zone AS jsonb), :headline,
                    :vessel_name, :vessel_type, :length,
                    :last_seen, CAST(:last_position AS jsonb),
                    :now, :now
                )
                ON CONFLICT (mmsi, rule_version, source_mode) DO UPDATE SET
                    evaluated_at   = EXCLUDED.evaluated_at,
                    lookback_hours = EXCLUDED.lookback_hours,
                    window_mode    = EXCLUDED.window_mode,
                    window_start   = EXCLUDED.window_start,
                    window_end     = EXCLUDED.window_end,
                    score          = EXCLUDED.score,
                    level          = EXCLUDED.level,
                    factors        = EXCLUDED.factors,
                    checks         = EXCLUDED.checks,
                    zone           = EXCLUDED.zone,
                    headline       = EXCLUDED.headline,
                    vessel_name    = EXCLUDED.vessel_name,
                    vessel_type    = EXCLUDED.vessel_type,
                    length         = EXCLUDED.length,
                    last_seen      = EXCLUDED.last_seen,
                    last_position  = EXCLUDED.last_position,
                    updated_at     = EXCLUDED.updated_at
                """
            ),
            {
                "id": str(aid),
                "mmsi": last_ping.mmsi,
                "rule_version": RULE_VERSION,
                "source_mode": mode,
                "evaluated_at": now_utc,
                "lookback_hours": hours,
                "window_mode": window.mode,
                "window_start": window.start.replace(tzinfo=timezone.utc),
                "window_end": window.end.replace(tzinfo=timezone.utc),
                "score": exp.score,
                "level": exp.level,
                "factors": factors_json,
                "checks": checks_json,
                "zone": zone_json,
                "headline": fleet.risk_engine.headline(last_ping, exp),
                "vessel_name": last_ping.name,
                "vessel_type": last_ping.vessel_type,
                "length": last_ping.length,
                "last_seen": last_seen_val,
                "last_position": last_position_json,
                "now": now_utc,
            },
        )
        synced += 1

    db.commit()

    return SyncResponse(
        synced=synced,
        evaluated_at=evaluated_at_iso,
        rule_version=RULE_VERSION,
        source_mode=_response_source_mode(synced_modes),
        lookback_hours=hours,
        window=window.as_dict(),
    )


@router.get("/assessments", response_model=AssessmentsResponse)
def get_assessments(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    mmsi: Optional[int] = Query(None, ge=100000000, le=999999999),
    _viewer: UserResponse = Depends(require_viewer),
    db: Session = Depends(get_db),
) -> AssessmentsResponse:
    """Return paginated, persisted vessel assessments ordered by score descending.

    ``source_mode`` is the stored provenance: a single recorded mode, ``mixed``
    when the returned page disagrees, or ``unknown`` when nothing was recorded.
    """
    filters = "WHERE mmsi = :mmsi" if mmsi is not None else ""
    total_row = db.execute(text(f"SELECT COUNT(*) FROM vessel_assessments {filters}"), {"mmsi": mmsi}).scalar()
    total = int(total_row or 0)

    rows = db.execute(
        text(
            f"""
            SELECT
                id, mmsi, vessel_name, vessel_type, score, level,
                rule_version, source_mode, evaluated_at, lookback_hours,
                window_mode, window_start, window_end,
                factors, checks, zone, headline, last_seen, last_position
            FROM vessel_assessments
            {filters}
            ORDER BY score DESC, evaluated_at DESC, id ASC
            LIMIT :limit OFFSET :offset
            """
        ),
        {"limit": limit, "offset": offset, "mmsi": mmsi},
    ).fetchall()

    items: List[AssessmentItem] = []
    for r in rows:
        items.append(
            AssessmentItem(
                id=str(r.id),
                mmsi=r.mmsi,
                vessel_name=r.vessel_name,
                vessel_type=r.vessel_type,
                score=float(r.score),
                level=r.level,
                rule_version=r.rule_version,
                source_mode=r.source_mode,
                evaluated_at=r.evaluated_at.isoformat() if r.evaluated_at else "",
                lookback_hours=r.lookback_hours,
                factors=r.factors if r.factors else [],
                checks=r.checks if r.checks else [],
                zone=r.zone if r.zone else None,
                headline=r.headline,
                last_seen=r.last_seen.isoformat() if r.last_seen else None,
                last_position=r.last_position if r.last_position else None,
                window=fleet.window_payload(
                    r.window_mode,
                    r.window_start,
                    r.window_end,
                    r.lookback_hours,
                ),
            )
        )

    return AssessmentsResponse(
        assessments=items,
        total=total,
        offset=offset,
        limit=limit,
        source_mode=_response_source_mode(item.source_mode for item in items),
        limitation=ASSESSMENT_LIMITATION,
    )
