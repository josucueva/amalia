"""
Agent data models.
"""

from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    """Agent status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    BUSY = "busy"


class MCPServerConfig(BaseModel):
    """MCP server configuration."""

    command: str = Field(..., description="Command to execute MCP server")
    args: List[str] = Field(default_factory=list, description="Command arguments")
    env: Optional[Dict[str, str]] = Field(
        default=None, description="Environment variables"
    )


class CommunicationConfig(BaseModel):
    """Agent communication configuration."""

    can_receive_from: List[str] = Field(
        default_factory=lambda: ["*"], description="List of agent IDs or '*' for all"
    )
    can_send_to: List[str] = Field(
        default_factory=list, description="List of agent IDs this agent can send to"
    )


class AgentConfig(BaseModel):
    """Agent configuration model."""

    name: str = Field(..., description="Agent name", min_length=1)
    description: str = Field(..., description="Agent description")
    model: str = Field(default="gpt-4o", description="LLM model to use")
    system_prompt: str = Field(..., description="System prompt defining agent behavior")
    provider: str = Field(
        default="internal",
        description="Agent provider (e.g., internal, google, aws, anthropic, custom)",
    )
    remote_endpoint: Optional[str] = Field(
        default=None,
        description="Remote HTTP endpoint for external agent execution",
    )
    icon: Optional[str] = Field(
        default=None, description="Icon emoji for visual representation"
    )
    a2a_enabled: bool = Field(default=False, description="Enable A2A communication")
    a2a_mode: str = Field(
        default="messaging",
        description="A2A mode: 'messaging' (send only) or 'autonomous' (listen and auto-execute)"
    )
    tools: List[str] = Field(
        default_factory=list, description="List of tool names this agent can use"
    )
    mcp_servers: Dict[str, MCPServerConfig] = Field(
        default_factory=dict, description="MCP servers configuration (legacy)"
    )
    mcp_server_ids: List[str] = Field(
        default_factory=list, description="IDs of MCP servers this agent uses"
    )
    communication: CommunicationConfig = Field(default_factory=CommunicationConfig)
    temperature: float = Field(
        default=0.7, ge=0.0, le=2.0, description="LLM temperature"
    )
    max_tokens: int = Field(
        default=2000, gt=0, description="Maximum tokens for response"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "data_preprocessor",
                "description": "Handles data cleaning and transformation",
                "model": "gpt-4o",
                "system_prompt": "You are a data preprocessing expert...",
                "provider": "internal",
                "remote_endpoint": None,
                "a2a_enabled": True,
                "tools": ["csv_reader", "data_transformer"],
                "communication": {
                    "can_receive_from": ["*"],
                    "can_send_to": ["model_trainer"],
                },
            }
        }


class Agent(BaseModel):
    """Agent instance model."""

    id: str = Field(..., description="Unique agent ID")
    config: AgentConfig = Field(..., description="Agent configuration")
    status: AgentStatus = Field(default=AgentStatus.ACTIVE)
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: Optional[str] = Field(default=None, description="Last update timestamp")

    def is_hidden(self) -> bool:
        """Check if agent is hidden from UI."""
        if self.config.metadata:
            return self.config.metadata.get("is_hidden", False)
        return False

    class Config:
        json_schema_extra = {
            "example": {
                "id": "agent_123",
                "config": {
                    "name": "data_preprocessor",
                    "description": "Handles data cleaning",
                    "model": "gpt-4o",
                    "system_prompt": "You are a data expert",
                    "a2a_enabled": True,
                    "tools": ["csv_reader"],
                },
                "status": "active",
                "created_at": "2025-11-26T10:00:00Z",
            }
        }


class AgentCreateRequest(BaseModel):
    """Request model for creating an agent."""

    config: AgentConfig

    class Config:
        json_schema_extra = {
            "example": {
                "config": {
                    "name": "data_preprocessor",
                    "description": "Handles data cleaning and transformation",
                    "model": "gpt-4o",
                    "system_prompt": "You are a data preprocessing expert...",
                    "tools": ["csv_reader"],
                }
            }
        }


class AgentListResponse(BaseModel):
    """Response model for listing agents."""

    agents: List[Agent]
    total: int

    class Config:
        json_schema_extra = {"example": {"agents": [], "total": 0}}
