#!/usr/bin/env python3
"""Read-only readiness check for the 10 November judging replay.

Run from ``apps/api`` (or inside the backend container)::

    python scripts/verify_judging_replay.py

It verifies, without reseeding or resetting anything:

* the database is at the current Alembic head;
* all fourteen seeded replay vessels and their positions are present;
* the newest replay position is still inside the UI/API look-back window;
* local Administrator role assignments exist;
* case/report row counts are unchanged by the run;
* the bounded local replay, historical SST and GFW endpoints answer;
* optionally, the local Administrator can sign in.

The sign-in check needs credentials. Supply them in the environment
(``SAMUDRA_VERIFY_USERNAME`` / ``SAMUDRA_VERIFY_PASSWORD``) or let the script
prompt with hidden input. They are never printed, logged or written to disk.
Without credentials the sign-in check is SKIPPED and the overall result is
PARTIAL, never a fabricated pass.

Exit codes: 0 = all checks passed, 2 = some checks skipped, 1 = a check failed.
This script only writes one short-lived login session when credentials are
supplied (and revokes it on logout); it never modifies vessel, case or report
records. It does not reset the shared database and does not run migrations.

External sources are checked with one bounded GFW request. If a provider or
local artifact is unavailable the check fails visibly with the observed error;
no placeholder data is substituted.
"""
import argparse
import getpass
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402
from alembic.config import Config as AlembicConfig  # noqa: E402
from alembic.script import ScriptDirectory  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.database import SessionLocal  # noqa: E402

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"

API_PREFIX = "/api/v1"
MAX_LOOKBACK_HOURS = 168
# A fixed, already-smoked historical window. Bounded to one small page.
GFW_START = "2024-01-01"
GFW_END = "2024-02-01"


def stale_after_error(latest_utc, now_utc, lookback_hours=MAX_LOOKBACK_HOURS):
    """Return a visible message when the newest replay position is too old."""
    if latest_utc is None:
        return "No replay positions were found."
    if latest_utc.tzinfo is None:
        latest_utc = latest_utc.replace(tzinfo=timezone.utc)
    age = now_utc - latest_utc.astimezone(timezone.utc)
    if age > timedelta(hours=lookback_hours):
        hours = age.total_seconds() / 3600
        return (
            f"Newest replay position is {hours:.1f} h old, outside the {lookback_hours} h "
            "look-back. Rerun `python scripts/seed_demo.py` deliberately to refresh the "
            "replay; this checker never reseeds."
        )
    return None


def geojson_shape_errors(payload):
    """Return structural problems in the bounded GFW GeoJSON response."""
    errors = []
    if payload.get("type") != "FeatureCollection":
        errors.append("response is not a FeatureCollection")
    if payload.get("mode") != "historical":
        errors.append("mode is not `historical`")
    features = payload.get("features")
    if not isinstance(features, list):
        return errors + ["features is not a list"]
    for index, feature in enumerate(features):
        geometry = (feature or {}).get("geometry") or {}
        coordinates = geometry.get("coordinates")
        if geometry.get("type") != "Point" or not (
            isinstance(coordinates, list)
            and len(coordinates) == 2
            and all(isinstance(value, (int, float)) for value in coordinates)
        ):
            errors.append(f"feature {index} is not a valid Point")
            continue
        lon, lat = coordinates
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            errors.append(f"feature {index} has out-of-range WGS84 coordinates")
        if not (feature.get("properties") or {}).get("event_id"):
            errors.append(f"feature {index} has no event_id")
    return errors


class Report:
    def __init__(self):
        self.results = []

    def check(self, condition, name, detail, skipped=False):
        status = SKIP if skipped else (PASS if condition else FAIL)
        self.results.append(status)
        print(f"[{status}] {name}: {detail}")
        return condition

    def fail(self, name, detail):
        return self.check(False, name, detail)

    def skip(self, name, detail):
        return self.check(False, name, detail, skipped=True)

    @property
    def failed(self):
        return self.results.count(FAIL)

    @property
    def skipped(self):
        return self.results.count(SKIP)


def expected_demo_mmsis():
    from scripts.seed_demo import STORY, TRAFFIC

    return sorted({vessel["mmsi"] for vessel in STORY} | {row[0] for row in TRAFFIC})


def current_head():
    ini = Path(__file__).resolve().parent.parent / "alembic.ini"
    return ScriptDirectory.from_config(AlembicConfig(str(ini))).get_current_head()


def table_counts(db):
    return {
        "cases": db.execute(text("SELECT count(*) FROM investigation_cases")).scalar_one(),
        "case_revisions": db.execute(
            text("SELECT count(*) FROM investigation_case_revisions")
        ).scalar_one(),
        "reports": db.execute(text("SELECT count(*) FROM incident_reports")).scalar_one(),
        "signed_reports": db.execute(
            text("SELECT count(*) FROM incident_reports WHERE signed_at IS NOT NULL")
        ).scalar_one(),
    }


def check_database(report, now):
    db = SessionLocal()
    try:
        revision = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
        head = current_head()
        report.check(
            revision == head,
            "migrations",
            f"database revision {revision!r}; Alembic head {head!r} (not modified by this check)",
        )

        expected = expected_demo_mmsis()
        rows = db.execute(
            text(
                "SELECT mmsi, count(*), min(timestamp), max(timestamp) FROM vessel_tracks "
                "WHERE mmsi = ANY(:mmsis) GROUP BY mmsi"
            ),
            {"mmsis": expected},
        ).all()
        found = {row[0]: row for row in rows}
        missing = sorted(set(expected) - set(found))
        report.check(
            not missing,
            "replay vessels",
            f"{len(found)}/{len(expected)} expected replay MMSIs present"
            + (f"; missing {missing}" if missing else ""),
        )

        positions = sum(row[1] for row in rows)
        report.check(positions > 0, "replay positions", f"{positions} stored positions")

        latest = max((row[3] for row in rows if row[3] is not None), default=None)
        error = stale_after_error(latest, now)
        report.check(
            error is None,
            "replay freshness",
            error or f"newest position {latest.isoformat()} is inside the 168 h window",
        )

        admins = db.execute(
            text(
                "SELECT u.username FROM users u JOIN user_role_assignments r "
                "ON r.user_id = u.id WHERE r.role = 'ADMINISTRATOR' AND u.is_active "
                "ORDER BY u.username"
            )
        ).scalars().all()
        report.check(bool(admins), "local administrator", f"active ADMINISTRATOR account(s): {admins}")

        counts = table_counts(db)
        report.check(
            True,
            "existing cases/reports",
            f"{counts['cases']} case(s), {counts['case_revisions']} revision(s), "
            f"{counts['reports']} report(s), {counts['signed_reports']} signed (read-only)",
        )
        return counts, admins
    finally:
        db.close()


def http_get(client, base, path, **params):
    response = client.get(f"{base}{API_PREFIX}{path}", params=params or None)
    return response


def check_http(report, client, base, expected_mmsis, username):
    try:
        health = client.get(f"{base}/health")
        report.check(
            health.status_code == 200 and health.json().get("status") == "healthy",
            "API health",
            f"HTTP {health.status_code} at {base}/health",
        )
    except httpx.HTTPError as exc:
        report.fail("API health", f"{type(exc).__name__}: {base} is not reachable")
        return

    try:
        vessels = http_get(client, base, "/vessels/", hours=MAX_LOOKBACK_HOURS)
    except httpx.HTTPError as exc:
        report.fail("replay through API", f"{type(exc).__name__}: request failed")
    else:
        payload = vessels.json() if vessels.status_code == 200 else {}
        listed = payload.get("vessels") or []
        mmsis = {vessel.get("mmsi") for vessel in listed}
        overlap = sorted(set(expected_mmsis) & mmsis)
        report.check(
            vessels.status_code == 200 and bool(overlap),
            "replay through API",
            f"HTTP {vessels.status_code}; {len(listed)} vessel(s) over {MAX_LOOKBACK_HOURS} h; "
            f"{len(overlap)} seeded replay vessel(s) returned",
        )

    try:
        environment = http_get(client, base, "/environment/regional")
    except httpx.HTTPError as exc:
        report.fail("historical SST", f"{type(exc).__name__}: request failed")
    else:
        data = environment.json() if environment.status_code == 200 else {}
        required = ("variable", "value", "unit", "observed_at", "attribution")
        shaped = all(key in data for key in required)
        report.check(
            environment.status_code == 200
            and shaped
            and data.get("mode") == "historical"
            and data.get("status") == "available"
            and data.get("unit") == "°C",
            "historical SST",
            (
                f"HTTP {environment.status_code}; {data.get('value')} {data.get('unit')} "
                f"observed {data.get('observed_at')}; mode {data.get('mode')}"
                if environment.status_code == 200
                else f"HTTP {environment.status_code}: prepared Copernicus subset unavailable"
            ),
        )

    try:
        events = http_get(
            client,
            base,
            "/gfw/events/regional/geojson",
            start_date=GFW_START,
            end_date=GFW_END,
            limit=5,
        )
    except httpx.HTTPError as exc:
        report.fail("GFW historical events", f"{type(exc).__name__}: external request failed")
    else:
        if events.status_code == 200:
            payload = events.json()
            errors = geojson_shape_errors(payload)
            report.check(
                not errors,
                "GFW historical events",
                f"HTTP 200; {len(payload.get('features') or [])} point feature(s) of "
                f"{payload.get('total')} for {GFW_START}..{GFW_END}"
                + (f"; problems: {errors[:3]}" if errors else ""),
            )
        else:
            detail = events.text.strip().replace("\n", " ")[:200]
            report.fail(
                "GFW historical events",
                f"HTTP {events.status_code}: external provider unavailable ({detail})",
            )

    if not username:
        report.skip(
            "administrator sign-in",
            "no credentials supplied; set SAMUDRA_VERIFY_USERNAME/SAMUDRA_VERIFY_PASSWORD "
            "or run in a terminal to confirm sign-in",
        )
        return

    password = os.environ.get("SAMUDRA_VERIFY_PASSWORD")
    if password is None:
        if sys.stdin.isatty():
            password = getpass.getpass(f"Password for {username} (hidden, not stored): ")
        else:
            report.skip("administrator sign-in", "no password supplied in a non-interactive run")
            return
    if not password:
        report.skip("administrator sign-in", "empty password supplied; nothing was checked")
        return

    try:
        login = client.post(
            f"{base}{API_PREFIX}/auth/login",
            json={"username": username, "password": password},
        )
    except httpx.HTTPError as exc:
        report.fail("administrator sign-in", f"{type(exc).__name__}: request failed")
        return
    if login.status_code != 200:
        report.fail("administrator sign-in", f"HTTP {login.status_code}; login rejected")
        return

    try:
        me = client.get(f"{base}{API_PREFIX}/auth/me")
        user = me.json() if me.status_code == 200 else {}
        roles = user.get("roles") or []
        report.check(
            me.status_code == 200
            and user.get("username") == username
            and "ADMINISTRATOR" in roles,
            "administrator sign-in",
            f"session accepted for {user.get('username')!r}; roles {roles}; CSRF cookie "
            f"{'present' if client.cookies.get('samudra_csrf') else 'missing'}",
        )
    finally:
        csrf = client.cookies.get("samudra_csrf")
        if csrf:
            try:
                client.post(f"{base}{API_PREFIX}/auth/logout", headers={"X-CSRF-Token": csrf})
            except httpx.HTTPError:
                pass


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--username",
        default=os.environ.get("SAMUDRA_VERIFY_USERNAME", ""),
        help="local administrator username for the optional sign-in check",
    )
    args = parser.parse_args(argv)

    if not args.username:
        # Default to the single local administrator when the name is unambiguous.
        db = SessionLocal()
        try:
            admins = db.execute(
                text(
                    "SELECT u.username FROM users u JOIN user_role_assignments r "
                    "ON r.user_id = u.id WHERE r.role = 'ADMINISTRATOR' AND u.is_active"
                )
            ).scalars().all()
            args.username = admins[0] if len(admins) == 1 else ""
        finally:
            db.close()

    now = datetime.now(timezone.utc)
    report = Report()
    print(f"SamudraSense judging replay verification ({now.isoformat()})")
    print("Read-only: no reseed, no reset, no migration. Replay is local/synthetic.\n")

    counts_before, _ = check_database(report, now)
    expected = expected_demo_mmsis()

    headers = {"Accept": "application/json"}
    with httpx.Client(timeout=30.0, headers=headers, follow_redirects=True) as client:
        check_http(report, client, args.api_base.rstrip("/"), expected, args.username)

    db = SessionLocal()
    try:
        counts_after = table_counts(db)
    finally:
        db.close()
    report.check(
        counts_before == counts_after,
        "case/report preservation",
        "row counts unchanged"
        if counts_before == counts_after
        else f"counts changed: before={counts_before} after={counts_after}",
    )

    print()
    if report.failed:
        print(f"RESULT: FAIL ({report.failed} failed, {report.skipped} skipped)")
        return 1
    if report.skipped:
        print(f"RESULT: PARTIAL ({report.skipped} skipped; nothing failed)")
        return 2
    print("RESULT: PASS (replay, sources and sign-in verified)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
