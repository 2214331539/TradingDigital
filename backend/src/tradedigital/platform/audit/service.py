from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from tradedigital.platform.audit.models import AuditOperationLog
from tradedigital.shared.auth_context import AuthContext


async def write_audit_log(
    session: AsyncSession,
    *,
    enterprise_id: str,
    user_id: Optional[str],
    module: str,
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    detail_json: Optional[dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AuditOperationLog:
    log = AuditOperationLog(
        enterprise_id=enterprise_id,
        user_id=user_id,
        module=module,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail_json=detail_json,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    session.add(log)
    return log


async def write_context_audit_log(
    session: AsyncSession,
    ctx: AuthContext,
    *,
    module: str,
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    detail_json: Optional[dict[str, Any]] = None,
) -> AuditOperationLog:
    return await write_audit_log(
        session,
        enterprise_id=ctx.enterprise_id,
        user_id=ctx.user_id,
        module=module,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail_json=detail_json,
    )

