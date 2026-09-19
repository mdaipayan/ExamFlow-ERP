from fastapi import APIRouter, Header, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from .db import get_db
from .security import hash_password
from .settings import settings
from .setup_schemas import InitialSetupRequest

router = APIRouter(prefix="/api/setup", tags=["setup"])


@router.get("/status")
def setup_status(db: Session = __import__("fastapi").Depends(get_db)):
    count = db.execute(text("SELECT count(*) FROM users")).scalar_one()
    return {"initialized": count > 0}


@router.post("/initialize", status_code=status.HTTP_201_CREATED)
def initialize(
    payload: InitialSetupRequest,
    x_bootstrap_key: str | None = Header(default=None),
    db: Session = __import__("fastapi").Depends(get_db),
):
    if not settings.bootstrap_key:
        raise HTTPException(status_code=503, detail="Initial setup is disabled until BOOTSTRAP_KEY is configured.")
    if x_bootstrap_key != settings.bootstrap_key:
        raise HTTPException(status_code=403, detail="Invalid bootstrap key.")

    count = db.execute(text("SELECT count(*) FROM users")).scalar_one()
    if count:
        raise HTTPException(status_code=409, detail="ExamFlow is already initialized.")

    try:
        institution = db.execute(
            text("""
                INSERT INTO institutions (name, code)
                VALUES (:name, :code)
                RETURNING id
            """),
            {"name": payload.institution_name, "code": payload.institution_code},
        ).scalar_one()

        user = db.execute(
            text("""
                INSERT INTO users (institution_id, email, full_name, password_hash)
                VALUES (:institution_id, :email, :full_name, :password_hash)
                RETURNING id
            """),
            {
                "institution_id": institution,
                "email": str(payload.admin_email),
                "full_name": payload.admin_name,
                "password_hash": hash_password(payload.admin_password),
            },
        ).scalar_one()

        role_rows = db.execute(
            text("SELECT id, code FROM roles WHERE code IN ('SUPER_ADMIN', 'COE')")
        ).mappings().all()
        role_map = {row["code"]: row["id"] for row in role_rows}
        if set(role_map) != {"SUPER_ADMIN", "COE"}:
            raise RuntimeError("Required role seed is missing. Run migrations/002_seed_roles.sql first.")

        for code in ("SUPER_ADMIN", "COE"):
            db.execute(
                text("INSERT INTO user_roles (user_id, role_id) VALUES (:user_id, :role_id)"),
                {"user_id": user, "role_id": role_map[code]},
            )

        db.commit()
        return {
            "institution_id": str(institution),
            "admin_user_id": str(user),
            "message": "ExamFlow has been initialized. Create separate operational users next.",
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Initial setup failed. Check institution code/email uniqueness and database state.") from exc
