"""
Data models for the application.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Message role enumeration."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    AGENT = "agent"


class MessageStatus(str, Enum):
    """Message status enumeration."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Message(BaseModel):
    """Chat message model."""

    id: str = Field(..., description="Unique message ID")
    role: MessageRole = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: MessageStatus = Field(default=MessageStatus.COMPLETED)
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata"
    )
    agent_id: Optional[str] = Field(
        default=None, description="ID of the agent that created this message"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "msg_123",
                "role": "user",
                "content": "Analyze the sales data",
                "timestamp": "2025-11-26T10:30:00Z",
                "status": "completed",
            }
        }


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    message: str = Field(..., description="User message", min_length=1)
    conversation_id: Optional[str] = Field(
        default=None, description="Conversation ID for context (deprecated, use session_id)"
    )
    session_id: Optional[str] = Field(
        default=None, description="Session ID for persistent chat history"
    )
    stream: bool = Field(default=False, description="Enable streaming response")
    attached_file: Optional[Dict[str, Any]] = Field(
        default=None, description="Information about attached file"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Load the sales.csv file and show me the first 5 rows",
                "conversation_id": "conv_123",
                "stream": False,
                "attached_file": {
                    "filename": "sales.csv",
                    "path": "/app/data/uploads/abc123_sales.csv",
                    "size_mb": 1.5,
                },
            }
        }


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    message: Message
    conversation_id: str = Field(..., description="Conversation ID")
    agents_involved: List[str] = Field(
        default_factory=list,
        description="List of agent IDs that processed this message",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "message": {
                    "id": "msg_456",
                    "role": "assistant",
                    "content": "Here are the first 5 rows of sales.csv...",
                    "timestamp": "2025-11-26T10:30:05Z",
                    "status": "completed",
                },
                "conversation_id": "conv_123",
                "agents_involved": ["data_preprocessor"],
            }
        }
