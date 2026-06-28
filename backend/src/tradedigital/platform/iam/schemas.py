from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class EnterpriseOut(BaseModel):
    id: str
    name: str
    code: str
    status: str


class UserOut(BaseModel):
    id: str
    enterprise_id: str
    email: EmailStr
    name: Optional[str]
    avatar_url: Optional[str]
    status: str
    roles: list[str]
    permissions: list[str] = []
    last_login_at: Optional[object]
    created_at: object


class RoleOut(BaseModel):
    id: str
    code: str
    name: str
    description: Optional[str]
    is_system: bool
    permissions: list[str] = []


class PermissionOut(BaseModel):
    id: str
    code: str
    name: str
    module: str
    resource: str
    action: str
    description: Optional[str]


class MeOut(BaseModel):
    user: UserOut
    enterprise: EnterpriseOut
    roles: list[str]
    permissions: list[str]
    isAuthenticated: bool = True


class UserStatusUpdate(BaseModel):
    status: Literal["active", "disabled"]


class UserRolesUpdate(BaseModel):
    role_ids: list[str] = Field(default_factory=list)


class RoleCreate(BaseModel):
    code: str = Field(min_length=2, max_length=36, pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None

    @field_validator("code", "name", mode="before")
    @classmethod
    def strip_required_string(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value


class RoleUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None

    @field_validator("name", mode="before")
    @classmethod
    def strip_optional_name(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value


class RolePermissionsUpdate(BaseModel):
    permission_ids: list[str] = Field(default_factory=list)
