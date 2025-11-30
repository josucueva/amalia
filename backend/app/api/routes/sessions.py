"""
Session management API routes.
"""

from fastapi import APIRouter, HTTPException, Request
from typing import Optional
import structlog

from app.models.session import (
    Session,
    SessionCreateRequest,
    SessionUpdateRequest,
    SessionListResponse,
    SessionStatus,
    AddMessageRequest,
    AddPipelineRequest,
)

logger = structlog.get_logger()
router = APIRouter()


def get_session_manager(req: Request):
    """Get session manager from app state."""
    if not hasattr(req.app.state, "session_manager"):
        from app.services.session_manager import SessionManager

        req.app.state.session_manager = SessionManager()
    return req.app.state.session_manager


@router.post("/", response_model=Session)
async def create_session(
    request_data: SessionCreateRequest,
    request: Request,
):
    """
    Create a new session.

    Args:
        request_data: Session creation request
        request: FastAPI request object

    Returns:
        Created session
    """
    try:
        session_manager = get_session_manager(request)
        session = session_manager.create_session(title=request_data.title)
        return session
    except Exception as e:
        logger.error("Error creating session", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=SessionListResponse)
async def list_sessions(
    request: Request,
    status: Optional[SessionStatus] = None,
    limit: Optional[int] = None,
):
    """
    List all sessions.

    Args:
        request: FastAPI request object
        status: Optional status filter
        limit: Optional limit

    Returns:
        List of sessions
    """
    try:
        session_manager = get_session_manager(request)
        sessions = session_manager.list_sessions(status=status, limit=limit)
        return SessionListResponse(sessions=sessions, total=len(sessions))
    except Exception as e:
        logger.error("Error listing sessions", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}", response_model=Session)
async def get_session(session_id: str, request: Request):
    """
    Get a specific session.

    Args:
        session_id: Session ID
        request: FastAPI request object

    Returns:
        Session
    """
    try:
        session_manager = get_session_manager(request)
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        return session
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting session", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{session_id}", response_model=Session)
async def update_session(
    session_id: str,
    request_data: SessionUpdateRequest,
    request: Request,
):
    """
    Update a session.

    Args:
        session_id: Session ID
        request_data: Update request
        request: FastAPI request object

    Returns:
        Updated session
    """
    try:
        session_manager = get_session_manager(request)
        session = session_manager.update_session(
            session_id=session_id,
            title=request_data.title,
            status=request_data.status,
        )
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        return session
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating session", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{session_id}")
async def delete_session(session_id: str, request: Request):
    """
    Delete a session.

    Args:
        session_id: Session ID
        request: FastAPI request object

    Returns:
        Success message
    """
    try:
        session_manager = get_session_manager(request)
        if not session_manager.delete_session(session_id):
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        return {"success": True, "message": f"Session {session_id} deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting session", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/messages")
async def add_message_to_session(
    session_id: str,
    request_data: AddMessageRequest,
    request: Request,
):
    """
    Add a message to a session.

    Args:
        session_id: Session ID
        request_data: Message data
        request: FastAPI request object

    Returns:
        Success message
    """
    try:
        session_manager = get_session_manager(request)
        if not session_manager.add_message(
            session_id=session_id,
            role=request_data.role,
            content=request_data.content,
            metadata=request_data.metadata,
        ):
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error adding message to session", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/pipelines")
async def add_pipeline_to_session(
    session_id: str,
    request_data: AddPipelineRequest,
    request: Request,
):
    """
    Add a pipeline snapshot to a session.

    Args:
        session_id: Session ID
        request_data: Pipeline data
        request: FastAPI request object

    Returns:
        Success message
    """
    try:
        session_manager = get_session_manager(request)
        if not session_manager.add_pipeline(
            session_id=session_id,
            nodes=request_data.nodes,
            connections=request_data.connections,
        ):
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error adding pipeline to session", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{session_id}/messages")
async def clear_session_messages(session_id: str, request: Request):
    """
    Clear all messages from a session.

    Args:
        session_id: Session ID
        request: FastAPI request object

    Returns:
        Success message
    """
    try:
        session_manager = get_session_manager(request)
        if not session_manager.clear_session_messages(session_id):
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        return {"success": True, "message": "Messages cleared"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error clearing session messages", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
