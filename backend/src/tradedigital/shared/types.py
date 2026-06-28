from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: str = "OK"
    message: str = "success"
    data: Optional[T] = None


def ok(data: Any = None) -> ApiResponse[Any]:
    return ApiResponse(data=data)
