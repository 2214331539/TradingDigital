import json
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.models import AiModel, AssistantPreset, Conversation, Message, ModelCallLog, Project, User
from app.db.session import SessionLocal, get_db
from app.schemas.chat import (
    ConversationCreate,
    ConversationUpdate,
    FeedbackRequest,
    ProjectCreate,
    ProjectUpdate,
    StreamChatRequest,
)
from app.schemas.common import ok
from app.services.model_gateway import build_context, stream_model_response
from app.services.serializers import (
    assistant_out,
    conversation_detail,
    conversation_out,
    message_out,
    model_out,
    project_out,
)

router = APIRouter(tags=["chat"])


def sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


def get_owned_conversation(db: Session, user: User, conversation_id: str) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    if (
        not conversation
        or conversation.deleted_at
        or conversation.user_id != user.id
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    return conversation


def default_model(db: Session) -> Optional[AiModel]:
    model = db.query(AiModel).filter(AiModel.enabled.is_(True), AiModel.is_default.is_(True)).first()
    if model:
        return model
    return db.query(AiModel).filter(AiModel.enabled.is_(True)).first()


@router.get("/models/available")
def available_models(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    role_ids = [role.id for role in current_user.roles]
    models = (
        db.query(AiModel)
        .filter(AiModel.enabled.is_(True), AiModel.deleted_at.is_(None))
        .order_by(AiModel.sort_order, AiModel.created_at)
        .all()
    )
    allowed = []
    for model in models:
        model_role_ids = [role.id for role in model.roles]
        if not model_role_ids or set(role_ids).intersection(model_role_ids):
            allowed.append(model_out(model))
    return ok(allowed)


@router.get("/assistants")
def assistants(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(AssistantPreset)
        .filter(AssistantPreset.enabled.is_(True))
        .order_by(AssistantPreset.sort_order, AssistantPreset.created_at)
        .all()
    )
    return ok([assistant_out(row) for row in rows])


def get_owned_project(db: Session, user: User, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if not project or project.deleted_at or project.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    return project


@router.get("/projects")
def list_projects(
    archived: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Project)
        .filter(
            Project.user_id == current_user.id,
            Project.deleted_at.is_(None),
            Project.is_archived.is_(archived),
        )
        .order_by(Project.sort_order, Project.updated_at.desc())
        .all()
    )
    return ok([project_out(row) for row in rows])


@router.post("/projects")
def create_project(
    payload: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="项目名称不能为空")
    project = Project(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        name=name,
        description=payload.description,
        icon=payload.icon,
        color=payload.color,
        sort_order=payload.sort_order,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return ok(project_out(project))


@router.patch("/projects/{project_id}")
def update_project(
    project_id: str,
    payload: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(db, current_user, project_id)
    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates and updates["name"] is not None:
        updates["name"] = updates["name"].strip()
        if not updates["name"]:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="项目名称不能为空")
    for key, value in updates.items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return ok(project_out(project))


@router.delete("/projects/{project_id}")
def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(db, current_user, project_id)
    project.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return ok({"success": True})


@router.post("/conversations")
def create_conversation(
    payload: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    model_id = payload.model_id or (default_model(db).id if default_model(db) else None)
    project_id = None
    if payload.project_id:
        project_id = get_owned_project(db, current_user, payload.project_id).id
    conversation = Conversation(
        user_id=current_user.id,
        title=payload.title or "新聊天",
        project_id=project_id,
        model_id=model_id,
        assistant_id=payload.assistant_id,
        is_temporary=payload.is_temporary,
        last_message_at=datetime.now(timezone.utc),
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return ok(conversation_out(conversation))


@router.get("/conversations")
def list_conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    keyword: str = "",
    project_id: Optional[str] = None,
    archived: Optional[bool] = None,
    favorited: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Conversation).filter(
        Conversation.user_id == current_user.id,
        Conversation.deleted_at.is_(None),
        Conversation.is_temporary.is_(False),
    )
    if archived is not None:
        query = query.filter(Conversation.is_archived.is_(archived))
    if favorited is not None:
        query = query.filter(Conversation.is_favorited.is_(favorited))
    if project_id is not None:
        query = query.filter(Conversation.project_id == project_id)
    if keyword:
        query = query.filter(Conversation.title.ilike(f"%{keyword}%"))
    total = query.count()
    rows = (
        query.order_by(Conversation.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return ok(
        {
            "items": [conversation_out(row) for row in rows],
            "page": page,
            "page_size": page_size,
            "total": total,
        }
    )


@router.get("/conversations/search")
def search_conversations(
    keyword: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversations = (
        db.query(Conversation)
        .outerjoin(Message, Message.conversation_id == Conversation.id)
        .filter(
            Conversation.user_id == current_user.id,
            Conversation.deleted_at.is_(None),
            or_(Conversation.title.ilike(f"%{keyword}%"), Message.content.ilike(f"%{keyword}%")),
        )
        .order_by(Conversation.updated_at.desc())
        .limit(20)
        .all()
    )
    return ok([conversation_out(row) for row in conversations])


@router.get("/conversations/{conversation_id}")
def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = get_owned_conversation(db, current_user, conversation_id)
    return ok(conversation_detail(conversation))


@router.patch("/conversations/{conversation_id}")
def update_conversation(
    conversation_id: str,
    payload: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = get_owned_conversation(db, current_user, conversation_id)
    updates = payload.model_dump(exclude_unset=True)
    if "project_id" in updates and updates["project_id"]:
        updates["project_id"] = get_owned_project(db, current_user, updates["project_id"]).id
    for key, value in updates.items():
        setattr(conversation, key, value)
    db.commit()
    db.refresh(conversation)
    return ok(conversation_out(conversation))


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = get_owned_conversation(db, current_user, conversation_id)
    conversation.deleted_at = datetime.now(timezone.utc)
    conversation.status = "deleted"
    db.commit()
    return ok({"success": True})


@router.get("/conversations/{conversation_id}/messages")
def messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = get_owned_conversation(db, current_user, conversation_id)
    return ok([message_out(message) for message in conversation.messages if not message.deleted_at])


@router.post("/chat/completions/stream")
async def stream_chat(
    payload: StreamChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not payload.content.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="消息不能为空")

    conversation = None
    if payload.conversation_id:
        conversation = get_owned_conversation(db, current_user, payload.conversation_id)
    else:
        project_id = None
        if payload.project_id:
            project_id = get_owned_project(db, current_user, payload.project_id).id
        conversation = Conversation(
            user_id=current_user.id,
            project_id=project_id,
            title=payload.content.strip()[:28] or "新聊天",
            model_id=payload.model_id,
            assistant_id=payload.assistant_id,
            is_temporary=payload.temporary,
        )
        db.add(conversation)
        db.flush()

    model = db.get(AiModel, payload.model_id or conversation.model_id) if (payload.model_id or conversation.model_id) else None
    if not model:
        model = default_model(db)
    if not model or not model.enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="当前模型不可用")

    if conversation.title == "新聊天" and payload.content:
        conversation.title = payload.content.strip()[:28]
    conversation.model_id = model.id
    conversation.assistant_id = payload.assistant_id or conversation.assistant_id

    user_message = Message(
        conversation_id=conversation.id,
        user_id=current_user.id,
        role="user",
        content=payload.content,
        status="completed",
        model_id=model.id,
        assistant_id=conversation.assistant_id,
    )
    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content="",
        status="streaming",
        model_id=model.id,
        assistant_id=conversation.assistant_id,
    )
    db.add_all([user_message, assistant_message])
    conversation.message_count += 2
    conversation.last_message_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user_message)
    db.refresh(assistant_message)
    db.refresh(conversation)
    conversation_payload = conversation_out(conversation)
    user_message_payload = message_out(user_message)
    assistant_message_payload = message_out(assistant_message)
    user_id = current_user.id
    conversation_id = conversation.id
    assistant_message_id = assistant_message.id
    model_id = model.id
    model_provider = model.provider

    previous_messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id, Message.id != assistant_message.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    context = build_context(previous_messages[:-1], payload.content)

    async def event_generator():
        start = time.perf_counter()
        accumulated = []
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
                yield sse("delta", {"message_id": assistant_message.id, "content": delta})
            content = "".join(accumulated)
            with SessionLocal() as stream_db:
                stored_message = stream_db.get(Message, assistant_message_id)
                stored_conversation = stream_db.get(Conversation, conversation_id)
                if stored_message:
                    stored_message.content = content
                    stored_message.status = "completed"
                if stored_conversation:
                    stored_conversation.last_message_at = datetime.now(timezone.utc)
                    stored_conversation.updated_at = datetime.now(timezone.utc)
                stream_db.add(
                    ModelCallLog(
                        user_id=user_id,
                        conversation_id=conversation_id,
                        message_id=assistant_message_id,
                        model_id=model_id,
                        provider=model_provider,
                        completion_tokens=len(content),
                        total_tokens=len(content) + len(payload.content),
                        latency_ms=int((time.perf_counter() - start) * 1000),
                        status="completed",
                    )
                )
                stream_db.commit()
            yield sse(
                "message_end",
                {"message_id": assistant_message_id, "status": "completed", "content": content},
            )
        except Exception as exc:
            with SessionLocal() as stream_db:
                stored_message = stream_db.get(Message, assistant_message_id)
                if stored_message:
                    stored_message.status = "failed"
                    stored_message.error_message = str(exc)
                stream_db.add(
                    ModelCallLog(
                        user_id=user_id,
                        conversation_id=conversation_id,
                        message_id=assistant_message_id,
                        model_id=model_id,
                        provider=model_provider,
                        status="failed",
                        error_message=str(exc),
                    )
                )
                stream_db.commit()
            yield sse(
                "error",
                {"code": "MODEL_CALL_FAILED", "message": "模型调用失败，请稍后重试"},
            )

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/messages/{message_id}/feedback")
def feedback(
    message_id: str,
    payload: FeedbackRequest,
    current_user: User = Depends(get_current_user),
):
    return ok({"message_id": message_id, "rating": payload.rating, "user_id": current_user.id})
