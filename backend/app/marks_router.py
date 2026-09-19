import csv
import io
from decimal import Decimal, InvalidOperation
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from .auth_dependencies import require_roles
from .db import get_db
from .marks_engine import validate_mark, validate_weightages
from .marks_schemas import MarkEntryRequest

router = APIRouter(prefix="/api/examinations", tags=["marks"])


def institution_id_from_claims(claims: dict) -> UUID:
    value = claims.get("institution_id")
    if not value:
        raise HTTPException(status_code=400, detail="Your account is not linked to an institution.")
    return UUID(str(value))


def get_exam(db: Session, examination_id: UUID, institution_id: UUID):
    row = db.execute(
        text("""
            SELECT id, status
            FROM examinations
            WHERE id = :id AND institution_id = :institution_id
        """),
        {"id": examination_id, "institution_id": institution_id},
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Examination not found.")
    return row


def get_component(db: Session, institution_id: UUID, course_id: UUID, component_code: str):
    row = db.execute(
        text("""
            SELECT cc.id, cc.course_id, cc.code, cc.max_marks, cc.weightage, cc.minimum_marks
            FROM course_components cc
            JOIN courses c ON c.id = cc.course_id
            WHERE c.institution_id = :institution_id
              AND cc.course_id = :course_id
              AND cc.code = :component_code
        """),
        {
            "institution_id": institution_id,
            "course_id": course_id,
            "component_code": component_code,
        },
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Course component not found.")
    return row


def assert_registered(db: Session, examination_id: UUID, student_id: UUID, course_id: UUID):
    row = db.execute(
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
    if row is None:
        raise HTTPException(status_code=400, detail="Student is not registered for this course in the examination.")


@router.put("/{examination_id}/marks")
def upsert_mark(
    examination_id: UUID,
    payload: MarkEntryRequest,
    claims: dict = Depends(require_roles("SUPER_ADMIN", "COE", "TC", "DATA_ENTRY")),
    db: Session = Depends(get_db),
):
    institution_id = institution_id_from_claims(claims)
    exam = get_exam(db, examination_id, institution_id)
    if exam["status"] not in {"IN_PROGRESS", "TRIAL"}:
        raise HTTPException(status_code=409, detail="Marks can only be entered while the examination is In Progress or in Trial.")

    assert_registered(db, examination_id, payload.student_id, payload.course_id)
    component = get_component(db, institution_id, payload.course_id, payload.component_code)

    problem = validate_mark(payload.marks, Decimal(str(component["max_marks"])))
    if problem:
        raise HTTPException(status_code=422, detail=problem)

    row = db.execute(
        text("""
            INSERT INTO mark_entries
                (examination_id, student_id, course_id, component_code,
                 marks, max_marks, source, original_marks)
            VALUES
                (:examination_id, :student_id, :course_id, :component_code,
                 :marks, :max_marks, 'MANUAL', :marks)
            ON CONFLICT (examination_id, student_id, course_id, component_code)
            DO UPDATE SET
                marks = EXCLUDED.marks,
                max_marks = EXCLUDED.max_marks,
                source = 'MANUAL',
                original_marks = COALESCE(mark_entries.original_marks, EXCLUDED.original_marks),
                updated_at = now()
            RETURNING id, examination_id, student_id, course_id,
                      component_code, marks, max_marks, source
        """),
        {
            "examination_id": examination_id,
            "student_id": payload.student_id,
            "course_id": payload.course_id,
            "component_code": payload.component_code,
            "marks": payload.marks,
            "max_marks": component["max_marks"],
        },
    ).mappings().one()
    db.commit()
    return dict(row)


@router.get("/{examination_id}/marks")
def list_marks(
    examination_id: UUID,
    course_id: UUID | None = None,
    claims: dict = Depends(require_roles("SUPER_ADMIN", "COE", "TC", "SCRUTINIZER", "DATA_ENTRY")),
    db: Session = Depends(get_db),
):
    institution_id = institution_id_from_claims(claims)
    get_exam(db, examination_id, institution_id)

    rows = db.execute(
        text("""
            SELECT me.id, me.student_id, s.registration_number, s.roll_number,
                   s.full_name, me.course_id, c.code AS course_code, c.name AS course_name,
                   me.component_code, me.marks, me.max_marks, me.source
            FROM mark_entries me
            JOIN students s ON s.id = me.student_id
            JOIN courses c ON c.id = me.course_id
            WHERE me.examination_id = :examination_id
              AND c.institution_id = :institution_id
              AND (:course_id IS NULL OR me.course_id = :course_id)
            ORDER BY s.registration_number, c.code, me.component_code
        """),
        {"examination_id": examination_id, "institution_id": institution_id, "course_id": course_id},
    ).mappings().all()
    return [dict(row) for row in rows]


@router.post("/{examination_id}/marks/import-csv", status_code=status.HTTP_201_CREATED)
async def import_marks_csv(
    examination_id: UUID,
    file: UploadFile = File(...),
    claims: dict = Depends(require_roles("SUPER_ADMIN", "COE", "TC", "DATA_ENTRY")),
    db: Session = Depends(get_db),
):
    institution_id = institution_id_from_claims(claims)
    exam = get_exam(db, examination_id, institution_id)
    if exam["status"] not in {"IN_PROGRESS", "TRIAL"}:
        raise HTTPException(status_code=409, detail="Marks import is closed for this examination.")

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=415, detail="Please upload a CSV file.")
    raw = await file.read()
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Marks CSV is too large. Maximum size is 10 MB.")

    try:
        text_data = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded.") from exc

    reader = csv.DictReader(io.StringIO(text_data))
    required = {"registration_number", "course_code", "component_code", "marks"}
    headers = set(reader.fieldnames or [])
    missing = sorted(required - headers)
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required columns: {', '.join(missing)}")

    validation_errors: list[dict] = []
    prepared: list[dict] = []

    for row_number, raw_row in enumerate(reader, start=2):
        row = {str(k).strip(): (v or "").strip() for k, v in raw_row.items() if k}
        reg_no = row.get("registration_number", "")
        course_code = row.get("course_code", "")
        component_code = row.get("component_code", "")
        marks_text = row.get("marks", "")

        if not reg_no or not course_code or not component_code:
            validation_errors.append({"row": row_number, "message": "registration_number, course_code and component_code are required."})
            continue

        try:
            marks = Decimal(marks_text) if marks_text != "" else None
        except InvalidOperation:
            validation_errors.append({"row": row_number, "message": "Marks must be numeric."})
            continue

        student = db.execute(
            text("""
                SELECT s.id
                FROM students s
                WHERE s.institution_id = :institution_id
                  AND s.registration_number = :registration_number
            """),
            {"institution_id": institution_id, "registration_number": reg_no},
        ).scalar_one_or_none()
        course = db.execute(
            text("""
                SELECT c.id
                FROM courses c
                WHERE c.institution_id = :institution_id AND c.code = :course_code
            """),
            {"institution_id": institution_id, "course_code": course_code},
        ).scalar_one_or_none()

        if student is None:
            validation_errors.append({"row": row_number, "message": f"Student not found: {reg_no}"})
            continue
        if course is None:
            validation_errors.append({"row": row_number, "message": f"Course not found: {course_code}"})
            continue

        registered = db.execute(
            text("""
                SELECT 1 FROM examination_registrations
                WHERE examination_id = :examination_id AND student_id = :student_id AND course_id = :course_id
            """),
            {"examination_id": examination_id, "student_id": student, "course_id": course},
        ).first()
        if registered is None:
            validation_errors.append({"row": row_number, "message": f"Student {reg_no} is not registered for {course_code}."})
            continue

        component = db.execute(
            text("""
                SELECT id, max_marks, weightage
                FROM course_components
                WHERE course_id = :course_id AND code = :component_code
            """),
            {"course_id": course, "component_code": component_code},
        ).mappings().first()
        if component is None:
            validation_errors.append({"row": row_number, "message": f"Component not found: {course_code}/{component_code}"})
            continue

        problem = validate_mark(marks, Decimal(str(component["max_marks"])))
        if problem:
            validation_errors.append({"row": row_number, "message": f"{problem}: {course_code}/{component_code}"})
            continue

        prepared.append({
            "row_number": row_number,
            "student_id": student,
            "course_id": course,
            "component_code": component_code,
            "marks": marks,
            "max_marks": component["max_marks"],
        })

    if validation_errors:
        db.rollback()
        return {
            "saved": False,
            "created": 0,
            "updated": 0,
            "errors": validation_errors,
            "message": "Nothing was saved because the import contains validation errors.",
        }

    batch_id = db.execute(
        text("""
            INSERT INTO mark_import_batches (examination_id, source_filename, imported_by)
            VALUES (:examination_id, :source_filename, :imported_by)
            RETURNING id
        """),
        {
            "examination_id": examination_id,
            "source_filename": file.filename,
            "imported_by": UUID(str(claims["sub"])),
        },
    ).scalar_one()

    created = updated = 0
    try:
        for item in prepared:
            existing = db.execute(
                text("""
                    SELECT id FROM mark_entries
                    WHERE examination_id = :examination_id AND student_id = :student_id
                      AND course_id = :course_id AND component_code = :component_code
                """),
                {
                    "examination_id": examination_id,
                    "student_id": item["student_id"],
                    "course_id": item["course_id"],
                    "component_code": item["component_code"],
                },
            ).scalar_one_or_none()

            db.execute(
                text("""
                    INSERT INTO mark_entries
                        (examination_id, student_id, course_id, component_code, marks, max_marks,
                         source, import_batch_id, original_marks)
                    VALUES
                        (:examination_id, :student_id, :course_id, :component_code, :marks, :max_marks,
                         'IMPORT', :batch_id, :marks)
                    ON CONFLICT (examination_id, student_id, course_id, component_code)
                    DO UPDATE SET
                        marks = EXCLUDED.marks,
                        max_marks = EXCLUDED.max_marks,
                        source = 'IMPORT',
                        import_batch_id = EXCLUDED.import_batch_id,
                        original_marks = COALESCE(mark_entries.original_marks, EXCLUDED.original_marks),
                        updated_at = now()
                """),
                {
                    "examination_id": examination_id,
                    "student_id": item["student_id"],
                    "course_id": item["course_id"],
                    "component_code": item["component_code"],
                    "marks": item["marks"],
                    "max_marks": item["max_marks"],
                    "batch_id": batch_id,
                },
            )
            if existing:
                updated += 1
            else:
                created += 1

        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="Import failed. No marks were saved.") from exc

    return {
        "saved": True,
        "batch_id": str(batch_id),
        "created": created,
        "updated": updated,
        "errors": [],
        "message": "Marks import completed.",
    }


@router.post("/{examination_id}/marks/validate")
def validate_marks(
    examination_id: UUID,
    claims: dict = Depends(require_roles("SUPER_ADMIN", "COE", "TC", "SCRUTINIZER")),
    db: Session = Depends(get_db),
):
    institution_id = institution_id_from_claims(claims)
    exam = get_exam(db, examination_id, institution_id)
    if exam["status"] not in {"IN_PROGRESS", "TRIAL", "UNDER_REVIEW"}:
        raise HTTPException(status_code=409, detail="Marks cannot be validated at this stage.")

    db.execute(text("""
        DELETE FROM mark_validation_issues
        WHERE examination_id = :examination_id
    """), {"examination_id": examination_id})

    issues: list[dict] = []

    courses = db.execute(
        text("""
            SELECT ec.course_id, c.code, c.name
            FROM examination_courses ec
            JOIN examinations e ON e.id = ec.examination_id
            JOIN courses c ON c.id = ec.course_id
            WHERE ec.examination_id = :examination_id AND e.institution_id = :institution_id
            ORDER BY c.code
        """),
        {"examination_id": examination_id, "institution_id": institution_id},
    ).mappings().all()

    for course in courses:
        components = db.execute(
            text("""
                SELECT code, max_marks, weightage
                FROM course_components
                WHERE course_id = :course_id
                ORDER BY sort_order, code
            """),
            {"course_id": course["course_id"]},
        ).mappings().all()

        weightage_error = validate_weightages([Decimal(str(x["weightage"])) for x in components])
        if weightage_error:
            issues.append({
                "severity": "ERROR",
                "course_id": str(course["course_id"]),
                "code": "WEIGHTAGE_TOTAL_INVALID",
                "message": f"{course['code']}: {weightage_error}",
            })

        registrations = db.execute(
            text("""
                SELECT er.student_id, s.registration_number, s.full_name
                FROM examination_registrations er
                JOIN students s ON s.id = er.student_id
                WHERE er.examination_id = :examination_id AND er.course_id = :course_id
                ORDER BY s.registration_number
            """),
            {"examination_id": examination_id, "course_id": course["course_id"]},
        ).mappings().all()

        for student in registrations:
            for component in components:
                mark = db.execute(
                    text("""
                        SELECT marks
                        FROM mark_entries
                        WHERE examination_id = :examination_id
                          AND student_id = :student_id
                          AND course_id = :course_id
                          AND component_code = :component_code
                    """),
                    {
                        "examination_id": examination_id,
                        "student_id": student["student_id"],
                        "course_id": course["course_id"],
                        "component_code": component["code"],
                    },
                ).scalar_one_or_none()

                if mark is None:
                    issues.append({
                        "severity": "ERROR",
                        "student_id": str(student["student_id"]),
                        "course_id": str(course["course_id"]),
                        "code": "MISSING_MARK",
                        "message": f"{student['registration_number']} · {course['code']} · {component['code']}: mark missing.",
                    })

    for issue in issues:
        db.execute(
            text("""
                INSERT INTO mark_validation_issues
                    (examination_id, student_id, course_id, severity, code, message)
                VALUES
                    (:examination_id, :student_id, :course_id, :severity, :code, :message)
            """),
            {
                "examination_id": examination_id,
                "student_id": UUID(issue["student_id"]) if issue.get("student_id") else None,
                "course_id": UUID(issue["course_id"]) if issue.get("course_id") else None,
                "severity": issue["severity"],
                "code": issue["code"],
                "message": issue["message"],
            },
        )

    db.commit()

    errors = sum(1 for x in issues if x["severity"] == "ERROR")
    warnings = sum(1 for x in issues if x["severity"] == "WARNING")
    return {
        "examination_id": str(examination_id),
        "errors": errors,
        "warnings": warnings,
        "issues": issues,
        "message": "Validation completed.",
    }
