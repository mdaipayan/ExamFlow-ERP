import hashlib
import json
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from .auth_dependencies import require_roles
from .db import get_db
from .result_engine import AcademicConfigurationError, calculate_course_results, calculate_course_total, calculate_sgpa

router = APIRouter(prefix="/api/examinations", tags=["results"])


def institution_id_from_claims(claims: dict) -> UUID:
    value = claims.get("institution_id")
    if not value:
        raise HTTPException(status_code=400, detail="Your account is not linked to an institution.")
    return UUID(str(value))


def canonical_hash(parameters: dict) -> str:
    canonical = json.dumps(
        parameters, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def get_exam(db: Session, examination_id: UUID, institution_id: UUID):
    exam = db.execute(
        text("""
            SELECT e.id, e.status, e.semester_id, e.programme_id,
                   s.name AS semester_name,
                   eps.parameters, eps.content_hash, eps.version_label
            FROM examinations e
            JOIN semesters s ON s.id = e.semester_id
            JOIN examination_parameter_snapshots eps ON eps.examination_id = e.id
            WHERE e.id = :examination_id AND e.institution_id = :institution_id
        """),
        {"examination_id": examination_id, "institution_id": institution_id},
    ).mappings().first()

    if exam is None:
        raise HTTPException(
            status_code=409,
            detail="Examination is not activated or its rule snapshot is missing.",
        )

    expected = canonical_hash(exam["parameters"] or {})
    if expected != exam["content_hash"]:
        raise HTTPException(status_code=409, detail="Examination rule snapshot integrity check failed.")
    return exam


def get_next_result_version(db: Session, examination_id: UUID) -> int:
    value = db.execute(
        text("SELECT COALESCE(MAX(version_number), 0) + 1 FROM result_versions WHERE examination_id = :id"),
        {"id": examination_id},
    ).scalar_one()
    return int(value)


@router.post("/{examination_id}/results/calculate")
def calculate_trial_result(
    examination_id: UUID,
    claims: dict = Depends(require_roles("SUPER_ADMIN", "COE", "TC")),
    db: Session = Depends(get_db),
):
    institution_id = institution_id_from_claims(claims)
    exam = get_exam(db, examination_id, institution_id)

    if exam["status"] not in {"IN_PROGRESS", "TRIAL", "UNDER_REVIEW"}:
        raise HTTPException(status_code=409, detail="The examination is not available for trial calculation.")

    error_count = db.execute(
        text("""
            SELECT count(*)
            FROM mark_validation_issues
            WHERE examination_id = :examination_id
              AND severity = 'ERROR'
              AND resolved_at IS NULL
        """),
        {"examination_id": examination_id},
    ).scalar_one()

    if int(error_count) > 0:
        raise HTTPException(
            status_code=409,
            detail=f"{error_count} unresolved mark validation errors must be fixed before calculation.",
        )

    config = exam["parameters"] or {}
    pass_grades = config.get("result", {}).get("pass_grades")
    non_counting_grades = config.get("sgpa", {}).get("non_counting_grades")
    if not isinstance(pass_grades, list) or not pass_grades:
        raise HTTPException(status_code=422, detail="Required academic parameter is missing: result.pass_grades")
    if not isinstance(non_counting_grades, list):
        raise HTTPException(status_code=422, detail="Required academic parameter is missing: sgpa.non_counting_grades")

    courses = db.execute(
        text("""
            SELECT c.id, c.code, c.name, c.credits, c.is_audit
            FROM examination_courses ec
            JOIN courses c ON c.id = ec.course_id
            WHERE ec.examination_id = :examination_id
            ORDER BY c.code
        """),
        {"examination_id": examination_id},
    ).mappings().all()

    if not courses:
        raise HTTPException(status_code=409, detail="No courses are attached to the examination.")

    course_results = []
    course_cutoffs = []

    try:
        for course in courses:
            components = db.execute(
                text("""
                    SELECT code, max_marks, weightage, minimum_marks
                    FROM course_components
                    WHERE course_id = :course_id
                    ORDER BY sort_order, code
                """),
                {"course_id": course["id"]},
            ).mappings().all()

            registrations = db.execute(
                text("""
                    SELECT er.student_id, s.registration_number, s.full_name,
                           coalesce(spe.entry_type, 'REGULAR') AS entry_type
                    FROM examination_registrations er
                    JOIN students s ON s.id = er.student_id
                    LEFT JOIN student_programme_enrolments spe
                      ON spe.student_id = s.id
                     AND spe.programme_id = :programme_id
                    WHERE er.examination_id = :examination_id
                      AND er.course_id = :course_id
                    ORDER BY s.registration_number
                """),
                {
                    "examination_id": examination_id,
                    "course_id": course["id"],
                    "programme_id": exam["programme_id"],
                },
            ).mappings().all()

            cohort = []
            for registration in registrations:
                marks_rows = db.execute(
                    text("""
                        SELECT component_code, marks
                        FROM mark_entries
                        WHERE examination_id = :examination_id
                          AND student_id = :student_id
                          AND course_id = :course_id
                    """),
                    {
                        "examination_id": examination_id,
                        "student_id": registration["student_id"],
                        "course_id": course["id"],
                    },
                ).mappings().all()

                marks_by_code = {
                    str(row["component_code"]): Decimal(str(row["marks"]))
                    for row in marks_rows
                    if row["marks"] is not None
                }
                total = calculate_course_total(components, marks_by_code)

                eligibility = db.execute(
                    text("""
                        SELECT eligible_for_ese, grade_override, reason
                        FROM eligibility_records
                        WHERE examination_id = :examination_id
                          AND student_id = :student_id
                          AND course_id = :course_id
                    """),
                    {
                        "examination_id": examination_id,
                        "student_id": registration["student_id"],
                        "course_id": course["id"],
                    },
                ).mappings().first()

                grade_override = eligibility["grade_override"] if eligibility else None

                component_failure = None
                for component in components:
                    minimum = component["minimum_marks"]
                    if minimum is not None:
                        actual = marks_by_code.get(str(component["code"]))
                        if actual is not None and actual < Decimal(str(minimum)):
                            component_failure = True
                            break

                cohort.append({
                    "student_id": registration["student_id"],
                    "registration_number": registration["registration_number"],
                    "full_name": registration["full_name"],
                    "entry_type": registration["entry_type"],
                    "total_marks": total,
                    "credits": Decimal(str(course["credits"])),
                    "grade_override": grade_override,
                    "component_failure": component_failure,
                    "eligibility_reason": eligibility["reason"] if eligibility else None,
                })

            # Apply explicit component minimum failure without inventing a grade.
            component_fail_grade = (config.get("component_minimum") or {}).get("fail_grade")
            if any(x["component_failure"] for x in cohort) and not component_fail_grade:
                raise AcademicConfigurationError(
                    "Component minimum failure exists but component_minimum.fail_grade is not configured."
                )

            for item in cohort:
                if item["component_failure"] and not item["grade_override"]:
                    item["grade_override"] = str(component_fail_grade)

            calculated = calculate_course_results(config, components, cohort)
            for item in calculated["results"]:
                item["course_id"] = course["id"]
                item["course_code"] = course["code"]
                item["course_name"] = course["name"]
                item["credits"] = Decimal(str(course["credits"]))
                course_results.append(item)

            course_cutoffs.append({
                "course_id": course["id"],
                "course_code": course["code"],
                "grading_method": str((config.get("grading") or {}).get("method", "")),
                "statistics": calculated["statistics"],
                "cutoffs": (calculated["statistics"] or {}).get("cutoffs")
                    if calculated["statistics"] else (config.get("grading") or {}).get("boundaries"),
            })

        # Group course results by student for SGPA.
        by_student: dict[UUID, list[dict]] = {}
        for item in course_results:
            by_student.setdefault(item["student_id"], []).append(item)

        sgpa_by_student = {
            student_id: calculate_sgpa(rows, config)
            for student_id, rows in by_student.items()
        }

        version_number = get_next_result_version(db, examination_id)
        result_version = db.execute(
            text("""
                INSERT INTO result_versions
                    (examination_id, version_number, status, reason, created_by)
                VALUES
                    (:examination_id, :version_number, 'TRIAL', 'Trial calculation', :created_by)
                RETURNING id, version_number, status
            """),
            {
                "examination_id": examination_id,
                "version_number": version_number,
                "created_by": UUID(str(claims["sub"])),
            },
        ).mappings().one()

        for item in course_results:
            explanation = {
                "grading_method": str((config.get("grading") or {}).get("method", "")),
                "statistics": item.get("statistics"),
                "eligibility_reason": item.get("eligibility_reason"),
            }
            db.execute(
                text("""
                    INSERT INTO result_courses
                        (result_version_id, student_id, course_id, total_marks, grade,
                         grade_point, credits, status, notation, explanation)
                    VALUES
                        (:result_version_id, :student_id, :course_id, :total_marks, :grade,
                         :grade_point, :credits, :status, :notation, CAST(:explanation AS jsonb))
                """),
                {
                    "result_version_id": result_version["id"],
                    "student_id": item["student_id"],
                    "course_id": item["course_id"],
                    "total_marks": item["total_marks"],
                    "grade": item["grade"],
                    "grade_point": item["grade_point"],
                    "credits": item["credits"],
                    "status": "PASS" if item["grade"] in set(pass_grades) else "FAIL",
                    "notation": None,
                    "explanation": json.dumps(explanation, default=str),
                },
            )

        for cutoff in course_cutoffs:
            db.execute(
                text("""
                    INSERT INTO grade_cutoffs
                        (result_version_id, course_id, grading_method, statistics, cutoffs)
                    VALUES
                        (:result_version_id, :course_id, :grading_method,
                         CAST(:statistics AS jsonb), CAST(:cutoffs AS jsonb))
                """),
                {
                    "result_version_id": result_version["id"],
                    "course_id": cutoff["course_id"],
                    "grading_method": cutoff["grading_method"],
                    "statistics": json.dumps(cutoff["statistics"], default=str),
                    "cutoffs": json.dumps(cutoff["cutoffs"], default=str),
                },
            )

        for student_id, sgpa in sgpa_by_student.items():
            all_rows = by_student[student_id]
            total_credits = sum(
                (Decimal(str(row["credits"])) for row in all_rows if row["grade"] in set(config.get("sgpa", {}).get("included_grades", []))),
                Decimal("0"),
            )
            failed = any(
                row["grade"] not in set(pass_grades)
                and row["grade"] not in set(non_counting_grades)
                for row in all_rows
            )
            db.execute(
                text("""
                    INSERT INTO semester_results
                        (result_version_id, student_id, semester_id, sgpa, result_status)
                    VALUES
                        (:result_version_id, :student_id, :semester_id, :sgpa, :result_status)
                """),
                {
                    "result_version_id": result_version["id"],
                    "student_id": student_id,
                    "semester_id": exam["semester_id"],
                    "sgpa": sgpa,
                    "result_status": "FAIL" if failed else "PASS",
                },
            )

        db.execute(
            text("""
                UPDATE examinations
                SET status = 'TRIAL'
                WHERE id = :examination_id AND institution_id = :institution_id
            """),
            {"examination_id": examination_id, "institution_id": institution_id},
        )
        db.commit()

    except AcademicConfigurationError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="Trial calculation failed. No result version was saved.") from exc

    return {
        "result_version_id": str(result_version["id"]),
        "version_number": result_version["version_number"],
        "status": result_version["status"],
        "students": len(sgpa_by_student),
        "courses": len(courses),
        "message": "Trial result calculated successfully.",
    }


@router.get("/{examination_id}/results/latest")
def latest_result(
    examination_id: UUID,
    claims: dict = Depends(require_roles("SUPER_ADMIN", "COE", "TC", "SCRUTINIZER")),
    db: Session = Depends(get_db),
):
    institution_id = institution_id_from_claims(claims)
    rows = db.execute(
        text("""
            SELECT rv.id AS result_version_id, rv.version_number, rv.status,
                   rc.student_id, s.registration_number, s.full_name,
                   rc.course_id, c.code AS course_code, rc.total_marks,
                   rc.grade, rc.grade_point, rc.credits, rc.status AS course_status
            FROM result_versions rv
            JOIN result_courses rc ON rc.result_version_id = rv.id
            JOIN students s ON s.id = rc.student_id
            JOIN courses c ON c.id = rc.course_id
            JOIN examinations e ON e.id = rv.examination_id
            WHERE rv.examination_id = :examination_id
              AND e.institution_id = :institution_id
              AND rv.version_number = (
                  SELECT max(version_number)
                  FROM result_versions
                  WHERE examination_id = :examination_id
              )
            ORDER BY s.registration_number, c.code
        """),
        {"examination_id": examination_id, "institution_id": institution_id},
    ).mappings().all()
    return [dict(row) for row in rows]
