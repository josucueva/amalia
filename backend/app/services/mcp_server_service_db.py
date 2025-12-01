"""
MongoDB-based MCP Server persistence and management service.
"""

import uuid
from typing import Dict, List, Optional
import structlog

from app.models.mcp_server import MCPServer
from app.database import get_db

logger = structlog.get_logger()


class MCPServerService:
    """Service for managing persisted MCP servers using MongoDB."""

    def __init__(self):
        """Initialize the MCP server service."""
        self.collection_name = "mcp_servers"

    def _get_collection(self):
        """Get MCP servers collection."""
        return get_db()[self.collection_name]

    async def initialize_default_servers(self):
        """Create default MCP server configurations if collection is empty."""
        collection = self._get_collection()
        count = await collection.count_documents({})

        if count == 0:
            default_servers = self._get_default_servers()
            if default_servers:
                await collection.insert_many([s.model_dump() for s in default_servers])
                logger.info(
                    "Default MCP servers initialized", count=len(default_servers)
                )

    def _get_default_servers(self) -> List[MCPServer]:
        """Get default MCP server configurations."""
        return [
            MCPServer(
                id="filesystem",
                name="Filesystem",
                command="npx",
                args=[
                    "-y",
                    "@modelcontextprotocol/server-filesystem",
                    "/app/data/uploads",
                ],
                env={},
                description="Access and manage files in the uploads directory",
                is_available=True,
            ),
        ]

    async def get_server(self, server_id: str) -> Optional[MCPServer]:
        """
        Get an MCP server by ID.

        Args:
            server_id: Server ID

        Returns:
            MCPServer or None if not found
        """
        collection = self._get_collection()
        data = await collection.find_one({"id": server_id})

        if data:
            data.pop("_id", None)
            return MCPServer(**data)
        return None

    async def list_servers(self, available_only: bool = False) -> List[MCPServer]:
        """
        List all MCP servers.

        Args:
            available_only: Only return available servers

        Returns:
            List of MCP servers
        """
        collection = self._get_collection()

        query = {}
        if available_only:
            query["is_available"] = True

        servers = []
        async for doc in collection.find(query):
            doc.pop("_id", None)
            servers.append(MCPServer(**doc))

        return servers

    async def add_server(self, server: MCPServer) -> MCPServer:
        """
        Add a new MCP server.

        Args:
            server: Server to add

        Returns:
            Added server

        Raises:
            ValueError: If server ID already exists
        """
        collection = self._get_collection()

        # Check if exists
        existing = await collection.find_one({"id": server.id})
        if existing:
            raise ValueError(f"MCP server with ID '{server.id}' already exists")

        # Generate ID if not provided
        if not server.id:
            server.id = f"mcp_{uuid.uuid4().hex[:12]}"

        await collection.insert_one(server.model_dump())
        logger.info("MCP server added", server_id=server.id, name=server.name)
        return server

    async def update_server(
        self, server_id: str, server: MCPServer
    ) -> Optional[MCPServer]:
        """
        Update an existing MCP server.

        Args:
            server_id: Server ID
            server: Updated server data

        Returns:
            Updated server or None if not found
        """
        collection = self._get_collection()

        result = await collection.replace_one({"id": server_id}, server.model_dump())

        if result.matched_count == 0:
            return None

        logger.info("MCP server updated", server_id=server_id)
        return server

    async def delete_server(self, server_id: str) -> bool:
        """
        Delete an MCP server.

        Args:
            server_id: Server ID

        Returns:
            True if deleted, False if not found
        """
        collection = self._get_collection()
        result = await collection.delete_one({"id": server_id})

        if result.deleted_count > 0:
            logger.info("MCP server deleted", server_id=server_id)
            return True
        return False

    async def set_server_availability(self, server_id: str, is_available: bool) -> bool:
        """
        Set MCP server availability status.

        Args:
            server_id: Server ID
            is_available: Availability status

        Returns:
            True if updated, False if not found
        """
        collection = self._get_collection()

        result = await collection.update_one(
            {"id": server_id}, {"$set": {"is_available": is_available}}
        )

        if result.matched_count > 0:
            logger.info(
                "MCP server availability updated",
                server_id=server_id,
                is_available=is_available,
            )
            return True
        return False

    async def get_servers_dict(self) -> Dict[str, MCPServer]:
        """
        Get all servers as a dictionary.

        Returns:
            Dictionary mapping server IDs to MCPServer objects
        """
        servers = await self.list_servers()
        return {server.id: server for server in servers}
