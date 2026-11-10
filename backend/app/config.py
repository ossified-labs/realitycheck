"""Runtime settings, read from environment variables (see .env.example)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    anthropic_model: str = field(default_factory=lambda: os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5"))
    tavily_api_key: str = field(default_factory=lambda: os.getenv("TAVILY_API_KEY", ""))
    database_path: str = field(default_factory=lambda: os.getenv("DATABASE_PATH", "realitycheck.db"))
    cors_origins: list[str] = field(
        default_factory=lambda: os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    )
    # Pipeline knobs
    max_subclaims: int = field(default_factory=lambda: _int("MAX_SUBCLAIMS", 4))
    queries_per_subclaim: int = field(default_factory=lambda: _int("QUERIES_PER_SUBCLAIM", 2))
    results_per_query: int = field(default_factory=lambda: _int("RESULTS_PER_QUERY", 5))
    sources_per_subclaim: int = field(default_factory=lambda: _int("SOURCES_PER_SUBCLAIM", 5))
    max_claim_chars: int = field(default_factory=lambda: _int("MAX_CLAIM_CHARS", 1000))
    rate_limit_per_hour: int = field(default_factory=lambda: _int("RATE_LIMIT_PER_HOUR", 20))


def get_settings() -> Settings:
    return Settings()
