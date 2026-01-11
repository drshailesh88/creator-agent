"""FastAPI application for the Content Orchestrator."""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
import logging
import uuid
from datetime import datetime

from .orchestrator import ContentOrchestrator
from ..base.orchestrator import OrchestratorRequest, OrchestratorResponse


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# FastAPI app
app = FastAPI(
    title="Content Orchestrator API",
    description="Multi-agent content creation orchestrator",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global orchestrator instance
orchestrator: Optional[ContentOrchestrator] = None


class ProcessRequest(BaseModel):
    """Request model for the /process endpoint."""
    task: str = Field(..., description="Type of task: research, write, graphics, social")
    content: str = Field(..., description="Main content or prompt for the task")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional parameters for the task"
    )
    session_id: Optional[str] = Field(
        None,
        description="Session ID for conversation continuity"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "task": "write",
                "content": "Write a blog post about the benefits of meditation",
                "parameters": {
                    "format": "blog",
                    "tone": "informative",
                    "length": "medium"
                },
                "session_id": "user-123-session-456"
            }
        }


class ProcessResponse(BaseModel):
    """Response model for the /process endpoint."""
    success: bool
    result: Any
    agent_used: Optional[str] = None
    task_type: Optional[str] = None
    execution_time: float = 0.0
    request_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: str
    agents_available: List[str]


class SessionRequest(BaseModel):
    """Request for session management."""
    session_id: str


@app.on_event("startup")
async def startup_event():
    """Initialize orchestrator on startup."""
    global orchestrator
    logger.info("Initializing Content Orchestrator...")
    orchestrator = ContentOrchestrator()
    logger.info(f"Content Orchestrator initialized with agents: {orchestrator.list_agents()}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Content Orchestrator...")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        agents_available=orchestrator.list_agents() if orchestrator else []
    )


@app.post("/process", response_model=ProcessResponse)
async def process_request(request: ProcessRequest):
    """
    Process a content creation request.

    This endpoint analyzes the request and delegates to the appropriate agent:
    - researcher: For research tasks, data gathering, summarization
    - writer: For content creation in various formats
    - graphics: For image prompts, infographics, diagrams
    - social: For social media content optimization
    """
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    request_id = str(uuid.uuid4())
    logger.info(f"Processing request {request_id}: task={request.task}")

    try:
        # Convert to internal request format
        orch_request = OrchestratorRequest(
            task=request.task,
            content=request.content,
            parameters=request.parameters,
            session_id=request.session_id,
            metadata=request.metadata
        )

        # Process through orchestrator
        response = await orchestrator.process(orch_request)

        return ProcessResponse(
            success=response.success,
            result=response.result,
            agent_used=response.agent_used,
            task_type=response.task_type,
            execution_time=response.execution_time,
            request_id=request_id,
            metadata=response.metadata,
            errors=response.errors
        )

    except Exception as e:
        logger.exception(f"Error processing request {request_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents")
async def list_agents():
    """List all available agents."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    return {
        "agents": orchestrator.list_agents(),
        "descriptions": {
            "researcher": "Research, data gathering, and summarization",
            "writer": "Content creation in multiple formats",
            "graphics": "Image prompts, infographics, diagrams",
            "social": "Social media content optimization"
        }
    }


@app.post("/session/clear")
async def clear_session(request: SessionRequest):
    """Clear a session's conversation memory."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    orchestrator.clear_session(request.session_id)
    return {"status": "cleared", "session_id": request.session_id}


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session entirely."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    orchestrator.delete_session(session_id)
    return {"status": "deleted", "session_id": session_id}


@app.get("/session/{session_id}/history")
async def get_session_history(session_id: str, limit: int = 10):
    """Get conversation history for a session."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    memory = orchestrator.get_or_create_session(session_id)
    return {
        "session_id": session_id,
        "history": memory.get_history(limit=limit),
        "context": memory.context
    }


# Convenience endpoints for specific tasks
@app.post("/research")
async def research(
    query: str,
    sources: List[str] = None,
    session_id: str = None
):
    """Convenience endpoint for research tasks."""
    request = ProcessRequest(
        task="research",
        content=query,
        parameters={"sources": sources or ["pubmed", "web"]},
        session_id=session_id
    )
    return await process_request(request)


@app.post("/write")
async def write(
    prompt: str,
    format: str = "blog",
    tone: str = "professional",
    session_id: str = None
):
    """Convenience endpoint for writing tasks."""
    request = ProcessRequest(
        task="write",
        content=prompt,
        parameters={"format": format, "tone": tone},
        session_id=session_id
    )
    return await process_request(request)


@app.post("/graphics")
async def graphics(
    description: str,
    type: str = "infographic",
    session_id: str = None
):
    """Convenience endpoint for graphics tasks."""
    request = ProcessRequest(
        task="graphics",
        content=description,
        parameters={"type": type},
        session_id=session_id
    )
    return await process_request(request)


@app.post("/social")
async def social(
    content: str,
    platform: str = "twitter",
    session_id: str = None
):
    """Convenience endpoint for social media tasks."""
    request = ProcessRequest(
        task="social",
        content=content,
        parameters={"platform": platform},
        session_id=session_id
    )
    return await process_request(request)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
