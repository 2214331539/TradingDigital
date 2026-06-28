from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from tradedigital.platform.audit.models import AuditOperationLog


def audit_query(enterprise_id: str) -> Select[tuple[AuditOperationLog]]:
    return (
        select(AuditOperationLog)
        .where(AuditOperationLog.enterprise_id == enterprise_id)
        .order_by(AuditOperationLog.created_at.desc())
    )


async def list_audit_logs(session: AsyncSession, enterprise_id: str, limit: int = 100):
    rows = await session.scalars(audit_query(enterprise_id).limit(limit))
    return rows.all()

