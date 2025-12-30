"""
Agent-to-Agent (A2A) communication service.

High-level service that combines message queue and routing for agent communication.
Provides simple API for sending/receiving messages with automatic permission validation.
"""

import asyncio
import uuid
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timezone
import structlog

from app.communication.message_queue import RedisMessageQueue
from app.communication.router import MessageRouter, MessageRoutingError
from app.models.message import A2AMessage
from app.agents.registry import AgentRegistry
from app.database import Database

logger = structlog.get_logger()


class A2ATimeoutError(Exception):
    """Exception raised when waiting for reply times out."""
    pass


class A2AService:
    """
    High-level Agent-to-Agent communication service.
    
    Provides async messaging capabilities with:
    - Automatic permission validation
    - Request/reply pattern with correlation IDs
    - Message persistence to MongoDB
    - Dead letter queue for failures
    - Broadcast support
    
    Usage:
        service = A2AService(agent_registry)
        await service.connect()
        
        # Send message
        await service.send_message(
            from_agent="agent_123",
            to_agent="agent_456",
            content={"result": "data processed"},
        )
        
        # Wait for reply
        reply = await service.wait_for_reply(correlation_id, timeout=30)
    """
    
    def __init__(self, agent_registry: AgentRegistry):
        """
        Initialize A2A service.
        
        Args:
            agent_registry: Registry for agent lookups
        """
        self.agent_registry = agent_registry
        self.message_queue = RedisMessageQueue()
        self.router = MessageRouter(agent_registry)
        
        # Track pending replies with correlation IDs
        self._pending_replies: Dict[str, asyncio.Future] = {}
        
        # Database for message persistence
        self._db = None
        
    async def connect(self) -> None:
        """Initialize connection to Redis and MongoDB."""
        await self.message_queue.connect()
        self._db = Database.get_database()
        logger.info("A2A service connected")
        
    async def disconnect(self) -> None:
        """Close connections and cleanup."""
        await self.message_queue.disconnect()
        
        # Cancel all pending reply futures
        for future in self._pending_replies.values():
            if not future.done():
                future.cancel()
        self._pending_replies.clear()
        
        logger.info("A2A service disconnected")
        
    async def send_message(
        self,
        from_agent: str,
        to_agent: str,
        content: Dict[str, Any],
        message_type: str = "task",
        correlation_id: Optional[str] = None,
        validate: bool = True,
    ) -> str:
        """
        Send a message from one agent to another.
        
        Args:
            from_agent: Sender agent ID
            to_agent: Target agent ID
            content: Message payload
            message_type: Type of message (task, reply, broadcast, etc.)
            correlation_id: For reply tracking (auto-generated if None)
            validate: Whether to validate routing permissions
            
        Returns:
            Correlation ID of the sent message
            
        Raises:
            MessageRoutingError: If routing validation fails
        """
        # Generate correlation ID if not provided
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())
            
        # Create A2A message
        message = A2AMessage(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            content=content,
            timestamp=datetime.now(timezone.utc),
            correlation_id=correlation_id,
        )
        
        # Validate routing if requested
        if validate:
            is_valid, error = self.router.validate_routing(message)
            if not is_valid:
                logger.error(
                    "Message routing validation failed",
                    from_agent=from_agent,
                    to_agent=to_agent,
                    error=error,
                )
                raise MessageRoutingError(error)
                
        # Publish to Redis
        try:
            success = await self.message_queue.publish_to_agent(to_agent, message)
            
            if not success:
                logger.warning(
                    "No subscribers for message",
                    to_agent=to_agent,
                    correlation_id=correlation_id,
                )
                
            # Persist to MongoDB for history/debugging
            await self._persist_message(message)
            
            logger.info(
                "A2A message sent",
                from_agent=from_agent,
                to_agent=to_agent,
                message_type=message_type,
                correlation_id=correlation_id,
            )
            
            return correlation_id
            
        except Exception as e:
            logger.error(
                "Failed to send A2A message",
                from_agent=from_agent,
                to_agent=to_agent,
                error=str(e),
            )
            # Push to dead letter queue
            await self.message_queue.push_to_dead_letter_queue(
                message,
                error=str(e),
            )
            raise
            
    async def send_broadcast(
        self,
        from_agent: str,
        content: Dict[str, Any],
        message_type: str = "broadcast",
    ) -> str:
        """
        Broadcast a message to all agents that accept from sender.
        
        Args:
            from_agent: Sender agent ID
            content: Message payload
            message_type: Type of broadcast message
            
        Returns:
            Correlation ID of the broadcast
        """
        correlation_id = str(uuid.uuid4())
        
        message = A2AMessage(
            from_agent=from_agent,
            to_agent="*",  # Broadcast indicator
            message_type=message_type,
            content=content,
            timestamp=datetime.now(timezone.utc),
            correlation_id=correlation_id,
        )
        
        # Publish to broadcast channel
        await self.message_queue.publish_broadcast(message)
        await self._persist_message(message)
        
        logger.info(
            "Broadcast message sent",
            from_agent=from_agent,
            correlation_id=correlation_id,
        )
        
        return correlation_id
        
    async def subscribe_agent(
        self,
        agent_id: str,
        callback: Callable[[A2AMessage], Any],
    ) -> None:
        """
        Subscribe an agent to receive messages.
        
        Args:
            agent_id: Agent ID to subscribe
            callback: Async function to call when message arrives
        """
        # Wrap callback to handle replies
        async def wrapped_callback(message: A2AMessage):
            # Check if this is a reply to a pending request
            if message.correlation_id in self._pending_replies:
                future = self._pending_replies.pop(message.correlation_id)
                if not future.done():
                    future.set_result(message)
            
            # Always call the user callback
            await callback(message)
            
        await self.message_queue.subscribe(
            agent_id,
            wrapped_callback,
            include_broadcast=True,
        )
        
    async def unsubscribe_agent(self, agent_id: str) -> None:
        """
        Unsubscribe an agent from receiving messages.
        
        Args:
            agent_id: Agent ID to unsubscribe
        """
        await self.message_queue.unsubscribe(agent_id)
        
    async def wait_for_reply(
        self,
        correlation_id: str,
        timeout: float = 30.0,
    ) -> A2AMessage:
        """
        Wait for a reply message with matching correlation ID.
        
        Used for request/reply pattern where sender expects response.
        
        Args:
            correlation_id: Correlation ID to wait for
            timeout: Maximum seconds to wait
            
        Returns:
            The reply message
            
        Raises:
            A2ATimeoutError: If timeout expires before reply
            asyncio.CancelledError: If wait is cancelled
        """
        # Create future for this correlation ID
        future = asyncio.Future()
        self._pending_replies[correlation_id] = future
        
        try:
            # Wait with timeout
            reply = await asyncio.wait_for(future, timeout=timeout)
            logger.info(
                "Reply received",
                correlation_id=correlation_id,
            )
            return reply
            
        except asyncio.TimeoutError:
            # Cleanup pending future
            if correlation_id in self._pending_replies:
                self._pending_replies.pop(correlation_id)
                
            error = f"Timeout waiting for reply (correlation_id={correlation_id})"
            logger.warning(error)
            raise A2ATimeoutError(error)
            
    async def send_and_wait_reply(
        self,
        from_agent: str,
        to_agent: str,
        content: Dict[str, Any],
        timeout: float = 30.0,
    ) -> A2AMessage:
        """
        Send a message and wait for reply (request/reply pattern).
        
        Args:
            from_agent: Sender agent ID
            to_agent: Target agent ID
            content: Message payload
            timeout: Maximum seconds to wait for reply
            
        Returns:
            The reply message
            
        Raises:
            A2ATimeoutError: If no reply within timeout
        """
        correlation_id = await self.send_message(
            from_agent=from_agent,
            to_agent=to_agent,
            content=content,
            message_type="request",
        )
        
        return await self.wait_for_reply(correlation_id, timeout=timeout)
        
    async def reply_to_message(
        self,
        original_message: A2AMessage,
        from_agent: str,
        content: Dict[str, Any],
    ) -> str:
        """
        Send a reply to a received message.
        
        Args:
            original_message: The message being replied to
            from_agent: Agent sending the reply
            content: Reply payload
            
        Returns:
            Correlation ID
        """
        return await self.send_message(
            from_agent=from_agent,
            to_agent=original_message.from_agent,
            content=content,
            message_type="reply",
            correlation_id=original_message.correlation_id,
        )
        
    async def _persist_message(self, message: A2AMessage) -> None:
        """
        Save message to MongoDB for history and debugging.
        
        Args:
            message: Message to persist
        """
        if self._db is None:
            return
            
        try:
            await self._db.a2a_messages.insert_one({
                "from_agent": message.from_agent,
                "to_agent": message.to_agent,
                "message_type": message.message_type,
                "content": message.content,
                "timestamp": message.timestamp,
                "correlation_id": message.correlation_id,
            })
        except Exception as e:
            # Don't fail message sending if persistence fails
            logger.error("Failed to persist A2A message", error=str(e))
            
    async def get_message_history(
        self,
        agent_id: str,
        limit: int = 50,
    ) -> list:
        """
        Retrieve message history for an agent.
        
        Args:
            agent_id: Agent ID
            limit: Maximum messages to return
            
        Returns:
            List of messages (newest first)
        """
        if self._db is None:
            return []
            
        cursor = self._db.a2a_messages.find(
            {"$or": [
                {"from_agent": agent_id},
                {"to_agent": agent_id},
            ]}
        ).sort("timestamp", -1).limit(limit)
        
        return await cursor.to_list(length=limit)
        
    @property
    def is_connected(self) -> bool:
        """Check if service is connected and ready."""
        return self.message_queue.is_connected
