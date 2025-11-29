# MCP Implementation Review and Improvements

## Overview

This document summarizes the review and improvements made to the MCP (Model Context Protocol) integration in AMALIA. The MCP integration allows agents to connect to external MCP servers and use their tools during pipeline execution.

## Problems Identified

### 1. Environment Variable Handling Bug (Critical)

**Problem:** In `mcp_service.py`, when creating the subprocess, `env=self.config.env or {}` was used. If `env` is an empty dict `{}`, it **replaces the entire process environment**, meaning the subprocess won't inherit `PATH`, `HOME`, or any other critical environment variables. This causes most MCP servers to fail to start.

**Solution:** Changed to merge custom environment variables with the system environment:

```python
process_env = os.environ.copy()
if self.config.env:
    process_env.update(self.config.env)
```

### 2. Missing MCP Protocol "initialized" Notification (Critical)

**Problem:** The MCP protocol requires sending an `initialized` notification after receiving the initialize response before any other requests. The original implementation skipped this step, potentially causing protocol compliance issues.

**Solution:** Added `_send_notification` method and call `notifications/initialized` after successful initialization:

```python
await self._send_notification("notifications/initialized", {})
```

### 3. No Timeout Handling for MCP Server Responses (High)

**Problem:** The `_send_request` method waited indefinitely for responses with `readline()`. If an MCP server hangs or crashes, the entire system would be blocked.

**Solution:** Implemented timeout handling using `asyncio.wait_for`:

```python
response_line = await asyncio.wait_for(
    self.process.stdout.readline(),
    timeout=self.timeout
)
```

### 4. Tools Not Passed to LLM Correctly (High)

**Problem:** In `canvas.py`, tools were added to `agent_config` but `generate_agent_response` didn't use them. It called `generate_with_system_prompt` which didn't accept or pass the `tools` parameter.

**Solution:** Updated both `generate_with_system_prompt` and `generate_agent_response` methods in `llm_service.py` to accept and pass the `tools` parameter to `generate_response`.

### 5. Incomplete Tool Call Handling Flow (High)

**Problem:** After executing tools, the code returned raw tool results instead of feeding them back to the LLM for a proper response. This broke the proper tool-use flow where the LLM should process tool results and provide a final answer.

**Solution:** Implemented a proper tool call loop in `canvas.py`:

- Execute tool calls and collect results
- Add tool results to conversation history
- Call LLM again with the updated context
- Repeat until LLM provides a final text response or max iterations reached

### 6. Resource Leak in Error Cases (Medium)

**Problem:** If an error occurred after connecting to MCP servers but before `disconnect_all()` was called, the subprocess would continue running as a zombie process.

**Solution:**

- Added `finally` block in `execute_node` to ensure cleanup
- Added `_cleanup_process` method with proper termination handling
- Implemented async context manager (`__aenter__`/`__aexit__`) for MCPService

### 7. Response ID Mismatch Not Checked (Low)

**Problem:** When receiving JSON-RPC responses, the code didn't verify that the response `id` matches the request `id`.

**Solution:** Added validation to check response ID matches request ID:

```python
if response.get("id") != request_id:
    logger.warning("Response ID mismatch", ...)
```

## Design Patterns Applied

### 1. Context Manager Pattern

The `MCPService` now implements the async context manager protocol, allowing safe resource management:

```python
async with MCPService() as service:
    await service.connect_servers(configs)
    # ... use service ...
# Automatic cleanup
```

### 2. Factory Method Pattern

`get_tools_for_llm()` provides tools in the specific format required by OpenAI-style function calling.

### 3. Template Method Pattern

The `_send_request` method provides a consistent interface for all JSON-RPC communication, with proper error handling and timeout management.

## Key Improvements

### MCP Server (`MCPServer` class)

- Added configurable timeout parameter
- Implemented proper MCP protocol initialization sequence
- Added async lock for thread-safe message sending
- Improved error handling with specific exception types
- Added `_cleanup_process` for reliable subprocess cleanup

### MCP Service (`MCPService` class)

- Implemented async context manager
- Added `get_tools_for_llm()` for LLM-ready tool formatting
- Added `is_connected()` helper method
- Improved `disconnect_all()` with parallel cleanup

### LLM Service (`LLMService` class)

- Updated `generate_with_system_prompt` to support tools parameter
- Updated `generate_agent_response` to pass tools through

### Canvas Execution (`execute_node` endpoint)

- Implemented complete tool call loop with proper LLM feedback
- Added max iteration limit to prevent infinite loops
- Added `finally` block for guaranteed resource cleanup
- Moved MCP import to top of file for better organization

## Files Modified

- `backend/app/services/mcp_service.py` - Major rewrite with fixes
- `backend/app/services/llm_service.py` - Added tools support to methods
- `backend/app/api/routes/canvas.py` - Fixed tool call flow

## Testing Recommendations

1. **Unit Tests:**

   - Test MCPServer connection and disconnection
   - Test timeout handling with mock server
   - Test environment variable merging
   - Test tool call parsing and execution

2. **Integration Tests:**

   - Test with actual MCP server (e.g., filesystem server)
   - Test full tool call loop with LLM
   - Test error recovery and cleanup

3. **Manual Testing:**
   - Create agent with MCP server configuration
   - Execute pipeline and verify tool usage
   - Test cancellation during tool execution

## Future Enhancements

1. **Connection Pooling:** Keep MCP servers running between requests for faster execution
2. **Tool Caching:** Cache tool lists to reduce initialization time
3. **Server Health Monitoring:** Track server health and auto-reconnect
4. **Tool Call Streaming:** Support streaming tool results for better UX
5. **Retry Logic:** Add configurable retry for transient failures
