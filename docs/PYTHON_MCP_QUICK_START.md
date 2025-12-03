# Quick Start: Adding a Python MCP Server

## 1. Create Server Directory

```bash
mkdir -p backend/mcp_servers/my_server
```

## 2. Create `server.py`

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("My Server Name")

@mcp.tool()
def my_tool(param: str) -> str:
    """Tool description for LLM."""
    return f"Result: {param}"

if __name__ == "__main__":
    mcp.run()
```

## 3. Create `requirements.txt` (optional)

```txt
# Add dependencies here
# httpx>=0.26.0
```

## 4. Add to Config

Edit `backend/mcp_servers_config.json`:

```json
{
  "servers": {
    "my_server": {
      "name": "My Server",
      "path": "/app/mcp_servers/my_server/server.py",
      "command": "python",
      "args": [],
      "allowed_paths": ["/app/data/uploads"],
      "env": { "PYTHONPATH": "/app" },
      "description": "My server description",
      "dependencies_file": "/app/mcp_servers/my_server/requirements.txt"
    }
  }
}
```

## 5. Restart Backend

```bash
docker-compose restart backend
```

## 6. Verify

```bash
# Check server is loaded
curl http://localhost:8000/api/mcp-servers/python

# Check it's in main MCP servers
curl http://localhost:8000/api/mcp-servers | grep python-my_server
```

## 7. Use in Agent

Edit agent YAML:

```yaml
mcp_servers:
  - python-my_server
```

## Done! 🎉

Your Python MCP server is now available to agents.

## File Access Example

```python
@mcp.tool()
def read_uploaded_file(filename: str) -> str:
    """Read a file from uploads directory."""
    import pandas as pd

    filepath = f"/app/data/uploads/{filename}"
    df = pd.read_csv(filepath)

    return f"Loaded {len(df)} rows from {filename}"
```

## Tips

- ✅ Use absolute paths: `/app/data/uploads/...`
- ✅ Add type hints for all parameters
- ✅ Write clear docstrings (LLMs see these)
- ✅ Handle errors with clear messages
- ❌ Don't use relative paths
- ❌ Don't hardcode secrets

See `docs/PYTHON_MCP_DEPLOYMENT.md` for complete guide.
