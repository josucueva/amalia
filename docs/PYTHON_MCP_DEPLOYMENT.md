# Python MCP Server Deployment Guide

## Overview

This guide explains how to deploy Python MCP (Model Context Protocol) servers in the AMALIA dockerized environment.

## Architecture

### Directory Structure

```
backend/
├── mcp_servers/                     # Python MCP servers root
│   ├── mathematics/                 # Example server
│   │   ├── server.py               # FastMCP server implementation
│   │   ├── requirements.txt        # Server-specific dependencies
│   │   └── README.md               # Server documentation
│   └── your_server/                # Your custom server
│       ├── server.py
│       ├── requirements.txt
│       └── README.md
├── mcp_servers_config.json         # Server configuration registry
└── init_python_mcp.py              # Startup initialization script
```

### Key Components

1. **FastMCP Server** (`server.py`): Python file using MCP SDK
2. **Dependencies** (`requirements.txt`): Python packages needed by the server
3. **Configuration** (`mcp_servers_config.json`): Server metadata and settings
4. **Manager** (`python_mcp_manager.py`): Configuration and dependency management
5. **API Routes** (`/api/mcp-servers/python/*`): Registration and management endpoints

## Creating a Python MCP Server

### Step 1: Create Server Directory

```bash
mkdir -p backend/mcp_servers/your_server
```

### Step 2: Create Server Implementation

Create `backend/mcp_servers/your_server/server.py`:

```python
"""
Your MCP Server Description
"""
from mcp.server.fastmcp import FastMCP

# Create server instance
mcp = FastMCP("Your Server Name")


@mcp.tool()
def your_tool(param1: str, param2: int) -> str:
    """
    Tool description for LLM.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Result description
    """
    # Your tool logic here
    return f"Processed: {param1} with {param2}"


# Run server
if __name__ == "__main__":
    mcp.run()
```

### Step 3: Specify Dependencies

Create `backend/mcp_servers/your_server/requirements.txt`:

```txt
# Add any Python packages your server needs
# The base 'mcp' package is already installed
httpx>=0.26.0
pandas>=2.0.0
# etc...
```

### Step 4: Register the Server

#### Option A: Manual Configuration

Edit `backend/mcp_servers_config.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "description": "Python MCP servers configuration for AMALIA",
  "servers": {
    "your_server": {
      "name": "Your Server Display Name",
      "path": "/app/mcp_servers/your_server/server.py",
      "command": "python",
      "args": [],
      "allowed_paths": ["/app/data/uploads"],
      "env": { "PYTHONPATH": "/app" },
      "description": "What your server does",
      "dependencies_file": "/app/mcp_servers/your_server/requirements.txt"
    }
  }
}
```

#### Option B: API Registration

```bash
curl -X POST http://localhost:8000/api/mcp-servers/python/your_server/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Your Server Display Name",
    "server_id": "your_server",
    "description": "What your server does",
    "allowed_paths": ["/app/data/uploads"]
  }'
```

### Step 5: Restart Backend

The server will be initialized on startup:

- Configuration loaded
- Files validated
- Dependencies installed
- Ready for use

## Docker Integration

### Volume Mounts

The `docker-compose.yml` includes:

```yaml
volumes:
  - ./backend/mcp_servers:/app/mcp_servers
  - ./backend/mcp_servers_config.json:/app/mcp_servers_config.json
```

### File Access

MCP servers can access configured paths:

- `/app/data/uploads` - Pipeline uploaded files (default)
- `/app/data` - Application data directory

To access uploaded files in your tool:

```python
@mcp.tool()
def process_file(filename: str) -> str:
    """Process an uploaded file."""
    import pandas as pd

    # Files are in /app/data/uploads
    filepath = f"/app/data/uploads/{filename}"
    df = pd.read_csv(filepath)

    return f"Processed {len(df)} rows"
```

## Path Resolution

### Container Paths

All paths are absolute within the Docker container:

- **Server files**: `/app/mcp_servers/{server_id}/server.py`
- **Dependencies**: `/app/mcp_servers/{server_id}/requirements.txt`
- **Uploaded data**: `/app/data/uploads/{filename}`
- **Config**: `/app/mcp_servers_config.json`

### Host Paths

When developing, edit files at:

- **Server files**: `./backend/mcp_servers/{server_id}/server.py`
- **Config**: `./backend/mcp_servers_config.json`

Changes sync immediately due to volume mounts.

## API Endpoints

### List Python MCP Servers

```bash
GET /api/mcp-servers/python
```

Returns all configured Python MCP servers with status.

### Get Specific Server

```bash
GET /api/mcp-servers/python/{server_id}
```

Returns configuration and validation status for a server.

### Register New Server

```bash
POST /api/mcp-servers/python/{server_id}/register
```

Registers a server and installs dependencies.

### Install Dependencies

```bash
POST /api/mcp-servers/python/{server_id}/install-dependencies
```

Reinstalls dependencies for a server.

## Using MCP Servers

### In Agent Configuration

MCP servers are registered in the main MCP server database with ID `python-{server_id}`.

To use in an agent YAML:

```yaml
mcp_servers:
  - python-mathematics
  - python-your_server
```

### Available Tools

Once registered, tools are available to agents:

```python
# The LLM can call your tools
{
  "tool_name": "your_tool",
  "arguments": {
    "param1": "value",
    "param2": 42
  }
}
```

## Example: Mathematics Server

The included mathematics server demonstrates best practices:

### Tools Provided

- `add`, `subtract`, `multiply`, `divide` - Basic arithmetic
- `power`, `square_root`, `factorial` - Advanced math
- `mean`, `median`, `standard_deviation` - Statistics
- `percentage`, `gcd`, `lcm` - Utilities

### Usage in Agent

```yaml
# config/agents/my_agent.yaml
name: "Data Analyst"
description: "Analyzes data with mathematical tools"
mcp_servers:
  - python-mathematics
```

The agent can now use all mathematics tools.

## Best Practices

### 1. Type Hints

Always use type hints for LLM schema generation:

```python
@mcp.tool()
def calculate(value: float, multiplier: int) -> dict:
    """Clear docstring for LLM."""
    return {"result": value * multiplier}
```

### 2. Error Handling

Provide clear error messages:

```python
@mcp.tool()
def divide(a: float, b: float) -> float:
    """Divide a by b."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
```

### 3. Docstrings

Write detailed docstrings - they become tool descriptions for LLMs:

```python
@mcp.tool()
def process_data(filepath: str, method: str) -> dict:
    """
    Process data file using specified method.

    Args:
        filepath: Relative path to file in uploads directory
        method: Processing method ('mean', 'sum', 'count')

    Returns:
        Dictionary with processing results
    """
    # Implementation
```

### 4. Dependencies

Keep `requirements.txt` minimal and pinned:

```txt
pandas==2.1.4
numpy==1.26.3
```

### 5. Server Names

Use descriptive, lowercase, hyphen-separated names:

- ✅ `data-analysis`, `file-processor`, `mathematics`
- ❌ `Server1`, `my_tool`, `ANALYSIS`

## Troubleshooting

### Server Not Found

**Error**: `Server file not found at /app/mcp_servers/{id}/server.py`

**Solution**: Ensure file exists and volume mount is correct:

```bash
ls -la backend/mcp_servers/{id}/server.py
```

### Dependencies Not Installing

**Error**: `Failed to install dependencies`

**Solution**: Check `requirements.txt` syntax and package availability:

```bash
# In container
docker exec -it agentic-backend bash
pip install -r /app/mcp_servers/{id}/requirements.txt
```

### Tools Not Available

**Error**: Tools don't appear in agent

**Solution**:

1. Check server is registered: `GET /api/mcp-servers/python`
2. Verify main MCP server exists: `GET /api/mcp-servers` (look for `python-{id}`)
3. Check agent config includes server: `mcp_servers: ["python-{id}"]`

### Path Access Issues

**Error**: `FileNotFoundError` when accessing files

**Solution**: Use absolute paths and check `allowed_paths`:

```python
# ✅ Correct
filepath = f"/app/data/uploads/{filename}"

# ❌ Wrong
filepath = f"./uploads/{filename}"
```

## Advanced Topics

### Custom Environment Variables

Add custom environment variables to your server:

```json
{
  "env": {
    "PYTHONPATH": "/app",
    "MY_API_KEY": "your-key-here",
    "DEBUG": "true"
  }
}
```

Access in server:

```python
import os

@mcp.tool()
def use_api() -> str:
    api_key = os.getenv("MY_API_KEY")
    # Use API key
```

### Multiple Allowed Paths

Grant access to multiple directories:

```json
{
  "allowed_paths": ["/app/data/uploads", "/app/data/processed", "/app/config"]
}
```

### Resource-Based Tools

MCP also supports resources (data contexts):

```python
@mcp.resource("data://statistics")
def get_statistics() -> dict:
    """Provide statistical data as context."""
    return {"mean": 42, "median": 40}
```

## Security Considerations

1. **File Access**: Only configure necessary paths in `allowed_paths`
2. **Dependencies**: Review third-party packages before installing
3. **Secrets**: Use environment variables, never hardcode secrets
4. **Input Validation**: Always validate tool arguments
5. **Error Messages**: Don't expose sensitive information in errors

## Reference

- [MCP Python SDK Documentation](https://github.com/modelcontextprotocol/python-sdk)
- [FastMCP Documentation](https://gofastmcp.com)
- [MCP Specification](https://spec.modelcontextprotocol.io)

## Support

For issues or questions:

1. Check logs: `docker logs agentic-backend`
2. Validate server: `GET /api/mcp-servers/python/{id}`
3. Review this documentation
4. Check MCP SDK documentation
