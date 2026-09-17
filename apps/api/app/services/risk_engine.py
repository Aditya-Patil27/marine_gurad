"""
Explainable vessel risk scoring.

The score is additive: each behaviour below adds a fixed share of its maximum
points, and the score is the sum (capped at 1.0). Because of that, the list of
factors is not an approximation of the model; it *is* the model. Nothing here
touches the database, so it can be unit-tested with plain lists of pings.

Distances use a local equirectangular projection, which is accurate to well
under 1% at the ranges involved (a few hundred metres to ~100 km).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from shapely.geometry import Point, Polygon
from shapely.ops import transform

ALERT_THRESHOLD = 0.60
WATCH_THRESHOLD = 0.30

# Maximum points per behaviour. Keep these in one place: the UI shows them.
MAX_POINTS = {
    "ais_gap": 0.31,
    "position_jump": 0.22,
    "encounter": 0.18,
    "loitering": 0.14,
    "fishing_in_park": 0.12,
}

AIS_GAP_MIN_H = 4.0          # a silence shorter than this is normal
AIS_GAP_FULL_H = 6.0         # a silence this long earns the full points
JUMP_MIN_KN = 25.0           # implied speed no small fishing vessel reaches
JUMP_MIN_KM = 5.0
ENCOUNTER_MAX_M = 500.0      # Global Fishing Watch encounter rule:
ENCOUNTER_MAX_KN = 2.0       #   within 500 m, both under 2 kn,
ENCOUNTER_MIN_H = 2.0        #   for at least 2 hours
ENCOUNTER_PAIR_WINDOW = timedelta(minutes=15)
LOITER_MAX_KN = 2.0
LOITER_MIN_H = 2.0
BUFFER_KM = 10.0
OUTAGE_RADIUS_KM = 50.0
MAX_SEGMENT = timedelta(hours=1)  # longer gaps between pings don't count as observed time

KN_PER_KMH = 1 / 1.852


@dataclass(frozen=True)
class Ping:
    mmsi: int
    t: datetime
    lat: float
    lon: float
    speed: Optional[float] = None
    course: Optional[float] = None
    name: Optional[str] = None
    vessel_type: Optional[str] = None
    length: Optional[float] = None


@dataclass(frozen=True)
class Zone:
    name: str
    polygon: Polygon


@dataclass
class Factor:
    key: str
    label: str
    detail: str
    points: float
    max_points: float
    evidence: dict = field(default_factory=dict)


@dataclass
class Check:
    key: str
    label: str
    status: str  # "ruled_out" | "not_ruled_out" | "not_checked"
    detail: str


@dataclass
class Explanation:
    mmsi: int
    score: float
    level: str  # "high" | "medium" | "low"
    threshold: float
    factors: List[Factor]
    checks: List[Check]
    clear_if: Optional[dict]
    zone: Optional[dict]
    gaps: List[dict]
    encounters: List[dict]


# ---------------------------------------------------------------- geometry

def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance (haversine)."""
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _local_km(lat0: float):
    kx = 111.320 * math.cos(math.radians(lat0))
    ky = 110.574
    return lambda x, y, z=None: (x * kx, y * ky)


def zone_relation(lat: float, lon: float, zones: Sequence[Zone]) -> Optional[dict]:
    """Closest protected area the point is inside of or within BUFFER_KM of."""
    best = None
    for zone in zones:
        project = _local_km(lat)
        poly = transform(project, zone.polygon)
        pt = Point(project(lon, lat))
        if poly.contains(pt):
            return {"name": zone.name, "relation": "inside", "distance_km": 0.0}
        d = poly.exterior.distance(pt)
        if d <= BUFFER_KM and (best is None or d < best["distance_km"]):
            best = {"name": zone.name, "relation": "buffer", "distance_km": round(d, 1)}
    return best


# ---------------------------------------------------------------- helpers

def _hours(delta: timedelta) -> float:
    return delta.total_seconds() / 3600


def fmt_duration(hours: float) -> str:
    total_min = int(round(hours * 60))
    h, m = divmod(total_min, 60)
    if h and m:
        return f"{h} h {m} m"
    return f"{h} h" if h else f"{m} m"


def vessel_label(p: Ping) -> str:
    return p.name or f"MMSI {p.mmsi}"


def find_gaps(pings: Sequence[Ping], now: datetime, min_h: float = 0.5) -> List[dict]:
    """Silences between pings (and since the last ping) of at least min_h hours."""
    gaps = []
    for a, b in zip(pings, pings[1:]):
        h = _hours(b.t - a.t)
        if h >= min_h:
            gaps.append({"start": a.t, "end": b.t, "hours": h, "open": False, "lat": a.lat, "lon": a.lon})
    if pings:
        h = _hours(now - pings[-1].t)
        if h >= min_h:
            last = pings[-1]
            gaps.append({"start": last.t, "end": now, "hours": h, "open": True, "lat": last.lat, "lon": last.lon})
    return gaps


# ---------------------------------------------------------------- factors

def _ais_gap(pings, now, others) -> Tuple[Optional[Factor], Optional[Check]]:
    gaps = [g for g in find_gaps(pings, now) if g["hours"] >= AIS_GAP_MIN_H]
    if not gaps:
        return None, None
    gap = max(gaps, key=lambda g: g["hours"])

    # Receiver outage: if nobody nearby reported during the silence, the gap may be ours, not theirs.
    reporters = {
        o.mmsi for o in others
        if gap["start"] < o.t <= gap["end"]
        and distance_km(gap["lat"], gap["lon"], o.lat, o.lon) <= OUTAGE_RADIUS_KM
    }
    if not reporters:
        check = Check(
            "receiver_outage", "AIS receiver outage", "not_ruled_out",
            f"No other vessel within {OUTAGE_RADIUS_KM:.0f} km reported during the silence, so it isn't counted.",
        )
        return None, check

    check = Check(
        "receiver_outage", "AIS receiver outage", "ruled_out",
        f"{len(reporters)} other vessel{'s' if len(reporters) != 1 else ''} within {OUTAGE_RADIUS_KM:.0f} km kept reporting",
    )
    share = min(1.0, gap["hours"] / AIS_GAP_FULL_H)
    detail = f"{gap['hours']:.1f} h" + (" so far" if gap["open"] else "") + f" · rule ≥ {AIS_GAP_MIN_H:.0f} h"
    factor = Factor(
        "ais_gap", "AIS switched off", detail, round(MAX_POINTS["ais_gap"] * share, 2), MAX_POINTS["ais_gap"],
        {"start": gap["start"], "end": gap["end"], "hours": round(gap["hours"], 2), "open": gap["open"]},
    )
    return factor, check


def _position_jump(pings) -> Optional[Factor]:
    worst = None
    for a, b in zip(pings, pings[1:]):
        h = _hours(b.t - a.t)
        if h <= 0:
            continue
        km = distance_km(a.lat, a.lon, b.lat, b.lon)
        kn = km / h * KN_PER_KMH
        if km >= JUMP_MIN_KM and kn >= JUMP_MIN_KN and (worst is None or kn > worst[2]):
            worst = (a, b, kn, km, h)
    if not worst:
        return None
    a, b, kn, km, h = worst
    return Factor(
        "position_jump", "Position jumped", f"{km:.0f} km in {fmt_duration(h)} · implies {kn:.0f} kn",
        MAX_POINTS["position_jump"], MAX_POINTS["position_jump"],
        {"from": a.t, "to": b.t, "km": round(km, 1), "implied_kn": round(kn, 1)},
    )


def _closest_slow_match(p: Ping, other: Sequence[Ping]) -> Optional[Tuple[float, Ping]]:
    """Nearest ping of `other` within the pairing window where both vessels are slow and close."""
    if p.speed is None or p.speed >= ENCOUNTER_MAX_KN:
        return None
    best = None
    for o in other:
        if abs(o.t - p.t) > ENCOUNTER_PAIR_WINDOW or o.speed is None or o.speed >= ENCOUNTER_MAX_KN:
            continue
        m = distance_km(p.lat, p.lon, o.lat, o.lon) * 1000
        if m <= ENCOUNTER_MAX_M and (best is None or m < best[0]):
            best = (m, o)
    return best


def find_encounters(pings: Sequence[Ping], others_by_mmsi: Dict[int, List[Ping]]) -> List[dict]:
    """Longest run of close, slow proximity with each other vessel, if it lasts ENCOUNTER_MIN_H."""
    found = []
    for other_mmsi, other in others_by_mmsi.items():
        runs, run = [], None
        for p in pings:
            match = _closest_slow_match(p, other)
            if match and run and p.t - run["end"] <= MAX_SEGMENT:
                run["end"] = p.t
                run["closest_m"] = min(run["closest_m"], match[0])
                run["at"] = (p.lat, p.lon) if match[0] <= run["closest_m"] else run["at"]
            elif match:
                run = {"start": p.t, "end": p.t, "closest_m": match[0], "at": (p.lat, p.lon), "other": match[1]}
                runs.append(run)
            else:
                run = None
        long_runs = [r for r in runs if _hours(r["end"] - r["start"]) >= ENCOUNTER_MIN_H]
        if not long_runs:
            continue
        r = max(long_runs, key=lambda r: r["end"] - r["start"])
        found.append({
            "mmsi": other_mmsi, "name": vessel_label(r["other"]), "vessel_type": r["other"].vessel_type,
            "start": r["start"], "end": r["end"], "hours": round(_hours(r["end"] - r["start"]), 2),
            "closest_m": round(r["closest_m"]), "lat": r["at"][0], "lon": r["at"][1],
        })
    return sorted(found, key=lambda e: -e["hours"])


def _encounter(encounters: List[dict]) -> Optional[Factor]:
    if not encounters:
        return None
    e = encounters[0]
    return Factor(
        "encounter", f"Met {e['name']}", f"{e['closest_m']} m apart · {fmt_duration(e['hours'])} · both under {ENCOUNTER_MAX_KN:.0f} kn",
        MAX_POINTS["encounter"], MAX_POINTS["encounter"], {"mmsi": e["mmsi"], "start": e["start"], "end": e["end"]},
    )


def _loitering(pings, zones) -> Optional[Factor]:
    total_h = 0.0
    zone_name = None
    relations = [zone_relation(p.lat, p.lon, zones) if p.speed is not None and p.speed < LOITER_MAX_KN else None for p in pings]
    for (a, ra), (b, rb) in zip(zip(pings, relations), zip(pings[1:], relations[1:])):
        if ra and rb and b.t - a.t <= MAX_SEGMENT:
            total_h += _hours(b.t - a.t)
            zone_name = zone_name or ra["name"]
    if total_h < LOITER_MIN_H:
        return None
    return Factor(
        "loitering", "Loitering in protected waters", f"{fmt_duration(total_h)} under {LOITER_MAX_KN:.0f} kn · {zone_name}",
        MAX_POINTS["loitering"], MAX_POINTS["loitering"], {"hours": round(total_h, 2), "zone": zone_name},
    )


def _fishing_in_park(last: Ping, relation: Optional[dict]) -> Optional[Factor]:
    if (last.vessel_type or "").upper() != "FISHING" or not relation or relation["relation"] != "inside":
        return None
    return Factor(
        "fishing_in_park", "Fishing vessel inside park", f"Last seen inside {relation['name']}",
        MAX_POINTS["fishing_in_park"], MAX_POINTS["fishing_in_park"], {"zone": relation["name"]},
    )


# ---------------------------------------------------------------- scoring

def level_for(score: float) -> str:
    if score >= ALERT_THRESHOLD:
        return "high"
    if score >= WATCH_THRESHOLD:
        return "medium"
    return "low"


def _sum(factors: Iterable[Factor]) -> float:
    return round(min(1.0, sum(f.points for f in factors)), 2)


def clear_if(factors: List[Factor], threshold: float = ALERT_THRESHOLD) -> Optional[dict]:
    """Smallest set of behaviours (largest first) whose absence drops the score below the alert line."""
    if _sum(factors) < threshold:
        return None
    remaining = sorted(factors, key=lambda f: -f.points)
    removed = []
    while remaining and _sum(remaining) >= threshold:
        removed.append(remaining.pop(0))
    return {"score": _sum(remaining), "without": [f.key for f in removed], "labels": [f.label for f in removed]}


def explain(
    pings: Sequence[Ping],
    others: Sequence[Ping],
    zones: Sequence[Zone],
    now: datetime,
) -> Explanation:
    """Score one vessel. `pings` are its own positions in time order; `others` are every other vessel's."""
    if not pings:
        raise ValueError("explain() needs at least one ping")
    pings = sorted(pings, key=lambda p: p.t)
    mmsi = pings[0].mmsi
    others = [o for o in others if o.mmsi != mmsi]

    others_by_mmsi: Dict[int, List[Ping]] = {}
    for o in sorted(others, key=lambda o: o.t):
        others_by_mmsi.setdefault(o.mmsi, []).append(o)

    last = pings[-1]
    relation = zone_relation(last.lat, last.lon, zones)
    encounters = find_encounters(pings, others_by_mmsi)

    gap_factor, outage_check = _ais_gap(pings, now, others)
    factors = [f for f in (
        gap_factor,
        _position_jump(pings),
        _encounter(encounters),
        _loitering(pings, zones),
        _fishing_in_park(last, relation),
    ) if f]
    factors.sort(key=lambda f: -f.points)

    checks = []
    if outage_check:
        checks.append(outage_check)
    if factors:
        checks.append(Check(
            "weather", "Bad weather", "not_checked",
            "No marine weather feed is connected yet, so storm sheltering can't be ruled out.",
        ))

    score = _sum(factors)
    return Explanation(
        mmsi=mmsi,
        score=score,
        level=level_for(score),
        threshold=ALERT_THRESHOLD,
        factors=factors,
        checks=checks,
        clear_if=clear_if(factors),
        zone=relation,
        gaps=[g for g in find_gaps(pings, now) if g["hours"] >= 0.5],
        encounters=encounters,
    )


def headline(last: Ping, exp: Explanation) -> str:
    """One line for queues: what the top behaviour was."""
    name = vessel_label(last)
    if not exp.factors:
        return f"{name} is behaving normally"
    top = exp.factors[0]
    if top.key == "ais_gap":
        return f"{name} went dark for {top.evidence['hours']:.1f} h"
    if top.key == "position_jump":
        return f"{name} jumped {top.evidence['km']:.0f} km"
    if top.key == "encounter":
        return f"{name} {top.label[0].lower()}{top.label[1:]}"
    if top.key == "loitering":
        return f"{name} is loitering near {top.evidence['zone']}"
    return f"{name} is fishing inside {top.evidence['zone']}"
