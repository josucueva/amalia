# Data Persistence Guide

AMALIA uses Docker volumes for persistent storage, ensuring your data survives container restarts and rebuilds.

## Overview

### Persistent Data Storage

All critical application data is stored in Docker named volumes:

| Volume                 | Purpose              | Data Stored                            |
| ---------------------- | -------------------- | -------------------------------------- |
| `amalia_agent_configs` | Agent configurations | YAML files for all agent definitions   |
| `amalia_app_data`      | Application state    | Models, sessions, MCP servers, uploads |
| `amalia_app_logs`      | Application logs     | Backend logs for debugging             |
| `amalia_redis_data`    | Redis persistence    | Message queue and cache data           |

### What Gets Persisted

✅ **Agent Configurations**

- All custom agent definitions (YAML)
- Agent updates and modifications
- System agents (planner, orchestrator, interaction)

✅ **Sessions**

- Chat history
- Pipeline snapshots
- Session metadata

✅ **Models**

- LLM model configurations
- API key settings
- Model availability status

✅ **MCP Servers**

- Server configurations
- Connection settings

✅ **Uploaded Files**

- User-uploaded datasets
- File metadata

✅ **Logs**

- Application logs
- Error traces
- Audit trails

## Usage

### Normal Operations

When you restart containers, all data is automatically persisted:

```powershell
# Restart containers - data is preserved
docker compose restart

# Rebuild containers - data is preserved
docker compose up --build

# Stop and start - data is preserved
docker compose down
docker compose up
```

### Volume Management

Use the included `manage-volumes.ps1` script:

#### List Volumes

```powershell
.\manage-volumes.ps1 -Action list
```

Shows all volumes and their status.

#### Backup Volumes

```powershell
.\manage-volumes.ps1 -Action backup
```

Creates a timestamped backup of all volumes in `./volume-backups/`.

#### Restore Volumes

```powershell
.\manage-volumes.ps1 -Action restore
```

Restores data from the most recent backup.

#### Clean Volumes

```powershell
.\manage-volumes.ps1 -Action clean
```

⚠️ **WARNING**: Deletes all persistent data! Use with caution.

#### Inspect Volumes

```powershell
.\manage-volumes.ps1 -Action inspect
```

Shows detailed information about each volume.

## File Locations

### Inside Containers

- **Agent Configs**: `/app/config/agents/`
- **Application Data**: `/app/data/`
  - Sessions: `/app/data/sessions.json`
  - Models: `/app/data/models.json`
  - MCP Servers: `/app/data/mcp_servers.json`
  - Uploads: `/app/data/uploads/`
- **Logs**: `/app/logs/`

### On Host (Volume Mounts)

Docker volumes are stored in Docker's internal storage. To access:

```powershell
# Find volume location
docker volume inspect amalia_app_data

# Access volume data via temporary container
docker run --rm -v amalia_app_data:/data alpine ls -la /data
```

## Migration & Backup Strategy

### Before Major Updates

1. **Backup volumes**:

   ```powershell
   .\manage-volumes.ps1 -Action backup
   ```

2. **Update code**:

   ```powershell
   git pull origin main
   ```

3. **Rebuild containers**:

   ```powershell
   docker compose up --build
   ```

4. **If issues occur**, restore backup:
   ```powershell
   docker compose down
   .\manage-volumes.ps1 -Action restore
   docker compose up
   ```

### Transferring to Another Machine

1. **On source machine**, backup volumes:

   ```powershell
   .\manage-volumes.ps1 -Action backup
   ```

2. **Copy** `volume-backups/` folder to target machine

3. **On target machine**, restore:
   ```powershell
   .\manage-volumes.ps1 -Action restore
   docker compose up
   ```

## Best Practices

### Regular Backups

Set up automated backups using Windows Task Scheduler:

```powershell
# Example: Daily backup at 2 AM
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" `
    -Argument "-File C:\path\to\manage-volumes.ps1 -Action backup"
$trigger = New-ScheduledTaskTrigger -Daily -At 2am
Register-ScheduledTask -TaskName "AMALIA Backup" `
    -Action $action -Trigger $trigger
```

### Development Workflow

- **Development**: Use volumes for fast iteration
- **Testing**: Clean volumes between tests
- **Production**: Regular backups + monitoring

### Troubleshooting

#### Data Not Persisting

1. Check volume exists:

   ```powershell
   docker volume ls | Select-String "amalia"
   ```

2. Inspect volume:

   ```powershell
   docker volume inspect amalia_app_data
   ```

3. Verify mount in container:
   ```powershell
   docker exec agentic-backend ls -la /app/data
   ```

#### Container Won't Start

1. Check logs:

   ```powershell
   docker compose logs backend
   ```

2. Verify volume permissions:
   ```powershell
   docker run --rm -v amalia_app_data:/data alpine ls -la /data
   ```

#### Corrupted Data

1. Stop containers:

   ```powershell
   docker compose down
   ```

2. Restore from backup:

   ```powershell
   .\manage-volumes.ps1 -Action restore
   ```

3. Restart:
   ```powershell
   docker compose up
   ```

## Technical Details

### Volume Drivers

- **Driver**: local
- **Type**: bind mount to Docker's storage directory
- **Persistence**: Survives container deletion
- **Scope**: local to Docker host

### Atomic Writes

Services use atomic write patterns:

- Write to temporary file
- Move to target location
- Prevents corruption on crash

### Data Format

- **Agent Configs**: YAML (human-readable, version-controllable)
- **Application State**: JSON (structured, easily parseable)
- **Logs**: Structured JSON logs (searchable, analyzable)

## API Endpoints

### Agent Persistence

- `POST /api/agents` - Create agent (auto-persisted)
- `PUT /api/agents/{id}` - Update agent (auto-persisted)
- `DELETE /api/agents/{id}` - Delete agent (removes YAML)
- `POST /api/agents/reload-from-yaml` - Reload from disk

### Session Persistence

- Sessions auto-save on every message
- Canvas state saved on demand via UI
- All operations atomic

### Model Persistence

- Model configs auto-save on add/update/delete
- API keys stored in environment variables (not in volumes)

## Security Considerations

### Sensitive Data

⚠️ **Never commit volumes to git**

- Volumes may contain API keys
- User data and sessions are private
- Backups should be encrypted for production

### API Keys

- Stored in `.env` file (not in volumes)
- Mounted as environment variables
- Never logged or exposed via API

### File Uploads

- Validated on upload
- Stored in isolated directory
- File permissions restricted

## Monitoring

### Check Disk Usage

```powershell
# Check volume sizes
docker system df -v

# Check specific volume
docker run --rm -v amalia_app_data:/data alpine du -sh /data
```

### Health Checks

The application includes health endpoints:

- `GET /health` - Overall health
- `GET /health/storage` - Storage status (if implemented)

## Future Enhancements

Planned improvements:

- [ ] PostgreSQL migration for structured data
- [ ] S3-compatible storage for uploads
- [ ] Automated backup to cloud storage
- [ ] Data encryption at rest
- [ ] Multi-environment volume sets
