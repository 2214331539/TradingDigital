from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ModelOut(BaseModel):
    id: str
    name: str
    provider: str
    model_key: str
    context_length: int
    max_output_tokens: int
    enabled: bool
    is_default: bool


class AssistantOut(BaseModel):
    id: str
    name: str
    description: Optional[str]
    icon: Optional[str]
    default_model_id: Optional[str]


class ProjectOut(BaseModel):
    id: str
    name: str
    description: Optional[str]
    icon: str
    color: Optional[str]
    sort_order: int
    is_archived: bool
    created_at: datetime
    updated_at: datetime


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    icon: str = "folder"
    color: Optional[str] = None
    sort_order: int = 0


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    sort_order: Optional[int] = None
    is_archived: Optional[bool] = None


class MessageOut(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    status: str
    model_id: Optional[str]
    created_at: datetime
    updated_at: datetime


class ConversationOut(BaseModel):
    id: str
    title: str
    project_id: Optional[str]
    model_id: Optional[str]
    assistant_id: Optional[str]
    status: str
    is_archived: bool
    is_favorited: bool
    is_temporary: bool
    message_count: int
    last_message_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationOut):
    messages: List[MessageOut]


class ConversationCreate(BaseModel):
    title: str = "新聊天"
    project_id: Optional[str] = None
    model_id: Optional[str] = None
    assistant_id: Optional[str] = None
    is_temporary: bool = False


class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    project_id: Optional[str] = None
    model_id: Optional[str] = None
    assistant_id: Optional[str] = None
    is_archived: Optional[bool] = None
    is_favorited: Optional[bool] = None


class StreamChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    project_id: Optional[str] = None
    model_id: Optional[str] = None
    assistant_id: Optional[str] = None
    content: str
    temporary: bool = False


class FeedbackRequest(BaseModel):
    rating: str
    reason: Optional[str] = None
    comment: Optional[str] = None
