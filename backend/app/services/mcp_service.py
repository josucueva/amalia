"""
MCP (Model Context Protocol) service for tool execution.
"""
import asyncio
import json
from typing import Dict, List, Any, Optional
import structlog

from app.models.agent import MCPServerConfig

logger = structlog.get_logger()


class MCPServer:
    """Represents a single MCP server connection."""
    
    def __init__(self, name: str, config: MCPServerConfig):
        self.name = name
        self.config = config
        self.process = None
        self.tools = []
        self.connected = False
        self.msg_id = 0
        
    async def connect(self):
        """Connect to the MCP server via stdio."""
        try:
            env = self.config.env or {}
            
            self.process = await asyncio.create_subprocess_exec(
                self.config.command,
                *self.config.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            # Initialize connection
            await self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "amalia",
                    "version": "1.0.0"
                }
            })
            
            # Discover tools
            await self._discover_tools()
            
            self.connected = True
            logger.info("MCP server connected", server=self.name, tools=len(self.tools))
            
        except Exception as e:
            logger.error("Failed to connect to MCP server", server=self.name, error=str(e))
            raise
    
    async def _send_request(self, method: str, params: Dict) -> Dict:
        """Send JSON-RPC request to MCP server."""
        if not self.process or not self.process.stdin:
            raise RuntimeError("MCP server not connected")
        
        self.msg_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.msg_id,
            "method": method,
            "params": params
        }
        
        request_str = json.dumps(request) + "\n"
        self.process.stdin.write(request_str.encode())
        await self.process.stdin.drain()
        
        # Read response
        response_line = await self.process.stdout.readline()
        response = json.loads(response_line.decode())
        
        if "error" in response:
            raise RuntimeError(f"MCP error: {response['error']}")
        
        return response.get("result", {})
    
    async def _discover_tools(self):
        """Discover available tools from the MCP server."""
        try:
            result = await self._send_request("tools/list", {})
            self.tools = result.get("tools", [])
        except Exception as e:
            logger.error("Failed to discover tools", server=self.name, error=str(e))
            self.tools = []
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool on the MCP server."""
        try:
            result = await self._send_request("tools/call", {
                "name": tool_name,
                "arguments": arguments
            })
            return result.get("content", [])
        except Exception as e:
            logger.error("Tool execution failed", server=self.name, tool=tool_name, error=str(e))
            raise
    
    async def disconnect(self):
        """Disconnect from the MCP server."""
        if self.process:
            self.process.terminate()
            await self.process.wait()
            self.connected = False
            logger.info("MCP server disconnected", server=self.name)


class MCPService:
    """Service for managing MCP servers and tool execution."""
    
    def __init__(self):
        self.servers: Dict[str, MCPServer] = {}
    
    async def connect_servers(self, mcp_configs: Dict[str, MCPServerConfig]):
        """Connect to multiple MCP servers."""
        for name, config in mcp_configs.items():
            if name not in self.servers:
                server = MCPServer(name, config)
                try:
                    await server.connect()
                    self.servers[name] = server
                except Exception as e:
                    logger.error("Failed to connect server", server=name, error=str(e))
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get all available tools from connected servers."""
        all_tools = []
        for server_name, server in self.servers.items():
            for tool in server.tools:
                tool_info = {
                    "server": server_name,
                    "name": tool.get("name"),
                    "description": tool.get("description"),
                    "inputSchema": tool.get("inputSchema")
                }
                all_tools.append(tool_info)
        return all_tools
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool by finding it in connected servers."""
        for server in self.servers.values():
            for tool in server.tools:
                if tool.get("name") == tool_name:
                    return await server.call_tool(tool_name, arguments)
        
        raise ValueError(f"Tool '{tool_name}' not found in any connected server")
    
    async def disconnect_all(self):
        """Disconnect from all MCP servers."""
        for server in self.servers.values():
            await server.disconnect()
        self.servers.clear()
    
    def get_tool_count(self) -> int:
        """Get total count of available tools."""
        return sum(len(server.tools) for server in self.servers.values())
