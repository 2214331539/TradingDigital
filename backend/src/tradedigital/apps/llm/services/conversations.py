"""Conversation & message logic."""

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from tradedigital.apps.llm.api.schemas import ConversationCreate, ConversationUpdate, MessageUpdate
from tradedigital.apps.llm.domain.models import Conversation, Message
from tradedigital.apps.llm.repositories import queries
from tradedigital.apps.llm.services import catalog, projects
from tradedigital.core.time import utc_now
from tradedigital.shared.auth_context import AuthContext


def normalize_conversation_title(title: Optional[str], fallback: str = "新聊天") -> str:
    if title is None:
        return fallback
    normalized = title.strip()
    if not normalized:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="会话标题不能为空")
    return normalized[:255]


async def list_conversations(
    session: AsyncSession,
    ctx: AuthContext,
    *,
    page: int,
    page_size: int,
    keyword: str,
    archived: bool | None,
    pinned: bool | None,
) -> tuple[list[Conversation], int]:
    return await queries.list_conversations(
        session,
        ctx,
        page=page,
        page_size=page_size,
        keyword=keyword,
        archived=archived,
        pinned=pinned,
    )


async def get_owned_conversation_or_404(
    session: AsyncSession, ctx: AuthContext, conversation_id: str
) -> Conversation:
    conversation = await queries.get_owned_conversation(session, ctx, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    return conversation


async def create_conversation(
    session: AsyncSession, ctx: AuthContext, payload: ConversationCreate
) -> Conversation:
    model = await queries.get_accessible_model(session, ctx, payload.model_id)
    if payload.model_id and not model:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权使用该模型")
    assistant_preset_id = await catalog.resolve_assistant_preset_id(session, ctx, payload.assistant_preset_id)
    project_id = await projects.resolve_project_id(session, ctx, payload.project_id)
    conversation = Conversation(
        enterprise_id=ctx.enterprise_id,
        user_id=ctx.user_id,
        title=normalize_conversation_title(payload.title),
        model_id=model.id if model else None,
        assistant_preset_id=assistant_preset_id,
        project_id=project_id,
        temporary=payload.temporary,
        last_message_at=utc_now(),
    )
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)
    return conversation


async def update_conversation(
    session: AsyncSession, ctx: AuthContext, conversation_id: str, payload: ConversationUpdate
) -> Conversation:
    conversation = await get_owned_conversation_or_404(session, ctx, conversation_id)
    updates = payload.model_dump(exclude_unset=True)
    if "model_id" in updates:
        if updates["model_id"]:
            model = await queries.get_accessible_model(session, ctx, updates["model_id"])
            if not model:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权使用该模型")
            updates["model_id"] = model.id
        else:
            updates["model_id"] = None
    if "assistant_preset_id" in updates:
        updates["assistant_preset_id"] = await catalog.resolve_assistant_preset_id(
            session, ctx, updates["assistant_preset_id"]
        )
    if "project_id" in updates:
        updates["project_id"] = await projects.resolve_project_id(session, ctx, updates["project_id"])
    if "title" in updates:
        updates["title"] = normalize_conversation_title(updates["title"])
    for key, value in updates.items():
        setattr(conversation, key, value)
    await session.commit()
    await session.refresh(conversation)
    return conversation


async def delete_conversation(session: AsyncSession, ctx: AuthContext, conversation_id: str) -> None:
    conversation = await get_owned_conversation_or_404(session, ctx, conversation_id)
    conversation.deleted_at = utc_now()
    conversation.status = "deleted"
    await session.commit()


async def update_message_feedback(
    session: AsyncSession, ctx: AuthContext, message_id: str, payload: MessageUpdate
) -> Message:
    message = await session.get(Message, message_id)
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="消息不存在")
    conversation = await queries.get_owned_conversation(session, ctx, message.conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="消息不存在")
    metadata = dict(message.metadata_json or {})
    updates = payload.model_dump(exclude_unset=True)
    if "feedback" in updates:
        metadata["feedback"] = updates["feedback"]
    message.metadata_json = metadata
    await session.commit()
    await session.refresh(message)
    return message
