"""
A2A communication API routes.

Endpoints for managing agent-to-agent messaging, subscriptions, and message history.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import structlog

from app.models.message import A2AMessage
from app.communication.router import MessageRoutingError

logger = structlog.get_logger()
router = APIRouter()


class SendMessageRequest(BaseModel):
    """Request to send an A2A message."""
    from_agent: str
    to_agent: str
    content: Dict[str, Any]
    message_type: str = "task"


class SendMessageResponse(BaseModel):
    """Response from sending an A2A message."""
    success: bool
    correlation_id: str
    message: str


class MessageHistoryResponse(BaseModel):
    """Response with message history."""
    messages: List[Dict[str, Any]]
    total: int


@router.post("/send", response_model=SendMessageResponse)
async def send_a2a_message(
    request_data: SendMessageRequest,
    request: Request,
):
    """
    Send an A2A message from one agent to another.
    
    Args:
        request_data: Message send request
        request: FastAPI request
        
    Returns:
        SendMessageResponse with correlation ID
    """
    try:
        a2a_service = getattr(request.app.state, "a2a_service", None)
        if not a2a_service:
            raise HTTPException(
                status_code=503,
                detail="A2A service not available"
            )
            
        correlation_id = await a2a_service.send_message(
            from_agent=request_data.from_agent,
            to_agent=request_data.to_agent,
            content=request_data.content,
            message_type=request_data.message_type,
        )
        
        logger.info(
            "A2A message sent via API",
            from_agent=request_data.from_agent,
            to_agent=request_data.to_agent,
            correlation_id=correlation_id,
        )
        
        return SendMessageResponse(
            success=True,
            correlation_id=correlation_id,
            message="Message sent successfully",
        )
        
    except MessageRoutingError as e:
        logger.error("Message routing failed", error=str(e))
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error("Error sending A2A message", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{agent_id}", response_model=MessageHistoryResponse)
async def get_message_history(
    agent_id: str,
    request: Request,
    limit: int = 50,
):
    """
    Get message history for an agent.
    
    Args:
        agent_id: Agent ID
        request: FastAPI request
        limit: Maximum messages to return
        
    Returns:
        MessageHistoryResponse with message list
    """
    try:
        a2a_service = getattr(request.app.state, "a2a_service", None)
        if not a2a_service:
            raise HTTPException(
                status_code=503,
                detail="A2A service not available"
            )
            
        messages = await a2a_service.get_message_history(agent_id, limit=limit)
        
        return MessageHistoryResponse(
            messages=messages,
            total=len(messages),
        )
        
    except Exception as e:
        logger.error("Error fetching message history", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_a2a_status(request: Request):
    """
    Get A2A service status.
    
    Returns:
        Service status information
    """
    try:
        a2a_service = getattr(request.app.state, "a2a_service", None)
        if not a2a_service:
            return {
                "available": False,
                "message": "A2A service not initialized"
            }
            
        return {
            "available": True,
            "connected": a2a_service.is_connected,
            "redis_connected": a2a_service.message_queue.is_connected,
        }
        
    except Exception as e:
        logger.error("Error checking A2A status", error=str(e))
        return {
            "available": False,
            "error": str(e)
        }
