"""Model & assistant-preset catalog logic."""

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from tradedigital.apps.llm.domain.models import AssistantPreset, LlmModel
from tradedigital.apps.llm.repositories import queries
from tradedigital.shared.auth_context import AuthContext


async def list_models(session: AsyncSession, ctx: AuthContext) -> list[LlmModel]:
    return await queries.list_accessible_models(session, ctx)


async def list_presets(session: AsyncSession, ctx: AuthContext) -> list[AssistantPreset]:
    return await queries.list_presets(session, ctx)


async def require_accessible_model(
    session: AsyncSession, ctx: AuthContext, model_id: str | None, *, detail: str
) -> LlmModel:
    model = await queries.get_accessible_model(session, ctx, model_id)
    if not model:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
    return model


async def resolve_assistant_preset_id(
    session: AsyncSession, ctx: AuthContext, preset_id: str | None
) -> str | None:
    if not preset_id:
        return None
    preset = await queries.get_accessible_preset(session, ctx, preset_id)
    if not preset:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权使用该助手预设")
    return preset.id


async def get_preset_system_prompt(
    session: AsyncSession, ctx: AuthContext, preset_id: str | None
) -> str | None:
    if not preset_id:
        return None
    preset = await queries.get_accessible_preset(session, ctx, preset_id)
    return preset.system_prompt if preset else None
