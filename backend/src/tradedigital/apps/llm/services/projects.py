"""Project (workspace) logic."""

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from tradedigital.apps.llm.api.schemas import ProjectCreate, ProjectUpdate
from tradedigital.apps.llm.domain.models import LlmProject
from tradedigital.apps.llm.repositories import queries
from tradedigital.shared.auth_context import AuthContext


def normalize_project_name(name: str) -> str:
    normalized = name.strip()
    if not normalized:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="项目名称不能为空")
    return normalized[:100]


async def resolve_project_id(session: AsyncSession, ctx: AuthContext, project_id: str | None) -> str | None:
    if not project_id:
        return None
    project = await queries.get_owned_project(session, ctx, project_id)
    if not project or project.archived:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    return project.id


async def list_projects(session: AsyncSession, ctx: AuthContext) -> list[LlmProject]:
    return await queries.list_projects(session, ctx)


async def create_project(session: AsyncSession, ctx: AuthContext, payload: ProjectCreate) -> LlmProject:
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
    return project


async def update_project(
    session: AsyncSession, ctx: AuthContext, project_id: str, payload: ProjectUpdate
) -> LlmProject:
    project = await queries.get_owned_project(session, ctx, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates and updates["name"] is not None:
        updates["name"] = normalize_project_name(updates["name"])
    for key, value in updates.items():
        setattr(project, key, value)
    await session.commit()
    await session.refresh(project)
    return project
