# MCP Tools Integration - Implementation Summary

## Overview

Implemented MCP (Model Context Protocol) tools integration following the project's existing design patterns. Agents can now connect to external MCP servers and use their tools during execution.

## Architecture

### Design Principles

- **Minimal Complexity**: Simple, straightforward implementation
- **Follows Project Patterns**: Uses existing component structure and API patterns
- **Embedded in Agent Details**: MCP configuration lives within agent modal, not separate
- **Subtle UI Indicators**: Small badge shows tool count without visual clutter

### How It Works

1. **Agent Configuration**: Each agent stores MCP server configs in `config.mcp_servers`
2. **Connection**: When agent executes, MCP service connects to configured servers via stdio
3. **Tool Discovery**: MCP servers expose available tools via JSON-RPC `tools/list`
4. **LLM Integration**: Available tools passed to LLM in OpenAI function format
5. **Tool Execution**: LLM can request tool execution, MCP service executes via `tools/call`

## Implementation Details

### Backend Changes

#### 1. Data Models (`backend/app/models/agent.py`)

```python
class MCPServerConfig(BaseModel):
    """MCP server configuration."""
    command: str  # e.g., "npx", "python"
    args: List[str]  # e.g., ["-y", "@modelcontextprotocol/server-filesystem"]
    env: Optional[Dict[str, str]]  # Environment variables

class AgentConfig(BaseModel):
    # ... existing fields ...
    mcp_servers: Dict[str, MCPServerConfig] = Field(default_factory=dict)
```

#### 2. MCP Service (`backend/app/services/mcp_service.py`)

- **MCPServer**: Manages single server connection via subprocess stdio
- **MCPService**: Manages multiple servers, tool discovery, and execution
- **JSON-RPC Protocol**: Implements MCP protocol (initialize, tools/list, tools/call)

Key methods:

- `connect_servers(configs)`: Connect to multiple MCP servers
- `get_available_tools()`: Get all tools from connected servers
- `execute_tool(name, args)`: Execute a specific tool
- `disconnect_all()`: Cleanup connections

#### 3. LLM Service Updates (`backend/app/services/llm_service.py`)

- Added `tools` parameter to `generate_response()`
- Returns tool calls when LLM requests function execution
- Supports OpenAI function calling format

#### 4. Canvas Execution (`backend/app/api/routes/canvas.py`)

Enhanced `execute_node()` endpoint:

1. Check if agent has MCP servers configured
2. Connect to MCP servers and discover tools
3. Pass tools to LLM in function calling format
4. Handle tool call responses from LLM
5. Execute tools via MCP service
6. Return results to LLM for final response
7. Cleanup MCP connections

### Frontend Changes

#### 1. Agent Details Modal (`frontend/src/js/components/AgentConfig.js`)

- **Title Changed**: "Edit Agent" → "Agent Details"
- **MCP Section Added**: Configure MCP servers within agent modal
- **Server Management**: Add/remove MCP servers with command, args, env

New features:

- `initMCPSection()`: Initialize MCP UI handlers
- `showAddMCPServerDialog()`: Prompt-based server addition
- `renderMCPServers()`: Display configured servers
- `mcpServers` state: Track server configurations

#### 2. Canvas Node Rendering (`frontend/src/js/main.js`)

- **Tool Count Badge**: Shows number of MCP servers configured
- **Subtle Design**: Small badge in top-right of node
- **Conditional Display**: Only shows when tools > 0

```javascript
const mcpServers = agent.config.mcp_servers || {};
const toolCount = Object.keys(mcpServers).length;

${toolCount > 0 ? `<span class="tool-count-badge">${toolCount}</span>` : ""}
```

#### 3. Styling (`frontend/src/css/components.css`)

Added MCP-specific styles:

- `.form-section`: Separator for MCP section
- `.mcp-servers-list`: Scrollable list of servers
- `.mcp-server-item`: Individual server display
- `.tool-count-badge`: Subtle badge on nodes (10px font, top-right)

## Usage Example

### 1. Create/Edit Agent

1. Open "Agent Details" for any agent
2. Scroll to "MCP Tools" section
3. Click "+ Add MCP Server"
4. Enter server details:
   - Name: `filesystem`
   - Command: `npx`
   - Args: `-y, @modelcontextprotocol/server-filesystem`

### 2. Configure Multiple Servers

Each agent can have multiple MCP servers:

- `filesystem`: File operations
- `sqlite`: Database queries
- `github`: Repository access
- Custom MCP servers

### 3. Execute Agent

When the agent node executes:

1. Connects to all configured MCP servers
2. Discovers available tools (e.g., `read_file`, `write_file`)
3. LLM receives tools in its context
4. LLM can call tools as needed
5. Results returned to LLM
6. Final response includes tool-enhanced output

### 4. Visual Feedback

- **Badge on Node**: Shows "2" if 2 MCP servers configured
- **Subtle Design**: Doesn't clutter the UI
- **Always Visible**: Easy to identify tool-enabled agents

## Technical Flow

```
User Message → Agent Execution
    ↓
Load Agent Config (includes mcp_servers)
    ↓
MCPService.connect_servers(config.mcp_servers)
    ↓
For each server:
    - Start subprocess (command + args)
    - Send JSON-RPC "initialize"
    - Send "tools/list"
    - Store available tools
    ↓
Convert tools to OpenAI function format
    ↓
LLMService.generate_response(message, tools)
    ↓
LLM returns either:
    - Text response (no tools needed)
    - Tool calls (execute functions)
    ↓
If tool calls:
    For each call:
        MCPService.execute_tool(name, args)
        Collect results
    ↓
    Send results back to LLM
    Get final response
    ↓
Return response to user
    ↓
MCPService.disconnect_all()
```

## Best Practices

### Adding MCP Servers

1. **Use Standard Servers**: npm packages like `@modelcontextprotocol/server-*`
2. **Environment Variables**: Store API keys in server env config
3. **Tool Discovery**: Let MCP service automatically discover tools
4. **Cleanup**: Service automatically disconnects after execution

### Agent Design

1. **Specialized Agents**: Create agents for specific tool categories

   - Data Agent: filesystem + database tools
   - Code Agent: github + editor tools
   - Analysis Agent: custom analytics tools

2. **Composable Pipelines**: Connect tool-enabled agents in canvas
   - Data Loader → Data Processor → Model Trainer
   - Each can have specialized MCP tools

### Security

- MCP servers run as subprocesses with configured env
- No direct file system access without configured tools
- Tools are explicitly listed and controlled per agent

## Files Modified

### Backend

- `backend/app/models/agent.py` - Added MCPServerConfig, mcp_servers field
- `backend/app/services/mcp_service.py` - NEW: MCP client implementation
- `backend/app/services/llm_service.py` - Added tool support
- `backend/app/api/routes/canvas.py` - Integrated MCP in execution

### Frontend

- `frontend/src/js/components/AgentConfig.js` - Added MCP section
- `frontend/src/js/main.js` - Added tool count badge
- `frontend/src/css/components.css` - Added MCP styles
- `frontend/index.html` - Added MCP UI elements

## Future Enhancements

### Potential Improvements

1. **Tool Visualization**: Show individual tools in UI, not just server count
2. **Tool Call History**: Display which tools were called during execution
3. **Persistent Connections**: Keep MCP servers running for faster execution
4. **Server Templates**: Pre-configured popular MCP servers
5. **Tool Filtering**: Select specific tools from a server
6. **Server Health**: Connection status indicators
7. **Tool Analytics**: Track tool usage and performance

### Not Implemented (Keeping It Simple)

- ❌ Separate MCP management modal
- ❌ Complex tool selection UI
- ❌ Server marketplace/discovery
- ❌ Tool call streaming
- ❌ Multi-turn tool conversations
- ❌ Tool result caching

## Comparison to Initial Approach

### Previous (Rejected) Approach

- Separate MCP Tools button in header
- Global MCP server management modal
- Centralized tool configuration
- More complex, separated from agents

### Current (Accepted) Approach

- MCP tools integrated into Agent Details
- Per-agent server configuration
- Minimal UI changes
- Follows existing patterns (like AgentConfig component)
- Simple, focused, functional

## Testing

### Manual Test Steps

1. Start backend: `docker compose up`
2. Create/edit an agent
3. Add MCP server (e.g., filesystem)
4. Save agent
5. Add agent to canvas
6. Verify tool count badge appears
7. Connect agent to pipeline
8. Execute pipeline
9. Verify tools are available and used

### Example MCP Server Test

```bash
# Test with filesystem MCP server
Server: filesystem
Command: npx
Args: -y, @modelcontextprotocol/server-filesystem, /path/to/allowed/directory

# Agent will have access to:
- read_file
- write_file
- list_directory
- etc.
```

## Conclusion

This implementation provides:

- ✅ Clean integration with existing architecture
- ✅ Minimal complexity and learning curve
- ✅ Follows established project patterns
- ✅ Subtle, non-intrusive UI
- ✅ Powerful tool capability for agents
- ✅ Easy to use and understand

The design prioritizes simplicity and maintainability while providing full MCP functionality.
