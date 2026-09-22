from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Algorise AI Solutions"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = True
    log_level: str = "INFO"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 1

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://algorise:testpass@localhost:5432/algorise",
        description="PostgreSQL async connection URL",
    )
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_timeout: int = 30

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )
    redis_max_connections: int = 50

    # Security
    secret_key: str = Field(
        default="dev-secret-change-in-production",
        description="Secret key for JWT signing",
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # API Keys (for client authentication)
    api_keys: dict = Field(
        default_factory=lambda: {
            "alg_live_test_key_9981": {"client": "Acme Corp", "tier": "Enterprise", "quota": 50000},
            "alg_demo_client_key_001": {"client": "Starlight Labs", "tier": "Growth", "quota": 10000},
        },
        description="Mapping of API keys to client info",
    )

    # External APIs
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    telegram_bot_token: str | None = None
    telegram_api_id: int | None = None
    telegram_api_hash: str | None = None

    # Observability
    otel_endpoint: str | None = None
    otel_service_name: str = "algorise-ai"
    prometheus_port: int = 9090

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # Facebook Developer App & Meta Graph API
    fb_app_id: str = Field(default="123456789012345", description="Facebook Developer App ID")
    fb_app_secret: str = Field(default="dev_fb_secret_key", description="Facebook Developer App Secret")
    fb_redirect_uri: str = Field(default="http://localhost:8000/api/v1/auth/facebook/callback", description="Facebook OAuth Redirect URI")
    fb_graph_api_version: str = "v19.0"

    # Admin Control Panel
    admin_secret: str = Field(default="algorise_surat_admin_9921", description="Admin panel access key")


@lru_cache
def get_settings() -> Settings:
    return Settings()