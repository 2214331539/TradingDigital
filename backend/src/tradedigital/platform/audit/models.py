import uuid

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from tradedigital.core.database import Base
from tradedigital.core.time import utc_now


def uuid_str() -> str:
    return str(uuid.uuid4())


class AuditOperationLog(Base):
    __tablename__ = "audit_operation_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    enterprise_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("core_enterprises.id"), index=True, nullable=False
    )
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("iam_users.id"), nullable=True)
    module: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    detail_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

