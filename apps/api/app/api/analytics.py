from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from app.config import settings
from app.database import get_db
from app.schemas.health import OHITimeSeries
from app.models.health import OceanHealthMetric
from app.models.vessel import VesselTrack
from app.models.pollution import PollutionEvent
from app.models.mpa import MarineProtectedArea
from typing import Optional
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/ohi", response_model=OHITimeSeries)
def get_ocean_health_index(
    region_id: int = Query(1, description="Region ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days to fetch"),
    db: Session = Depends(get_db)
):
    """Get Ocean Health Index time series data from database"""

    # Query ocean health metrics from database
    query = text("""
        SELECT
            date,
            ohi_score,
            temperature,
            ph,
            forecasted_score
        FROM ocean_health_metrics
        WHERE region_id = :region_id
        AND date >= CURRENT_DATE - INTERVAL '1 day' * :days
        ORDER BY date ASC
    """)

    result = db.execute(query, {"region_id": region_id, "days": days})

    dates = []
    ohi_scores = []
    temperatures = []
    ph_values = []
    forecasts = []

    for row in result:
        dates.append(row.date.isoformat() if row.date else None)
        ohi_scores.append(row.ohi_score or 0.0)
        temperatures.append(row.temperature or 0.0)
        ph_values.append(row.ph or 0.0)
        forecasts.append(row.forecasted_score)

    return {
        "dates": dates,
        "ohi_scores": ohi_scores,
        "temperatures": temperatures,
        "ph_values": ph_values,
        "forecasts": forecasts,
    }

@router.get("/statistics")
def get_statistics(db: Session = Depends(get_db)):
    """Get overall platform statistics from database"""

    # Count active vessels (last 24 hours)
    vessels_query = text("""
        SELECT COUNT(DISTINCT mmsi) as count
        FROM vessel_tracks
        WHERE timestamp > NOW() - INTERVAL '24 hours'
    """)
    vessels_result = db.execute(vessels_query).fetchone()
    active_vessels = vessels_result.count if vessels_result else 0

    # Count dark vessels
    dark_vessels_query = text("""
        SELECT COUNT(DISTINCT mmsi) as count
        FROM vessel_tracks
        WHERE is_dark = true
        AND timestamp > NOW() - INTERVAL '24 hours'
    """)
    dark_vessels_result = db.execute(dark_vessels_query).fetchone()
    dark_vessels = dark_vessels_result.count if dark_vessels_result else 0

    # Count high-risk vessels (the dashboard's "High Risk" tile)
    high_risk_query = text("""
        SELECT COUNT(DISTINCT mmsi) as count
        FROM vessel_tracks
        WHERE risk_score > :threshold
        AND timestamp > NOW() - INTERVAL '24 hours'
    """)
    high_risk_result = db.execute(high_risk_query, {"threshold": settings.IUU_RISK_THRESHOLD}).fetchone()
    high_risk_vessels = high_risk_result.count if high_risk_result else 0

    # Count pollution events (last 7 days)
    pollution_query = text("""
        SELECT COUNT(*) as count
        FROM pollution_events
        WHERE detected_at > NOW() - INTERVAL '7 days'
    """)
    pollution_result = db.execute(pollution_query).fetchone()
    pollution_events = pollution_result.count if pollution_result else 0

    # Count MPAs
    mpa_query = text("""
        SELECT COUNT(*) as count
        FROM marine_protected_areas
    """)
    mpa_result = db.execute(mpa_query).fetchone()
    mpas_monitored = mpa_result.count if mpa_result else 0

    # Calculate average OHI score (last 30 days)
    ohi_query = text("""
        SELECT AVG(ohi_score) as avg_score
        FROM ocean_health_metrics
        WHERE date >= CURRENT_DATE - INTERVAL '30 days'
    """)
    ohi_result = db.execute(ohi_query).fetchone()
    avg_ohi = round(ohi_result.avg_score, 1) if ohi_result and ohi_result.avg_score else 0.0

    return {
        "active_vessels": active_vessels,
        "dark_vessels": dark_vessels,
        "high_risk_vessels": high_risk_vessels,
        "pollution_events": pollution_events,
        "mpas_monitored": mpas_monitored,
        "avg_ocean_health": avg_ohi,
    }
