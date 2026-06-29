"""Chat streaming orchestration (SSE)."""

import time

from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from tradedigital.apps.llm.api.schemas import StreamChatRequest
from tradedigital.apps.llm.api.serializers import conversation_out, message_out
from tradedigital.apps.llm.domain.models import Conversation, LlmModelCallLog, Message
from tradedigital.apps.llm.infrastructure.model_gateway import (
    ModelGatewayError,
    build_context,
    stream_model_response,
)
from tradedigital.apps.llm.infrastructure.sse import sse
from tradedigital.apps.llm.repositories import queries
from tradedigital.apps.llm.services import catalog, projects
from tradedigital.core.database import AsyncSessionLocal
from tradedigital.core.time import utc_now
from tradedigital.platform.audit.service import write_context_audit_log
from tradedigital.shared.auth_context import AuthContext


async def stream_chat(
    payload: StreamChatRequest, ctx: AuthContext, session: AsyncSession
) -> StreamingResponse:
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="消息不能为空")

    conversation = None
    previous_messages = []
    if payload.conversation_id:
        conversation = await queries.get_owned_conversation(session, ctx, payload.conversation_id)
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
        previous_messages = await queries.conversation_messages(session, conversation.id)

    model = await catalog.require_accessible_model(
        session,
        ctx,
        payload.model_id or (conversation.model_id if conversation else None),
        detail="当前模型不可用或无权使用",
    )
    assistant_preset_id = await catalog.resolve_assistant_preset_id(session, ctx, payload.assistant_preset_id)
    project_id = await projects.resolve_project_id(session, ctx, payload.project_id)

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

    system_prompt = await catalog.get_preset_system_prompt(session, ctx, conversation.assistant_preset_id)
    context = build_context(previous_messages, content, system_prompt)

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
    enterprise_id = ctx.enterprise_id
    user_id = ctx.user_id

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
                        enterprise_id=enterprise_id,
                        user_id=user_id,
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
                        enterprise_id=enterprise_id,
                        user_id=user_id,
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
