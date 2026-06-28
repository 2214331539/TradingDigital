from sqlalchemy.ext.asyncio import AsyncSession

from tradedigital.apps.knowledge.models import QueryLog
from tradedigital.apps.knowledge.repository import (
    get_accessible_knowledge_base,
    get_accessible_tool,
    list_accessible_knowledge_bases,
)
from tradedigital.apps.knowledge.service import knowledge_base_out, tool_out
from tradedigital.shared.auth_context import AuthContext


class KnowledgeGateway:
    @staticmethod
    async def list_accessible_knowledge_bases(session: AsyncSession, ctx: AuthContext) -> list[dict]:
        rows = await list_accessible_knowledge_bases(session, ctx)
        return [knowledge_base_out(row) for row in rows]

    @staticmethod
    async def query(
        session: AsyncSession,
        ctx: AuthContext,
        *,
        query: str,
        knowledge_base_id: str | None = None,
    ) -> dict:
        kb = None
        if knowledge_base_id:
            kb = await get_accessible_knowledge_base(session, ctx, knowledge_base_id)
            if not kb:
                return {"items": [], "message": "knowledge base unavailable"}
        result = {"items": [], "message": "KnowledgeBase retrieval is not configured yet."}
        session.add(
            QueryLog(
                enterprise_id=ctx.enterprise_id,
                user_id=ctx.user_id,
                knowledge_base_id=kb.id if kb else None,
                query=query,
                result_json=result,
            )
        )
        return result

    @staticmethod
    async def execute_tool(
        session: AsyncSession,
        ctx: AuthContext,
        *,
        tool_code: str,
        payload: dict,
    ) -> dict:
        tool = await get_accessible_tool(session, ctx, tool_code)
        if not tool:
            return {"executed": False, "message": "tool unavailable"}
        return {"executed": False, "tool": tool_out(tool), "payload": payload}

