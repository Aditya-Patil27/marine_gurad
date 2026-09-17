#!/usr/bin/env python3
"""
Seed the Gulf of Mannar demo story, with timestamps relative to now so the console always looks live.

  Sea Pearl II   trawler that loiters in the park buffer, meets a carrier, then switches AIS off
  Hai Feng 818   the carrier it meets
  Lakshmi Matha  jumps about 35 km in 15 minutes and then loiters inside the park
  Arul Jyothi    loiters near the park, nothing else
  + ten ordinary vessels moving through the gulf, so receiver outages can be ruled out

All names, MMSIs and tracks are invented. Re-running replaces the previous demo tracks.

Usage (from apps/api):  python scripts/seed_demo.py
"""

import math
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app.database import SessionLocal
from app.services.fleet import rescore_all
from scripts.load_mpas import load_sample_mpas

NOW = datetime.utcnow().replace(microsecond=0)
rng = random.Random(14)


def ago(hours):
    return NOW - timedelta(hours=hours)


def leg(start, end, t0, t1, speed, step_min=10, jitter=0.0):
    """Straight line from start to end between t0 and t1 (hours ago), one ping every step_min."""
    pings, n = [], max(1, int(round((t0 - t1) * 60 / step_min)))
    course = (math.degrees(math.atan2(end[1] - start[1], end[0] - start[0])) + 360) % 360
    for i in range(n + 1):
        f = i / n
        lat = start[0] + (end[0] - start[0]) * f + rng.uniform(-jitter, jitter)
        lon = start[1] + (end[1] - start[1]) * f + rng.uniform(-jitter, jitter)
        pings.append((ago(t0 - (t0 - t1) * f), lat, lon, max(0.1, speed + rng.uniform(-0.3, 0.3)), course))
    return pings


def drift(center, t0, t1, speed, step_min=10, radius=0.0012):
    """Slow wander around a point: loitering, fishing or waiting alongside."""
    pings, n = [], int(round((t0 - t1) * 60 / step_min))
    for i in range(n + 1):
        pings.append((ago(t0 - (t0 - t1) * i / n), center[0] + rng.uniform(-radius, radius),
                      center[1] + rng.uniform(-radius, radius), max(0.1, speed + rng.uniform(-0.3, 0.3)),
                      rng.uniform(0, 359)))
    return pings


def wander(start, heading, speed, hours, step_min=15, box=((8.05, 8.85), (78.35, 79.65))):
    """Ordinary traffic: steady course that turns back at the edge of open water."""
    pings, lat, lon = [], *start
    for i in range(int(hours * 60 / step_min) + 1):
        t = ago(hours - i * step_min / 60)
        pings.append((t, lat, lon, speed + rng.uniform(-0.5, 0.5), heading))
        step_deg = speed * 1.852 * step_min / 60 / 111
        lat += step_deg * math.cos(math.radians(heading))
        lon += step_deg * math.sin(math.radians(heading))
        if not box[0][0] <= lat <= box[0][1]:
            heading = (180 - heading) % 360
        if not box[1][0] <= lon <= box[1][1]:
            heading = (360 - heading) % 360
    return pings


SEA_PEARL = (8.900, 78.950)
CARRIER = (8.9035, 78.9515)  # alongside, ~420 m away
STORY = [
    dict(mmsi=419007431, name="SEA PEARL II", type="FISHING", length=23.4, callsign="AUSP7",
         pings=leg((8.55, 78.70), SEA_PEARL, 12, 9, 9.5) + drift(SEA_PEARL, 8.83, 6.2, 0.9, radius=0.0004)),
    dict(mmsi=412440918, name="HAI FENG 818", type="CARGO", length=86.0, callsign="BQHF8",
         pings=leg((8.62, 79.45), CARRIER, 12, 8.9, 10.0)
         + drift(CARRIER, 8.83, 6.5, 0.7, radius=0.0004)
         + leg(CARRIER, (8.30, 79.60), 6.33, 0, 8.0, step_min=15)),
    dict(mmsi=419001265, name="LAKSHMI MATHA", type="FISHING", length=14.2, callsign="AULM2",
         pings=leg((8.55, 78.30), (8.70, 78.55), 8, 3, 3.6) + drift((8.945, 78.76), 2.75, 0, 1.2, radius=0.004)),
    dict(mmsi=419003318, name="ARUL JYOTHI", type="FISHING", length=16.8, callsign="AUAJ3",
         pings=leg((8.70, 79.40), (8.98, 79.20), 7, 3.5, 6.5) + drift((8.98, 79.20), 3.33, 0, 1.0, radius=0.003)),
]

TRAFFIC = [
    (419005120, "PAMBAN STAR", "FISHING", 12.0, (8.30, 78.60), 70, 6.0),
    (419008842, "TUTICORIN TRADER", "CARGO", 110.0, (8.20, 78.40), 95, 11.0),
    (419004471, "KANYAKUMARI QUEEN", "PASSENGER", 48.0, (8.10, 79.00), 20, 9.0),
    (419006613, "BLUE MARLIN", "FISHING", 18.5, (8.60, 79.30), 200, 5.5),
    (419002290, "MARIA STELLA", "FISHING", 15.0, (8.40, 79.50), 250, 6.5),
    (419009934, "GULF PRIDE", "TANKER", 142.0, (8.15, 79.60), 285, 10.0),
    (419001877, "NILA", "FISHING", 11.5, (8.75, 78.45), 150, 5.0),
    (419007702, "OCEAN CREST", "CARGO", 96.0, (8.50, 78.90), 120, 9.5),
    (419003056, "SETHU", "OTHER", 28.0, (8.80, 79.00), 300, 7.0),
    (419008120, "CORAL BAY", "TANKER", 128.0, (8.25, 79.20), 45, 10.5),
]


def main():
    vessels = STORY + [
        dict(mmsi=m, name=n, type=t, length=l, callsign=None, pings=wander(start, heading, speed, 12))
        for m, n, t, l, start, heading, speed in TRAFFIC
    ]
    db = SessionLocal()
    try:
        load_sample_mpas(db)
        db.execute(text("DELETE FROM vessel_tracks WHERE mmsi = ANY(:mmsi)"), {"mmsi": [v["mmsi"] for v in vessels]})
        rows = [
            {"mmsi": v["mmsi"], "name": v["name"], "type": v["type"], "length": v["length"], "callsign": v["callsign"],
             "t": t, "lat": lat, "lon": lon, "speed": round(speed, 1), "course": round(course, 1)}
            for v in vessels for t, lat, lon, speed, course in v["pings"]
        ]
        db.execute(text("""
            INSERT INTO vessel_tracks (mmsi, vessel_name, vessel_type, length, callsign, timestamp, location,
                                       speed, course, is_dark, risk_score)
            VALUES (:mmsi, :name, CAST(:type AS vesseltype), :length, :callsign, :t,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), :speed, :course, false, 0)
        """), rows)
        db.commit()
        print(f"Inserted {len(rows)} positions for {len(vessels)} vessels")
        print(f"Rescored {rescore_all(db)} vessels")
    finally:
        db.close()


if __name__ == "__main__":
    main()
