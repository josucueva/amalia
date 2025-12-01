# Persistence Implementation Summary

## Overview

Implemented comprehensive data persistence for AMALIA using Docker volumes, ensuring all application state survives container restarts and rebuilds.

## Changes Made

### 1. Docker Configuration

**File**: `docker-compose.yml`

- Added named volumes for persistent storage:

  - `amalia_agent_configs` - Agent configuration YAML files
  - `amalia_app_data` - Application state (sessions, models, MCP servers, uploads)
  - `amalia_app_logs` - Application logs
  - `amalia_redis_data` - Redis persistence (already existed)

- Updated backend volume mounts to use named volumes instead of bind mounts for data directories

### 2. Backend Services

**New File**: `backend/app/services/agent_service.py`

- Created `AgentService` class for agent configuration management
- Handles loading agents from YAML files
- Implements create/update/delete operations with automatic persistence
- Supports import/export of agent configurations
- Integrates with existing `AgentRegistry`

**Updated File**: `backend/app/api/routes/agents.py`

- Refactored to use `AgentService` instead of direct file operations
- All CRUD operations now automatically persist to disk
- Simplified code by delegating persistence logic to service layer

**Updated File**: `backend/app/main.py`

- Initialize `AgentService` on startup
- Store both service and registry in app state for access by routes

### 3. Management Scripts

**New File**: `manage-volumes.ps1`

PowerShell script for volume management:

- `backup` - Create timestamped backups of all volumes
- `restore` - Restore from latest backup
- `list` - Show all volumes and their status
- `inspect` - Detailed volume information
- `clean` - Delete all volumes (with confirmation)

**New File**: `init-volumes.ps1`

Initialize volumes with existing local data:

- Copies agent configs from `./config/agents/`
- Copies application data from `./data/`
- Creates necessary directories in volumes

### 4. Documentation

**New File**: `docs/PERSISTENCE.md`

Comprehensive guide covering:

- Persistence architecture
- Volume structure and contents
- Usage instructions
- Backup and restore procedures
- Troubleshooting
- Best practices
- Security considerations

**New File**: `PERSISTENCE_QUICK_REF.md`

Quick reference card for common operations:

- Daily development workflow
- Backup/restore commands
- Emergency recovery
- API endpoints reference

**Updated File**: `README.md`

- Added persistence feature to features list
- Added volume management section
- Added link to persistence documentation

**Updated File**: `.gitignore`

- Added `volume-backups/` to prevent committing backup data

## What Gets Persisted

### Agent Configurations

- Location: `config/agents/*.yaml`
- Auto-saved on: Create, Update
- Deleted on: Agent deletion

### Sessions

- Location: `data/sessions.json`
- Auto-saved on: Every message, pipeline update
- Format: JSON with complete chat history and pipeline snapshots

### Models

- Location: `data/models.json`
- Auto-saved on: Add, Update, Delete
- Format: JSON with model configurations

### MCP Servers

- Location: `data/mcp_servers.json`
- Auto-saved on: Configuration changes
- Format: JSON with server definitions

### File Uploads

- Location: `data/uploads/`
- Auto-saved on: Upload
- Preserved indefinitely

### Logs

- Location: `logs/`
- Auto-saved: Real-time
- Format: Structured JSON logs

## Usage

### First-Time Setup

```powershell
# Initialize volumes with existing data (optional)
.\init-volumes.ps1

# Start containers
docker compose up
```

### Daily Workflow

```powershell
# Restart containers (data persists)
docker compose restart

# Rebuild after code changes (data persists)
docker compose up --build
```

### Backup & Restore

```powershell
# Create backup before major changes
.\manage-volumes.ps1 -Action backup

# Restore if needed
.\manage-volumes.ps1 -Action restore
```

## Benefits

✅ **No Data Loss**: Container restarts and rebuilds preserve all data
✅ **Easy Backups**: Simple PowerShell commands for backup/restore
✅ **Atomic Operations**: All persistence operations use atomic writes
✅ **Transparent**: Developers don't need to manually save/load
✅ **Portable**: Easy to transfer data between machines
✅ **Version Control**: YAML configs can be committed to git
✅ **Debugging**: Logs persist for troubleshooting

## Migration Path

For users with existing local data:

1. Run `.\init-volumes.ps1` to copy existing data to volumes
2. Start containers with `docker compose up`
3. Verify data loaded correctly
4. Continue using the app normally

All future changes automatically persist to volumes.

## API Changes

No breaking changes to existing APIs. All endpoints continue to work as before, but now automatically persist data.

New endpoint:

- `POST /api/agents/reload-from-yaml` - Reload agents from disk

## Technical Details

### Persistence Strategy

- **Agent Configs**: YAML files (human-readable, git-friendly)
- **App State**: JSON files (structured, easily parseable)
- **Atomic Writes**: Temp file → rename pattern prevents corruption
- **Volume Drivers**: Local driver with Docker-managed storage

### File Locations

**In Container**:

- `/app/config/agents/` - Agent YAML files
- `/app/data/` - Application JSON files
- `/app/logs/` - Log files

**On Host**:

- Docker internal storage (inspect with `docker volume inspect`)
- Backups in `./volume-backups/`

## Testing

To test persistence:

1. Create some data (agents, sessions, etc.)
2. Stop containers: `docker compose down`
3. Start containers: `docker compose up`
4. Verify data is still there

To test backups:

1. Create data
2. Backup: `.\manage-volumes.ps1 -Action backup`
3. Delete data or modify it
4. Restore: `.\manage-volumes.ps1 -Action restore`
5. Verify original data restored

## Future Enhancements

Potential improvements:

- PostgreSQL migration for relational data
- S3-compatible storage for uploads
- Automated backup scheduling
- Data encryption at rest
- Multi-environment volume sets
- Cloud backup integration
