from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from .auth_dependencies import require_roles
from .db import get_db
from .registration_schemas import RegisterStudentsRequest, SetEligibilityRequest

router = APIRouter(prefix="/api/examinations", tags=["registration"])


def institution_id_from_claims(claims: dict) -> UUID:
    value = claims.get("institution_id")
    if not value:
        raise HTTPException(status_code=400, detail="Your account is not linked to an institution.")
    return UUID(str(value))


def get_exam(db: Session, examination_id: UUID, institution_id: UUID):
    row = db.execute(
        text("""
            SELECT id, programme_id, semester_id, status
            FROM examinations
            WHERE id = :id AND institution_id = :institution_id
        """),
        {"id": examination_id, "institution_id": institution_id},
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Examination not found.")
    return row


@router.post("/{examination_id}/register-students", status_code=status.HTTP_201_CREATED)
def register_students(
    examination_id: UUID,
    payload: RegisterStudentsRequest,
    claims: dict = Depends(require_roles("SUPER_ADMIN", "COE")),
    db: Session = Depends(get_db),
):
    institution_id = institution_id_from_claims(claims)
    exam = get_exam(db, examination_id, institution_id)

    if exam["status"] not in {"DRAFT", "IN_PROGRESS"}:
        raise HTTPException(status_code=409, detail="Student registration is closed for this examination.")

    course_rows = db.execute(
        text("""
            SELECT ec.course_id
            FROM examination_courses ec
            WHERE ec.examination_id = :examination_id
            ORDER BY ec.course_id
        """),
        {"examination_id": examination_id},
    ).all()
    if not course_rows:
        raise HTTPException(status_code=409, detail="Add courses to the examination before registering students.")

    student_ids = list(dict.fromkeys(payload.student_ids))

    eligible_rows = db.execute(
        text("""
            SELECT DISTINCT s.id
            FROM students s
            JOIN student_programme_enrolments spe ON spe.student_id = s.id
            WHERE s.institution_id = :institution_id
              AND spe.programme_id = :programme_id
        """),
        {
            "institution_id": institution_id,
            "programme_id": exam["programme_id"],
        },
    ).scalars().all()

    eligible_set = {UUID(str(student_id)) for student_id in eligible_rows}
    valid_students = [student_id for student_id in student_ids if student_id in eligible_set]

    valid_set = set(valid_students)
    invalid = [str(student_id) for student_id in student_ids if student_id not in valid_set]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail={"message": "Some students are not enrolled in this programme.", "student_ids": invalid},
        )

    registered = 0
    try:
        for student_id in valid_students:
            for course_row in course_rows:
                db.execute(
                    text("""
                        INSERT INTO examination_registrations
                            (examination_id, student_id, course_id)
                        VALUES
                            (:examination_id, :student_id, :course_id)
                        ON CONFLICT (examination_id, student_id, course_id) DO NOTHING
                    """),
                    {
                        "examination_id": examination_id,
                        "student_id": student_id,
                        "course_id": course_row[0],
                    },
                )
                registered += 1
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="Student registration failed.") from exc

    return {
        "students": len(valid_students),
        "course_registrations_added_or_existing": registered,
    }


@router.get("/{examination_id}/registrations")
def list_registrations(
    examination_id: UUID,
    claims: dict = Depends(require_roles(
        "SUPER_ADMIN", "COE", "TC", "SCRUTINIZER", "DATA_ENTRY"
    )),
    db: Session = Depends(get_db),
):
    institution_id = institution_id_from_claims(claims)
    get_exam(db, examination_id, institution_id)

    rows = db.execute(
        text("""
            SELECT er.id, er.student_id, s.registration_number, s.roll_number,
                   s.full_name, er.course_id, c.code AS course_code,
                   c.name AS course_name, er.attempt_type, er.registration_status
            FROM examination_registrations er
            JOIN students s ON s.id = er.student_id
            JOIN courses c ON c.id = er.course_id
            JOIN examinations e ON e.id = er.examination_id
            WHERE er.examination_id = :examination_id
              AND e.institution_id = :institution_id
            ORDER BY s.registration_number, c.code
        """),
        {"examination_id": examination_id, "institution_id": institution_id},
    ).mappings().all()
    return [dict(row) for row in rows]


@router.put("/{examination_id}/eligibility/{student_id}/{course_id}")
def set_eligibility(
    examination_id: UUID,
    student_id: UUID,
    course_id: UUID,
    payload: SetEligibilityRequest,
    claims: dict = Depends(require_roles("SUPER_ADMIN", "COE", "TC")),
    db: Session = Depends(get_db),
):
    institution_id = institution_id_from_claims(claims)
    exam = get_exam(db, examination_id, institution_id)
    if exam["status"] not in {"DRAFT", "IN_PROGRESS"}:
        raise HTTPException(status_code=409, detail="Eligibility cannot be changed after review has started.")

    registered = db.execute(
        text("""
            SELECT 1
            FROM examination_registrations
            WHERE examination_id = :examination_id
              AND student_id = :student_id
              AND course_id = :course_id
        """),
        {
            "examination_id": examination_id,
            "student_id": student_id,
            "course_id": course_id,
        },
    ).first()
    if registered is None:
        raise HTTPException(status_code=404, detail="Student is not registered for this course in the examination.")

    grade_override = payload.grade_override
    if payload.eligible_for_ese:
        grade_override = None
    else:
        grade_override = grade_override or "I"

    row = db.execute(
        text("""
            INSERT INTO eligibility_records
                (examination_id, student_id, course_id, attendance_percent,
                 eligible_for_ese, reason, grade_override)
            VALUES
                (:examination_id, :student_id, :course_id, :attendance_percent,
                 :eligible_for_ese, :reason, :grade_override)
            ON CONFLICT (examination_id, student_id, course_id)
            DO UPDATE SET
                attendance_percent = EXCLUDED.attendance_percent,
                eligible_for_ese = EXCLUDED.eligible_for_ese,
                reason = EXCLUDED.reason,
                grade_override = EXCLUDED.grade_override
            RETURNING id, examination_id, student_id, course_id,
                      attendance_percent, eligible_for_ese, reason, grade_override
        """),
        {
            "examination_id": examination_id,
            "student_id": student_id,
            "course_id": course_id,
            **payload.model_dump(),
            "grade_override": grade_override,
        },
    ).mappings().one()
    db.commit()
    return dict(row)


@router.get("/{examination_id}/eligibility")
def list_eligibility(
    examination_id: UUID,
    claims: dict = Depends(require_roles(
        "SUPER_ADMIN", "COE", "TC", "SCRUTINIZER", "DATA_ENTRY"
    )),
    db: Session = Depends(get_db),
):
    institution_id = institution_id_from_claims(claims)
    get_exam(db, examination_id, institution_id)

    rows = db.execute(
        text("""
            SELECT er.id, er.student_id, s.registration_number, s.full_name,
                   er.course_id, c.code AS course_code,
                   er.attendance_percent, er.eligible_for_ese,
                   er.reason, er.grade_override
            FROM eligibility_records er
            JOIN students s ON s.id = er.student_id
            JOIN courses c ON c.id = er.course_id
            JOIN examinations e ON e.id = er.examination_id
            WHERE er.examination_id = :examination_id
              AND e.institution_id = :institution_id
            ORDER BY s.registration_number, c.code
        """),
        {"examination_id": examination_id, "institution_id": institution_id},
    ).mappings().all()
    return [dict(row) for row in rows]
