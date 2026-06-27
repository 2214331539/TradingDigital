from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import OperationLog


def write_operation_log(
    db: Session,
    *,
    user_id: Optional[str],
    action: str,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    result: str = "success",
    detail: Optional[str] = None,
):
    db.add(
        OperationLog(
            user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            result=result,
            detail=detail,
        )
    )

