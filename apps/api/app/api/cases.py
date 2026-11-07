"""Stable investigation cases linking an assessment to report revisions."""
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.auth import csrf_protect, require_analyst, require_viewer
from app.api.reports import digest
from app.database import get_db
from app.schemas.user import UserResponse

router = APIRouter()


class CreateCase(BaseModel):
    assessment_id: UUID
    title: str = Field(min_length=1, max_length=200)


class AddRevision(BaseModel):
    report_id: int = Field(gt=0)
    expected_version: int = Field(ge=0)


class StatusTransition(BaseModel):
    expected_version: int = Field(ge=0)
    note: str | None = Field(default=None, max_length=500)


def _append_event(db: Session, case_id: UUID | str, event: str, actor: str, note: str | None = None) -> None:
    db.execute(
        text("""INSERT INTO case_events (case_id, event, actor, note)
                VALUES (:case_id, :event, :actor, :note)"""),
        {"case_id": str(case_id), "event": event, "actor": actor, "note": note},
    )


@router.get("/")
def list_cases(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
               _viewer: UserResponse = Depends(require_viewer), db: Session = Depends(get_db)):
    rows = db.execute(text("SELECT * FROM investigation_cases ORDER BY created_at DESC, id LIMIT :limit OFFSET :offset"),
                      {"limit": limit, "offset": offset})
    return [dict(row._mapping) for row in rows]


@router.post("/", status_code=201)
def create_case(payload: CreateCase, user: UserResponse = Depends(require_analyst),
                _csrf: None = Depends(csrf_protect), db: Session = Depends(get_db)):
    title = payload.title.strip()
    if not title:
        raise HTTPException(422, "Case title must not be empty")
    assessment = db.execute(text("SELECT mmsi FROM vessel_assessments WHERE id = :id"),
                            {"id": str(payload.assessment_id)}).first()
    if assessment is None:
        raise HTTPException(404, "Assessment not found")
    case_id = uuid4()
    try:
        row = db.execute(text("""INSERT INTO investigation_cases (id, mmsi, assessment_id, title, created_by)
        VALUES (:id, :mmsi, :assessment_id, :title, :created_by) RETURNING *"""),
        {"id": str(case_id), "mmsi": assessment.mmsi, "assessment_id": str(payload.assessment_id),
         "title": title, "created_by": user.username}).one()
        _append_event(db, case_id, "opened", user.username)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Case could not be created") from exc
    return dict(row._mapping)


@router.get("/{case_id}")
def get_case(case_id: UUID, _viewer: UserResponse = Depends(require_viewer), db: Session = Depends(get_db)):
    row = db.execute(text("SELECT * FROM investigation_cases WHERE id = :id"), {"id": str(case_id)}).first()
    if row is None:
        raise HTTPException(404, "Case not found")
    revisions = db.execute(text("""SELECT r.version, r.report_id, r.report_sha256, r.created_by, r.created_at,
        i.sha256 AS current_sha256, i.snapshot, i.signed_at, i.signed_by
        FROM investigation_case_revisions r JOIN incident_reports i ON i.id = r.report_id
        WHERE r.case_id = :id ORDER BY r.version"""), {"id": str(case_id)})
    result = dict(row._mapping)
    result["revisions"] = []
    for revision in revisions:
        value = dict(revision._mapping)
        value["integrity_ok"] = digest(value["snapshot"]) == value["report_sha256"] == value["current_sha256"]
        result["revisions"].append(value)
    events = db.execute(
        text("""SELECT id, event, actor, note, created_at
                FROM case_events
                WHERE case_id = :id
                ORDER BY created_at, id"""),
        {"id": str(case_id)},
    )
    result["events"] = [dict(event._mapping) for event in events]
    return result


def _transition_case(
    case_id: UUID,
    payload: StatusTransition,
    user: UserResponse,
    target_status: str,
    event: str,
    db: Session,
):
    case = db.execute(
        text("SELECT * FROM investigation_cases WHERE id = :id FOR UPDATE"),
        {"id": str(case_id)},
    ).first()
    if case is None:
        raise HTTPException(404, "Case not found")
    if case.version != payload.expected_version:
        raise HTTPException(409, "Case changed; reload before retrying")
    expected_status = "open" if target_status == "closed" else "closed"
    if case.status != expected_status:
        raise HTTPException(409, f"Only {expected_status} cases can be {event}")
    note = (payload.note or "").strip() or None
    try:
        db.execute(
            text("""UPDATE investigation_cases
                    SET status = :status, version = version + 1
                    WHERE id = :id"""),
            {"status": target_status, "id": str(case_id)},
        )
        _append_event(db, case_id, event, user.username, note)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Case transition could not be recorded") from exc
    return get_case(case_id, _viewer=user, db=db)


@router.post("/{case_id}/close")
def close_case(
    case_id: UUID,
    payload: StatusTransition,
    user: UserResponse = Depends(require_analyst),
    _csrf: None = Depends(csrf_protect),
    db: Session = Depends(get_db),
):
    return _transition_case(case_id, payload, user, "closed", "closed", db)


@router.post("/{case_id}/reopen")
def reopen_case(
    case_id: UUID,
    payload: StatusTransition,
    user: UserResponse = Depends(require_analyst),
    _csrf: None = Depends(csrf_protect),
    db: Session = Depends(get_db),
):
    return _transition_case(case_id, payload, user, "open", "reopened", db)


@router.post("/{case_id}/revisions", status_code=201)
def add_revision(case_id: UUID, payload: AddRevision, user: UserResponse = Depends(require_analyst),
                 _csrf: None = Depends(csrf_protect), db: Session = Depends(get_db)):
    case = db.execute(text("SELECT * FROM investigation_cases WHERE id = :id FOR UPDATE"), {"id": str(case_id)}).first()
    if case is None:
        raise HTTPException(404, "Case not found")
    if case.status != "open" or case.version != payload.expected_version:
        raise HTTPException(409, "Case is closed or changed; reload before retrying")
    report = db.execute(text("SELECT * FROM incident_reports WHERE id = :id FOR SHARE"), {"id": payload.report_id}).first()
    if report is None or report.mmsi != case.mmsi:
        raise HTTPException(404, "Report not found for this case's vessel")
    if digest(report.snapshot) != report.sha256:
        raise HTTPException(409, "Report integrity check failed")
    captured = report.snapshot.get("persisted_assessment") or {}
    if str(captured.get("id")) != str(case.assessment_id):
        raise HTTPException(409, "Report must include this case's assessment")
    version = case.version + 1
    try:
        revision = db.execute(text("""INSERT INTO investigation_case_revisions
            (case_id, version, report_id, report_sha256, created_by)
            VALUES (:id, :version, :report_id, :sha, :created_by) RETURNING *"""),
            {"id": str(case_id), "version": version, "report_id": payload.report_id,
             "sha": report.sha256, "created_by": user.username}).one()
        db.execute(text("UPDATE investigation_cases SET version = :version WHERE id = :id"),
                   {"version": version, "id": str(case_id)})
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Report already belongs to this case") from exc
    return dict(revision._mapping)
