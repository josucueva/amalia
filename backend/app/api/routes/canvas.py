"""
Canvas routes for managing agent pipelines and connections.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List
import structlog

from app.services.agent_pipeline import AgentPipelineService
from app.services.llm_service import get_llm_service
from app.config import get_settings

logger = structlog.get_logger()
router = APIRouter()


class NodePosition(BaseModel):
    x: float
    y: float


class CanvasNode(BaseModel):
    instanceId: str
    agentId: str
    position: NodePosition


class CanvasConnection(BaseModel):
    id: str
    fromInstanceId: str
    toInstanceId: str


class BuildPipelineRequest(BaseModel):
    command: str  # e.g., "BUILD"


class BuildPipelineResponse(BaseModel):
    success: bool
    message: str
    nodes: List[CanvasNode]
    connections: List[CanvasConnection]


@router.post("/build", response_model=BuildPipelineResponse)
async def build_pipeline(
    request_data: BuildPipelineRequest,
    request: Request,
):
    """
    Execute a BUILD command to create a pipeline with agents.

    Args:
        request_data: Build command request
        request: FastAPI request object

    Returns:
        BuildPipelineResponse: Created nodes and connections
    """
    try:
        logger.info("Processing BUILD command", command=request_data.command)

        # Get agent registry
        agent_registry = getattr(request.app.state, "agent_registry", None)
        if not agent_registry:
            raise HTTPException(status_code=500, detail="Agent registry not available")

        # Get LLM service
        settings = get_settings()
        llm_service = get_llm_service(settings)

        # Create pipeline service
        pipeline_service = AgentPipelineService(llm_service, agent_registry)

        # Execute simple build (for backward compatibility)
        result = pipeline_service.execute_simple_build()

        orchestration = result["orchestration"]

        return BuildPipelineResponse(
            success=True,
            message=orchestration.get("message", "Pipeline created"),
            nodes=orchestration["nodes"],
            connections=orchestration["connections"],
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error building pipeline", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
