"""
Agent management routes.
"""

from fastapi import APIRouter, HTTPException, Request
from typing import List
import structlog
from datetime import datetime
import uuid

from app.models import Agent, AgentCreateRequest, AgentListResponse, AgentStatus
from app.agents.registry import AgentRegistry
from app.agents.config_loader import (
    load_agent_configs_from_yaml,
    save_agent_config_to_yaml,
)

logger = structlog.get_logger()
router = APIRouter()


def get_registry(req: Request) -> AgentRegistry:
    """Get agent registry from app state, with fallback initialization."""
    if not hasattr(req.app.state, "agent_registry"):
        from app.config import get_settings
        from app.agents.config_loader import load_agents_from_directory

        registry = AgentRegistry()
        settings = get_settings()
        try:
            agents = load_agents_from_directory(settings.agent_config_dir)
            for agent in agents:
                registry.register_agent(agent)
            logger.info("Fallback: agents loaded", count=len(agents))
        except Exception as e:
            logger.error("Fallback: error loading agents", error=str(e))
        req.app.state.agent_registry = registry
    return req.app.state.agent_registry


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
        all_agents = get_registry(request).list_agents()

        # Filter out hidden agents unless explicitly requested
        if not include_hidden:
            agents = [agent for agent in all_agents if not agent.is_hidden()]
        else:
            agents = all_agents

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
        agent = get_registry(request).get_agent(agent_id)
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
    Create a new agent.

    Args:
        request: Agent creation request

    Returns:
        Agent: Created agent
    """
    try:
        agent_id = f"agent_{uuid.uuid4().hex[:12]}"
        timestamp = datetime.now().isoformat()

        agent = Agent(
            id=agent_id,
            config=req.config,
            status=AgentStatus.ACTIVE,
            created_at=timestamp,
        )

        get_registry(request).register_agent(agent)
        logger.info("Agent created", agent_id=agent_id, name=req.config.name)

        return agent
    except Exception as e:
        logger.error("Error creating agent", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{agent_id}", response_model=Agent)
async def update_agent(agent_id: str, req: AgentCreateRequest, request: Request):
    """
    Update an existing agent.

    Args:
        agent_id: Agent ID
        request: Agent update request

    Returns:
        Agent: Updated agent
    """
    try:
        existing_agent = get_registry(request).get_agent(agent_id)
        if not existing_agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        updated_agent = Agent(
            id=agent_id,
            config=req.config,
            status=existing_agent.status,
            created_at=existing_agent.created_at,
            updated_at=datetime.now().isoformat(),
        )

        get_registry(request).update_agent(updated_agent)
        save_agent_config_to_yaml(updated_agent)
        logger.info("Agent updated and saved to YAML", agent_id=agent_id)

        return updated_agent
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating agent", agent_id=agent_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str, request: Request):
    """
    Delete an agent.

    Args:
        agent_id: Agent ID

    Returns:
        dict: Deletion confirmation
    """
    try:
        success = get_registry(request).unregister_agent(agent_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        logger.info("Agent deleted", agent_id=agent_id)
        return {"status": "deleted", "agent_id": agent_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting agent", agent_id=agent_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reload-from-yaml")
async def reload_agents_from_yaml(request: Request):
    """
    Reload all agents from YAML configuration files.

    Returns:
        dict: Reload status with count of loaded agents
    """
    try:
        agents = load_agent_configs_from_yaml()

        # Clear and re-register all agents
        reg = get_registry(request)
        reg.clear()
        for agent in agents:
            get_registry(request).register_agent(agent)

        logger.info("Agents reloaded from YAML", count=len(agents))
        return {
            "status": "success",
            "agents_loaded": len(agents),
            "agents": [{"id": a.id, "name": a.config.name} for a in agents],
        }
    except Exception as e:
        logger.error("Error reloading agents from YAML", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
