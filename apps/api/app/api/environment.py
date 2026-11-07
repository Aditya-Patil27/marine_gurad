"""Regional environmental reading adapter for frontend map/evidence cards."""
import math
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException

from app.api.ocean import load_satellite_observations

router = APIRouter()


def select_latest_observation(values):
    """Deterministically choose the observation with the latest timestamp.

    Ties are broken stably by higher latitude, then higher longitude.
    Validates presence of required fields: observed_at, latitude, longitude, temperature_c.
    """
    if not isinstance(values, list) or not values:
        raise ValueError("Observation values list is empty or invalid")

    valid_candidates = []
    for item in values:
        if not isinstance(item, dict):
            continue
        observed_at = item.get("observed_at")
        lat = item.get("latitude")
        lon = item.get("longitude")
        temp = item.get("temperature_c")
        if observed_at is None or lat is None or lon is None or temp is None:
            continue
        if not isinstance(observed_at, str) or not observed_at.strip():
            continue
        try:
            timestamp = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                continue
            lat_f = float(lat)
            lon_f = float(lon)
            temp_f = float(temp)
        except (ValueError, TypeError):
            continue
        if (
            any(isinstance(value, bool) for value in (lat, lon, temp))
            or not all(math.isfinite(value) for value in (lat_f, lon_f, temp_f))
            or not -90 <= lat_f <= 90
            or not -180 <= lon_f <= 180
        ):
            continue
        valid_candidates.append({
            "observed_at": observed_at,
            "_timestamp": timestamp.astimezone(timezone.utc),
            "latitude": lat_f,
            "longitude": lon_f,
            "temperature_c": temp_f,
        })

    if not valid_candidates:
        raise ValueError("No valid observation candidates found")

    # Deterministic sort: latest timestamp first, tie-break by higher lat, then higher lon
    valid_candidates.sort(
        key=lambda c: (c["_timestamp"], c["latitude"], c["longitude"]),
        reverse=True
    )
    selected = valid_candidates[0]
    return {key: value for key, value in selected.items() if key != "_timestamp"}


@router.get("/regional")
async def regional_environment():
    """Return latest regional environmental reading for frontend environmental card.

    Provides B's five expected fields:
      - variable
      - value
      - unit
      - observed_at
      - attribution
    along with explicit mode, kind, coordinates, dataset metadata, and limitations.
    Values are strictly derived from the prepared Copernicus satellite observation artifact.
    """
    try:
        data = load_satellite_observations()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Prepared Copernicus observation subset unavailable") from exc

    values = data.get("values")
    try:
        latest = select_latest_observation(values)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail="No valid observation reading available in subset") from exc

    if data.get("unit") != "°C":
        raise HTTPException(status_code=503, detail="Unexpected observation unit")
    unit = data["unit"]
    doi = data.get("doi")
    attribution = "Copernicus Marine Service"
    if doi:
        attribution = f"Copernicus Marine Service (DOI: {doi})"

    return {
        # B's five core fields
        "variable": "Historical satellite-derived sea surface temperature (single grid cell)",
        "value": latest["temperature_c"],
        "unit": unit,
        "observed_at": latest["observed_at"],
        "attribution": attribution,
        # Explicit status, mode, location and dataset metadata
        "status": "available",
        "mode": "historical",
        "kind": data.get("kind", "satellite_observation"),
        "source": data.get("source", "Copernicus Marine Service"),
        "product": data.get("product"),
        "dataset": data.get("dataset"),
        "dataset_version": data.get("dataset_version"),
        "doi": doi,
        "location": {
            "latitude": latest["latitude"],
            "longitude": latest["longitude"],
        },
        "limitations": (
            "Historical satellite-derived SST for a single grid cell; not a live forecast, "
            "model output, or regional average."
        ),
    }
