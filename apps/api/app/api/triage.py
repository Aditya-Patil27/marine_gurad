"""Read-only reviewer triage over persisted assessment, alert and case state."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.auth import require_viewer
from app.database import get_db
from app.schemas.user import UserResponse

router = APIRouter()

LIMITATION = (
    "Triage is a deterministic review queue over persisted screening artefacts. "
    "It is not proof of an offence, does not infer provider coverage, and does "
    "not change any risk score or case/alert status."
)
WEATHER_NOT_CHECKED = {
    "status": "not_checked",
    "reason": "This read-only triage view does not fetch weather; unavailable weather never lowers risk or review priority.",
}


def review_state(level: str | None, open_cases: int, high_alerts: int) -> str:
    """Apply the published review ordering without altering underlying evidence."""
    if open_cases > 0:
        return "under_review"
    if high_alerts > 0 or str(level or "").upper() == "HIGH":
        return "needs_review"
    return "monitor"


@router.get("/assessments")
def list_triage(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    mmsi: Optional[int] = Query(None, ge=100000000, le=999999999),
    _viewer: UserResponse = Depends(require_viewer),
    db: Session = Depends(get_db),
) -> dict:
    """Return persisted review priorities without provider calls or writes."""
    params = {"limit": limit, "offset": offset, "mmsi": mmsi}
    where = "WHERE a.mmsi = :mmsi" if mmsi is not None else ""
    total = int(db.execute(text(f"SELECT count(*) FROM vessel_assessments a {where}"), params).scalar() or 0)
    rows = db.execute(text(f"""
        SELECT a.id, a.mmsi, a.vessel_name, a.score, a.level, a.rule_version,
               a.source_mode, a.evaluated_at, a.last_seen,
               (SELECT count(*) FROM alert_records ar WHERE ar.mmsi = a.mmsi) AS alerts_total,
               (SELECT count(*) FROM alert_records ar WHERE ar.mmsi = a.mmsi AND ar.status = 'open') AS alerts_open,
               (SELECT count(*) FROM alert_records ar WHERE ar.mmsi = a.mmsi AND ar.status = 'acknowledged') AS alerts_acknowledged,
               (SELECT count(*) FROM alert_records ar WHERE ar.mmsi = a.mmsi AND ar.status = 'resolved') AS alerts_resolved,
               (SELECT count(*) FROM alert_records ar WHERE ar.mmsi = a.mmsi AND ar.severity = 'HIGH' AND ar.status IN ('open', 'acknowledged')) AS alerts_high_active,
               (SELECT count(*) FROM investigation_cases ic WHERE ic.mmsi = a.mmsi AND ic.status = 'open') AS cases_open,
               (SELECT count(*) FROM investigation_cases ic WHERE ic.mmsi = a.mmsi AND ic.status = 'closed') AS cases_closed
        FROM vessel_assessments a
        {where}
        ORDER BY
          CASE WHEN EXISTS (SELECT 1 FROM investigation_cases ic WHERE ic.mmsi = a.mmsi AND ic.status = 'open') THEN 0
               WHEN a.level = 'HIGH' OR EXISTS (SELECT 1 FROM alert_records ar WHERE ar.mmsi = a.mmsi AND ar.severity = 'HIGH' AND ar.status IN ('open', 'acknowledged')) THEN 1
               ELSE 2 END,
          a.score DESC, a.evaluated_at DESC
        LIMIT :limit OFFSET :offset
    """), params).mappings().all()
    items = []
    for row in rows:
        mapping = dict(row)
        open_cases = int(mapping.pop("cases_open") or 0)
        high_alerts = int(mapping.pop("alerts_high_active") or 0)
        alerts = {
            "total": int(mapping.pop("alerts_total") or 0), "open": int(mapping.pop("alerts_open") or 0),
            "acknowledged": int(mapping.pop("alerts_acknowledged") or 0), "resolved": int(mapping.pop("alerts_resolved") or 0),
            "high_active": high_alerts,
        }
        cases = {"open": open_cases, "closed": int(mapping.pop("cases_closed") or 0)}
        items.append({
            **mapping,
            "id": str(mapping["id"]),
            "review_state": review_state(mapping.get("level"), open_cases, high_alerts),
            "alerts": alerts,
            "cases": cases,
        })
    return {"items": items, "total": total, "offset": offset, "limit": limit,
            "weather": WEATHER_NOT_CHECKED, "limitation": LIMITATION}
