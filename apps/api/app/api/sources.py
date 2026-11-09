"""Source health and bounded manual provider-run checkpoints.

``GET /health`` deliberately makes no provider request and writes nothing. It
reports configured/local state only; ``configured`` never means available. The
per-source limitations must travel with the values so a console cannot present
unknown coverage as live data.

``POST /runs`` is separate: it requires an Analyst (Administrator implies it)
and a matching CSRF token, runs exactly one bounded provider operation, and
persists only safe run metadata (no credentials and no raw provider payload).
"""
from datetime import date, datetime, timezone
from typing import Annotated, Literal, Union

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from app.api import aisstream, gfw
from app.api.auth import csrf_protect, require_analyst, require_viewer
from app.api.environment import select_latest_observation
from app.api.ocean import load_satellite_observations
from app.config import settings
from app.database import get_db
from app.schemas.user import UserResponse
from app.models.vessel import VesselTrack
from app.services import source_runs as run_store

router = APIRouter()

MAX_LOOKBACK_HOURS = 168
MAX_MANUAL_EVENT_DAYS = 31


def _as_utc(value):
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def replay_health(db: Session, now: datetime, lookback_hours: int = MAX_LOOKBACK_HOURS) -> dict:
    """Summarize locally stored vessel records with their recorded provenance."""
    row = db.execute(
        text(
            "SELECT count(*) AS positions, count(DISTINCT mmsi) AS vessels, "
            "max(timestamp) AS latest, "
            "array_agg(DISTINCT source_mode ORDER BY source_mode) AS source_modes "
            "FROM vessel_tracks"
        )
    ).mappings().one()
    latest = _as_utc(row["latest"])
    positions = int(row["positions"] or 0)
    age_hours = None
    if latest is not None:
        age_hours = round((now - latest).total_seconds() / 3600, 1)

    if positions == 0:
        status = "empty"
    elif age_hours is not None and age_hours > lookback_hours:
        status = "stale"
    else:
        status = "available"

    modes = sorted({mode for mode in (row.get("source_modes") or []) if mode})
    if not modes:
        mode = "unknown"
    elif len(modes) == 1:
        mode = modes[0]
    else:
        mode = "mixed"

    return {
        "source": "local vessel records",
        "kind": "local_replay_or_import",
        "status": status,
        "positions": positions,
        "vessels": int(row["vessels"] or 0),
        "latest_observed_at": latest.isoformat() if latest else None,
        "age_hours": age_hours,
        "lookback_hours": lookback_hours,
        "source_mode": mode,
        "source_modes": modes,
        "limitations": (
            "Source mode is derived from stored track rows; 'unknown' means provenance "
            "was not recorded and 'mixed' means rows disagree. It is not verified provider "
            "or receiver coverage. The current demo uses invented replay/synthetic tracks, "
            "and re-seeding is not a live feed."
        ),
    }


def prepared_sst_health(loader=None) -> dict:
    """Describe the prepared historical Copernicus subset, or its absence."""
    try:
        data = (loader or load_satellite_observations)()
        latest = select_latest_observation(data.get("values"))
    except (HTTPException, ValueError):
        return {
            "source": "Copernicus Marine Service",
            "status": "unavailable",
            "mode": "historical",
            "limitations": "Prepared Copernicus observation subset is missing, malformed or empty; no value is substituted.",
        }
    return {
        "source": data.get("source", "Copernicus Marine Service"),
        "status": "available",
        "mode": "historical",
        "kind": data.get("kind", "satellite_observation"),
        "dataset": data.get("dataset"),
        "dataset_version": data.get("dataset_version"),
        "doi": data.get("doi"),
        "latest_observed_at": latest["observed_at"],
        "value": latest["temperature_c"],
        "unit": data.get("unit"),
        "attribution": (
            f"Copernicus Marine Service (DOI: {data['doi']})" if data.get("doi") else "Copernicus Marine Service"
        ),
        "limitations": (
            "Historical satellite-derived SST for a single grid cell; not a live forecast, "
            "model output, or regional average."
        ),
    }


def gfw_health(last_run: dict | None = None) -> dict:
    health = gfw.provider_health()
    return {
        **health,
        "status": "configured" if health["configured"] else "not_configured",
        "availability": "not_checked",
        "checked_here": False,
        "last_run": last_run,
        "last_run_note": (
            "Last-run status is historical, persisted metadata only; it is not current "
            "provider availability or coverage."
        ),
    }


def aisstream_health(last_run: dict | None = None) -> dict:
    configured = bool(settings.AISSTREAM_API_KEY)
    return {
        "source": "AISStream",
        "status": "configured" if configured else "not_configured",
        "availability": "not_checked",
        "coverage": "unknown",
        "last_run": last_run,
        "last_run_note": (
            "Last-run status is historical, persisted metadata only; an empty run is not "
            "proof of absence and does not establish position coverage."
        ),
        "limitations": (
            "A configured key or a prior subscription does not establish position coverage. "
            "Use the separate snapshot route for a bounded live sample; an empty sample is not proof of absence."
        ),
    }


def open_meteo_health() -> dict:
    return {
        "source": "Open-Meteo Marine",
        "status": "not_checked",
        "availability": "not_checked",
        "kind": "modelled_marine_data",
        "limitations": "No network request is made here; values are model estimates, not observations.",
    }


def build_source_health(db: Session, now: datetime | None = None, runs: dict | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    if runs is None:
        runs = run_store.latest_runs(db)
    return {
        "checked_at": now.isoformat(),
        "external_calls": False,
        "writes": False,
        "sources": {
            "local_vessel_records": replay_health(db, now),
            "copernicus_sst": prepared_sst_health(),
            "global_fishing_watch": gfw_health(runs.get("gfw")),
            "aisstream": aisstream_health(runs.get("aisstream")),
            "open_meteo_marine": open_meteo_health(),
        },
        "limitations": (
            "Per-source status only; this endpoint does not call providers. Configured is not "
            "available, coverage or quota state may be stale or unknown, and last-run records "
            "are historical checkpoints rather than live availability."
        ),
    }


@router.get("/health")
def source_health(
    _viewer: UserResponse = Depends(require_viewer), db: Session = Depends(get_db),
) -> dict:
    """Read-only source status; no provider request and no database write."""
    return build_source_health(db)


class AisSourceRunRequest(BaseModel):
    provider: Literal["aisstream"]
    max_positions: int = Field(default=30, ge=1, le=30)
    duration_seconds: int = Field(default=12, ge=1, le=12)
    persist_positions: bool = False


class GfwSourceRunRequest(BaseModel):
    provider: Literal["gfw"]
    start_date: date
    end_date: date
    offset: int = Field(default=0, ge=0, le=10000)
    limit: int = Field(default=20, ge=1, le=50)


SourceRunRequest = Annotated[
    Union[AisSourceRunRequest, GfwSourceRunRequest],
    Field(discriminator="provider"),
]


def _finish(started_at: datetime) -> datetime:
    finished_at = datetime.now(timezone.utc)
    return finished_at if finished_at >= started_at else started_at


def _unavailable_run(*, db, payload, started_at, triggered_by, checkpoint, message, request_count=1,
                     status="unavailable", error_category=None):
    message = run_store.bounded_message(message)
    run = run_store.insert_run(
        db,
        provider=payload.provider,
        operation="ais_snapshot" if payload.provider == "aisstream" else "gfw_regional_events",
        status=status,
        mode="live" if payload.provider == "aisstream" else "historical",
        started_at=started_at,
        finished_at=_finish(started_at),
        request_count=request_count,
        position_count=0 if payload.provider == "aisstream" else None,
        event_count=None if payload.provider == "aisstream" else 0,
        error_category=error_category or run_store.error_category_for(message),
        error_message=message,
        checkpoint=checkpoint,
        triggered_by=triggered_by,
    )
    return {"run": run, "result": None}


def _snapshot_timestamp(position: dict) -> datetime:
    """Return a UTC timestamp explicitly supplied by the adapter.

    ``provider_received_at`` is preferred.  ``captured_at`` is the bounded
    snapshot reception time and is used only when AISStream did not include a
    provider reception time; it is not represented as a vessel-sent timestamp.
    """
    raw = position.get("provider_received_at") or position.get("captured_at")
    if not raw:
        raise ValueError("AIS position has no recorded reception time")
    value = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def persist_live_ais_positions(db: Session, positions: list[dict]) -> int:
    """Persist a bounded, validated AISStream sample with explicit provenance.

    This intentionally has no synthetic fallback and does not attempt to infer
    receiver coverage, vessel type, or identifiers unavailable from the live
    position message.  Duplicate messages inside one provider snapshot are
    ignored by MMSI and the recorded reception timestamp.
    """
    seen: set[tuple[int, datetime]] = set()
    inserted = 0
    try:
        for position in positions:
            mmsi = int(position["mmsi"])
            latitude = float(position["latitude"])
            longitude = float(position["longitude"])
            timestamp = _snapshot_timestamp(position)
            if not (100000000 <= mmsi <= 999999999 and 7.5 <= latitude <= 10.5 and 77.0 <= longitude <= 81.0):
                continue
            identity = (mmsi, timestamp)
            if identity in seen:
                continue
            seen.add(identity)
            db.add(VesselTrack(
                mmsi=mmsi,
                location=from_shape(Point(longitude, latitude), srid=4326),
                timestamp=timestamp,
                speed=position.get("speed_knots"),
                course=position.get("course_degrees"),
                heading=position.get("heading_degrees"),
                vessel_name=position.get("name"),
                source="AISStream bounded live snapshot",
                source_mode="live",
            ))
            inserted += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    return inserted


async def _run_aisstream(db, payload: AisSourceRunRequest, started_at, triggered_by) -> dict:
    checkpoint = {
        "bounds_lat_lon": aisstream.BOX[0],
        "max_positions": payload.max_positions,
        "duration_seconds": payload.duration_seconds,
        "persist_positions": payload.persist_positions,
        "request_count_scope": "one bounded snapshot attempt; no cache reuse",
    }
    try:
        result = await aisstream.collect_snapshot(
            max_positions=payload.max_positions,
            duration_seconds=payload.duration_seconds,
            use_cache=False,
        )
    except HTTPException as exc:
        return _unavailable_run(
            db=db, payload=payload, started_at=started_at, triggered_by=triggered_by,
            checkpoint=checkpoint, message=exc.detail,
        )
    except Exception:  # noqa: BLE001 - adapter failures become safe metadata
        return _unavailable_run(
            db=db, payload=payload, started_at=started_at, triggered_by=triggered_by,
            checkpoint=checkpoint, message="AISStream run failed unexpectedly",
            status="failed", error_category="unknown",
        )

    positions = list(result.get("positions") or [])
    persisted_positions = 0
    if payload.persist_positions and positions:
        if not settings.AISSTREAM_PERSIST_ENABLED:
            return _unavailable_run(
                db=db, payload=payload, started_at=started_at, triggered_by=triggered_by,
                checkpoint=checkpoint,
                message="AISStream position persistence is disabled pending retention approval",
                status="rejected", error_category="config", request_count=1,
            )
        try:
            persisted_positions = persist_live_ais_positions(db, positions)
        except Exception:  # no raw provider detail or database detail in an operator response
            return _unavailable_run(
                db=db, payload=payload, started_at=started_at, triggered_by=triggered_by,
                checkpoint=checkpoint, message="AISStream live positions could not be persisted",
                status="failed", error_category="unknown",
            )
    checkpoint = {
        **checkpoint,
        "captured_at": result.get("captured_at"),
        "delivery": result.get("delivery"),
        "provider_status": result.get("status"),
        "persisted_positions": persisted_positions,
    }
    run = run_store.insert_run(
        db,
        provider="aisstream",
        operation="ais_snapshot",
        status="succeeded" if positions else "empty",
        mode="live",
        started_at=started_at,
        finished_at=_finish(started_at),
        request_count=1,
        position_count=len(positions),
        checkpoint=checkpoint,
        triggered_by=triggered_by,
    )
    return {"run": run, "result": result}


async def _run_gfw(db, payload: GfwSourceRunRequest, started_at, triggered_by) -> dict:
    checkpoint = {
        "region": gfw.REGION,
        "start_date": payload.start_date.isoformat(),
        "end_date_exclusive": payload.end_date.isoformat(),
        "offset": payload.offset,
        "limit": payload.limit,
        "request_count_scope": "provider operation attempts issued by this run; internal retries are not counted separately",
    }
    days = (payload.end_date - payload.start_date).days
    if not 0 < days <= MAX_MANUAL_EVENT_DAYS:
        message = run_store.bounded_message(
            f"Manual runs require a 1 to {MAX_MANUAL_EVENT_DAYS} day range; end date is exclusive"
        )
        run = run_store.insert_run(
            db,
            provider="gfw",
            operation="gfw_regional_events",
            status="rejected",
            mode="historical",
            started_at=started_at,
            finished_at=_finish(started_at),
            request_count=0,
            event_count=0,
            error_category="validation",
            error_message=message,
            checkpoint=checkpoint,
            triggered_by=triggered_by,
        )
        raise HTTPException(422, detail={"message": message, "run": run})

    try:
        result = await gfw.fetch_regional_events(
            payload.start_date, payload.end_date, payload.offset, payload.limit, use_cache=False
        )
    except HTTPException as exc:
        return _unavailable_run(
            db=db, payload=payload, started_at=started_at, triggered_by=triggered_by,
            checkpoint=checkpoint, message=exc.detail,
        )
    except Exception:  # noqa: BLE001 - adapter failures become safe metadata
        return _unavailable_run(
            db=db, payload=payload, started_at=started_at, triggered_by=triggered_by,
            checkpoint=checkpoint, message="Global Fishing Watch run failed unexpectedly",
            status="failed", error_category="unknown",
        )

    entries = list(((result.get("data") or {}).get("entries")) or [])
    checkpoint = {
        **checkpoint,
        "delivery": result.get("delivery"),
        "retrieved_at": result.get("retrieved_at"),
        "total": (result.get("data") or {}).get("total"),
    }
    run = run_store.insert_run(
        db,
        provider="gfw",
        operation="gfw_regional_events",
        status="succeeded" if entries else "empty",
        mode="historical",
        started_at=started_at,
        finished_at=_finish(started_at),
        request_count=1,
        event_count=len(entries),
        checkpoint=checkpoint,
        triggered_by=triggered_by,
    )
    return {"run": run, "result": result}


@router.post("/runs")
async def trigger_source_run(
    payload: SourceRunRequest,
    user: UserResponse = Depends(require_analyst),
    _csrf: None = Depends(csrf_protect),
    db: Session = Depends(get_db),
) -> dict:
    """Run exactly one bounded provider operation and persist safe metadata.

    Provider failures are recorded and returned as an ``unavailable`` run; an
    out-of-range GFW window is rejected before any provider request.
    """
    started_at = datetime.now(timezone.utc)
    if settings.OFFLINE_MODE:
        raise HTTPException(409, "Offline mode is enabled; remote source runs are paused")
    if payload.provider == "aisstream":
        return await _run_aisstream(db, payload, started_at, user.username)
    return await _run_gfw(db, payload, started_at, user.username)
