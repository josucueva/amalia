# Python MCP Server Testing Guide

## Pre-Test Setup

### 1. Rebuild Backend Container

```bash
docker-compose down
docker-compose build backend
docker-compose up -d
```

### 2. Monitor Logs

In a separate terminal:

```bash
docker logs -f agentic-backend
```

Look for:

```
Python MCP server initialization...
Found 1 Python MCP server(s) to initialize
Validating server configurations...
Installing server dependencies...
Python MCP initialization complete
```

## Test Suite

### Test 1: Configuration Loading

**Expected**: Mathematics server loaded from config

```bash
# Check Python MCP servers endpoint
curl http://localhost:8000/api/mcp-servers/python | jq

# Expected output:
{
  "mathematics": {
    "server_id": "mathematics",
    "name": "Mathematics Server",
    "path": "/app/mcp_servers/mathematics/server.py",
    "command": "python",
    "args": [],
    "allowed_paths": ["/app/data/uploads"],
    "env": {"PYTHONPATH": "/app"},
    "description": "Mathematical operations and statistical calculations",
    "dependencies_file": "/app/mcp_servers/mathematics/requirements.txt",
    "is_valid": true,
    "dependencies_installed": true
  }
}
```

**✅ Pass Criteria**:

- Mathematics server appears
- `is_valid` is `true`
- `dependencies_installed` is `true`

---

### Test 2: Main MCP Server Registration

**Expected**: Python server registered in main MCP database as `python-mathematics`

```bash
# Check main MCP servers
curl http://localhost:8000/api/mcp-servers | jq

# Look for entry:
{
  "id": "python-mathematics",
  "name": "Mathematics Server",
  "command": "python",
  "args": ["/app/mcp_servers/mathematics/server.py"],
  ...
}
```

**✅ Pass Criteria**:

- `python-mathematics` server exists
- Command is `python`
- Args include correct path

---

### Test 3: Server Validation

**Expected**: Server file exists and is accessible

```bash
# Get specific server
curl http://localhost:8000/api/mcp-servers/python/mathematics | jq

# Check validation
docker exec agentic-backend ls -la /app/mcp_servers/mathematics/server.py

# Expected: File exists and is readable
-rw-r--r-- 1 root root ... /app/mcp_servers/mathematics/server.py
```

**✅ Pass Criteria**:

- Server file exists
- File is readable
- API returns `is_valid: true`

---

### Test 4: Tool Discovery via Agent

**Expected**: Agent can discover mathematics tools

#### 4a. Create Test Agent

Create `config/agents/math_test.yaml`:

```yaml
id: "math_test"
name: "Mathematics Test Agent"
description: "Test agent for mathematics MCP server"
system_prompt: "You are a helpful mathematics assistant."
tools: []
mcp_servers:
  - python-mathematics
temperature: 0.7
```

#### 4b. Test Agent Creation

```bash
# Create session with math test agent
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "math_test",
    "model_id": "gpt-4o-mini"
  }' | jq

# Save the session_id from response
```

#### 4c. Send Test Message

```bash
# Replace SESSION_ID with actual session ID
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "SESSION_ID",
    "message": "What is 15 + 27?"
  }' | jq

# Expected: Agent uses 'add' tool and returns 42
```

**✅ Pass Criteria**:

- Agent responds with correct answer (42)
- Logs show tool call to `add`
- Response includes tool execution

---

### Test 5: Tool Execution

**Expected**: Mathematics tools work correctly

```bash
# Test via backend logs
# Look for:
# - Tool call: add(15, 27)
# - Tool result: 42

# Or test multiple operations
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "SESSION_ID",
    "message": "Calculate the mean of these numbers: 10, 20, 30, 40, 50"
  }' | jq

# Expected: Agent uses 'mean' tool and returns 30
```

**✅ Pass Criteria**:

- Tools execute without errors
- Correct results returned
- Logs show successful execution

---

### Test 6: File Access

**Expected**: Server can access uploaded files

#### 6a. Upload Test File

```bash
# Create test CSV
echo "name,value
test1,10
test2,20
test3,30" > test_math.csv

# Upload via frontend or API
curl -X POST http://localhost:8000/api/files/upload \
  -F "file=@test_math.csv" | jq
```

#### 6b. Create File-Access Server

Create `backend/mcp_servers/file_test/server.py`:

```python
from mcp.server.fastmcp import FastMCP
import pandas as pd

mcp = FastMCP("File Test Server")

@mcp.tool()
def count_csv_rows(filename: str) -> int:
    """Count rows in uploaded CSV file."""
    df = pd.read_csv(f"/app/data/uploads/{filename}")
    return len(df)

if __name__ == "__main__":
    mcp.run()
```

Create `backend/mcp_servers/file_test/requirements.txt`:

```txt
pandas==2.1.4
```

#### 6c. Add to Config

Edit `backend/mcp_servers_config.json`:

```json
{
  "servers": {
    "file_test": {
      "name": "File Test Server",
      "path": "/app/mcp_servers/file_test/server.py",
      "command": "python",
      "args": [],
      "allowed_paths": ["/app/data/uploads"],
      "env": { "PYTHONPATH": "/app" },
      "description": "Test file access",
      "dependencies_file": "/app/mcp_servers/file_test/requirements.txt"
    }
  }
}
```

#### 6d. Restart and Test

```bash
docker-compose restart backend

# Wait for startup, then test
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "SESSION_ID",
    "message": "Count rows in file: test_math.csv"
  }' | jq

# Expected: Returns 3
```

**✅ Pass Criteria**:

- File accessible from server
- Tool returns correct row count
- No permission errors

---

### Test 7: Dependency Installation

**Expected**: Dependencies auto-install on startup

```bash
# Check logs for pandas installation
docker logs agentic-backend 2>&1 | grep -i pandas

# Expected output:
# Successfully installed pandas-2.1.4
# Dependencies installed successfully

# Verify in container
docker exec agentic-backend pip list | grep pandas

# Expected: pandas listed with version
```

**✅ Pass Criteria**:

- Pandas installed
- No installation errors
- Package available in container

---

### Test 8: API Registration

**Expected**: Can register server via API

```bash
# Create new server directory
docker exec agentic-backend mkdir -p /app/mcp_servers/api_test

# Create server file
docker exec agentic-backend sh -c 'cat > /app/mcp_servers/api_test/server.py << "EOF"
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("API Test Server")

@mcp.tool()
def hello(name: str) -> str:
    """Say hello."""
    return f"Hello, {name}!"

if __name__ == "__main__":
    mcp.run()
EOF'

# Register via API
curl -X POST http://localhost:8000/api/mcp-servers/python/api_test/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "API Test Server",
    "server_id": "api_test",
    "description": "Test API registration"
  }' | jq

# Expected:
{
  "message": "Python MCP server registered successfully",
  "server_id": "api_test",
  "mcp_server_id": "python-api_test",
  "is_valid": true,
  "dependencies_installed": true
}
```

**✅ Pass Criteria**:

- Registration succeeds
- Server appears in listings
- No validation errors

---

### Test 9: Error Handling

**Expected**: Graceful handling of missing files

```bash
# Try to get non-existent server
curl http://localhost:8000/api/mcp-servers/python/nonexistent | jq

# Expected:
{
  "detail": "Python MCP server 'nonexistent' not found"
}

# HTTP status: 404
```

**✅ Pass Criteria**:

- Returns 404 status
- Error message is clear
- No crashes or stack traces

---

### Test 10: Live Editing

**Expected**: Changes to server files work without rebuild

```bash
# Edit mathematics server to add new tool
# (Do this on host, not in container)
cat >> backend/mcp_servers/mathematics/server.py << 'EOF'

@mcp.tool()
def test_tool() -> str:
    """Test tool added dynamically."""
    return "Dynamic tool works!"
EOF

# Restart backend (not rebuild)
docker-compose restart backend

# Wait for startup, then check
# Tool should be available
```

**✅ Pass Criteria**:

- New tool appears without rebuild
- Volume mount working correctly
- Fast iteration cycle

---

## Troubleshooting

### Issue: Server Not Found

**Symptoms**: `Server file not found at /app/mcp_servers/.../server.py`

**Checks**:

```bash
# Verify file exists on host
ls -la backend/mcp_servers/*/server.py

# Verify volume mount
docker exec agentic-backend ls -la /app/mcp_servers/

# Check docker-compose.yml
grep -A2 "mcp_servers:" docker-compose.yml
```

**Fix**: Ensure volume mount is correct and backend restarted after adding files.

---

### Issue: Dependencies Not Installing

**Symptoms**: `Failed to install dependencies`

**Checks**:

```bash
# Check requirements.txt syntax
cat backend/mcp_servers/*/requirements.txt

# Try manual install
docker exec agentic-backend pip install -r /app/mcp_servers/.../requirements.txt

# Check logs
docker logs agentic-backend 2>&1 | grep -i "install"
```

**Fix**: Verify requirements.txt format and package names.

---

### Issue: Tools Not Available

**Symptoms**: Agent doesn't use tools

**Checks**:

```bash
# Verify server registered
curl http://localhost:8000/api/mcp-servers | grep python-

# Check agent config
cat config/agents/your_agent.yaml | grep mcp_servers

# Look for connection errors in logs
docker logs agentic-backend 2>&1 | grep -i "mcp.*error"
```

**Fix**: Ensure agent config includes `python-{server_id}` in mcp_servers list.

---

## Success Checklist

After running all tests:

- [ ] Configuration loads successfully
- [ ] Mathematics server appears in Python MCP list
- [ ] Mathematics server registered as `python-mathematics`
- [ ] Server file validated correctly
- [ ] Agent discovers and uses mathematics tools
- [ ] Tool execution returns correct results
- [ ] Server can access uploaded files
- [ ] Dependencies install automatically
- [ ] Can register servers via API
- [ ] Error handling works correctly
- [ ] Live editing works (volume mounts)

## Performance Benchmarks

**Startup Time**: ~5-10 seconds for MCP initialization
**Tool Discovery**: < 1 second
**Tool Execution**: < 100ms for simple operations
**Dependency Install**: 10-60 seconds depending on packages

## Next Steps

Once all tests pass:

1. ✅ Delete test servers/agents
2. ✅ Create your production MCP servers
3. ✅ Configure agents to use new servers
4. ✅ Monitor logs for issues
5. ✅ Document custom servers

## Automated Test Script

Create `test_python_mcp.sh`:

```bash
#!/bin/bash

echo "Testing Python MCP Implementation..."

# Test 1: Configuration
echo -n "Test 1: Configuration... "
RESULT=$(curl -s http://localhost:8000/api/mcp-servers/python | jq -r '.mathematics.is_valid')
[ "$RESULT" = "true" ] && echo "✅ PASS" || echo "❌ FAIL"

# Test 2: Main Registration
echo -n "Test 2: Main Registration... "
RESULT=$(curl -s http://localhost:8000/api/mcp-servers | jq -r '.servers[] | select(.id=="python-mathematics") | .id')
[ "$RESULT" = "python-mathematics" ] && echo "✅ PASS" || echo "❌ FAIL"

# Test 3: Server Validation
echo -n "Test 3: Server Validation... "
RESULT=$(docker exec agentic-backend test -f /app/mcp_servers/mathematics/server.py && echo "exists")
[ "$RESULT" = "exists" ] && echo "✅ PASS" || echo "❌ FAIL"

# Add more automated tests...

echo "Testing complete!"
```

Run with:

```bash
chmod +x test_python_mcp.sh
./test_python_mcp.sh
```
