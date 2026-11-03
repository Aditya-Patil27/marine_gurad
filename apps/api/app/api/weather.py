"""Optional weather context for the time of the latest AIS gap."""
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import fleet, risk_engine

router = APIRouter()


@router.get("/{mmsi}")
async def vessel_weather(mmsi: int, db: Session = Depends(get_db)):
    pings, explanation = fleet.score_vessel(db, mmsi, 24)
    if explanation is None:
        raise HTTPException(404, "No recent vessel positions")
    gaps = [g for g in explanation.gaps if g["hours"] >= risk_engine.AIS_GAP_MIN_H]
    if not gaps:
        return {"status": "not_checked", "reason": "No qualifying AIS gap"}
    gap = max(gaps, key=lambda g: g["hours"])
    target = gap["start"].replace(tzinfo=timezone.utc)
    params = {"latitude": gap["lat"], "longitude": gap["lon"], "past_days": 2,
              "forecast_days": 1, "timezone": "UTC"}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            wind = await client.get("https://api.open-meteo.com/v1/forecast", params={**params, "hourly": "wind_speed_10m", "wind_speed_unit": "kn"})
            wave = await client.get("https://marine-api.open-meteo.com/v1/marine", params={**params, "hourly": "wave_height"})
            wind.raise_for_status()
            wave.raise_for_status()
        def nearest(data, key):
            hourly = data["hourly"]
            index = min(range(len(hourly["time"])), key=lambda i: abs((datetime.fromisoformat(hourly["time"][i]).replace(tzinfo=timezone.utc) - target).total_seconds()))
            observed = datetime.fromisoformat(hourly["time"][index]).replace(tzinfo=timezone.utc)
            if abs((observed - target).total_seconds()) > 3600:
                raise ValueError("No weather data close to the gap")
            return hourly[key][index], hourly["time"][index]
        wind_kn, time = nearest(wind.json(), "wind_speed_10m")
        wave_m, _ = nearest(wave.json(), "wave_height")
        if wind_kn is None or wave_m is None:
            raise ValueError("Weather data unavailable at this location")
        return {"status": "available", "time_utc": time + "Z", "wind_kn": wind_kn, "wave_m": wave_m,
                "source": "Open-Meteo forecast/model data", "latitude": gap["lat"], "longitude": gap["lon"],
                "note": "Context only; conditions are model estimates and do not prove why AIS stopped."}
    except (httpx.HTTPError, ValueError, KeyError, TypeError, IndexError):
        return {"status": "unavailable", "reason": "Weather data could not be retrieved for this gap; no alert was downgraded."}
