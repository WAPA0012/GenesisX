"""
Genesis X Database Models

SQLAlchemy ORM models for persistent storage of sessions, memories, users, and system state.

Models are organized into:
- session_models: Session, state, episodes, and memories
- user_models: Users, preferences, quotas, and API keys
"""

from common.database import Base
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.sql import func
from datetime import datetime, timezone


class BaseModel(Base):
    """
    Abstract base model with common fields.

    All models inherit from this class to get:
    - Primary key (id)
    - Timestamps (created_at, updated_at)
    - Soft delete (deleted_at)
    """

    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        server_onupdate=func.now(),
    )
    deleted_at = Column(DateTime, nullable=True, index=True)

    def soft_delete(self):
        """Mark record as deleted without actually removing it."""
        self.deleted_at = datetime.now(timezone.utc)

    def is_deleted(self) -> bool:
        """Check if record is soft-deleted."""
        return self.deleted_at is not None

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }


# Import all models to make them available
from models.session_models import (
    GenesisSession,
    SessionState,
    Episode,
    Memory,
)

from models.user import (
    User,
    UserSession,
    UserPreferences,
    UserRole,
    UserStatus,
)

__all__ = [
    "Base",
    "BaseModel",
    "GenesisSession",
    "SessionState",
    "Episode",
    "Memory",
    "User",
    "UserSession",
    "UserPreferences",
    "UserRole",
    "UserStatus",
]
