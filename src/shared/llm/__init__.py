"""
LLM Abstraction Layer for Life OS Multi-Agent System.

This module provides a unified interface for interacting with multiple LLM providers
with automatic fallback support.

Fallback Chain Priority:
1. GLM 4.7 (Zhipu AI) - Primary
2. Kimi K2 (Moonshot AI) - Fallback 1
3. GPT-4o mini (OpenAI) - Fallback 2

Usage:
    # Simple usage with fallback chain
    from shared.llm import LLMFallbackChain, Message

    async with LLMFallbackChain() as chain:
        result = await chain.chat([
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content="Hello!")
        ])
        print(f"Response from {result.provider_used}: {result.response.content}")

    # Or use the convenience function
    from shared.llm import chat_with_fallback, Message

    result = await chat_with_fallback([
        Message(role="user", content="Hello!")
    ])

    # Direct provider access (no fallback)
    from shared.llm import get_provider, Message

    provider = get_provider("zhipu", model="glm-4")
    response = await provider.chat([
        Message(role="user", content="Hello!")
    ])

Environment Variables Required:
    - ZHIPU_API_KEY: API key for Zhipu AI (GLM models)
    - MOONSHOT_API_KEY: API key for Moonshot AI (Kimi models)
    - OPENAI_API_KEY: API key for OpenAI (GPT models)
"""

from .providers import (
    BaseLLMProvider,
    ZhipuProvider,
    MoonshotProvider,
    OpenAIProvider,
    LLMResponse,
    LLMError,
    Message,
    get_provider,
    PROVIDER_REGISTRY,
)

from .fallback import (
    LLMFallbackChain,
    FallbackResult,
    RetryConfig,
    chat_with_fallback,
)

from .config import (
    LLM_CHAIN,
    SETTINGS,
    LLMSettings,
    API_KEY_ENV_VARS,
)


__all__ = [
    # Providers
    "BaseLLMProvider",
    "ZhipuProvider",
    "MoonshotProvider",
    "OpenAIProvider",
    "get_provider",
    "PROVIDER_REGISTRY",
    # Data classes
    "LLMResponse",
    "LLMError",
    "Message",
    # Fallback chain
    "LLMFallbackChain",
    "FallbackResult",
    "RetryConfig",
    "chat_with_fallback",
    # Configuration
    "LLM_CHAIN",
    "SETTINGS",
    "LLMSettings",
    "API_KEY_ENV_VARS",
]


# Version info
__version__ = "1.0.0"
