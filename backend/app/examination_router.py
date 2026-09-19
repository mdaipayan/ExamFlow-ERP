import hashlib
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from .auth_dependencies import require_roles
from .db import get_db
from .examination_schemas import AddCourseRequest, ExaminationCreate

router = APIRouter(prefix="/api/examinations", tags=["examinations"])


def institution_id_from_claims(claims: dict) -> UUID:
    value = claims.get("institution_id")
    if not value:
        raise HTTPException(status_code=400, detail="Your account is not linked to an institution.")
    return UUID(str(value))


def canonical_hash(parameters: dict) -> str:
    canonical = json.dumps(
        parameters,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


@router.post("", status_code=status.HTTP_201_CREATED)
def create_examination(
    payload: ExaminationCreate,
    claims: dict = Depends(require_roles("SUPER_ADMIN", "COE")),
    db: Session = Depends(get_db),
):
    institution_id = institution_id_from_claims(claims)

    valid_structure = db.execute(
        text("""
            SELECT 1
            FROM semesters s
            JOIN programmes p ON p.id = s.programme_id
            WHERE s.id = :semester_id
              AND s.programme_id = :programme_id
              AND p.institution_id = :institution_id
        """),
        {
            "semester_id": payload.semester_id,
            "programme_id": payload.programme_id,
            "institution_id": institution_id,
        },
    ).first()
    if valid_structure is None:
        raise HTTPException(status_code=400, detail="Programme and semester do not belong together.")

    regulation = db.execute(
        text("""
            SELECT r.id AS regulation_id, rv.id, rv.version_label, rv.status, rv.parameters
            FROM regulation_versions rv
            JOIN regulations r ON r.id = rv.regulation_id
            WHERE rv.id = :regulation_version_id
              AND r.institution_id = :institution_id
        """),
        {"regulation_version_id": payload.regulation_version_id, "institution_id": institution_id},
    ).mappings().first()
    if regulation is None:
        raise HTTPException(status_code=404, detail="Regulation version not found.")
    if regulation["status"] != "APPROVED":
        raise HTTPException(status_code=409, detail="Only an approved regulation version can be used for an examination.")

    row = db.execute(
        text("""
            INSERT INTO examinations
                (institution_id, programme_id, semester_id, regulation_version_id,
                 name, term_label, status, starts_on, ends_on, created_by)
            VALUES
                (:institution_id, :programme_id, :semester_id, :regulation_version_id,
                 :name, :term_label, 'DRAFT', :starts_on, :ends_on, :created_by)
            RETURNING id, programme_id, semester_id, regulation_version_id,
                      name, term_label, status, starts_on, ends_on
        """),
        {
            "institution_id": institution_id,
            **payload.model_dump(),
            "created_by": UUID(str(claims["sub"])),
        },
    ).mappings().one()
    db.commit()
    return dict(row)


@router.get("")
def list_examinations(
    claims: dict = Depends(require_roles(
        "SUPER_ADMIN", "COE", "TC", "SCRUTINIZER", "DATA_ENTRY"
    )),
    db: Session = Depends(get_db),
):
    institution_id = institution_id_from_claims(claims)
    rows = db.execute(
        text("""
            SELECT e.id, e.name, e.term_label, e.status,
                   e.programme_id, p.code AS programme_code, p.name AS programme_name,
                   e.semester_id, s.number AS semester_number,
                   e.regulation_version_id, rv.version_label
            FROM examinations e
            JOIN programmes p ON p.id = e.programme_id
            JOIN semesters s ON s.id = e.semester_id
            JOIN regulation_versions rv ON rv.id = e.regulation_version_id
            WHERE e.institution_id = :institution_id
            ORDER BY e.created_at DESC
        """),
        {"institution_id": institution_id},
    ).mappings().all()
    return [dict(row) for row in rows]


@router.post("/{examination_id}/courses", status_code=status.HTTP_201_CREATED)
def add_course(
    examination_id: UUID,
    payload: AddCourseRequest,
    claims: dict = Depends(require_roles("SUPER_ADMIN", "COE")),
    db: Session = Depends(get_db),
):
    institution_id = institution_id_from_claims(claims)
    exam = db.execute(
        text("SELECT id, status FROM examinations WHERE id = :id AND institution_id = :institution_id"),
        {"id": examination_id, "institution_id": institution_id},
    ).mappings().first()
    if exam is None:
        raise HTTPException(status_code=404, detail="Examination not found.")
    if exam["status"] != "DRAFT":
        raise HTTPException(status_code=409, detail="Courses can only be added while the examination is in Draft.")

    owns_course = db.execute(
        text("SELECT 1 FROM courses WHERE id = :course_id AND institution_id = :institution_id"),
        {"course_id": payload.course_id, "institution_id": institution_id},
    ).first()
    if owns_course is None:
        raise HTTPException(status_code=404, detail="Course not found.")

    try:
        row = db.execute(
            text("""
                INSERT INTO examination_courses (examination_id, course_id)
                VALUES (:examination_id, :course_id)
                RETURNING examination_id, course_id
            """),
            {"examination_id": examination_id, "course_id": payload.course_id},
        ).mappings().one()
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Course is already added to this examination.") from exc
    return dict(row)


@router.get("/{examination_id}/courses")
def list_exam_courses(
    examination_id: UUID,
    claims: dict = Depends(require_roles(
        "SUPER_ADMIN", "COE", "TC", "SCRUTINIZER", "DATA_ENTRY"
    )),
    db: Session = Depends(get_db),
):
    institution_id = institution_id_from_claims(claims)
    rows = db.execute(
        text("""
            SELECT c.id, c.code, c.name, c.credits, c.course_type, c.is_audit
            FROM examination_courses ec
            JOIN examinations e ON e.id = ec.examination_id
            JOIN courses c ON c.id = ec.course_id
            WHERE ec.examination_id = :examination_id
              AND e.institution_id = :institution_id
            ORDER BY c.code
        """),
        {"examination_id": examination_id, "institution_id": institution_id},
    ).mappings().all()
    return [dict(row) for row in rows]


@router.post("/{examination_id}/activate")
def activate_examination(
    examination_id: UUID,
    claims: dict = Depends(require_roles("SUPER_ADMIN", "COE")),
    db: Session = Depends(get_db),
):
    institution_id = institution_id_from_claims(claims)
    exam = db.execute(
        text("""
            SELECT e.id, e.status, e.regulation_version_id, rv.regulation_id,
                   rv.version_label, rv.status AS regulation_status, rv.parameters
            FROM examinations e
            JOIN regulation_versions rv ON rv.id = e.regulation_version_id
            WHERE e.id = :examination_id AND e.institution_id = :institution_id
        """),
        {"examination_id": examination_id, "institution_id": institution_id},
    ).mappings().first()

    if exam is None:
        raise HTTPException(status_code=404, detail="Examination not found.")
    if exam["status"] != "DRAFT":
        raise HTTPException(status_code=409, detail="Only Draft examinations can be activated.")
    if exam["regulation_status"] != "APPROVED":
        raise HTTPException(status_code=409, detail="The selected regulation version is not approved.")

    course_count = db.execute(
        text("SELECT count(*) FROM examination_courses WHERE examination_id = :examination_id"),
        {"examination_id": examination_id},
    ).scalar_one()
    if course_count == 0:
        raise HTTPException(status_code=409, detail="Add at least one course before activating the examination.")

    parameters = exam["parameters"] or {}
    snapshot_hash = canonical_hash(parameters)

    try:
        db.execute(
            text("""
                INSERT INTO examination_parameter_snapshots
                    (examination_id, regulation_id, regulation_version_id,
                     version_label, parameters, content_hash, frozen_by_user_id)
                VALUES
                    (:examination_id, :regulation_id, :regulation_version_id,
                     :version_label, CAST(:parameters AS jsonb), :content_hash, :frozen_by_user_id)
            """),
            {
                "examination_id": examination_id,
                "regulation_id": exam["regulation_id"],
                "regulation_version_id": exam["regulation_version_id"],
                "version_label": exam["version_label"],
                "parameters": json.dumps(parameters, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
                "content_hash": snapshot_hash,
                "frozen_by_user_id": UUID(str(claims["sub"])),
            },
        )
        updated = db.execute(
            text("""
                UPDATE examinations
                SET status = 'IN_PROGRESS'
                WHERE id = :examination_id AND institution_id = :institution_id
                RETURNING id, status
            """),
            {"examination_id": examination_id, "institution_id": institution_id},
        ).mappings().one()
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Could not activate examination.") from exc

    return {
        "examination": dict(updated),
        "rule_snapshot": {
            "version_label": exam["version_label"],
            "content_hash": snapshot_hash,
            "frozen": True,
        },
    }
