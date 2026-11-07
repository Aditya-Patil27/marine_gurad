from dataclasses import asdict
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import fleet, risk_engine

router = APIRouter()


def _provided(value: Any) -> Optional[datetime]:
    """Normalise FastAPI's Query sentinel for direct (non-HTTP) callers."""
    return value if isinstance(value, datetime) else None


def _selected_window(
    hours: int,
    window_start: Optional[datetime],
    window_end: Optional[datetime],
) -> fleet.FleetWindow:
    try:
        return fleet.resolve_window(
            hours=hours,
            start=_provided(window_start),
            end=_provided(window_end),
        )
    except fleet.WindowSelectionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _window_error(mmsi: int, window: fleet.FleetWindow) -> str:
    if window.mode == "historical":
        value = window.as_dict()
        return (
            f"No positions for MMSI {mmsi} in the selected historical window "
            f"{value['start']} to {value['end']}"
        )
    return f"No positions for MMSI {mmsi} in the last {window.hours} h"


def _json(value: Any) -> Any:
    """Naive UTC datetimes become ISO strings with Z so browsers don't read them as local time."""
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds") + "Z"
    if isinstance(value, dict):
        return {k: _json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json(v) for v in value]
    return value


def _state(exp: risk_engine.Explanation) -> str:
    if exp.level == "high":
        return "flagged"
    if exp.level == "medium":
        return "watch"
    return "tracked"


def _summary(pings, exp):
    last = pings[-1]
    return {
        "mmsi": last.mmsi,
        "name": last.name,
        "vessel_type": last.vessel_type,
        "length": last.length,
        "last_seen": last.t,
        "position": {"lat": last.lat, "lon": last.lon},
        "course": last.course,
        "speed": last.speed,
        "score": exp.score,
        "level": exp.level,
        "state": _state(exp),
        "headline": risk_engine.headline(last, exp),
        "reasons": [f.label for f in exp.factors],
        "dark": any(f.key == "ais_gap" and f.evidence.get("open") for f in exp.factors),
        "source": getattr(last, "source", None),
        "source_mode": getattr(last, "source_mode", None),
    }


@router.get("/")
def list_vessels(
    hours: int = Query(168, ge=1, le=168, description="Rolling look-back window; ignored when window_start/window_end are supplied"),
    window_start: Optional[datetime] = Query(
        None,
        description="Explicit historical window start in UTC (ISO 8601 with Z or offset); requires window_end",
    ),
    window_end: Optional[datetime] = Query(
        None,
        description="Explicit historical window end in UTC (ISO 8601 with Z or offset, inclusive); requires window_start",
    ),
    db: Session = Depends(get_db),
):
    """Every vessel seen in the selected window with its explainable risk score, highest first."""
    window = _selected_window(hours, window_start, window_end)
    results = fleet.score_fleet(db, window=window)
    return _json({
        "generated_at": fleet.utcnow(),
        "threshold": risk_engine.ALERT_THRESHOLD,
        "window": window.as_dict(),
        "vessels": [_summary(own, exp) for own, exp in results],
    })


def get_vessel_limitations() -> list[dict[str, str]]:
    """Return explicit, honest data limitations for vessel detail and report snapshots.

    Returns a freshly instantiated list of keyed objects compatible with User B's
    DataLimitations component ({key, label, detail}).
    """
    return [
        {
            "key": "source_mode",
            "label": "Source and receiver coverage",
            "detail": (
                "Each response carries stored track provenance (`source`, `source_mode`). "
                "`unknown` means provenance was not recorded and `mixed` means positions disagree; "
                "shore and satellite reception coverage remains unknown and must not be assumed complete."
            ),
        },
        {
            "key": "indicators_not_proof",
            "label": "Investigation indicators",
            "detail": (
                "AIS gaps, loitering events, and encounters are investigative indicators, not proof of "
                "intent, transshipment, or an offence."
            ),
        },
        {
            "key": "boundaries",
            "label": "Protected-area boundaries",
            "detail": (
                "Marine protected area boundaries in the demonstration environment are indicative; official "
                "coordinates, gazetted limits, and applicable local fishing restrictions must be separately verified."
            ),
        },
        {
            "key": "heuristic_score",
            "label": "Heuristic risk score",
            "detail": (
                "The rule-based score is an explainable screening heuristic, not a validated statistical probability "
                "or legal determination."
            ),
        },
    ]


@router.get("/{mmsi}")
def get_vessel(
    mmsi: int,
    hours: int = Query(168, ge=1, le=168, description="Rolling look-back window; ignored when window_start/window_end are supplied"),
    db: Session = Depends(get_db),
    window_start: Optional[datetime] = Query(
        None,
        description="Explicit historical window start in UTC (ISO 8601 with Z or offset); requires window_end",
    ),
    window_end: Optional[datetime] = Query(
        None,
        description="Explicit historical window end in UTC (ISO 8601 with Z or offset, inclusive); requires window_start",
    ),
):
    """One vessel: track, score breakdown, checks, what would clear the alert, gaps and encounters."""
    window = _selected_window(hours, window_start, window_end)
    pings, exp = fleet.score_vessel(db, mmsi, window=window)
    if exp is None:
        raise HTTPException(status_code=404, detail=_window_error(mmsi, window))
    return _json({
        **_summary(pings, exp),
        "generated_at": fleet.utcnow(),
        "window": window.as_dict(),
        "threshold": exp.threshold,
        "max_points": risk_engine.MAX_POINTS,
        "zone": exp.zone,
        "factors": [asdict(f) for f in exp.factors],
        "checks": [asdict(c) for c in exp.checks],
        "clear_if": exp.clear_if,
        "limitations": get_vessel_limitations(),
        "gaps": [{k: v for k, v in g.items() if k not in ("lat", "lon")} for g in exp.gaps],
        "encounters": exp.encounters,
        "track": [
            {"t": p.t, "lat": p.lat, "lon": p.lon, "speed": p.speed, "course": p.course,
             "source": getattr(p, "source", None), "source_mode": getattr(p, "source_mode", None)}
            for p in pings
        ],
    })
