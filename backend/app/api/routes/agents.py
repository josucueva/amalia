"""
Agent management routes with MongoDB persistence.
"""

from fastapi import APIRouter, HTTPException, Request
from typing import List
import structlog
import uuid

from app.models import Agent, AgentCreateRequest, AgentListResponse

logger = structlog.get_logger()
router = APIRouter()


def get_agent_service(req: Request):
    """Get agent service from app state."""
    if not hasattr(req.app.state, "agent_service"):
        raise HTTPException(status_code=500, detail="Agent service not initialized")
    return req.app.state.agent_service


@router.get("/", response_model=AgentListResponse)
async def list_agents(request: Request, include_hidden: bool = False):
    """
    List all registered agents.

    Args:
        include_hidden: Include hidden agents (planner, orchestrator)

    Returns:
        AgentListResponse: List of all agents
    """
    try:
        agents = await get_agent_service(request).list_agents(
            include_hidden=include_hidden
        )
        return AgentListResponse(agents=agents, total=len(agents))
    except Exception as e:
        logger.error("Error listing agents", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str, request: Request):
    """
    Get a specific agent by ID.

    Args:
        agent_id: Agent ID

    Returns:
        Agent: Agent details
    """
    try:
        agent = await get_agent_service(request).get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        return agent
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting agent", agent_id=agent_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=Agent, status_code=201)
async def create_agent(req: AgentCreateRequest, request: Request):
    """
    Create a new agent and persist to MongoDB.

    Args:
        request: Agent creation request

    Returns:
        Agent: Created agent
    """
    try:
        agent_id = f"agent_{uuid.uuid4().hex[:12]}"
        agent = await get_agent_service(request).create_agent(agent_id, req.config)
        logger.info(
            "Agent created and persisted", agent_id=agent_id, name=req.config.name
        )
        return agent
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error creating agent", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{agent_id}", response_model=Agent)
async def update_agent(agent_id: str, req: AgentCreateRequest, request: Request):
    """
    Update an existing agent and persist to MongoDB.

    Args:
        agent_id: Agent ID
        request: Agent update request

    Returns:
        Agent: Updated agent
    """
    try:
        agent = await get_agent_service(request).update_agent(agent_id, req.config)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        logger.info("Agent updated and persisted", agent_id=agent_id)
        return agent
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating agent", agent_id=agent_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str, request: Request):
    """
    Delete an agent from MongoDB and remove its YAML file.

    Args:
        agent_id: Agent ID

    Returns:
        dict: Deletion confirmation
    """
    try:
        success = await get_agent_service(request).delete_agent(agent_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        logger.info("Agent deleted and config removed", agent_id=agent_id)
        return {"status": "deleted", "agent_id": agent_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting agent", agent_id=agent_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reload-from-yaml")
async def reload_agents_from_yaml(request: Request):
    """
    Reload all agents from YAML configuration files into MongoDB.

    Returns:
        dict: Reload status with count of loaded agents
    """
    try:
        service = get_agent_service(request)
        await service.reload_agents()
        agents = await service.list_agents(include_hidden=True)

        logger.info("Agents reloaded from YAML", count=len(agents))
        return {
            "status": "success",
            "agents_loaded": len(agents),
            "agents": [{"id": a.id, "name": a.config.name} for a in agents],
        }
    except Exception as e:
        logger.error("Error reloading agents from YAML", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
