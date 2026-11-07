"""Bounded, read-only live AISStream snapshot; does not mix demo tracks into the database."""
import asyncio
import json
from datetime import datetime, timezone
from time import monotonic

import websockets
from fastapi import APIRouter, HTTPException, Query

from app.config import settings

router = APIRouter()
URL = "wss://stream.aisstream.io/v0/stream"
# Gulf of Mannar, latitude then longitude, for an initial bounded trial.
BOX = [[[7.5, 77.0], [10.5, 81.0]]]
_lock = asyncio.Lock()
_cached = {}


def normalize(message):
    if message.get("MessageType") != "PositionReport":
        return None
    metadata = message.get("MetaData") or {}
    report = (message.get("Message") or {}).get("PositionReport") or {}
    try:
        mmsi = int(metadata.get("MMSI") or report["UserID"])
        lat = float(report.get("Latitude", metadata.get("latitude", metadata.get("Latitude"))))
        lon = float(report.get("Longitude", metadata.get("longitude", metadata.get("Longitude"))))
        if report.get("Valid") is False or not (100000000 <= mmsi <= 999999999 and 7.5 <= lat <= 10.5 and 77 <= lon <= 81):
            return None
        received = datetime.now(timezone.utc)
        # AIS position reports carry only the UTC second, not a complete timestamp.
        # Use the provider reception time when present; never infer the missing date.
        raw_time = metadata.get("time_utc") or metadata.get("TimeUTC")
        provider_time = None
        if raw_time:
            parsed = datetime.fromisoformat(str(raw_time).replace("Z", "+00:00"))
            provider_time = (parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)).isoformat()
        speed = report.get("Sog")
        course = report.get("Cog")
        heading = report.get("TrueHeading")
        return {"mmsi": mmsi, "latitude": lat, "longitude": lon,
                "name": str(metadata.get("ShipName") or "").strip() or None,
                "speed_knots": speed if isinstance(speed, (int, float)) and 0 <= speed < 102.3 else None,
                "course_degrees": course if isinstance(course, (int, float)) and 0 <= course < 360 else None,
                "heading_degrees": heading if isinstance(heading, (int, float)) and 0 <= heading < 360 else None,
                "provider_received_at": provider_time, "captured_at": received.isoformat()}
    except (KeyError, ValueError, TypeError, OverflowError):
        return None


async def collect_snapshot(max_positions: int = 30, duration_seconds: int = 12, use_cache: bool = True):
    """Collect a bounded live AIS sample; used by the read route and manual runs."""
    if not settings.AISSTREAM_API_KEY:
        raise HTTPException(503, "AISStream credentials are not configured")
    key = (max_positions, duration_seconds)
    async with _lock:
        cached = _cached.get(key)
        if use_cache and cached is not None and monotonic() - cached[0] < 30:
            return {**cached[1], "delivery": "cached"}
        positions = []
        confirmed = False
        try:
            async with websockets.connect(URL, open_timeout=8, close_timeout=2, max_size=1048576) as ws:
                await ws.send(json.dumps({"APIKey": settings.AISSTREAM_API_KEY,
                                          "BoundingBoxes": BOX,
                                          "FilterMessageTypes": ["PositionReport"]}))
                deadline = monotonic() + duration_seconds
                while len(positions) < max_positions and monotonic() < deadline:
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=max(0.01, deadline - monotonic()))
                    except asyncio.TimeoutError:
                        break
                    message = json.loads(raw)
                    if message.get("MessageType") == "SubscriptionConfirmation":
                        confirmed = True
                    position = normalize(message)
                    if position:
                        positions.append(position)
        except (OSError, asyncio.TimeoutError, websockets.exceptions.WebSocketException, ValueError):
            raise HTTPException(503, "AISStream connection unavailable; check provider access and connection limits")
        if not confirmed:
            raise HTTPException(503, "AISStream subscription was not confirmed")
        result = {"status": "available", "source": "AISStream", "mode": "live",
                  "delivery": "live", "captured_at": datetime.now(timezone.utc).isoformat(),
                  "bounds_lat_lon": BOX[0], "max_positions": max_positions,
                  "duration_seconds": duration_seconds, "positions": positions,
                  "limitations": "Snapshot only; coverage is unknown, messages can be missed, and timestamps are provider reception times when available."}
        if len(_cached) >= 8:
            _cached.pop(next(iter(_cached)))
        _cached[key] = (monotonic(), result)
        return result


@router.get("/snapshot")
async def snapshot(max_positions: int = Query(30, ge=1, le=30),
                   duration_seconds: int = Query(12, ge=1, le=12)):
    """Collect up to 30 live AIS positions for at most 12 seconds; no persistence."""
    return await collect_snapshot(max_positions=max_positions, duration_seconds=duration_seconds)
