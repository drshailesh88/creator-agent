"""LLM provider implementations for the Life OS multi-agent system.

Provides unified interfaces for:
- ZhipuProvider (GLM 4.7)
- MoonshotProvider (Kimi K2)
- OpenAIProvider (GPT-4o mini)
"""

import os
import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, AsyncGenerator
from datetime import datetime

import httpx

from .config import API_KEY_ENV_VARS, SETTINGS


logger = logging.getLogger(__name__)


@dataclass
class Message:
    """A chat message."""
    role: str  # 'system', 'user', 'assistant'
    content: str


@dataclass
class LLMResponse:
    """Response from an LLM provider."""
    content: str
    model: str
    provider: str
    usage: Dict[str, int] = field(default_factory=dict)
    finish_reason: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None


@dataclass
class LLMError(Exception):
    """Custom exception for LLM errors."""
    provider: str
    model: str
    message: str
    status_code: Optional[int] = None
    retry_after: Optional[float] = None

    def __str__(self) -> str:
        return f"[{self.provider}/{self.model}] {self.message}"


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    provider_name: str = "base"

    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        timeout: int = 60,
        max_retries: int = 2,
    ):
        self.model = model
        self.api_key = api_key or self._get_api_key()
        self.api_base = api_base
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None

    def _get_api_key(self) -> str:
        """Get API key from environment variable."""
        env_var = API_KEY_ENV_VARS.get(self.provider_name)
        if not env_var:
            raise LLMError(
                provider=self.provider_name,
                model=self.model,
                message=f"No environment variable configured for provider '{self.provider_name}'"
            )
        api_key = os.environ.get(env_var)
        if not api_key:
            raise LLMError(
                provider=self.provider_name,
                model=self.model,
                message=f"API key not found. Set {env_var} environment variable."
            )
        return api_key

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    @abstractmethod
    async def chat(
        self,
        messages: List[Message],
        temperature: float = None,
        max_tokens: int = None,
        top_p: float = None,
        **kwargs
    ) -> LLMResponse:
        """Send a chat completion request."""
        pass

    @abstractmethod
    async def chat_stream(
        self,
        messages: List[Message],
        temperature: float = None,
        max_tokens: int = None,
        top_p: float = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Send a streaming chat completion request."""
        pass

    def _build_messages_payload(self, messages: List[Message]) -> List[Dict[str, str]]:
        """Convert Message objects to API payload format."""
        return [{"role": m.role, "content": m.content} for m in messages]


class ZhipuProvider(BaseLLMProvider):
    """Zhipu AI provider for GLM-4 models."""

    provider_name = "zhipu"

    def __init__(
        self,
        model: str = "glm-4",
        api_key: Optional[str] = None,
        api_base: str = "https://open.bigmodel.cn/api/paas/v4",
        **kwargs
    ):
        super().__init__(model=model, api_key=api_key, api_base=api_base, **kwargs)

    async def chat(
        self,
        messages: List[Message],
        temperature: float = None,
        max_tokens: int = None,
        top_p: float = None,
        **kwargs
    ) -> LLMResponse:
        """Send a chat completion request to Zhipu AI."""
        client = await self._get_client()
        url = f"{self.api_base}/chat/completions"

        payload = {
            "model": self.model,
            "messages": self._build_messages_payload(messages),
            "temperature": temperature or SETTINGS.default_temperature,
            "max_tokens": max_tokens or SETTINGS.default_max_tokens,
            "top_p": top_p or SETTINGS.default_top_p,
        }
        payload.update(kwargs)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

            return LLMResponse(
                content=data["choices"][0]["message"]["content"],
                model=self.model,
                provider=self.provider_name,
                usage=data.get("usage", {}),
                finish_reason=data["choices"][0].get("finish_reason"),
                raw_response=data,
            )

        except httpx.HTTPStatusError as e:
            raise LLMError(
                provider=self.provider_name,
                model=self.model,
                message=f"HTTP error: {e.response.status_code} - {e.response.text}",
                status_code=e.response.status_code,
            )
        except Exception as e:
            raise LLMError(
                provider=self.provider_name,
                model=self.model,
                message=str(e),
            )

    async def chat_stream(
        self,
        messages: List[Message],
        temperature: float = None,
        max_tokens: int = None,
        top_p: float = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Send a streaming chat completion request to Zhipu AI."""
        client = await self._get_client()
        url = f"{self.api_base}/chat/completions"

        payload = {
            "model": self.model,
            "messages": self._build_messages_payload(messages),
            "temperature": temperature or SETTINGS.default_temperature,
            "max_tokens": max_tokens or SETTINGS.default_max_tokens,
            "top_p": top_p or SETTINGS.default_top_p,
            "stream": True,
        }
        payload.update(kwargs)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with client.stream("POST", url, json=payload, headers=headers) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    import json
                    chunk = json.loads(data)
                    if chunk["choices"][0].get("delta", {}).get("content"):
                        yield chunk["choices"][0]["delta"]["content"]


class MoonshotProvider(BaseLLMProvider):
    """Moonshot AI provider for Kimi models."""

    provider_name = "moonshot"

    def __init__(
        self,
        model: str = "kimi-k2",
        api_key: Optional[str] = None,
        api_base: str = "https://api.moonshot.cn/v1",
        **kwargs
    ):
        super().__init__(model=model, api_key=api_key, api_base=api_base, **kwargs)

    async def chat(
        self,
        messages: List[Message],
        temperature: float = None,
        max_tokens: int = None,
        top_p: float = None,
        **kwargs
    ) -> LLMResponse:
        """Send a chat completion request to Moonshot AI."""
        client = await self._get_client()
        url = f"{self.api_base}/chat/completions"

        payload = {
            "model": self.model,
            "messages": self._build_messages_payload(messages),
            "temperature": temperature or SETTINGS.default_temperature,
            "max_tokens": max_tokens or SETTINGS.default_max_tokens,
            "top_p": top_p or SETTINGS.default_top_p,
        }
        payload.update(kwargs)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

            return LLMResponse(
                content=data["choices"][0]["message"]["content"],
                model=self.model,
                provider=self.provider_name,
                usage=data.get("usage", {}),
                finish_reason=data["choices"][0].get("finish_reason"),
                raw_response=data,
            )

        except httpx.HTTPStatusError as e:
            raise LLMError(
                provider=self.provider_name,
                model=self.model,
                message=f"HTTP error: {e.response.status_code} - {e.response.text}",
                status_code=e.response.status_code,
            )
        except Exception as e:
            raise LLMError(
                provider=self.provider_name,
                model=self.model,
                message=str(e),
            )

    async def chat_stream(
        self,
        messages: List[Message],
        temperature: float = None,
        max_tokens: int = None,
        top_p: float = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Send a streaming chat completion request to Moonshot AI."""
        client = await self._get_client()
        url = f"{self.api_base}/chat/completions"

        payload = {
            "model": self.model,
            "messages": self._build_messages_payload(messages),
            "temperature": temperature or SETTINGS.default_temperature,
            "max_tokens": max_tokens or SETTINGS.default_max_tokens,
            "top_p": top_p or SETTINGS.default_top_p,
            "stream": True,
        }
        payload.update(kwargs)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with client.stream("POST", url, json=payload, headers=headers) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    import json
                    chunk = json.loads(data)
                    if chunk["choices"][0].get("delta", {}).get("content"):
                        yield chunk["choices"][0]["delta"]["content"]


class OpenAIProvider(BaseLLMProvider):
    """OpenAI provider for GPT models."""

    provider_name = "openai"

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        api_base: str = "https://api.openai.com/v1",
        **kwargs
    ):
        super().__init__(model=model, api_key=api_key, api_base=api_base, **kwargs)

    async def chat(
        self,
        messages: List[Message],
        temperature: float = None,
        max_tokens: int = None,
        top_p: float = None,
        **kwargs
    ) -> LLMResponse:
        """Send a chat completion request to OpenAI."""
        client = await self._get_client()
        url = f"{self.api_base}/chat/completions"

        payload = {
            "model": self.model,
            "messages": self._build_messages_payload(messages),
            "temperature": temperature or SETTINGS.default_temperature,
            "max_tokens": max_tokens or SETTINGS.default_max_tokens,
            "top_p": top_p or SETTINGS.default_top_p,
        }
        payload.update(kwargs)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

            return LLMResponse(
                content=data["choices"][0]["message"]["content"],
                model=self.model,
                provider=self.provider_name,
                usage=data.get("usage", {}),
                finish_reason=data["choices"][0].get("finish_reason"),
                raw_response=data,
            )

        except httpx.HTTPStatusError as e:
            raise LLMError(
                provider=self.provider_name,
                model=self.model,
                message=f"HTTP error: {e.response.status_code} - {e.response.text}",
                status_code=e.response.status_code,
            )
        except Exception as e:
            raise LLMError(
                provider=self.provider_name,
                model=self.model,
                message=str(e),
            )

    async def chat_stream(
        self,
        messages: List[Message],
        temperature: float = None,
        max_tokens: int = None,
        top_p: float = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Send a streaming chat completion request to OpenAI."""
        client = await self._get_client()
        url = f"{self.api_base}/chat/completions"

        payload = {
            "model": self.model,
            "messages": self._build_messages_payload(messages),
            "temperature": temperature or SETTINGS.default_temperature,
            "max_tokens": max_tokens or SETTINGS.default_max_tokens,
            "top_p": top_p or SETTINGS.default_top_p,
            "stream": True,
        }
        payload.update(kwargs)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with client.stream("POST", url, json=payload, headers=headers) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    import json
                    chunk = json.loads(data)
                    if chunk["choices"][0].get("delta", {}).get("content"):
                        yield chunk["choices"][0]["delta"]["content"]


# Provider registry
PROVIDER_REGISTRY: Dict[str, type[BaseLLMProvider]] = {
    "zhipu": ZhipuProvider,
    "moonshot": MoonshotProvider,
    "openai": OpenAIProvider,
}


def get_provider(
    provider_name: str,
    model: Optional[str] = None,
    **kwargs
) -> BaseLLMProvider:
    """Factory function to get a provider instance."""
    if provider_name not in PROVIDER_REGISTRY:
        raise ValueError(f"Unknown provider: {provider_name}. Available: {list(PROVIDER_REGISTRY.keys())}")

    provider_class = PROVIDER_REGISTRY[provider_name]
    if model:
        return provider_class(model=model, **kwargs)
    return provider_class(**kwargs)
