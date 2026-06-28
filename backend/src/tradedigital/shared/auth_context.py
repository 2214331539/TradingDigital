from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AuthContext:
    user_id: str
    enterprise_id: str
    email: str
    name: Optional[str]
    roles: list[str]
    permissions: list[str]

