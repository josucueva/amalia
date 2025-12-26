# MCP Servers Directory

This directory contains Python MCP (Model Context Protocol) server implementations that extend AMALIA's capabilities.

## 🚀 Quick Start

See `/docs/PYTHON_MCP_QUICK_START.md` for a complete quick start guide.

## 📁 Included Servers

### Mathematics Server

- **Location**: `mathematics/`
- **Tools**: 15 mathematical and statistical operations
- **Usage**: Add `python-mathematics` to agent's `mcp_servers` list

## 📚 Documentation

- **Quick Start**: `/docs/PYTHON_MCP_QUICK_START.md` - Get started in 5 minutes
- **Full Guide**: `/docs/PYTHON_MCP_DEPLOYMENT.md` - Complete deployment documentation
- **Testing Guide**: `/docs/PYTHON_MCP_TESTING.md` - How to test your servers
- **Implementation**: `/docs/PYTHON_MCP_IMPLEMENTATION_SUMMARY.md` - Technical details

## 💡 Quick Example

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("My Server")

@mcp.tool()
def my_tool(param: str) -> str:
    """Tool description."""
    return f"Result: {param}"

if __name__ == "__main__":
    mcp.run()
```

Save as `my_server/server.py`, add to config, restart backend. Done!
