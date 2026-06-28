from sqlalchemy import Select, and_, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from tradedigital.apps.llm.models import (
    AssistantPreset,
    Conversation,
    LlmProject,
    LlmModel,
    Message,
    llm_model_role_grants,
)
from tradedigital.shared.auth_context import AuthContext


def model_access_clause(ctx: AuthContext):
    return or_(
        ~exists().where(llm_model_role_grants.c.model_id == LlmModel.id),
        exists().where(
            and_(
                llm_model_role_grants.c.model_id == LlmModel.id,
                llm_model_role_grants.c.role_id.in_(ctx.roles),
            )
        ),
    )


async def list_accessible_models(session: AsyncSession, ctx: AuthContext) -> list[LlmModel]:
    rows = await session.scalars(
        select(LlmModel)
        .where(LlmModel.enabled.is_(True), model_access_clause(ctx))
        .order_by(LlmModel.is_default.desc(), LlmModel.display_name)
    )
    return rows.all()


async def get_accessible_model(
    session: AsyncSession, ctx: AuthContext, model_id: str | None
) -> LlmModel | None:
    query = select(LlmModel).where(LlmModel.enabled.is_(True), model_access_clause(ctx))
    if model_id:
        query = query.where(LlmModel.id == model_id)
    else:
        query = query.order_by(LlmModel.is_default.desc(), LlmModel.display_name)
    return await session.scalar(query)


async def get_owned_conversation(
    session: AsyncSession, ctx: AuthContext, conversation_id: str
) -> Conversation | None:
    return await session.scalar(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(
            Conversation.id == conversation_id,
            Conversation.enterprise_id == ctx.enterprise_id,
            Conversation.user_id == ctx.user_id,
            Conversation.deleted_at.is_(None),
        )
    )


def conversation_query(ctx: AuthContext) -> Select[tuple[Conversation]]:
    return select(Conversation).where(
        Conversation.enterprise_id == ctx.enterprise_id,
        Conversation.user_id == ctx.user_id,
        Conversation.deleted_at.is_(None),
        Conversation.temporary.is_(False),
    )


async def list_conversations(
    session: AsyncSession,
    ctx: AuthContext,
    *,
    page: int,
    page_size: int,
    keyword: str = "",
    archived: bool | None = False,
    pinned: bool | None = None,
) -> tuple[list[Conversation], int]:
    query = conversation_query(ctx)
    if archived is not None:
        query = query.where(Conversation.archived.is_(archived))
    if pinned is not None:
        query = query.where(Conversation.pinned.is_(pinned))
    if keyword:
        like = f"%{keyword}%"
        query = query.where(
            or_(
                Conversation.title.ilike(like),
                exists().where(
                    and_(
                        Message.conversation_id == Conversation.id,
                        Message.deleted_at.is_(None),
                        Message.content.ilike(like),
                    )
                ),
            )
        )
    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    rows = await session.scalars(
        query.order_by(Conversation.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    return rows.all(), int(total or 0)


async def list_presets(session: AsyncSession, ctx: AuthContext) -> list[AssistantPreset]:
    rows = await session.scalars(
        select(AssistantPreset)
        .where(
            AssistantPreset.enterprise_id == ctx.enterprise_id,
            AssistantPreset.enabled.is_(True),
            or_(AssistantPreset.visibility != "private", AssistantPreset.created_by == ctx.user_id),
        )
        .order_by(AssistantPreset.created_at)
    )
    return rows.all()


async def get_accessible_preset(
    session: AsyncSession, ctx: AuthContext, preset_id: str
) -> AssistantPreset | None:
    return await session.scalar(
        select(AssistantPreset).where(
            AssistantPreset.id == preset_id,
            AssistantPreset.enterprise_id == ctx.enterprise_id,
            AssistantPreset.enabled.is_(True),
            or_(AssistantPreset.visibility != "private", AssistantPreset.created_by == ctx.user_id),
        )
    )


async def conversation_messages(session: AsyncSession, conversation_id: str) -> list[Message]:
    rows = await session.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id, Message.deleted_at.is_(None))
        .order_by(Message.created_at)
    )
    return rows.all()


async def list_projects(session: AsyncSession, ctx: AuthContext) -> list[LlmProject]:
    rows = await session.scalars(
        select(LlmProject)
        .where(
            LlmProject.enterprise_id == ctx.enterprise_id,
            LlmProject.user_id == ctx.user_id,
            LlmProject.deleted_at.is_(None),
            LlmProject.archived.is_(False),
        )
        .order_by(LlmProject.updated_at.desc(), LlmProject.name)
    )
    return rows.all()


async def get_owned_project(
    session: AsyncSession,
    ctx: AuthContext,
    project_id: str,
) -> LlmProject | None:
    return await session.scalar(
        select(LlmProject).where(
            LlmProject.id == project_id,
            LlmProject.enterprise_id == ctx.enterprise_id,
            LlmProject.user_id == ctx.user_id,
            LlmProject.deleted_at.is_(None),
        )
    )
