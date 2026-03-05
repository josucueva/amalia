"""
API routes for MCP server management.
"""

import os
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
import structlog
import uuid

from app.models.mcp_server import (
    MCPServer,
    MCPServerCreateRequest,
    MCPServerListResponse,
)
from app.services.mcp_tool_catalog import get_mcp_tool_catalog

router = APIRouter(prefix="/api/mcp-servers", tags=["mcp-servers"])
logger = structlog.get_logger()


@router.get("", response_model=MCPServerListResponse)
async def list_mcp_servers(request: Request, available_only: bool = False):
    """
    Get all MCP servers or only available ones.

    Args:
        available_only: If True, only return available servers

    Returns:
        List of MCP servers
    """
    try:
        service = request.app.state.mcp_server_service
        servers = await service.list_servers(available_only=available_only)
        return MCPServerListResponse(servers=servers, count=len(servers))
    except Exception as e:
        logger.error("Error listing MCP servers", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{server_id}", response_model=MCPServer)
async def get_mcp_server(request: Request, server_id: str):
    """
    Get a specific MCP server by ID.

    Args:
        server_id: The server ID

    Returns:
        The MCP server
    """
    try:
        service = request.app.state.mcp_server_service
        server = await service.get_server(server_id)

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


@router.get("/{server_id}/tools")
async def get_mcp_server_tools(request: Request, server_id: str):
    """
    Get available tools from an MCP server.

    Args:
        server_id: The server ID

    Returns:
        List of tools with their schemas
    """
    try:
        catalog = get_mcp_tool_catalog()
        tools = catalog.get_tools_for_server(server_id)
        
        tools_data = []
        for tool in tools:
            tools_data.append({
                "name": tool.name,
                "description": tool.description,
                "parameters": [
                    {
                        "name": p.name,
                        "type": p.type,
                        "description": p.description,
                        "required": p.required,
                        "default": p.default
                    }
                    for p in tool.parameters
                ],
                "returnType": tool.return_type,
                "category": tool.category
            })
        
        logger.info("MCP tools retrieved", server_id=server_id, tool_count=len(tools))
        return {
            "server_id": server_id,
            "server_name": tools[0].server_name if tools else server_id,
            "tools": tools_data,
            "count": len(tools_data)
        }
    except Exception as e:
        logger.error("Error getting MCP server tools", server_id=server_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/catalog/all")
async def get_tool_catalog(request: Request):
    """
    Get the complete tool catalog across all MCP servers.
    
    Returns:
        Complete tool catalog with categorized tools
    """
    try:
        catalog = get_mcp_tool_catalog()
        summary = catalog.get_tools_summary()
        
        logger.info("Tool catalog retrieved", total_tools=summary["total_tools"])
        return summary
    except Exception as e:
        logger.error("Error getting tool catalog", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=MCPServer)
async def create_mcp_server(request: Request, req: MCPServerCreateRequest):
    """
    Create a new MCP server.

    Args:
        req: MCP server creation request

    Returns:
        The created server
    """
    try:
        service = request.app.state.mcp_server_service

        # Generate unique ID from name
        server_id = req.name.lower().replace(" ", "-").replace("_", "-")

        # If ID exists, append random suffix
        if await service.get_server(server_id):
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

        created_server = await service.add_server(server)
        logger.info("MCP server created", server_id=server_id, name=req.name)

        return created_server
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error creating MCP server", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{server_id}", response_model=MCPServer)
async def update_mcp_server(
    request: Request, server_id: str, req: MCPServerCreateRequest
):
    """
    Update an existing MCP server.

    Args:
        server_id: The server ID
        req: MCP server update request

    Returns:
        The updated server
    """
    try:
        service = request.app.state.mcp_server_service

        server = MCPServer(
            id=server_id,
            name=req.name,
            command=req.command,
            args=req.args,
            env=req.env,
            description=req.description,
            is_available=True,
        )

        updated_server = await service.update_server(server_id, server)
        logger.info("MCP server updated", server_id=server_id)

        return updated_server
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Error updating MCP server", server_id=server_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{server_id}")
async def delete_mcp_server(request: Request, server_id: str):
    """
    Delete an MCP server.

    Args:
        server_id: The server ID

    Returns:
        Success message
    """
    try:
        service = request.app.state.mcp_server_service
        success = await service.delete_server(server_id)

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


# ============================================================================
# Python MCP Server Routes
# ============================================================================


class PythonMCPServerRequest(BaseModel):
    """Request to create/update Python MCP server."""
    name: str = Field(..., description="Display name for the server")
    server_id: str = Field(..., description="Unique server ID (directory name)")
    description: Optional[str] = Field(None, description="Server description")
    allowed_paths: List[str] = Field(
        default_factory=lambda: ["/app/data/uploads"],
        description="Paths the server can access"
    )


class PythonMCPServerResponse(BaseModel):
    """Response for Python MCP server."""
    server_id: str
    name: str
    path: str
    command: str
    args: List[str]
    allowed_paths: List[str]
    env: Dict[str, str]
    description: Optional[str]
    dependencies_file: Optional[str]
    is_valid: bool
    dependencies_installed: bool


@router.get("/python", response_model=Dict[str, PythonMCPServerResponse])
async def list_python_mcp_servers(request: Request):
    """
    Get all Python MCP servers from configuration.

    Returns:
        Dictionary of Python MCP servers with their status
    """
    try:
        python_mcp_manager = request.app.state.python_mcp_manager
        servers = python_mcp_manager.list_servers()
        
        response = {}
        for server_id, config in servers.items():
            is_valid = python_mcp_manager.validate_server(server_id)
            
            response[server_id] = PythonMCPServerResponse(
                server_id=config.server_id,
                name=config.name,
                path=config.path,
                command=config.command,
                args=config.args,
                allowed_paths=config.allowed_paths,
                env=config.env,
                description=config.description,
                dependencies_file=config.dependencies_file,
                is_valid=is_valid,
                dependencies_installed=True,  # Assume installed at startup
            )
        
        return response
    except Exception as e:
        logger.error("Error listing Python MCP servers", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/python/{server_id}", response_model=PythonMCPServerResponse)
async def get_python_mcp_server(request: Request, server_id: str):
    """
    Get a specific Python MCP server.

    Args:
        server_id: The server ID

    Returns:
        The Python MCP server configuration and status
    """
    try:
        python_mcp_manager = request.app.state.python_mcp_manager
        config = python_mcp_manager.get_server(server_id)
        
        if not config:
            raise HTTPException(
                status_code=404,
                detail=f"Python MCP server '{server_id}' not found"
            )
        
        is_valid = python_mcp_manager.validate_server(server_id)
        
        return PythonMCPServerResponse(
            server_id=config.server_id,
            name=config.name,
            path=config.path,
            command=config.command,
            args=config.args,
            allowed_paths=config.allowed_paths,
            env=config.env,
            description=config.description,
            dependencies_file=config.dependencies_file,
            is_valid=is_valid,
            dependencies_installed=True,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting Python MCP server", server_id=server_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/python/{server_id}/register")
async def register_python_mcp_server(
    request: Request,
    server_id: str,
    req: PythonMCPServerRequest
):
    """
    Register a Python MCP server that exists in the mcp_servers directory.
    
    The server's Python file should already exist at:
    /app/mcp_servers/{server_id}/server.py
    
    Args:
        server_id: Directory name where server.py is located
        req: Server registration request with metadata
        
    Returns:
        The registered server with MCP server ID
    """
    try:
        from app.utils.python_mcp_manager import PythonMCPConfig
        
        python_mcp_manager = request.app.state.python_mcp_manager
        mcp_server_service = request.app.state.mcp_server_service
        
        # Build paths
        server_path = f"/app/mcp_servers/{server_id}/server.py"
        deps_file = f"/app/mcp_servers/{server_id}/requirements.txt"
        
        # Create Python MCP config
        python_config = PythonMCPConfig(
            server_id=server_id,
            name=req.name,
            path=server_path,
            command="python",
            args=[],
            allowed_paths=req.allowed_paths,
            env={"PYTHONPATH": "/app"},
            description=req.description,
            dependencies_file=deps_file if os.path.exists(deps_file) else None,
        )
        
        # Add to Python MCP manager
        python_mcp_manager.add_server(python_config)
        
        # Validate and install dependencies
        is_valid = python_mcp_manager.validate_server(server_id)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"Server file not found at {server_path}"
            )
        
        deps_installed = python_mcp_manager.install_dependencies(server_id)
        
        # Also register in main MCP server database for frontend
        mcp_server = MCPServer(
            id=f"python-{server_id}",
            name=req.name,
            command="python",
            args=[server_path],
            env={"PYTHONPATH": "/app"},
            description=req.description or f"Python MCP Server: {req.name}",
            is_available=True,
        )
        
        await mcp_server_service.add_server(mcp_server)
        
        logger.info(
            "Python MCP server registered",
            server_id=server_id,
            valid=is_valid,
            dependencies_installed=deps_installed,
        )
        
        return {
            "message": "Python MCP server registered successfully",
            "server_id": server_id,
            "mcp_server_id": f"python-{server_id}",
            "path": server_path,
            "is_valid": is_valid,
            "dependencies_installed": deps_installed,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error registering Python MCP server", server_id=server_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/python/{server_id}/install-dependencies")
async def install_python_server_dependencies(request: Request, server_id: str):
    """
    Install or reinstall dependencies for a Python MCP server.

    Args:
        server_id: The server ID

    Returns:
        Installation status
    """
    try:
        import os
        
        python_mcp_manager = request.app.state.python_mcp_manager
        
        config = python_mcp_manager.get_server(server_id)
        if not config:
            raise HTTPException(
                status_code=404,
                detail=f"Python MCP server '{server_id}' not found"
            )
        
        success = python_mcp_manager.install_dependencies(server_id)
        
        return {
            "message": "Dependencies installation " + ("succeeded" if success else "failed"),
            "server_id": server_id,
            "success": success,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error installing dependencies",
            server_id=server_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))
