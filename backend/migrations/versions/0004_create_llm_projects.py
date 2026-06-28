"""create llm projects

Revision ID: 0004_create_llm_projects
Revises: 0003_create_knowledge_tables
Create Date: 2026-06-28
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_create_llm_projects"
down_revision = "0003_create_knowledge_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_projects",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("enterprise_id", sa.String(length=36), sa.ForeignKey("core_enterprises.id"), nullable=False),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("iam_users.id"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("color", sa.String(length=32), nullable=True),
        sa.Column("archived", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_llm_projects_enterprise_id", "llm_projects", ["enterprise_id"])
    op.create_index("ix_llm_projects_user_id", "llm_projects", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_llm_projects_user_id", table_name="llm_projects")
    op.drop_index("ix_llm_projects_enterprise_id", table_name="llm_projects")
    op.drop_table("llm_projects")
