"""
Memory Gates: Hippocampal-Inspired Gating for Episodic Memory

Implements:
- Novelty gating (high novelty -> store)
- Significance gating (high reward/delta -> store)
- Capacity-based gating

References:
- 代码大纲架构 memory/gates.py
- 论文 3.4 CLS三层记忆系统
- Hippocampal gating research
"""

from typing import Dict, Any, Optional, Union, Tuple
from .utils import get_episode_attr as _get_episode_attr


class MemoryGate:
    """
    Memory storage gating mechanism.

    Determines what gets stored in episodic memory.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Gating thresholds
        self.novelty_threshold = config.get("novelty_threshold", 0.6)
        self.significance_threshold = config.get("significance_threshold", 0.5)
        self.delta_threshold = config.get("delta_threshold", 0.3)

        # Capacity management
        self.max_episodic_size = config.get("max_episodic_size", 1000)
        self.current_episodic_count = 0

    def should_store_episodic(
        self,
        episode: Union[Dict[str, Any], Any],
        novelty_score: float,
    ) -> Tuple[bool, float]:
        """
        Determine if episode should be stored in episodic memory.

        Args:
            episode: Episode data
            novelty_score: Novelty score [0, 1]

        Returns:
            (should_store, gate_strength) tuple
        """
        # Check capacity
        if self.current_episodic_count >= self.max_episodic_size:
            # Only store if very significant
            capacity_penalty = 0.5
        else:
            capacity_penalty = 0.0

        # Novelty gate
        novelty_gate = novelty_score > self.novelty_threshold

        # Significance gate (based on reward and delta)
        reward = abs(_get_episode_attr(episode, "reward", 0.0))
        delta = abs(_get_episode_attr(episode, "delta", 0.0))

        significance = max(reward, delta)
        significance_gate = significance > self.significance_threshold

        # RPE gate (large prediction error)
        delta_gate = delta > self.delta_threshold

        # Combine gates
        gate_strength = max(
            novelty_score if novelty_gate else 0.0,
            significance if significance_gate else 0.0,
            delta if delta_gate else 0.0,
        ) - capacity_penalty

        should_store = gate_strength > 0.3

        return should_store, gate_strength

    def should_consolidate_to_schema(
        self,
        episode: Union[Dict[str, Any], Any],
        frequency: int,
    ) -> bool:
        """
        Determine if episode should be consolidated to schema memory.

        Args:
            episode: Episode data
            frequency: Number of similar episodes

        Returns:
            True if should consolidate
        """
        # Consolidate if seen multiple times
        min_frequency = self.config.get("min_consolidation_frequency", 3)

        if frequency >= min_frequency:
            return True

        # Also consolidate if very significant
        reward = abs(_get_episode_attr(episode, "reward", 0.0))
        if reward > 0.8:
            return True

        return False

    def should_extract_skill(
        self,
        action_sequence: list,
        success_rate: float,
    ) -> bool:
        """
        Determine if action sequence should be extracted as skill.

        Args:
            action_sequence: Sequence of actions
            success_rate: Success rate [0, 1]

        Returns:
            True if should extract skill
        """
        # Extract if consistently successful
        min_success_rate = self.config.get("min_skill_success_rate", 0.8)

        if success_rate >= min_success_rate:
            return True

        # Extract if sequence is long and moderately successful
        if len(action_sequence) > 5 and success_rate > 0.6:
            return True

        return False

    def update_capacity(self, current_count: int):
        """
        Update current episodic memory count.

        Args:
            current_count: Current number of episodes
        """
        self.current_episodic_count = current_count

    def get_priority_score(
        self,
        episode: Union[Dict[str, Any], Any],
        novelty_score: float,
    ) -> float:
        """
        Calculate priority score for episode.

        Higher priority = more important to keep.

        Args:
            episode: Episode data
            novelty_score: Novelty score

        Returns:
            Priority score [0, 1]
        """
        # Components
        reward = abs(_get_episode_attr(episode, "reward", 0.0))
        delta = abs(_get_episode_attr(episode, "delta", 0.0))

        # Combine with weights
        priority = (
            0.3 * novelty_score +
            0.4 * reward +
            0.3 * delta
        )

        return min(1.0, priority)

    def get_gate_stats(self) -> Dict[str, Any]:
        """Get gating statistics"""
        return {
            "novelty_threshold": self.novelty_threshold,
            "significance_threshold": self.significance_threshold,
            "delta_threshold": self.delta_threshold,
            "current_episodic_count": self.current_episodic_count,
            "max_episodic_size": self.max_episodic_size,
            "capacity_ratio": self.current_episodic_count / max(1, self.max_episodic_size),
        }
