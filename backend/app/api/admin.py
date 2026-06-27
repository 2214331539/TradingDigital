from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import require_permission
from app.core.security import hash_password
from app.db.models import AiModel, ModelCallLog, OperationLog, Permission, Role, User
from app.db.session import get_db
from app.schemas.admin import ModelCreate, ModelUpdate, UserCreate, UserUpdate
from app.schemas.common import ok
from app.services.audit import write_operation_log
from app.services.serializers import admin_user_out, model_out, role_out

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard")
def dashboard(
    current_user: User = Depends(require_permission("analytics:read")),
    db: Session = Depends(get_db),
):
    today = datetime.now(timezone.utc) - timedelta(days=1)
    total_users = db.query(User).filter(User.deleted_at.is_(None)).count()
    active_users_today = db.query(User).filter(User.last_login_at >= today).count()
    model_calls_today = db.query(ModelCallLog).filter(ModelCallLog.created_at >= today).count()
    failures_today = (
        db.query(ModelCallLog)
        .filter(ModelCallLog.created_at >= today, ModelCallLog.status == "failed")
        .count()
    )
    avg_latency = 0
    calls = db.query(ModelCallLog).filter(ModelCallLog.created_at >= today).all()
    latency_values = [call.latency_ms for call in calls if call.latency_ms]
    if latency_values:
        avg_latency = int(sum(latency_values) / len(latency_values))
    return ok(
        {
            "total_users": total_users,
            "active_users_today": active_users_today,
            "messages_today": model_calls_today * 2,
            "model_calls_today": model_calls_today,
            "avg_latency_ms": avg_latency,
            "failure_rate": round(failures_today / model_calls_today, 4) if model_calls_today else 0,
            "current_admin": current_user.username,
        }
    )


@router.get("/users")
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = "",
    current_user: User = Depends(require_permission("user:read")),
    db: Session = Depends(get_db),
):
    query = db.query(User).filter(User.deleted_at.is_(None))
    if keyword:
        query = query.filter((User.username.ilike(f"%{keyword}%")) | (User.email.ilike(f"%{keyword}%")))
    total = query.count()
    rows = query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return ok({"items": [admin_user_out(row) for row in rows], "page": page, "page_size": page_size, "total": total})


@router.post("/users")
def create_user(
    payload: UserCreate,
    current_user: User = Depends(require_permission("user:create")),
    db: Session = Depends(get_db),
):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="邮箱已存在")
    roles = db.query(Role).filter(Role.id.in_(payload.role_ids)).all()
    if any(role.code == "super_admin" for role in roles) and not any(
        role.code == "super_admin" for role in current_user.roles
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="不能创建超级管理员")
    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
        status=payload.status,
        roles=roles,
    )
    db.add(user)
    db.flush()
    write_operation_log(db, user_id=current_user.id, action="user:create", target_type="user", target_id=user.id)
    db.commit()
    db.refresh(user)
    return ok(admin_user_out(user))


@router.patch("/users/{user_id}")
def update_user(
    user_id: str,
    payload: UserUpdate,
    current_user: User = Depends(require_permission("user:update")),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    updates = payload.model_dump(exclude_unset=True)
    if "role_ids" in updates and updates["role_ids"] is not None:
        roles = db.query(Role).filter(Role.id.in_(updates.pop("role_ids"))).all()
        if any(role.code == "super_admin" for role in roles) and not any(
            role.code == "super_admin" for role in current_user.roles
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="不能分配超级管理员")
        user.roles = roles
    for key, value in updates.items():
        setattr(user, key, value)
    write_operation_log(db, user_id=current_user.id, action="user:update", target_type="user", target_id=user.id)
    db.commit()
    db.refresh(user)
    return ok(admin_user_out(user))


@router.post("/users/{user_id}/disable")
def disable_user(
    user_id: str,
    current_user: User = Depends(require_permission("user:disable")),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if any(role.code == "super_admin" for role in user.roles) and not any(
        role.code == "super_admin" for role in current_user.roles
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="不能禁用超级管理员")
    user.status = "disabled"
    write_operation_log(db, user_id=current_user.id, action="user:disable", target_type="user", target_id=user.id)
    db.commit()
    return ok({"success": True})


@router.post("/users/{user_id}/enable")
def enable_user(
    user_id: str,
    current_user: User = Depends(require_permission("user:disable")),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    user.status = "active"
    write_operation_log(db, user_id=current_user.id, action="user:enable", target_type="user", target_id=user.id)
    db.commit()
    return ok({"success": True})


@router.get("/roles")
def roles(current_user: User = Depends(require_permission("role:read")), db: Session = Depends(get_db)):
    return ok([role_out(role) for role in db.query(Role).order_by(Role.created_at).all()])


@router.get("/permissions")
def permissions(
    current_user: User = Depends(require_permission("permission:read")),
    db: Session = Depends(get_db),
):
    rows = db.query(Permission).order_by(Permission.module, Permission.code).all()
    return ok(
        [
            {
                "id": row.id,
                "module": row.module,
                "name": row.name,
                "code": row.code,
                "description": row.description,
            }
            for row in rows
        ]
    )


@router.get("/models")
def admin_models(
    current_user: User = Depends(require_permission("model:read")),
    db: Session = Depends(get_db),
):
    rows = db.query(AiModel).filter(AiModel.deleted_at.is_(None)).order_by(AiModel.sort_order).all()
    return ok([model_out(row) for row in rows])


@router.post("/models")
def create_model(
    payload: ModelCreate,
    current_user: User = Depends(require_permission("model:create")),
    db: Session = Depends(get_db),
):
    roles = db.query(Role).filter(Role.id.in_(payload.allowed_role_ids)).all() if payload.allowed_role_ids else []
    model = AiModel(
        name=payload.name,
        provider=payload.provider,
        model_key=payload.model_key,
        base_url=payload.base_url,
        api_key_ref=payload.api_key_ref,
        context_length=payload.context_length,
        max_output_tokens=payload.max_output_tokens,
        default_temperature=payload.default_temperature,
        support_streaming=payload.support_streaming,
        enabled=payload.enabled,
        roles=roles,
    )
    db.add(model)
    db.flush()
    write_operation_log(db, user_id=current_user.id, action="model:create", target_type="model", target_id=model.id)
    db.commit()
    db.refresh(model)
    return ok(model_out(model))


@router.patch("/models/{model_id}")
def update_model(
    model_id: str,
    payload: ModelUpdate,
    current_user: User = Depends(require_permission("model:update")),
    db: Session = Depends(get_db),
):
    model = db.get(AiModel, model_id)
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型不存在")
    updates = payload.model_dump(exclude_unset=True)
    if "allowed_role_ids" in updates:
        role_ids = updates.pop("allowed_role_ids") or []
        model.roles = db.query(Role).filter(Role.id.in_(role_ids)).all() if role_ids else []
    for key, value in updates.items():
        setattr(model, key, value)
    write_operation_log(db, user_id=current_user.id, action="model:update", target_type="model", target_id=model.id)
    db.commit()
    db.refresh(model)
    return ok(model_out(model))


@router.post("/models/{model_id}/disable")
def disable_model(
    model_id: str,
    current_user: User = Depends(require_permission("model:disable")),
    db: Session = Depends(get_db),
):
    model = db.get(AiModel, model_id)
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型不存在")
    model.enabled = False
    write_operation_log(db, user_id=current_user.id, action="model:disable", target_type="model", target_id=model.id)
    db.commit()
    return ok({"success": True})


@router.get("/logs/operations")
def operation_logs(
    current_user: User = Depends(require_permission("log:read")),
    db: Session = Depends(get_db),
):
    rows = db.query(OperationLog).order_by(OperationLog.created_at.desc()).limit(100).all()
    return ok(
        [
            {
                "id": row.id,
                "user_id": row.user_id,
                "action": row.action,
                "target_type": row.target_type,
                "target_id": row.target_id,
                "result": row.result,
                "created_at": row.created_at,
            }
            for row in rows
        ]
    )


@router.get("/logs/model-calls")
def model_call_logs(
    current_user: User = Depends(require_permission("log:read")),
    db: Session = Depends(get_db),
):
    rows = db.query(ModelCallLog).order_by(ModelCallLog.created_at.desc()).limit(100).all()
    return ok(
        [
            {
                "id": row.id,
                "user_id": row.user_id,
                "conversation_id": row.conversation_id,
                "model_id": row.model_id,
                "provider": row.provider,
                "total_tokens": row.total_tokens,
                "latency_ms": row.latency_ms,
                "status": row.status,
                "created_at": row.created_at,
            }
            for row in rows
        ]
    )

