"""User models for Genesis X authentication and multi-tenant support.

Implements SQLAlchemy models for:
- User accounts with secure authentication
- User sessions for JWT management
- User preferences for customization
- Multi-tenant isolation (each user has their own Genesis X instances)
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from enum import Enum
import re
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    Float, ForeignKey, Text, UniqueConstraint, Index, JSON
)
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property

from common.database import Base


class UserRole(str, Enum):
    """User role enumeration for RBAC."""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class UserStatus(str, Enum):
    """User account status."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"
    DELETED = "deleted"


class User(Base):
    """User account model with secure authentication support.

    Features:
    - Secure password hashing (handled by AuthService)
    - Role-based access control
    - Email validation
    - Multi-tenant support (each user has isolated Genesis X instances)
    - Quota management
    - Account status tracking
    """
    __tablename__ = "users"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Authentication
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    # Profile
    full_name = Column(String(100), nullable=True)
    role = Column(String(20), default=UserRole.USER.value, nullable=False)
    status = Column(String(20), default=UserStatus.ACTIVE.value, nullable=False)

    # Security
    email_verified = Column(Boolean, default=False, nullable=False)
    two_factor_enabled = Column(Boolean, default=False, nullable=False)
    two_factor_secret = Column(String(32), nullable=True)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    last_failed_login = Column(DateTime, nullable=True)
    account_locked_until = Column(DateTime, nullable=True)

    # Password reset
    password_reset_token = Column(String(255), nullable=True, index=True)
    password_reset_expires = Column(DateTime, nullable=True)

    # Multi-tenant isolation
    tenant_id = Column(String(50), unique=True, nullable=False, index=True)

    # Quotas and limits
    max_instances = Column(Integer, default=3, nullable=False)
    max_storage_mb = Column(Integer, default=1000, nullable=False)
    max_api_calls_per_day = Column(Integer, default=10000, nullable=False)
    current_instances = Column(Integer, default=0, nullable=False)
    current_storage_mb = Column(Float, default=0.0, nullable=False)

    # Rate limiting tracking
    api_calls_today = Column(Integer, default=0, nullable=False)
    api_calls_reset_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    last_activity_at = Column(DateTime, nullable=True)

    # Relationships
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    genesis_sessions = relationship("GenesisSession", back_populates="user")
    preferences = relationship("UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan")

    # Indexes for performance
    __table_args__ = (
        Index('idx_user_role_status', 'role', 'status'),
        Index('idx_user_tenant', 'tenant_id'),
        Index('idx_user_email_verified', 'email_verified'),
    )

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}', role='{self.role}')>"

    @validates('email')
    def validate_email(self, key, email):
        """Validate email format."""
        if not email:
            raise ValueError("Email cannot be empty")

        # RFC 5322 simplified email regex
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValueError(f"Invalid email format: {email}")

        return email.lower()

    @validates('username')
    def validate_username(self, key, username):
        """Validate username format."""
        if not username:
            raise ValueError("Username cannot be empty")

        if len(username) < 3:
            raise ValueError("Username must be at least 3 characters")

        if len(username) > 50:
            raise ValueError("Username must be at most 50 characters")

        # Allow alphanumeric, underscore, and hyphen
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")

        return username

    @validates('role')
    def validate_role(self, key, role):
        """Validate user role."""
        valid_roles = [r.value for r in UserRole]
        if role not in valid_roles:
            raise ValueError(f"Invalid role: {role}. Must be one of {valid_roles}")
        return role

    @validates('status')
    def validate_status(self, key, status):
        """Validate user status."""
        valid_statuses = [s.value for s in UserStatus]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")
        return status

    @hybrid_property
    def is_active(self) -> bool:
        """Check if user account is active."""
        return self.status == UserStatus.ACTIVE.value

    @hybrid_property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == UserRole.ADMIN.value

    @hybrid_property
    def is_locked(self) -> bool:
        """Check if account is temporarily locked."""
        if self.account_locked_until is None:
            return False
        return datetime.now(timezone.utc) < self.account_locked_until

    def can_login(self) -> bool:
        """Check if user can login."""
        return (
            self.is_active and
            not self.is_locked and
            self.status != UserStatus.SUSPENDED.value
        )

    def record_failed_login(self, lock_threshold: int = 5, lock_duration_minutes: int = 30):
        """Record a failed login attempt and lock account if threshold exceeded."""
        self.failed_login_attempts += 1
        self.last_failed_login = datetime.now(timezone.utc)

        if self.failed_login_attempts >= lock_threshold:
            self.account_locked_until = datetime.now(timezone.utc) + timedelta(minutes=lock_duration_minutes)

    def reset_failed_logins(self):
        """Reset failed login counter on successful login."""
        self.failed_login_attempts = 0
        self.last_failed_login = None
        self.account_locked_until = None

    def check_quota(self, instances: int = 0, storage_mb: float = 0, api_calls: int = 0) -> bool:
        """Check if user has sufficient quota."""
        if instances > 0 and self.current_instances + instances > self.max_instances:
            return False
        if storage_mb > 0 and self.current_storage_mb + storage_mb > self.max_storage_mb:
            return False
        if api_calls > 0:
            # Reset daily counter if needed
            if self.api_calls_reset_at is None or datetime.now(timezone.utc) >= self.api_calls_reset_at:
                self.api_calls_today = 0
                self.api_calls_reset_at = datetime.now(timezone.utc) + timedelta(days=1)

            if self.api_calls_today + api_calls > self.max_api_calls_per_day:
                return False

        return True

    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert user to dictionary (safe for API responses)."""
        data = {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "status": self.status,
            "email_verified": self.email_verified,
            "two_factor_enabled": self.two_factor_enabled,
            "tenant_id": self.tenant_id,
            "max_instances": self.max_instances,
            "max_storage_mb": self.max_storage_mb,
            "max_api_calls_per_day": self.max_api_calls_per_day,
            "current_instances": self.current_instances,
            "current_storage_mb": self.current_storage_mb,
            "api_calls_today": self.api_calls_today,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }

        if include_sensitive:
            data.update({
                "failed_login_attempts": self.failed_login_attempts,
                "account_locked_until": self.account_locked_until.isoformat() if self.account_locked_until else None,
                "password_reset_token": self.password_reset_token,
            })

        return data


class UserSession(Base):
    """User session model for JWT token management.

    Features:
    - Token blacklist for logout
    - Refresh token rotation
    - Session expiry tracking
    - Device/IP tracking for security
    """
    __tablename__ = "user_sessions"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Token management
    jti = Column(String(36), unique=True, nullable=False, index=True)  # JWT ID
    refresh_token_jti = Column(String(36), unique=True, nullable=True, index=True)
    token_type = Column(String(20), default="access", nullable=False)

    # Session tracking
    is_active = Column(Boolean, default=True, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)

    # Security metadata
    ip_address = Column(String(45), nullable=True)  # IPv6 support
    user_agent = Column(Text, nullable=True)
    device_info = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    last_used_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    revoked_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="sessions")

    # Indexes
    __table_args__ = (
        Index('idx_session_user_active', 'user_id', 'is_active'),
        Index('idx_session_expires', 'expires_at'),
        Index('idx_session_jti', 'jti'),
    )

    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, jti='{self.jti}', active={self.is_active})>"

    @hybrid_property
    def is_expired(self) -> bool:
        """Check if session has expired."""
        return datetime.now(timezone.utc) > self.expires_at

    @hybrid_property
    def is_valid(self) -> bool:
        """Check if session is valid (active, not revoked, not expired)."""
        return self.is_active and not self.is_revoked and not self.is_expired

    def revoke(self):
        """Revoke the session."""
        self.is_revoked = True
        self.is_active = False
        self.revoked_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "jti": self.jti,
            "token_type": self.token_type,
            "is_active": self.is_active,
            "is_revoked": self.is_revoked,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }


class UserPreferences(Base):
    """User preferences model for Genesis X customization.

    Stores user-specific settings for their Genesis X instances:
    - Runtime configuration overrides
    - Personality genome preferences
    - Value system setpoints
    - Tool preferences
    - UI/UX settings
    """
    __tablename__ = "user_preferences"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key (one-to-one with User)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Genesis X configuration preferences (stored as JSON)
    runtime_config = Column(JSON, nullable=True)
    genome_config = Column(JSON, nullable=True)
    value_setpoints = Column(JSON, nullable=True)
    tool_preferences = Column(JSON, nullable=True)

    # UI preferences
    theme = Column(String(20), default="dark", nullable=False)
    language = Column(String(10), default="en", nullable=False)
    timezone = Column(String(50), default="UTC", nullable=False)

    # Notification preferences
    email_notifications = Column(Boolean, default=True, nullable=False)
    system_alerts = Column(Boolean, default=True, nullable=False)

    # Privacy preferences
    telemetry_enabled = Column(Boolean, default=True, nullable=False)
    share_anonymous_usage = Column(Boolean, default=False, nullable=False)

    # Custom settings (flexible JSON field)
    custom_settings = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = relationship("User", back_populates="preferences")

    def __repr__(self):
        return f"<UserPreferences(id={self.id}, user_id={self.user_id}, theme='{self.theme}')>"

    @validates('theme')
    def validate_theme(self, key, theme):
        """Validate theme selection."""
        valid_themes = ["dark", "light", "auto"]
        if theme not in valid_themes:
            raise ValueError(f"Invalid theme: {theme}. Must be one of {valid_themes}")
        return theme

    def get_runtime_config(self, default: Optional[Dict] = None) -> Dict[str, Any]:
        """Get runtime configuration with defaults."""
        if self.runtime_config:
            return self.runtime_config
        return default or {}

    def get_genome_config(self, default: Optional[Dict] = None) -> Dict[str, Any]:
        """Get genome configuration with defaults."""
        if self.genome_config:
            return self.genome_config
        return default or {}

    def get_value_setpoints(self, default: Optional[Dict] = None) -> Dict[str, Any]:
        """Get value setpoints with defaults."""
        if self.value_setpoints:
            return self.value_setpoints
        return default or {}

    def update_preferences(self, **kwargs):
        """Update multiple preferences at once."""
        allowed_fields = [
            'theme', 'language', 'timezone', 'email_notifications',
            'system_alerts', 'telemetry_enabled', 'share_anonymous_usage',
            'runtime_config', 'genome_config', 'value_setpoints',
            'tool_preferences', 'custom_settings'
        ]

        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(self, key, value)

        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert preferences to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "runtime_config": self.runtime_config,
            "genome_config": self.genome_config,
            "value_setpoints": self.value_setpoints,
            "tool_preferences": self.tool_preferences,
            "theme": self.theme,
            "language": self.language,
            "timezone": self.timezone,
            "email_notifications": self.email_notifications,
            "system_alerts": self.system_alerts,
            "telemetry_enabled": self.telemetry_enabled,
            "share_anonymous_usage": self.share_anonymous_usage,
            "custom_settings": self.custom_settings,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
