"""
Agent management routes.
"""
from fastapi import APIRouter, HTTPException
from typing import List
import structlog
from datetime import datetime
import uuid

from app.models import Agent, AgentCreateRequest, AgentListResponse, AgentStatus
from app.agents.registry import AgentRegistry
from app.agents.config_loader import load_agent_configs_from_yaml

logger = structlog.get_logger()
router = APIRouter()

# Global agent registry
agent_registry = AgentRegistry()


@router.get("/", response_model=AgentListResponse)
async def list_agents():
    """
    List all registered agents.
    
    Returns:
        AgentListResponse: List of all agents
    """
    try:
        agents = agent_registry.list_agents()
        return AgentListResponse(
            agents=agents,
            total=len(agents)
        )
    except Exception as e:
        logger.error("Error listing agents", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str):
    """
    Get a specific agent by ID.
    
    Args:
        agent_id: Agent ID
        
    Returns:
        Agent: Agent details
    """
    try:
        agent = agent_registry.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        return agent
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting agent", agent_id=agent_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=Agent, status_code=201)
async def create_agent(request: AgentCreateRequest):
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
            config=request.config,
            status=AgentStatus.ACTIVE,
            created_at=timestamp
        )
        
        agent_registry.register_agent(agent)
        logger.info("Agent created", agent_id=agent_id, name=request.config.name)
        
        return agent
    except Exception as e:
        logger.error("Error creating agent", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{agent_id}", response_model=Agent)
async def update_agent(agent_id: str, request: AgentCreateRequest):
    """
    Update an existing agent.
    
    Args:
        agent_id: Agent ID
        request: Agent update request
        
    Returns:
        Agent: Updated agent
    """
    try:
        existing_agent = agent_registry.get_agent(agent_id)
        if not existing_agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        
        updated_agent = Agent(
            id=agent_id,
            config=request.config,
            status=existing_agent.status,
            created_at=existing_agent.created_at,
            updated_at=datetime.now().isoformat()
        )
        
        agent_registry.update_agent(updated_agent)
        logger.info("Agent updated", agent_id=agent_id)
        
        return updated_agent
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating agent", agent_id=agent_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str):
    """
    Delete an agent.
    
    Args:
        agent_id: Agent ID
        
    Returns:
        dict: Deletion confirmation
    """
    try:
        success = agent_registry.unregister_agent(agent_id)
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
async def reload_agents_from_yaml():
    """
    Reload all agents from YAML configuration files.
    
    Returns:
        dict: Reload status with count of loaded agents
    """
    try:
        agents = load_agent_configs_from_yaml()
        
        # Clear and re-register all agents
        agent_registry.clear()
        for agent in agents:
            agent_registry.register_agent(agent)
        
        logger.info("Agents reloaded from YAML", count=len(agents))
        return {
            "status": "success",
            "agents_loaded": len(agents),
            "agents": [{"id": a.id, "name": a.config.name} for a in agents]
        }
    except Exception as e:
        logger.error("Error reloading agents from YAML", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
