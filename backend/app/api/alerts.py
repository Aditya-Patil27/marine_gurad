from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid
from app.services.alert_generator import AlertGenerator

router = APIRouter()

class Alert(BaseModel):
    id: str
    type: str  # POLLUTION, IUU_FISHING, MPA_VIOLATION
    severity: str  # HIGH, MEDIUM, LOW
    title: str
    description: str
    timestamp: datetime
    location: dict
    metadata: Optional[dict] = None

@router.get("/", response_model=List[Alert])
def get_alerts(
    limit: int = Query(50, ge=1, le=100),
    severity: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get active alerts with predictive warnings from database.
    
    Optimized to avoid N+1 query problem - vessel coordinates are now
    included directly in the alert data from AlertGenerator.
    """

    # Use AlertGenerator to generate real-time alerts
    alert_gen = AlertGenerator(db)
    raw_alerts = alert_gen.check_mpa_violations()

    alerts = []

    for alert in raw_alerts:
        # Filter by severity if specified
        severity_map = {"critical": "HIGH", "high": "HIGH", "medium": "MEDIUM", "low": "LOW"}
        severity_upper = severity_map.get(alert["severity"], "MEDIUM")
        if severity and severity_upper != severity.upper():
            continue

        # Extract location directly from alert data (no additional query needed)
        # AlertGenerator now includes lat/lon coordinates via SQL JOIN
        location = {}
        if "lat" in alert and "lon" in alert:
            location = {"lat": alert["lat"], "lon": alert["lon"]}

        # Generate title and description based on alert type
        title = ""
        description = ""

        if alert["type"] == "MPA_VIOLATION":
            title = f"MPA Violation Detected - {alert.get('mpa_name', 'Unknown MPA')}"
            description = f"Vessel {alert['mmsi']} is currently inside {alert.get('mpa_name', 'protected area')}. Risk score: {alert['risk_score']:.2f}"
        elif alert["type"] == "MPA_APPROACH_PREDICTED":
            title = f"Predicted MPA Violation - {alert.get('mpa_name', 'Unknown MPA')}"
            description = f"Vessel {alert['mmsi']} is predicted to enter {alert.get('mpa_name', 'protected area')} in {alert.get('estimated_time', 'unknown time')}. Distance: {alert.get('distance_km', 0):.2f}km"
        elif alert["type"] == "MPA_APPROACH":
            title = f"Vessel Near MPA - {alert.get('mpa_name', 'Unknown MPA')}"
            description = f"Vessel {alert['mmsi']} is within {alert.get('distance_km', 0):.2f}km of {alert.get('mpa_name', 'protected area')}"

        # Generate unique alert ID using UUID to prevent collisions
        # when same vessel triggers multiple alerts of the same type
        alert_id = f"{alert['type']}_{alert['mmsi']}_{uuid.uuid4().hex[:8]}"

        alerts.append({
            "id": alert_id,
            "type": alert["type"],
            "severity": severity_upper,
            "title": title,
            "description": description,
            "timestamp": datetime.utcnow(),
            "location": location,
            "metadata": {k: v for k, v in alert.items() if k not in ["type", "severity", "mmsi", "lat", "lon"]}
        })

    # Sort by severity (HIGH first), then risk score (highest first)
    severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    alerts.sort(key=lambda x: (severity_order.get(x["severity"], 3), -(x["metadata"].get("risk_score") or 0)))

    return alerts[:limit]
