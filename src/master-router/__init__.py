"""
Master Router - Entry point for Life OS request routing.

This service receives messages from Clawdbot and routes them to the appropriate
domain orchestrator (content, business, or personal) based on intent classification.
"""

from .main import app
from .router import IntentRouter
from .models import QueryRequest, QueryResponse, HealthResponse
from .config import Settings

__version__ = "0.1.0"
__all__ = [
    "app",
    "IntentRouter",
    "QueryRequest",
    "QueryResponse",
    "HealthResponse",
    "Settings",
]
