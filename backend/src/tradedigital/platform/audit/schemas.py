from typing import Any, Optional

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: str
    enterprise_id: str
    user_id: Optional[str]
    module: str
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    detail_json: Optional[dict[str, Any]]
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: object

