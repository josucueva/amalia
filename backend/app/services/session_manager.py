"""
Session management service.
"""

from typing import Dict, List, Optional
import uuid
import json
from pathlib import Path
from datetime import datetime
import structlog
import pytz

from app.models.session import (
    Session,
    SessionMessage,
    PipelineSnapshot,
    SessionStatus,
)

logger = structlog.get_logger()
TIMEZONE = 'America/Guayaquil'
local_tz = pytz.timezone(TIMEZONE)


class SessionManager:
    """Manages user sessions with chat history and pipeline snapshots."""

    def __init__(self, storage_path: str = "data/sessions.json"):
        """
        Initialize session manager.

        Args:
            storage_path: Path to JSON file for session persistence
        """
        self.storage_path = Path(storage_path)
        self._sessions: Dict[str, Session] = {}
        self._load_sessions()

    def _load_sessions(self):
        """Load sessions from disk."""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                    self._sessions = {
                        sid: Session(**session_data)
                        for sid, session_data in data.items()
                    }
                logger.info(
                    "Sessions loaded", count=len(self._sessions), file=str(self.storage_path)
                )
            else:
                # Create directory if it doesn't exist
                self.storage_path.parent.mkdir(parents=True, exist_ok=True)
                self._save_sessions()
                logger.info("Session storage initialized", file=str(self.storage_path))
        except Exception as e:
            logger.error("Error loading sessions", error=str(e))
            self._sessions = {}

    def _save_sessions(self):
        """Persist sessions to disk."""
        try:
            with open(self.storage_path, "w") as f:
                data = {
                    sid: session.model_dump() for sid, session in self._sessions.items()
                }
                json.dump(data, f, indent=2)
            logger.debug("Sessions saved", count=len(self._sessions))
        except Exception as e:
            logger.error("Error saving sessions", error=str(e))

    def create_session(self, title: Optional[str] = None) -> Session:
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

        self._sessions[session_id] = session
        self._save_sessions()

        logger.info("Session created", session_id=session_id, title=session_title)
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get a session by ID.

        Args:
            session_id: Session ID

        Returns:
            Session or None if not found
        """
        return self._sessions.get(session_id)

    def list_sessions(
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
        sessions = list(self._sessions.values())

        # Filter by status if provided
        if status:
            sessions = [s for s in sessions if s.status == status]

        # Sort by updated_at descending
        sessions.sort(key=lambda s: s.updated_at, reverse=True)

        # Apply limit if provided
        if limit:
            sessions = sessions[:limit]

        return sessions

    def update_session(
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
        session = self._sessions.get(session_id)
        if not session:
            return None

        if title:
            session.title = title
        if status:
            session.status = status

        session.updated_at = datetime.now().isoformat()
        self._save_sessions()

        logger.info("Session updated", session_id=session_id)
        return session

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: Session ID

        Returns:
            True if deleted, False if not found
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            self._save_sessions()
            logger.info("Session deleted", session_id=session_id)
            return True
        return False

    def add_message(
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
        session = self._sessions.get(session_id)
        if not session:
            return False

        message = SessionMessage(role=role, content=content, metadata=metadata)
        session.messages.append(message)
        session.updated_at = datetime.now().isoformat()
        self._save_sessions()

        logger.debug(
            "Message added to session", session_id=session_id, role=role
        )
        return True

    def add_pipeline(
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
        session = self._sessions.get(session_id)
        if not session:
            return False

        pipeline = PipelineSnapshot(nodes=nodes, connections=connections)
        session.pipelines.append(pipeline)
        session.updated_at = datetime.now().isoformat()
        self._save_sessions()

        logger.info(
            "Pipeline added to session",
            session_id=session_id,
            nodes=len(nodes),
            connections=len(connections),
        )
        return True

    def get_session_history(self, session_id: str) -> List[Dict[str, str]]:
        """
        Get conversation history in LLM format.

        Args:
            session_id: Session ID

        Returns:
            List of messages in format [{"role": "...", "content": "..."}]
        """
        session = self._sessions.get(session_id)
        if not session:
            return []

        return [
            {"role": msg.role, "content": msg.content} for msg in session.messages
        ]

    def clear_session_messages(self, session_id: str) -> bool:
        """
        Clear all messages from a session.

        Args:
            session_id: Session ID

        Returns:
            True if cleared, False if session not found
        """
        session = self._sessions.get(session_id)
        if not session:
            return False

        session.messages = []
        session.updated_at = datetime.now().isoformat()
        self._save_sessions()

        logger.info("Session messages cleared", session_id=session_id)
        return True
