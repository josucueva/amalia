# How to Verify A2A Communication is Working

## Quick Checks

### 1. **Check Which Agents Have A2A Enabled**

```bash
curl http://localhost:8000/api/a2a/agents-using-a2a | jq
```

**What to look for:**

- List of agents with `a2a_enabled: true`
- Their `can_send_to` and `can_receive_from` configurations

---

### 2. **View A2A Statistics**

```bash
curl "http://localhost:8000/api/a2a/stats?hours=24&limit=50" | jq
```

**Shows:**

- `total_messages`: Total A2A messages in last 24 hours
- `messages_by_agent`: Message count per agent
- `recent_messages`: List of recent A2A communications
- `active_agents`: Agents actively using A2A

---

### 3. **Check Execution Response Metadata**

When you execute a pipeline node, the response now includes:

```json
{
  "instanceId": "instance_123",
  "agentType": "data_preprocessor",
  "output": "Processing complete\n\n🔗 A2A: Message sent to 'model_trainer' (correlation: abc12345...)",
  "a2a_used": true,
  "a2a_target": "model_trainer",
  "a2a_correlation_id": "abc12345-6789-...",
  "timestamp": "2025-12-30T16:30:00Z"
}
```

**Indicators:**

- ✅ `a2a_used: true` - A2A was used
- ✅ `a2a_target` - Shows which agent received the message
- ✅ `a2a_correlation_id` - Unique ID to trace the message
- ✅ Output contains 🔗 emoji and "A2A: Message sent..." text

---

### 4. **Trace a Specific Message**

If you have a correlation ID:

```bash
curl "http://localhost:8000/api/a2a/trace/{correlation_id}" | jq
```

**Shows:**

- Full message chain for request/reply patterns
- All agents involved
- Message content and timestamps

---

### 5. **View Message History for an Agent**

```bash
curl "http://localhost:8000/api/a2a/history/data_preprocessor?limit=20" | jq
```

**Shows:**

- All messages sent/received by the agent
- Recent communication patterns

---

### 6. **Watch Backend Logs**

A2A messages are logged with special markers:

```bash
docker compose logs -f backend | grep "A2A"
```

**Look for:**

```json
{
  "event": "✅ A2A MESSAGE SENT",
  "from_agent": "data_loader",
  "to_agent": "data_preprocessor",
  "correlation_id": "...",
  "mode": "A2A_ENABLED"
}
```

---

## Visual Indicators in Output

When A2A is used, you'll see in the agent output:

```
📊 Data preprocessing complete
- Cleaned 5000 rows
- Removed 42 duplicates
- Normalized numeric columns

🔗 A2A: Message sent to 'model_trainer' (correlation: 7a8b9c0d...)
```

The 🔗 emoji and message are automatically added when A2A mode is active.

---

## Testing A2A

### Execute with A2A Enabled

```bash
curl -X POST http://localhost:8000/api/canvas/execute \
  -H "Content-Type: application/json" \
  -d '{
    "instanceId": "test_123",
    "agentType": "data_loader",
    "inputs": [],
    "useA2A": true,
    "nextAgentId": "data_preprocessor"
  }' | jq
```

**Expected response:**

```json
{
  "a2a_used": true,
  "a2a_target": "data_preprocessor",
  "a2a_correlation_id": "uuid-here",
  "output": "...\n\n🔗 A2A: Message sent to 'data_preprocessor'..."
}
```

### Send Direct A2A Message

```bash
curl -X POST http://localhost:8000/api/a2a/send \
  -H "Content-Type: application/json" \
  -d '{
    "from_agent": "data_loader",
    "to_agent": "data_preprocessor",
    "content": {"test": "message"},
    "message_type": "task"
  }' | jq
```

Then check stats:

```bash
curl http://localhost:8000/api/a2a/stats | jq
```

---

## Common Scenarios

### ❌ A2A NOT Used (Direct Execution)

```json
{
  "a2a_used": false,
  "a2a_target": null,
  "a2a_correlation_id": null,
  "output": "Processing complete"
}
```

**Reasons:**

1. `a2a_enabled: false` in agent config
2. No `nextAgentId` provided
3. `useA2A: false` explicitly set

---

### ✅ A2A IS Used

```json
{
  "a2a_used": true,
  "a2a_target": "model_trainer",
  "a2a_correlation_id": "7a8b9c0d-...",
  "output": "...\n\n🔗 A2A: Message sent to 'model_trainer'..."
}
```

**Confirmed by:**

1. Response metadata shows `a2a_used: true`
2. Backend logs show "✅ A2A MESSAGE SENT"
3. Stats endpoint shows message count increased
4. Message appears in target agent's history

---

## Troubleshooting

### "I executed a pipeline but don't see A2A usage"

**Check:**

1. **Agent has A2A enabled:**

   ```bash
   curl http://localhost:8000/api/a2a/agents-using-a2a | jq '.agents[].name'
   ```

2. **Permissions are correct:**

   ```yaml
   # Sender must have target in can_send_to
   can_send_to: ["target_agent"]

   # Receiver must have sender in can_receive_from or "*"
   can_receive_from: ["*"]
   ```

3. **Request included A2A parameters:**

   ```json
   {
     "useA2A": true,
     "nextAgentId": "target_agent"
   }
   ```

4. **Check logs for errors:**
   ```bash
   docker compose logs backend | grep -i "a2a\|permission\|routing"
   ```

---

## Dashboard URLs

- **A2A Status**: http://localhost:8000/api/a2a/status
- **Statistics**: http://localhost:8000/api/a2a/stats
- **Enabled Agents**: http://localhost:8000/api/a2a/agents-using-a2a
- **API Docs**: http://localhost:8000/docs#/a2a

---

## Quick Summary

| What                       | Command                                        | Look For                |
| -------------------------- | ---------------------------------------------- | ----------------------- |
| Is A2A working?            | `curl localhost:8000/api/a2a/status`           | `"connected": true`     |
| Which agents use A2A?      | `curl localhost:8000/api/a2a/agents-using-a2a` | Agent list with configs |
| Was A2A used in execution? | Check response JSON                            | `"a2a_used": true`      |
| See recent A2A activity    | `curl localhost:8000/api/a2a/stats`            | `total_messages > 0`    |
| Trace specific message     | `curl localhost:8000/api/a2a/trace/{id}`       | Message chain           |
| Watch live                 | `docker compose logs -f backend \| grep A2A`   | Log entries with ✅     |

---

**Pro Tip:** Bookmark this URL for real-time stats:

```
http://localhost:8000/api/a2a/stats?hours=1
```
