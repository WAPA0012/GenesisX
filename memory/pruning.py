"""
Memory Pruning: Capacity Management with Consolidation

Implements:
- Importance-based pruning
- Consolidation to schema memory
- Skill extraction from repeated patterns

References:
- 代码大纲架构 memory/pruning.py
- 论文 3.4.3 记忆固化与剪枝
"""

from typing import Dict, Any, List, Optional, Union
import hashlib
from .utils import get_episode_attr as _get_episode_attr, cosine_similarity as _cosine_similarity_func

try:
    import numpy as np
except ImportError:
    np = None


class PruningStrategy:
    """Memory pruning strategy"""

    LRU = "lru"                    # Least Recently Used
    IMPORTANCE = "importance"      # Keep high-importance memories
    CONSOLIDATION = "consolidation"  # Consolidate similar memories


class MemoryPruner:
    """
    Memory capacity management with consolidation.

    Strategies:
    - Prune low-importance episodic memories
    - Consolidate similar episodes to schemas
    - Extract skills from repeated action sequences
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Capacity limits (修复 M55: 与论文 Appendix A.7 对齐)
        # 论文: N_ep=50000, N_sch=1000, N_sk=300
        self.max_episodic = config.get("max_episodic_memory", 50000)
        self.max_schema = config.get("max_schema_memory", 1000)
        self.max_skills = config.get("max_skills", 300)

        # Pruning thresholds
        self.prune_threshold = config.get("prune_threshold", 0.9)  # Start pruning at 90% capacity
        self.min_importance = config.get("min_importance", 0.2)

        # Consolidation
        self.similarity_threshold = config.get("similarity_threshold", 0.8)

    def should_prune(
        self,
        current_count: int,
        max_capacity: int
    ) -> bool:
        """
        Check if pruning should be triggered.

        Args:
            current_count: Current memory count
            max_capacity: Max capacity

        Returns:
            True if should prune
        """
        usage_ratio = current_count / max(1, max_capacity)
        return usage_ratio >= self.prune_threshold

    def select_episodes_to_prune(
        self,
        episodes: List[Dict[str, Any]],
        target_count: int
    ) -> List[str]:
        """
        Select episodes to prune.

        Args:
            episodes: List of episodes
            target_count: Target number to keep

        Returns:
            List of episode IDs to remove
        """
        # Calculate importance scores
        max_tick = max((_get_episode_attr(e, "tick", 0) for e in episodes), default=0)
        scored_episodes = []
        for episode in episodes:
            importance = self._calculate_importance(episode, max_tick=max_tick)
            episode_id = _get_episode_attr(episode, "episode_id", "")
            scored_episodes.append((episode_id, importance, episode))

        # Sort by importance (ascending)
        scored_episodes.sort(key=lambda x: x[1])

        # Select least important to prune
        num_to_prune = len(episodes) - target_count
        to_prune = [eid for eid, _, _ in scored_episodes[:num_to_prune]]

        return to_prune

    def consolidate_episodes(
        self,
        episodes: List[Dict[str, Any]],
        embeddings: Optional[Dict[str, np.ndarray]] = None
    ) -> List[Dict[str, Any]]:
        """
        Consolidate similar episodes into schemas.

        Args:
            episodes: List of episodes
            embeddings: Optional embeddings dict

        Returns:
            List of consolidated schemas
        """
        if not episodes:
            return []

        # Group similar episodes
        clusters = self._cluster_episodes(episodes, embeddings)

        # Create schemas from clusters
        schemas = []
        for cluster in clusters:
            if len(cluster) >= 2:  # Only consolidate if 2+ similar episodes
                schema = self._create_schema(cluster)
                schemas.append(schema)

        return schemas

    def extract_skills(
        self,
        episodes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Extract skill patterns from episodes.

        Args:
            episodes: List of episodes

        Returns:
            List of extracted skills
        """
        # Group episodes by action sequences
        action_sequences = {}

        for episode in episodes:
            action = _get_episode_attr(episode, "action", {})
            tool_id = action.get("tool_id", "") if isinstance(action, dict) else getattr(action, "tool_id", "")

            if tool_id:
                if tool_id not in action_sequences:
                    action_sequences[tool_id] = []
                action_sequences[tool_id].append(episode)

        # Extract skills for repeated successful actions
        skills = []
        for tool_id, tool_episodes in action_sequences.items():
            # Calculate success rate
            successes = sum(1 for e in tool_episodes if _get_episode_attr(e, "reward", 0) > 0)
            success_rate = successes / len(tool_episodes)

            if success_rate > 0.7 and len(tool_episodes) >= 3:
                rewards = [_get_episode_attr(e, "reward", 0) for e in tool_episodes]
                avg_reward = sum(rewards) / len(rewards) if rewards else 0.0
                skill = {
                    "skill_id": f"skill_{tool_id}",
                    "tool_id": tool_id,
                    "success_rate": success_rate,
                    "usage_count": len(tool_episodes),
                    "avg_reward": avg_reward,
                }
                skills.append(skill)

        return skills

    def _calculate_importance(self, episode: Dict[str, Any], max_tick: int = 0) -> float:
        """
        Calculate episode importance score.

        Args:
            episode: Episode data
            max_tick: Current maximum tick (for recency normalization)

        Returns:
            Importance score [0, 1]
        """
        # Components
        reward = abs(_get_episode_attr(episode, "reward", 0.0))
        delta = abs(_get_episode_attr(episode, "delta", 0.0))

        # Recency (newer = more important)
        tick = _get_episode_attr(episode, "tick", 0)
        effective_max = max(1, max_tick) if max_tick > 0 else max(1, tick)
        recency = min(1.0, tick / effective_max)

        # Novelty (if available)
        novelty = _get_episode_attr(episode, "novelty", 0.5)

        # Combine
        importance = (
            0.3 * reward +
            0.2 * delta +
            0.2 * recency +
            0.3 * novelty
        )

        return min(1.0, importance)

    def _cluster_episodes(
        self,
        episodes: List[Dict[str, Any]],
        embeddings: Optional[Dict[str, np.ndarray]] = None
    ) -> List[List[Dict[str, Any]]]:
        """
        Cluster similar episodes.

        Simple implementation using similarity threshold.

        Args:
            episodes: List of episodes
            embeddings: Optional embeddings dict

        Returns:
            List of episode clusters
        """
        if not embeddings:
            # Without embeddings, cluster by tags
            return self._cluster_by_tags(episodes)

        # Cluster by embedding similarity
        clusters = []
        used = set()

        for i, episode_i in enumerate(episodes):
            if i in used:
                continue

            episode_id_i = _get_episode_attr(episode_i, "episode_id", str(i))
            if episode_id_i not in embeddings:
                continue

            cluster = [episode_i]
            used.add(i)

            for j, episode_j in enumerate(episodes[i+1:], start=i+1):
                if j in used:
                    continue

                episode_id_j = _get_episode_attr(episode_j, "episode_id", str(j))
                if episode_id_j not in embeddings:
                    continue

                # Calculate similarity
                similarity = _cosine_similarity_func(
                    embeddings[episode_id_i],
                    embeddings[episode_id_j]
                )

                if similarity >= self.similarity_threshold:
                    cluster.append(episode_j)
                    used.add(j)

            clusters.append(cluster)

        return clusters

    def _cluster_by_tags(
        self,
        episodes: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """Cluster episodes by shared tags"""
        tag_clusters = {}

        for episode in episodes:
            tags = tuple(sorted(_get_episode_attr(episode, "tags", [])))
            if tags:
                if tags not in tag_clusters:
                    tag_clusters[tags] = []
                tag_clusters[tags].append(episode)

        return list(tag_clusters.values())

    def _create_schema(self, cluster: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create schema from episode cluster.

        Args:
            cluster: List of similar episodes

        Returns:
            Schema dict
        """
        # Aggregate statistics
        rewards = [_get_episode_attr(e, "reward", 0) for e in cluster]
        deltas = [_get_episode_attr(e, "delta", 0) for e in cluster]
        avg_reward = sum(rewards) / len(rewards) if rewards else 0.0
        avg_delta = sum(deltas) / len(deltas) if deltas else 0.0

        # Extract common tags
        all_tags = []
        for episode in cluster:
            all_tags.extend(_get_episode_attr(episode, "tags", []))

        common_tags = list(set(all_tags))

        # Create schema
        schema = {
            # 修复 M54: 使用确定性哈希替代内置hash() (Python hash随机化导致跨进程不确定)
            "schema_id": f"schema_{hashlib.sha256(','.join(sorted(common_tags)).encode()).hexdigest()[:16]}",
            "episode_count": len(cluster),
            "avg_reward": avg_reward,
            "avg_delta": avg_delta,
            "tags": common_tags,
            "representative_episode": cluster[0],  # Use first episode as representative
        }

        return schema

    def get_pruning_stats(
        self,
        current_counts: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        Get pruning statistics.

        Args:
            current_counts: Dict with episodic/schema/skills counts

        Returns:
            Stats dict
        """
        episodic_count = current_counts.get("episodic", 0)
        schema_count = current_counts.get("schema", 0)
        skills_count = current_counts.get("skills", 0)

        return {
            "episodic": {
                "count": episodic_count,
                "max": self.max_episodic,
                "usage_ratio": episodic_count / max(1, self.max_episodic),
                "should_prune": self.should_prune(episodic_count, self.max_episodic),
            },
            "schema": {
                "count": schema_count,
                "max": self.max_schema,
                "usage_ratio": schema_count / max(1, self.max_schema),
                "should_prune": self.should_prune(schema_count, self.max_schema),
            },
            "skills": {
                "count": skills_count,
                "max": self.max_skills,
                "usage_ratio": skills_count / max(1, self.max_skills),
                "should_prune": self.should_prune(skills_count, self.max_skills),
            },
        }
