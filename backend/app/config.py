"""Application configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Scanner configuration. All values can be overridden via environment variables."""

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # HTTP probing
    http_timeout: float = 10.0
    latency_samples: int = 5
    latency_delay: float = 0.2  # seconds between latency probes

    # Cache
    cache_ttl_seconds: int = 86400  # 24 hours

    # MCP registry URLs
    mcp_registry_urls: list[str] = [
        "https://mcp.so",
        "https://smithery.ai",
    ]

    model_config = {"env_prefix": "SCANNER_"}


settings = Settings()
