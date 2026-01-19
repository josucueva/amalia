"""
Agent-to-Agent (A2A) communication module.

This module provides asynchronous message passing between agents using Redis Pub/Sub,
following microservices best practices for distributed agent communication.
"""

from app.communication.message_queue import RedisMessageQueue
from app.communication.router import MessageRouter
from app.communication.a2a import A2AService

__all__ = [
    "RedisMessageQueue",
    "MessageRouter",
    "A2AService",
]
