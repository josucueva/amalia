"""
Agent registry for managing agent instances.
"""
from typing import Dict, List, Optional
import structlog
from app.models import Agent

logger = structlog.get_logger()


class AgentRegistry:
    """
    Registry for managing agent instances.
    Implements the Registry pattern for agent management.
    """
    
    def __init__(self):
        """Initialize the agent registry."""
        self._agents: Dict[str, Agent] = {}
        logger.info("Agent registry initialized")
    
    def register_agent(self, agent: Agent) -> None:
        """
        Register a new agent.
        
        Args:
            agent: Agent instance to register
        """
        self._agents[agent.id] = agent
        logger.info("Agent registered", agent_id=agent.id, name=agent.config.name)
    
    def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent.
        
        Args:
            agent_id: ID of the agent to unregister
            
        Returns:
            bool: True if agent was unregistered, False if not found
        """
        if agent_id in self._agents:
            agent_name = self._agents[agent_id].config.name
            del self._agents[agent_id]
            logger.info("Agent unregistered", agent_id=agent_id, name=agent_name)
            return True
        return False
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """
        Get an agent by ID.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Optional[Agent]: Agent instance or None if not found
        """
        return self._agents.get(agent_id)
    
    def get_agent_by_name(self, name: str) -> Optional[Agent]:
        """
        Get an agent by name.
        
        Args:
            name: Agent name
            
        Returns:
            Optional[Agent]: Agent instance or None if not found
        """
        for agent in self._agents.values():
            if agent.config.name == name:
                return agent
        return None
    
    def list_agents(self) -> List[Agent]:
        """
        List all registered agents.
        
        Returns:
            List[Agent]: List of all agents
        """
        return list(self._agents.values())
    
    def update_agent(self, agent: Agent) -> None:
        """
        Update an existing agent.
        
        Args:
            agent: Updated agent instance
        """
        if agent.id in self._agents:
            self._agents[agent.id] = agent
            logger.info("Agent updated", agent_id=agent.id, name=agent.config.name)
        else:
            logger.warning("Attempted to update non-existent agent", agent_id=agent.id)
    
    def clear(self) -> None:
        """Clear all agents from the registry."""
        count = len(self._agents)
        self._agents.clear()
        logger.info("Agent registry cleared", agents_removed=count)
    
    def get_agents_by_tool(self, tool_name: str) -> List[Agent]:
        """
        Get all agents that have access to a specific tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            List[Agent]: List of agents with the tool
        """
        return [
            agent for agent in self._agents.values()
            if tool_name in agent.config.tools
        ]
    
    def count(self) -> int:
        """
        Get the number of registered agents.
        
        Returns:
            int: Number of agents
        """
        return len(self._agents)
