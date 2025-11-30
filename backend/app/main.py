"""
FastAPI main application entry point.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import structlog

from app.config import get_settings
from app.api.routes import chat, agents, files, health, canvas, models, mcp_servers, sessions
from app.utils.logger import setup_logging


# Setup logging
setup_logging()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    settings = get_settings()
    logger.info("Starting application", version=settings.app_version)

    # Startup logic
    import os

    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(os.path.dirname(settings.log_file), exist_ok=True)

    # Load agents from YAML configuration
    from app.agents.registry import AgentRegistry
    from app.agents.config_loader import load_agents_from_directory

    try:
        agent_registry = AgentRegistry()
        agents_loaded = load_agents_from_directory(settings.agent_config_dir)
        for agent in agents_loaded:
            agent_registry.register_agent(agent)
        logger.info("Agents loaded", count=len(agents_loaded))

        # Store registry in app state
        app.state.agent_registry = agent_registry
    except Exception as e:
        logger.error("Error loading agents", error=str(e))
        # Continue without agents - app will use default configuration

    yield

    # Shutdown logic
    logger.info("Shutting down application")


# Create FastAPI application
app = FastAPI(
    title="Agentic AutoML Platform API",
    description="Backend API for the Agentic AutoML Platform",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Get settings
settings = get_settings()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(canvas.router, prefix="/api/canvas", tags=["canvas"])
app.include_router(models.router, tags=["models"])
app.include_router(mcp_servers.router, tags=["mcp-servers"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.debug,
    )
