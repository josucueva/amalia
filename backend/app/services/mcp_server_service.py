"""
MCP Server persistence and management service.
"""
import json
import uuid
from pathlib import Path
from typing import Optional, Dict
import structlog

from app.models.mcp_server import MCPServer

logger = structlog.get_logger()


class MCPServerService:
    """Service for managing persisted MCP servers."""

    def __init__(self, servers_file: Path = None):
        """
        Initialize the MCP server service.

        Args:
            servers_file: Path to JSON file storing MCP servers
        """
        if servers_file is None:
            servers_file = Path("data/mcp_servers.json")

        self.servers_file = servers_file
        self.servers: Dict[str, MCPServer] = {}

        # Ensure data directory exists
        self.servers_file.parent.mkdir(parents=True, exist_ok=True)

        # Load servers from file if it exists
        if self.servers_file.exists():
            self._load_servers()
        else:
            # Create empty servers file
            self._save_servers()
            logger.info("MCP servers file created", file=str(self.servers_file))

    def _load_servers(self):
        """Load MCP servers from JSON file."""
        try:
            with open(self.servers_file, 'r') as f:
                data = json.load(f)
                self.servers = {
                    server_id: MCPServer(**server_data)
                    for server_id, server_data in data.items()
                }
            logger.info("MCP servers loaded", count=len(self.servers), file=str(self.servers_file))
        except Exception as e:
            logger.error("Error loading MCP servers", error=str(e), file=str(self.servers_file))
            # Don't create defaults on error - let user explicitly add servers
            self.servers = {}
            logger.warning("Started with empty MCP servers list")

    def _create_default_servers(self):
        """Create default MCP server configurations."""
        default_servers = [
            MCPServer(
                id="filesystem",
                name="Filesystem",
                command="npx",
                args=["-y", "@modelcontextprotocol/server-filesystem", "/app/data/uploads"],
                env={},
                description="Access and manage files in the uploads directory",
                is_available=True
            ),
        ]

        self.servers = {server.id: server for server in default_servers}
        self._save_servers()
        logger.info("Default MCP servers created", count=len(self.servers))

    def _save_servers(self):
        """Save MCP servers to JSON file atomically."""
        try:
            # Write to temporary file first
            temp_file = self.servers_file.with_suffix('.tmp')
            data = {server_id: server.model_dump() for server_id, server in self.servers.items()}

            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2)

            # Atomic replace
            temp_file.replace(self.servers_file)
            logger.info("MCP servers saved", count=len(self.servers), file=str(self.servers_file))
        except Exception as e:
            logger.error("Error saving MCP servers", error=str(e), file=str(self.servers_file))
            raise

    def get_all_servers(self) -> list[MCPServer]:
        """
        Get all MCP servers.

        Returns:
            List of all MCP servers
        """
        return list(self.servers.values())

    def get_available_servers(self) -> list[MCPServer]:
        """
        Get only available MCP servers.

        Returns:
            List of available MCP servers
        """
        return [server for server in self.servers.values() if server.is_available]

    def get_server(self, server_id: str) -> Optional[MCPServer]:
        """
        Get a specific MCP server by ID.

        Args:
            server_id: The server ID

        Returns:
            The MCP server or None if not found
        """
        return self.servers.get(server_id)

    def add_server(self, server: MCPServer) -> MCPServer:
        """
        Add a new MCP server.

        Args:
            server: The server to add

        Returns:
            The added server
        """
        if server.id in self.servers:
            raise ValueError(f"MCP server with ID {server.id} already exists")

        self.servers[server.id] = server
        self._save_servers()
        logger.info("MCP server added", server_id=server.id, name=server.name)
        return server

    def update_server(self, server_id: str, server: MCPServer) -> MCPServer:
        """
        Update an existing MCP server.

        Args:
            server_id: The ID of the server to update
            server: The updated server data

        Returns:
            The updated server
        """
        if server_id not in self.servers:
            raise ValueError(f"MCP server with ID {server_id} not found")

        # Ensure ID matches
        server.id = server_id
        self.servers[server_id] = server
        self._save_servers()
        logger.info("MCP server updated", server_id=server_id)
        return server

    def delete_server(self, server_id: str) -> bool:
        """
        Delete an MCP server.

        Args:
            server_id: The ID of the server to delete

        Returns:
            True if deleted, False if not found
        """
        if server_id in self.servers:
            del self.servers[server_id]
            self._save_servers()
            logger.info("MCP server deleted", server_id=server_id)
            return True
        return False


# Singleton instance
_mcp_server_service: Optional[MCPServerService] = None


def get_mcp_server_service() -> MCPServerService:
    """Get the singleton MCP server service instance."""
    global _mcp_server_service
    if _mcp_server_service is None:
        _mcp_server_service = MCPServerService()
    return _mcp_server_service
