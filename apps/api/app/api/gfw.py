"""Small server-side Global Fishing Watch vessel identity adapter."""
import asyncio
import hashlib
import json
import math
from collections import deque
from datetime import date, datetime, timezone
from time import monotonic

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.config import settings
from app.api.ocean import load_satellite_observations
from app.services.provider_pacing import GfwPacer

router = APIRouter()
URL = "https://gateway.api.globalfishingwatch.org/v3/vessels/search"
DATASET = "public-global-vessel-identity:latest"
EVENTS_DATASET = "public-global-fishing-events:latest"
EVENTS_URL = "https://gateway.api.globalfishingwatch.org/v3/events"
REGION = {"type": "Polygon", "coordinates": [[[77, 7.5], [81, 7.5], [81, 10.5], [77, 10.5], [77, 7.5]]]}
RATE_HEADERS = (
    "daily-limit-requests", "monthly-limit-requests", "daily-remaining-requests",
    "monthly-remaining-requests", "daily-current-usage", "monthly-current-usage",
    "daily-reset-hours", "monthly-reset-days",
)
_lock = asyncio.Lock()
_cache = {}
_rate = {}
_rate_checked_at = None
_rate_checked_monotonic = 0.0
_last_request_at = 0.0
_blocked_until = 0.0
_recent_requests = deque()
_pacer = GfwPacer()


def _prune_requests(now):
    while _recent_requests and now - _recent_requests[0] >= 1800:
        _recent_requests.popleft()


def _capture_headers(headers):
    global _rate, _rate_checked_at, _rate_checked_monotonic
    found = {}
    for suffix in RATE_HEADERS:
        value = headers.get("x-ratelimit-" + suffix)
        if value is not None:
            try:
                found[suffix.replace("-", "_")] = int(value)
            except ValueError:
                pass
    if found:
        _rate = found
        _rate_checked_at = datetime.now(timezone.utc).isoformat()
        _rate_checked_monotonic = monotonic()
        _pacer.store_rate(found, _rate_checked_at)


def provider_health():
    """Read-only snapshot of configured state and locally observed quota headers.

    This never calls the provider, so it cannot claim current availability.
    Shared pacing status is reported as last observed; a Redis outage degrades
    to process-local guarding rather than failing this read.
    """
    _prune_requests(monotonic())
    shared_rate = _pacer.rate_snapshot()
    shared_values = shared_rate.get("rate") if isinstance(shared_rate, dict) else None
    rate = shared_values if isinstance(shared_values, dict) and shared_values else dict(_rate)
    observed_at = (shared_rate.get("observed_at") if isinstance(shared_rate, dict) else None) or _rate_checked_at
    return {
        "provider": "Global Fishing Watch",
        "configured": bool(settings.GFW_API_TOKEN),
        "rate_limits": rate,
        "rate_limits_observed_at": observed_at,
        "local_requests_last_30_minutes": len(_recent_requests),
        "pacing": _pacer.status(),
        "limitations": "Provider usage counters can lag by 30 minutes; local state is per process and resets on restart. Shared pacing is best-effort and does not guarantee account-wide quota compliance.",
    }


@router.get("/status")
async def status():
    return provider_health()



async def _fetch(url, params, cache_key, dataset, limitations, body=None, use_cache=True):
    global _last_request_at, _blocked_until
    if not settings.GFW_API_TOKEN:
        raise HTTPException(503, "Global Fishing Watch token is not configured")
    async with _lock:
        cached = _cache.get(cache_key)
        if use_cache and cached and monotonic() - cached[0] < 900:
            return {**cached[1], "delivery": "cached"}
        if monotonic() < _blocked_until or _pacer.blocked_seconds() > 0:
            raise HTTPException(503, "Global Fishing Watch is rate limited; retry after the provider reset")
        _prune_requests(monotonic())
        recent = len(_recent_requests)
        if sum(monotonic() - request_time < 60 for request_time in _recent_requests) >= 60:
            raise HTTPException(503, "Local Global Fishing Watch request pace is limited; retry later")
        # Counters are updated by the provider every 30 minutes. Reject new queries
        # conservatively near exhaustion and periodically allow fresh headers.
        if monotonic() - _rate_checked_monotonic < 1860 and (
            _rate.get("daily_remaining_requests", 100 + recent) - recent < 100 or
            _rate.get("monthly_remaining_requests", 1000 + recent) - recent < 1000
        ):
            raise HTTPException(503, "Global Fishing Watch quota is low; retry after the provider's next usage check")
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                for attempt in range(3):
                    delay = max(0.0, 1.0 - (monotonic() - _last_request_at))
                    if delay:
                        await asyncio.sleep(delay)
                    if not _pacer.try_acquire():
                        raise HTTPException(503, "Global Fishing Watch request pacing is limited across processes; retry later")
                    _last_request_at = monotonic()
                    _recent_requests.append(_last_request_at)
                    headers = {"Authorization": f"Bearer {settings.GFW_API_TOKEN}"}
                    if body is None:
                        response = await client.get(url, params=params, headers=headers)
                    else:
                        response = await client.post(url, params=params, json=body, headers=headers)
                    _capture_headers(response.headers)
                    if response.status_code in (500, 502, 503, 504) and attempt < 2:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    if response.status_code == 429:
                        # Provider reset headers are coarse; allow rechecks at most
                        # every 30 minutes when no Retry-After is supplied.
                        try:
                            retry_after = float(response.headers.get("retry-after", "1800"))
                        except ValueError:
                            retry_after = 1800
                        _blocked_until = monotonic() + min(max(retry_after, 60), 86400)
                        _pacer.block(min(max(retry_after, 60), 86400))
                        raise HTTPException(503, "Global Fishing Watch rate limit reached; check source status and retry after reset")
                    if response.status_code in (401, 403):
                        raise HTTPException(503, "Global Fishing Watch authentication or dataset access failed")
                    response.raise_for_status()
                    data = response.json()
                    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
                        raise ValueError("Unexpected response")
                    result = {"source": "Global Fishing Watch", "dataset": dataset,
                              "source_url": "https://globalfishingwatch.org/our-apis/documentation/",
                              "retrieved_at": datetime.now(timezone.utc).isoformat(), "delivery": "live",
                              "limitations": limitations,
                              "data": data}
                    if len(_cache) >= 128:
                        _cache.pop(next(iter(_cache)))
                    _cache[cache_key] = (monotonic(), result)
                    return result
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise HTTPException(503, "Global Fishing Watch data is unavailable") from exc


@router.get("/vessels/search")
async def search_vessels(query: str = Query(..., min_length=3, max_length=100)):
    """Search identities; records are not live positions or proof of activity."""
    query = query.strip()
    if len(query) < 3:
        raise HTTPException(422, "Search requires at least three non-space characters")
    return await _fetch(URL, {"query": query, "datasets[0]": DATASET}, ("vessel", query), DATASET,
                        "Identity records are not live positions and do not establish illegal activity.")


async def fetch_regional_events(start_date: date, end_date: date, offset: int = 0, limit: int = 20,
                                use_cache: bool = True):
    """Fetch one bounded page of historical regional fishing events.

    Shared by the read route and the authenticated manual-run trigger so both
    enforce the same region, date and pagination limits. Never reaches the
    tracks or SAR datasets.
    """
    if not 0 < (end_date - start_date).days <= 366:
        raise HTTPException(422, "Choose a date range between 1 and 366 days; end date is exclusive")
    body = {"datasets": [EVENTS_DATASET], "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(), "geometry": REGION}
    key = ("regional-events", start_date.isoformat(), end_date.isoformat(), offset, limit)
    result = await _fetch(EVENTS_URL, {"offset": offset, "limit": limit}, key, EVENTS_DATASET,
        "Historical, inferred apparent fishing events; not live tracking, proven fishing or evidence of illegality. End date is exclusive.", body,
        use_cache=use_cache)
    return {**result, "requested_region": REGION, "requested_start": start_date.isoformat(),
            "requested_end_exclusive": end_date.isoformat()}


@router.get("/events/regional")
async def regional_events(start_date: date = Query(...), end_date: date = Query(...),
                          offset: int = Query(0, ge=0, le=10000), limit: int = Query(20, ge=1, le=50)):
    """Query apparent fishing events in the bounded Gulf of Mannar region."""
    return await fetch_regional_events(start_date, end_date, offset, limit)


@router.get("/events/evidence")
async def export_event_evidence(event_id: str = Query(..., min_length=1, max_length=128),
                                start_date: date = Query(...), end_date: date = Query(...),
                                offset: int = Query(0, ge=0, le=10000), limit: int = Query(20, ge=1, le=50),
                                include_regional_ocean_context: bool = False):
    """Export a selected event from the requested page as a source-bound JSON snapshot."""
    page = await regional_events(start_date, end_date, offset, limit)
    selected = next((event for event in page["data"]["entries"] if event.get("id") == event_id), None)
    if selected is None:
        raise HTTPException(404, "Event not found on the requested page")
    snapshot = {"source": page["source"], "dataset": page["dataset"], "source_url": page["source_url"],
                "retrieved_at": page["retrieved_at"], "requested_region": page["requested_region"],
                "requested_start": page["requested_start"], "requested_end_exclusive": page["requested_end_exclusive"],
                "limitations": page["limitations"], "event": selected}
    if include_regional_ocean_context:
        snapshot["regional_ocean_context"] = {**load_satellite_observations(),
            "association": "Regional historical context only; not necessarily concurrent with or at the event position."}
    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return JSONResponse({"snapshot": snapshot, "sha256": hashlib.sha256(canonical).hexdigest(),
                         "integrity_note": "Checksum detects changes only when compared with a separately trusted copy; not a digital signature."},
                        headers={"Content-Disposition": "attachment; filename=gfw-event-evidence.json"})


@router.get("/events/regional/geojson")
async def regional_events_geojson(start_date: date = Query(...), end_date: date = Query(...),
                                 offset: int = Query(0, ge=0, le=10000), limit: int = Query(20, ge=1, le=50)):
    """Map one page of historical event positions; these points are not tracks."""
    page = await regional_events(start_date, end_date, offset, limit)
    features = []
    omitted = 0
    for event in page["data"]["entries"]:
        position = event.get("position") or {}
        try:
            lat, lon = float(position["lat"]), float(position["lon"])
            if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
                raise ValueError("invalid coordinates")
        except (KeyError, TypeError, ValueError):
            omitted += 1
            continue
        vessel = event.get("vessel") or {}
        features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]},
                         "properties": {"event_id": event.get("id"), "event_type": event.get("type"),
                                        "start": event.get("start"), "end": event.get("end"),
                                        "vessel_id": vessel.get("id"), "vessel_name": vessel.get("name"),
                                        "mmsi": vessel.get("ssvid"), "flag": vessel.get("flag")}})
    return {"type": "FeatureCollection", "features": features, "source": page["source"],
            "dataset": page["dataset"], "source_url": page["source_url"],
            "mode": "historical", "retrieved_at": page["retrieved_at"], "delivery": page["delivery"],
            "requested_start": page["requested_start"], "requested_end_exclusive": page["requested_end_exclusive"],
            "offset": offset, "limit": limit, "total": page["data"].get("total"), "omitted_invalid_positions": omitted,
            "limitations": "Historical inferred apparent-fishing event locations, not live positions or vessel tracks; not proof of fishing or illegality."}
