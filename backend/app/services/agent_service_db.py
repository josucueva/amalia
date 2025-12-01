"""
MongoDB-based agent service for managing agent configurations.
"""

import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
import structlog

from app.models.agent import Agent, AgentConfig
from app.agents.registry import AgentRegistry
from app.database import get_db

logger = structlog.get_logger()


class AgentService:
    """
    Service for managing agent configurations using MongoDB.
    Also maintains YAML files for version control and portability.
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
        self.collection_name = "agents"
        self._ensure_config_directory()

    def _ensure_config_directory(self):
        """Ensure the config directory exists."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _get_collection(self):
        """Get agents collection."""
        return get_db()[self.collection_name]

    async def initialize_from_yaml(self):
        """Load all agent configurations from YAML files into MongoDB and registry."""
        if not self.config_dir.exists():
            logger.warning("Agent config directory not found", dir=str(self.config_dir))
            return

        yaml_files = list(self.config_dir.glob("*.yaml")) + list(
            self.config_dir.glob("*.yml")
        )

        collection = self._get_collection()

        for yaml_file in yaml_files:
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    config_data = yaml.safe_load(f)

                # Handle YAML files with 'agent' wrapper key
                if "agent" in config_data:
                    config_data = config_data["agent"]

                agent_id = yaml_file.stem
                agent_config = AgentConfig(**config_data)

                # Create agent with timestamps
                now = datetime.now(timezone.utc).isoformat()
                agent = Agent(
                    id=agent_id, config=agent_config, created_at=now, updated_at=now
                )

                # Store in MongoDB (upsert)
                await collection.replace_one(
                    {"id": agent_id}, agent.model_dump(), upsert=True
                )

                # Register in memory
                self.registry.register_agent(agent)

            except Exception as e:
                logger.error(
                    "Failed to load agent config",
                    file=str(yaml_file),
                    error=str(e),
                )

        logger.info(
            "Agents initialized from YAML",
            count=self.registry.count(),
            dir=str(self.config_dir),
        )

    async def _save_agent_to_yaml(self, agent: Agent):
        """
        Save an agent configuration to a YAML file.

        Args:
            agent: Agent to save
        """
        yaml_file = self.config_dir / f"{agent.id}.yaml"
        config_dict = agent.config.model_dump(exclude_none=True)

        with open(yaml_file, "w", encoding="utf-8") as f:
            yaml.dump(
                config_dict,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

        logger.debug(
            "Agent config saved to YAML", agent_id=agent.id, file=str(yaml_file)
        )

    async def create_agent(
        self,
        agent_id: str,
        config: AgentConfig,
    ) -> Agent:
        """
        Create a new agent and persist to MongoDB and YAML.

        Args:
            agent_id: Unique agent ID
            config: Agent configuration

        Returns:
            Created agent

        Raises:
            ValueError: If agent ID already exists
        """
        collection = self._get_collection()

        # Check if exists
        existing = await collection.find_one({"id": agent_id})
        if existing:
            raise ValueError(f"Agent with ID '{agent_id}' already exists")

        now = datetime.now(timezone.utc).isoformat()
        agent = Agent(id=agent_id, config=config, created_at=now, updated_at=now)

        # Store in MongoDB
        await collection.insert_one(agent.model_dump())

        # Save to YAML
        await self._save_agent_to_yaml(agent)

        # Register in memory
        self.registry.register_agent(agent)

        logger.info("Agent created", agent_id=agent_id, name=config.name)
        return agent

    async def update_agent(
        self,
        agent_id: str,
        config: AgentConfig,
    ) -> Optional[Agent]:
        """
        Update an existing agent and persist to MongoDB and YAML.

        Args:
            agent_id: Agent ID
            config: Updated agent configuration

        Returns:
            Updated agent or None if not found
        """
        collection = self._get_collection()

        # Check if exists
        existing = await collection.find_one({"id": agent_id})
        if not existing:
            logger.warning("Agent not found for update", agent_id=agent_id)
            return None

        # Preserve created_at, update updated_at
        created_at = existing.get("created_at", datetime.now(timezone.utc).isoformat())
        now = datetime.now(timezone.utc).isoformat()
        agent = Agent(id=agent_id, config=config, created_at=created_at, updated_at=now)

        # Update in MongoDB
        await collection.replace_one({"id": agent_id}, agent.model_dump())

        # Save to YAML
        await self._save_agent_to_yaml(agent)

        # Update in memory
        self.registry.update_agent(agent)

        logger.info("Agent updated", agent_id=agent_id, name=config.name)
        return agent

    async def delete_agent(self, agent_id: str) -> bool:
        """
        Delete an agent from MongoDB, YAML, and memory.

        Args:
            agent_id: Agent ID

        Returns:
            True if deleted, False if not found
        """
        collection = self._get_collection()

        # Delete from MongoDB
        result = await collection.delete_one({"id": agent_id})

        if result.deleted_count == 0:
            return False

        # Remove YAML file
        yaml_file = self.config_dir / f"{agent_id}.yaml"
        if yaml_file.exists():
            yaml_file.unlink()
            logger.debug("Agent YAML file deleted", file=str(yaml_file))

        # Unregister from memory
        self.registry.unregister_agent(agent_id)

        logger.info("Agent deleted", agent_id=agent_id)
        return True

    async def get_agent(self, agent_id: str) -> Optional[Agent]:
        """
        Get an agent by ID from MongoDB.

        Args:
            agent_id: Agent ID

        Returns:
            Agent or None if not found
        """
        collection = self._get_collection()
        data = await collection.find_one({"id": agent_id})

        if data:
            data.pop("_id", None)
            return Agent(**data)
        return None

    async def list_agents(self, include_hidden: bool = False) -> List[Agent]:
        """
        List all agents from MongoDB.

        Args:
            include_hidden: Whether to include hidden/system agents

        Returns:
            List of agents
        """
        collection = self._get_collection()

        agents = []
        async for doc in collection.find({}):
            doc.pop("_id", None)
            agent = Agent(**doc)

            # Filter hidden agents
            if not include_hidden:
                is_hidden = agent.config.metadata and agent.config.metadata.get(
                    "is_hidden", False
                )
                if is_hidden:
                    continue

            agents.append(agent)

        return agents

    async def reload_agents(self):
        """
        Reload all agent configurations from YAML files.
        Useful for syncing changes made outside the application.
        """
        self.registry.clear()
        await self.initialize_from_yaml()
        logger.info("Agents reloaded from YAML", count=self.registry.count())

    async def export_agent(self, agent_id: str) -> Optional[Dict]:
        """
        Export agent configuration as a dictionary.

        Args:
            agent_id: Agent ID

        Returns:
            Agent config dict or None if not found
        """
        agent = await self.get_agent(agent_id)
        if not agent:
            return None

        return agent.config.model_dump(exclude_none=True)

    async def import_agent(self, agent_id: str, config_dict: Dict) -> Agent:
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
        return await self.create_agent(agent_id, config)
