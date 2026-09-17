"""Loads recent AIS and protected areas from PostGIS and runs the risk engine over them."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from shapely import wkb
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services import risk_engine
from app.services.risk_engine import Explanation, Ping, Zone


def utcnow() -> datetime:
    # The engine works in naive UTC throughout
    return datetime.utcnow()


def _naive_utc(t: datetime) -> datetime:
    return t.astimezone(timezone.utc).replace(tzinfo=None) if t.tzinfo else t


def load_pings(db: Session, since: datetime, mmsi: Optional[int] = None) -> List[Ping]:
    sql = """
        SELECT mmsi, timestamp, ST_Y(location::geometry) AS lat, ST_X(location::geometry) AS lon,
               speed, course, vessel_name, vessel_type, length
        FROM vessel_tracks
        WHERE timestamp > :since {extra}
        ORDER BY mmsi, timestamp
    """.format(extra="AND mmsi = :mmsi" if mmsi is not None else "")
    params = {"since": since.replace(tzinfo=timezone.utc)}
    if mmsi is not None:
        params["mmsi"] = mmsi
    return [
        Ping(r.mmsi, _naive_utc(r.timestamp), r.lat, r.lon, r.speed, r.course, r.vessel_name,
             getattr(r.vessel_type, "value", r.vessel_type), r.length)
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


def score_fleet(db: Session, hours: int = 24, now: Optional[datetime] = None):
    """Score every vessel seen in the window. Returns [(pings, explanation)] sorted by score."""
    now = now or utcnow()
    pings = load_pings(db, now - timedelta(hours=hours))
    zones = load_zones(db)
    results = []
    for mmsi, own in group_by_vessel(pings).items():
        results.append((own, risk_engine.explain(own, pings, zones, now)))
    results.sort(key=lambda r: -r[1].score)
    return results


def score_vessel(db: Session, mmsi: int, hours: int = 24, now: Optional[datetime] = None):
    now = now or utcnow()
    pings = load_pings(db, now - timedelta(hours=hours))
    own = [p for p in pings if p.mmsi == mmsi]
    if not own:
        return None, None
    return own, risk_engine.explain(own, pings, load_zones(db), now)


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
