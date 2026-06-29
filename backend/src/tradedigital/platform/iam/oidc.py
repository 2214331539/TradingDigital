from datetime import timedelta
from typing import Any

import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client
from fastapi import HTTPException, Request, status
from joserfc import jwk, jwt
from joserfc.errors import JoseError
from starlette.responses import RedirectResponse

from tradedigital.core.config import get_settings
from tradedigital.core.security import code_challenge, generate_code_verifier, generate_nonce, generate_state
from tradedigital.core.time import utc_now
from tradedigital.platform.iam.models import AuthState, SSOConnection


async def discover_oidc(issuer_url: str) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=10, trust_env=False) as client:
            response = await client.get(f"{issuer_url.rstrip('/')}/.well-known/openid-configuration")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OIDC provider unavailable",
        ) from exc


async def build_login_redirect(
    connection: SSOConnection,
    *,
    enterprise_id: str,
    redirect_after_login: str,
) -> tuple[AuthState, RedirectResponse]:
    metadata = await discover_oidc(connection.issuer_url)
    state = generate_state()
    nonce = generate_nonce()
    verifier = generate_code_verifier()
    auth_state = AuthState(
        state=state,
        enterprise_id=enterprise_id,
        nonce=nonce,
        code_verifier=verifier,
        redirect_after_login=redirect_after_login,
        expires_at=utc_now() + timedelta(minutes=10),
    )
    client = AsyncOAuth2Client(
        client_id=connection.client_id,
        redirect_uri=connection.redirect_uri,
        scope="openid email profile",
        trust_env=False,
    )
    authorization_url, _ = client.create_authorization_url(
        metadata["authorization_endpoint"],
        state=state,
        nonce=nonce,
        code_challenge=code_challenge(verifier),
        code_challenge_method="S256",
    )
    return auth_state, RedirectResponse(authorization_url)


async def exchange_code_for_claims(
    request: Request,
    connection: SSOConnection,
    auth_state: AuthState,
) -> dict[str, Any]:
    metadata = await discover_oidc(connection.issuer_url)
    client = AsyncOAuth2Client(
        client_id=connection.client_id,
        client_secret=connection.client_secret_encrypted,
        redirect_uri=connection.redirect_uri,
        scope="openid email profile",
        trust_env=False,
    )
    token = await client.fetch_token(
        metadata["token_endpoint"],
        code=request.query_params.get("code"),
        code_verifier=auth_state.code_verifier,
        grant_type="authorization_code",
    )
    id_token = token.get("id_token")
    if not id_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="OIDC id_token missing")
    async with httpx.AsyncClient(timeout=10, trust_env=False) as http:
        jwks_response = await http.get(metadata["jwks_uri"])
        jwks_response.raise_for_status()
    key_set = jwk.KeySet.import_key_set(jwks_response.json())
    try:
        token = jwt.decode(id_token, key_set)
        claims = dict(token.claims)
        jwt.JWTClaimsRegistry(
            iss={"essential": True, "value": connection.issuer_url.rstrip("/")},
            aud={"essential": True, "value": connection.client_id},
            nonce={"essential": True, "value": auth_state.nonce},
        ).validate(claims)
    except JoseError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="OIDC id_token invalid") from exc
    return claims


def frontend_redirect_url(path: str) -> str:
    settings = get_settings()
    base = settings.frontend_url.rstrip("/")
    # Only allow same-origin relative paths to avoid open-redirect attacks via
    # the attacker-controlled ``redirect_after_login`` query parameter.
    # Reject absolute URLs ("https://evil.com"), scheme-relative URLs ("//evil.com"),
    # and anything that does not start with a single "/".
    if not path or not path.startswith("/") or path.startswith("//"):
        return base + "/app"
    return base + "/" + path.lstrip("/")
