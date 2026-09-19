from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from .auth_dependencies import require_roles
from .db import get_db

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

DASHBOARD_ROLES = (
    "SUPER_ADMIN",
    "COE",
    "TC",
    "SCRUTINIZER",
    "DATA_ENTRY",
)


def institution_id_from_claims(claims: dict) -> UUID:
    value = claims.get("institution_id")
    if not value:
        raise HTTPException(
            status_code=400,
            detail="Your account is not linked to an institution.",
        )
    return UUID(str(value))


@router.get("")
def get_dashboard(
    claims: dict = Depends(require_roles(*DASHBOARD_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    institution_id = institution_id_from_claims(claims)

    institution = db.execute(
        text(
            """
            SELECT id, name, code, timezone
            FROM institutions
            WHERE id = :institution_id
            """
        ),
        {"institution_id": institution_id},
    ).mappings().first()

    if institution is None:
        raise HTTPException(status_code=404, detail="Institution not found.")

    current = db.execute(
        text(
            """
            SELECT
                e.id,
                e.name,
                e.term_label,
                e.status,
                e.programme_id,
                p.code AS programme_code,
                p.name AS programme_name,
                e.semester_id,
                s.number AS semester_number
            FROM examinations e
            JOIN programmes p ON p.id = e.programme_id
            JOIN semesters s ON s.id = e.semester_id
            WHERE e.institution_id = :institution_id
              AND e.status <> 'PUBLISHED'
            ORDER BY
                CASE e.status
                    WHEN 'IN_PROGRESS' THEN 1
                    WHEN 'TRIAL' THEN 2
                    WHEN 'UNDER_REVIEW' THEN 3
                    WHEN 'APPROVED' THEN 4
                    WHEN 'DRAFT' THEN 5
                    WHEN 'LOCKED' THEN 6
                    ELSE 7
                END,
                e.created_at DESC
            LIMIT 1
            """
        ),
        {"institution_id": institution_id},
    ).mappings().first()

    if current is None:
        return {
            "institution": dict(institution),
            "current_examination": None,
            "metrics": {
                "active_examinations": 0,
                "registered_students": 0,
                "marks_recorded": 0,
                "validation_errors": 0,
                "validation_warnings": 0,
                "pending_result_review": 0,
                "pending_result_approval": 0,
            },
            "workflow": {
                "stage": "SETUP",
                "label": "Create examination",
                "action": "CREATE_EXAMINATION",
            },
        }

    exam_id = current["id"]

    active_examinations = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM examinations
            WHERE institution_id = :institution_id
              AND status IN ('DRAFT','IN_PROGRESS','TRIAL','UNDER_REVIEW','APPROVED')
            """
        ),
        {"institution_id": institution_id},
    ).scalar_one()

    metrics = db.execute(
        text(
            """
            SELECT
                COUNT(DISTINCT er.student_id) AS registered_students,
                COUNT(DISTINCT me.id) AS marks_recorded,
                COUNT(DISTINCT mvi.id) FILTER (
                    WHERE mvi.severity = 'ERROR' AND mvi.resolved_at IS NULL
                ) AS validation_errors,
                COUNT(DISTINCT mvi.id) FILTER (
                    WHERE mvi.severity = 'WARNING' AND mvi.resolved_at IS NULL
                ) AS validation_warnings
            FROM examinations e
            LEFT JOIN examination_registrations er
              ON er.examination_id = e.id
            LEFT JOIN mark_entries me
              ON me.examination_id = e.id
            LEFT JOIN mark_validation_issues mvi
              ON mvi.examination_id = e.id
            WHERE e.id = :examination_id
            """
        ),
        {"examination_id": exam_id},
    ).mappings().one()

    pending_review = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM examinations
            WHERE institution_id = :institution_id
              AND status = 'UNDER_REVIEW'
            """
        ),
        {"institution_id": institution_id},
    ).scalar_one()

    pending_approval = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM result_versions rv
            JOIN examinations e ON e.id = rv.examination_id
            WHERE e.institution_id = :institution_id
              AND rv.status = 'TRIAL'
              AND rv.version_number = (
                  SELECT MAX(rv2.version_number)
                  FROM result_versions rv2
                  WHERE rv2.examination_id = rv.examination_id
              )
            """
        ),
        {"institution_id": institution_id},
    ).scalar_one()

    workflow_by_status = {
        "DRAFT": {
            "stage": "EXAMINATION_SETUP",
            "label": "Continue examination setup",
            "action": "OPEN_EXAMINATION",
        },
        "IN_PROGRESS": {
            "stage": "MARKS",
            "label": "Enter or import marks",
            "action": "OPEN_MARKS",
        },
        "TRIAL": {
            "stage": "RESULT_REVIEW",
            "label": "Review trial result",
            "action": "OPEN_RESULTS",
        },
        "UNDER_REVIEW": {
            "stage": "SCRUTINY",
            "label": "Complete result scrutiny",
            "action": "OPEN_SCRUTINY",
        },
        "APPROVED": {
            "stage": "FINALIZATION",
            "label": "Finalize and lock result",
            "action": "OPEN_RESULTS",
        },
        "LOCKED": {
            "stage": "PUBLICATION",
            "label": "Prepare publication",
            "action": "OPEN_REPORTS",
        },
    }

    return {
        "institution": dict(institution),
        "current_examination": {
            "id": str(current["id"]),
            "name": current["name"],
            "term_label": current["term_label"],
            "status": current["status"],
            "programme_id": str(current["programme_id"]),
            "programme_code": current["programme_code"],
            "programme_name": current["programme_name"],
            "semester_id": str(current["semester_id"]),
            "semester_number": current["semester_number"],
        },
        "metrics": {
            "active_examinations": int(active_examinations or 0),
            "registered_students": int(metrics["registered_students"] or 0),
            "marks_recorded": int(metrics["marks_recorded"] or 0),
            "validation_errors": int(metrics["validation_errors"] or 0),
            "validation_warnings": int(metrics["validation_warnings"] or 0),
            "pending_result_review": int(pending_review or 0),
            "pending_result_approval": int(pending_approval or 0),
        },
        "workflow": workflow_by_status.get(
            str(current["status"]),
            {
                "stage": str(current["status"]),
                "label": "Open examination",
                "action": "OPEN_EXAMINATION",
            },
        ),
    }
