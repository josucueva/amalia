"""
MCP Server configuration models.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List


class MCPServer(BaseModel):
    """MCP Server configuration."""

    id: str = Field(..., description="Unique identifier for the MCP server")
    name: str = Field(..., description="Display name for the MCP server")
    command: str = Field(..., description="Command to execute MCP server")
    args: List[str] = Field(default_factory=list, description="Command arguments")
    env: Optional[Dict[str, str]] = Field(
        default=None, description="Environment variables"
    )
    description: Optional[str] = Field(
        None, description="Description of the MCP server"
    )
    is_available: bool = Field(
        True, description="Whether the server is available for use"
    )


class MCPServerCreateRequest(BaseModel):
    """Request to create a new MCP server."""

    name: str = Field(..., description="Display name for the MCP server")
    command: str = Field(..., description="Command to execute MCP server")
    args: List[str] = Field(default_factory=list, description="Command arguments")
    env: Optional[Dict[str, str]] = Field(
        default=None, description="Environment variables"
    )
    description: Optional[str] = Field(
        None, description="Description of the MCP server"
    )


class MCPServerListResponse(BaseModel):
    """Response containing a list of MCP servers."""

    servers: List[MCPServer]
    count: int
