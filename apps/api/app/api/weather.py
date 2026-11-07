"""Optional weather context for the time of the latest AIS gap.

The route and the report snapshot helper share the same event-time lookup. The
report route is synchronous, so it uses a blocking client instead of calling
``asyncio.run`` inside FastAPI's event loop.
"""
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import fleet, risk_engine

router = APIRouter()

SOURCE = "Open-Meteo forecast/model data"
MODEL_OR_OBSERVATION = "model_forecast"
KIND = "modelled_weather"
NOTE = "Context only; conditions are model estimates and do not prove why AIS stopped."
UNAVAILABLE_REASON = "Weather data could not be retrieved for this gap; no alert was downgraded."
NO_GAP_REASON = "No qualifying AIS gap"
LIMITATIONS = [
    "Hourly model/forecast values for the grid cell nearest the AIS gap start; not in-situ measurements.",
    "Only the nearest hourly step within one hour of the gap start is used; otherwise the result is unavailable.",
    "Context only; weather does not prove why AIS stopped and does not change risk scores or evidence states.",
]
WIND_URL = "https://api.open-meteo.com/v1/forecast"
WAVE_URL = "https://marine-api.open-meteo.com/v1/marine"


def _now():
    return datetime.now(timezone.utc).isoformat()


def _select_gap(explanation):
    gaps = [g for g in explanation.gaps if g["hours"] >= risk_engine.AIS_GAP_MIN_H]
    if not gaps:
        return None, NO_GAP_REASON
    return max(gaps, key=lambda g: g["hours"]), None


def _params(gap):
    return {"latitude": gap["lat"], "longitude": gap["lon"], "past_days": 2,
            "forecast_days": 1, "timezone": "UTC"}


def _nearest(data, key, target):
    hourly = data["hourly"]
    index = min(range(len(hourly["time"])), key=lambda i: abs((datetime.fromisoformat(hourly["time"][i]).replace(tzinfo=timezone.utc) - target).total_seconds()))
    observed = datetime.fromisoformat(hourly["time"][index]).replace(tzinfo=timezone.utc)
    if abs((observed - target).total_seconds()) > 3600:
        raise ValueError("No weather data close to the gap")
    return hourly[key][index], hourly["time"][index]


def _available(wind_data, wave_data, gap):
    target = gap["start"].replace(tzinfo=timezone.utc)
    wind_kn, time = _nearest(wind_data, "wind_speed_10m", target)
    wave_m, wave_time = _nearest(wave_data, "wave_height", target)
    if wind_kn is None or wave_m is None:
        raise ValueError("Weather data unavailable at this location")
    return {
        "status": "available",
        "time_utc": time + "Z",
        "event_time_utc": target.isoformat(),
        "wave_time_utc": wave_time + "Z",
        "wind_kn": wind_kn,
        "wave_m": wave_m,
        "source": SOURCE,
        "kind": KIND,
        "model_or_observation": MODEL_OR_OBSERVATION,
        "retrieved_at": _now(),
        "latitude": gap["lat"],
        "longitude": gap["lon"],
        "note": NOTE,
        "limitations": LIMITATIONS,
    }


def _not_checked(reason):
    return {
        "status": "not_checked",
        "reason": reason,
        "retrieved_at": _now(),
        "limitations": ["No event-time weather was retrieved; no values were substituted."],
        "note": "No weather values were substituted and the risk score and evidence states are unchanged.",
    }


def _unavailable(gap=None):
    result = {
        "status": "unavailable",
        "reason": UNAVAILABLE_REASON,
        "source": SOURCE,
        "kind": KIND,
        "model_or_observation": MODEL_OR_OBSERVATION,
        "retrieved_at": _now(),
        "limitations": LIMITATIONS,
        "note": "No weather values were substituted and the risk score and evidence states are unchanged.",
    }
    if gap is not None:
        result.update(
            event_time_utc=gap["start"].replace(tzinfo=timezone.utc).isoformat(),
            latitude=gap["lat"],
            longitude=gap["lon"],
        )
    return result


@router.get("/{mmsi}")
async def vessel_weather(mmsi: int, db: Session = Depends(get_db)):
    pings, explanation = fleet.score_vessel(db, mmsi, 24)
    if explanation is None:
        raise HTTPException(404, "No recent vessel positions")
    gap, reason = _select_gap(explanation)
    if gap is None:
        return _not_checked(reason)
    params = _params(gap)
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            wind = await client.get(WIND_URL, params={**params, "hourly": "wind_speed_10m", "wind_speed_unit": "kn"})
            wave = await client.get(WAVE_URL, params={**params, "hourly": "wave_height"})
            wind.raise_for_status()
            wave.raise_for_status()
        return _available(wind.json(), wave.json(), gap)
    except (httpx.HTTPError, ValueError, KeyError, TypeError, IndexError):
        return _unavailable(gap)


def event_weather_context(db: Session, mmsi: int):
    """Capture fresh event-time weather for a report snapshot.

    This is a synchronous helper for the report route, which runs in FastAPI's
    threadpool. It never calls ``asyncio.run`` and returns an explicit
    ``not_checked`` or ``unavailable`` result instead of inventing values.
    """
    _, explanation = fleet.score_vessel(db, mmsi, 24)
    if explanation is None:
        return _not_checked("No recent vessel positions available for weather timing")
    gap, reason = _select_gap(explanation)
    if gap is None:
        return _not_checked(reason)
    params = _params(gap)
    try:
        with httpx.Client(timeout=8.0) as client:
            wind = client.get(WIND_URL, params={**params, "hourly": "wind_speed_10m", "wind_speed_unit": "kn"})
            wave = client.get(WAVE_URL, params={**params, "hourly": "wave_height"})
            wind.raise_for_status()
            wave.raise_for_status()
        return _available(wind.json(), wave.json(), gap)
    except (httpx.HTTPError, ValueError, KeyError, TypeError, IndexError):
        return _unavailable(gap)
