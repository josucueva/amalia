# MCP Implementation Testing Guide

## Prerequisites

- Node.js installed (for npx)
- Docker and Docker Compose running
- AMALIA backend and frontend running

## Test 1: Filesystem MCP Server

### Step 1: Start the Application

```powershell
docker compose up
```

### Step 2: Configure an Agent with MCP

1. Open AMALIA in browser (http://localhost:5173)
2. Go to Canvas mode
3. Click on any existing agent (e.g., "Data Loader")
4. In the Agent Details modal, scroll to "MCP Tools Configuration" section
5. Click "+ Add MCP Server"
6. Enter the following:
   - **Server Name**: `filesystem`
   - **Command**: `npx`
   - **Arguments**: `-y @modelcontextprotocol/server-filesystem C:\Users\josuc\OneDrive\Documentos\Code\agentic\amalia\data\uploads`
   - **Environment Variables**: `{}` (leave as empty JSON)
7. Click "Save Agent"

### Step 3: Verify Tool Badge

- The agent node should now show a small badge with "1" indicating 1 MCP server configured

### Step 4: Test Execution

1. Add the agent to canvas if not already there
2. Click "Execute" on the agent node
3. Enter a test prompt like: "List all files in the directory"
4. Watch the execution

**Expected Behavior:**

- Agent connects to filesystem MCP server
- Discovers tools (read_file, write_file, list_directory, etc.)
- LLM receives these tools in its context
- LLM calls appropriate tool (e.g., list_directory)
- Results returned to LLM
- Final response includes file listing

### Step 5: Check Logs

Backend logs should show:

```
MCP server connected, server=filesystem, tools=<number>
MCP tools loaded, tool_count=<number>
Processing tool calls, iteration=1, tool_count=1, tools=['list_directory']
```

---

## Test 2: Create a Simple Python MCP Server

### Step 1: Create Test MCP Server

Create `c:\Users\josuc\OneDrive\Documentos\Code\agentic\amalia\test_mcp_server.py`:

```python
#!/usr/bin/env python3
"""
Simple test MCP server that provides a calculator tool.
"""
import sys
import json


def send_response(response):
    """Send JSON-RPC response to stdout."""
    print(json.dumps(response), flush=True)


def handle_initialize(request_id):
    """Handle initialize request."""
    send_response({
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "serverInfo": {
                "name": "test-calculator",
                "version": "1.0.0"
            }
        }
    })


def handle_tools_list(request_id):
    """Handle tools/list request."""
    send_response({
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "tools": [
                {
                    "name": "add",
                    "description": "Add two numbers",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "a": {"type": "number", "description": "First number"},
                            "b": {"type": "number", "description": "Second number"}
                        },
                        "required": ["a", "b"]
                    }
                },
                {
                    "name": "multiply",
                    "description": "Multiply two numbers",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "a": {"type": "number", "description": "First number"},
                            "b": {"type": "number", "description": "Second number"}
                        },
                        "required": ["a", "b"]
                    }
                }
            ]
        }
    })


def handle_tool_call(request_id, params):
    """Handle tools/call request."""
    tool_name = params.get("name")
    arguments = params.get("arguments", {})

    try:
        if tool_name == "add":
            result = arguments["a"] + arguments["b"]
            content = [{"type": "text", "text": f"Result: {result}"}]
        elif tool_name == "multiply":
            result = arguments["a"] * arguments["b"]
            content = [{"type": "text", "text": f"Result: {result}"}]
        else:
            content = [{"type": "text", "text": f"Unknown tool: {tool_name}"}]

        send_response({
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"content": content}
        })
    except Exception as e:
        send_response({
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -1, "message": str(e)}
        })


def main():
    """Main loop for MCP server."""
    # Read line-delimited JSON from stdin
    for line in sys.stdin:
        try:
            request = json.loads(line)
            method = request.get("method")
            request_id = request.get("id")
            params = request.get("params", {})

            if method == "initialize":
                handle_initialize(request_id)
            elif method == "notifications/initialized":
                # Just acknowledge, no response needed for notifications
                pass
            elif method == "tools/list":
                handle_tools_list(request_id)
            elif method == "tools/call":
                handle_tool_call(request_id, params)
            else:
                send_response({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"}
                })
        except Exception as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)


if __name__ == "__main__":
    main()
```

### Step 2: Make Script Executable

```powershell
# No need to chmod on Windows, just ensure Python is in PATH
```

### Step 3: Configure Agent

1. Open Agent Details for an agent
2. Add MCP Server:
   - **Server Name**: `calculator`
   - **Command**: `python`
   - **Arguments**: `C:\Users\josuc\OneDrive\Documentos\Code\agentic\amalia\test_mcp_server.py`
   - **Environment Variables**: `{}`
3. Save

### Step 4: Test

Execute the agent with prompt: "What is 15 + 27?"

**Expected:**

- Agent connects to calculator server
- LLM sees `add` and `multiply` tools
- LLM calls `add` tool with `{"a": 15, "b": 27}`
- Tool returns "Result: 42"
- LLM includes this in final response

---

## Test 3: Multiple MCP Servers

Configure an agent with both servers:

1. `filesystem` server (from Test 1)
2. `calculator` server (from Test 2)

**Test Prompt**: "Add 10 and 20, then save the result to a file called result.txt"

**Expected:**

- Agent has access to both filesystem and calculator tools
- LLM calls `add(10, 20)` → gets 30
- LLM calls `write_file("result.txt", "30")` → saves file
- Final response confirms both operations

---

## Debugging Tips

### Check Backend Logs

```powershell
docker compose logs -f backend
```

Look for:

- `MCP server connected` - Server started successfully
- `MCP tools loaded` - Tools discovered
- `Processing tool calls` - LLM requesting tools
- `Tool execution failed` - Tool errors

### Common Issues

**Issue**: "Timeout connecting to MCP server"

- **Fix**: Check command and args are correct
- **Fix**: Ensure the MCP server executable is accessible

**Issue**: "Tool 'X' not found in any connected server"

- **Fix**: Verify tools were discovered (check logs for tool_count)
- **Fix**: Ensure tool name matches exactly what LLM requested

**Issue**: "MCP server closed connection unexpectedly"

- **Fix**: Check MCP server implementation handles all protocol methods
- **Fix**: Ensure server sends proper JSON-RPC responses

**Issue**: "Environment variable errors"

- **Fix**: Review the env merging fix in mcp_service.py
- **Fix**: Check if MCP server needs specific env vars (PATH, HOME, etc.)

### Verify Protocol Flow

MCP servers should handle these methods:

1. `initialize` - Initial handshake (MUST respond)
2. `notifications/initialized` - No response needed
3. `tools/list` - Return available tools (MUST respond)
4. `tools/call` - Execute tool (MUST respond)

---

## Advanced Testing

### Test Error Handling

1. Configure invalid MCP server (wrong command)
2. Execute agent
3. Verify graceful degradation (agent works without tools)

### Test Timeout

1. Create MCP server that sleeps before responding
2. Verify timeout handling (should fail after 30 seconds)

### Test Resource Cleanup

1. Execute agent with MCP servers
2. Cancel execution mid-way
3. Check that subprocesses are terminated (no zombie processes)

```powershell
# Check for python/npx processes
Get-Process | Where-Object {$_.ProcessName -match "python|node"}
```

---

## Success Criteria

✅ Agent connects to MCP server successfully  
✅ Tools are discovered and passed to LLM  
✅ LLM can call tools when appropriate  
✅ Tool results flow back to LLM  
✅ Final response includes tool-enhanced information  
✅ Resources cleaned up after execution  
✅ Error cases handled gracefully  
✅ Multiple servers work simultaneously

---

## Example Test Scenarios

### Scenario 1: File Analysis

- Agent: Data Loader with filesystem MCP
- Prompt: "Read the CSV file and tell me how many rows it has"
- Expected: Agent reads file, counts rows, responds

### Scenario 2: Data Processing

- Agent: Data Preprocessor with calculator + filesystem MCP
- Prompt: "Calculate the average of numbers in data.csv and save to summary.txt"
- Expected: Agent reads file, calculates, writes result

### Scenario 3: Multi-Step Pipeline

- Agent 1: Loads data (filesystem MCP)
- Agent 2: Processes data (calculator MCP)
- Agent 3: Saves results (filesystem MCP)
- Execute full pipeline and verify data flows correctly

---

## Monitoring Dashboard Ideas

Track these metrics during testing:

- Number of MCP servers connected
- Tools available per agent
- Tool call success/failure rate
- Average tool execution time
- MCP server connection errors

---

## Next Steps After Testing

Once MCP is verified working:

1. Merge branch to main
2. Update documentation
3. Create video demo
4. Add more sophisticated MCP servers
5. Build server templates library
6. Implement connection pooling for performance
