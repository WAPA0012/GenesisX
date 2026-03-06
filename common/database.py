"""
Shared Database Configuration for Genesis X.

Provides a single shared SQLAlchemy Base for all ORM models.
All models should import Base from this module to ensure
they share the same metadata registry.
"""

from sqlalchemy.orm import declarative_base

# Single shared Base for all ORM models
Base = declarative_base()
