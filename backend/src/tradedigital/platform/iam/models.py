import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Table, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tradedigital.core.database import Base
from tradedigital.core.time import utc_now


def uuid_str() -> str:
    return str(uuid.uuid4())


iam_user_roles = Table(
    "iam_user_roles",
    Base.metadata,
    Column("user_id", String(36), ForeignKey("iam_users.id"), primary_key=True),
    Column("role_id", String(36), ForeignKey("iam_roles.id"), primary_key=True),
    Column("created_at", DateTime(timezone=True), default=utc_now, nullable=False),
)


iam_role_permissions = Table(
    "iam_role_permissions",
    Base.metadata,
    Column("role_id", String(36), ForeignKey("iam_roles.id"), primary_key=True),
    Column("permission_id", String(36), ForeignKey("iam_permissions.id"), primary_key=True),
    Column("created_at", DateTime(timezone=True), default=utc_now, nullable=False),
)


class TimestampMixin:
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class User(Base, TimestampMixin):
    __tablename__ = "iam_users"
    __table_args__ = (
        UniqueConstraint("enterprise_id", "email", name="uq_iam_users_enterprise_email"),
        UniqueConstraint(
            "enterprise_id",
            "sso_provider",
            "sso_subject",
            name="uq_iam_users_enterprise_sso_subject",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    enterprise_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("core_enterprises.id"), index=True, nullable=False
    )
    sso_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    sso_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    last_login_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)

    roles: Mapped[list["Role"]] = relationship(
        "Role", secondary=iam_user_roles, back_populates="users", lazy="selectin"
    )


class Role(Base, TimestampMixin):
    __tablename__ = "iam_roles"
    __table_args__ = (UniqueConstraint("enterprise_id", "code", name="uq_iam_roles_enterprise_code"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    enterprise_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("core_enterprises.id"), index=True, nullable=False
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    users: Mapped[list[User]] = relationship(
        "User", secondary=iam_user_roles, back_populates="roles", lazy="selectin"
    )
    permissions: Mapped[list["Permission"]] = relationship(
        "Permission", secondary=iam_role_permissions, back_populates="roles", lazy="selectin"
    )


class Permission(Base):
    __tablename__ = "iam_permissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    module: Mapped[str] = mapped_column(String(64), nullable=False)
    resource: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    roles: Mapped[list[Role]] = relationship(
        "Role", secondary=iam_role_permissions, back_populates="permissions", lazy="selectin"
    )


class SSOConnection(Base, TimestampMixin):
    __tablename__ = "iam_sso_connections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    enterprise_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("core_enterprises.id"), index=True, nullable=False
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    issuer_url: Mapped[str] = mapped_column(Text, nullable=False)
    client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    client_secret_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    redirect_uri: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AuthState(Base):
    __tablename__ = "iam_auth_states"

    state: Mapped[str] = mapped_column(String(255), primary_key=True)
    enterprise_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("core_enterprises.id"), index=True, nullable=False
    )
    nonce: Mapped[str] = mapped_column(String(255), nullable=False)
    code_verifier: Mapped[str] = mapped_column(Text, nullable=False)
    redirect_after_login: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class Session(Base, TimestampMixin):
    __tablename__ = "iam_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    enterprise_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("core_enterprises.id"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("iam_users.id"), index=True, nullable=False)
    session_token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expires_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
