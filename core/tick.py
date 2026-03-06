"""Tick Context - carries information through one tick.

TickContext(t, dt, phase, rng_seed, replay_mode, budgets, feature_cache,
           ledger_view, obs_batch, retrieved)
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from common.models import Observation


@dataclass
class TickContext:
    """Context passed through all phases of a tick.

    Contains immutable snapshot and mutable cache for feature extraction.
    """
    # Basic tick info
    t: int  # Tick number
    dt: float  # Time delta (seconds)
    phase: str = "init"  # Current phase name
    rng_seed: Optional[int] = None

    # Replay mode
    replay_mode: bool = False
    replay_strict: bool = False

    # Budgets (remaining for this tick)
    budgets: Dict[str, float] = field(default_factory=dict)

    # Feature cache (for reuse across phases)
    feature_cache: Dict[str, Any] = field(default_factory=dict)

    # Ledger view (read-only snapshot)
    ledger_view: Dict[str, float] = field(default_factory=dict)

    # Observations collected this tick
    obs_batch: List[Observation] = field(default_factory=list)

    # Retrieved memories (from Retrieve phase)
    retrieved: List[Dict[str, Any]] = field(default_factory=list)

    # Proposed actions from organs
    proposed_actions: List[Any] = field(default_factory=list)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def advance_phase(self, next_phase: str):
        """Move to next phase."""
        self.phase = next_phase

    def add_observation(self, obs: Observation):
        """Add observation to batch."""
        self.obs_batch.append(obs)

    def cache_feature(self, key: str, value: Any):
        """Cache a computed feature for reuse."""
        self.feature_cache[key] = value

    def get_cached_feature(self, key: str, default=None) -> Any:
        """Get cached feature."""
        return self.feature_cache.get(key, default)
