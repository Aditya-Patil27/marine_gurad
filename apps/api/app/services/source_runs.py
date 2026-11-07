"""Persist and read bounded provider-run metadata.

The table deliberately stores no raw provider payloads and no credentials. Error
messages are limited to short operator-safe strings produced by our adapters.
"""
import json
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

MAX_ERROR_MESSAGE = 200
RUN_FIELDS = (
    "id", "provider", "operation", "status", "mode", "started_at", "finished_at",
    "request_count", "position_count", "event_count", "error_category",
    "error_message", "checkpoint", "triggered_by",
)
_SELECT = ", ".join(RUN_FIELDS)


def _iso(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def serialize_run(row) -> dict:
    mapping = dict(row)
    checkpoint = mapping.get("checkpoint") or {}
    if not isinstance(checkpoint, dict):
        checkpoint = {}
    return {
        "id": mapping["id"],
        "provider": mapping["provider"],
        "operation": mapping["operation"],
        "status": mapping["status"],
        "mode": mapping["mode"],
        "started_at": _iso(mapping["started_at"]),
        "finished_at": _iso(mapping["finished_at"]),
        "request_count": mapping["request_count"],
        "position_count": mapping["position_count"],
        "event_count": mapping["event_count"],
        "error_category": mapping["error_category"],
        "error_message": mapping["error_message"],
        "checkpoint": checkpoint,
        "triggered_by": mapping["triggered_by"],
    }


def bounded_message(message) -> str:
    """Collapse whitespace and cap an operator-safe error message."""
    return " ".join(str(message or "").split())[:MAX_ERROR_MESSAGE]


def error_category_for(message: str) -> str:
    lowered = (message or "").lower()
    if "not configured" in lowered or "credentials" in lowered:
        return "config"
    if "quota" in lowered or "rate limit" in lowered:
        return "quota"
    if "authentication" in lowered or "dataset access" in lowered:
        return "auth"
    if "timeout" in lowered:
        return "timeout"
    if "connection" in lowered or "unavailable" in lowered:
        return "network"
    return "provider"


def insert_run(
    db: Session,
    *,
    provider: str,
    operation: str,
    status: str,
    mode: str,
    started_at: datetime,
    finished_at: datetime,
    request_count: int,
    position_count: int | None = None,
    event_count: int | None = None,
    error_category: str | None = None,
    error_message: str | None = None,
    checkpoint: dict | None = None,
    triggered_by: str,
) -> dict:
    checkpoint_json = json.dumps(checkpoint or {}, ensure_ascii=False, separators=(",", ":"))
    row = db.execute(
        text(
            "INSERT INTO source_runs (provider, operation, status, mode, started_at, "
            "finished_at, request_count, position_count, event_count, error_category, "
            "error_message, checkpoint, triggered_by) "
            "VALUES (:provider, :operation, :status, :mode, :started_at, :finished_at, "
            ":request_count, :position_count, :event_count, :error_category, :error_message, "
            "CAST(:checkpoint AS jsonb), :triggered_by) "
            f"RETURNING {_SELECT}"
        ),
        {
            "provider": provider,
            "operation": operation,
            "status": status,
            "mode": mode,
            "started_at": started_at,
            "finished_at": finished_at,
            "request_count": request_count,
            "position_count": position_count,
            "event_count": event_count,
            "error_category": error_category,
            "error_message": bounded_message(error_message) if error_message else None,
            "checkpoint": checkpoint_json,
            "triggered_by": triggered_by,
        },
    ).mappings().one()
    db.commit()
    return serialize_run(row)


def latest_runs(db: Session, providers=("aisstream", "gfw")) -> dict[str, dict]:
    """Latest persisted run per provider; no provider request and no write."""
    rows = db.execute(
        text(
            f"SELECT DISTINCT ON (provider) {_SELECT} FROM source_runs "
            "WHERE provider = ANY(:providers) "
            "ORDER BY provider, started_at DESC, id DESC"
        ),
        {"providers": list(providers)},
    ).mappings().all()
    return {row["provider"]: serialize_run(row) for row in rows}
