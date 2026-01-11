"""LLM fallback chain implementation for the Life OS multi-agent system.

Implements a cascading fallback strategy:
1. Try primary provider (GLM 4.7 - Zhipu AI)
2. If fails, try fallback 1 (Kimi K2 - Moonshot AI)
3. If fails, try fallback 2 (GPT-4o mini - OpenAI)
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, AsyncGenerator
from datetime import datetime

from .config import LLM_CHAIN, SETTINGS, ProviderConfig
from .providers import (
    BaseLLMProvider,
    LLMResponse,
    LLMError,
    Message,
    get_provider,
)


logger = logging.getLogger(__name__)


@dataclass
class FallbackResult:
    """Result from the fallback chain execution."""
    response: LLMResponse
    provider_used: str
    model_used: str
    attempts: int
    fallback_chain: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    total_time: float = 0.0


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 2
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt using exponential backoff."""
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        return delay


class LLMFallbackChain:
    """
    Manages LLM provider fallback chain with retry logic.

    Usage:
        chain = LLMFallbackChain()
        result = await chain.chat(messages)
        print(f"Response from {result.provider_used}: {result.response.content}")
    """

    def __init__(
        self,
        chain_config: Optional[List[ProviderConfig]] = None,
        retry_config: Optional[RetryConfig] = None,
    ):
        self.chain_config = chain_config or LLM_CHAIN
        self.retry_config = retry_config or RetryConfig(
            base_delay=SETTINGS.retry_delay_base,
            max_delay=SETTINGS.retry_delay_max,
        )
        self._providers: Dict[str, BaseLLMProvider] = {}
        self._initialize_providers()

    def _initialize_providers(self) -> None:
        """Initialize providers from chain configuration."""
        # Sort by priority
        sorted_config = sorted(self.chain_config, key=lambda x: x["priority"])

        for config in sorted_config:
            provider_name = config["provider"]
            try:
                provider = get_provider(
                    provider_name=provider_name,
                    model=config["model"],
                    api_base=config.get("api_base"),
                    timeout=config.get("timeout", 60),
                    max_retries=config.get("max_retries", 2),
                )
                self._providers[provider_name] = provider
                logger.info(f"Initialized provider: {provider_name} ({config['model']})")
            except LLMError as e:
                # Log but don't fail - provider may not have API key configured
                logger.warning(f"Could not initialize provider {provider_name}: {e}")

    def get_provider_order(self) -> List[str]:
        """Get the ordered list of providers by priority."""
        sorted_config = sorted(self.chain_config, key=lambda x: x["priority"])
        return [c["provider"] for c in sorted_config]

    async def _try_provider(
        self,
        provider_name: str,
        messages: List[Message],
        temperature: float = None,
        max_tokens: int = None,
        top_p: float = None,
        **kwargs
    ) -> LLMResponse:
        """
        Try a single provider with retry logic.

        Raises LLMError if all retries fail.
        """
        if provider_name not in self._providers:
            raise LLMError(
                provider=provider_name,
                model="unknown",
                message=f"Provider '{provider_name}' not initialized"
            )

        provider = self._providers[provider_name]
        last_error: Optional[LLMError] = None

        for attempt in range(self.retry_config.max_retries + 1):
            try:
                if attempt > 0:
                    delay = self.retry_config.get_delay(attempt - 1)
                    logger.info(f"Retrying {provider_name} after {delay:.1f}s (attempt {attempt + 1})")
                    await asyncio.sleep(delay)

                response = await provider.chat(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=top_p,
                    **kwargs
                )
                return response

            except LLMError as e:
                last_error = e
                logger.warning(f"Provider {provider_name} failed (attempt {attempt + 1}): {e}")

                # Don't retry on certain status codes
                if e.status_code in (401, 403):  # Auth errors
                    break

            except Exception as e:
                last_error = LLMError(
                    provider=provider_name,
                    model=provider.model,
                    message=str(e)
                )
                logger.warning(f"Provider {provider_name} failed (attempt {attempt + 1}): {e}")

        raise last_error or LLMError(
            provider=provider_name,
            model=provider.model,
            message="All retry attempts failed"
        )

    async def chat(
        self,
        messages: List[Message],
        temperature: float = None,
        max_tokens: int = None,
        top_p: float = None,
        **kwargs
    ) -> FallbackResult:
        """
        Execute chat completion with fallback chain.

        Tries each provider in priority order until one succeeds.

        Args:
            messages: List of chat messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            top_p: Top-p sampling parameter
            **kwargs: Additional provider-specific parameters

        Returns:
            FallbackResult with the response and metadata

        Raises:
            LLMError: If all providers fail
        """
        start_time = datetime.utcnow()
        provider_order = self.get_provider_order()
        errors: List[str] = []
        attempts = 0
        fallback_chain: List[str] = []

        for provider_name in provider_order:
            if provider_name not in self._providers:
                logger.warning(f"Skipping unconfigured provider: {provider_name}")
                errors.append(f"{provider_name}: not configured")
                continue

            fallback_chain.append(provider_name)
            attempts += 1

            try:
                logger.info(f"Trying provider: {provider_name}")
                response = await self._try_provider(
                    provider_name=provider_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=top_p,
                    **kwargs
                )

                total_time = (datetime.utcnow() - start_time).total_seconds()

                if SETTINGS.log_provider_usage:
                    logger.info(
                        f"LLM request completed: provider={provider_name}, "
                        f"model={response.model}, attempts={attempts}, "
                        f"time={total_time:.2f}s"
                    )

                return FallbackResult(
                    response=response,
                    provider_used=provider_name,
                    model_used=response.model,
                    attempts=attempts,
                    fallback_chain=fallback_chain,
                    errors=errors,
                    total_time=total_time,
                )

            except LLMError as e:
                error_msg = f"{provider_name}: {e.message}"
                errors.append(error_msg)
                logger.warning(f"Provider failed, trying next: {error_msg}")
                continue

        # All providers failed
        total_time = (datetime.utcnow() - start_time).total_seconds()
        error_summary = "; ".join(errors)

        raise LLMError(
            provider="fallback_chain",
            model="all",
            message=f"All providers failed after {attempts} attempts ({total_time:.2f}s): {error_summary}"
        )

    async def chat_stream(
        self,
        messages: List[Message],
        temperature: float = None,
        max_tokens: int = None,
        top_p: float = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Execute streaming chat completion with fallback chain.

        Note: Streaming does not support mid-stream fallback.
        If the primary provider fails during streaming, an error is raised.

        For robust streaming, consider using non-streaming mode.
        """
        provider_order = self.get_provider_order()
        errors: List[str] = []

        for provider_name in provider_order:
            if provider_name not in self._providers:
                errors.append(f"{provider_name}: not configured")
                continue

            provider = self._providers[provider_name]

            try:
                logger.info(f"Starting stream with provider: {provider_name}")
                async for chunk in provider.chat_stream(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=top_p,
                    **kwargs
                ):
                    yield chunk
                return  # Successfully streamed

            except LLMError as e:
                error_msg = f"{provider_name}: {e.message}"
                errors.append(error_msg)
                logger.warning(f"Stream provider failed, trying next: {error_msg}")
                continue

            except Exception as e:
                error_msg = f"{provider_name}: {str(e)}"
                errors.append(error_msg)
                logger.warning(f"Stream provider failed, trying next: {error_msg}")
                continue

        # All providers failed
        error_summary = "; ".join(errors)
        raise LLMError(
            provider="fallback_chain",
            model="all",
            message=f"All streaming providers failed: {error_summary}"
        )

    async def close(self) -> None:
        """Close all provider connections."""
        for provider in self._providers.values():
            await provider.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Convenience function for simple usage
async def chat_with_fallback(
    messages: List[Message],
    temperature: float = None,
    max_tokens: int = None,
    **kwargs
) -> FallbackResult:
    """
    Simple function to chat with LLM using fallback chain.

    Example:
        from shared.llm import chat_with_fallback, Message

        result = await chat_with_fallback([
            Message(role="user", content="Hello!")
        ])
        print(result.response.content)
    """
    async with LLMFallbackChain() as chain:
        return await chain.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
