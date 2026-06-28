from typing import Optional

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    model_id: Optional[str] = None
    assistant_preset_id: Optional[str] = None
    project_id: Optional[str] = None
    temporary: bool = False


class ConversationUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    model_id: Optional[str] = None
    assistant_preset_id: Optional[str] = None
    project_id: Optional[str] = None
    archived: Optional[bool] = None
    pinned: Optional[bool] = None


class StreamChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    model_id: Optional[str] = None
    assistant_preset_id: Optional[str] = None
    project_id: Optional[str] = None
    content: str = Field(min_length=1)
    temporary: bool = False


class RegenerateRequest(BaseModel):
    conversation_id: str
    message_id: str


class EditAndRerunRequest(BaseModel):
    conversation_id: str
    message_id: str
    content: str = Field(min_length=1)


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    color: Optional[str] = Field(default=None, max_length=32)


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    color: Optional[str] = Field(default=None, max_length=32)
    archived: Optional[bool] = None


class MessageUpdate(BaseModel):
    feedback: Optional[str] = Field(default=None, pattern="^(like|dislike)$")
