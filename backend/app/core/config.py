from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application Settings loaded from environment variables and .env file.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # Project metadata
    PROJECT_NAME: str = "MoTA Scholarship API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = Field(default="development", description="Environment mode")

    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Supabase Configuration
    SUPABASE_URL: str = Field(
        default="",
        description="Supabase Project URL (e.g. https://xyz.supabase.co)"
    )
    SUPABASE_ANON_KEY: str = Field(
        default="",
        description="Supabase Anonymous Public Key"
    )
    SUPABASE_SERVICE_ROLE_KEY: str = Field(
        default="",
        description="Supabase Service Role Privileged Key"
    )

    # JWT Configuration (for standalone token verification if configured)
    JWT_SECRET: str = Field(
        default="",
        description="JWT Secret for token signature verification"
    )
    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="JWT Algorithm"
    )

    # CORS Configuration
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]


# Singleton instance
settings = Settings()
