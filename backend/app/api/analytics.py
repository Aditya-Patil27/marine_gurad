from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.schemas.health import OHITimeSeries
from typing import Optional
from datetime import datetime, timedelta
from app.demo_data import DEMO_STATS, DEMO_OHI_DATA

router = APIRouter()

@router.get("/ohi", response_model=OHITimeSeries)
async def get_ocean_health_index(
    region_id: int = Query(1, description="Region ID"),
    days: int = Query(30, description="Number of days to fetch"),
    db: Session = Depends(get_db)
):
    """Get Ocean Health Index time series data - DEMO MODE with hardcoded data"""

    dates = [item["date"] for item in DEMO_OHI_DATA["historical_data"]]
    ohi_scores = [item["score"] for item in DEMO_OHI_DATA["historical_data"]]

    # Generate temperature and pH data
    temperatures = [26.5 + i * 0.1 for i in range(len(dates))]
    ph_values = [8.1 - i * 0.01 for i in range(len(dates))]
    forecasts = [score + 1.5 for score in ohi_scores]

    return {
        "dates": dates,
        "ohi_scores": ohi_scores,
        "temperatures": temperatures,
        "ph_values": ph_values,
        "forecasts": forecasts,
    }

@router.get("/statistics")
async def get_statistics(db: Session = Depends(get_db)):
    """Get overall platform statistics - DEMO MODE with hardcoded data"""

    return DEMO_STATS
