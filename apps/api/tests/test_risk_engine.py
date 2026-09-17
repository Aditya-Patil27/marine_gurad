from datetime import datetime, timedelta

import pytest
from shapely.geometry import Polygon

from app.services import risk_engine as re
from app.services.risk_engine import Ping, Zone

NOW = datetime(2026, 9, 17, 12, 0)
PARK = Zone("Test Park", Polygon([(79.0, 9.0), (79.2, 9.0), (79.2, 9.2), (79.0, 9.2)]))


def track(mmsi, start_h_ago, end_h_ago, lat, lon, speed=8.0, step_min=10, dlat=0.0, dlon=0.0, **kw):
    """Pings every step_min minutes from start_h_ago to end_h_ago hours before NOW."""
    pings, t, i = [], NOW - timedelta(hours=start_h_ago), 0
    while t <= NOW - timedelta(hours=end_h_ago):
        pings.append(Ping(mmsi, t, lat + dlat * i, lon + dlon * i, speed, **kw))
        t += timedelta(minutes=step_min)
        i += 1
    return pings


def neighbours(lat=8.8, lon=78.9):
    return track(900, 12, 0, lat, lon, speed=9) + track(901, 12, 0, lat + 0.1, lon, speed=9)


def test_normal_vessel_scores_zero_with_no_checks():
    exp = re.explain(track(1, 6, 0, 8.5, 78.5), neighbours(), [PARK], NOW)
    assert exp.score == 0
    assert exp.level == "low"
    assert exp.factors == []
    assert exp.checks == []
    assert exp.clear_if is None


def test_ais_gap_counts_when_neighbours_kept_reporting():
    exp = re.explain(track(1, 12, 6.2, 8.8, 78.9), neighbours(), [], NOW)
    gap = next(f for f in exp.factors if f.key == "ais_gap")
    assert gap.points == re.MAX_POINTS["ais_gap"]
    assert gap.evidence["open"] is True
    outage = next(c for c in exp.checks if c.key == "receiver_outage")
    assert outage.status == "ruled_out"


def test_ais_gap_is_scaled_below_full_duration():
    exp = re.explain(track(1, 12, 4.5, 8.8, 78.9), neighbours(), [], NOW)
    gap = next(f for f in exp.factors if f.key == "ais_gap")
    assert gap.points == round(re.MAX_POINTS["ais_gap"] * 4.5 / 6, 2)


def test_short_gap_is_ignored():
    exp = re.explain(track(1, 12, 3, 8.8, 78.9), neighbours(), [], NOW)
    assert not any(f.key == "ais_gap" for f in exp.factors)


def test_ais_gap_not_counted_when_nobody_nearby_reported():
    far_away = track(900, 12, 0, 15.0, 72.0)
    exp = re.explain(track(1, 12, 6.2, 8.8, 78.9), far_away, [], NOW)
    assert not any(f.key == "ais_gap" for f in exp.factors)
    outage = next(c for c in exp.checks if c.key == "receiver_outage")
    assert outage.status == "not_ruled_out"


def test_position_jump():
    pings = track(1, 6, 3, 8.5, 78.5, speed=6) + [Ping(1, NOW - timedelta(hours=2, minutes=30), 8.5, 78.85, 6)]
    exp = re.explain(pings, neighbours(), [], NOW)
    jump = next(f for f in exp.factors if f.key == "position_jump")
    assert jump.evidence["km"] == pytest.approx(38.5, abs=1)
    assert jump.evidence["implied_kn"] > re.JUMP_MIN_KN


def test_encounter_follows_gfw_rule():
    a = track(1, 6, 0, 8.80, 78.90, speed=1.0, name="Sea Pearl II")
    b = track(2, 6, 0, 8.803, 78.90, speed=0.8, name="Hai Feng 818")  # ~330 m north
    exp = re.explain(a, b + neighbours(), [], NOW)
    enc = next(f for f in exp.factors if f.key == "encounter")
    assert enc.label == "Met Hai Feng 818"
    assert exp.encounters[0]["closest_m"] == pytest.approx(332, abs=10)
    assert exp.encounters[0]["hours"] == pytest.approx(6, abs=0.2)


def test_no_encounter_if_too_short_or_too_fast():
    a = track(1, 6, 0, 8.80, 78.90, speed=1.0)
    short = track(2, 1.5, 0, 8.801, 78.90, speed=1.0)
    fast = track(3, 6, 0, 8.801, 78.90, speed=5.0)
    exp = re.explain(a, short + fast, [], NOW)
    assert exp.encounters == []


def test_loitering_in_buffer_and_fishing_inside_park():
    near = track(1, 4, 0, 8.95, 79.1, speed=1.0)  # ~5.5 km south of the park
    exp = re.explain(near, neighbours(), [PARK], NOW)
    assert exp.zone["relation"] == "buffer"
    assert [f.key for f in exp.factors] == ["loitering"]

    inside = track(2, 1, 0, 9.1, 79.1, speed=6.0, vessel_type="FISHING")
    exp = re.explain(inside, neighbours(), [PARK], NOW)
    assert exp.zone["relation"] == "inside"
    assert [f.key for f in exp.factors] == ["fishing_in_park"]


def test_score_is_exact_sum_and_clear_if_removes_largest_first():
    a = track(1, 12, 6, 8.95, 79.1, speed=1.0, name="Sea Pearl II", vessel_type="FISHING")
    b = track(2, 12, 0, 8.952, 79.1, speed=1.0, name="Hai Feng 818")
    exp = re.explain(a, b + neighbours(8.9, 79.0), [PARK], NOW)
    keys = {f.key for f in exp.factors}
    assert keys == {"ais_gap", "encounter", "loitering"}
    assert exp.score == round(sum(f.points for f in exp.factors), 2) == 0.63
    assert exp.level == "high"
    assert exp.clear_if == {"score": 0.32, "without": ["ais_gap"], "labels": ["AIS switched off"]}
    assert any(c.key == "weather" and c.status == "not_checked" for c in exp.checks)
    assert re.headline(a[-1], exp) == "Sea Pearl II went dark for 6.0 h"
