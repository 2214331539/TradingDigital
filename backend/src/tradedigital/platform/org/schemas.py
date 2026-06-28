from pydantic import BaseModel


class EnterpriseOut(BaseModel):
    id: str
    name: str
    code: str
    status: str

