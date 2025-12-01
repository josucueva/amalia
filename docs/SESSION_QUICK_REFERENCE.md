# Session Management - Quick Reference

## Overview

AMALIA's session management system provides persistent chat history and pipeline state using MongoDB.

## Key Features

✅ Automatic session creation on first message  
✅ Pipeline persistence (no duplicates)  
✅ MongoDB-backed storage  
✅ Session switching with history  
✅ Auto-restore most recent session on app load

---

## User Workflow

### Creating a Session

1. Click "New Session" button in sidebar
2. Session auto-created when sending first message
3. Each session has unique ID and timestamp title

### Using Sessions

```
Send Message → Creates/uses session automatically
Create Pipeline → Saved to current session (backend handles it)
Switch Sessions → Click session in sidebar
Delete Session → Auto-switches to next available
```

### Canvas Mode

```
Toggle Canvas Mode → Loads last pipeline from current session
Create Pipeline → Saves to current session
Switch Session → Reloads that session's last pipeline
```

---

## API Endpoints

### Sessions

```javascript
// Create session
POST /api/sessions/
Body: { "title": "Optional Title" }
Response: { "id": "session_xxx", "title": "...", ... }

// List sessions
GET /api/sessions/
Response: { "sessions": [...], "total": N }

// Get specific session
GET /api/sessions/{session_id}
Response: { "id": "...", "messages": [...], "pipelines": [...] }

// Update session
PUT /api/sessions/{session_id}
Body: { "title": "New Title", "status": "active|archived" }

// Delete session
DELETE /api/sessions/{session_id}
Response: { "success": true }

// Add message
POST /api/sessions/{session_id}/messages
Body: { "role": "user|assistant", "content": "..." }

// Add pipeline
POST /api/sessions/{session_id}/pipelines
Body: { "nodes": [...], "connections": [...] }
```

---

## Frontend State

### Global State

```javascript
state = {
  currentSession: {
    id: "session_xxxxx",
    title: "Session YYYY-MM-DD HH:MM",
    status: "active",
    messages: [
      { role: "user", content: "...", timestamp: "..." },
      { role: "assistant", content: "...", timestamp: "..." }
    ],
    pipelines: [
      { nodes: [...], connections: [...], created_at: "..." }
    ]
  },
  sessions: [...]  // List of all sessions
}
```

### State Updates

```javascript
// Update current session
state.setState({ currentSession: updatedSession });

// Refresh from backend
const session = await api.getSession(sessionId);
state.setState({ currentSession: session });
```

---

## MongoDB Schema

```javascript
{
  "_id": ObjectId("..."),
  "id": "session_xxxxx",           // Custom unique ID
  "title": "Session ...",
  "status": "active",              // "active" or "archived"
  "created_at": "2025-12-01T...",
  "updated_at": "2025-12-01T...",
  "messages": [
    {
      "role": "user|assistant",
      "content": "...",
      "timestamp": "2025-12-01T...",
      "metadata": {}
    }
  ],
  "pipelines": [
    {
      "nodes": [
        {
          "instanceId": "inst_1",
          "agentId": "data_loader",
          "position": { "x": 100, "y": 200 }
        }
      ],
      "connections": [
        {
          "id": "conn_1",
          "fromInstanceId": "inst_1",
          "toInstanceId": "inst_2"
        }
      ],
      "created_at": "2025-12-01T..."
    }
  ],
  "metadata": {}
}
```

---

## Common Tasks

### How to Create a New Session

```javascript
// Frontend (automatic)
const session = await api.createSession();
state.setState({ currentSession: session });

// Backend
session_manager = request.app.state.session_manager;
session = await session_manager.create_session((title = "My Session"));
```

### How to Save a Pipeline

```javascript
// Backend (in chat route - already handled)
await session_manager.add_pipeline(
  (session_id = session_id),
  (nodes = nodes),
  (connections = connections)
);

// Frontend - DON'T save manually, just refresh:
const updatedSession = await api.getSession(currentSession.id);
state.setState({ currentSession: updatedSession });
```

### How to Switch Sessions

```javascript
// In SessionSidebar.js
async switchSession(sessionId) {
  const session = await api.getSession(sessionId);
  state.setState({ currentSession: session });

  // Load messages
  globalThis.chat.clearMessages();
  session.messages.forEach(msg => {
    globalThis.chat.addMessage(msg);
  });

  // Load pipeline if in canvas mode
  if (globalThis.app.canvasMode && session.pipelines.length > 0) {
    const lastPipeline = session.pipelines[session.pipelines.length - 1];
    await globalThis.app.createPipelineFromData(
      lastPipeline.nodes,
      lastPipeline.connections
    );
  }
}
```

### How to Delete a Session

```javascript
// In SessionSidebar.js
async deleteSession(sessionId) {
  await api.deleteSession(sessionId);

  // If deleted current session, switch to next
  if (state.getState().currentSession?.id === sessionId) {
    const sessions = state.getState().sessions;
    if (sessions.length > 0) {
      await this.switchSession(sessions[0].id);
    }
  }

  await this.loadSessions();
}
```

---

## Debugging

### Check Session State

```javascript
// In browser console
console.log(state.getState().currentSession);
console.log(state.getState().sessions);
```

### Verify MongoDB Data

```bash
# In terminal
docker exec agentic-mongodb mongosh amalia --quiet --eval "db.sessions.find().pretty()"

# Count documents
docker exec agentic-mongodb mongosh amalia --quiet --eval "db.sessions.countDocuments({})"

# Get specific session
docker exec agentic-mongodb mongosh amalia --quiet --eval "db.sessions.findOne({id: 'session_xxxxx'})"
```

### Common Issues

**Issue**: Session not updating after pipeline creation

```javascript
// Fix: Refresh session from backend
const updatedSession = await api.getSession(currentSession.id);
state.setState({ currentSession: updatedSession });
```

**Issue**: Duplicate pipelines

```javascript
// Already fixed! Frontend no longer saves pipelines
// Backend handles it in chat.py
```

**Issue**: Session sidebar not updating

```javascript
// Make sure to call loadSessions() after changes
await this.loadSessions();
this.updateActiveSession(sessionId);
```

---

## Performance Tips

1. **Pagination**: Limit sessions loaded

   ```javascript
   const sessions = await api.listSessions("active", 20);
   ```

2. **Lazy Loading**: Only load messages when switching

   ```javascript
   // Don't load all messages upfront
   // Load on-demand when session is opened
   ```

3. **Debounce Updates**: Avoid excessive API calls
   ```javascript
   // Use throttling for rapid state changes
   const debouncedUpdate = debounce(updateSession, 500);
   ```

---

## Testing

### Manual Testing Checklist

- [ ] Create new session
- [ ] Send multiple messages
- [ ] Create pipeline via chat
- [ ] Switch between sessions
- [ ] Verify messages load correctly
- [ ] Verify pipelines load in canvas mode
- [ ] Delete session
- [ ] Verify auto-switch after deletion
- [ ] Refresh page and verify session restoration

### API Testing

```powershell
# PowerShell
$headers = @{'Content-Type'='application/json'}

# Create session
$session = Invoke-RestMethod -Uri http://localhost:8000/api/sessions/ -Method Post -Headers $headers -Body '{"title":"Test"}'

# Add message
$msg = @{role='user';content='Test'} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/sessions/$($session.id)/messages" -Method Post -Headers $headers -Body $msg

# Verify
Invoke-RestMethod -Uri "http://localhost:8000/api/sessions/$($session.id)" -Method Get
```

---

## Security Considerations

1. **Session Isolation**: Each user should have their own sessions
2. **Input Validation**: Sanitize message content
3. **Rate Limiting**: Prevent session spam
4. **Data Retention**: Implement session cleanup policy

---

## Future Enhancements

### Planned

- [ ] Session search/filter
- [ ] Session pagination
- [ ] Export/import sessions
- [ ] Session templates

### Ideas

- [ ] Session sharing/collaboration
- [ ] Real-time sync across tabs
- [ ] Offline support
- [ ] Session analytics

---

## References

- [SESSION_FIXES.md](./SESSION_FIXES.md) - Detailed fix documentation
- [SESSION_REVIEW_SUMMARY.md](./SESSION_REVIEW_SUMMARY.md) - Comprehensive review
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture

---

## Support

### Getting Help

1. Check console logs: `console.log(state.getState())`
2. Verify MongoDB: `docker exec agentic-mongodb mongosh amalia`
3. Check backend logs: `docker logs agentic-backend`
4. Review API responses in Network tab

### Common Errors

```
404 - Session not found
→ Session was deleted or doesn't exist
→ Refresh session list

500 - Internal server error
→ Check backend logs
→ Verify MongoDB connection

TypeError - Cannot read property 'id' of null
→ Session state not initialized
→ Call loadSessions() first
```

---

**Last Updated**: December 1, 2025  
**Status**: Production Ready ✓
