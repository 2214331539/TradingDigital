from sqlalchemy import and_, exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from tradedigital.apps.knowledge.models import KnowledgeBase, Tool, kb_role_grants, kb_tool_role_grants
from tradedigital.shared.auth_context import AuthContext


def knowledge_access_clause(ctx: AuthContext):
    return or_(
        ~exists().where(kb_role_grants.c.knowledge_base_id == KnowledgeBase.id),
        exists().where(
            and_(
                kb_role_grants.c.knowledge_base_id == KnowledgeBase.id,
                kb_role_grants.c.role_id.in_(ctx.role_ids),
            )
        ),
    )


async def list_accessible_knowledge_bases(
    session: AsyncSession, ctx: AuthContext
) -> list[KnowledgeBase]:
    rows = await session.scalars(
        select(KnowledgeBase)
        .where(
            KnowledgeBase.enterprise_id == ctx.enterprise_id,
            KnowledgeBase.status != "deleted",
            knowledge_access_clause(ctx),
        )
        .order_by(KnowledgeBase.updated_at.desc())
    )
    return rows.all()


async def get_accessible_knowledge_base(
    session: AsyncSession, ctx: AuthContext, kb_id: str
) -> KnowledgeBase | None:
    return await session.scalar(
        select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.enterprise_id == ctx.enterprise_id,
            KnowledgeBase.status != "deleted",
            knowledge_access_clause(ctx),
        )
    )


async def get_accessible_tool(session: AsyncSession, ctx: AuthContext, tool_code: str) -> Tool | None:
    return await session.scalar(
        select(Tool).where(
            Tool.enterprise_id == ctx.enterprise_id,
            Tool.code == tool_code,
            Tool.enabled.is_(True),
            or_(
                ~exists().where(kb_tool_role_grants.c.tool_id == Tool.id),
                exists().where(
                    and_(
                        kb_tool_role_grants.c.tool_id == Tool.id,
                        kb_tool_role_grants.c.role_id.in_(ctx.role_ids),
                    )
                ),
            ),
        )
    )

