from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import RedirectResponse

from tradedigital.core.config import get_settings
from tradedigital.core.database import get_session
from tradedigital.core.time import utc_now
from tradedigital.platform.audit.service import write_audit_log
from tradedigital.platform.iam.deps import get_current_context
from tradedigital.platform.iam.models import AuthState
from tradedigital.platform.iam.oidc import build_login_redirect, exchange_code_for_claims, frontend_redirect_url
from tradedigital.platform.iam.repository import get_sso_connection, get_user_with_roles
from tradedigital.platform.iam.service import create_session, revoke_session, upsert_oidc_user, user_out
from tradedigital.platform.org.repository import get_enterprise, get_enterprise_by_code
from tradedigital.platform.org.service import enterprise_out
from tradedigital.shared.auth_context import AuthContext
from tradedigital.shared.types import ok

router = APIRouter()


@router.get("/sso/login")
async def sso_login(
    enterprise_code: str = Query(default="default"),
    redirect_after_login: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    settings = get_settings()
    enterprise = await get_enterprise_by_code(session, enterprise_code)
    if not enterprise or enterprise.status != "active":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enterprise not found")
    connection = await get_sso_connection(session, enterprise.id, settings.oidc_provider)
    if not connection:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SSO not configured")
    auth_state, response = await build_login_redirect(
        connection,
        enterprise_id=enterprise.id,
        redirect_after_login=redirect_after_login or settings.default_login_redirect,
    )
    session.add(auth_state)
    await session.commit()
    return response


@router.get("/sso/callback")
async def sso_callback(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    settings = get_settings()
    state = request.query_params.get("state")
    if not state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OIDC state missing")
    auth_state = await session.get(AuthState, state)
    expires_at = auth_state.expires_at if auth_state else None
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if not auth_state or not expires_at or expires_at <= utc_now():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OIDC state expired")
    connection = await get_sso_connection(session, auth_state.enterprise_id, settings.oidc_provider)
    if not connection:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SSO not configured")

    try:
        claims = await exchange_code_for_claims(request, connection, auth_state)
        subject = str(claims.get("sub") or "")
        email = str(claims.get("email") or "").lower()
        if not subject or not email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="OIDC identity incomplete")
        user = await upsert_oidc_user(
            session,
            enterprise_id=auth_state.enterprise_id,
            provider=connection.provider,
            subject=subject,
            email=email,
            name=claims.get("name") or claims.get("preferred_username"),
            avatar_url=claims.get("picture"),
        )
        token = await create_session(
            session,
            user,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
        await write_audit_log(
            session,
            enterprise_id=user.enterprise_id,
            user_id=user.id,
            module="iam",
            action="login.success",
            resource_type="iam_user",
            resource_id=user.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        await session.execute(delete(AuthState).where(AuthState.state == auth_state.state))
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    response = RedirectResponse(
        frontend_redirect_url(auth_state.redirect_after_login),
        status_code=status.HTTP_302_FOUND,
    )
    response.set_cookie(
        settings.session_cookie_name,
        token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.session_expire_hours * 3600,
        path="/",
    )
    return response


@router.get("/me")
async def me(
    ctx: AuthContext = Depends(get_current_context),
    session: AsyncSession = Depends(get_session),
):
    user = await get_user_with_roles(session, ctx.user_id)
    enterprise = await get_enterprise(session, ctx.enterprise_id)
    if not user or not enterprise:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session unavailable")
    return ok(
        {
            "user": user_out(user),
            "enterprise": enterprise_out(enterprise),
            "roles": ctx.roles,
            "permissions": ctx.permissions,
            "isAuthenticated": True,
        }
    )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    ctx: AuthContext = Depends(get_current_context),
    session: AsyncSession = Depends(get_session),
):
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        await revoke_session(session, token)
    await write_audit_log(
        session,
        enterprise_id=ctx.enterprise_id,
        user_id=ctx.user_id,
        module="iam",
        action="logout",
        resource_type="iam_user",
        resource_id=ctx.user_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()
    response.delete_cookie(settings.session_cookie_name, path="/")
    return ok({"success": True})
