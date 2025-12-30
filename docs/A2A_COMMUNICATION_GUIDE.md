# Agent-to-Agent (A2A) Communication - Implementation Guide

## Overview

The A2A communication system enables asynchronous message passing between agents using **Redis Pub/Sub**, following microservices best practices for distributed agent coordination.

## Architecture

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│  Agent A    │         │ Redis Pub/Sub│         │  Agent B    │
│             │────────▶│   Channel    │────────▶│             │
│ a2a_enabled │  send   │ agent:B:inbox│  recv   │ a2a_enabled │
└─────────────┘         └──────────────┘         └─────────────┘
       │                       │                         │
       │                       ▼                         │
       │               ┌──────────────┐                  │
       └──────────────▶│   MongoDB    │◀─────────────────┘
                       │  (History)   │
                       └──────────────┘
```

### Components

1. **RedisMessageQueue** (`backend/app/communication/message_queue.py`)

   - Async pub/sub messaging
   - Connection pooling
   - Dead letter queue for failures

2. **MessageRouter** (`backend/app/communication/router.py`)

   - Permission validation
   - `can_send_to` / `can_receive_from` enforcement
   - Broadcast support

3. **A2AService** (`backend/app/communication/a2a.py`)
   - High-level API
   - Message persistence
   - Request/reply pattern

---

## Configuration

### Enable A2A for an Agent

Edit `config/agents/<agent_name>.yaml`:

```yaml
agent:
  name: data_preprocessor
  description: "Handles data cleaning"
  model: "gpt-4o"
  system_prompt: "You are a data preprocessing expert"
  a2a_enabled: true # ← Enable A2A communication

  communication:
    can_receive_from:
      - "*" # Accept from anyone
    can_send_to:
      - "model_trainer" # Can only send to model_trainer
      - "feature_engineer"
```

### Communication Patterns

| Pattern              | `can_receive_from` | `can_send_to`          | Description                                   |
| -------------------- | ------------------ | ---------------------- | --------------------------------------------- |
| **Open Receiver**    | `["*"]`            | `["agent1", "agent2"]` | Accepts from anyone, sends to specific agents |
| **Restricted**       | `["agent1"]`       | `["agent2"]`           | Only accepts from agent1, sends to agent2     |
| **Broadcast Sender** | `["*"]`            | `["*"]`                | Fully open communication                      |
| **Isolated**         | `[]`               | `[]`                   | No A2A communication                          |

---

## Usage

### Method 1: Via Canvas (Frontend)

When executing agent nodes with connections:

```javascript
// Execute node with A2A enabled
const response = await fetch('/api/canvas/execute', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    instanceId: "instance_123",
    agentType: "data_preprocessor",
    inputs: [...],
    useA2A: true,  // Force A2A mode
    nextAgentId: "model_trainer"  // Target agent
  })
});
```

### Method 2: Direct API

Send message between agents:

```bash
curl -X POST http://localhost:8000/api/a2a/send \
  -H "Content-Type: application/json" \
  -d '{
    "from_agent": "data_preprocessor",
    "to_agent": "model_trainer",
    "content": {
      "file_path": "/app/data/uploads/sales.csv",
      "rows_cleaned": 1000
    },
    "message_type": "task"
  }'
```

Response:

```json
{
  "success": true,
  "correlation_id": "uuid-abc-123",
  "message": "Message sent successfully"
}
```

### Method 3: Python Service

```python
from app.communication.a2a import A2AService

# In your code
a2a_service = request.app.state.a2a_service

# Send message
correlation_id = await a2a_service.send_message(
    from_agent="data_loader",
    to_agent="data_preprocessor",
    content={"file_path": "/app/data/uploads/data.csv"},
    message_type="task"
)

# Wait for reply (request/reply pattern)
reply = await a2a_service.wait_for_reply(correlation_id, timeout=30.0)
print(reply.content)  # {'status': 'processed', 'rows': 5000}
```

---

## API Endpoints

### `GET /api/a2a/status`

Check A2A service status.

**Response:**

```json
{
  "available": true,
  "connected": true,
  "redis_connected": true
}
```

### `POST /api/a2a/send`

Send an A2A message.

**Request:**

```json
{
  "from_agent": "agent_id",
  "to_agent": "target_id",
  "content": { "key": "value" },
  "message_type": "task"
}
```

**Response:**

```json
{
  "success": true,
  "correlation_id": "uuid",
  "message": "Message sent successfully"
}
```

### `GET /api/a2a/history/{agent_id}?limit=50`

Get message history for an agent.

**Response:**

```json
{
  "messages": [
    {
      "from_agent": "agent_a",
      "to_agent": "agent_b",
      "content": {...},
      "timestamp": "2025-12-30T16:00:00Z",
      "correlation_id": "uuid"
    }
  ],
  "total": 15
}
```

---

## Advanced Features

### Request/Reply Pattern

```python
# Agent A sends request and waits for reply
reply = await a2a_service.send_and_wait_reply(
    from_agent="orchestrator",
    to_agent="data_loader",
    content={"action": "load_file", "path": "/data/sales.csv"},
    timeout=30.0
)

# Agent B processes and sends reply
await a2a_service.reply_to_message(
    original_message=received_message,
    from_agent="data_loader",
    content={"status": "loaded", "rows": 10000}
)
```

### Broadcast Messages

```python
# Send to all agents that accept from sender
await a2a_service.send_broadcast(
    from_agent="orchestrator",
    content={"command": "shutdown"},
    message_type="broadcast"
)
```

### Subscribe to Messages

```python
async def handle_message(message: A2AMessage):
    print(f"Received from {message.from_agent}: {message.content}")

await a2a_service.subscribe_agent(
    agent_id="model_trainer",
    callback=handle_message
)
```

---

## Error Handling

### Permission Denied

```json
{
  "status_code": 403,
  "detail": "Agent 'data_loader' is not allowed to send to 'admin_agent'. Check can_send_to configuration."
}
```

**Solution:** Update `can_send_to` list in sender's YAML configuration.

### Agent Not Found

```json
{
  "status_code": 404,
  "detail": "Receiver agent 'unknown_agent' not found"
}
```

**Solution:** Verify agent ID exists in registry.

### A2A Not Enabled

```json
{
  "status_code": 403,
  "detail": "Agent 'my_agent' does not have A2A enabled"
}
```

**Solution:** Set `a2a_enabled: true` in agent YAML.

### Timeout Waiting for Reply

```python
try:
    reply = await a2a_service.wait_for_reply(correlation_id, timeout=10.0)
except A2ATimeoutError:
    print("No reply received within 10 seconds")
```

---

## Debugging

### View Redis Messages (Live)

```bash
# Subscribe to all agent channels
docker exec -it agentic-redis redis-cli
127.0.0.1:6379> PSUBSCRIBE agent:*:inbox
```

### Check Dead Letter Queue

Messages that failed to deliver are stored in Redis:

```bash
docker exec -it agentic-redis redis-cli
127.0.0.1:6379> LRANGE agent:dead_letter_queue 0 -1
```

### View Message History

```bash
curl http://localhost:8000/api/a2a/history/data_preprocessor?limit=20
```

### Monitor Logs

```bash
docker compose logs -f backend | grep "A2A\|Message"
```

---

## Performance Characteristics

| Metric              | Value            | Notes                                     |
| ------------------- | ---------------- | ----------------------------------------- |
| **Message Latency** | < 10ms           | Redis pub/sub is sub-millisecond          |
| **Throughput**      | 10,000+ msg/s    | Limited by Redis capacity                 |
| **Persistence**     | Yes              | Messages stored in MongoDB                |
| **Durability**      | Best-effort      | Pub/sub doesn't persist if no subscribers |
| **Ordering**        | FIFO per channel | Per-agent inbox ordering guaranteed       |

---

## Best Practices

### 1. Use Specific Permissions

❌ **Don't:**

```yaml
communication:
  can_send_to: ["*"] # Too permissive
```

✅ **Do:**

```yaml
communication:
  can_send_to: ["model_trainer", "feature_engineer"] # Explicit
```

### 2. Handle Timeouts Gracefully

```python
try:
    reply = await a2a_service.send_and_wait_reply(
        from_agent="orchestrator",
        to_agent="slow_agent",
        content={...},
        timeout=60.0  # Adjust based on expected processing time
    )
except A2ATimeoutError:
    logger.warning("Agent did not respond, continuing with defaults")
    # Fallback logic
```

### 3. Include Context in Messages

```python
# Good message structure
content = {
    "file_path": "/app/data/uploads/sales.csv",
    "action": "preprocess",
    "parameters": {
        "remove_nulls": True,
        "normalize": True
    },
    "metadata": {
        "user_id": "user_123",
        "session_id": "session_456"
    }
}
```

### 4. Monitor Message History

Regularly check message history for debugging:

```python
messages = await a2a_service.get_message_history(
    agent_id="data_preprocessor",
    limit=100
)
```

---

## Comparison: A2A vs Direct Execution

| Aspect               | Direct Execution | A2A Communication    |
| -------------------- | ---------------- | -------------------- |
| **Coupling**         | Tight            | Loose                |
| **Async**            | Blocking         | Non-blocking         |
| **Scalability**      | Limited          | High                 |
| **Failure Handling** | Immediate fail   | Dead letter queue    |
| **Auditability**     | None             | Full message history |
| **Latency**          | Lower (~100ms)   | Higher (~110ms)      |

**When to use A2A:**

- Multi-agent workflows with complex dependencies
- Need for message audit trail
- Decoupled agent communication
- Broadcast notifications

**When to use Direct:**

- Simple single-agent execution
- Minimum latency required
- Sequential processing

---

## Troubleshooting

### Redis Connection Failed

**Error:** `redis.exceptions.ConnectionError: Error 111 connecting to localhost:6379`

**Solution:**

```bash
# Check Redis is running
docker compose ps redis

# Verify REDIS_HOST in .env
cat .env | grep REDIS_HOST
# Should be: REDIS_HOST=redis (not localhost)
```

### Messages Not Delivered

**Check:**

1. Both agents have `a2a_enabled: true`
2. Sender has target in `can_send_to`
3. Receiver has sender in `can_receive_from` or `["*"]`
4. Redis is running and connected

```bash
# Check A2A status
curl http://localhost:8000/api/a2a/status

# View recent logs
docker compose logs backend --tail=50 | grep "A2A"
```

### High Memory Usage

If Redis memory grows large:

```bash
# Check Redis memory
docker exec -it agentic-redis redis-cli INFO memory

# Clear old messages (if needed)
docker exec -it agentic-redis redis-cli FLUSHDB
```

---

## Future Enhancements

Planned improvements:

- [ ] WebSocket notifications for real-time message delivery
- [ ] Message priority queues
- [ ] Circuit breaker pattern for failing agents
- [ ] Metrics and observability (Prometheus/Grafana)
- [ ] Message encryption for sensitive data
- [ ] Rate limiting per agent
- [ ] Message replay functionality

---

## Examples

### Example 1: Data Processing Pipeline

```yaml
# data_loader.yaml
communication:
  can_send_to: ["data_preprocessor"]

# data_preprocessor.yaml
communication:
  can_receive_from: ["data_loader"]
  can_send_to: ["model_trainer"]

# model_trainer.yaml
communication:
  can_receive_from: ["data_preprocessor"]
  can_send_to: ["model_evaluator"]
```

Workflow:

```
data_loader → data_preprocessor → model_trainer → model_evaluator
```

### Example 2: Orchestrator Pattern

```yaml
# orchestrator.yaml
communication:
  can_send_to: ["*"]  # Can send to anyone
  can_receive_from: ["*"]  # Accepts replies

# worker agents
communication:
  can_receive_from: ["orchestrator"]
  can_send_to: ["orchestrator"]
```

Orchestrator broadcasts tasks to workers, collects results.

---

## Summary

The A2A communication system provides:

✅ **Asynchronous** message passing via Redis Pub/Sub  
✅ **Permission-based** routing with `can_send_to`/`can_receive_from`  
✅ **Persistent** message history in MongoDB  
✅ **Scalable** architecture for distributed agents  
✅ **Observable** with logging and monitoring  
✅ **Reliable** with dead letter queue for failures

For questions or issues, check the [troubleshooting section](#troubleshooting) or review logs with:

```bash
docker compose logs backend | grep -i "a2a\|redis\|error"
```
