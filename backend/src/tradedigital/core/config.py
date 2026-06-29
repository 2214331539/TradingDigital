from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "TradeDigital"
    app_env: str = "development"
    debug: bool = True

    frontend_url: str = "http://127.0.0.1:5273"
    backend_url: str = "http://127.0.0.1:8000"
    database_url: str = "postgresql+asyncpg://tradedigital:tradedigital@127.0.0.1:5432/tradedigital"

    session_cookie_name: str = "td_session"
    session_secret: str = "change-this-in-development"
    session_expire_hours: int = 24

    oidc_provider: str = "keycloak"
    oidc_issuer_url: str = "http://127.0.0.1:8080/realms/tradedigital"
    oidc_client_id: str = "tradedigital-web"
    oidc_client_secret: str = "change-this-client-secret"
    oidc_redirect_uri: str = "http://127.0.0.1:8000/api/v1/auth/sso/callback"

    default_enterprise_code: str = "default"
    default_login_redirect: str = "/app"

    default_model_display_name: str = "Gemini 3.5 Flash"
    default_model_provider_code: str = "openai_compatible"
    default_model_key: str = "gemini-3.5-flash"
    default_model_base_url: str = "https://aicenter.thyseed.com/v1"
    default_model_api_key_ref: str = "AICENTER_API_KEY"
    default_model_support_streaming: bool = False
    default_model_context_length: int = 128000
    default_model_max_output_tokens: int = 4096
    default_model_temperature: float = 0.7

    cors_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:5273", "http://127.0.0.1:5273"]
    )

    @property
    def cookie_secure(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
