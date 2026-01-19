#!/usr/bin/env python3
"""
Initialize Python MCP servers on container startup.

This script:
1. Loads all Python MCP server configurations
2. Validates server files and paths
3. Installs required dependencies for each server
4. Logs the initialization status
"""
import sys
import structlog
from app.utils.python_mcp_manager import get_python_mcp_manager

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ]
)

logger = structlog.get_logger()


def initialize_python_mcp_servers():
    """Initialize all Python MCP servers."""
    logger.info("Starting Python MCP server initialization...")

    try:
        # Get manager instance (loads configurations)
        manager = get_python_mcp_manager()

        servers = manager.list_servers()
        if not servers:
            logger.info("No Python MCP servers configured")
            return True

        logger.info(f"Found {len(servers)} Python MCP server(s) to initialize")

        # Validate all servers
        logger.info("Validating server configurations...")
        validation_results = manager.validate_all_servers()

        invalid_servers = [
            server_id for server_id, valid in validation_results.items() if not valid
        ]
        if invalid_servers:
            logger.warning(
                "Some servers failed validation",
                invalid_servers=invalid_servers,
            )

        # Install dependencies
        logger.info("Installing server dependencies...")
        install_results = manager.install_all_dependencies()

        failed_installs = [
            server_id for server_id, success in install_results.items() if not success
        ]
        if failed_installs:
            logger.warning(
                "Some dependency installations failed",
                failed_servers=failed_installs,
            )

        # Summary
        total = len(servers)
        valid = sum(1 for v in validation_results.values() if v)
        deps_ok = sum(1 for v in install_results.values() if v)

        logger.info(
            "Python MCP server initialization complete",
            total_servers=total,
            valid_servers=valid,
            successful_dependencies=deps_ok,
        )

        # Log each server status
        for server_id, config in servers.items():
            logger.info(
                "Server status",
                server_id=server_id,
                name=config.name,
                valid=validation_results.get(server_id, False),
                dependencies_installed=install_results.get(server_id, False),
                path=config.path,
            )

        return True

    except Exception as e:
        logger.error("Python MCP server initialization failed", error=str(e))
        return False


if __name__ == "__main__":
    success = initialize_python_mcp_servers()
    sys.exit(0 if success else 1)
