"""Module assembly entrypoint.

Keeps wiring in one place so the LLM app can be mounted into the platform today
and extracted into a standalone service later with minimal changes.
"""

from fastapi import FastAPI

from tradedigital.apps.llm.api.routes import router

DEFAULT_PREFIX = "/api/v1/llm"


def register(app: FastAPI, *, prefix: str = DEFAULT_PREFIX) -> None:
    app.include_router(router, prefix=prefix, tags=["llm"])
