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
        default="sqlite+aiosqlite:///./algorise_prod.db",
        description="Async SQLAlchemy database connection URL (SQLite default, PostgreSQL supported)",
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
            "alg_live_test_key_9981": {
                "client": "Acme Corp",
                "tier": "Enterprise Tier",
                "quota": 50000,
                "role": "admin",
                "scopes": [
                    "quarantine:read",
                    "quarantine:write",
                    "blast_radius:read",
                    "incident:heal",
                    "usage:read",
                    "admin:*",
                ],
            },
            "alg_demo_client_key_001": {
                "client": "Starlight Labs",
                "tier": "Growth Tier",
                "quota": 10000,
                "role": "developer",
                "scopes": [
                    "quarantine:read",
                    "quarantine:write",
                    "blast_radius:read",
                    "usage:read",
                ],
            },
            "alg_readonly_key_002": {
                "client": "Audit Viewer",
                "tier": "Viewer Tier",
                "quota": 5000,
                "role": "viewer",
                "scopes": ["quarantine:read", "blast_radius:read", "usage:read"],
            },
        },
        description="Mapping of API keys to client info, role and RBAC scopes",
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

    # Operational flags
    migrate_on_start: bool = Field(
        default=True,
        description="Run Base.metadata.create_all() during startup. Disable in production where "
        "migrations are executed by a dedicated pre-deploy job.",
    )
    redis_required: bool = Field(
        default=False,
        description="Treat Redis as a readiness-critical dependency. Enable in production.",
    )
    enable_embedded_scheduler: bool = Field(
        default=True,
        description="Run the in-process Facebook sweep loop inside this process. Disable on API "
        "replicas so scheduled work is executed exactly once by the dedicated scheduler workload.",
    )
    cors_allowed_origins: str = Field(
        default="",
        description="Comma-separated exact origins allowed by CORS. Empty falls back to the built-in profile.",
    )
    enforce_production_security: bool = Field(
        default=False,
        description="Make insecure production configuration fatal at startup. Enable once real "
        "credentials are provisioned in the deployment environment.",
    )

    def validate_production_safety(self) -> None:
        """Validates that production environment does not use insecure development defaults.

        In production this reports every insecure default loudly. It is fatal
        only when ENFORCE_PRODUCTION_SECURITY is enabled, so a deployment
        cannot be taken down by a configuration gap while the operator is
        still rotating credentials.
        """
        if self.environment.lower() not in ("production", "prod"):
            return

        insecure_defaults = []
        if self.secret_key == "dev-secret-change-in-production":
            insecure_defaults.append("SECRET_KEY is set to default 'dev-secret-change-in-production'")
        if self.admin_secret == "algorise_surat_admin_9921":
            insecure_defaults.append("ADMIN_SECRET is set to default 'algorise_surat_admin_9921'")
        if self.fb_app_secret == "dev_fb_secret_key":
            insecure_defaults.append("FB_APP_SECRET is set to default 'dev_fb_secret_key'")
        if not self.migrate_on_start:
            insecure_defaults.append(
                "MIGRATE_ON_START is disabled; the pre-deploy migration job owns schema changes"
            )

        if not insecure_defaults:
            return

        message = (
            "CRITICAL PRODUCTION SECURITY VIOLATION: insecure default configuration detected: "
            + "; ".join(insecure_defaults)
            + ". Set the corresponding environment variables."
        )

        if self.enforce_production_security:
            raise ValueError(message)

        print(f"WARNING: {message}")



@lru_cache
def get_settings() -> Settings:
    return Settings()