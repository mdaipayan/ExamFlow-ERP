from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from .auth_dependencies import get_current_claims
from .auth_schemas import LoginRequest, LoginResponse, UserSummary
from .db import get_db
from .security import create_access_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    row = db.execute(
        text(
            """
            SELECT u.id, u.email, u.full_name, u.institution_id, u.password_hash,
                   COALESCE(array_agg(r.code) FILTER (WHERE r.code IS NOT NULL), ARRAY[]::text[]) AS roles
            FROM users u
            LEFT JOIN user_roles ur ON ur.user_id = u.id
            LEFT JOIN roles r ON r.id = ur.role_id
            WHERE lower(u.email) = lower(:email) AND u.is_active = true
            GROUP BY u.id
            """
        ),
        {"email": str(payload.email)},
    ).mappings().first()

    if row is None or not row["password_hash"] or not verify_password(
        payload.password, row["password_hash"]
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    roles = list(row["roles"] or [])
    user = UserSummary(
        id=str(row["id"]),
        email=row["email"],
        full_name=row["full_name"],
        institution_id=str(row["institution_id"]) if row["institution_id"] else None,
        roles=roles,
    )
    return LoginResponse(
        access_token=create_access_token(
            str(row["id"]),
            str(row["institution_id"]) if row["institution_id"] else None,
            roles,
        ),
        user=user,
    )


@router.get("/me")
def me(claims: dict = Depends(get_current_claims)) -> dict:
    return claims
