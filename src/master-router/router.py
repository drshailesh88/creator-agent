"""
Intent classification and routing logic for Master Router.

Classifies incoming requests by domain using keyword matching with LLM fallback,
then routes to the appropriate orchestrator.
"""

import re
from pathlib import Path
from typing import Any, Optional

import httpx
import structlog
import yaml

from .config import Settings, get_settings
from .models import DomainType, QueryRequest, QueryResponse, RoutingInfo

logger = structlog.get_logger(__name__)


class DomainConfig:
    """Configuration for a single domain."""

    def __init__(self, name: str, config: dict[str, Any]):
        self.name = name
        self.display_name = config.get("name", name.title())
        self.description = config.get("description", "")
        self.endpoint = config.get("endpoint", "/process")
        self.weight = config.get("weight", 1.0)
        self.priority = config.get("priority", 99)

        keywords = config.get("keywords", {})
        self.primary_keywords = set(k.lower() for k in keywords.get("primary", []))
        self.secondary_keywords = set(k.lower() for k in keywords.get("secondary", []))
        self.all_keywords = self.primary_keywords | self.secondary_keywords


class IntentRouter:
    """Routes requests to appropriate orchestrators based on intent classification."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.domains: dict[str, DomainConfig] = {}
        self.cross_domain_keywords: set[str] = set()
        self.classification_config: dict[str, Any] = {}
        self._http_client: Optional[httpx.AsyncClient] = None

        self._load_domains_config()

    def _load_domains_config(self) -> None:
        """Load domain configuration from YAML file."""
        config_path = self.settings.domains_config_path

        if not config_path.exists():
            logger.warning("domains_config_not_found", path=str(config_path))
            self._load_default_domains()
            return

        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)

            # Load domains
            for domain_name, domain_config in config.get("domains", {}).items():
                self.domains[domain_name] = DomainConfig(domain_name, domain_config)

            # Load cross-domain keywords
            self.cross_domain_keywords = set(
                k.lower() for k in config.get("cross_domain", [])
            )

            # Load classification config
            self.classification_config = config.get("classification", {})

            logger.info(
                "domains_config_loaded",
                domains=list(self.domains.keys()),
                cross_domain_count=len(self.cross_domain_keywords)
            )

        except Exception as e:
            logger.error("domains_config_load_error", error=str(e))
            self._load_default_domains()

    def _load_default_domains(self) -> None:
        """Load default domain configuration."""
        default_config = {
            "content": {
                "name": "Content Creation",
                "keywords": {
                    "primary": ["write", "blog", "twitter", "research", "article",
                               "paper", "newsletter"],
                    "secondary": ["edit", "draft", "publish"]
                }
            },
            "business": {
                "name": "Business Operations",
                "keywords": {
                    "primary": ["hr", "finance", "loan", "invoice", "employee",
                               "payroll", "budget", "legal"],
                    "secondary": ["contract", "tax", "accounting"]
                }
            },
            "personal": {
                "name": "Personal Life",
                "keywords": {
                    "primary": ["health", "family", "schedule", "reminder", "fitness",
                               "learning", "wellness"],
                    "secondary": ["calendar", "workout", "habit"]
                }
            }
        }

        for domain_name, domain_config in default_config.items():
            self.domains[domain_name] = DomainConfig(domain_name, domain_config)

        logger.info("default_domains_loaded", domains=list(self.domains.keys()))

    async def get_http_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.settings.orchestrator_timeout)
            )
        return self._http_client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    def classify_intent_keywords(self, message: str) -> tuple[DomainType, float, list[str]]:
        """
        Classify intent using keyword matching.

        Returns:
            Tuple of (domain, confidence, matched_keywords)
        """
        message_lower = message.lower()
        words = set(re.findall(r'\b\w+\b', message_lower))

        # Also check for multi-word phrases
        phrases = set()
        for domain_config in self.domains.values():
            for keyword in domain_config.all_keywords:
                if ' ' in keyword and keyword in message_lower:
                    phrases.add(keyword)

        words_and_phrases = words | phrases

        domain_scores: dict[str, tuple[float, list[str]]] = {}

        primary_weight = self.classification_config.get("primary_keyword_weight", 1.0)
        secondary_weight = self.classification_config.get("secondary_keyword_weight", 0.6)

        for domain_name, domain_config in self.domains.items():
            score = 0.0
            matched = []

            # Check primary keywords
            primary_matches = words_and_phrases & domain_config.primary_keywords
            for match in primary_matches:
                score += primary_weight
                matched.append(match)

            # Check secondary keywords
            secondary_matches = words_and_phrases & domain_config.secondary_keywords
            for match in secondary_matches:
                score += secondary_weight
                matched.append(match)

            # Apply domain weight
            score *= domain_config.weight

            if score > 0:
                domain_scores[domain_name] = (score, matched)

        if not domain_scores:
            return DomainType.UNKNOWN, 0.0, []

        # Find the best matching domain
        best_domain = max(
            domain_scores.keys(),
            key=lambda d: (domain_scores[d][0], -self.domains[d].priority)
        )

        best_score, matched_keywords = domain_scores[best_domain]

        # Normalize confidence (sigmoid-like normalization)
        confidence = min(1.0, best_score / 2.0)

        try:
            domain_type = DomainType(best_domain)
        except ValueError:
            domain_type = DomainType.UNKNOWN

        return domain_type, confidence, matched_keywords

    async def classify_intent_llm(
        self,
        message: str,
        context: Optional[dict[str, Any]] = None
    ) -> tuple[DomainType, float]:
        """
        Classify intent using LLM when keyword matching is insufficient.

        Uses GLM-4 as default, Claude as fallback.
        """
        domains_description = "\n".join(
            f"- {name}: {config.description}"
            for name, config in self.domains.items()
        )

        prompt = f"""Classify the following user message into one of these domains:

{domains_description}

User message: "{message}"

Respond with ONLY the domain name (content, business, or personal) and a confidence score from 0 to 1, separated by a comma.
Example: content, 0.85

If the message doesn't clearly fit any domain, respond with: unknown, 0.0"""

        try:
            # Try GLM-4 first
            if self.settings.default_llm == "glm4" and self.settings.is_glm4_configured:
                domain, confidence = await self._classify_with_glm4(prompt)
            elif self.settings.is_claude_configured:
                domain, confidence = await self._classify_with_claude(prompt)
            elif self.settings.is_glm4_configured:
                domain, confidence = await self._classify_with_glm4(prompt)
            else:
                logger.warning("no_llm_configured")
                return DomainType.UNKNOWN, 0.0

            return domain, confidence

        except Exception as e:
            logger.error("llm_classification_error", error=str(e))

            # Try fallback LLM
            try:
                if self.settings.default_llm == "glm4" and self.settings.is_claude_configured:
                    return await self._classify_with_claude(prompt)
                elif self.settings.is_glm4_configured:
                    return await self._classify_with_glm4(prompt)
            except Exception as fallback_error:
                logger.error("llm_fallback_error", error=str(fallback_error))

            return DomainType.UNKNOWN, 0.0

    async def _classify_with_glm4(self, prompt: str) -> tuple[DomainType, float]:
        """Classify using GLM-4 API."""
        client = await self.get_http_client()

        response = await client.post(
            f"{self.settings.glm4_api_base}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.settings.glm4_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": self.settings.glm4_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 50
            },
            timeout=self.settings.llm_timeout
        )
        response.raise_for_status()

        result = response.json()
        content = result["choices"][0]["message"]["content"].strip().lower()

        return self._parse_llm_response(content)

    async def _classify_with_claude(self, prompt: str) -> tuple[DomainType, float]:
        """Classify using Claude API."""
        client = await self.get_http_client()

        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.settings.claude_api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            },
            json={
                "model": self.settings.claude_model,
                "max_tokens": 50,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=self.settings.llm_timeout
        )
        response.raise_for_status()

        result = response.json()
        content = result["content"][0]["text"].strip().lower()

        return self._parse_llm_response(content)

    def _parse_llm_response(self, content: str) -> tuple[DomainType, float]:
        """Parse LLM classification response."""
        try:
            parts = content.split(",")
            domain_str = parts[0].strip()
            confidence = float(parts[1].strip()) if len(parts) > 1 else 0.8

            try:
                domain = DomainType(domain_str)
            except ValueError:
                domain = DomainType.UNKNOWN
                confidence = 0.0

            return domain, min(1.0, max(0.0, confidence))

        except Exception:
            return DomainType.UNKNOWN, 0.0

    async def classify_intent(
        self,
        message: str,
        context: Optional[dict[str, Any]] = None
    ) -> RoutingInfo:
        """
        Classify the intent of a message and return routing information.

        Uses keyword matching first, then LLM fallback if confidence is low.
        """
        # First try keyword matching
        domain, confidence, matched_keywords = self.classify_intent_keywords(message)
        used_llm = False

        threshold = self.classification_config.get(
            "llm_fallback_threshold",
            self.settings.keyword_confidence_threshold
        )

        # Use LLM fallback if confidence is too low
        if confidence < threshold and self.settings.llm_fallback_enabled:
            logger.info(
                "using_llm_fallback",
                keyword_confidence=confidence,
                threshold=threshold
            )

            llm_domain, llm_confidence = await self.classify_intent_llm(message, context)

            if llm_confidence > confidence:
                domain = llm_domain
                confidence = llm_confidence
                used_llm = True
                matched_keywords = []  # LLM doesn't provide matched keywords

        logger.info(
            "intent_classified",
            domain=domain.value,
            confidence=confidence,
            matched_keywords=matched_keywords,
            used_llm=used_llm
        )

        return RoutingInfo(
            domain=domain,
            confidence=confidence,
            matched_keywords=matched_keywords,
            used_llm_fallback=used_llm
        )

    async def route_request(self, request: QueryRequest) -> QueryResponse:
        """
        Route a request to the appropriate orchestrator.

        Returns:
            QueryResponse with the orchestrator's response
        """
        # Classify intent
        routing_info = await self.classify_intent(request.message, request.context)

        if routing_info.domain == DomainType.UNKNOWN:
            return QueryResponse(
                success=False,
                message=self._add_personality(
                    "I'm not sure which area this falls into. Could you provide more "
                    "details about what you're trying to do?"
                ),
                domain=DomainType.UNKNOWN,
                routing_info=routing_info,
                conversation_id=request.conversation_id
            )

        # Get orchestrator URL
        orchestrator_url = self.settings.get_orchestrator_url(routing_info.domain.value)

        if not orchestrator_url:
            logger.error(
                "orchestrator_url_not_configured",
                domain=routing_info.domain.value
            )
            return QueryResponse(
                success=False,
                message=self._add_personality(
                    f"The {routing_info.domain.value} system isn't configured yet. "
                    "Please try again later."
                ),
                domain=routing_info.domain,
                routing_info=routing_info,
                conversation_id=request.conversation_id
            )

        # Forward to orchestrator
        try:
            client = await self.get_http_client()
            domain_config = self.domains.get(routing_info.domain.value)
            endpoint = domain_config.endpoint if domain_config else "/process"

            response = await client.post(
                f"{orchestrator_url}{endpoint}",
                json={
                    "message": request.message,
                    "conversation_id": request.conversation_id,
                    "user_id": request.user_id,
                    "context": request.context,
                    "history": [msg.model_dump() for msg in request.history] if request.history else []
                },
                headers={"X-API-Key": self.settings.api_key} if self.settings.api_key else {}
            )

            if response.status_code == 200:
                result = response.json()
                return QueryResponse(
                    success=True,
                    message=self._add_personality(result.get("message", "")),
                    domain=routing_info.domain,
                    routing_info=routing_info,
                    data=result.get("data", {}),
                    conversation_id=result.get("conversation_id", request.conversation_id)
                )
            else:
                logger.error(
                    "orchestrator_error",
                    domain=routing_info.domain.value,
                    status_code=response.status_code,
                    response=response.text
                )
                return QueryResponse(
                    success=False,
                    message=self._add_personality(
                        "I ran into some trouble processing that request. "
                        "Let me try again in a moment."
                    ),
                    domain=routing_info.domain,
                    routing_info=routing_info,
                    conversation_id=request.conversation_id
                )

        except httpx.TimeoutException:
            logger.error(
                "orchestrator_timeout",
                domain=routing_info.domain.value,
                timeout=self.settings.orchestrator_timeout
            )
            return QueryResponse(
                success=False,
                message=self._add_personality(
                    "That's taking longer than expected. The system might be busy - "
                    "please try again in a few moments."
                ),
                domain=routing_info.domain,
                routing_info=routing_info,
                conversation_id=request.conversation_id
            )

        except Exception as e:
            logger.error(
                "orchestrator_connection_error",
                domain=routing_info.domain.value,
                error=str(e)
            )
            return QueryResponse(
                success=False,
                message=self._add_personality(
                    "I couldn't connect to the right system. "
                    "Please check that everything is running properly."
                ),
                domain=routing_info.domain,
                routing_info=routing_info,
                conversation_id=request.conversation_id
            )

    def _add_personality(self, message: str) -> str:
        """Add Clawdbot personality to response messages."""
        # Simple personality injection - in production, this could use LLM
        cat_intros = [
            "Meow! ",
            "Purr... ",
            "*stretches* ",
            "*perks ears* ",
        ]

        # Only add personality prefix occasionally and for shorter messages
        if len(message) < 500 and not message.startswith(tuple(cat_intros)):
            # Use a simple hash to consistently choose an intro for similar messages
            intro_index = hash(message[:20]) % (len(cat_intros) + 2)
            if intro_index < len(cat_intros):
                message = cat_intros[intro_index] + message

        return message
