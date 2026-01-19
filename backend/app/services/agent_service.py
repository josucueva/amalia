"""
Service for managing agent configurations with persistent storage.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional
import structlog

from app.models.agent import Agent, AgentConfig
from app.agents.registry import AgentRegistry

logger = structlog.get_logger()


class AgentService:
    """
    Service for managing agent configurations.
    Handles loading from YAML and persisting changes to disk.
    """

    def __init__(
        self,
        config_dir: str = "config/agents",
        registry: Optional[AgentRegistry] = None,
    ):
        """
        Initialize the agent service.

        Args:
            config_dir: Directory containing agent YAML configs
            registry: Optional agent registry instance
        """
        self.config_dir = Path(config_dir)
        self.registry = registry or AgentRegistry()
        self._ensure_config_directory()
        self._load_all_agents()

    def _ensure_config_directory(self):
        """Ensure the config directory exists."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _load_all_agents(self):
        """Load all agent configurations from YAML files."""
        if not self.config_dir.exists():
            logger.warning("Agent config directory not found", dir=str(self.config_dir))
            return

        yaml_files = list(self.config_dir.glob("*.yaml")) + list(
            self.config_dir.glob("*.yml")
        )

        for yaml_file in yaml_files:
            try:
                self._load_agent_from_file(yaml_file)
            except Exception as e:
                logger.error(
                    "Failed to load agent config",
                    file=str(yaml_file),
                    error=str(e),
                )

        logger.info(
            "Agents loaded from config",
            count=self.registry.count(),
            dir=str(self.config_dir),
        )

    def _load_agent_from_file(self, yaml_file: Path):
        """
        Load an agent configuration from a YAML file.

        Args:
            yaml_file: Path to YAML file
        """
        with open(yaml_file, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        # Use filename (without extension) as agent ID
        agent_id = yaml_file.stem

        # Create AgentConfig
        agent_config = AgentConfig(**config_data)

        # Create Agent with ID
        agent = Agent(id=agent_id, config=agent_config)

        # Register agent
        self.registry.register_agent(agent)

    def _save_agent_to_file(self, agent: Agent):
        """
        Save an agent configuration to a YAML file.

        Args:
            agent: Agent to save
        """
        yaml_file = self.config_dir / f"{agent.id}.yaml"

        # Convert agent config to dict
        config_dict = agent.config.model_dump(exclude_none=True)

        # Write to YAML file
        with open(yaml_file, "w", encoding="utf-8") as f:
            yaml.dump(
                config_dict,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

        logger.info("Agent config saved", agent_id=agent.id, file=str(yaml_file))

    def create_agent(
        self,
        agent_id: str,
        config: AgentConfig,
    ) -> Agent:
        """
        Create a new agent and persist to disk.

        Args:
            agent_id: Unique agent ID
            config: Agent configuration

        Returns:
            Created agent

        Raises:
            ValueError: If agent ID already exists
        """
        if self.registry.get_agent(agent_id):
            raise ValueError(f"Agent with ID '{agent_id}' already exists")

        agent = Agent(id=agent_id, config=config)
        self.registry.register_agent(agent)
        self._save_agent_to_file(agent)

        logger.info("Agent created", agent_id=agent_id, name=config.name)
        return agent

    def update_agent(
        self,
        agent_id: str,
        config: AgentConfig,
    ) -> Optional[Agent]:
        """
        Update an existing agent and persist to disk.

        Args:
            agent_id: Agent ID
            config: Updated agent configuration

        Returns:
            Updated agent or None if not found
        """
        agent = self.registry.get_agent(agent_id)
        if not agent:
            logger.warning("Agent not found for update", agent_id=agent_id)
            return None

        # Update agent config
        agent.config = config
        self.registry.update_agent(agent)
        self._save_agent_to_file(agent)

        logger.info("Agent updated", agent_id=agent_id, name=config.name)
        return agent

    def delete_agent(self, agent_id: str) -> bool:
        """
        Delete an agent and remove its config file.

        Args:
            agent_id: Agent ID

        Returns:
            True if deleted, False if not found
        """
        if not self.registry.unregister_agent(agent_id):
            return False

        # Remove YAML file
        yaml_file = self.config_dir / f"{agent_id}.yaml"
        if yaml_file.exists():
            yaml_file.unlink()
            logger.info("Agent config file deleted", file=str(yaml_file))

        logger.info("Agent deleted", agent_id=agent_id)
        return True

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """
        Get an agent by ID.

        Args:
            agent_id: Agent ID

        Returns:
            Agent or None if not found
        """
        return self.registry.get_agent(agent_id)

    def list_agents(self, include_hidden: bool = False) -> List[Agent]:
        """
        List all agents.

        Args:
            include_hidden: Whether to include hidden/system agents

        Returns:
            List of agents
        """
        agents = self.registry.list_agents()

        if not include_hidden:
            agents = [
                agent
                for agent in agents
                if not agent.config.metadata
                or not agent.config.metadata.get("is_hidden", False)
            ]

        return agents

    def reload_agents(self):
        """
        Reload all agent configurations from disk.
        Useful for syncing changes made outside the application.
        """
        self.registry.clear()
        self._load_all_agents()
        logger.info("Agents reloaded from disk", count=self.registry.count())

    def export_agent(self, agent_id: str) -> Optional[Dict]:
        """
        Export agent configuration as a dictionary.

        Args:
            agent_id: Agent ID

        Returns:
            Agent config dict or None if not found
        """
        agent = self.registry.get_agent(agent_id)
        if not agent:
            return None

        return agent.config.model_dump(exclude_none=True)

    def import_agent(self, agent_id: str, config_dict: Dict) -> Agent:
        """
        Import agent configuration from a dictionary.

        Args:
            agent_id: Agent ID
            config_dict: Agent configuration dictionary

        Returns:
            Imported agent

        Raises:
            ValueError: If agent ID already exists
        """
        config = AgentConfig(**config_dict)
        return self.create_agent(agent_id, config)
