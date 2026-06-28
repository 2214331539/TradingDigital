from fastapi import FastAPI

from tradedigital.apps.llm.router import router as llm_router
from tradedigital.apps.knowledge.router import router as kb_router
from tradedigital.platform.audit.router import router as audit_router
from tradedigital.platform.iam.router import router as iam_router
from tradedigital.platform.org.router import router as org_router


def register_routes(app: FastAPI) -> None:
    app.include_router(iam_router, prefix="/api/v1/auth", tags=["Auth"])
    app.include_router(org_router, prefix="/api/v1/platform", tags=["Platform"])
    app.include_router(audit_router, prefix="/api/v1/audit", tags=["Audit"])
    app.include_router(llm_router, prefix="/api/v1/llm", tags=["llm"])
    app.include_router(kb_router, prefix="/api/v1/kb", tags=["KnowledgeBase"])

