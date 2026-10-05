from typing import List, Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")

    # Application
    APP_ENV: Literal["development", "production", "test"] = "development"
    LOG_LEVEL: str = "INFO"
    WORKER_CONCURRENCY: int = 2

    # Security
    JWT_SECRET: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    CORS_ORIGINS: List[str] = []

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str

    # LLM
    LLM_PROVIDER: Literal["openai", "gemini"] = "openai"
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    LLM_TIMEOUT: int = 60

    # Object Storage (MinIO / S3)
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = "ai-job-agent"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB

    # Browser
    BROWSER_ENABLED: bool = True
    BROWSER_HEADLESS: bool = True
    BROWSER_TIMEOUT_MS: int = 30000
    BROWSER_NAVIGATION_TIMEOUT_MS: int = 30000
    BROWSER_MAX_SESSIONS: int = 5
    BROWSER_MAX_PAGES: int = 10
    BROWSER_MAX_DOWNLOAD_MB: int = 50
    BROWSER_MAX_UPLOAD_MB: int = 10
    BROWSER_MAX_REDIRECTS: int = 3
    BROWSER_SESSION_TIMEOUT_MINUTES: int = 30
    BROWSER_TRACE_ENABLED: bool = False
    BROWSER_SCREENSHOT_ENABLED: bool = True
    BROWSER_ALLOWED_ORIGINS: List[str] = []

    # Observability
    SENTRY_DSN: Optional[str] = None

    # Matching Configuration
    MATCHING_VERSION: str = "v1"
    MATCH_WEIGHT_SEMANTIC: float = 0.4
    MATCH_WEIGHT_SKILL: float = 0.3
    MATCH_WEIGHT_EXPERIENCE: float = 0.2
    MATCH_WEIGHT_EDUCATION: float = 0.1
    MATCH_WEIGHT_PREFERENCE: float = 0.8
    SEMANTIC_DUPLICATE_THRESHOLD: float = 0.85


settings = Settings()  # type: ignore[call-arg]
