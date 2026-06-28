from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

KnowledgeBaseType = Literal["api_docs", "documents", "database", "mixed"]
KnowledgeBaseStatus = Literal["active", "disabled", "deleted"]


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    type: KnowledgeBaseType = "documents"

    @field_validator("name", mode="before")
    @classmethod
    def strip_required_name(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value


class KnowledgeBaseUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = None
    type: Optional[KnowledgeBaseType] = None
    status: Optional[KnowledgeBaseStatus] = None

    @field_validator("name", mode="before")
    @classmethod
    def strip_optional_name(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value


class KnowledgeBaseRolesUpdate(BaseModel):
    role_ids: list[str] = Field(default_factory=list)


class KnowledgeQueryRequest(BaseModel):
    query: str = Field(min_length=1)
    knowledge_base_id: Optional[str] = None


class ToolExecuteRequest(BaseModel):
    tool_code: str = Field(min_length=1)
    payload: dict = Field(default_factory=dict)
