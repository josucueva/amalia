"""
YAML configuration loader for agents.
"""

import os
from pathlib import Path
from typing import List, Optional
import yaml
import structlog
from datetime import datetime
import uuid

from app.models import Agent, AgentConfig, AgentStatus, CommunicationConfig
from app.config import get_settings

logger = structlog.get_logger()


def load_agent_config_from_file(file_path: Path) -> Agent:
    """
    Load agent configuration from a YAML file.

    Args:
        file_path: Path to the YAML configuration file

    Returns:
        Agent: Agent instance created from the configuration

    Raises:
        ValueError: If the configuration is invalid
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data or "agent" not in data:
            raise ValueError(f"Invalid agent configuration in {file_path}")

        agent_data = data["agent"]

        # Parse communication config
        comm_data = agent_data.get("communication", {})
        communication = CommunicationConfig(
            can_receive_from=comm_data.get("can_receive_from", ["*"]),
            can_send_to=comm_data.get("can_send_to", []),
        )

        # Create agent config
        config = AgentConfig(
            name=agent_data["name"],
            description=agent_data["description"],
            model=agent_data.get("model", "gpt-4o"),
            system_prompt=agent_data["system_prompt"],
            icon=agent_data.get("icon"),
            a2a_enabled=agent_data.get("a2a_enabled", False),
            tools=agent_data.get("tools", []),
            communication=communication,
            temperature=agent_data.get("temperature", 0.7),
            max_tokens=agent_data.get("max_tokens", 2000),
            metadata=agent_data.get("metadata"),
        )

        # Create agent instance
        agent = Agent(
            id=f"agent_{uuid.uuid4().hex[:12]}",
            config=config,
            status=AgentStatus.ACTIVE,
            created_at=datetime.now().isoformat(),
        )

        logger.info(
            "Agent loaded from YAML", file=str(file_path), agent_name=config.name
        )
        return agent

    except Exception as e:
        logger.error("Error loading agent from YAML", file=str(file_path), error=str(e))
        raise


def load_agent_configs_from_yaml() -> List[Agent]:
    """
    Load all agent configurations from YAML files in the config directory.

    Returns:
        List[Agent]: List of agent instances
    """
    settings = get_settings()
    config_dir = Path(settings.agent_config_dir)

    if not config_dir.exists():
        logger.warning("Agent config directory does not exist", path=str(config_dir))
        os.makedirs(config_dir, exist_ok=True)
        return []

    agents = []
    yaml_files = list(config_dir.glob("*.yaml")) + list(config_dir.glob("*.yml"))

    for yaml_file in yaml_files:
        try:
            agent = load_agent_config_from_file(yaml_file)
            agents.append(agent)
        except Exception as e:
            logger.error(
                "Failed to load agent configuration", file=str(yaml_file), error=str(e)
            )

    logger.info("Loaded agents from YAML", count=len(agents))
    return agents


def load_agents_from_directory(directory: str) -> List[Agent]:
    """
    Load all agent configurations from YAML files in a specific directory.

    Args:
        directory: Path to the directory containing YAML files

    Returns:
        List[Agent]: List of agent instances
    """
    config_dir = Path(directory)

    if not config_dir.exists():
        logger.warning("Agent config directory does not exist", path=str(config_dir))
        os.makedirs(config_dir, exist_ok=True)
        return []

    agents = []
    yaml_files = list(config_dir.glob("*.yaml")) + list(config_dir.glob("*.yml"))

    for yaml_file in yaml_files:
        try:
            agent = load_agent_config_from_file(yaml_file)
            agents.append(agent)
        except Exception as e:
            logger.error(
                "Failed to load agent configuration", file=str(yaml_file), error=str(e)
            )

    logger.info("Loaded agents from directory", directory=directory, count=len(agents))
    return agents


def save_agent_config_to_yaml(agent: Agent, directory: Optional[Path] = None) -> Path:
    """
    Save agent configuration to a YAML file.

    Args:
        agent: Agent instance to save
        directory: Directory to save the file (defaults to agent_config_dir)

    Returns:
        Path: Path to the saved file
    """
    if directory is None:
        settings = get_settings()
        directory = Path(settings.agent_config_dir)

    os.makedirs(directory, exist_ok=True)

    # Create YAML structure
    data = {
        "agent": {
            "name": agent.config.name,
            "description": agent.config.description,
            "model": agent.config.model,
            "system_prompt": agent.config.system_prompt,
            "a2a_enabled": agent.config.a2a_enabled,
            "tools": agent.config.tools,
            "communication": {
                "can_receive_from": agent.config.communication.can_receive_from,
                "can_send_to": agent.config.communication.can_send_to,
            },
            "temperature": agent.config.temperature,
            "max_tokens": agent.config.max_tokens,
        }
    }

    # Add icon if present
    if agent.config.icon:
        data["agent"]["icon"] = agent.config.icon

    if agent.config.metadata:
        data["agent"]["metadata"] = agent.config.metadata

    # Save to file
    file_path = directory / f"{agent.config.name}.yaml"

    with open(file_path, "w", encoding="utf-8") as f:
        yaml.dump(
            data, f, default_flow_style=False, sort_keys=False, allow_unicode=True
        )

    logger.info(
        "Agent config saved to YAML", file=str(file_path), agent_name=agent.config.name
    )
    return file_path
