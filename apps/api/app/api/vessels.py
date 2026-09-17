from dataclasses import asdict
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import fleet, risk_engine

router = APIRouter()


def _json(value: Any) -> Any:
    """Naive UTC datetimes become ISO strings with Z so browsers don't read them as local time."""
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds") + "Z"
    if isinstance(value, dict):
        return {k: _json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json(v) for v in value]
    return value


def _state(exp: risk_engine.Explanation) -> str:
    if exp.level == "high":
        return "flagged"
    if exp.level == "medium":
        return "watch"
    return "tracked"


def _summary(pings, exp):
    last = pings[-1]
    return {
        "mmsi": last.mmsi,
        "name": last.name,
        "vessel_type": last.vessel_type,
        "length": last.length,
        "last_seen": last.t,
        "position": {"lat": last.lat, "lon": last.lon},
        "course": last.course,
        "speed": last.speed,
        "score": exp.score,
        "level": exp.level,
        "state": _state(exp),
        "headline": risk_engine.headline(last, exp),
        "reasons": [f.label for f in exp.factors],
        "dark": any(f.key == "ais_gap" and f.evidence.get("open") for f in exp.factors),
    }


@router.get("/")
def list_vessels(
    hours: int = Query(24, ge=1, le=72, description="Look-back window"),
    db: Session = Depends(get_db),
):
    """Every vessel seen in the window with its explainable risk score, highest first."""
    results = fleet.score_fleet(db, hours)
    return _json({
        "generated_at": fleet.utcnow(),
        "threshold": risk_engine.ALERT_THRESHOLD,
        "vessels": [_summary(own, exp) for own, exp in results],
    })


@router.get("/{mmsi}")
def get_vessel(
    mmsi: int,
    hours: int = Query(24, ge=1, le=72),
    db: Session = Depends(get_db),
):
    """One vessel: track, score breakdown, checks, what would clear the alert, gaps and encounters."""
    pings, exp = fleet.score_vessel(db, mmsi, hours)
    if exp is None:
        raise HTTPException(status_code=404, detail=f"No positions for MMSI {mmsi} in the last {hours} h")
    return _json({
        **_summary(pings, exp),
        "generated_at": fleet.utcnow(),
        "threshold": exp.threshold,
        "max_points": risk_engine.MAX_POINTS,
        "zone": exp.zone,
        "factors": [asdict(f) for f in exp.factors],
        "checks": [asdict(c) for c in exp.checks],
        "clear_if": exp.clear_if,
        "gaps": [{k: v for k, v in g.items() if k not in ("lat", "lon")} for g in exp.gaps],
        "encounters": exp.encounters,
        "track": [
            {"t": p.t, "lat": p.lat, "lon": p.lon, "speed": p.speed, "course": p.course}
            for p in pings
        ],
    })
