from datetime import timedelta
from datetime import timezone
from typing import Optional

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from tradedigital.core.config import get_settings
from tradedigital.core.security import generate_token, hash_token
from tradedigital.core.time import utc_now
from tradedigital.platform.audit.service import write_audit_log
from tradedigital.platform.iam.models import Permission, Role, Session, User
from tradedigital.platform.iam.repository import (
    get_role_by_code,
    get_session_by_hash,
    get_user_by_email,
    get_user_by_sso_subject,
    get_user_with_roles,
)
from tradedigital.shared.auth_context import AuthContext


def role_codes(user: User) -> list[str]:
    return [role.code for role in user.roles]


def role_ids(user: User) -> list[str]:
    return [role.id for role in user.roles]


def permission_codes(user: User) -> list[str]:
    codes: set[str] = set()
    for role in user.roles:
        for permission in role.permissions:
            codes.add(permission.code)
    return sorted(codes)


def user_out(user: User) -> dict:
    return {
        "id": user.id,
        "enterprise_id": user.enterprise_id,
        "email": user.email,
        "name": user.name,
        "avatar_url": user.avatar_url,
        "status": user.status,
        "roles": role_codes(user),
        "permissions": permission_codes(user),
        "last_login_at": user.last_login_at,
        "created_at": user.created_at,
    }


def role_out(role: Role) -> dict:
    return {
        "id": role.id,
        "code": role.code,
        "name": role.name,
        "description": role.description,
        "is_system": role.is_system,
        "permissions": [permission.code for permission in role.permissions],
    }


def permission_out(permission: Permission) -> dict:
    return {
        "id": permission.id,
        "code": permission.code,
        "name": permission.name,
        "module": permission.module,
        "resource": permission.resource,
        "action": permission.action,
        "description": permission.description,
    }


async def build_auth_context(session: AsyncSession, session_token: str) -> AuthContext:
    record = await get_session_by_hash(session, hash_token(session_token))
    now = utc_now()
    expires_at = record.expires_at if record else None
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if not record or record.revoked_at or not expires_at or expires_at <= now:
        raise ValueError("Session unavailable")
    user = await get_user_with_roles(session, record.user_id)
    if not user or user.status != "active":
        raise ValueError("User unavailable")
    return AuthContext(
        user_id=user.id,
        enterprise_id=user.enterprise_id,
        email=user.email,
        name=user.name,
        roles=role_codes(user),
        role_ids=role_ids(user),
        permissions=permission_codes(user),
    )


async def create_session(
    session: AsyncSession,
    user: User,
    *,
    user_agent: Optional[str],
    ip_address: Optional[str],
) -> str:
    settings = get_settings()
    token = generate_token()
    record = Session(
        enterprise_id=user.enterprise_id,
        user_id=user.id,
        session_token_hash=hash_token(token),
        user_agent=user_agent,
        ip_address=ip_address,
        expires_at=utc_now() + timedelta(hours=settings.session_expire_hours),
    )
    session.add(record)
    return token


async def revoke_session(session: AsyncSession, session_token: str) -> None:
    record = await get_session_by_hash(session, hash_token(session_token))
    if record and not record.revoked_at:
        record.revoked_at = utc_now()


async def upsert_oidc_user(
    session: AsyncSession,
    *,
    enterprise_id: str,
    provider: str,
    subject: str,
    email: str,
    name: Optional[str],
    avatar_url: Optional[str] = None,
) -> User:
    normalized_email = email.lower()
    user = await get_user_by_sso_subject(session, enterprise_id, provider, subject)
    if not user:
        user = await get_user_by_email(session, enterprise_id, normalized_email)
    if user:
        user.sso_provider = provider
        user.sso_subject = subject
        user.email = normalized_email
        user.name = name
        user.avatar_url = avatar_url
        user.last_login_at = utc_now()
    else:
        employee = await get_role_by_code(session, enterprise_id, "employee")
        user = User(
            enterprise_id=enterprise_id,
            sso_provider=provider,
            sso_subject=subject,
            email=normalized_email,
            name=name,
            avatar_url=avatar_url,
            status="active",
            last_login_at=utc_now(),
            roles=[employee] if employee else [],
        )
        session.add(user)
    return user


def users_query(enterprise_id: str, keyword: str = "") -> Select[tuple[User]]:
    query = (
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(User.enterprise_id == enterprise_id)
    )
    if keyword:
        like = f"%{keyword}%"
        query = query.where(or_(User.email.ilike(like), User.name.ilike(like)))
    return query


def ordered_unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


async def list_users(
    session: AsyncSession, enterprise_id: str, *, page: int, page_size: int, keyword: str = ""
) -> tuple[list[User], int]:
    query = users_query(enterprise_id, keyword)
    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    rows = await session.scalars(
        query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    return rows.all(), int(total or 0)


async def update_user_status(
    session: AsyncSession, ctx: AuthContext, user_id: str, status: str
) -> User:
    user = await get_user_with_roles(session, user_id)
    if not user or user.enterprise_id != ctx.enterprise_id:
        raise ValueError("User not found")
    user.status = status
    await write_audit_log(
        session,
        enterprise_id=ctx.enterprise_id,
        user_id=ctx.user_id,
        module="iam",
        action="iam.user.status.update",
        resource_type="iam_user",
        resource_id=user.id,
        detail_json={"status": status},
    )
    return user


async def assign_roles_to_user(
    session: AsyncSession, ctx: AuthContext, user_id: str, role_ids: list[str]
) -> User:
    user = await get_user_with_roles(session, user_id)
    if not user or user.enterprise_id != ctx.enterprise_id:
        raise ValueError("User not found")
    requested_role_ids = ordered_unique(role_ids)
    roles = []
    if requested_role_ids:
        roles = (
            await session.scalars(
                select(Role)
                .options(selectinload(Role.permissions))
                .where(Role.enterprise_id == ctx.enterprise_id, Role.id.in_(requested_role_ids))
            )
        ).all()
    found_role_ids = {role.id for role in roles}
    missing_role_ids = [
        role_id for role_id in requested_role_ids if role_id not in found_role_ids
    ]
    if missing_role_ids:
        raise ValueError(f"Role not found: {', '.join(missing_role_ids)}")
    user.roles = roles
    await write_audit_log(
        session,
        enterprise_id=ctx.enterprise_id,
        user_id=ctx.user_id,
        module="iam",
        action="iam.user.roles.update",
        resource_type="iam_user",
        resource_id=user.id,
        detail_json={"role_ids": requested_role_ids},
    )
    return user


async def update_role_permissions(
    session: AsyncSession, ctx: AuthContext, role_id: str, permission_ids: list[str]
) -> Role:
    role = await session.scalar(
        select(Role)
        .options(selectinload(Role.permissions))
        .where(Role.enterprise_id == ctx.enterprise_id, Role.id == role_id)
    )
    if not role:
        raise ValueError("Role not found")
    requested_permission_ids = ordered_unique(permission_ids)
    permissions = []
    if requested_permission_ids:
        permissions = (
            await session.scalars(
                select(Permission).where(Permission.id.in_(requested_permission_ids))
            )
        ).all()
    found_permission_ids = {permission.id for permission in permissions}
    missing_permission_ids = [
        permission_id
        for permission_id in requested_permission_ids
        if permission_id not in found_permission_ids
    ]
    if missing_permission_ids:
        raise ValueError(f"Permission not found: {', '.join(missing_permission_ids)}")
    role.permissions = permissions
    await write_audit_log(
        session,
        enterprise_id=ctx.enterprise_id,
        user_id=ctx.user_id,
        module="iam",
        action="iam.role.permissions.update",
        resource_type="iam_role",
        resource_id=role.id,
        detail_json={"permission_ids": requested_permission_ids},
    )
    return role
