"""
A2A Listener Manager for Autonomous Agent Communication.

Manages background listeners that subscribe to agent inbox channels
and trigger autonomous execution when messages arrive.
"""

import asyncio
from typing import Dict, Set
import structlog

from app.communication.agent_executor import AgentExecutor
from app.models.message import A2AMessage

logger = structlog.get_logger()


class A2AListenerManager:
    """
    Manages background listeners for autonomous A2A agents.
    
    Each autonomous agent gets a dedicated listener task that:
    - Subscribes to the agent's inbox channel
    - Receives incoming A2A messages
    - Triggers agent execution via AgentExecutor
    """
    
    def __init__(self, a2a_service, agent_executor: AgentExecutor):
        """
        Initialize listener manager.
        
        Args:
            a2a_service: A2A service for subscribing to channels
            agent_executor: Executor for running agents
        """
        self.a2a_service = a2a_service
        self.agent_executor = agent_executor
        
        # Track active listener tasks
        self._listener_tasks: Dict[str, asyncio.Task] = {}
        
        # Track which agents are in autonomous mode
        self._autonomous_agents: Set[str] = set()
    
    async def start_listeners(self, agent_registry) -> None:
        """
        Start listeners for all autonomous agents.
        
        Args:
            agent_registry: Registry containing agent configurations
        """
        agents = agent_registry.list_agents()
        
        for agent in agents:
            # Check if agent has A2A enabled and is in autonomous mode
            if not agent.config.a2a_enabled:
                continue
                
            # Get a2a_mode from config (default to "messaging" for backward compatibility)
            a2a_mode = getattr(agent.config, "a2a_mode", "messaging")
            
            if a2a_mode == "autonomous":
                await self.start_listener(agent.id)
                self._autonomous_agents.add(agent.id)
        
        logger.info(
            "A2A autonomous listeners started",
            autonomous_agents=len(self._autonomous_agents),
            agents=list(self._autonomous_agents)
        )
    
    async def start_listener(self, agent_id: str) -> None:
        """
        Start a listener for a specific agent.
        
        Args:
            agent_id: ID of the agent to listen for
        """
        if agent_id in self._listener_tasks:
            logger.warning(
                "Listener already running for agent",
                agent_id=agent_id
            )
            return
        
        # Create background task for listening
        task = asyncio.create_task(self._listen_loop(agent_id))
        self._listener_tasks[agent_id] = task
        
        logger.info(
            "🎧 A2A listener started",
            agent_id=agent_id,
            channel=f"agent:{agent_id}:inbox"
        )
    
    async def stop_listener(self, agent_id: str) -> None:
        """
        Stop a listener for a specific agent.
        
        Args:
            agent_id: ID of the agent
        """
        task = self._listener_tasks.pop(agent_id, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            self._autonomous_agents.discard(agent_id)
            
            logger.info(
                "🔇 A2A listener stopped",
                agent_id=agent_id
            )
    
    async def stop_all_listeners(self) -> None:
        """Stop all active listeners."""
        agent_ids = list(self._listener_tasks.keys())
        
        for agent_id in agent_ids:
            await self.stop_listener(agent_id)
        
        logger.info("All A2A listeners stopped")
    
    async def _listen_loop(self, agent_id: str) -> None:
        """
        Background loop that listens for messages and executes agent.
        
        Args:
            agent_id: ID of the agent to listen for
        """
        try:
            # Subscribe to agent's inbox channel
            async for message in self.a2a_service.subscribe(agent_id):
                if message is None:
                    continue
                
                logger.info(
                    "📬 A2A message received",
                    agent_id=agent_id,
                    from_agent=message.from_agent,
                    message_type=message.message_type,
                    correlation_id=message.correlation_id
                )
                
                # Execute agent in response to message
                # Run in background to not block other messages
                asyncio.create_task(
                    self._handle_message(agent_id, message)
                )
                
        except asyncio.CancelledError:
            logger.info(
                "Listener cancelled",
                agent_id=agent_id
            )
            raise
            
        except Exception as e:
            logger.error(
                "Listener error",
                agent_id=agent_id,
                error=str(e)
            )
    
    async def _handle_message(
        self,
        agent_id: str,
        message: A2AMessage
    ) -> None:
        """
        Handle an incoming message by executing the agent.
        
        Args:
            agent_id: ID of the agent
            message: Incoming A2A message
        """
        try:
            await self.agent_executor.execute_from_message(agent_id, message)
            
        except Exception as e:
            logger.error(
                "Message handling failed",
                agent_id=agent_id,
                correlation_id=message.correlation_id,
                error=str(e)
            )
    
    def is_autonomous(self, agent_id: str) -> bool:
        """
        Check if an agent is running in autonomous mode.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            True if agent is autonomous
        """
        return agent_id in self._autonomous_agents
    
    def get_autonomous_agents(self) -> list:
        """
        Get list of all autonomous agents.
        
        Returns:
            List of agent IDs in autonomous mode
        """
        return list(self._autonomous_agents)
