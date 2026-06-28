import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from tradedigital.apps.llm.model_gateway import ModelGatewayError, build_context, stream_model_response
from tradedigital.apps.llm.models import Conversation, Message, LlmModelCallLog, LlmProject
from tradedigital.apps.llm.repository import (
    conversation_messages,
    get_accessible_model,
    get_accessible_preset,
    get_owned_conversation,
    get_owned_project,
    list_accessible_models,
    list_conversations,
    list_projects,
    list_presets,
)
from tradedigital.apps.llm.schemas import (
    ConversationCreate,
    ConversationUpdate,
    EditAndRerunRequest,
    MessageUpdate,
    ProjectCreate,
    ProjectUpdate,
    RegenerateRequest,
    StreamChatRequest,
)
from tradedigital.apps.llm.service import (
    assistant_out,
    conversation_detail,
    conversation_out,
    message_out,
    model_out,
    project_out,
)
from tradedigital.apps.llm.stream import sse
from tradedigital.core.database import AsyncSessionLocal, get_session
from tradedigital.core.time import utc_now
from tradedigital.platform.audit.service import write_context_audit_log
from tradedigital.platform.iam.deps import require_permission
from tradedigital.shared.auth_context import AuthContext
from tradedigital.shared.types import ok

router = APIRouter()


def normalize_conversation_title(title: Optional[str], fallback: str = "新聊天") -> str:
    if title is None:
        return fallback
    normalized = title.strip()
    if not normalized:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="会话标题不能为空")
    return normalized[:255]


async def resolve_assistant_preset_id(
    session: AsyncSession,
    ctx: AuthContext,
    preset_id: str | None,
) -> str | None:
    if not preset_id:
        return None
    preset = await get_accessible_preset(session, ctx, preset_id)
    if not preset:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权使用该助手预设")
    return preset.id


def normalize_project_name(name: str) -> str:
    normalized = name.strip()
    if not normalized:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="项目名称不能为空")
    return normalized[:100]


async def resolve_project_id(
    session: AsyncSession,
    ctx: AuthContext,
    project_id: str | None,
) -> str | None:
    if not project_id:
        return None
    project = await get_owned_project(session, ctx, project_id)
    if not project or project.archived:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    return project.id


@router.get("/models")
async def models(
    ctx: AuthContext = Depends(require_permission("llm.model.read")),
    session: AsyncSession = Depends(get_session),
):
    rows = await list_accessible_models(session, ctx)
    return ok([model_out(row) for row in rows])


@router.get("/assistant-presets")
async def assistant_presets(
    ctx: AuthContext = Depends(require_permission("llm.preset.read")),
    session: AsyncSession = Depends(get_session),
):
    rows = await list_presets(session, ctx)
    return ok([assistant_out(row) for row in rows])


@router.get("/projects")
async def projects(
    ctx: AuthContext = Depends(require_permission("llm.conversation.read_own")),
    session: AsyncSession = Depends(get_session),
):
    rows = await list_projects(session, ctx)
    return ok([project_out(row) for row in rows])


@router.post("/projects")
async def create_project(
    payload: ProjectCreate,
    ctx: AuthContext = Depends(require_permission("llm.conversation.manage_own")),
    session: AsyncSession = Depends(get_session),
):
    project = LlmProject(
        enterprise_id=ctx.enterprise_id,
        user_id=ctx.user_id,
        name=normalize_project_name(payload.name),
        description=payload.description,
        color=payload.color,
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return ok(project_out(project))


@router.patch("/projects/{project_id}")
async def update_project(
    project_id: str,
    payload: ProjectUpdate,
    ctx: AuthContext = Depends(require_permission("llm.conversation.manage_own")),
    session: AsyncSession = Depends(get_session),
):
    project = await get_owned_project(session, ctx, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates and updates["name"] is not None:
        updates["name"] = normalize_project_name(updates["name"])
    for key, value in updates.items():
        setattr(project, key, value)
    await session.commit()
    await session.refresh(project)
    return ok(project_out(project))


@router.get("/conversations")
async def conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(80, ge=1, le=100),
    keyword: str = "",
    archived: bool | None = False,
    pinned: bool | None = None,
    ctx: AuthContext = Depends(require_permission("llm.conversation.read_own")),
    session: AsyncSession = Depends(get_session),
):
    rows, total = await list_conversations(
        session,
        ctx,
        page=page,
        page_size=page_size,
        keyword=keyword,
        archived=archived,
        pinned=pinned,
    )
    return ok({"items": [conversation_out(row) for row in rows], "page": page, "page_size": page_size, "total": total})


@router.post("/conversations")
async def create_conversation(
    payload: ConversationCreate,
    ctx: AuthContext = Depends(require_permission("llm.conversation.manage_own")),
    session: AsyncSession = Depends(get_session),
):
    model = await get_accessible_model(session, ctx, payload.model_id)
    if payload.model_id and not model:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权使用该模型")
    assistant_preset_id = await resolve_assistant_preset_id(session, ctx, payload.assistant_preset_id)
    project_id = await resolve_project_id(session, ctx, payload.project_id)
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
    return ok(conversation_out(conversation))


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    ctx: AuthContext = Depends(require_permission("llm.conversation.read_own")),
    session: AsyncSession = Depends(get_session),
):
    conversation = await get_owned_conversation(session, ctx, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    return ok(conversation_detail(conversation))


@router.patch("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    payload: ConversationUpdate,
    ctx: AuthContext = Depends(require_permission("llm.conversation.manage_own")),
    session: AsyncSession = Depends(get_session),
):
    conversation = await get_owned_conversation(session, ctx, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    updates = payload.model_dump(exclude_unset=True)
    if "model_id" in updates and updates["model_id"]:
        model = await get_accessible_model(session, ctx, updates["model_id"])
        if not model:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权使用该模型")
        updates["model_id"] = model.id
    if "assistant_preset_id" in updates and updates["assistant_preset_id"]:
        updates["assistant_preset_id"] = await resolve_assistant_preset_id(
            session, ctx, updates["assistant_preset_id"]
        )
    if "project_id" in updates:
        updates["project_id"] = await resolve_project_id(session, ctx, updates["project_id"])
    if "title" in updates:
        updates["title"] = normalize_conversation_title(updates["title"])
    for key, value in updates.items():
        setattr(conversation, key, value)
    await session.commit()
    await session.refresh(conversation)
    return ok(conversation_out(conversation))


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    ctx: AuthContext = Depends(require_permission("llm.conversation.manage_own")),
    session: AsyncSession = Depends(get_session),
):
    conversation = await get_owned_conversation(session, ctx, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    conversation.deleted_at = utc_now()
    conversation.status = "deleted"
    await session.commit()
    return ok({"success": True})


@router.post("/chat/stream")
async def stream_chat(
    payload: StreamChatRequest,
    ctx: AuthContext = Depends(require_permission("llm.chat.use")),
    session: AsyncSession = Depends(get_session),
):
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="消息不能为空")

    conversation = None
    previous_messages = []
    if payload.conversation_id:
        conversation = await get_owned_conversation(session, ctx, payload.conversation_id)
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
        previous_messages = await conversation_messages(session, conversation.id)

    model = await get_accessible_model(
        session, ctx, payload.model_id or (conversation.model_id if conversation else None)
    )
    if not model:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前模型不可用或无权使用")
    assistant_preset_id = await resolve_assistant_preset_id(session, ctx, payload.assistant_preset_id)
    project_id = await resolve_project_id(session, ctx, payload.project_id)

    if not conversation:
        conversation = Conversation(
            enterprise_id=ctx.enterprise_id,
            user_id=ctx.user_id,
            title=content[:28] or "新聊天",
            model_id=model.id,
            assistant_preset_id=assistant_preset_id,
            project_id=project_id,
            temporary=payload.temporary,
        )
        session.add(conversation)
        await session.flush()

    conversation.model_id = model.id
    conversation.assistant_preset_id = assistant_preset_id or conversation.assistant_preset_id
    conversation.project_id = project_id or conversation.project_id
    if conversation.title == "新聊天":
        conversation.title = content[:28]

    context = build_context(previous_messages, content)
    user_message = Message(
        enterprise_id=ctx.enterprise_id,
        conversation_id=conversation.id,
        user_id=ctx.user_id,
        role="user",
        content=content,
        status="completed",
        model_id=model.id,
    )
    assistant_message = Message(
        enterprise_id=ctx.enterprise_id,
        conversation_id=conversation.id,
        user_id=None,
        role="assistant",
        content="",
        status="streaming",
        model_id=model.id,
    )
    session.add_all([user_message, assistant_message])
    conversation.message_count += 2
    conversation.last_message_at = utc_now()
    await session.commit()
    await session.refresh(conversation)
    await session.refresh(user_message)
    await session.refresh(assistant_message)

    conversation_payload = conversation_out(conversation)
    user_message_payload = message_out(user_message)
    assistant_message_payload = message_out(assistant_message)
    conversation_id = conversation.id
    assistant_message_id = assistant_message.id
    model_id = model.id
    provider_code = model.provider_code

    async def event_generator():
        start = time.perf_counter()
        accumulated: list[str] = []
        yield sse(
            "message_start",
            {
                "conversation": conversation_payload,
                "user_message": user_message_payload,
                "assistant_message": assistant_message_payload,
            },
        )
        try:
            async for delta in stream_model_response(model, context):
                accumulated.append(delta)
                yield sse("delta", {"message_id": assistant_message_id, "content": delta})
            answer = "".join(accumulated)
            if not answer:
                raise ModelGatewayError("模型未返回内容")
            async with AsyncSessionLocal() as stream_session:
                stored_message = await stream_session.get(Message, assistant_message_id)
                stored_conversation = await stream_session.get(Conversation, conversation_id)
                if stored_message:
                    stored_message.content = answer
                    stored_message.status = "completed"
                if stored_conversation:
                    stored_conversation.last_message_at = utc_now()
                    stored_conversation.updated_at = utc_now()
                stream_session.add(
                    LlmModelCallLog(
                        enterprise_id=ctx.enterprise_id,
                        user_id=ctx.user_id,
                        conversation_id=conversation_id,
                        model_id=model_id,
                        provider_code=provider_code,
                        completion_tokens=len(answer),
                        total_tokens=len(answer) + len(content),
                        status="completed",
                        latency_ms=int((time.perf_counter() - start) * 1000),
                    )
                )
                await write_context_audit_log(
                    stream_session,
                    ctx,
                    module="llm",
                    action="llm.model.call",
                    resource_type="llm_model",
                    resource_id=model_id,
                    detail_json={"conversation_id": conversation_id, "status": "completed"},
                )
                await stream_session.commit()
            yield sse(
                "message_end",
                {"message_id": assistant_message_id, "status": "completed", "content": answer},
            )
        except Exception as exc:
            async with AsyncSessionLocal() as stream_session:
                stored_message = await stream_session.get(Message, assistant_message_id)
                if stored_message:
                    stored_message.status = "failed"
                    stored_message.metadata_json = {"error_message": str(exc)}
                stream_session.add(
                    LlmModelCallLog(
                        enterprise_id=ctx.enterprise_id,
                        user_id=ctx.user_id,
                        conversation_id=conversation_id,
                        model_id=model_id,
                        provider_code=provider_code,
                        status="failed",
                        error_message=str(exc),
                    )
                )
                await write_context_audit_log(
                    stream_session,
                    ctx,
                    module="llm",
                    action="llm.model.call",
                    resource_type="llm_model",
                    resource_id=model_id,
                    detail_json={"conversation_id": conversation_id, "status": "failed"},
                )
                await stream_session.commit()
            yield sse("error", {"code": "MODEL_CALL_FAILED", "message": "模型调用失败，请稍后重试"})

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.patch("/messages/{message_id}")
async def update_message(
    message_id: str,
    payload: MessageUpdate,
    ctx: AuthContext = Depends(require_permission("llm.conversation.manage_own")),
    session: AsyncSession = Depends(get_session),
):
    message = await session.get(Message, message_id)
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="消息不存在")
    conversation = await get_owned_conversation(session, ctx, message.conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="消息不存在")
    metadata = dict(message.metadata_json or {})
    updates = payload.model_dump(exclude_unset=True)
    if "feedback" in updates:
        metadata["feedback"] = updates["feedback"]
    message.metadata_json = metadata
    await session.commit()
    await session.refresh(message)
    return ok(message_out(message))


@router.post("/chat/regenerate")
async def regenerate(
    payload: RegenerateRequest,
    ctx: AuthContext = Depends(require_permission("llm.chat.use")),
):
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="重新生成暂未实现")


@router.post("/chat/edit-and-rerun")
async def edit_and_rerun(
    payload: EditAndRerunRequest,
    ctx: AuthContext = Depends(require_permission("llm.chat.use")),
):
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="编辑并重新运行暂未实现")
