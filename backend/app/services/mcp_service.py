"""
MCP (Model Context Protocol) service for tool execution.

This module implements a client for the Model Context Protocol (MCP),
enabling agents to connect to and use external tools via MCP servers.
"""
import asyncio
import json
import os
from typing import Dict, List, Any, Optional
import structlog

from app.models.agent import MCPServerConfig

logger = structlog.get_logger()

# Default timeout for MCP server operations in seconds
DEFAULT_TIMEOUT = 30.0


class MCPServer:
    """Represents a single MCP server connection."""

    def __init__(self, name: str, config: MCPServerConfig, timeout: float = DEFAULT_TIMEOUT):
        self.name = name
        self.config = config
        self.timeout = timeout
        self.process: Optional[asyncio.subprocess.Process] = None
        self.tools: List[Dict[str, Any]] = []
        self.connected = False
        self._msg_id = 0
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        """Connect to the MCP server via stdio.

        Raises:
            RuntimeError: If the server fails to start or initialize.
        """
        try:
            # Merge custom env with system env (system env as base, custom overrides)
            process_env = os.environ.copy()
            if self.config.env:
                process_env.update(self.config.env)

            self.process = await asyncio.create_subprocess_exec(
                self.config.command,
                *self.config.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=process_env,
            )

            # Initialize connection per MCP protocol
            await self._send_request(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "amalia", "version": "1.0.0"},
                },
            )

            # Send initialized notification (required by MCP protocol)
            await self._send_notification("notifications/initialized", {})

            # Discover available tools
            await self._discover_tools()

            self.connected = True
            logger.info("MCP server connected", server=self.name, tools=len(self.tools))

        except asyncio.TimeoutError:
            await self._cleanup_process()
            raise RuntimeError(f"Timeout connecting to MCP server '{self.name}'")
        except Exception as e:
            await self._cleanup_process()
            logger.error("Failed to connect to MCP server", server=self.name, error=str(e))
            raise RuntimeError(f"Failed to connect to MCP server '{self.name}': {e}")

    async def _send_notification(self, method: str, params: Dict) -> None:
        """Send a JSON-RPC notification (no response expected).

        Args:
            method: The notification method name.
            params: The notification parameters.
        """
        if not self.process or not self.process.stdin:
            raise RuntimeError("MCP server not connected")

        notification = {"jsonrpc": "2.0", "method": method, "params": params}

        notification_str = json.dumps(notification) + "\n"
        self.process.stdin.write(notification_str.encode())
        await self.process.stdin.drain()

    async def _send_request(self, method: str, params: Dict) -> Dict:
        """Send JSON-RPC request to MCP server and wait for response.

        Args:
            method: The RPC method name.
            params: The method parameters.

        Returns:
            The result from the MCP server.

        Raises:
            RuntimeError: If the server is not connected or returns an error.
            asyncio.TimeoutError: If the server doesn't respond in time.
        """
        if not self.process or not self.process.stdin or not self.process.stdout:
            raise RuntimeError("MCP server not connected")

        async with self._lock:
            self._msg_id += 1
            request_id = self._msg_id

            request = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}

            request_str = json.dumps(request) + "\n"
            self.process.stdin.write(request_str.encode())
            await self.process.stdin.drain()

            # Read response with timeout
            try:
                response_line = await asyncio.wait_for(
                    self.process.stdout.readline(), timeout=self.timeout
                )
            except asyncio.TimeoutError:
                logger.error("Timeout waiting for MCP response", server=self.name, method=method)
                raise

            if not response_line:
                raise RuntimeError(f"MCP server '{self.name}' closed connection unexpectedly")

            try:
                response = json.loads(response_line.decode())
            except json.JSONDecodeError as e:
                raise RuntimeError(f"Invalid JSON response from MCP server: {e}")

            # Verify response ID matches request ID
            if response.get("id") != request_id:
                logger.warning(
                    "Response ID mismatch",
                    expected=request_id,
                    received=response.get("id"),
                    server=self.name,
                )

            if "error" in response:
                error = response["error"]
                error_msg = (
                    error.get("message", str(error)) if isinstance(error, dict) else str(error)
                )
                raise RuntimeError(f"MCP error: {error_msg}")

            return response.get("result", {})

    async def _discover_tools(self) -> None:
        """Discover available tools from the MCP server."""
        try:
            result = await self._send_request("tools/list", {})
            self.tools = result.get("tools", [])
        except Exception as e:
            logger.error("Failed to discover tools", server=self.name, error=str(e))
            self.tools = []

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool on the MCP server.

        Args:
            tool_name: The name of the tool to call.
            arguments: The arguments to pass to the tool.

        Returns:
            The tool execution result content.

        Raises:
            RuntimeError: If tool execution fails.
        """
        try:
            # Ensure arguments is always a dict (MCP expects a record, not null)
            if arguments is None:
                arguments = {}
            
            result = await self._send_request(
                "tools/call", {"name": tool_name, "arguments": arguments}
            )
            return result.get("content", [])
        except Exception as e:
            logger.error("Tool execution failed", server=self.name, tool=tool_name, error=str(e))
            raise

    async def _cleanup_process(self) -> None:
        """Clean up the subprocess if it exists."""
        if self.process:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
            except Exception as e:
                logger.warning("Error during process cleanup", server=self.name, error=str(e))
            finally:
                self.process = None
                self.connected = False

    async def disconnect(self) -> None:
        """Disconnect from the MCP server and clean up resources."""
        if self.process:
            await self._cleanup_process()
            logger.info("MCP server disconnected", server=self.name)


class MCPService:
    """Service for managing MCP servers and tool execution.

    This service manages connections to multiple MCP servers and provides
    a unified interface for discovering and executing tools.

    Usage:
        async with MCPService() as service:
            await service.connect_servers(configs)
            tools = service.get_available_tools()
            result = await service.execute_tool("tool_name", {"arg": "value"})
    """

    def __init__(self, timeout: float = DEFAULT_TIMEOUT):
        """Initialize the MCP service.

        Args:
            timeout: Default timeout for MCP operations in seconds.
        """
        self.servers: Dict[str, MCPServer] = {}
        self.timeout = timeout

    async def __aenter__(self) -> "MCPService":
        """Support async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Ensure all servers are disconnected on context exit."""
        await self.disconnect_all()

    async def connect_servers(self, mcp_configs: Dict[str, MCPServerConfig]) -> None:
        """Connect to multiple MCP servers.

        Args:
            mcp_configs: Dictionary mapping server names to their configurations.
        """
        for name, config in mcp_configs.items():
            if name not in self.servers:
                server = MCPServer(name, config, timeout=self.timeout)
                try:
                    await server.connect()
                    self.servers[name] = server
                except Exception as e:
                    logger.error("Failed to connect server", server=name, error=str(e))
                    # Continue with other servers even if one fails

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get all available tools from connected servers.

        Returns:
            List of tool information dictionaries with server, name,
            description, and inputSchema fields.
        """
        all_tools = []
        for server_name, server in self.servers.items():
            for tool in server.tools:
                tool_info = {
                    "server": server_name,
                    "name": tool.get("name"),
                    "description": tool.get("description"),
                    "inputSchema": tool.get("inputSchema"),
                }
                all_tools.append(tool_info)
        return all_tools

    def get_tools_for_llm(self) -> List[Dict[str, Any]]:
        """Get tools formatted for OpenAI/LLM function calling.

        Returns:
            List of tools in OpenAI function calling format.
        """
        tools = self.get_available_tools()
        formatted_tools = []
        
        for tool in tools:
            if not tool.get("name"):
                continue
                
            # Get input schema, ensure it's properly formatted
            input_schema = tool.get("inputSchema", {})
            if not isinstance(input_schema, dict):
                input_schema = {"type": "object", "properties": {}}
            
            # Ensure required fields exist
            if "type" not in input_schema:
                input_schema["type"] = "object"
            if "properties" not in input_schema:
                input_schema["properties"] = {}
            
            formatted_tool = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": input_schema,
                },
            }
            
            formatted_tools.append(formatted_tool)
            
        return formatted_tools

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool by finding it in connected servers.

        Args:
            tool_name: The name of the tool to execute.
            arguments: The arguments to pass to the tool.

        Returns:
            The tool execution result.

        Raises:
            ValueError: If the tool is not found in any connected server.
        """
        for server in self.servers.values():
            for tool in server.tools:
                if tool.get("name") == tool_name:
                    return await server.call_tool(tool_name, arguments)

        raise ValueError(f"Tool '{tool_name}' not found in any connected server")

    async def disconnect_all(self) -> None:
        """Disconnect from all MCP servers and clean up resources."""
        disconnect_tasks = [server.disconnect() for server in self.servers.values()]
        if disconnect_tasks:
            server_names = list(self.servers.keys())
            results = await asyncio.gather(*disconnect_tasks, return_exceptions=True)
            # Log any exceptions that occurred during disconnect
            for server_name, result in zip(server_names, results):
                if isinstance(result, Exception):
                    logger.warning(
                        "Error disconnecting MCP server", server=server_name, error=str(result)
                    )
        self.servers.clear()

    def get_tool_count(self) -> int:
        """Get total count of available tools across all servers.

        Returns:
            The total number of tools available.
        """
        return sum(len(server.tools) for server in self.servers.values())

    def is_connected(self) -> bool:
        """Check if any MCP servers are connected.

        Returns:
            True if at least one server is connected.
        """
        return any(server.connected for server in self.servers.values())
