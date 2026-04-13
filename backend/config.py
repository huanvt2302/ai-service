from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://aiplatform:aiplatform@localhost:5432/aiplatform"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # JWT
    jwt_secret: str = "super-secret-jwt-key"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # LLM
    vllm_base_url: str = "http://localhost:8000"
    embedding_base_url: str = "http://localhost:8000"
    default_chat_model: str = "qwen3.5-plus"
    default_embedding_model: str = "text-embedding-3-small"

    # Ray
    ray_address: str = "ray://localhost:10001"

    # CORS
    allowed_origins: str = "http://localhost:3000"

    # Upload
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 50

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
