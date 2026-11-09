"""Evidence snapshots and authenticated officer sign-off; no dispatch.

Listing requires Viewer; drafting requires Analyst; signing requires Approver
(or Administrator) plus CSRF. The legacy ``officer`` body field is accepted for
frontend compatibility but identity always comes from the session cookie.
"""
import hashlib
import json
from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api import gfw
from app.api.auth import csrf_protect, require_analyst, require_approver, require_viewer
from app.api.vessels import get_vessel
from app.api.ocean import load_satellite_observations
from app.api.weather import event_weather_context
from app.database import get_db
from app.schemas.user import UserResponse
from app.services import fleet

router = APIRouter()


def _naive_utc(value: datetime) -> datetime:
    return value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value


def canonical_bytes(snapshot) -> bytes:
    """Stable UTF-8 bytes used by the report checksum and export manifest."""
    return json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(snapshot):
    return hashlib.sha256(canonical_bytes(snapshot)).hexdigest()


def _stored_bytes(value) -> bytes | None:
    stored = value.get("canonical_snapshot")
    if stored is None:
        return None
    return stored.tobytes() if isinstance(stored, memoryview) else bytes(stored)


def report(row):
    value = dict(row._mapping)
    canonical = canonical_bytes(value["snapshot"])
    stored = _stored_bytes(value)
    value["integrity_ok"] = (
        hashlib.sha256(stored or canonical).hexdigest() == value["sha256"]
        and (stored is None or stored == canonical)
    )
    value["canonical_bytes_available"] = stored is not None
    value.pop("canonical_snapshot", None)
    return value


def _validated_manifest(row, db: Session) -> dict:
    """Return export metadata only when the saved report still proves its sources."""
    value = dict(row._mapping)
    snapshot = value["snapshot"]
    canonical = canonical_bytes(snapshot)
    stored = _stored_bytes(value)
    if hashlib.sha256(stored or canonical).hexdigest() != value["sha256"] or (
        stored is not None and stored != canonical
    ):
        raise HTTPException(409, "Evidence snapshot failed integrity verification")
    if str(snapshot.get("mmsi")) != str(value["mmsi"]):
        raise HTTPException(409, "Report snapshot does not identify its stored vessel")

    references = []
    assessment = snapshot.get("persisted_assessment")
    if assessment is not None:
        assessment_id = assessment.get("id") if isinstance(assessment, dict) else None
        linked = db.execute(
            text("SELECT mmsi FROM vessel_assessments WHERE id = :id"), {"id": str(assessment_id)}
        ).first() if assessment_id else None
        if linked is None or str(linked.mmsi) != str(value["mmsi"]):
            raise HTTPException(409, "Report's persisted assessment reference is missing or mismatched")
        references.append({"type": "persisted_assessment", "id": str(assessment_id)})

    event_evidence = snapshot.get("gfw_event_evidence")
    if event_evidence is not None:
        event_snapshot = event_evidence.get("snapshot") if isinstance(event_evidence, dict) else None
        event = event_snapshot.get("event") if isinstance(event_snapshot, dict) else None
        if (
            not isinstance(event, dict)
            or digest(event_snapshot) != event_evidence.get("sha256")
            or str((event.get("vessel") or {}).get("ssvid")) != str(value["mmsi"])
        ):
            raise HTTPException(409, "Report's canonical GFW event reference failed verification")
        references.append({
            "type": "gfw_event",
            "id": event.get("id"),
            "sha256": event_evidence["sha256"],
        })
    if snapshot.get("evidence_basis") == "gfw_event_only" and event_evidence is None:
        raise HTTPException(409, "Event-only report is missing its canonical GFW event reference")

    return {
        "report_id": value["id"],
        "mmsi": value["mmsi"],
        "canonical_json": canonical.decode("utf-8"),
        "canonical_sha256": value["sha256"],
        "canonical_bytes_available": stored is not None,
        "checksum_note": "SHA-256 is an integrity checksum for this stored snapshot, not a digital signature or proof of source authenticity.",
        "evidence_references": references,
        "signed_at": value["signed_at"],
        "signed_by": value["signed_by"],
    }


def _pdf_escape(value: str) -> str:
    return value.encode("latin-1", "replace").decode("latin-1").replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _reviewed_pdf(manifest: dict) -> bytes:
    """A small deterministic PDF; it deliberately contains no generation clock."""
    lines = [
        "SamudraSense reviewed evidence report",
        f"Report ID: {manifest['report_id']}",
        f"Vessel MMSI: {manifest['mmsi']}",
        f"Approved by: {manifest['signed_by']}",
        f"Approved at: {manifest['signed_at']}",
        f"Snapshot SHA-256: {manifest['canonical_sha256']}",
        "Evidence references:",
    ]
    for reference in manifest["evidence_references"]:
        lines.append("- " + ", ".join(f"{key}={value}" for key, value in reference.items()))
    if not manifest["evidence_references"]:
        lines.append("- Server-generated vessel evidence snapshot (no external reference id)")
    lines.extend([
        "Checksum scope: canonical UTF-8 JSON in the accompanying manifest.",
        "This is a human-review aid, not proof of illegal activity.",
    ])
    content = ["BT", "/F1 10 Tf", "50 760 Td", "13 TL"]
    for line in lines:
        content.append(f"({_pdf_escape(line[:150])}) Tj")
        content.append("T*")
    content.append("ET")
    stream = "\n".join(content).encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode("ascii"))
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii"))
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii"))
    return bytes(output)


def _insert_report(db: Session, mmsi: int, snapshot: dict):
    canonical = canonical_bytes(snapshot)
    return db.execute(text("""INSERT INTO incident_reports (mmsi, snapshot, sha256, canonical_snapshot)
        VALUES (:mmsi, CAST(:snapshot AS jsonb), :sha, :canonical_snapshot) RETURNING *"""), {
            "mmsi": mmsi,
            "snapshot": json.dumps(snapshot, ensure_ascii=False),
            "sha": hashlib.sha256(canonical).hexdigest(),
            "canonical_snapshot": canonical,
        }).one()


class CreateReport(BaseModel):
    mmsi: int = Field(ge=100000000, le=999999999)
    lookback_hours: int = Field(default=168, ge=1, le=168)
    include_regional_ocean_context: bool = False
    include_weather_context: bool = False
    assessment_id: UUID | None = None
    window_start: datetime | None = None
    window_end: datetime | None = None
    gfw_event_id: str | None = Field(default=None, min_length=1, max_length=128)
    gfw_start_date: date | None = None
    gfw_end_date: date | None = None
    gfw_offset: int = Field(default=0, ge=0, le=10000)
    gfw_limit: int = Field(default=20, ge=1, le=50)
    include_gfw_ocean_context: bool = False
    event_only: bool = False


def event_only_limitations() -> str:
    return (
        "A GFW event is a historical, inferred event location. It is not a vessel "
        "track, live position, fishing proof or proof of illegality; no AIS "
        "observation or risk assessment supports this record."
    )


async def load_gfw_evidence(request: CreateReport) -> dict | None:
    """Re-fetch and canonicalize the selected GFW event before any report insert."""
    if request.event_only:
        if (
            request.assessment_id is not None
            or request.window_start is not None
            or request.window_end is not None
            or request.include_weather_context
        ):
            raise HTTPException(
                422,
                "event_only cannot be combined with assessment_id, window_start, "
                "window_end or include_weather_context; no report was created.",
            )
        if request.gfw_event_id is None:
            raise HTTPException(
                422,
                "event_only requires gfw_event_id with gfw_start_date and "
                "gfw_end_date; no report was created.",
            )
    if request.gfw_event_id is None:
        if request.gfw_start_date is not None or request.gfw_end_date is not None:
            raise HTTPException(422, "gfw_start_date and gfw_end_date require gfw_event_id")
        return None
    if request.gfw_start_date is None or request.gfw_end_date is None:
        raise HTTPException(422, "gfw_event_id requires gfw_start_date and gfw_end_date")
    page = await gfw.regional_events(
        request.gfw_start_date, request.gfw_end_date, request.gfw_offset, request.gfw_limit
    )
    evidence = gfw.canonical_event_evidence(
        page, request.gfw_event_id, request.include_gfw_ocean_context
    )
    ssvid = (evidence["snapshot"]["event"].get("vessel") or {}).get("ssvid")
    if ssvid is None or str(ssvid) != str(request.mmsi):
        raise HTTPException(
            409,
            "The selected GFW event does not identify this report's vessel; no report was created.",
        )
    return evidence


class SignReport(BaseModel):
    officer: str = Field(
        min_length=1,
        max_length=120,
        description="Legacy typed name; accepted but ignored. Identity comes from the session.",
    )
    reviewed: bool
    expected_sha256: str | None = Field(default=None, min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")


@router.get("/")
def list_reports(
    _viewer: UserResponse = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    return [report(row) for row in db.execute(text("SELECT * FROM incident_reports ORDER BY created_at DESC LIMIT 100"))]


@router.get("/{report_id}")
def get_report(report_id: int, _viewer: UserResponse = Depends(require_viewer), db: Session = Depends(get_db)):
    row = db.execute(text("SELECT * FROM incident_reports WHERE id = :id"), {"id": report_id}).first()
    if row is None:
        raise HTTPException(404, "Report not found")
    return report(row)


@router.get("/{report_id}/manifest")
def report_manifest(report_id: int, _viewer: UserResponse = Depends(require_viewer), db: Session = Depends(get_db)):
    row = db.execute(text("SELECT * FROM incident_reports WHERE id = :id"), {"id": report_id}).first()
    if row is None:
        raise HTTPException(404, "Report not found")
    return _validated_manifest(row, db)


@router.get("/{report_id}/export.pdf")
def export_report_pdf(report_id: int, _viewer: UserResponse = Depends(require_viewer), db: Session = Depends(get_db)):
    row = db.execute(text("SELECT * FROM incident_reports WHERE id = :id"), {"id": report_id}).first()
    if row is None:
        raise HTTPException(404, "Report not found")
    manifest = _validated_manifest(row, db)
    if manifest["signed_at"] is None:
        raise HTTPException(409, "Report must be approved before export")
    return Response(
        _reviewed_pdf(manifest), media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="samudrasense-report-{report_id}.pdf"'},
    )


@router.post("/", status_code=201)
def create_report(
    request: CreateReport,
    # Identity before CSRF so anonymous requests get 401, not 403. All
    # dependencies resolve before the body, so denied requests have no effect.
    _analyst: UserResponse = Depends(require_analyst),
    _csrf: None = Depends(csrf_protect),
    db: Session = Depends(get_db),
    gfw_evidence: dict | None = Depends(load_gfw_evidence),
):
    # The same bounded UTC window as the evidence/assessment callers. When
    # window_start/window_end are omitted, keep the existing rolling call shape.
    if request.event_only:
        # No vessel lookup, assessment or risk score: a GFW event alone cannot
        # produce them, and missing AIS must stay visibly missing.
        if not isinstance(gfw_evidence, dict):
            raise HTTPException(422, "GFW event evidence was not resolved")
        snapshot = {
            "mmsi": request.mmsi,
            "evidence_basis": "gfw_event_only",
            "ais_evidence": {
                "status": "unavailable",
                "note": "No AIS observation or vessel assessment is attached to this report; neither is synthesized or inferred.",
                "limitation": "Missing AIS is a source and reception coverage gap, not evidence that the vessel was absent, did not fish or acted illegally.",
            },
            "assessment": {
                "status": "unavailable",
                "note": "No persisted vessel assessment is attached and no risk score is copied.",
            },
            "gfw_event_evidence": {
                **gfw_evidence,
                "association": "Selected historical inferred GFW event re-fetched from the bounded regional page when this report was created; preserved as a source-bound event point, not a vessel track, live position or proof of illegality.",
            },
            "limitations": event_only_limitations(),
        }
        if request.include_regional_ocean_context:
            context = load_satellite_observations()
            snapshot["regional_ocean_context"] = {
                **context,
                "association": "Regional historical context only; not necessarily concurrent with or at the event position.",
            }
        row = _insert_report(db, request.mmsi, snapshot)
        db.commit()
        return report(row)
    report_window = None
    if request.window_start is not None or request.window_end is not None:
        try:
            report_window = fleet.resolve_window(
                hours=request.lookback_hours,
                start=request.window_start,
                end=request.window_end,
            )
        except fleet.WindowSelectionError as exc:
            raise HTTPException(422, str(exc)) from exc
        snapshot = get_vessel(
            request.mmsi,
            request.lookback_hours,
            db,
            window_start=request.window_start,
            window_end=request.window_end,
        )
    else:
        snapshot = get_vessel(request.mmsi, request.lookback_hours, db)
    if request.assessment_id is not None:
        assessment = db.execute(text("""SELECT id, mmsi, rule_version, source_mode,
            evaluated_at, lookback_hours, score, level, factors, checks, zone, headline,
            window_mode, window_start, window_end
            FROM vessel_assessments WHERE id = :id AND mmsi = :mmsi"""),
            {"id": str(request.assessment_id), "mmsi": request.mmsi}).first()
        if assessment is None:
            raise HTTPException(404, "Assessment not found for this vessel")
        assessment_fields = dict(assessment._mapping)
        persisted_window = fleet.window_payload(
            assessment_fields["window_mode"],
            assessment_fields["window_start"],
            assessment_fields["window_end"],
            assessment_fields["lookback_hours"],
        )
        window_match = None
        if report_window is not None and report_window.mode == "historical":
            if (
                assessment_fields["window_mode"] is None
                or assessment_fields["window_start"] is None
                or assessment_fields["window_end"] is None
            ):
                raise HTTPException(
                    409,
                    "The selected assessment has no stored observation window anchors, "
                    "so it cannot be associated with a historical report window; no report "
                    "was created. Re-run POST /api/v1/alerts/assessments/sync with the same "
                    "window_start and window_end, select the refreshed assessment_id, then "
                    "create the report again.",
                )
            if (
                assessment_fields["window_mode"] != "historical"
                or _naive_utc(assessment_fields["window_start"]) != report_window.start
                or _naive_utc(assessment_fields["window_end"]) != report_window.end
            ):
                raise HTTPException(
                    409,
                    "The selected assessment was evaluated over a different observation "
                    "window; no report was created. Re-run "
                    "POST /api/v1/alerts/assessments/sync with the same window_start and "
                    "window_end, select the refreshed assessment_id, then create the report "
                    "again.",
                )
            window_match = True
        snapshot["persisted_assessment"] = {
            **jsonable_encoder(assessment_fields),
            "association": "Persisted assessment at its evaluation time; vessel details are evaluated separately and may differ.",
            "limitation": "Source and reception coverage are unknown; the score is a screening indicator, not proof of an offence.",
            "window": persisted_window,
            "report_window": snapshot.get("window"),
            "window_match": window_match,
            "window_note": (
                "The persisted assessment stores the actual window it was evaluated over. "
                "A historical report is only created when that stored window matches the "
                "report window exactly; matching anchors are recorded here and hashed."
            ),
        }
    detections = db.execute(text("""SELECT id, observed_at, latitude, longitude, source, scene_id,
        confidence, match_distance_m, match_time_seconds FROM sar_detections
        WHERE matched_mmsi = :mmsi ORDER BY observed_at DESC LIMIT 100"""), {"mmsi": request.mmsi})
    snapshot["sar_candidates"] = []
    for row in detections:
        candidate = dict(row._mapping)
        candidate["observed_at"] = candidate["observed_at"].isoformat()
        snapshot["sar_candidates"].append(candidate)
    if request.gfw_event_id is not None:
        if not isinstance(gfw_evidence, dict):
            raise HTTPException(422, "GFW event evidence was not resolved")
        snapshot["gfw_event_evidence"] = {
            **gfw_evidence,
            "association": "Selected historical inferred GFW event re-fetched from the bounded regional page when this report was created; preserved as a source-bound event point, not a vessel track, live position or proof of illegality.",
        }
    if request.include_regional_ocean_context:
        context = load_satellite_observations()
        snapshot["regional_ocean_context"] = {
            **context,
            "association": "Regional historical context only; not necessarily concurrent with or at the vessel position.",
        }
    if request.include_weather_context:
        snapshot["weather_context"] = {
            **event_weather_context(db, request.mmsi),
            "captured": "Weather was fetched from the existing event-time weather path when this report was created.",
            "association": "Context only; it may differ from weather displayed earlier, does not prove why AIS stopped, and does not change risk scores or evidence states.",
        }
    row = _insert_report(db, request.mmsi, snapshot)
    db.commit()
    return report(row)


@router.post("/{report_id}/sign")
def sign_report(
    report_id: int,
    request: SignReport,
    # Approver identity before CSRF; see create_report for ordering rationale.
    current_user: UserResponse = Depends(require_approver),
    _csrf: None = Depends(csrf_protect),
    db: Session = Depends(get_db),
):
    if not request.reviewed:
        raise HTTPException(400, "Evidence review is required")
    row = db.execute(text("SELECT * FROM incident_reports WHERE id = :id FOR UPDATE"), {"id": report_id}).first()
    if not row:
        raise HTTPException(404, "Report not found")
    current = report(row)
    if not current["integrity_ok"]:
        raise HTTPException(409, "Evidence snapshot failed integrity verification")
    if request.expected_sha256 is not None and request.expected_sha256 != current["sha256"]:
        raise HTTPException(409, "Report changed; reload before approving")
    _validated_manifest(row, db)
    if current["signed_at"]:
        raise HTTPException(409, "Report has already been signed")
    row = db.execute(text("""UPDATE incident_reports SET signed_by = :officer, signed_at = :now
        WHERE id = :id RETURNING *"""), {"officer": current_user.username, "now": datetime.now(timezone.utc), "id": report_id}).one()
    db.commit()
    return report(row)
