"""Loads recent AIS and protected areas from PostGIS and runs the risk engine over them."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from shapely import wkb
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services import risk_engine
from app.services.risk_engine import Explanation, Ping, Zone

# One week is the same bound the existing rolling callers expose (1-168 h).
MAX_WINDOW_HOURS = 168


class WindowSelectionError(ValueError):
    """An explicit historical window was missing, inverted, unbounded or not UTC."""


@dataclass(frozen=True)
class FleetWindow:
    """A bounded UTC selection over stored observations.

    ``start`` is exclusive and ``end`` is inclusive, matching the existing
    ``timestamp > :since`` rolling query. Timestamps remain naive UTC because
    the risk engine works in naive UTC throughout.
    """

    mode: str  # "rolling" | "historical"
    start: datetime
    end: datetime
    hours: int

    def as_dict(self) -> Dict[str, object]:
        return {
            "mode": self.mode,
            "start": _iso_utc(self.start),
            "end": _iso_utc(self.end),
            "hours": self.hours,
            "max_hours": MAX_WINDOW_HOURS,
            "utc": True,
            "end_inclusive": True,
            "timestamps": "original stored observation timestamps are preserved",
        }


def utcnow() -> datetime:
    # The engine works in naive UTC throughout
    return datetime.utcnow()


def _naive_utc(t: datetime) -> datetime:
    return t.astimezone(timezone.utc).replace(tzinfo=None) if t.tzinfo else t


def _iso_utc(t: datetime) -> str:
    return _naive_utc(t).replace(tzinfo=timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def window_payload(
    mode: Optional[str],
    start: Optional[datetime],
    end: Optional[datetime],
    hours: int,
) -> Optional[Dict[str, object]]:
    """Build the shared window object from stored fields, without inference.

    ``None`` mode means a legacy row whose anchors are unknown. A mode with
    missing anchors is reported as missing rather than reconstructed from
    ``hours`` or ``evaluated_at``.
    """
    if mode is None:
        return None
    if start is None or end is None:
        return {
            "mode": mode,
            "start": None,
            "end": None,
            "hours": hours,
            "max_hours": MAX_WINDOW_HOURS,
            "utc": True,
            "end_inclusive": True,
            "timestamps": "original stored observation timestamps are preserved",
            "anchors": "missing",
        }
    return FleetWindow(mode, start, end, hours).as_dict()


def resolve_window(
    hours: int = 24,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    now: Optional[datetime] = None,
) -> FleetWindow:
    """Resolve either the existing rolling look-back or an explicit historical window.

    Rolling callers keep their current semantics: ``hours`` is measured back
    from the evaluation clock. An explicit historical window requires both
    bounds, an explicit UTC offset, a positive span and at most
    ``MAX_WINDOW_HOURS``. Invalid input raises ``WindowSelectionError`` so API
    routes can return a clear 422 instead of silently widening or shifting.
    """
    # Use the clock directly rather than the patchable ``utcnow`` helper: a
    # caller may freeze ``generated_at`` for display without changing window
    # selection, and tests patch that helper with a string.
    current = _naive_utc(now) if now is not None else datetime.utcnow()

    if (start is None) != (end is None):
        raise WindowSelectionError("window_start and window_end must be supplied together")

    if start is None:
        if not isinstance(hours, int) or not 1 <= hours <= MAX_WINDOW_HOURS:
            raise WindowSelectionError(
                f"lookback_hours must be between 1 and {MAX_WINDOW_HOURS}"
            )
        return FleetWindow("rolling", current - timedelta(hours=hours), current, hours)

    if start.tzinfo is None or end.tzinfo is None:
        raise WindowSelectionError(
            "window_start and window_end must include an explicit UTC offset, "
            "for example 2026-10-31T00:00:00Z"
        )

    start_utc = _naive_utc(start)
    end_utc = _naive_utc(end)
    if end_utc <= start_utc:
        raise WindowSelectionError("window_end must be after window_start")

    span = end_utc - start_utc
    if span > timedelta(hours=MAX_WINDOW_HOURS):
        raise WindowSelectionError(
            f"historical window must not exceed {MAX_WINDOW_HOURS} hours"
        )
    if end_utc > current:
        raise WindowSelectionError(
            "window_end must not be in the future; historical selection cannot include unobserved time"
        )

    span_hours = max(1, math.ceil(span.total_seconds() / 3600))
    return FleetWindow("historical", start_utc, end_utc, span_hours)


def load_pings(
    db: Session,
    since: datetime,
    mmsi: Optional[int] = None,
    until: Optional[datetime] = None,
) -> List[Ping]:
    extra = ""
    params = {"since": since.replace(tzinfo=timezone.utc)}
    if mmsi is not None:
        extra += " AND mmsi = :mmsi"
        params["mmsi"] = mmsi
    if until is not None:
        extra += " AND timestamp <= :until"
        params["until"] = until.replace(tzinfo=timezone.utc)
    sql = """
        SELECT mmsi, timestamp, ST_Y(location::geometry) AS lat, ST_X(location::geometry) AS lon,
               speed, course, vessel_name, vessel_type, length, source, source_mode
        FROM vessel_tracks
        WHERE timestamp > :since {extra}
        ORDER BY mmsi, timestamp
    """.format(extra=extra)
    return [
        Ping(r.mmsi, _naive_utc(r.timestamp), r.lat, r.lon, r.speed, r.course, r.vessel_name,
             getattr(r.vessel_type, "value", r.vessel_type), r.length,
             getattr(r, "source", None), getattr(r, "source_mode", None))
        for r in db.execute(text(sql), params)
    ]


def load_zones(db: Session) -> List[Zone]:
    rows = db.execute(text("SELECT name, ST_AsBinary(boundary) AS geom FROM marine_protected_areas"))
    return [Zone(r.name, wkb.loads(bytes(r.geom))) for r in rows]


def group_by_vessel(pings: List[Ping]) -> Dict[int, List[Ping]]:
    grouped: Dict[int, List[Ping]] = {}
    for p in pings:
        grouped.setdefault(p.mmsi, []).append(p)
    return grouped


def score_fleet(
    db: Session,
    hours: int = 24,
    now: Optional[datetime] = None,
    window: Optional[FleetWindow] = None,
):
    """Score every vessel seen in the window. Returns [(pings, explanation)] sorted by score.

    Passing ``window`` uses that exact bounded selection (rolling or
    historical); otherwise the existing rolling look-back is derived from
    ``hours``/``now``. For a historical window the evaluation clock is the
    window end, so a later wall clock does not manufacture an open AIS gap.
    """
    window = window or resolve_window(hours=hours, now=now)
    until = window.end if window.mode == "historical" else None
    pings = load_pings(db, window.start, until=until)
    zones = load_zones(db)
    results = []
    for mmsi, own in group_by_vessel(pings).items():
        results.append((own, risk_engine.explain(own, pings, zones, window.end)))
    results.sort(key=lambda r: -r[1].score)
    return results


def score_vessel(
    db: Session,
    mmsi: int,
    hours: int = 24,
    now: Optional[datetime] = None,
    window: Optional[FleetWindow] = None,
):
    """Score one vessel over an exact window; see ``score_fleet``."""
    window = window or resolve_window(hours=hours, now=now)
    until = window.end if window.mode == "historical" else None
    pings = load_pings(db, window.start, until=until)
    own = [p for p in pings if p.mmsi == mmsi]
    if not own:
        return None, None
    return own, risk_engine.explain(own, pings, load_zones(db), window.end)


def persist_scores(db: Session, results) -> int:
    """Write each vessel's score onto its latest ping so older endpoints (alerts, statistics) see it."""
    updated = 0
    for own, exp in results:
        is_dark = any(f.key == "ais_gap" and f.evidence.get("open") for f in exp.factors)
        db.execute(
            text("""
                UPDATE vessel_tracks SET risk_score = :score, is_dark = :dark
                WHERE mmsi = :mmsi AND timestamp = :t
            """),
            {"score": exp.score, "dark": is_dark, "mmsi": own[-1].mmsi, "t": own[-1].t.replace(tzinfo=timezone.utc)},
        )
        updated += 1
    db.commit()
    return updated


def rescore_all(db: Session, hours: int = 24) -> int:
    return persist_scores(db, score_fleet(db, hours))
