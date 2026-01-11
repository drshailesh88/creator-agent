"""LLM configuration for the Life OS multi-agent system.

Defines the fallback chain priority:
1. GLM 4.7 (Zhipu AI) - Primary
2. Kimi K2 (Moonshot AI) - Fallback 1
3. GPT-4o mini (OpenAI) - Fallback 2
"""

from typing import TypedDict, List, Optional
from dataclasses import dataclass


class ProviderConfig(TypedDict):
    """Configuration for a single LLM provider."""
    provider: str
    model: str
    priority: int
    api_base: Optional[str]
    timeout: int
    max_retries: int


# LLM fallback chain configuration
LLM_CHAIN: List[ProviderConfig] = [
    {
        "provider": "zhipu",
        "model": "glm-4",
        "priority": 1,
        "api_base": "https://open.bigmodel.cn/api/paas/v4",
        "timeout": 60,
        "max_retries": 2,
    },
    {
        "provider": "moonshot",
        "model": "kimi-k2",
        "priority": 2,
        "api_base": "https://api.moonshot.cn/v1",
        "timeout": 60,
        "max_retries": 2,
    },
    {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "priority": 3,
        "api_base": "https://api.openai.com/v1",
        "timeout": 60,
        "max_retries": 2,
    },
]


@dataclass
class LLMSettings:
    """Global LLM settings."""
    default_temperature: float = 0.7
    default_max_tokens: int = 4096
    default_top_p: float = 0.95
    retry_delay_base: float = 1.0  # Base delay for exponential backoff
    retry_delay_max: float = 30.0  # Maximum retry delay
    log_provider_usage: bool = True


# Global settings instance
SETTINGS = LLMSettings()


# Environment variable names for API keys
API_KEY_ENV_VARS = {
    "zhipu": "ZHIPU_API_KEY",
    "moonshot": "MOONSHOT_API_KEY",
    "openai": "OPENAI_API_KEY",
}
