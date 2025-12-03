"""
Python MCP Server Configuration Loader and Dependency Manager

Handles loading Python MCP server configurations, installing dependencies,
and providing utilities for server path resolution.
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional
import structlog

logger = structlog.get_logger()


class PythonMCPConfig:
    """Configuration for a Python MCP server."""

    def __init__(
        self,
        server_id: str,
        name: str,
        path: str,
        command: str = "python",
        args: Optional[List[str]] = None,
        allowed_paths: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        description: Optional[str] = None,
        dependencies_file: Optional[str] = None,
    ):
        self.server_id = server_id
        self.name = name
        self.path = path
        self.command = command
        self.args = args or []
        self.allowed_paths = allowed_paths or ["/app/data/uploads"]
        self.env = env or {"PYTHONPATH": "/app"}
        self.description = description
        self.dependencies_file = dependencies_file

    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            "id": self.server_id,
            "name": self.name,
            "path": self.path,
            "command": self.command,
            "args": self.args,
            "allowed_paths": self.allowed_paths,
            "env": self.env,
            "description": self.description,
            "dependencies_file": self.dependencies_file,
        }


class PythonMCPManager:
    """Manager for Python MCP servers."""

    def __init__(self, config_path: str = "/app/mcp_servers_config.json"):
        self.config_path = config_path
        self.servers: Dict[str, PythonMCPConfig] = {}
        self._load_configurations()

    def _load_configurations(self) -> None:
        """Load server configurations from JSON file."""
        if not os.path.exists(self.config_path):
            logger.warning(
                "Python MCP config file not found, using empty configuration",
                path=self.config_path,
            )
            return

        try:
            with open(self.config_path, "r") as f:
                data = json.load(f)

            servers_data = data.get("servers", {})
            for server_id, config in servers_data.items():
                self.servers[server_id] = PythonMCPConfig(
                    server_id=server_id,
                    name=config.get("name", server_id),
                    path=config["path"],
                    command=config.get("command", "python"),
                    args=config.get("args", []),
                    allowed_paths=config.get("allowed_paths", ["/app/data/uploads"]),
                    env=config.get("env", {"PYTHONPATH": "/app"}),
                    description=config.get("description"),
                    dependencies_file=config.get("dependencies_file"),
                )

            logger.info(
                "Loaded Python MCP server configurations", count=len(self.servers)
            )
        except Exception as e:
            logger.error(
                "Failed to load Python MCP configurations",
                path=self.config_path,
                error=str(e),
            )
            raise

    def get_server(self, server_id: str) -> Optional[PythonMCPConfig]:
        """Get server configuration by ID."""
        return self.servers.get(server_id)

    def list_servers(self) -> Dict[str, PythonMCPConfig]:
        """Get all server configurations."""
        return self.servers

    def add_server(self, config: PythonMCPConfig) -> None:
        """Add a new server configuration."""
        self.servers[config.server_id] = config
        self._save_configurations()
        logger.info("Added Python MCP server", server_id=config.server_id)

    def remove_server(self, server_id: str) -> bool:
        """Remove a server configuration."""
        if server_id in self.servers:
            del self.servers[server_id]
            self._save_configurations()
            logger.info("Removed Python MCP server", server_id=server_id)
            return True
        return False

    def _save_configurations(self) -> None:
        """Save configurations to JSON file."""
        try:
            data = {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "description": "Python MCP servers configuration for AMALIA",
                "servers": {
                    server_id: {
                        "name": config.name,
                        "path": config.path,
                        "command": config.command,
                        "args": config.args,
                        "allowed_paths": config.allowed_paths,
                        "env": config.env,
                        "description": config.description,
                        "dependencies_file": config.dependencies_file,
                    }
                    for server_id, config in self.servers.items()
                },
            }

            with open(self.config_path, "w") as f:
                json.dump(data, f, indent=2)

            logger.info("Saved Python MCP configurations", path=self.config_path)
        except Exception as e:
            logger.error(
                "Failed to save Python MCP configurations",
                path=self.config_path,
                error=str(e),
            )
            raise

    def install_dependencies(self, server_id: str) -> bool:
        """Install dependencies for a specific server.

        Args:
            server_id: ID of the server

        Returns:
            True if successful, False otherwise
        """
        config = self.get_server(server_id)
        if not config:
            logger.error("Server not found", server_id=server_id)
            return False

        if not config.dependencies_file:
            logger.info(
                "No dependencies file specified for server", server_id=server_id
            )
            return True

        if not os.path.exists(config.dependencies_file):
            logger.warning(
                "Dependencies file not found",
                server_id=server_id,
                path=config.dependencies_file,
            )
            return True

        try:
            logger.info(
                "Installing dependencies for server",
                server_id=server_id,
                file=config.dependencies_file,
            )

            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", config.dependencies_file],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes timeout
            )

            if result.returncode == 0:
                logger.info("Dependencies installed successfully", server_id=server_id)
                return True
            else:
                logger.error(
                    "Failed to install dependencies",
                    server_id=server_id,
                    stderr=result.stderr,
                )
                return False

        except subprocess.TimeoutExpired:
            logger.error(
                "Dependency installation timed out", server_id=server_id
            )
            return False
        except Exception as e:
            logger.error(
                "Error installing dependencies",
                server_id=server_id,
                error=str(e),
            )
            return False

    def install_all_dependencies(self) -> Dict[str, bool]:
        """Install dependencies for all configured servers.

        Returns:
            Dictionary mapping server IDs to installation success status
        """
        results = {}
        for server_id in self.servers:
            results[server_id] = self.install_dependencies(server_id)

        successful = sum(1 for success in results.values() if success)
        logger.info(
            "Dependency installation complete",
            total=len(results),
            successful=successful,
            failed=len(results) - successful,
        )

        return results

    def validate_server(self, server_id: str) -> bool:
        """Validate that a server's Python file exists and is accessible.

        Args:
            server_id: ID of the server

        Returns:
            True if valid, False otherwise
        """
        config = self.get_server(server_id)
        if not config:
            logger.error("Server not found", server_id=server_id)
            return False

        if not os.path.exists(config.path):
            logger.error(
                "Server file not found", server_id=server_id, path=config.path
            )
            return False

        if not os.access(config.path, os.R_OK):
            logger.error(
                "Server file not readable", server_id=server_id, path=config.path
            )
            return False

        # Validate allowed paths exist
        for allowed_path in config.allowed_paths:
            if not os.path.exists(allowed_path):
                logger.warning(
                    "Allowed path does not exist",
                    server_id=server_id,
                    path=allowed_path,
                )

        logger.info("Server validation successful", server_id=server_id)
        return True

    def validate_all_servers(self) -> Dict[str, bool]:
        """Validate all configured servers.

        Returns:
            Dictionary mapping server IDs to validation status
        """
        results = {}
        for server_id in self.servers:
            results[server_id] = self.validate_server(server_id)

        valid = sum(1 for is_valid in results.values() if is_valid)
        logger.info(
            "Server validation complete",
            total=len(results),
            valid=valid,
            invalid=len(results) - valid,
        )

        return results

    @staticmethod
    def resolve_server_path(relative_path: str) -> str:
        """Resolve a relative server path to absolute Docker container path.

        Args:
            relative_path: Relative path (e.g., "mathematics/server.py")

        Returns:
            Absolute path within container (e.g., "/app/mcp_servers/mathematics/server.py")
        """
        return f"/app/mcp_servers/{relative_path}"

    @staticmethod
    def get_server_directory(server_id: str) -> str:
        """Get the directory path for a server.

        Args:
            server_id: ID of the server

        Returns:
            Absolute path to server directory
        """
        return f"/app/mcp_servers/{server_id}"


# Singleton instance
_manager_instance: Optional[PythonMCPManager] = None


def get_python_mcp_manager() -> PythonMCPManager:
    """Get or create the singleton PythonMCPManager instance."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = PythonMCPManager()
    return _manager_instance
