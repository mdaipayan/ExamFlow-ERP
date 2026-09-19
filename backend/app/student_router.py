import csv
import io
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from .auth_dependencies import require_roles
from .db import get_db
from .student_schemas import EnrollmentCreate, StudentCreate

router = APIRouter(prefix="/api/students", tags=["students"])


def institution_id_from_claims(claims: dict) -> UUID:
    value = claims.get("institution_id")
    if not value:
        raise HTTPException(status_code=400, detail="Your account is not linked to an institution.")
    return UUID(str(value))


@router.get("")
def list_students(
    search: str | None = None,
    claims: dict = Depends(require_roles(
        "SUPER_ADMIN", "COE", "TC", "SCRUTINIZER", "DATA_ENTRY", "FACULTY"
    )),
    db: Session = Depends(get_db),
):
    institution_id = institution_id_from_claims(claims)
    term = (search or "").strip()
    rows = db.execute(
        text("""
            SELECT id, registration_number, roll_number, full_name, gender, mother_name, status
            FROM students
            WHERE institution_id = :institution_id
              AND (
                :term = ''
                OR registration_number ILIKE '%' || :term || '%'
                OR coalesce(roll_number, '') ILIKE '%' || :term || '%'
                OR full_name ILIKE '%' || :term || '%'
              )
            ORDER BY registration_number
            LIMIT 500
        """),
        {"institution_id": institution_id, "term": term},
    ).mappings().all()
    return [dict(row) for row in rows]


@router.get("/{student_id}")
def get_student(
    student_id: UUID,
    claims: dict = Depends(require_roles(
        "SUPER_ADMIN", "COE", "TC", "SCRUTINIZER", "DATA_ENTRY", "FACULTY", "STUDENT"
    )),
    db: Session = Depends(get_db),
):
    institution_id = institution_id_from_claims(claims)
    row = db.execute(
        text("""
            SELECT id, registration_number, roll_number, full_name, gender, mother_name, status
            FROM students
            WHERE id = :student_id AND institution_id = :institution_id
        """),
        {"student_id": student_id, "institution_id": institution_id},
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    if "STUDENT" in claims.get("roles", []) and str(row["id"]) != str(claims["sub"]):
        # Student self-service mapping is intentionally not enabled yet.
        raise HTTPException(status_code=403, detail="Student self-service is not configured yet.")
    return dict(row)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_student(
    payload: StudentCreate,
    claims: dict = Depends(require_roles("SUPER_ADMIN", "COE", "TC")),
    db: Session = Depends(get_db),
):
    institution_id = institution_id_from_claims(claims)
    try:
        row = db.execute(
            text("""
                INSERT INTO students
                    (institution_id, registration_number, roll_number, full_name, gender, mother_name, status)
                VALUES
                    (:institution_id, :registration_number, :roll_number, :full_name, :gender, :mother_name, :status)
                RETURNING id, registration_number, roll_number, full_name, gender, mother_name, status
            """),
            {"institution_id": institution_id, **payload.model_dump()},
        ).mappings().one()
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Registration number already exists or student data is invalid.") from exc
    return dict(row)


@router.post("/import-csv", status_code=status.HTTP_201_CREATED)
async def import_students_csv(
    file: UploadFile = File(...),
    claims: dict = Depends(require_roles("SUPER_ADMIN", "COE", "TC")),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=415, detail="Please upload a CSV file.")

    raw = await file.read()
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="CSV file is too large. Maximum size is 5 MB.")

    try:
        text_data = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded.") from exc

    reader = csv.DictReader(io.StringIO(text_data))
    required = {"registration_number", "full_name"}
    headers = set(reader.fieldnames or [])
    missing = sorted(required - headers)
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required columns: {', '.join(missing)}")

    institution_id = institution_id_from_claims(claims)
    created = 0
    updated = 0
    errors: list[dict] = []

    try:
        for row_number, raw_row in enumerate(reader, start=2):
            row = {str(k).strip(): (v or "").strip() for k, v in raw_row.items() if k}
            registration_number = row.get("registration_number", "")
            full_name = row.get("full_name", "")
            if not registration_number or not full_name:
                errors.append({"row": row_number, "message": "registration_number and full_name are required."})
                continue

            existing = db.execute(
                text("""
                    SELECT id FROM students
                    WHERE institution_id = :institution_id
                      AND registration_number = :registration_number
                """),
                {"institution_id": institution_id, "registration_number": registration_number},
            ).scalar_one_or_none()

            values = {
                "institution_id": institution_id,
                "registration_number": registration_number,
                "roll_number": row.get("roll_number") or None,
                "full_name": full_name,
                "gender": row.get("gender") or None,
                "mother_name": row.get("mother_name") or None,
                "status": row.get("status") or "ACTIVE",
            }

            if existing:
                db.execute(
                    text("""
                        UPDATE students
                        SET roll_number = :roll_number,
                            full_name = :full_name,
                            gender = :gender,
                            mother_name = :mother_name,
                            status = :status
                        WHERE id = :id AND institution_id = :institution_id
                    """),
                    {**values, "id": existing},
                )
                updated += 1
            else:
                db.execute(
                    text("""
                        INSERT INTO students
                            (institution_id, registration_number, roll_number, full_name, gender, mother_name, status)
                        VALUES
                            (:institution_id, :registration_number, :roll_number, :full_name, :gender, :mother_name, :status)
                    """),
                    values,
                )
                created += 1

        if errors:
            db.rollback()
            return {
                "created": 0,
                "updated": 0,
                "errors": errors,
                "message": "No rows were saved because the file contains validation errors.",
            }

        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="Import failed. No changes were saved.") from exc

    return {
        "created": created,
        "updated": updated,
        "errors": [],
        "message": "Student import completed.",
    }


@router.post("/{student_id}/enrolments", status_code=status.HTTP_201_CREATED)
def create_enrolment(
    student_id: UUID,
    payload: EnrollmentCreate,
    claims: dict = Depends(require_roles("SUPER_ADMIN", "COE")),
    db: Session = Depends(get_db),
):
    institution_id = institution_id_from_claims(claims)

    owns_student = db.execute(
        text("SELECT 1 FROM students WHERE id = :student_id AND institution_id = :institution_id"),
        {"student_id": student_id, "institution_id": institution_id},
    ).first()
    if owns_student is None:
        raise HTTPException(status_code=404, detail="Student not found.")

    owns_programme = db.execute(
        text("SELECT 1 FROM programmes WHERE id = :programme_id AND institution_id = :institution_id"),
        {"programme_id": payload.programme_id, "institution_id": institution_id},
    ).first()
    if owns_programme is None:
        raise HTTPException(status_code=404, detail="Programme not found.")

    try:
        row = db.execute(
            text("""
                INSERT INTO student_programme_enrolments
                    (student_id, programme_id, admission_year, category, entry_type)
                VALUES
                    (:student_id, :programme_id, :admission_year, :category, :entry_type)
                RETURNING id, student_id, programme_id, admission_year, category, entry_type
            """),
            {"student_id": student_id, **payload.model_dump()},
        ).mappings().one()
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="This student is already enrolled in the programme for that admission year.") from exc
    return dict(row)


@router.get("/{student_id}/enrolments")
def list_enrolments(
    student_id: UUID,
    claims: dict = Depends(require_roles(
        "SUPER_ADMIN", "COE", "TC", "SCRUTINIZER", "DATA_ENTRY", "FACULTY"
    )),
    db: Session = Depends(get_db),
):
    institution_id = institution_id_from_claims(claims)
    rows = db.execute(
        text("""
            SELECT spe.id, spe.student_id, spe.programme_id, p.code AS programme_code,
                   p.name AS programme_name, spe.admission_year, spe.category, spe.entry_type
            FROM student_programme_enrolments spe
            JOIN students s ON s.id = spe.student_id
            JOIN programmes p ON p.id = spe.programme_id
            WHERE spe.student_id = :student_id AND s.institution_id = :institution_id
            ORDER BY spe.admission_year DESC
        """),
        {"student_id": student_id, "institution_id": institution_id},
    ).mappings().all()
    return [dict(row) for row in rows]
