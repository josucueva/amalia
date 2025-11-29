"""
API routes for MCP server management.
"""

from fastapi import APIRouter, HTTPException
import structlog
import uuid

from app.models.mcp_server import (
    MCPServer,
    MCPServerCreateRequest,
    MCPServerListResponse,
)
from app.services.mcp_server_service import get_mcp_server_service

router = APIRouter(prefix="/api/mcp-servers", tags=["mcp-servers"])
logger = structlog.get_logger()


@router.get("", response_model=MCPServerListResponse)
async def list_mcp_servers(available_only: bool = False):
    """
    Get all MCP servers or only available ones.

    Args:
        available_only: If True, only return available servers

    Returns:
        List of MCP servers
    """
    try:
        service = get_mcp_server_service()

        if available_only:
            servers = service.get_available_servers()
        else:
            servers = service.get_all_servers()

        return MCPServerListResponse(servers=servers, count=len(servers))
    except Exception as e:
        logger.error("Error listing MCP servers", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{server_id}", response_model=MCPServer)
async def get_mcp_server(server_id: str):
    """
    Get a specific MCP server by ID.

    Args:
        server_id: The server ID

    Returns:
        The MCP server
    """
    try:
        service = get_mcp_server_service()
        server = service.get_server(server_id)

        if not server:
            raise HTTPException(
                status_code=404, detail=f"MCP server {server_id} not found"
            )

        return server
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting MCP server", server_id=server_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=MCPServer)
async def create_mcp_server(req: MCPServerCreateRequest):
    """
    Create a new MCP server.

    Args:
        req: MCP server creation request

    Returns:
        The created server
    """
    try:
        service = get_mcp_server_service()

        # Generate unique ID from name
        server_id = req.name.lower().replace(" ", "-").replace("_", "-")

        # If ID exists, append random suffix
        if service.get_server(server_id):
            server_id = f"{server_id}-{uuid.uuid4().hex[:6]}"

        server = MCPServer(
            id=server_id,
            name=req.name,
            command=req.command,
            args=req.args,
            env=req.env,
            description=req.description,
            is_available=True,
        )

        created_server = service.add_server(server)
        logger.info("MCP server created", server_id=server_id, name=req.name)

        return created_server
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error creating MCP server", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{server_id}", response_model=MCPServer)
async def update_mcp_server(server_id: str, req: MCPServerCreateRequest):
    """
    Update an existing MCP server.

    Args:
        server_id: The server ID
        req: MCP server update request

    Returns:
        The updated server
    """
    try:
        service = get_mcp_server_service()

        server = MCPServer(
            id=server_id,
            name=req.name,
            command=req.command,
            args=req.args,
            env=req.env,
            description=req.description,
            is_available=True,
        )

        updated_server = service.update_server(server_id, server)
        logger.info("MCP server updated", server_id=server_id)

        return updated_server
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Error updating MCP server", server_id=server_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{server_id}")
async def delete_mcp_server(server_id: str):
    """
    Delete an MCP server.

    Args:
        server_id: The server ID

    Returns:
        Success message
    """
    try:
        service = get_mcp_server_service()
        success = service.delete_server(server_id)

        if not success:
            raise HTTPException(
                status_code=404, detail=f"MCP server {server_id} not found"
            )

        logger.info("MCP server deleted", server_id=server_id)
        return {"message": "MCP server deleted successfully", "server_id": server_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting MCP server", server_id=server_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
