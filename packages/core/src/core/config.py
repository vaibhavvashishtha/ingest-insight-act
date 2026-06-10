from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:54322/postgres"
    redis_url: str = "redis://localhost:6379/0"

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    anthropic_api_key: str = ""
    google_application_credentials: str = ""

    secret_key: str = "change-me"
    environment: str = "development"
    log_level: str = "INFO"

    # Dev test harness — NEVER set in production
    dev_tenant_id: str | None = None
    mock_claude: bool = False

    # Comma-separated list of allowed CORS origins. In dev, defaults to localhost:3000.
    cors_origins: str = "http://localhost:3000"

    # Per-IP rate limits for sensitive endpoints (slowapi format)
    rate_limit_seed: str = "5/hour"
    rate_limit_llm: str = "20/hour"


settings = Settings()
