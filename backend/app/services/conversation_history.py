"""
Conversation history management.
"""

from typing import Dict, List, Optional
from datetime import datetime
import structlog

logger = structlog.get_logger()


class ConversationHistory:
    """In-memory conversation history manager."""

    def __init__(self):
        """Initialize conversation history storage."""
        # Format: {conversation_id: [{"role": "user", "content": "..."}, ...]}
        self._conversations: Dict[str, List[Dict[str, str]]] = {}
        self._metadata: Dict[str, Dict] = {}

    def add_message(self, conversation_id: str, role: str, content: str):
        """
        Add a message to conversation history.

        Args:
            conversation_id: Conversation ID
            role: Message role (user/assistant/system)
            content: Message content
        """
        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = []
            self._metadata[conversation_id] = {
                "created_at": datetime.now().isoformat(),
                "message_count": 0,
            }

        self._conversations[conversation_id].append({"role": role, "content": content})

        self._metadata[conversation_id]["message_count"] = len(
            self._conversations[conversation_id]
        )
        self._metadata[conversation_id]["updated_at"] = datetime.now().isoformat()

        logger.debug(
            "Message added to conversation",
            conversation_id=conversation_id,
            role=role,
            total_messages=self._metadata[conversation_id]["message_count"],
        )

    def get_history(
        self, conversation_id: str, max_messages: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        Get conversation history.

        Args:
            conversation_id: Conversation ID
            max_messages: Maximum number of recent messages to return

        Returns:
            List of messages
        """
        if conversation_id not in self._conversations:
            return []

        messages = self._conversations[conversation_id]

        if max_messages and max_messages > 0:
            return messages[-max_messages:]

        return messages.copy()

    def clear_conversation(self, conversation_id: str):
        """
        Clear a conversation history.

        Args:
            conversation_id: Conversation ID
        """
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            del self._metadata[conversation_id]
            logger.info("Conversation cleared", conversation_id=conversation_id)

    def get_all_conversations(self) -> List[Dict]:
        """
        Get metadata for all conversations.

        Returns:
            List of conversation metadata
        """
        return [
            {"conversation_id": conv_id, **metadata}
            for conv_id, metadata in self._metadata.items()
        ]

    def conversation_exists(self, conversation_id: str) -> bool:
        """
        Check if conversation exists.

        Args:
            conversation_id: Conversation ID

        Returns:
            True if conversation exists
        """
        return conversation_id in self._conversations


# Global conversation history instance
conversation_history = ConversationHistory()
