import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


def uuid_str() -> str:
    return str(uuid.uuid4())


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", String(36), ForeignKey("users.id"), primary_key=True),
    Column("role_id", String(36), ForeignKey("roles.id"), primary_key=True),
    Column("created_at", DateTime(timezone=True), default=now_utc, nullable=False),
)


role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", String(36), ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", String(36), ForeignKey("permissions.id"), primary_key=True),
    Column("created_at", DateTime(timezone=True), default=now_utc, nullable=False),
)


ai_model_roles = Table(
    "ai_model_roles",
    Base.metadata,
    Column("model_id", String(36), ForeignKey("ai_models.id"), primary_key=True),
    Column("role_id", String(36), ForeignKey("roles.id"), primary_key=True),
    Column("created_at", DateTime(timezone=True), default=now_utc, nullable=False),
)


class TimestampMixin:
    created_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc, nullable=False)


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, default=uuid_str)
    name = Column(String(100), nullable=False)
    code = Column(String(64), unique=True, nullable=False)
    status = Column(String(32), default="active", nullable=False)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=uuid_str)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=True)
    username = Column(String(64), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    avatar_url = Column(Text, nullable=True)
    status = Column(String(32), default="active", nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    roles = relationship("Role", secondary=user_roles, back_populates="users")


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id = Column(String(36), primary_key=True, default=uuid_str)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=True)
    name = Column(String(64), nullable=False)
    code = Column(String(64), nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_system = Column(Boolean, default=False, nullable=False)

    users = relationship("User", secondary=user_roles, back_populates="roles")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(String(36), primary_key=True, default=uuid_str)
    module = Column(String(64), nullable=False)
    name = Column(String(100), nullable=False)
    code = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)

    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")


class AiModel(Base, TimestampMixin):
    __tablename__ = "ai_models"

    id = Column(String(36), primary_key=True, default=uuid_str)
    name = Column(String(100), nullable=False)
    provider = Column(String(64), default="openai_compatible", nullable=False)
    model_key = Column(String(128), nullable=False)
    base_url = Column(Text, nullable=False)
    api_key_ref = Column(String(128), nullable=False)
    context_length = Column(Integer, default=128000, nullable=False)
    max_output_tokens = Column(Integer, default=4096, nullable=False)
    default_temperature = Column(Numeric(3, 2), default=0.7, nullable=False)
    support_streaming = Column(Boolean, default=True, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    roles = relationship("Role", secondary=ai_model_roles)


class AssistantPreset(Base, TimestampMixin):
    __tablename__ = "assistant_presets"

    id = Column(String(36), primary_key=True, default=uuid_str)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=False)
    default_model_id = Column(String(36), ForeignKey("ai_models.id"), nullable=True)
    icon = Column(String(64), nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    is_system = Column(Boolean, default=False, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=uuid_str)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=True)
    user_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(64), default="folder", nullable=False)
    color = Column(String(32), nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=uuid_str)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=True)
    user_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    title = Column(String(255), default="新聊天", nullable=False)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=True)
    model_id = Column(String(36), ForeignKey("ai_models.id"), nullable=True)
    assistant_id = Column(String(36), ForeignKey("assistant_presets.id"), nullable=True)
    status = Column(String(32), default="active", nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)
    is_favorited = Column(Boolean, default=False, nullable=False)
    is_temporary = Column(Boolean, default=False, nullable=False)
    message_count = Column(Integer, default=0, nullable=False)
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    messages = relationship("Message", back_populates="conversation", order_by="Message.created_at")


class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=uuid_str)
    conversation_id = Column(String(36), ForeignKey("conversations.id"), index=True, nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    parent_message_id = Column(String(36), ForeignKey("messages.id"), nullable=True)
    role = Column(String(32), nullable=False)
    content = Column(Text, default="", nullable=False)
    status = Column(String(32), default="completed", nullable=False)
    model_id = Column(String(36), ForeignKey("ai_models.id"), nullable=True)
    assistant_id = Column(String(36), ForeignKey("assistant_presets.id"), nullable=True)
    version_group_id = Column(String(36), nullable=True)
    version_index = Column(Integer, default=1, nullable=False)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    error_code = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    conversation = relationship("Conversation", back_populates="messages")


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id = Column(String(36), primary_key=True, default=uuid_str)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    target_type = Column(String(64), nullable=True)
    target_id = Column(String(36), nullable=True)
    ip = Column(String(64), nullable=True)
    user_agent = Column(Text, nullable=True)
    result = Column(String(32), default="success", nullable=False)
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)


class ModelCallLog(Base):
    __tablename__ = "model_call_logs"

    id = Column(String(36), primary_key=True, default=uuid_str)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=True)
    message_id = Column(String(36), ForeignKey("messages.id"), nullable=True)
    model_id = Column(String(36), ForeignKey("ai_models.id"), nullable=True)
    provider = Column(String(64), nullable=False)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    status = Column(String(32), default="completed", nullable=False)
    error_code = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)


class SystemSetting(Base, TimestampMixin):
    __tablename__ = "system_settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    updated_by = Column(String(36), ForeignKey("users.id"), nullable=True)
