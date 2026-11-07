"""Small, attributed marine-model data slice for the regional demonstration."""
from datetime import datetime, timezone
from time import monotonic
from pathlib import Path
import json

import httpx
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()
URL = "https://marine-api.open-meteo.com/v1/marine"
_cache = {}
CACHE_SECONDS = 900
OBSERVATION_FILE = Path(__file__).resolve().parents[2] / "data" / "copernicus" / "gulf_mannar_sst_20261018_20.json"


def load_satellite_observations():
    """Read the prepared, explicitly historical Copernicus observation subset."""
    try:
        with OBSERVATION_FILE.open(encoding="utf-8") as source:
            data = json.load(source)
        if data.get("dataset") != "IFREMER-GLOB-SST-L3-NRT-OBS_FULL_TIME_SERIE" or not isinstance(data.get("values"), list):
            raise ValueError("Unexpected observation artifact")
        return {"status": "available", **data}
    except (OSError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=503, detail="Prepared Copernicus observation subset unavailable") from exc


@router.get("/observations")
async def satellite_observations():
    return load_satellite_observations()


@router.get("/temperature")
async def sea_surface_temperature(
    latitude: float = Query(8.8, ge=-90, le=90),
    longitude: float = Query(78.9, ge=-180, le=180),
):
    """Return recent modelled SST at a point, with the actual provider grid cell."""
    key = (round(latitude, 3), round(longitude, 3))
    cached = _cache.get(key)
    if cached and monotonic() - cached[0] < CACHE_SECONDS:
        return {**cached[1], "delivery": "cached"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(URL, params={
                "latitude": key[0], "longitude": key[1],
                "hourly": "sea_surface_temperature", "past_days": 1,
                "forecast_days": 1, "timezone": "UTC", "cell_selection": "sea",
            })
            response.raise_for_status()
            data = response.json()
        hourly = data["hourly"]
        times, temperatures = hourly["time"], hourly["sea_surface_temperature"]
        if len(times) != len(temperatures) or data["hourly_units"]["sea_surface_temperature"] != "°C":
            raise ValueError("Unexpected marine data format or units")
        now = datetime.now(timezone.utc)
        values = []
        for timestamp, value in zip(times, temperatures):
            observed = datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc)
            if observed <= now and value is not None:
                values.append({"valid_at": observed.isoformat(), "temperature_c": value})
        if not values:
            raise ValueError("No recent sea-surface temperature values for this grid cell")
        result = {
            "status": "available", "delivery": "live", "kind": "modelled_marine_data",
            "source": "Open-Meteo Marine API; generated using E.U. Copernicus Marine Service Information",
            "source_url": "https://open-meteo.com/en/docs/marine-weather-api",
            "product": "Météo-France sea surface temperature (Open-Meteo)",
            "retrieved_at": now.isoformat(), "time_zone": "UTC", "unit": "°C",
            "requested_location": {"latitude": latitude, "longitude": longitude},
            "grid_location": {"latitude": data["latitude"], "longitude": data["longitude"]},
            "values": values,
            "limitations": "Modelled values, not direct observations; coastal grid accuracy can be limited.",
        }
        if len(_cache) >= 128:
            _cache.pop(next(iter(_cache)))
        _cache[key] = (monotonic(), result)
        return result
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=503, detail="Marine temperature data unavailable") from exc
