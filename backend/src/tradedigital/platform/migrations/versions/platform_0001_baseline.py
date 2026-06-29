"""platform baseline (enterprises, iam, audit)

Revision ID: platform_0001_baseline
Revises:
Create Date: 2026-06-29

Branch: platform
"""

from alembic import op
import sqlalchemy as sa

revision = "platform_0001_baseline"
down_revision = None
branch_labels = ("platform",)
depends_on = None


def upgrade() -> None:
    op.create_table(
        "core_enterprises",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_core_enterprises_code", "core_enterprises", ["code"])

    op.create_table(
        "core_app_settings",
        sa.Column("key", sa.String(length=100), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "iam_permissions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("module", sa.String(length=64), nullable=False),
        sa.Column("resource", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "iam_roles",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("enterprise_id", sa.String(length=36), sa.ForeignKey("core_enterprises.id"), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("enterprise_id", "code", name="uq_iam_roles_enterprise_code"),
    )
    op.create_index("ix_iam_roles_enterprise_id", "iam_roles", ["enterprise_id"])

    op.create_table(
        "iam_users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("enterprise_id", sa.String(length=36), sa.ForeignKey("core_enterprises.id"), nullable=False),
        sa.Column("sso_provider", sa.String(length=64), nullable=False),
        sa.Column("sso_subject", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("enterprise_id", "email", name="uq_iam_users_enterprise_email"),
        sa.UniqueConstraint(
            "enterprise_id",
            "sso_provider",
            "sso_subject",
            name="uq_iam_users_enterprise_sso_subject",
        ),
    )
    op.create_index("ix_iam_users_enterprise_id", "iam_users", ["enterprise_id"])
    op.create_index("ix_iam_users_email", "iam_users", ["email"])

    op.create_table(
        "iam_user_roles",
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("iam_users.id"), primary_key=True),
        sa.Column("role_id", sa.String(length=36), sa.ForeignKey("iam_roles.id"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "iam_role_permissions",
        sa.Column("role_id", sa.String(length=36), sa.ForeignKey("iam_roles.id"), primary_key=True),
        sa.Column("permission_id", sa.String(length=36), sa.ForeignKey("iam_permissions.id"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "iam_sso_connections",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("enterprise_id", sa.String(length=36), sa.ForeignKey("core_enterprises.id"), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("issuer_url", sa.Text(), nullable=False),
        sa.Column("client_id", sa.String(length=255), nullable=False),
        sa.Column("client_secret_encrypted", sa.Text(), nullable=False),
        sa.Column("redirect_uri", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_iam_sso_connections_enterprise_id", "iam_sso_connections", ["enterprise_id"])

    op.create_table(
        "iam_auth_states",
        sa.Column("state", sa.String(length=255), primary_key=True),
        sa.Column("enterprise_id", sa.String(length=36), sa.ForeignKey("core_enterprises.id"), nullable=False),
        sa.Column("nonce", sa.String(length=255), nullable=False),
        sa.Column("code_verifier", sa.Text(), nullable=False),
        sa.Column("redirect_after_login", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_iam_auth_states_enterprise_id", "iam_auth_states", ["enterprise_id"])

    op.create_table(
        "iam_sessions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("enterprise_id", sa.String(length=36), sa.ForeignKey("core_enterprises.id"), nullable=False),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("iam_users.id"), nullable=False),
        sa.Column("session_token_hash", sa.String(length=128), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("session_token_hash"),
    )
    op.create_index("ix_iam_sessions_enterprise_id", "iam_sessions", ["enterprise_id"])
    op.create_index("ix_iam_sessions_user_id", "iam_sessions", ["user_id"])
    op.create_index("ix_iam_sessions_session_token_hash", "iam_sessions", ["session_token_hash"])

    op.create_table(
        "audit_operation_logs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("enterprise_id", sa.String(length=36), sa.ForeignKey("core_enterprises.id"), nullable=False),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("iam_users.id"), nullable=True),
        sa.Column("module", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=True),
        sa.Column("resource_id", sa.String(length=36), nullable=True),
        sa.Column("detail_json", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_operation_logs_enterprise_id", "audit_operation_logs", ["enterprise_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_operation_logs_enterprise_id", table_name="audit_operation_logs")
    op.drop_table("audit_operation_logs")
    op.drop_index("ix_iam_sessions_session_token_hash", table_name="iam_sessions")
    op.drop_index("ix_iam_sessions_user_id", table_name="iam_sessions")
    op.drop_index("ix_iam_sessions_enterprise_id", table_name="iam_sessions")
    op.drop_table("iam_sessions")
    op.drop_index("ix_iam_auth_states_enterprise_id", table_name="iam_auth_states")
    op.drop_table("iam_auth_states")
    op.drop_index("ix_iam_sso_connections_enterprise_id", table_name="iam_sso_connections")
    op.drop_table("iam_sso_connections")
    op.drop_table("iam_role_permissions")
    op.drop_table("iam_user_roles")
    op.drop_index("ix_iam_users_email", table_name="iam_users")
    op.drop_index("ix_iam_users_enterprise_id", table_name="iam_users")
    op.drop_table("iam_users")
    op.drop_index("ix_iam_roles_enterprise_id", table_name="iam_roles")
    op.drop_table("iam_roles")
    op.drop_table("iam_permissions")
    op.drop_table("core_app_settings")
    op.drop_index("ix_core_enterprises_code", table_name="core_enterprises")
    op.drop_table("core_enterprises")
