from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from tradedigital.apps.knowledge.gateway import KnowledgeGateway
from tradedigital.apps.knowledge.models import KnowledgeBase, kb_role_grants
from tradedigital.apps.knowledge.repository import get_accessible_knowledge_base
from tradedigital.apps.knowledge.schemas import (
    KnowledgeBaseCreate,
    KnowledgeBaseRolesUpdate,
    KnowledgeBaseUpdate,
    KnowledgeQueryRequest,
    ToolExecuteRequest,
)
from tradedigital.apps.knowledge.service import knowledge_base_out
from tradedigital.core.database import get_session
from tradedigital.platform.audit.service import write_context_audit_log
from tradedigital.platform.iam.deps import require_permission
from tradedigital.platform.iam.models import Role
from tradedigital.shared.auth_context import AuthContext
from tradedigital.shared.types import ok

router = APIRouter()


def ordered_unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


@router.get("/knowledge-bases")
async def knowledge_bases(
    ctx: AuthContext = Depends(require_permission("kb.knowledge_base.read")),
    session: AsyncSession = Depends(get_session),
):
    return ok(await KnowledgeGateway.list_accessible_knowledge_bases(session, ctx))


@router.post("/knowledge-bases")
async def create_knowledge_base(
    payload: KnowledgeBaseCreate,
    ctx: AuthContext = Depends(require_permission("kb.knowledge_base.manage")),
    session: AsyncSession = Depends(get_session),
):
    row = KnowledgeBase(
        enterprise_id=ctx.enterprise_id,
        name=payload.name.strip(),
        description=payload.description,
        type=payload.type,
        created_by=ctx.user_id,
    )
    session.add(row)
    await session.flush()
    await write_context_audit_log(
        session,
        ctx,
        module="kb",
        action="kb.knowledge_base.create",
        resource_type="kb_knowledge_base",
        resource_id=row.id,
    )
    await session.commit()
    await session.refresh(row)
    return ok(knowledge_base_out(row))


@router.get("/knowledge-bases/{kb_id}")
async def knowledge_base_detail(
    kb_id: str,
    ctx: AuthContext = Depends(require_permission("kb.knowledge_base.read")),
    session: AsyncSession = Depends(get_session),
):
    row = await get_accessible_knowledge_base(session, ctx, kb_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")
    return ok(knowledge_base_out(row))


@router.patch("/knowledge-bases/{kb_id}")
async def update_knowledge_base(
    kb_id: str,
    payload: KnowledgeBaseUpdate,
    ctx: AuthContext = Depends(require_permission("kb.knowledge_base.manage")),
    session: AsyncSession = Depends(get_session),
):
    row = await session.scalar(
        select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id, KnowledgeBase.enterprise_id == ctx.enterprise_id
        )
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")
    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates:
        if updates["name"] is None or not updates["name"].strip():
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="知识库名称不能为空")
        updates["name"] = updates["name"].strip()
    for key, value in updates.items():
        setattr(row, key, value)
    await write_context_audit_log(
        session,
        ctx,
        module="kb",
        action="kb.knowledge_base.update",
        resource_type="kb_knowledge_base",
        resource_id=row.id,
    )
    await session.commit()
    await session.refresh(row)
    return ok(knowledge_base_out(row))


@router.patch("/knowledge-bases/{kb_id}/roles")
async def update_knowledge_base_roles(
    kb_id: str,
    payload: KnowledgeBaseRolesUpdate,
    ctx: AuthContext = Depends(require_permission("kb.knowledge_base.manage")),
    session: AsyncSession = Depends(get_session),
):
    row = await session.scalar(
        select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id, KnowledgeBase.enterprise_id == ctx.enterprise_id
        )
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")
    requested_role_ids = ordered_unique(payload.role_ids)
    if requested_role_ids:
        existing_role_ids = (
            await session.scalars(
                select(Role.id).where(
                    Role.enterprise_id == ctx.enterprise_id,
                    Role.id.in_(requested_role_ids),
                )
            )
        ).all()
        existing_role_id_set = set(existing_role_ids)
        missing_role_ids = [
            role_id for role_id in requested_role_ids if role_id not in existing_role_id_set
        ]
        if missing_role_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role not found: {', '.join(missing_role_ids)}",
            )
    await session.execute(delete(kb_role_grants).where(kb_role_grants.c.knowledge_base_id == kb_id))
    if requested_role_ids:
        await session.execute(
            insert(kb_role_grants),
            [{"knowledge_base_id": kb_id, "role_id": role_id} for role_id in requested_role_ids],
        )
    await write_context_audit_log(
        session,
        ctx,
        module="kb",
        action="kb.knowledge_base.roles.update",
        resource_type="kb_knowledge_base",
        resource_id=kb_id,
        detail_json={"role_ids": requested_role_ids},
    )
    await session.commit()
    return ok({"success": True})


@router.post("/query")
async def query(
    payload: KnowledgeQueryRequest,
    ctx: AuthContext = Depends(require_permission("kb.query.use")),
    session: AsyncSession = Depends(get_session),
):
    query_text = payload.query.strip()
    if not query_text:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="查询内容不能为空")
    result = await KnowledgeGateway.query(
        session,
        ctx,
        query=query_text,
        knowledge_base_id=payload.knowledge_base_id,
    )
    await write_context_audit_log(
        session,
        ctx,
        module="kb",
        action="kb.query",
        resource_type="kb_knowledge_base",
        resource_id=payload.knowledge_base_id,
    )
    await session.commit()
    return ok(result)


@router.post("/tools/execute")
async def execute_tool(
    payload: ToolExecuteRequest,
    ctx: AuthContext = Depends(require_permission("kb.tool.execute")),
    session: AsyncSession = Depends(get_session),
):
    tool_code = payload.tool_code.strip()
    if not tool_code:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="工具编码不能为空")
    result = await KnowledgeGateway.execute_tool(
        session,
        ctx,
        tool_code=tool_code,
        payload=payload.payload,
    )
    await write_context_audit_log(
        session,
        ctx,
        module="kb",
        action="kb.tool.execute",
        resource_type="kb_tool",
        resource_id=tool_code,
    )
    await session.commit()
    return ok(result)
