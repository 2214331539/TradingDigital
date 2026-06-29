"""add pinned to llm projects

Revision ID: 0005_add_project_pinned
Revises: 0004_create_llm_projects
Create Date: 2026-06-29
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_add_project_pinned"
down_revision = "0004_create_llm_projects"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "llm_projects",
        sa.Column("pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("llm_projects", "pinned", server_default=None)


def downgrade() -> None:
    op.drop_column("llm_projects", "pinned")
