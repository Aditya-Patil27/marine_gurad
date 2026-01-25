from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from app.demo_data import DEMO_ALERTS

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
async def get_alerts(
    limit: int = Query(50, le=100),
    severity: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get active alerts with predictive warnings - DEMO MODE with hardcoded data"""

    alerts = []

    for alert in DEMO_ALERTS:
        # Filter by severity if specified
        if severity and alert["severity"] != severity.upper():
            continue

        # Create location dict
        location = {}
        if "mmsi" in alert:
            # Find vessel location from demo vessels
            from app.demo_data import DEMO_VESSELS
            vessel = next((v for v in DEMO_VESSELS if v["mmsi"] == alert.get("mmsi")), None)
            if vessel:
                location = {"lat": vessel["coordinates"][1], "lon": vessel["coordinates"][0]}

        alerts.append({
            "id": str(alert["id"]),
            "type": alert["type"],
            "severity": alert["severity"],
            "title": alert["title"],
            "description": alert["description"],
            "timestamp": alert["timestamp"],
            "location": location,
            "metadata": {k: v for k, v in alert.items() if k not in ["id", "type", "severity", "title", "description", "timestamp"]}
        })

    # Sort by timestamp descending
    alerts.sort(key=lambda x: x["timestamp"], reverse=True)

    return alerts[:limit]
