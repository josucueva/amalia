"""
MongoDB database connection and utilities.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
import structlog

from app.config import get_settings

logger = structlog.get_logger()


class Database:
    """MongoDB database connection manager."""

    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None

    @classmethod
    async def connect(cls):
        """Connect to MongoDB."""
        settings = get_settings()

        try:
            cls.client = AsyncIOMotorClient(settings.mongodb_url)
            cls.db = cls.client[settings.mongodb_db_name]

            # Test connection
            await cls.client.admin.command("ping")
            logger.info("MongoDB connected", db=settings.mongodb_db_name)
        except Exception as e:
            logger.error("MongoDB connection failed", error=str(e))
            raise

    @classmethod
    async def disconnect(cls):
        """Disconnect from MongoDB."""
        if cls.client:
            cls.client.close()
            logger.info("MongoDB disconnected")

    @classmethod
    def get_database(cls) -> AsyncIOMotorDatabase:
        """Get database instance."""
        if cls.db is None:
            raise RuntimeError("Database not initialized. Call connect() first.")
        return cls.db

    @classmethod
    def get_collection(cls, name: str):
        """Get a collection by name."""
        return cls.get_database()[name]


# Convenience function
def get_db() -> AsyncIOMotorDatabase:
    """Get database instance."""
    return Database.get_database()
