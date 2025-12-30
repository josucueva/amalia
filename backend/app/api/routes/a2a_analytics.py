"""
A2A Analytics and Monitoring Routes.

Provides endpoints to track and analyze A2A communication patterns.
"""

from fastapi import APIRouter, Request, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger()
router = APIRouter()


class A2AStats(BaseModel):
    """A2A communication statistics."""
    total_messages: int
    messages_by_agent: Dict[str, int]
    recent_messages: List[Dict[str, Any]]
    active_agents: List[str]


@router.get("/stats", response_model=A2AStats)
async def get_a2a_stats(
    request: Request,
    hours: int = Query(24, description="Time window in hours"),
    limit: int = Query(50, description="Max recent messages to return"),
):
    """
    Get A2A communication statistics and recent activity.
    
    Shows:
    - Total messages in time window
    - Messages sent/received per agent
    - Recent message list
    - List of agents actively using A2A
    """
    try:
        a2a_service = getattr(request.app.state, "a2a_service", None)
        if a2a_service is None or a2a_service._db is None:
            return A2AStats(
                total_messages=0,
                messages_by_agent={},
                recent_messages=[],
                active_agents=[],
            )
        
        # Calculate time threshold
        time_threshold = datetime.utcnow() - timedelta(hours=hours)
        
        # Query recent messages
        cursor = a2a_service._db.a2a_messages.find(
            {"timestamp": {"$gte": time_threshold}}
        ).sort("timestamp", -1).limit(limit)
        
        messages = await cursor.to_list(length=limit)
        
        # Calculate statistics
        messages_by_agent = {}
        active_agents = set()
        
        for msg in messages:
            from_agent = msg.get("from_agent", "unknown")
            to_agent = msg.get("to_agent", "unknown")
            
            # Count messages per agent
            messages_by_agent[from_agent] = messages_by_agent.get(from_agent, 0) + 1
            
            # Track active agents
            active_agents.add(from_agent)
            if to_agent != "*":  # Don't count broadcast target
                active_agents.add(to_agent)
        
        # Format recent messages for response
        recent_messages_formatted = [
            {
                "from": msg.get("from_agent"),
                "to": msg.get("to_agent"),
                "type": msg.get("message_type"),
                "timestamp": msg.get("timestamp").isoformat() if msg.get("timestamp") else None,
                "correlation_id": msg.get("correlation_id"),
            }
            for msg in messages
        ]
        
        logger.info(
            "A2A statistics requested",
            hours=hours,
            total_messages=len(messages),
            active_agents=len(active_agents),
        )
        
        return A2AStats(
            total_messages=len(messages),
            messages_by_agent=messages_by_agent,
            recent_messages=recent_messages_formatted,
            active_agents=sorted(list(active_agents)),
        )
        
    except Exception as e:
        logger.error("Error fetching A2A stats", error=str(e))
        return A2AStats(
            total_messages=0,
            messages_by_agent={},
            recent_messages=[],
            active_agents=[],
        )


@router.get("/trace/{correlation_id}")
async def trace_message(
    correlation_id: str,
    request: Request,
):
    """
    Trace a message by correlation ID.
    
    Shows the full message chain for request/reply patterns.
    """
    try:
        a2a_service = getattr(request.app.state, "a2a_service", None)
        if a2a_service is None or a2a_service._db is None:
            return {
                "found": False,
                "message": "A2A service not available"
            }
        
        # Find all messages with this correlation ID
        cursor = a2a_service._db.a2a_messages.find(
            {"correlation_id": correlation_id}
        ).sort("timestamp", 1)
        
        messages = await cursor.to_list(length=100)
        
        if not messages:
            return {
                "found": False,
                "correlation_id": correlation_id,
                "message": "No messages found with this correlation ID"
            }
        
        # Format message chain
        chain = [
            {
                "from_agent": msg.get("from_agent"),
                "to_agent": msg.get("to_agent"),
                "message_type": msg.get("message_type"),
                "content": msg.get("content"),
                "timestamp": msg.get("timestamp").isoformat() if msg.get("timestamp") else None,
            }
            for msg in messages
        ]
        
        logger.info(
            "Message traced",
            correlation_id=correlation_id,
            message_count=len(chain),
        )
        
        return {
            "found": True,
            "correlation_id": correlation_id,
            "message_count": len(chain),
            "chain": chain,
        }
        
    except Exception as e:
        logger.error("Error tracing message", error=str(e))
        return {
            "found": False,
            "error": str(e)
        }


@router.get("/agents-using-a2a")
async def get_agents_using_a2a(request: Request):
    """
    List all agents that have A2A enabled.
    
    Returns agent names, IDs, and their communication configurations.
    """
    try:
        agent_registry = getattr(request.app.state, "agent_registry", None)
        if not agent_registry:
            return {
                "agents": [],
                "total": 0
            }
        
        agents = agent_registry.list_agents()
        a2a_enabled_agents = [
            {
                "id": agent.id,
                "name": agent.config.name,
                "can_send_to": agent.config.communication.can_send_to,
                "can_receive_from": agent.config.communication.can_receive_from,
                "provider": agent.config.provider,
            }
            for agent in agents
            if agent.config.a2a_enabled
        ]
        
        logger.info(
            "A2A enabled agents listed",
            total=len(a2a_enabled_agents),
        )
        
        return {
            "agents": a2a_enabled_agents,
            "total": len(a2a_enabled_agents),
        }
        
    except Exception as e:
        logger.error("Error listing A2A agents", error=str(e))
        return {
            "agents": [],
            "total": 0,
            "error": str(e)
        }
