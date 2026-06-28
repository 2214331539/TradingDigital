from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tradedigital.platform.org.models import Enterprise


async def get_enterprise(session: AsyncSession, enterprise_id: str) -> Enterprise | None:
    return await session.get(Enterprise, enterprise_id)


async def get_enterprise_by_code(session: AsyncSession, code: str) -> Enterprise | None:
    return await session.scalar(select(Enterprise).where(Enterprise.code == code))
