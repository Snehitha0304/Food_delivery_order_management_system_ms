from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SERVICE_NAME: str = "delivery-service"
    PROJECT_NAME: str = "Food Delivery - Delivery & Dispatch Service"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    SERVICE_PORT: int = 8004

    # Dedicated Delivery Service Database
    DATABASE_URL: str = "sqlite:///../../databases/delivery_service.db"

    # Downstream Microservice URLs
    USER_SERVICE_URL: str = "http://127.0.0.1:8001"
    ORDER_SERVICE_URL: str = "http://127.0.0.1:8003"
    HTTP_TIMEOUT_SECONDS: float = 10.0

    # Security / JWT
    JWT_SECRET_KEY: str = "9b47e954c7d0d08bfad3c14c53880629acbd3e2e0573e8eec80f55c5dfb51234"
    JWT_ALGORITHM: str = "HS256"
    INTERNAL_API_KEY: str = "fd-internal-service-secret-key-2026"

    CORS_ORIGINS: List[str] = ["*"]
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        return ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
