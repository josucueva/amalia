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
    a2a,
    a2a_analytics,
)
from app.api.routes import a2a_autonomous
from app.utils.logger import setup_logging


# Setup logging
setup_logging()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    settings = get_settings()
    logger.info("Starting application", version=settings.app_version)

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
    from app.services.llm_service import get_llm_service
    from app.utils.python_mcp_manager import get_python_mcp_manager

    try:
        # Initialize Python MCP servers (install dependencies, validate)
        logger.info("Initializing Python MCP servers...")
        python_mcp_manager = get_python_mcp_manager()
        validation_results = python_mcp_manager.validate_all_servers()
        install_results = python_mcp_manager.install_all_dependencies()
        
        valid_count = sum(1 for v in validation_results.values() if v)
        deps_count = sum(1 for v in install_results.values() if v)
        logger.info(
            "Python MCP initialization complete",
            total=len(python_mcp_manager.list_servers()),
            valid=valid_count,
            dependencies_installed=deps_count
        )
        app.state.python_mcp_manager = python_mcp_manager
        
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
        
        # Register Python MCP servers in main MCP database
        from app.models.mcp_server import MCPServer
        for server_id, config in python_mcp_manager.list_servers().items():
            mcp_server_id = f"python-{server_id}"
            
            # Check if already registered
            existing = await mcp_service.get_server(mcp_server_id)
            if not existing:
                python_mcp_server = MCPServer(
                    id=mcp_server_id,
                    name=config.name,
                    command=config.command,
                    args=[config.path],
                    env=config.env,
                    description=config.description or f"Python MCP Server: {config.name}",
                    is_available=True,
                )
                await mcp_service.add_server(python_mcp_server)
                logger.info("Registered Python MCP server", server_id=mcp_server_id, name=config.name)
            else:
                logger.info("Python MCP server already registered", server_id=mcp_server_id)

        # Initialize session manager
        session_manager = SessionManager()
        app.state.session_manager = session_manager
        logger.info("Session manager initialized")

        # Initialize A2A communication service
        from app.communication.a2a import A2AService
        from app.communication.agent_executor import AgentExecutor
        from app.communication.listener_manager import A2AListenerManager

        a2a_service = A2AService(agent_service.registry)
        await a2a_service.connect()
        app.state.a2a_service = a2a_service
        logger.info("A2A communication service initialized")
        
        # Initialize agent executor for autonomous A2A
        llm_service = get_llm_service(settings)
        agent_executor = AgentExecutor(llm_service, agent_service.registry, a2a_service)
        app.state.agent_executor = agent_executor
        
        # Initialize and start A2A listener manager
        listener_manager = A2AListenerManager(a2a_service, agent_executor)
        await listener_manager.start_listeners(agent_service.registry)
        app.state.listener_manager = listener_manager
        logger.info("A2A autonomous listeners initialized")

    except Exception as e:
        logger.error("Error initializing services", error=str(e))
        raise

    yield

    # Shutdown logic
    # Stop A2A listeners
    if hasattr(app.state, "listener_manager"):
        try:
            await app.state.listener_manager.stop_all_listeners()
            logger.info("A2A listeners stopped")
        except Exception as e:
            logger.warning("Error stopping A2A listeners", error=str(e))
    
    # Disconnect A2A service
    if hasattr(app.state, "a2a_service"):
        try:
            await app.state.a2a_service.disconnect()
            logger.info("A2A service disconnected")
        except Exception as e:
            logger.warning("Error disconnecting A2A service", error=str(e))

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
app.include_router(a2a.router, prefix="/api/a2a", tags=["a2a"])
app.include_router(a2a_analytics.router, prefix="/api/a2a", tags=["a2a-analytics"])
app.include_router(a2a_autonomous.router, prefix="/api/a2a", tags=["a2a-autonomous"])


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
