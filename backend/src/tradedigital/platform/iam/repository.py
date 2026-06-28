from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from tradedigital.platform.iam.models import Permission, Role, SSOConnection, Session, User


async def get_sso_connection(
    session: AsyncSession, enterprise_id: str, provider: str
) -> SSOConnection | None:
    return await session.scalar(
        select(SSOConnection).where(
            SSOConnection.enterprise_id == enterprise_id,
            SSOConnection.provider == provider,
            SSOConnection.enabled.is_(True),
        )
    )


async def get_user_with_roles(session: AsyncSession, user_id: str) -> User | None:
    return await session.scalar(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(User.id == user_id)
    )


async def get_user_by_email(session: AsyncSession, enterprise_id: str, email: str) -> User | None:
    return await session.scalar(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(User.enterprise_id == enterprise_id, User.email == email.lower())
    )


async def get_user_by_sso_subject(
    session: AsyncSession, enterprise_id: str, provider: str, subject: str
) -> User | None:
    return await session.scalar(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(
            User.enterprise_id == enterprise_id,
            User.sso_provider == provider,
            User.sso_subject == subject,
        )
    )


async def get_session_by_hash(session: AsyncSession, token_hash: str) -> Session | None:
    return await session.scalar(select(Session).where(Session.session_token_hash == token_hash))


async def get_role_by_code(session: AsyncSession, enterprise_id: str, code: str) -> Role | None:
    return await session.scalar(
        select(Role)
        .options(selectinload(Role.permissions))
        .where(Role.enterprise_id == enterprise_id, Role.code == code)
    )


async def list_roles(session: AsyncSession, enterprise_id: str) -> list[Role]:
    rows = await session.scalars(
        select(Role)
        .options(selectinload(Role.permissions))
        .where(Role.enterprise_id == enterprise_id)
        .order_by(Role.created_at)
    )
    return rows.all()


async def list_permissions(session: AsyncSession) -> list[Permission]:
    rows = await session.scalars(select(Permission).order_by(Permission.module, Permission.code))
    return rows.all()
