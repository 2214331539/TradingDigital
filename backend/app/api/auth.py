from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import get_current_user
from app.core.security import create_access_token, verify_password
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import LoginRequest
from app.schemas.common import ok
from app.services.serializers import user_summary

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="邮箱或密码错误")
    if user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号不可用")

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    token = create_access_token(user.id)
    settings = get_settings()
    return ok(
        {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
            "user": user_summary(user),
        }
    )


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return ok(user_summary(current_user))


@router.post("/logout")
def logout():
    return ok({"success": True})

