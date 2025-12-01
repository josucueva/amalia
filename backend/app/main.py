"""
FastAPI main application entry point.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import structlog

from app.config import get_settings
from app.api.routes import (
    chat,
    agents,
    files,
    health,
    canvas,
    models,
    mcp_servers,
    sessions,
)
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

    # Initialize MongoDB connection
    from app.database import Database

    try:
        await Database.connect()
        logger.info("MongoDB connection established")
    except Exception as e:
        logger.error("Failed to connect to MongoDB", error=str(e))
        raise

    # Initialize services with MongoDB
    from app.services.agent_service_db import AgentService
    from app.services.model_service_db import ModelService
    from app.services.mcp_server_service_db import MCPServerService
    from app.services.session_manager_db import SessionManager

    try:
        # Initialize agent service and load from YAML
        agent_service = AgentService(config_dir=settings.agent_config_dir)
        await agent_service.initialize_from_yaml()
        logger.info("Agents loaded", count=agent_service.registry.count())

        # Store both service and registry in app state
        app.state.agent_service = agent_service
        app.state.agent_registry = agent_service.registry

        # Initialize model service with defaults
        model_service = ModelService()
        await model_service.initialize_default_models()
        app.state.model_service = model_service
        logger.info("Model service initialized")

        # Initialize MCP server service with defaults
        mcp_service = MCPServerService()
        await mcp_service.initialize_default_servers()
        app.state.mcp_server_service = mcp_service
        logger.info("MCP server service initialized")

        # Initialize session manager
        session_manager = SessionManager()
        app.state.session_manager = session_manager
        logger.info("Session manager initialized")

    except Exception as e:
        logger.error("Error initializing services", error=str(e))
        raise

    yield

    # Shutdown logic
    await Database.disconnect()
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
