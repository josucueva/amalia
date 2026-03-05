"""
MCP Tool Catalog Service

Extracts tool definitions from MCP servers and provides a catalog
for agent configuration and intelligent tool-aware orchestration.
"""
import os
import inspect
import importlib.util
from pathlib import Path
from typing import Dict, List, Any, Optional
import structlog
from pydantic import BaseModel

logger = structlog.get_logger()


class ToolParameter(BaseModel):
    """Schema for a tool parameter."""
    name: str
    type: str
    description: Optional[str] = None
    required: bool = True
    default: Any = None


class MCPToolDefinition(BaseModel):
    """Complete definition of an MCP tool."""
    name: str
    description: str
    server_id: str
    server_name: str
    parameters: List[ToolParameter]
    return_type: str
    category: str  # data_loading, data_preparation, model_training, model_evaluation, mathematics


class MCPToolCatalog:
    """
    Catalog of all available MCP tools across all servers.
    Provides tool discovery and metadata for agent configuration.
    """
    
    def __init__(self):
        self.tools: Dict[str, MCPToolDefinition] = {}
        self.tools_by_server: Dict[str, List[MCPToolDefinition]] = {}
        self._loaded = False
    
    def load_catalog(self, mcp_servers_path: str = "/app/mcp_servers") -> None:
        """
        Load all tools from MCP server implementations.
        
        Args:
            mcp_servers_path: Path to MCP servers directory
        """
        if self._loaded:
            return
        
        logger.info("Loading MCP tool catalog", path=mcp_servers_path)
        
        # Map server directories to IDs
        server_mapping = {
            "data_loading": {
                "id": "data-loading",
                "name": "Data Loading Server",
                "category": "data_loading"
            },
            "data_preparation": {
                "id": "data-preparation",
                "name": "Data Preparation Server",
                "category": "data_preparation"
            },
            "model_training": {
                "id": "model-training",
                "name": "Model Training Server",
                "category": "model_training"
            },
            "model_evaluation": {
                "id": "model-evaluation",
                "name": "Model Evaluation Server",
                "category": "model_evaluation"
            },
            "mathematics": {
                "id": "python-mathematics",
                "name": "Mathematics Server",
                "category": "mathematics"
            }
        }
        
        servers_path = Path(mcp_servers_path)
        if not servers_path.exists():
            logger.warning("MCP servers path not found", path=mcp_servers_path)
            return
        
        # Scan each server directory
        for server_dir in servers_path.iterdir():
            if not server_dir.is_dir():
                continue
            
            server_name = server_dir.name
            if server_name not in server_mapping:
                continue
            
            server_info = server_mapping[server_name]
            server_id = server_info["id"]
            
            # Load server.py module
            server_file = server_dir / "server.py"
            if not server_file.exists():
                continue
            
            try:
                tools = self._extract_tools_from_server(
                    server_file,
                    server_id=server_id,
                    server_name=server_info["name"],
                    category=server_info["category"]
                )
                
                self.tools_by_server[server_id] = tools
                for tool in tools:
                    self.tools[f"{server_id}:{tool.name}"] = tool
                
                logger.info(
                    "Loaded tools from server",
                    server=server_id,
                    tool_count=len(tools)
                )
            
            except Exception as e:
                logger.error(
                    "Failed to load tools from server",
                    server=server_id,
                    error=str(e)
                )
        
        self._loaded = True
        logger.info("MCP tool catalog loaded", total_tools=len(self.tools))
    
    def _extract_tools_from_server(
        self,
        server_file: Path,
        server_id: str,
        server_name: str,
        category: str
    ) -> List[MCPToolDefinition]:
        """
        Extract tool definitions from a server.py file by parsing @mcp.tool() decorators.
        
        Args:
            server_file: Path to server.py
            server_id: Server identifier
            server_name: Human-readable server name
            category: Tool category
            
        Returns:
            List of tool definitions
        """
        tools = []
        
        # Load module dynamically
        spec = importlib.util.spec_from_file_location(f"mcp_server_{server_id}", server_file)
        if spec is None or spec.loader is None:
            return tools
        
        module = importlib.util.module_from_spec(spec)
        
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            logger.error("Failed to load module", file=str(server_file), error=str(e))
            return tools
        
        # Find all functions decorated with @mcp.tool()
        for name, obj in inspect.getmembers(module):
            if not inspect.isfunction(obj):
                continue
            
            # Check if function has FastMCP tool decorator (heuristic: check if registered)
            if not hasattr(module, 'mcp'):
                continue
            
            # Get function signature
            sig = inspect.signature(obj)
            docstring = inspect.getdoc(obj) or ""
            
            # Extract parameters
            parameters = []
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                
                param_type = "string"
                if param.annotation != inspect.Parameter.empty:
                    annotation = param.annotation
                    if annotation == int:
                        param_type = "integer"
                    elif annotation == float:
                        param_type = "number"
                    elif annotation == bool:
                        param_type = "boolean"
                    elif hasattr(annotation, '__origin__'):
                        # Handle List, Optional, etc.
                        if annotation.__origin__ == list:
                            param_type = "array"
                        elif annotation.__origin__ == dict:
                            param_type = "object"
                
                is_required = param.default == inspect.Parameter.empty
                default_value = None if is_required else param.default
                
                # Extract parameter description from docstring (simple heuristic)
                param_desc = None
                if f"{param_name}:" in docstring:
                    lines = docstring.split('\n')
                    for line in lines:
                        if f"{param_name}:" in line:
                            param_desc = line.split(':', 1)[1].strip()
                            break
                
                parameters.append(ToolParameter(
                    name=param_name,
                    type=param_type,
                    description=param_desc,
                    required=is_required,
                    default=default_value
                ))
            
            # Extract return type
            return_type = "object"
            if sig.return_annotation != inspect.Signature.empty:
                if sig.return_annotation == dict:
                    return_type = "object"
                elif sig.return_annotation == str:
                    return_type = "string"
                elif sig.return_annotation == int:
                    return_type = "integer"
                elif sig.return_annotation == float:
                    return_type = "number"
            
            # Extract description (first line of docstring)
            description = docstring.split('\n')[0] if docstring else name
            
            # Only include functions that look like tools (have docstrings and params)
            if docstring and parameters:
                tools.append(MCPToolDefinition(
                    name=name,
                    description=description,
                    server_id=server_id,
                    server_name=server_name,
                    parameters=parameters,
                    return_type=return_type,
                    category=category
                ))
        
        return tools
    
    def get_tools_for_server(self, server_id: str) -> List[MCPToolDefinition]:
        """
        Get all tools for a specific server.
        
        Args:
            server_id: MCP server identifier
            
        Returns:
            List of tool definitions
        """
        if not self._loaded:
            self.load_catalog()
        
        return self.tools_by_server.get(server_id, [])
    
    def get_tool(self, server_id: str, tool_name: str) -> Optional[MCPToolDefinition]:
        """
        Get a specific tool definition.
        
        Args:
            server_id: MCP server identifier
            tool_name: Tool name
            
        Returns:
            Tool definition or None
        """
        if not self._loaded:
            self.load_catalog()
        
        key = f"{server_id}:{tool_name}"
        return self.tools.get(key)
    
    def get_all_tools(self) -> Dict[str, MCPToolDefinition]:
        """Get all tools in the catalog."""
        if not self._loaded:
            self.load_catalog()
        
        return self.tools
    
    def get_tools_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all tools organized by category and server.
        Useful for agent system prompts.
        
        Returns:
            Dictionary with categorized tool information
        """
        if not self._loaded:
            self.load_catalog()
        
        summary = {
            "total_tools": len(self.tools),
            "servers": {},
            "by_category": {}
        }
        
        for server_id, tools in self.tools_by_server.items():
            tool_list = []
            for tool in tools:
                tool_list.append({
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": [p.name for p in tool.parameters]
                })
                
                # Organize by category
                if tool.category not in summary["by_category"]:
                    summary["by_category"][tool.category] = []
                summary["by_category"][tool.category].append({
                    "server_id": server_id,
                    "tool_name": tool.name,
                    "description": tool.description
                })
            
            summary["servers"][server_id] = {
                "name": tools[0].server_name if tools else server_id,
                "tool_count": len(tools),
                "tools": tool_list
            }
        
        return summary
    
    def format_tools_for_agent_prompt(self, server_ids: List[str]) -> str:
        """
        Format tool information for agent system prompts.
        
        Args:
            server_ids: List of MCP server IDs the agent has access to
            
        Returns:
            Formatted string describing available tools
        """
        if not self._loaded:
            self.load_catalog()
        
        lines = ["## Available MCP Tools\n"]
        
        for server_id in server_ids:
            tools = self.get_tools_for_server(server_id)
            if not tools:
                continue
            
            lines.append(f"\n### {tools[0].server_name} ({server_id})")
            for tool in tools:
                params = ", ".join([f"{p.name}: {p.type}" for p in tool.parameters if p.required])
                optional_params = ", ".join([f"{p.name}?: {p.type}" for p in tool.parameters if not p.required])
                all_params = params
                if optional_params:
                    all_params = f"{params}, {optional_params}" if params else optional_params
                
                lines.append(f"- **{tool.name}**({all_params}): {tool.description}")
        
        return "\n".join(lines)


# Global singleton instance
_catalog_instance: Optional[MCPToolCatalog] = None


def get_mcp_tool_catalog() -> MCPToolCatalog:
    """Get the global MCP tool catalog instance."""
    global _catalog_instance
    if _catalog_instance is None:
        _catalog_instance = MCPToolCatalog()
        _catalog_instance.load_catalog()
    return _catalog_instance
