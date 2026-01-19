"""
Message router for agent-to-agent communication.

Validates permissions and routes messages based on agent communication configuration.
Implements authorization using can_send_to and can_receive_from rules.
"""

from typing import List, Optional
import structlog

from app.models.message import A2AMessage
from app.models.agent import Agent
from app.agents.registry import AgentRegistry

logger = structlog.get_logger()


class MessageRoutingError(Exception):
    """Exception raised when message routing fails."""
    pass


class MessageRouter:
    """
    Routes messages between agents with permission validation.
    
    Enforces communication rules defined in agent configurations:
    - can_send_to: List of agent IDs this agent can send messages to
    - can_receive_from: List of agent IDs or "*" for all
    
    Supports multiple routing patterns:
    - Point-to-point: Single sender to single receiver
    - Broadcast: One sender to multiple receivers
    - Wildcard: Agents that accept from "*" receive all messages
    """
    
    def __init__(self, agent_registry: AgentRegistry):
        """
        Initialize message router.
        
        Args:
            agent_registry: Registry to look up agent configurations
        """
        self.agent_registry = agent_registry
        
    def validate_send_permission(
        self,
        from_agent: Agent,
        to_agent_id: str,
    ) -> bool:
        """
        Check if sender is allowed to send to target agent.
        
        Args:
            from_agent: Sending agent
            to_agent_id: Target agent ID
            
        Returns:
            True if allowed, False otherwise
        """
        can_send_to = from_agent.config.communication.can_send_to
        
        # Empty list means can't send to anyone via A2A
        if not can_send_to:
            logger.warning(
                "Agent not configured to send A2A messages",
                agent_id=from_agent.id,
                agent_name=from_agent.config.name,
            )
            return False
        
        # "*" means can send to anyone
        if "*" in can_send_to:
            return True
            
        # Check if target is in allowed list
        # Support both agent ID and agent name
        to_agent = self.agent_registry.get_agent(to_agent_id)
        if not to_agent:
            return to_agent_id in can_send_to
            
        return (to_agent_id in can_send_to or 
                to_agent.config.name in can_send_to)
    
    def validate_receive_permission(
        self,
        to_agent: Agent,
        from_agent_id: str,
    ) -> bool:
        """
        Check if receiver accepts messages from sender.
        
        Args:
            to_agent: Receiving agent
            from_agent_id: Sender agent ID
            
        Returns:
            True if allowed, False otherwise
        """
        can_receive_from = to_agent.config.communication.can_receive_from
        
        # "*" means accepts from anyone
        if "*" in can_receive_from:
            return True
            
        # Check if sender is in allowed list
        from_agent = self.agent_registry.get_agent(from_agent_id)
        if not from_agent:
            return from_agent_id in can_receive_from
            
        return (from_agent_id in can_receive_from or 
                from_agent.config.name in can_receive_from)
    
    def validate_routing(
        self,
        message: A2AMessage,
    ) -> tuple[bool, Optional[str]]:
        """
        Validate that message routing is allowed by both parties.
        
        Args:
            message: A2A message to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Get sender agent
        from_agent = self.agent_registry.get_agent(message.from_agent)
        if not from_agent:
            error = f"Sender agent '{message.from_agent}' not found"
            logger.error("Routing validation failed", error=error)
            return False, error
            
        # Check if sender has A2A enabled
        if not from_agent.config.a2a_enabled:
            error = f"Agent '{from_agent.config.name}' does not have A2A enabled"
            logger.warning("A2A not enabled for sender", agent=from_agent.config.name)
            return False, error
            
        # Get receiver agent
        to_agent = self.agent_registry.get_agent(message.to_agent)
        if not to_agent:
            error = f"Receiver agent '{message.to_agent}' not found"
            logger.error("Routing validation failed", error=error)
            return False, error
            
        # Check if receiver has A2A enabled
        if not to_agent.config.a2a_enabled:
            error = f"Agent '{to_agent.config.name}' does not have A2A enabled"
            logger.warning("A2A not enabled for receiver", agent=to_agent.config.name)
            return False, error
            
        # Validate sender permission
        if not self.validate_send_permission(from_agent, message.to_agent):
            error = (
                f"Agent '{from_agent.config.name}' is not allowed to send to "
                f"'{to_agent.config.name}'. Check can_send_to configuration."
            )
            logger.warning(
                "Send permission denied",
                from_agent=from_agent.config.name,
                to_agent=to_agent.config.name,
                can_send_to=from_agent.config.communication.can_send_to,
            )
            return False, error
            
        # Validate receiver permission
        if not self.validate_receive_permission(to_agent, message.from_agent):
            error = (
                f"Agent '{to_agent.config.name}' does not accept messages from "
                f"'{from_agent.config.name}'. Check can_receive_from configuration."
            )
            logger.warning(
                "Receive permission denied",
                from_agent=from_agent.config.name,
                to_agent=to_agent.config.name,
                can_receive_from=to_agent.config.communication.can_receive_from,
            )
            return False, error
            
        logger.info(
            "Message routing validated",
            from_agent=from_agent.config.name,
            to_agent=to_agent.config.name,
            message_type=message.message_type,
        )
        
        return True, None
    
    def get_broadcast_targets(
        self,
        from_agent_id: str,
    ) -> List[Agent]:
        """
        Get list of agents that can receive broadcast messages from sender.
        
        Args:
            from_agent_id: Sender agent ID
            
        Returns:
            List of agents that accept messages from sender
        """
        targets = []
        
        for agent in self.agent_registry.list_agents():
            # Skip sender
            if agent.id == from_agent_id:
                continue
                
            # Skip if A2A not enabled
            if not agent.config.a2a_enabled:
                continue
                
            # Check if agent accepts from sender
            if self.validate_receive_permission(agent, from_agent_id):
                targets.append(agent)
                
        logger.info(
            "Broadcast targets identified",
            from_agent=from_agent_id,
            target_count=len(targets),
            targets=[a.config.name for a in targets],
        )
        
        return targets
    
    def resolve_agent_targets(
        self,
        from_agent: Agent,
        target_ids: List[str],
    ) -> List[Agent]:
        """
        Resolve a list of target agent IDs/names to Agent objects.
        
        Filters out invalid targets and validates permissions.
        
        Args:
            from_agent: Sending agent
            target_ids: List of target agent IDs or names
            
        Returns:
            List of valid target agents
        """
        targets = []
        
        for target_id in target_ids:
            # Handle broadcast
            if target_id == "*":
                return self.get_broadcast_targets(from_agent.id)
                
            # Try to get agent by ID first, then by name
            target = self.agent_registry.get_agent(target_id)
            if not target:
                # Try finding by name
                all_agents = self.agent_registry.list_agents()
                target = next(
                    (a for a in all_agents if a.config.name == target_id),
                    None
                )
                
            if not target:
                logger.warning(
                    "Target agent not found",
                    target_id=target_id,
                    from_agent=from_agent.config.name,
                )
                continue
                
            # Validate permissions
            if not self.validate_send_permission(from_agent, target.id):
                logger.warning(
                    "Send permission denied for target",
                    from_agent=from_agent.config.name,
                    target=target.config.name,
                )
                continue
                
            if not self.validate_receive_permission(target, from_agent.id):
                logger.warning(
                    "Receive permission denied for target",
                    from_agent=from_agent.config.name,
                    target=target.config.name,
                )
                continue
                
            targets.append(target)
            
        return targets
