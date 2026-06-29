from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from tradedigital.apps.llm.api.deps import require_permission
from tradedigital.apps.llm.api.schemas import (
    ConversationCreate,
    ConversationUpdate,
    EditAndRerunRequest,
    MessageUpdate,
    ProjectCreate,
    ProjectUpdate,
    RegenerateRequest,
    StreamChatRequest,
)
from tradedigital.apps.llm.api.serializers import (
    assistant_out,
    conversation_detail,
    conversation_out,
    message_out,
    model_out,
    project_out,
)
from tradedigital.apps.llm.services import catalog, chat, conversations, projects
from tradedigital.core.database import get_session
from tradedigital.shared.auth_context import AuthContext
from tradedigital.shared.types import ok

router = APIRouter()


@router.get("/models")
async def list_models(
    ctx: AuthContext = Depends(require_permission("llm.model.read")),
    session: AsyncSession = Depends(get_session),
):
    rows = await catalog.list_models(session, ctx)
    return ok([model_out(row) for row in rows])


@router.get("/assistant-presets")
async def list_assistant_presets(
    ctx: AuthContext = Depends(require_permission("llm.preset.read")),
    session: AsyncSession = Depends(get_session),
):
    rows = await catalog.list_presets(session, ctx)
    return ok([assistant_out(row) for row in rows])


@router.get("/projects")
async def list_projects(
    ctx: AuthContext = Depends(require_permission("llm.conversation.read_own")),
    session: AsyncSession = Depends(get_session),
):
    rows = await projects.list_projects(session, ctx)
    return ok([project_out(row) for row in rows])


@router.post("/projects")
async def create_project(
    payload: ProjectCreate,
    ctx: AuthContext = Depends(require_permission("llm.conversation.manage_own")),
    session: AsyncSession = Depends(get_session),
):
    project = await projects.create_project(session, ctx, payload)
    return ok(project_out(project))


@router.patch("/projects/{project_id}")
async def update_project(
    project_id: str,
    payload: ProjectUpdate,
    ctx: AuthContext = Depends(require_permission("llm.conversation.manage_own")),
    session: AsyncSession = Depends(get_session),
):
    project = await projects.update_project(session, ctx, project_id, payload)
    return ok(project_out(project))


@router.get("/conversations")
async def list_conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(80, ge=1, le=100),
    keyword: str = "",
    archived: bool | None = False,
    pinned: bool | None = None,
    ctx: AuthContext = Depends(require_permission("llm.conversation.read_own")),
    session: AsyncSession = Depends(get_session),
):
    rows, total = await conversations.list_conversations(
        session, ctx, page=page, page_size=page_size, keyword=keyword, archived=archived, pinned=pinned
    )
    return ok({"items": [conversation_out(row) for row in rows], "page": page, "page_size": page_size, "total": total})


@router.post("/conversations")
async def create_conversation(
    payload: ConversationCreate,
    ctx: AuthContext = Depends(require_permission("llm.conversation.manage_own")),
    session: AsyncSession = Depends(get_session),
):
    conversation = await conversations.create_conversation(session, ctx, payload)
    return ok(conversation_out(conversation))


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    ctx: AuthContext = Depends(require_permission("llm.conversation.read_own")),
    session: AsyncSession = Depends(get_session),
):
    conversation = await conversations.get_owned_conversation_or_404(session, ctx, conversation_id)
    return ok(conversation_detail(conversation))


@router.patch("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    payload: ConversationUpdate,
    ctx: AuthContext = Depends(require_permission("llm.conversation.manage_own")),
    session: AsyncSession = Depends(get_session),
):
    conversation = await conversations.update_conversation(session, ctx, conversation_id, payload)
    return ok(conversation_out(conversation))


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    ctx: AuthContext = Depends(require_permission("llm.conversation.manage_own")),
    session: AsyncSession = Depends(get_session),
):
    await conversations.delete_conversation(session, ctx, conversation_id)
    return ok({"success": True})


@router.post("/chat/stream")
async def stream_chat(
    payload: StreamChatRequest,
    ctx: AuthContext = Depends(require_permission("llm.chat.use")),
    session: AsyncSession = Depends(get_session),
):
    return await chat.stream_chat(payload, ctx, session)


@router.patch("/messages/{message_id}")
async def update_message(
    message_id: str,
    payload: MessageUpdate,
    ctx: AuthContext = Depends(require_permission("llm.conversation.manage_own")),
    session: AsyncSession = Depends(get_session),
):
    message = await conversations.update_message_feedback(session, ctx, message_id, payload)
    return ok(message_out(message))


@router.post("/chat/regenerate")
async def regenerate(
    payload: RegenerateRequest,
    ctx: AuthContext = Depends(require_permission("llm.chat.use")),
):
    from fastapi import HTTPException, status

    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="重新生成暂未实现")


@router.post("/chat/edit-and-rerun")
async def edit_and_rerun(
    payload: EditAndRerunRequest,
    ctx: AuthContext = Depends(require_permission("llm.chat.use")),
):
    from fastapi import HTTPException, status

    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="编辑并重新运行暂未实现")
