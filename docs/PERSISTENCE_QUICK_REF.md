# Quick Reference: Data Persistence

## Common Operations

### First-Time Setup

```powershell
# Initialize volumes with existing data
.\init-volumes.ps1

# Start containers
docker compose up
```

### Daily Development

```powershell
# Restart containers (data persists)
docker compose restart

# Rebuild after code changes (data persists)
docker compose up --build

# Stop containers (data persists)
docker compose down
```

### Backup & Restore

```powershell
# Create backup
.\manage-volumes.ps1 -Action backup

# Restore latest backup
.\manage-volumes.ps1 -Action restore

# List all volumes
.\manage-volumes.ps1 -Action list
```

### Troubleshooting

```powershell
# Inspect volumes
.\manage-volumes.ps1 -Action inspect

# View container logs
docker compose logs backend
docker compose logs frontend

# Access volume data
docker run --rm -v amalia_app_data:/data alpine ls -la /data
```

### Clean Start

```powershell
# WARNING: Deletes all data!
.\manage-volumes.ps1 -Action clean

# Then initialize fresh
.\init-volumes.ps1
docker compose up
```

## What Gets Persisted

| Data Type     | Location                | Auto-Save               |
| ------------- | ----------------------- | ----------------------- |
| Agent configs | `config/agents/*.yaml`  | ✅ On create/update     |
| Sessions      | `data/sessions.json`    | ✅ On every message     |
| Models        | `data/models.json`      | ✅ On add/update/delete |
| MCP Servers   | `data/mcp_servers.json` | ✅ On config change     |
| Uploads       | `data/uploads/`         | ✅ On upload            |
| Logs          | `logs/`                 | ✅ Real-time            |

## Best Practices

✅ **DO**

- Backup before major updates
- Use version control for agent configs
- Monitor disk usage regularly
- Test restores periodically

❌ **DON'T**

- Commit volume backups to git
- Store API keys in volumes
- Edit files directly in volumes
- Delete volumes without backup

## Emergency Recovery

If something goes wrong:

1. **Stop containers**:

   ```powershell
   docker compose down
   ```

2. **Restore from backup**:

   ```powershell
   .\manage-volumes.ps1 -Action restore
   ```

3. **Restart**:
   ```powershell
   docker compose up
   ```

## File Locations Reference

### In Container

- Agent configs: `/app/config/agents/`
- App data: `/app/data/`
- Logs: `/app/logs/`

### On Host

- Code: `./backend/`, `./frontend/`
- Backups: `./volume-backups/`
- Volumes: Docker internal storage

## API Endpoints

### Agent Management

- `GET /api/agents` - List all agents
- `POST /api/agents` - Create agent (persisted)
- `PUT /api/agents/{id}` - Update agent (persisted)
- `DELETE /api/agents/{id}` - Delete agent (removes file)
- `POST /api/agents/reload-from-yaml` - Reload from disk

### Session Management

- `GET /api/sessions` - List sessions
- `POST /api/sessions` - Create session
- `GET /api/sessions/{id}` - Get session (with history)
- `DELETE /api/sessions/{id}` - Delete session

### Model Management

- `GET /api/models` - List models
- `POST /api/models` - Add model
- `PUT /api/models/{id}` - Update model
- `DELETE /api/models/{id}` - Delete model

All operations automatically persist to disk!
