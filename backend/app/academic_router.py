from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from .academic_schemas import (
    ComponentCreate,
    CourseCreate,
    ProgrammeCreate,
    RegulationCreate,
    RegulationVersionCreate,
    SemesterCreate,
)
from .auth_dependencies import require_roles
from .db import get_db

router = APIRouter(prefix="/api/academic", tags=["academic"])


def institution_id_from_claims(claims: dict) -> UUID:
    value = claims.get("institution_id")
    if not value:
        raise HTTPException(status_code=400, detail="Your account is not linked to an institution.")
    return UUID(str(value))


@router.get("/institution")
def get_institution(
    claims: dict = Depends(require_roles("SUPER_ADMIN", "COE", "TC", "SCRUTINIZER", "DATA_ENTRY")),
    db: Session = Depends(get_db),
):
    institution_id = institution_id_from_claims(claims)
    row = db.execute(
        text("SELECT id, name, code, timezone FROM institutions WHERE id = :id"),
        {"id": institution_id},
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Institution not found.")
    return dict(row)


@router.post("/programmes", status_code=status.HTTP_201_CREATED)
def create_programme(
    payload: ProgrammeCreate,
    claims: dict = Depends(require_roles("SUPER_ADMIN", "COE")),
    db: Session = Depends(get_db),
):
    institution_id = institution_id_from_claims(claims)
    try:
        row = db.execute(
            text("""
                INSERT INTO programmes (institution_id, code, name, level, duration_semesters)
                VALUES (:institution_id, :code, :name, :level, :duration_semesters)
                RETURNING id, code, name, level, duration_semesters
            """),
            {"institution_id": institution_id, **payload.model_dump()},
        ).mappings().one()
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Programme code already exists or data is invalid.") from exc
    return dict(row)


@router.get("/programmes")
def list_programmes(
    claims: dict = Depends(require_roles("SUPER_ADMIN", "COE", "TC", "SCRUTINIZER", "DATA_ENTRY")),
    db: Session = Depends(get_db),
):
    institution_id = institution_id_from_claims(claims)
    rows = db.execute(
        text("""
            SELECT id, code, name, level, duration_semesters
            FROM programmes
            WHERE institution_id = :institution_id
            ORDER BY code
        """),
        {"institution_id": institution_id},
    ).mappings().all()
    return [dict(row) for row in rows]


@router.post("/programmes/{programme_id}/semesters", status_code=status.HTTP_201_CREATED)
def create_semester(
    programme_id: UUID,
    payload: SemesterCreate,
    claims: dict = Depends(require_roles("SUPER_ADMIN", "COE")),
    db: Session = Depends(get_db),
):
    institution_id = institution_id_from_claims(claims)
    owns = db.execute(
        text("SELECT 1 FROM programmes WHERE id = :programme_id AND institution_id = :institution_id"),
        {"programme_id": programme_id, "institution_id": institution_id},
    ).first()
    if owns is None:
        raise HTTPException(status_code=404, detail="Programme not found.")
    try:
        row = db.execute(
            text("""
                INSERT INTO semesters (programme_id, number, name)
                VALUES (:programme_id, :number, :name)
                RETURNING id, programme_id, number, name
            """),
            {"programme_id": programme_id, **payload.model_dump()},
        ).mappings().one()
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Semester number already exists for this programme.") from exc
    return dict(row)


@router.get("/programmes/{programme_id}/semesters")
def list_semesters(
    programme_id: UUID,
    claims: dict = Depends(require_roles("SUPER_ADMIN", "COE", "TC", "SCRUTINIZER", "DATA_ENTRY")),
    db: Session = Depends(get_db),
):
    institution_id = institution_id_from_claims(claims)
    rows = db.execute(
        text("""
            SELECT s.id, s.programme_id, s.number, s.name
            FROM semesters s
            JOIN programmes p ON p.id = s.programme_id
            WHERE s.programme_id = :programme_id AND p.institution_id = :institution_id
            ORDER BY s.number
        """),
        {"programme_id": programme_id, "institution_id": institution_id},
    ).mappings().all()
    return [dict(row) for row in rows]


@router.post("/courses", status_code=status.HTTP_201_CREATED)
def create_course(
    payload: CourseCreate,
    claims: dict = Depends(require_roles("SUPER_ADMIN", "COE")),
    db: Session = Depends(get_db),
):
    institution_id = institution_id_from_claims(claims)
    try:
        row = db.execute(
            text("""
                INSERT INTO courses (institution_id, code, name, credits, course_type, is_audit)
                VALUES (:institution_id, :code, :name, :credits, :course_type, :is_audit)
                RETURNING id, code, name, credits, course_type, is_audit
            """),
            {"institution_id": institution_id, **payload.model_dump()},
        ).mappings().one()
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Course code already exists or data is invalid.") from exc
    return dict(row)


@router.get("/courses")
def list_courses(
    claims: dict = Depends(require_roles("SUPER_ADMIN", "COE", "TC", "SCRUTINIZER", "DATA_ENTRY")),
    db: Session = Depends(get_db),
):
    institution_id = institution_id_from_claims(claims)
    rows = db.execute(
        text("""
            SELECT id, code, name, credits, course_type, is_audit
            FROM courses
            WHERE institution_id = :institution_id
            ORDER BY code
        """),
        {"institution_id": institution_id},
    ).mappings().all()
    return [dict(row) for row in rows]


@router.post("/courses/{course_id}/components", status_code=status.HTTP_201_CREATED)
def create_component(
    course_id: UUID,
    payload: ComponentCreate,
    claims: dict = Depends(require_roles("SUPER_ADMIN", "COE")),
    db: Session = Depends(get_db),
):
    institution_id = institution_id_from_claims(claims)
    owns = db.execute(
        text("SELECT 1 FROM courses WHERE id = :course_id AND institution_id = :institution_id"),
        {"course_id": course_id, "institution_id": institution_id},
    ).first()
    if owns is None:
        raise HTTPException(status_code=404, detail="Course not found.")
    try:
        row = db.execute(
            text("""
                INSERT INTO course_components
                    (course_id, code, name, max_marks, weightage, minimum_marks, sort_order)
                VALUES
                    (:course_id, :code, :name, :max_marks, :weightage, :minimum_marks, :sort_order)
                RETURNING id, course_id, code, name, max_marks, weightage, minimum_marks, sort_order
            """),
            {"course_id": course_id, **payload.model_dump()},
        ).mappings().one()
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Component code already exists or data is invalid.") from exc
    return dict(row)


@router.get("/courses/{course_id}/components")
def list_components(
    course_id: UUID,
    claims: dict = Depends(require_roles("SUPER_ADMIN", "COE", "TC", "SCRUTINIZER", "DATA_ENTRY")),
    db: Session = Depends(get_db),
):
    institution_id = institution_id_from_claims(claims)
    rows = db.execute(
        text("""
            SELECT cc.id, cc.course_id, cc.code, cc.name, cc.max_marks,
                   cc.weightage, cc.minimum_marks, cc.sort_order
            FROM course_components cc
            JOIN courses c ON c.id = cc.course_id
            WHERE cc.course_id = :course_id AND c.institution_id = :institution_id
            ORDER BY cc.sort_order, cc.code
        """),
        {"course_id": course_id, "institution_id": institution_id},
    ).mappings().all()
    return [dict(row) for row in rows]


@router.post("/regulations", status_code=status.HTTP_201_CREATED)
def create_regulation(
    payload: RegulationCreate,
    claims: dict = Depends(require_roles("SUPER_ADMIN", "COE")),
    db: Session = Depends(get_db),
):
    institution_id = institution_id_from_claims(claims)
    try:
        row = db.execute(
            text("""
                INSERT INTO regulations (institution_id, name, code)
                VALUES (:institution_id, :name, :code)
                RETURNING id, name, code
            """),
            {"institution_id": institution_id, **payload.model_dump()},
        ).mappings().one()
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Regulation code already exists or data is invalid.") from exc
    return dict(row)


@router.get("/regulations")
def list_regulations(
    claims: dict = Depends(require_roles("SUPER_ADMIN", "COE", "TC", "SCRUTINIZER")),
    db: Session = Depends(get_db),
):
    institution_id = institution_id_from_claims(claims)
    rows = db.execute(
        text("""
            SELECT id, name, code FROM regulations
            WHERE institution_id = :institution_id ORDER BY code
        """),
        {"institution_id": institution_id},
    ).mappings().all()
    return [dict(row) for row in rows]


@router.post("/regulations/{regulation_id}/versions", status_code=status.HTTP_201_CREATED)
def create_regulation_version(
    regulation_id: UUID,
    payload: RegulationVersionCreate,
    claims: dict = Depends(require_roles("SUPER_ADMIN", "COE")),
    db: Session = Depends(get_db),
):
    institution_id = institution_id_from_claims(claims)
    owns = db.execute(
        text("""
            SELECT r.id FROM regulations r
            WHERE r.id = :regulation_id AND r.institution_id = :institution_id
        """),
        {"regulation_id": regulation_id, "institution_id": institution_id},
    ).first()
    if owns is None:
        raise HTTPException(status_code=404, detail="Regulation not found.")

    row = db.execute(
        text("""
            INSERT INTO regulation_versions
                (regulation_id, version_label, status, effective_from, effective_to, parameters)
            VALUES
                (:regulation_id, :version_label, 'DRAFT', :effective_from, :effective_to, CAST(:parameters AS jsonb))
            RETURNING id, regulation_id, version_label, status, effective_from, effective_to, parameters
        """),
        {
            "regulation_id": regulation_id,
            **payload.model_dump(),
            "parameters": __import__("json").dumps(payload.parameters),
        },
    ).mappings().one()
    db.commit()
    return dict(row)


@router.get("/regulations/{regulation_id}/versions")
def list_regulation_versions(
    regulation_id: UUID,
    claims: dict = Depends(require_roles("SUPER_ADMIN", "COE", "TC", "SCRUTINIZER")),
    db: Session = Depends(get_db),
):
    institution_id = institution_id_from_claims(claims)
    rows = db.execute(
        text("""
            SELECT rv.id, rv.regulation_id, rv.version_label, rv.status,
                   rv.effective_from, rv.effective_to, rv.parameters,
                   rv.approved_by, rv.approved_at
            FROM regulation_versions rv
            JOIN regulations r ON r.id = rv.regulation_id
            WHERE rv.regulation_id = :regulation_id AND r.institution_id = :institution_id
            ORDER BY rv.created_at DESC
        """),
        {"regulation_id": regulation_id, "institution_id": institution_id},
    ).mappings().all()
    return [dict(row) for row in rows]
