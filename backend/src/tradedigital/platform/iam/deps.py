from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from tradedigital.core.config import get_settings
from tradedigital.core.database import get_session
from tradedigital.platform.audit.service import write_audit_log
from tradedigital.platform.iam.service import build_auth_context
from tradedigital.shared.auth_context import AuthContext


async def get_current_context(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> AuthContext:
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        return await build_auth_context(session, token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


def require_permission(permission_code: str) -> Callable:
    async def dependency(
        request: Request,
        ctx: AuthContext = Depends(get_current_context),
        session: AsyncSession = Depends(get_session),
    ) -> AuthContext:
        if permission_code not in ctx.permissions:
            await write_audit_log(
                session,
                enterprise_id=ctx.enterprise_id,
                user_id=ctx.user_id,
                module="iam",
                action="permission.denied",
                resource_type="permission",
                resource_id=permission_code,
                detail_json={"path": str(request.url.path)},
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
            await session.commit()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
        return ctx

    return dependency

