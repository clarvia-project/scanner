"""Application configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Scanner configuration. All values can be overridden via environment variables."""

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://clarvia.art",
        "https://www.clarvia.art",
        "https://clarvia-aeo-scanner.vercel.app",
    ]

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
        "https://glama.ai",
    ]

    # Stripe (legacy — kept for backward compat)
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id: str = ""

    # Lemon Squeezy (primary payment)
    lemonsqueezy_store_id: str = ""      # e.g. "clarvia"
    lemonsqueezy_variant_id: str = ""    # product variant ID from LS dashboard
    lemonsqueezy_webhook_secret: str = ""

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""

    # Admin API key for write operations (profiles, admin dashboard)
    admin_api_key: str = ""

    # Frontend URL (for Stripe redirects)
    frontend_url: str = "http://localhost:3000"

    # IP hashing secret (for visitor traffic privacy — daily salt generation)
    # If empty, a random ephemeral key is used (hashes won't persist across restarts)
    ip_hash_secret: str = ""

    model_config = {
        "env_prefix": "SCANNER_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
