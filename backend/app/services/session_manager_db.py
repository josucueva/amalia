"""
MongoDB-based session management service.
"""

from typing import Dict, List, Optional
import uuid
from datetime import datetime
import structlog
import pytz

from app.models.session import (
    Session,
    SessionMessage,
    PipelineSnapshot,
    SessionStatus,
)
from app.database import get_db

logger = structlog.get_logger()
TIMEZONE = "America/Guayaquil"
local_tz = pytz.timezone(TIMEZONE)


class SessionManager:
    """Manages user sessions with chat history and pipeline snapshots using MongoDB."""

    def __init__(self):
        """Initialize session manager."""
        self.collection_name = "sessions"

    def _get_collection(self):
        """Get sessions collection."""
        return get_db()[self.collection_name]

    async def create_session(self, title: Optional[str] = None) -> Session:
        """
        Create a new session.

        Args:
            title: Optional session title

        Returns:
            Created session
        """
        now_local = datetime.now(local_tz)
        session_id = f"session_{uuid.uuid4().hex[:16]}"
        session_title = title or f"Session {now_local.strftime('%Y-%m-%d %H:%M')}"

        session = Session(
            id=session_id,
            title=session_title,
            status=SessionStatus.ACTIVE,
        )

        # Store in MongoDB
        collection = self._get_collection()
        await collection.insert_one(session.model_dump())

        logger.info("Session created", session_id=session_id, title=session_title)
        return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get a session by ID.

        Args:
            session_id: Session ID

        Returns:
            Session or None if not found
        """
        collection = self._get_collection()
        data = await collection.find_one({"id": session_id})

        if data:
            # Remove MongoDB's _id field
            data.pop("_id", None)
            return Session(**data)
        return None

    async def list_sessions(
        self, status: Optional[SessionStatus] = None, limit: Optional[int] = None
    ) -> List[Session]:
        """
        List all sessions.

        Args:
            status: Filter by status
            limit: Maximum number of sessions to return

        Returns:
            List of sessions sorted by updated_at (most recent first)
        """
        collection = self._get_collection()

        # Build query
        query = {}
        if status:
            query["status"] = status.value

        # Execute query with sorting
        cursor = collection.find(query).sort("updated_at", -1)

        if limit:
            cursor = cursor.limit(limit)

        sessions = []
        async for doc in cursor:
            doc.pop("_id", None)
            sessions.append(Session(**doc))

        return sessions

    async def update_session(
        self,
        session_id: str,
        title: Optional[str] = None,
        status: Optional[SessionStatus] = None,
    ) -> Optional[Session]:
        """
        Update a session.

        Args:
            session_id: Session ID
            title: New title
            status: New status

        Returns:
            Updated session or None if not found
        """
        collection = self._get_collection()

        # Build update document
        update_doc = {"updated_at": datetime.now().isoformat()}
        if title:
            update_doc["title"] = title
        if status:
            update_doc["status"] = status.value

        # Update in MongoDB
        result = await collection.update_one({"id": session_id}, {"$set": update_doc})

        if result.matched_count == 0:
            return None

        logger.info("Session updated", session_id=session_id)
        return await self.get_session(session_id)

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: Session ID

        Returns:
            True if deleted, False if not found
        """
        collection = self._get_collection()
        result = await collection.delete_one({"id": session_id})

        if result.deleted_count > 0:
            logger.info("Session deleted", session_id=session_id)
            return True
        return False

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """
        Add a message to a session.

        Args:
            session_id: Session ID
            role: Message role
            content: Message content
            metadata: Optional metadata

        Returns:
            True if added, False if session not found
        """
        collection = self._get_collection()

        message = SessionMessage(role=role, content=content, metadata=metadata)

        result = await collection.update_one(
            {"id": session_id},
            {
                "$push": {"messages": message.model_dump()},
                "$set": {"updated_at": datetime.now().isoformat()},
            },
        )

        if result.matched_count > 0:
            logger.debug("Message added to session", session_id=session_id, role=role)
            return True
        return False

    async def add_pipeline(
        self, session_id: str, nodes: List[Dict], connections: List[Dict]
    ) -> bool:
        """
        Add a pipeline snapshot to a session.

        Args:
            session_id: Session ID
            nodes: Pipeline nodes
            connections: Pipeline connections

        Returns:
            True if added, False if session not found
        """
        collection = self._get_collection()

        pipeline = PipelineSnapshot(nodes=nodes, connections=connections)

        result = await collection.update_one(
            {"id": session_id},
            {
                "$push": {"pipelines": pipeline.model_dump()},
                "$set": {"updated_at": datetime.now().isoformat()},
            },
        )

        if result.matched_count > 0:
            logger.info(
                "Pipeline added to session",
                session_id=session_id,
                nodes=len(nodes),
                connections=len(connections),
            )
            return True
        return False

    async def get_session_history(self, session_id: str) -> List[Dict[str, str]]:
        """
        Get conversation history in LLM format.

        Args:
            session_id: Session ID

        Returns:
            List of messages in format [{"role": "...", "content": "..."}]
        """
        session = await self.get_session(session_id)
        if not session:
            return []

        return [{"role": msg.role, "content": msg.content} for msg in session.messages]

    async def clear_session_messages(self, session_id: str) -> bool:
        """
        Clear all messages from a session.

        Args:
            session_id: Session ID

        Returns:
            True if cleared, False if session not found
        """
        collection = self._get_collection()

        result = await collection.update_one(
            {"id": session_id},
            {"$set": {"messages": [], "updated_at": datetime.now().isoformat()}},
        )

        if result.matched_count > 0:
            logger.info("Session messages cleared", session_id=session_id)
            return True
        return False
