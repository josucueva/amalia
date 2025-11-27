"""
Canvas routes for managing agent pipelines and connections.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional
import structlog
import random

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

        # Get all available agents (excluding interaction_agent)
        agents = agent_registry.list_agents()
        available_agents = [
            agent for agent in agents if agent.config.name != "interaction_agent"
        ]

        if len(available_agents) < 2:
            raise HTTPException(
                status_code=400,
                detail="Not enough agents available. Need at least 2 agents (excluding interaction_agent).",
            )

        # Select two random agents
        selected_agents = random.sample(available_agents, 2)

        # Generate instance IDs and positions
        import time

        timestamp = int(time.time() * 1000)
        instance1_id = f"instance_{timestamp}_{random.randint(1000, 9999)}"
        instance2_id = f"instance_{timestamp + 1}_{random.randint(1000, 9999)}"

        # Create nodes with positions
        nodes = [
            CanvasNode(
                instanceId=instance1_id,
                agentId=selected_agents[0].id,
                position=NodePosition(x=200, y=200),
            ),
            CanvasNode(
                instanceId=instance2_id,
                agentId=selected_agents[1].id,
                position=NodePosition(x=500, y=200),
            ),
        ]

        # Create connection from first to second agent
        connection_id = f"{instance1_id}_to_{instance2_id}"
        connections = [
            CanvasConnection(
                id=connection_id,
                fromInstanceId=instance1_id,
                toInstanceId=instance2_id,
            )
        ]

        logger.info(
            "Pipeline built successfully",
            agent1=selected_agents[0].config.name,
            agent2=selected_agents[1].config.name,
        )

        return BuildPipelineResponse(
            success=True,
            message=f"Built pipeline: {selected_agents[0].config.name} → {selected_agents[1].config.name}",
            nodes=nodes,
            connections=connections,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error building pipeline", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
