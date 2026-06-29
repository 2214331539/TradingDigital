import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, Numeric, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tradedigital.core.database import Base
from tradedigital.core.time import utc_now


def uuid_str() -> str:
    return str(uuid.uuid4())


llm_model_role_grants = Table(
    "llm_model_role_grants",
    Base.metadata,
    Column("model_id", String(36), ForeignKey("llm_models.id"), primary_key=True),
    Column("role_id", String(36), ForeignKey("iam_roles.id"), primary_key=True),
    Column("created_at", DateTime(timezone=True), default=utc_now, nullable=False),
)


class TimestampMixin:
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class LlmModel(Base, TimestampMixin):
    __tablename__ = "llm_models"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    provider_code: Mapped[str] = mapped_column(String(64), nullable=False)
    model_key: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(32), default="chat", nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    api_key_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    context_length: Mapped[int] = mapped_column(Integer, default=128000, nullable=False)
    max_output_tokens: Mapped[int] = mapped_column(Integer, default=4096, nullable=False)
    default_temperature: Mapped[object] = mapped_column(Numeric(3, 2), default=0.7, nullable=False)
    support_streaming: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class AssistantPreset(Base, TimestampMixin):
    __tablename__ = "llm_assistant_presets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    enterprise_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("core_enterprises.id"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[str] = mapped_column(String(32), default="enterprise", nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("iam_users.id"), nullable=True)
    default_model_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("llm_models.id"), nullable=True)
    icon: Mapped[str | None] = mapped_column(String(64), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class LlmProject(Base, TimestampMixin):
    __tablename__ = "llm_projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    enterprise_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("core_enterprises.id"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("iam_users.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    color: Mapped[str | None] = mapped_column(String(32), nullable=True)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Conversation(Base, TimestampMixin):
    __tablename__ = "llm_conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    enterprise_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("core_enterprises.id"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("iam_users.id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="新聊天", nullable=False)
    assistant_preset_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("llm_assistant_presets.id"), nullable=True
    )
    model_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("llm_models.id"), nullable=True)
    project_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("llm_projects.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    temporary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_message_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Loaded on demand only: list endpoints never touch ``messages`` and would
    # otherwise eagerly fetch every message of every conversation in the page.
    # Code paths that need messages (e.g. get_owned_conversation) opt in with an
    # explicit selectinload(Conversation.messages).
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="conversation", order_by="Message.created_at", lazy="select"
    )


class Message(Base, TimestampMixin):
    __tablename__ = "llm_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    enterprise_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("core_enterprises.id"), index=True, nullable=False
    )
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("llm_conversations.id"), index=True, nullable=False
    )
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("iam_users.id"), nullable=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="completed", nullable=False)
    model_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("llm_models.id"), nullable=True)
    deleted_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)

    conversation: Mapped[Conversation] = relationship("Conversation", back_populates="messages")


class LlmModelCallLog(Base):
    __tablename__ = "llm_model_call_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    enterprise_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("core_enterprises.id"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("iam_users.id"), index=True, nullable=False)
    conversation_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("llm_conversations.id"), nullable=True
    )
    model_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("llm_models.id"), nullable=True)
    provider_code: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="completed", nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
