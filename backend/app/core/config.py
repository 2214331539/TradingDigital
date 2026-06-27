from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "ChatAI"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./chatai.db"
    jwt_secret: str = "change-this-secret-before-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    cors_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    class Config:
        env_file = ".env"
        env_prefix = "CHATAI_"


@lru_cache
def get_settings() -> Settings:
    return Settings()
