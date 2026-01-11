"""
Pydantic models for Master Router request/response schemas.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class DomainType(str, Enum):
    """Available domain types for routing."""
    CONTENT = "content"
    BUSINESS = "business"
    PERSONAL = "personal"
    UNKNOWN = "unknown"


class MessageRole(str, Enum):
    """Role of the message sender."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    """A single message in the conversation."""
    role: MessageRole
    content: str
    timestamp: Optional[datetime] = None


class QueryRequest(BaseModel):
    """Request model for the /query endpoint."""
    message: str = Field(..., description="The user's message to process")
    conversation_id: Optional[str] = Field(
        None, description="Optional conversation ID for context continuity"
    )
    user_id: Optional[str] = Field(
        None, description="User identifier for personalization"
    )
    context: Optional[dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional context for the request"
    )
    history: Optional[list[Message]] = Field(
        default_factory=list,
        description="Previous messages in the conversation"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Write a blog post about AI agents",
                "conversation_id": "conv_123",
                "user_id": "user_456",
                "context": {"platform": "clawdbot"},
                "history": []
            }
        }
    }


class RoutingInfo(BaseModel):
    """Information about how the request was routed."""
    domain: DomainType
    confidence: float = Field(..., ge=0.0, le=1.0)
    matched_keywords: list[str] = Field(default_factory=list)
    used_llm_fallback: bool = False


class QueryResponse(BaseModel):
    """Response model for the /query endpoint."""
    success: bool
    message: str = Field(..., description="The response message with Clawdbot personality")
    domain: DomainType = Field(..., description="The domain that handled the request")
    routing_info: Optional[RoutingInfo] = None
    data: Optional[dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional response data from the orchestrator"
    )
    conversation_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "Meow! I've drafted that blog post for you...",
                "domain": "content",
                "routing_info": {
                    "domain": "content",
                    "confidence": 0.95,
                    "matched_keywords": ["blog", "write"],
                    "used_llm_fallback": False
                },
                "data": {"draft_id": "draft_789"},
                "conversation_id": "conv_123",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }
    }


class HealthStatus(str, Enum):
    """Health status values."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ServiceHealth(BaseModel):
    """Health status of an individual service."""
    name: str
    status: HealthStatus
    latency_ms: Optional[float] = None
    message: Optional[str] = None


class HealthResponse(BaseModel):
    """Response model for the /health endpoint."""
    status: HealthStatus
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    services: list[ServiceHealth] = Field(default_factory=list)

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "version": "0.1.0",
                "timestamp": "2024-01-15T10:30:00Z",
                "services": [
                    {"name": "content-orchestrator", "status": "healthy", "latency_ms": 45.2},
                    {"name": "business-orchestrator", "status": "healthy", "latency_ms": 38.1},
                    {"name": "personal-orchestrator", "status": "healthy", "latency_ms": 42.7}
                ]
            }
        }
    }


class ErrorResponse(BaseModel):
    """Error response model."""
    success: bool = False
    error: str
    error_code: Optional[str] = None
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
