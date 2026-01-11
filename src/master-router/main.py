"""
Master Router - FastAPI Application

Entry point for the Life OS system that routes requests to appropriate orchestrators.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated, Optional

import httpx
import structlog
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import __version__
from .config import Settings, get_settings
from .models import (
    DomainType,
    ErrorResponse,
    HealthResponse,
    HealthStatus,
    QueryRequest,
    QueryResponse,
    ServiceHealth,
)
from .router import IntentRouter

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Global router instance
router_instance: Optional[IntentRouter] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global router_instance

    settings = get_settings()
    router_instance = IntentRouter(settings)

    logger.info(
        "master_router_starting",
        version=__version__,
        host=settings.api_host,
        port=settings.api_port
    )

    yield

    # Cleanup
    if router_instance:
        await router_instance.close()

    logger.info("master_router_stopped")


# Create FastAPI application
app = FastAPI(
    title="Life OS Master Router",
    description="Entry point for Life OS - routes requests to domain orchestrators",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_router() -> IntentRouter:
    """Dependency to get the router instance."""
    if router_instance is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Router not initialized"
        )
    return router_instance


async def verify_api_key(
    x_api_key: Annotated[Optional[str], Header()] = None,
    settings: Settings = Depends(get_settings)
) -> bool:
    """Verify API key from header."""
    # If no API key is configured, allow all requests (development mode)
    if not settings.api_key:
        return True

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return True


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal server error",
            error_code="INTERNAL_ERROR",
            detail=str(exc) if get_settings().debug else None
        ).model_dump()
    )


@app.post(
    "/query",
    response_model=QueryResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
    summary="Process a query and route to appropriate orchestrator",
    description="Receives a message, classifies the intent, and routes to the appropriate domain orchestrator.",
)
async def query(
    request: QueryRequest,
    router: IntentRouter = Depends(get_router),
    _authenticated: bool = Depends(verify_api_key),
) -> QueryResponse:
    """
    Process a query message and route to the appropriate orchestrator.

    The router will:
    1. Classify the intent using keyword matching and LLM fallback
    2. Route to the appropriate domain orchestrator (content, business, or personal)
    3. Return the response with Clawdbot personality

    Args:
        request: The query request containing the message and context

    Returns:
        QueryResponse with the processed result
    """
    logger.info(
        "query_received",
        message_length=len(request.message),
        conversation_id=request.conversation_id,
        user_id=request.user_id
    )

    response = await router.route_request(request)

    logger.info(
        "query_processed",
        domain=response.domain.value,
        success=response.success,
        conversation_id=response.conversation_id
    )

    return response


@app.post(
    "/health",
    response_model=HealthResponse,
    summary="Health check endpoint",
    description="Check the health status of the master router and connected orchestrators.",
)
async def health_check(
    settings: Settings = Depends(get_settings),
) -> HealthResponse:
    """
    Check the health of the master router and all connected orchestrators.

    Returns:
        HealthResponse with overall status and individual service health
    """
    services: list[ServiceHealth] = []
    overall_status = HealthStatus.HEALTHY

    # Check orchestrator health
    orchestrators = [
        ("content-orchestrator", settings.content_orchestrator_url),
        ("business-orchestrator", settings.business_orchestrator_url),
        ("personal-orchestrator", settings.personal_orchestrator_url),
    ]

    async with httpx.AsyncClient(timeout=settings.health_check_timeout) as client:
        for name, url in orchestrators:
            try:
                start_time = datetime.utcnow()
                response = await client.get(f"{url}/health")
                latency = (datetime.utcnow() - start_time).total_seconds() * 1000

                if response.status_code == 200:
                    services.append(ServiceHealth(
                        name=name,
                        status=HealthStatus.HEALTHY,
                        latency_ms=round(latency, 2)
                    ))
                else:
                    services.append(ServiceHealth(
                        name=name,
                        status=HealthStatus.DEGRADED,
                        latency_ms=round(latency, 2),
                        message=f"Unexpected status code: {response.status_code}"
                    ))
                    if overall_status == HealthStatus.HEALTHY:
                        overall_status = HealthStatus.DEGRADED

            except httpx.TimeoutException:
                services.append(ServiceHealth(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message="Connection timeout"
                ))
                overall_status = HealthStatus.DEGRADED

            except Exception as e:
                services.append(ServiceHealth(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=str(e)
                ))
                overall_status = HealthStatus.DEGRADED

    # Check LLM availability
    llm_status = HealthStatus.HEALTHY
    llm_message = None

    if not settings.is_glm4_configured and not settings.is_claude_configured:
        llm_status = HealthStatus.DEGRADED
        llm_message = "No LLM API keys configured"
    elif not settings.is_glm4_configured:
        llm_message = "GLM-4 not configured, using Claude"
    elif not settings.is_claude_configured:
        llm_message = "Claude not configured, using GLM-4"

    services.append(ServiceHealth(
        name="llm-service",
        status=llm_status,
        message=llm_message
    ))

    return HealthResponse(
        status=overall_status,
        version=__version__,
        services=services
    )


@app.get(
    "/",
    summary="Root endpoint",
    description="Returns basic service information.",
)
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Life OS Master Router",
        "version": __version__,
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


@app.get(
    "/domains",
    summary="List available domains",
    description="Returns information about available routing domains.",
)
async def list_domains(
    router: IntentRouter = Depends(get_router),
    _authenticated: bool = Depends(verify_api_key),
):
    """List all available domains and their configurations."""
    return {
        "domains": {
            name: {
                "display_name": config.display_name,
                "description": config.description,
                "keywords": list(config.primary_keywords)[:10],  # Sample keywords
            }
            for name, config in router.domains.items()
        }
    }


# For running with uvicorn directly
if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "master_router.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
