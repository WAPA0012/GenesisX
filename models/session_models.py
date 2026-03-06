"""
Session-related database models for Genesis X.

Models:
- GenesisSession: Main session metadata
- SessionState: State snapshots at each tick
- Episode: Episode records (one per tick)
- Memory: Episodic, semantic, and skill memories
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Text,
    JSON,
    ForeignKey,
    Index,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from models import BaseModel


class SessionStatus(str, enum.Enum):
    """Session status enumeration."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class MemoryType(str, enum.Enum):
    """Memory type enumeration."""

    EPISODIC = "episodic"  # Autobiographical events
    SEMANTIC = "semantic"  # Schema, facts, concepts
    SKILL = "skill"  # Learned skills/procedures


class GenesisSession(BaseModel):
    """
    Main session record for Genesis X.

    A session represents one continuous run of the Genesis X system,
    containing multiple ticks and episodes.
    """

    __tablename__ = "genesis_sessions"

    # Session identification
    session_id = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # Session metadata
    status = Column(SQLEnum(SessionStatus), default=SessionStatus.ACTIVE, nullable=False, index=True)
    mode = Column(String(32), default="work", nullable=False)  # work, friend, sleep
    stage = Column(String(32), default="adult", nullable=False)  # embryo, juvenile, adult, elder

    # Timing
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    ended_at = Column(DateTime, nullable=True)
    last_tick_at = Column(DateTime, nullable=True)

    # Counters
    tick_count = Column(Integer, default=0, nullable=False)
    episode_count = Column(Integer, default=0, nullable=False)
    total_interactions = Column(Integer, default=0, nullable=False)

    # Resource usage
    total_tokens = Column(Integer, default=0, nullable=False)
    total_cost = Column(Float, default=0.0, nullable=False)
    total_io_ops = Column(Integer, default=0, nullable=False)
    total_net_bytes = Column(Integer, default=0, nullable=False)

    # Final state snapshot
    final_state = Column(JSON, nullable=True)

    # Configuration
    config = Column(JSON, nullable=True)

    # Notes and tags
    notes = Column(Text, nullable=True)
    tags = Column(JSON, default=list, nullable=True)

    # Relationships
    user = relationship("User", back_populates="genesis_sessions")
    states = relationship("SessionState", back_populates="session", cascade="all, delete-orphan")
    episodes = relationship("Episode", back_populates="session", cascade="all, delete-orphan")
    memories = relationship("Memory", back_populates="session", cascade="all, delete-orphan")

    # Indexes for performance
    __table_args__ = (
        Index("idx_session_user_status", "user_id", "status"),
        Index("idx_session_started", "started_at"),
        Index("idx_session_mode_stage", "mode", "stage"),
    )

    def __repr__(self):
        return f"<GenesisSession(id={self.id}, session_id={self.session_id}, status={self.status})>"


class SessionState(BaseModel):
    """
    State snapshot at a specific tick.

    Stores the complete internal state S_t = ⟨O_t, X_t, M_t, K_t, θ, ω_t⟩
    """

    __tablename__ = "session_states"

    # Foreign keys
    session_id = Column(Integer, ForeignKey("genesis_sessions.id"), nullable=False, index=True)
    tick = Column(Integer, nullable=False, index=True)

    # Internal state X_t
    energy = Column(Float, default=0.8, nullable=False)
    mood = Column(Float, default=0.5, nullable=False)
    stress = Column(Float, default=0.2, nullable=False)
    fatigue = Column(Float, default=0.1, nullable=False)
    bond = Column(Float, default=0.0, nullable=False)
    trust = Column(Float, default=0.5, nullable=False)
    boredom = Column(Float, default=0.0, nullable=False)

    # Value system
    value_pred = Column(Float, default=0.0, nullable=False)  # V(s_t)
    weights = Column(JSON, nullable=True)  # w_t - dynamic weights
    gaps = Column(JSON, nullable=True)  # d_t - drive gaps
    setpoints = Column(JSON, nullable=True)  # θ - setpoints
    utilities = Column(JSON, nullable=True)  # u_t - utility values

    # Working memory
    current_goal = Column(Text, nullable=True)
    current_plan = Column(Text, nullable=True)
    last_user_interaction = Column(Float, default=0.0, nullable=False)

    # Memory counts
    episodic_count = Column(Integer, default=0, nullable=False)
    schema_count = Column(Integer, default=0, nullable=False)
    skill_count = Column(Integer, default=0, nullable=False)

    # Resource ledger
    tokens_used = Column(Integer, default=0, nullable=False)
    io_ops = Column(Integer, default=0, nullable=False)
    net_bytes = Column(Integer, default=0, nullable=False)
    money_spent = Column(Float, default=0.0, nullable=False)

    # Complete state as JSON (for flexibility)
    full_state = Column(JSON, nullable=True)

    # Timestamp
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    session = relationship("GenesisSession", back_populates="states")

    # Indexes
    __table_args__ = (
        Index("idx_state_session_tick", "session_id", "tick", unique=True),
        Index("idx_state_timestamp", "timestamp"),
    )

    def __repr__(self):
        return f"<SessionState(session_id={self.session_id}, tick={self.tick}, energy={self.energy:.2f})>"


class Episode(BaseModel):
    """
    Episode record: Complete record of one tick.

    e_t = ⟨t, O_t, a_t, outcome_t, r_t, δ_t, tags⟩

    Based on Section 3.10.2 of the paper.
    """

    __tablename__ = "episodes"

    # Foreign keys
    session_id = Column(Integer, ForeignKey("genesis_sessions.id"), nullable=False, index=True)
    tick = Column(Integer, nullable=False, index=True)

    # Timestamp
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Observation O_t
    observation_type = Column(String(64), nullable=True)
    observation_payload = Column(JSON, nullable=True)
    observation_source = Column(String(128), nullable=True)

    # Action a_t
    action_type = Column(String(64), nullable=True)  # CHAT, USE_TOOL, LEARN_SKILL, etc.
    action_params = Column(JSON, nullable=True)
    action_risk_level = Column(Float, default=0.0, nullable=False)
    action_capabilities = Column(JSON, nullable=True)  # Required capabilities

    # Outcome
    outcome_ok = Column(Boolean, default=True, nullable=False)
    outcome_status = Column(String(256), nullable=True)
    outcome_tool_output_ref = Column(String(256), nullable=True)
    outcome_major_error = Column(Boolean, default=False, nullable=False)
    outcome_error_message = Column(Text, nullable=True)

    # Cost vector
    cost_cpu_tokens = Column(Integer, default=0, nullable=False)
    cost_io_ops = Column(Integer, default=0, nullable=False)
    cost_net_bytes = Column(Integer, default=0, nullable=False)
    cost_latency_ms = Column(Float, default=0.0, nullable=False)
    cost_risk_score = Column(Float, default=0.0, nullable=False)
    cost_money = Column(Float, default=0.0, nullable=False)

    # Reward and value
    reward = Column(Float, default=0.0, nullable=False)  # r_t
    delta = Column(Float, default=0.0, nullable=False)  # δ_t (RPE)
    value_pred = Column(Float, default=0.0, nullable=False)  # V(s_t)

    # State snapshot reference
    state_snapshot = Column(JSON, nullable=True)

    # Value system snapshot
    weights = Column(JSON, nullable=True)
    gaps = Column(JSON, nullable=True)
    utilities = Column(JSON, nullable=True)

    # Goal and plan
    current_goal = Column(Text, nullable=True)
    selected_plan = Column(Text, nullable=True)

    # Metadata
    tags = Column(JSON, default=list, nullable=True)  # Dimensions, tools, emotions, topics

    # Replay
    replay_mode = Column(Boolean, default=False, nullable=False)
    rng_seed = Column(Integer, nullable=True)

    # Full episode data (for completeness)
    full_episode = Column(JSON, nullable=True)

    # Relationships
    session = relationship("GenesisSession", back_populates="episodes")

    # Indexes for querying
    __table_args__ = (
        Index("idx_episode_session_tick", "session_id", "tick", unique=True),
        Index("idx_episode_timestamp", "timestamp"),
        Index("idx_episode_action_type", "action_type"),
        Index("idx_episode_reward", "reward"),
        Index("idx_episode_outcome", "outcome_ok"),
    )

    def __repr__(self):
        return f"<Episode(session_id={self.session_id}, tick={self.tick}, action={self.action_type})>"


class Memory(BaseModel):
    """
    Memory storage: Episodic, semantic (schema), and skill memories.

    Supports the three-store memory system from Section 3.10.
    """

    __tablename__ = "memories"

    # Foreign keys
    session_id = Column(Integer, ForeignKey("genesis_sessions.id"), nullable=False, index=True)

    # Memory identification
    memory_type = Column(SQLEnum(MemoryType), nullable=False, index=True)
    memory_id = Column(String(64), unique=True, nullable=False, index=True)

    # Core content
    content = Column(JSON, nullable=False)  # Memory content (flexible schema)
    summary = Column(Text, nullable=True)  # Human-readable summary

    # Episodic-specific fields
    tick = Column(Integer, nullable=True, index=True)  # For episodic memories
    episode_id = Column(Integer, ForeignKey("episodes.id"), nullable=True, index=True)

    # Semantic-specific fields (schema)
    schema_type = Column(String(64), nullable=True)  # Type of schema
    evidence_count = Column(Integer, default=1, nullable=False)  # Supporting episodes
    confidence = Column(Float, default=0.5, nullable=False)  # Confidence score

    # Skill-specific fields
    skill_name = Column(String(128), nullable=True, index=True)
    skill_domain = Column(String(64), nullable=True)
    success_rate = Column(Float, nullable=True)  # Historical success rate
    usage_count = Column(Integer, default=0, nullable=False)

    # Salience and importance
    salience = Column(Float, default=0.5, nullable=False, index=True)  # Salience score
    importance = Column(Float, default=0.5, nullable=False)  # Importance score
    recency = Column(Float, default=1.0, nullable=False)  # Recency factor

    # Retrieval and access
    last_accessed_at = Column(DateTime, nullable=True)
    access_count = Column(Integer, default=0, nullable=False)

    # Emotional valence
    emotional_valence = Column(Float, default=0.0, nullable=False)  # -1 to 1

    # Tags and categories
    tags = Column(JSON, default=list, nullable=True)
    categories = Column(JSON, default=list, nullable=True)

    # Embeddings (for semantic search)
    embedding = Column(JSON, nullable=True)  # Vector embedding

    # Consolidation
    consolidated = Column(Boolean, default=False, nullable=False)  # Has been consolidated
    consolidation_level = Column(Integer, default=0, nullable=False)  # Consolidation depth

    # Related memories
    related_memory_ids = Column(JSON, default=list, nullable=True)

    # Relationships
    session = relationship("GenesisSession", back_populates="memories")
    episode = relationship("Episode", foreign_keys=[episode_id])

    # Indexes for performance
    __table_args__ = (
        Index("idx_memory_type_session", "memory_type", "session_id"),
        Index("idx_memory_salience", "salience"),
        Index("idx_memory_importance", "importance"),
        Index("idx_memory_tick", "tick"),
        Index("idx_memory_skill", "skill_name"),
        Index("idx_memory_schema", "schema_type"),
        Index("idx_memory_accessed", "last_accessed_at"),
        Index("idx_memory_consolidated", "consolidated"),
    )

    def __repr__(self):
        return f"<Memory(id={self.id}, type={self.memory_type}, memory_id={self.memory_id})>"

    def update_access(self):
        """Update access statistics."""
        self.last_accessed_at = datetime.now(timezone.utc)
        self.access_count += 1

    def decay_salience(self, decay_rate: float = 0.95):
        """Apply temporal decay to salience."""
        self.salience *= decay_rate
