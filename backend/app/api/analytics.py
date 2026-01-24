from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.schemas.health import OHITimeSeries
from typing import Optional
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/ohi", response_model=OHITimeSeries)
async def get_ocean_health_index(
    region_id: int = Query(1, description="Region ID"),
    days: int = Query(30, description="Number of days to fetch"),
    db: Session = Depends(get_db)
):
    """Get Ocean Health Index time series data"""
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    query = text("""
        SELECT 
            date,
            ohi_score,
            temperature,
            ph,
            forecasted_score
        FROM ocean_health_metrics
        WHERE region_id = :region_id
        AND date BETWEEN :start_date AND :end_date
        ORDER BY date ASC
    """)
    
    result = db.execute(
        query,
        {"region_id": region_id, "start_date": start_date, "end_date": end_date}
    )
    
    dates = []
    ohi_scores = []
    temperatures = []
    ph_values = []
    forecasts = []
    
    for row in result:
        dates.append(row.date.isoformat())
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
async def get_statistics(db: Session = Depends(get_db)):
    """Get overall platform statistics"""
    
    vessel_count_query = text("""
        SELECT COUNT(DISTINCT mmsi) as count
        FROM vessel_tracks
        WHERE timestamp > NOW() - INTERVAL '24 hours'
    """)
    
    pollution_count_query = text("""
        SELECT COUNT(*) as count
        FROM pollution_events
        WHERE detected_at > NOW() - INTERVAL '7 days'
    """)
    
    high_risk_query = text("""
        SELECT COUNT(*) as count
        FROM vessel_tracks
        WHERE risk_score > 0.7
        AND timestamp > NOW() - INTERVAL '24 hours'
    """)
    
    vessel_count = db.execute(vessel_count_query).scalar()
    pollution_count = db.execute(pollution_count_query).scalar()
    high_risk_count = db.execute(high_risk_query).scalar()
    
    return {
        "active_vessels": vessel_count or 0,
        "pollution_events_week": pollution_count or 0,
        "high_risk_vessels": high_risk_count or 0,
        "mpas_monitored": 150,  # This could be a query
    }
