from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from tradedigital.core.database import get_session
from tradedigital.platform.audit.repository import list_audit_logs
from tradedigital.platform.iam.deps import require_permission
from tradedigital.shared.auth_context import AuthContext
from tradedigital.shared.types import ok

router = APIRouter()


@router.get("/logs")
async def logs(
    ctx: AuthContext = Depends(require_permission("audit.log.read")),
    session: AsyncSession = Depends(get_session),
):
    rows = await list_audit_logs(session, ctx.enterprise_id)
    return ok(
        [
            {
                "id": row.id,
                "enterprise_id": row.enterprise_id,
                "user_id": row.user_id,
                "module": row.module,
                "action": row.action,
                "resource_type": row.resource_type,
                "resource_id": row.resource_id,
                "detail_json": row.detail_json,
                "ip_address": row.ip_address,
                "user_agent": row.user_agent,
                "created_at": row.created_at,
            }
            for row in rows
        ]
    )
