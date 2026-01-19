"""
Redis-based message queue for agent communication.

Implements async pub/sub pattern using aioredis for low-latency message delivery.
Follows best practices from FastAPI + Redis integration patterns.
"""

import asyncio
import json
from typing import Optional, Callable, Dict, Any
from datetime import datetime, timezone
import structlog
from redis.asyncio import Redis, ConnectionPool
from redis.exceptions import RedisError

from app.config import get_settings
from app.models.message import A2AMessage

logger = structlog.get_logger()


class RedisMessageQueue:
    """
    Async Redis message queue for agent-to-agent communication.
    
    Uses pub/sub pattern where each agent subscribes to its own inbox channel.
    Supports point-to-point, broadcast, and multi-target messaging patterns.
    """
    
    def __init__(self):
        """Initialize Redis message queue with connection pooling."""
        self._redis_client: Optional[Redis] = None
        self._pubsub = None
        self._listeners: Dict[str, asyncio.Task] = {}
        self._is_connected = False
        settings = get_settings()
        
        # Create connection pool for efficiency
        self._pool = ConnectionPool.from_url(
            settings.redis_url,
            max_connections=20,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
        )
        
    async def connect(self) -> None:
        """
        Establish connection to Redis server.
        
        Raises:
            RedisError: If connection fails
        """
        try:
            self._redis_client = Redis(connection_pool=self._pool)
            # Test connection
            await self._redis_client.ping()
            self._is_connected = True
            logger.info("Redis message queue connected successfully")
        except RedisError as e:
            logger.error("Failed to connect to Redis", error=str(e))
            raise
            
    async def disconnect(self) -> None:
        """Close Redis connection and cleanup resources."""
        try:
            # Stop all listeners
            for task in self._listeners.values():
                task.cancel()
                
            if self._pubsub:
                await self._pubsub.close()
                
            if self._redis_client:
                await self._redis_client.close()
                
            await self._pool.disconnect()
            self._is_connected = False
            logger.info("Redis message queue disconnected")
        except Exception as e:
            logger.error("Error during Redis disconnect", error=str(e))
            
    def _get_agent_channel(self, agent_id: str) -> str:
        """
        Get Redis channel name for an agent's inbox.
        
        Args:
            agent_id: The agent identifier
            
        Returns:
            Channel name in format 'agent:{agent_id}:inbox'
        """
        return f"agent:{agent_id}:inbox"
    
    def _get_broadcast_channel(self) -> str:
        """
        Get Redis broadcast channel name for system-wide messages.
        
        Returns:
            Broadcast channel name
        """
        return "agent:broadcast"
    
    async def publish(
        self, 
        channel: str, 
        message: A2AMessage
    ) -> bool:
        """
        Publish a message to a Redis channel.
        
        Args:
            channel: Target channel name
            message: A2A message to publish
            
        Returns:
            True if published successfully, False otherwise
            
        Raises:
            RedisError: If publish operation fails
        """
        if not self._is_connected or not self._redis_client:
            raise RedisError("Redis client not connected")
            
        try:
            # Serialize message with metadata envelope
            envelope = {
                "from_agent": message.from_agent,
                "to_agent": message.to_agent,
                "message_type": message.message_type,
                "content": message.content,
                "timestamp": message.timestamp.isoformat(),
                "correlation_id": message.correlation_id,
            }
            
            message_json = json.dumps(envelope)
            
            # Publish to channel (returns number of subscribers who received it)
            subscriber_count = await self._redis_client.publish(channel, message_json)
            
            logger.info(
                "Message published to Redis",
                channel=channel,
                from_agent=message.from_agent,
                to_agent=message.to_agent,
                subscribers=subscriber_count,
            )
            
            return subscriber_count > 0
            
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(
                "Failed to publish message",
                channel=channel,
                error=str(e),
            )
            raise
            
    async def publish_to_agent(
        self, 
        agent_id: str, 
        message: A2AMessage
    ) -> bool:
        """
        Publish a message to a specific agent's inbox.
        
        Args:
            agent_id: Target agent identifier
            message: A2A message to send
            
        Returns:
            True if delivered successfully
        """
        channel = self._get_agent_channel(agent_id)
        return await self.publish(channel, message)
    
    async def publish_broadcast(self, message: A2AMessage) -> bool:
        """
        Broadcast a message to all agents.
        
        Args:
            message: A2A message to broadcast
            
        Returns:
            True if broadcast successfully
        """
        channel = self._get_broadcast_channel()
        return await self.publish(channel, message)
    
    async def subscribe(
        self,
        agent_id: str,
        callback: Callable[[A2AMessage], Any],
        include_broadcast: bool = True,
    ) -> None:
        """
        Subscribe an agent to receive messages from its inbox.
        
        Creates a background task that listens for messages and invokes
        the callback function when messages arrive.
        
        Args:
            agent_id: The agent identifier to subscribe
            callback: Async function to call when message received
            include_broadcast: Whether to also listen to broadcast channel
        """
        if not self._is_connected or not self._redis_client:
            raise RedisError("Redis client not connected")
            
        # Create new pubsub instance for this subscription
        pubsub = self._redis_client.pubsub()
        
        # Subscribe to agent's inbox
        agent_channel = self._get_agent_channel(agent_id)
        await pubsub.subscribe(agent_channel)
        
        # Optionally subscribe to broadcast channel
        if include_broadcast:
            broadcast_channel = self._get_broadcast_channel()
            await pubsub.subscribe(broadcast_channel)
            
        logger.info(
            "Agent subscribed to message queue",
            agent_id=agent_id,
            channels=[agent_channel] + ([broadcast_channel] if include_broadcast else []),
        )
        
        # Start listener task
        task = asyncio.create_task(
            self._listen_loop(agent_id, pubsub, callback)
        )
        self._listeners[agent_id] = task
        
    async def _listen_loop(
        self,
        agent_id: str,
        pubsub,
        callback: Callable[[A2AMessage], Any],
    ) -> None:
        """
        Background task that listens for messages and invokes callback.
        
        Args:
            agent_id: Agent identifier
            pubsub: Redis pubsub instance
            callback: Function to call with received messages
        """
        try:
            async for message in pubsub.listen():
                # Skip subscription confirmation messages
                if message["type"] not in ("message", "pmessage"):
                    continue
                    
                try:
                    # Deserialize message
                    data = json.loads(message["data"])
                    
                    # Reconstruct A2AMessage
                    a2a_message = A2AMessage(
                        from_agent=data["from_agent"],
                        to_agent=data["to_agent"],
                        message_type=data["message_type"],
                        content=data["content"],
                        timestamp=datetime.fromisoformat(data["timestamp"]),
                        correlation_id=data.get("correlation_id"),
                    )
                    
                    logger.info(
                        "Message received",
                        agent_id=agent_id,
                        from_agent=a2a_message.from_agent,
                        message_type=a2a_message.message_type,
                    )
                    
                    # Invoke callback
                    if asyncio.iscoroutinefunction(callback):
                        await callback(a2a_message)
                    else:
                        callback(a2a_message)
                        
                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(
                        "Failed to parse message",
                        agent_id=agent_id,
                        error=str(e),
                        raw_data=message.get("data", ""),
                    )
                    # Continue listening despite parse errors
                    continue
                    
        except asyncio.CancelledError:
            logger.info("Listener cancelled", agent_id=agent_id)
            await pubsub.unsubscribe()
            await pubsub.close()
            raise
        except Exception as e:
            logger.error(
                "Listener error",
                agent_id=agent_id,
                error=str(e),
            )
            raise
            
    async def unsubscribe(self, agent_id: str) -> None:
        """
        Unsubscribe an agent from its inbox.
        
        Args:
            agent_id: Agent identifier to unsubscribe
        """
        if agent_id in self._listeners:
            task = self._listeners.pop(agent_id)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass  # Expected when cancelling task
            logger.info("Agent unsubscribed", agent_id=agent_id)
            
    async def push_to_dead_letter_queue(
        self,
        message: A2AMessage,
        error: str,
    ) -> None:
        """
        Push a failed message to dead letter queue for debugging.
        
        Args:
            message: The failed message
            error: Error description
        """
        if not self._redis_client:
            return
            
        try:
            dlq_entry = {
                "message": {
                    "from_agent": message.from_agent,
                    "to_agent": message.to_agent,
                    "message_type": message.message_type,
                    "content": message.content,
                    "correlation_id": message.correlation_id,
                },
                "error": error,
                "failed_at": datetime.now(timezone.utc).isoformat(),
            }
            
            await self._redis_client.lpush(
                "agent:dead_letter_queue",
                json.dumps(dlq_entry),
            )
            
            logger.warning(
                "Message pushed to DLQ",
                from_agent=message.from_agent,
                to_agent=message.to_agent,
                error=error,
            )
        except Exception as e:
            logger.error("Failed to push to DLQ", error=str(e))
            
    @property
    def is_connected(self) -> bool:
        """Check if Redis connection is active."""
        return self._is_connected
