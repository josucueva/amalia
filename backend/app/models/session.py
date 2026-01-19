"""
Session models for managing chat history and pipeline state.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum


class SessionStatus(str, Enum):
    """Session status enum."""

    ACTIVE = "active"
    ARCHIVED = "archived"


class PipelineSnapshot(BaseModel):
    """Snapshot of a pipeline configuration."""

    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    connections: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class SessionMessage(BaseModel):
    """Message in a session."""

    role: str
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    metadata: Optional[Dict[str, Any]] = None


class Session(BaseModel):
    """Session model containing chat history and pipelines."""

    id: str
    title: str = Field(default="New Session")
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    messages: List[SessionMessage] = Field(default_factory=list)
    pipelines: List[PipelineSnapshot] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SessionCreateRequest(BaseModel):
    """Request to create a new session."""

    title: Optional[str] = None


class SessionUpdateRequest(BaseModel):
    """Request to update a session."""

    title: Optional[str] = None
    status: Optional[SessionStatus] = None


class SessionListResponse(BaseModel):
    """Response with list of sessions."""

    sessions: List[Session]
    total: int


class AddMessageRequest(BaseModel):
    """Request to add a message to a session."""

    role: str
    content: str
    metadata: Optional[Dict[str, Any]] = None


class AddPipelineRequest(BaseModel):
    """Request to add a pipeline snapshot to a session."""

    nodes: List[Dict[str, Any]]
    connections: List[Dict[str, Any]]
