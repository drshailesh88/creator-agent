"""
Configuration management for Master Router.

Loads settings from environment variables with sensible defaults.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Configuration
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_key: str = Field(default="", alias="MASTER_ROUTER_API_KEY")
    debug: bool = Field(default=False, alias="DEBUG")

    # LLM Configuration
    glm4_api_key: str = Field(default="", alias="GLM4_API_KEY")
    glm4_api_base: str = Field(
        default="https://open.bigmodel.cn/api/paas/v4",
        alias="GLM4_API_BASE"
    )
    glm4_model: str = Field(default="glm-4", alias="GLM4_MODEL")

    claude_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    claude_model: str = Field(default="claude-3-haiku-20240307", alias="CLAUDE_MODEL")

    # Default model preference (glm4 or claude)
    default_llm: str = Field(default="glm4", alias="DEFAULT_LLM")

    # Orchestrator Endpoints
    content_orchestrator_url: str = Field(
        default="http://localhost:8001",
        alias="CONTENT_ORCHESTRATOR_URL"
    )
    business_orchestrator_url: str = Field(
        default="http://localhost:8002",
        alias="BUSINESS_ORCHESTRATOR_URL"
    )
    personal_orchestrator_url: str = Field(
        default="http://localhost:8003",
        alias="PERSONAL_ORCHESTRATOR_URL"
    )

    # Timeouts (in seconds)
    orchestrator_timeout: float = Field(default=60.0, alias="ORCHESTRATOR_TIMEOUT")
    llm_timeout: float = Field(default=30.0, alias="LLM_TIMEOUT")
    health_check_timeout: float = Field(default=5.0, alias="HEALTH_CHECK_TIMEOUT")

    # Routing Configuration
    keyword_confidence_threshold: float = Field(
        default=0.7,
        alias="KEYWORD_CONFIDENCE_THRESHOLD"
    )
    llm_fallback_enabled: bool = Field(default=True, alias="LLM_FALLBACK_ENABLED")

    # Paths
    domains_config_path: Path = Field(
        default=Path(__file__).parent / "domains.yaml",
        alias="DOMAINS_CONFIG_PATH"
    )

    # Clawdbot Personality
    clawdbot_name: str = Field(default="Clawdbot", alias="CLAWDBOT_NAME")
    clawdbot_personality_prompt: str = Field(
        default=(
            "You are Clawdbot, a helpful and friendly AI assistant cat. "
            "You occasionally use cat-related expressions like 'Meow!', 'Purr-fect!', "
            "or 'Let me paw through that for you.' Keep responses helpful and professional "
            "while maintaining a warm, slightly playful cat personality. "
            "Don't overdo the cat references - use them sparingly for charm."
        ),
        alias="CLAWDBOT_PERSONALITY_PROMPT"
    )

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    def get_orchestrator_url(self, domain: str) -> Optional[str]:
        """Get the orchestrator URL for a given domain."""
        urls = {
            "content": self.content_orchestrator_url,
            "business": self.business_orchestrator_url,
            "personal": self.personal_orchestrator_url,
        }
        return urls.get(domain)

    @property
    def is_glm4_configured(self) -> bool:
        """Check if GLM-4 API is configured."""
        return bool(self.glm4_api_key)

    @property
    def is_claude_configured(self) -> bool:
        """Check if Claude API is configured."""
        return bool(self.claude_api_key)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
