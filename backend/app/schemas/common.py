from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel
from pydantic.generics import GenericModel

T = TypeVar("T")


class ApiResponse(GenericModel, Generic[T]):
    code: str = "OK"
    message: str = "success"
    data: Optional[T] = None


class PageResponse(GenericModel, Generic[T]):
    items: List[T]
    page: int
    page_size: int
    total: int


class ErrorDetail(BaseModel):
    field: Optional[str] = None
    reason: str


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Optional[List[ErrorDetail]] = None


def ok(data: Any = None) -> ApiResponse[Any]:
    return ApiResponse(data=data)

