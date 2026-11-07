from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid
from app.services.alert_generator import AlertGenerator

router = APIRouter()

# Deterministic namespace so the same live projection is stable across reads.
_ALERT_NS = uuid.UUID("b2c3d4e5-f6a7-8901-bcde-f12345678901")
_SEVERITY_RANK = {"critical": 3, "high": 2, "medium": 1, "low": 0}
_SEVERITY_MAP = {"critical": "HIGH", "high": "HIGH", "medium": "MEDIUM", "low": "LOW"}


class Alert(BaseModel):
    id: str
    type: str  # POLLUTION, IUU_FISHING, MPA_VIOLATION
    severity: str  # HIGH, MEDIUM, LOW
    title: str
    description: str
    timestamp: datetime
    location: dict
    metadata: Optional[dict] = None


def alert_identity(alert: dict) -> tuple:
    """Stable deduplication key for one vessel/condition/zone projection."""
    zone = alert.get("mpa_id") or alert.get("mpa_name") or ""
    return (alert["type"], int(alert["mmsi"]), str(zone))


def alert_id(alert: dict) -> str:
    return str(uuid.uuid5(_ALERT_NS, ":".join(str(part) for part in alert_identity(alert))))


def _alert_rank(alert: dict) -> tuple:
    return (_SEVERITY_RANK.get(alert.get("severity"), 0), alert.get("risk_score") or 0)


def severity_label(alert: dict) -> str:
    """Normalize generator severity to the stored/read vocabulary."""
    return _SEVERITY_MAP.get(str(alert.get("severity") or "").lower(), "MEDIUM")


def alert_location(alert: dict) -> dict:
    if alert.get("lat") is None or alert.get("lon") is None:
        return {}
    return {"lat": alert["lat"], "lon": alert["lon"]}


def alert_title(alert: dict) -> str:
    mpa = alert.get("mpa_name", "Unknown MPA")
    if alert["type"] == "MPA_VIOLATION":
        return f"MPA Violation Detected - {mpa}"
    if alert["type"] == "MPA_APPROACH_PREDICTED":
        return f"Predicted MPA Violation - {mpa}"
    if alert["type"] == "MPA_APPROACH":
        return f"Vessel Near MPA - {mpa}"
    return ""


def alert_description(alert: dict) -> str:
    mpa = alert.get("mpa_name", "protected area")
    if alert["type"] == "MPA_VIOLATION":
        return (
            f"Vessel {alert['mmsi']} is currently inside {mpa}. "
            f"Risk score: {alert['risk_score']:.2f}"
        )
    if alert["type"] == "MPA_APPROACH_PREDICTED":
        return (
            f"Vessel {alert['mmsi']} is predicted to enter {mpa} in "
            f"{alert.get('estimated_time', 'unknown time')}. "
            f"Distance: {alert.get('distance_km', 0):.2f}km"
        )
    if alert["type"] == "MPA_APPROACH":
        return (
            f"Vessel {alert['mmsi']} is within {alert.get('distance_km', 0):.2f}km "
            f"of {mpa}"
        )
    return ""


def alert_context(alert: dict) -> dict:
    """Generator extras excluding identity, location, time and provenance."""
    return {
        key: value
        for key, value in alert.items()
        if key not in ["type", "severity", "mmsi", "lat", "lon", "timestamp",
                       "source", "source_mode"]
    }


def deduplicate_alerts(raw_alerts) -> dict:
    """Collapse generator rows by stable identity, keeping the strongest row."""
    grouped = {}
    for alert in raw_alerts:
        key = alert_identity(alert)
        current = grouped.get(key)
        if current is None or _alert_rank(alert) > _alert_rank(current):
            grouped[key] = alert
    return grouped


@router.get("/", response_model=List[Alert])
def get_alerts(
    limit: int = Query(50, ge=1, le=100),
    severity: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Return a stable, deduplicated projection of current generator alerts.

    This is still an ephemeral read: nothing is persisted, acknowledged or
    resolved here, and repeated reads intentionally share IDs for the same
    vessel/condition/zone so a client can merge duplicates safely.
    """

    # Use AlertGenerator to generate real-time alerts
    alert_gen = AlertGenerator(db)
    raw_alerts = alert_gen.check_mpa_violations()

    # Collapse duplicate generator rows deterministically before mapping.
    grouped = deduplicate_alerts(raw_alerts)

    alerts = []

    for alert in grouped.values():
        # Filter by severity if specified
        severity_upper = severity_label(alert)
        if severity and severity_upper != severity.upper():
            continue

        # Extract location directly from alert data (no additional query needed)
        # AlertGenerator now includes lat/lon coordinates via SQL JOIN
        location = alert_location(alert)

        metadata = alert_context(alert)
        metadata.update({
            "source": alert.get("source"),
            "source_mode": alert.get("source_mode"),
            "persisted": False,
            "lifecycle": "ephemeral_projection",
        })

        alerts.append({
            "id": alert_id(alert),
            "type": alert["type"],
            "severity": severity_upper,
            "title": alert_title(alert),
            "description": alert_description(alert),
            "timestamp": alert.get("timestamp") or datetime.utcnow(),
            "location": location,
            "metadata": metadata,
        })

    # Sort by severity (HIGH first), then risk score (highest first)
    severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    alerts.sort(key=lambda x: (severity_order.get(x["severity"], 3), -(x["metadata"].get("risk_score") or 0)))

    return alerts[:limit]
