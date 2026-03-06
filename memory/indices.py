"""
Memory Indices: Fast Retrieval with Multi-Index Support

Provides:
- Time-based index (recency)
- Value-based index (high reward episodes)
- Similarity-based index (embedding search)

References:
- 代码大纲架构 memory/indices.py
- 论文 3.4 记忆检索
"""

from typing import Dict, Any, List, Optional, Union
from collections import defaultdict

try:
    import numpy as np
except ImportError:
    np = None
from .utils import get_episode_attr as _get_episode_attr, cosine_similarity as _cosine_similarity_func


class MemoryIndex:
    """
    Multi-index system for fast memory retrieval.

    Supports:
    - Temporal index (tick-based)
    - Value index (reward-based)
    - Similarity index (embedding-based)
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Time-based index: tick -> episode_ids
        self.time_index: Dict[int, List[str]] = defaultdict(list)

        # Value-based index: reward_bucket -> episode_ids
        self.value_index: Dict[str, List[str]] = defaultdict(list)

        # Tag-based index: tag -> episode_ids
        self.tag_index: Dict[str, List[str]] = defaultdict(list)

        # Episode storage: episode_id -> episode_data
        self.episodes: Dict[str, Dict[str, Any]] = {}

        # Embedding storage: episode_id -> embedding
        self.embeddings: Dict[str, np.ndarray] = {}

    def add_episode(
        self,
        episode_id: str,
        episode: Union[Dict[str, Any], Any],
        embedding: Optional[np.ndarray] = None
    ):
        """
        Add episode to indices.

        Args:
            episode_id: Unique episode identifier
            episode: Episode data
            embedding: Optional embedding vector
        """
        # Store episode
        self.episodes[episode_id] = episode

        # Time index
        tick = _get_episode_attr(episode, "tick", 0)
        self.time_index[tick].append(episode_id)

        # Value index
        reward = _get_episode_attr(episode, "reward", 0.0)
        value_bucket = self._get_value_bucket(reward)
        self.value_index[value_bucket].append(episode_id)

        # Tag index
        tags = _get_episode_attr(episode, "tags", [])
        for tag in tags:
            self.tag_index[tag].append(episode_id)

        # Embedding storage
        if embedding is not None:
            self.embeddings[episode_id] = embedding

    def retrieve_by_time(
        self,
        start_tick: int,
        end_tick: Optional[int] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve episodes by time range.

        Args:
            start_tick: Start tick
            end_tick: End tick (or None for all after start)
            max_results: Max number of results

        Returns:
            List of episodes
        """
        if end_tick is None:
            end_tick = max(self.time_index.keys()) if self.time_index else start_tick

        episode_ids = []
        for tick, eids in self.time_index.items():
            if start_tick <= tick <= end_tick:
                episode_ids.extend(eids)

        # Return most recent first
        episode_ids = episode_ids[-max_results:]

        return [self.episodes[eid] for eid in episode_ids if eid in self.episodes]

    def retrieve_by_value(
        self,
        min_reward: float = 0.5,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve high-value episodes.

        Args:
            min_reward: Minimum reward threshold
            max_results: Max number of results

        Returns:
            List of episodes sorted by reward
        """
        episode_ids = []

        # Get all value buckets >= min_reward
        for bucket_key in self.value_index.keys():
            bucket_reward = self._parse_value_bucket(bucket_key)
            if bucket_reward >= min_reward:
                episode_ids.extend(self.value_index[bucket_key])

        # Sort by reward
        episodes = [self.episodes[eid] for eid in episode_ids if eid in self.episodes]
        episodes.sort(key=lambda e: _get_episode_attr(e, "reward", 0.0), reverse=True)

        return episodes[:max_results]

    def retrieve_by_tag(
        self,
        tags: List[str],
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve episodes by tags.

        Args:
            tags: List of tags to match
            max_results: Max number of results

        Returns:
            List of episodes
        """
        episode_ids = set()

        for tag in tags:
            episode_ids.update(self.tag_index.get(tag, []))

        episodes = [self.episodes[eid] for eid in episode_ids if eid in self.episodes]

        return episodes[:max_results]

    def retrieve_by_similarity(
        self,
        query_embedding: np.ndarray,
        max_results: int = 10,
        min_similarity: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve episodes by embedding similarity.

        Args:
            query_embedding: Query embedding vector
            max_results: Max number of results
            min_similarity: Minimum cosine similarity

        Returns:
            List of episodes sorted by similarity
        """
        if not self.embeddings:
            return []

        # Calculate similarities
        similarities = []
        for episode_id, embedding in self.embeddings.items():
            similarity = _cosine_similarity_func(query_embedding, embedding)
            if similarity >= min_similarity:
                similarities.append((episode_id, similarity))

        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Get top results
        top_ids = [eid for eid, _ in similarities[:max_results]]

        return [self.episodes[eid] for eid in top_ids if eid in self.episodes]

    def remove_episode(self, episode_id: str):
        """
        Remove episode from all indices.

        Args:
            episode_id: Episode identifier
        """
        if episode_id not in self.episodes:
            return

        episode = self.episodes[episode_id]

        # Remove from time index
        tick = _get_episode_attr(episode, "tick", 0)
        if tick in self.time_index:
            self.time_index[tick] = [
                eid for eid in self.time_index[tick] if eid != episode_id
            ]

        # Remove from value index
        reward = _get_episode_attr(episode, "reward", 0.0)
        value_bucket = self._get_value_bucket(reward)
        if value_bucket in self.value_index:
            self.value_index[value_bucket] = [
                eid for eid in self.value_index[value_bucket] if eid != episode_id
            ]

        # Remove from tag index
        tags = _get_episode_attr(episode, "tags", [])
        for tag in tags:
            if tag in self.tag_index:
                self.tag_index[tag] = [
                    eid for eid in self.tag_index[tag] if eid != episode_id
                ]

        # Remove episode and embedding
        del self.episodes[episode_id]
        if episode_id in self.embeddings:
            del self.embeddings[episode_id]

    def _get_value_bucket(self, reward: float) -> str:
        """
        Get value bucket for reward.

        Args:
            reward: Reward value

        Returns:
            Bucket key
        """
        # Bucket by 0.1 intervals
        bucket = int(reward * 10) / 10.0
        return f"reward_{bucket:.1f}"

    def _parse_value_bucket(self, bucket_key: str) -> float:
        """Parse reward from bucket key"""
        try:
            return float(bucket_key.split("_")[1])
        except (IndexError, ValueError):
            return 0.0

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        return {
            "total_episodes": len(self.episodes),
            "total_embeddings": len(self.embeddings),
            "time_buckets": len(self.time_index),
            "value_buckets": len(self.value_index),
            "tags": len(self.tag_index),
        }
