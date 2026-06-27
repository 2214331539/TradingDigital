from typing import List

from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class UserSummary(BaseModel):
    id: str
    username: str
    email: str
    status: str
    roles: List[str]
    permissions: List[str]


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: UserSummary
