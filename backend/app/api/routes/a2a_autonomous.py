"""
A2A Autonomous Mode Routes.

Endpoints for managing and monitoring autonomous A2A agents.
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import List
import structlog

logger = structlog.get_logger()
router = APIRouter()


class AutonomousAgentsResponse(BaseModel):
    """Response with autonomous agent information."""
    autonomous_agents: List[str]
    total: int
    messaging_agents: List[str]


@router.get("/autonomous-agents", response_model=AutonomousAgentsResponse)
async def get_autonomous_agents(request: Request):
    """
    Get list of agents running in autonomous mode.
    
    Autonomous agents listen to their inbox and auto-execute when messages arrive.
    """
    try:
        listener_manager = getattr(request.app.state, "listener_manager", None)
        agent_registry = getattr(request.app.state, "agent_registry", None)
        
        if not listener_manager or not agent_registry:
            return AutonomousAgentsResponse(
                autonomous_agents=[],
                total=0,
                messaging_agents=[]
            )
        
        # Get autonomous agents
        autonomous = listener_manager.get_autonomous_agents()
        
        # Get all A2A enabled agents
        all_agents = agent_registry.list_agents()
        a2a_enabled = [
            agent.id for agent in all_agents
            if agent.config.a2a_enabled
        ]
        
        # Messaging mode = A2A enabled but not autonomous
        messaging = [
            agent_id for agent_id in a2a_enabled
            if agent_id not in autonomous
        ]
        
        logger.info(
            "Autonomous agents query",
            autonomous=len(autonomous),
            messaging=len(messaging)
        )
        
        return AutonomousAgentsResponse(
            autonomous_agents=autonomous,
            total=len(autonomous),
            messaging_agents=messaging
        )
        
    except Exception as e:
        logger.error("Error getting autonomous agents", error=str(e))
        return AutonomousAgentsResponse(
            autonomous_agents=[],
            total=0,
            messaging_agents=[],
        )


@router.get("/mode-explanation")
async def get_mode_explanation():
    """
    Explain the difference between messaging and autonomous A2A modes.
    """
    return {
        "modes": {
            "messaging": {
                "description": "Agents send A2A messages but don't auto-execute",
                "behavior": "Messages are logged and can be queried, but agents are triggered manually",
                "use_case": "Tracking communication without autonomous execution"
            },
            "autonomous": {
                "description": "Agents listen to their inbox and auto-execute when messages arrive",
                "behavior": "Agents subscribe to Redis channels and trigger execution on message receipt",
                "use_case": "True agent-to-agent orchestration with autonomous task delegation"
            }
        },
        "configuration": {
            "agent_yaml": {
                "a2a_enabled": "Set to true to enable A2A features",
                "a2a_mode": "Set to 'messaging' or 'autonomous'"
            }
        }
    }
