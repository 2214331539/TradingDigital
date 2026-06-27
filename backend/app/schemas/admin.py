from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class RoleOut(BaseModel):
    id: str
    name: str
    code: str
    description: Optional[str]
    is_system: bool


class PermissionOut(BaseModel):
    id: str
    module: str
    name: str
    code: str
    description: Optional[str]


class AdminUserOut(BaseModel):
    id: str
    username: str
    email: str
    status: str
    roles: List[str]
    last_login_at: Optional[datetime]
    created_at: datetime


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role_ids: List[str]
    status: str = "active"


class UserUpdate(BaseModel):
    username: Optional[str] = None
    status: Optional[str] = None
    role_ids: Optional[List[str]] = None


class ModelCreate(BaseModel):
    name: str
    provider: str = "openai_compatible"
    model_key: str
    base_url: str
    api_key_ref: str
    context_length: int = 128000
    max_output_tokens: int = 4096
    default_temperature: float = 0.7
    support_streaming: bool = True
    enabled: bool = True
    allowed_role_ids: List[str] = []


class ModelUpdate(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    model_key: Optional[str] = None
    base_url: Optional[str] = None
    api_key_ref: Optional[str] = None
    context_length: Optional[int] = None
    max_output_tokens: Optional[int] = None
    default_temperature: Optional[float] = None
    support_streaming: Optional[bool] = None
    enabled: Optional[bool] = None
    allowed_role_ids: Optional[List[str]] = None
