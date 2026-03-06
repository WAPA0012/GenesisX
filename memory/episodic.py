"""Episodic Memory - event-sourcing view of episodes."""
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from pathlib import Path
from common.models import EpisodeRecord
from common.jsonl import read_jsonl
from common.logger import get_logger
import bisect
import shutil
from collections import deque
from datetime import datetime, timezone

logger = get_logger(__name__)

# 延迟导入联想记忆
if TYPE_CHECKING:
    from .familiarity import AssociativeMemory


# 尝试导入 orjson，如果不可用则使用标准库 json
try:
    import orjson
    HAS_ORJSON = True
except ImportError:
    import json as orjson
    HAS_ORJSON = False


class EpisodicMemory:
    """Append-only episodic memory backed by episodes.jsonl.

    Provides query methods by:
    - Time range
    - Tag filtering
    - Goal filtering
    - Salience threshold
    - Associative retrieval (联想检索)

    Performance optimizations:
    - Sorted tick list for binary search O(log n)
    - Index-based lookups
    - LRU cache size limit
    """

    def __init__(
        self,
        episodes_path: Optional[Path] = None,
        max_cache_size: int = 50000,
        enable_associative: bool = True
    ):
        """Initialize episodic memory.

        Args:
            episodes_path: Path to episodes.jsonl (if None, in-memory only)
            max_cache_size: Maximum number of episodes to keep in cache
            enable_associative: Enable associative memory (联想记忆)
        """
        self.episodes_path = episodes_path
        self._cache: deque = deque()  # Ordered episodes for iteration/eviction
        self._by_tick: Dict[int, EpisodeRecord] = {}  # tick -> episode (O(1) lookup)
        self._sorted_ticks: List[int] = []  # Sorted list of ticks for binary search
        self.max_cache_size = max_cache_size

        # 联想记忆
        self.enable_associative = enable_associative
        self._associative_memory: Optional["AssociativeMemory"] = None

        if episodes_path and episodes_path.exists():
            self._load_from_disk()

    def _load_from_disk(self):
        """Load episodes from disk into cache."""
        for record in read_jsonl(self.episodes_path):
            try:
                episode = EpisodeRecord(**record)
                self._cache.append(episode)
                self._by_tick[episode.tick] = episode
                self._sorted_ticks.append(episode.tick)
            except Exception as e:
                print(f"[EpisodicMemory] Failed to load episode: {e}")

        # Sort ticks for binary search
        self._sorted_ticks.sort()

    def append(self, episode: EpisodeRecord):
        """Append new episode to memory and persist to disk (修复 H22).

        Args:
            episode: Episode to append
        """
        self._cache.append(episode)
        self._by_tick[episode.tick] = episode

        # Insert into sorted ticks list (maintain sorted order)
        bisect.insort(self._sorted_ticks, episode.tick)

        # 添加到联想记忆
        if self.enable_associative and self._associative_memory:
            self._add_to_associative(episode)

        # 修复 H22: 立即持久化到磁盘，防止进程崩溃丢失数据
        if self.episodes_path:
            self._persist_episode(episode)

        # Enforce cache size limit - remove oldest if needed
        if len(self._cache) > self.max_cache_size:
            self._evict_oldest()

    def _persist_episode(self, episode: EpisodeRecord):
        """Persist a single episode to disk (append mode).

        Args:
            episode: Episode to persist
        """
        if not self.episodes_path:
            print(f"[EpisodicMemory] ERROR: episodes_path is None, cannot persist episode {episode.tick}")
            return  # 没有设置路径，跳过持久化

        print(f"[EpisodicMemory] Persisting episode {episode.tick} to {self.episodes_path}")
        try:
            episode_dict = episode.model_dump()
            if HAS_ORJSON:
                with open(self.episodes_path, 'ab') as f:
                    json_bytes = orjson.dumps(
                        episode_dict,
                        option=orjson.OPT_APPEND_NEWLINE | orjson.OPT_SERIALIZE_NUMPY
                    )
                    f.write(json_bytes)
            else:
                import json
                with open(self.episodes_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(episode_dict, ensure_ascii=False, default=str) + '\n')
            print(f"[EpisodicMemory] Successfully persisted episode {episode.tick}")
        except Exception as e:
            # 持久化失败不应该阻塞主循环，但需要记录
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"[EpisodicMemory] Failed to persist episode {episode.tick}: {e}", exc_info=True)
            print(f"[EpisodicMemory] ERROR: Failed to persist episode {episode.tick}: {e}")

    def _evict_oldest(self):
        """Remove oldest episode from cache to maintain size limit. O(log n)."""
        if not self._cache:
            return

        # Remove oldest (first in deque) - O(1)
        oldest = self._cache.popleft()
        self._by_tick.pop(oldest.tick, None)

        # Remove from sorted ticks - O(log n) find + O(n) remove
        tick_idx = bisect.bisect_left(self._sorted_ticks, oldest.tick)
        if tick_idx < len(self._sorted_ticks) and self._sorted_ticks[tick_idx] == oldest.tick:
            self._sorted_ticks.pop(tick_idx)

    def get_by_tick(self, tick: int) -> Optional[EpisodeRecord]:
        """Get episode by tick number. O(1) dict lookup.

        Args:
            tick: Tick number

        Returns:
            EpisodeRecord or None
        """
        return self._by_tick.get(tick)

    def query_recent(self, n: int = 10) -> List[EpisodeRecord]:
        """Get N most recent episodes.

        Args:
            n: Number of episodes

        Returns:
            List of episodes
        """
        if not self._cache:
            return []
        n = min(n, len(self._cache))
        # deque doesn't support slicing; use reversed iteration for efficiency
        result = []
        it = reversed(self._cache)
        for _ in range(n):
            result.append(next(it))
        result.reverse()
        return result

    def query_by_time_range(self, start_tick: int, end_tick: int) -> List[EpisodeRecord]:
        """Query episodes in time range [start_tick, end_tick].

        Uses binary search for O(log n) finding of range boundaries.

        Args:
            start_tick: Start tick (inclusive)
            end_tick: End tick (inclusive)

        Returns:
            List of episodes
        """
        # Use binary search to find range boundaries
        left_idx = bisect.bisect_left(self._sorted_ticks, start_tick)
        right_idx = bisect.bisect_right(self._sorted_ticks, end_tick)

        # Get episodes in range
        result = []
        for i in range(left_idx, right_idx):
            if i < len(self._sorted_ticks):
                tick = self._sorted_ticks[i]
                episode = self.get_by_tick(tick)
                if episode:
                    result.append(episode)

        return result

    def query_by_goal(self, goal: str, limit: int = 20) -> List[EpisodeRecord]:
        """Query episodes related to a goal.

        Args:
            goal: Goal string to match
            limit: Maximum episodes to return

        Returns:
            List of episodes
        """
        matches = [
            ep for ep in self._cache
            if ep.current_goal == goal
        ]
        return matches[-limit:]

    def query_by_tags(self, tags: List[str], limit: int = 20) -> List[EpisodeRecord]:
        """Query episodes containing any of the tags.

        Args:
            tags: List of tags to match
            limit: Maximum episodes to return

        Returns:
            List of episodes
        """
        matches = [
            ep for ep in self._cache
            if any(tag in getattr(ep, 'tags', []) for tag in tags)
        ]
        return matches[-limit:]

    def query_high_salience(self, threshold: float = 0.7, limit: int = 20) -> List[EpisodeRecord]:
        """Query episodes with high salience (based on |delta|).

        Args:
            threshold: Salience threshold
            limit: Maximum episodes to return

        Returns:
            List of episodes
        """
        matches = [
            ep for ep in self._cache
            if abs(ep.delta) > threshold
        ]
        # Sort by absolute delta descending
        matches.sort(key=lambda e: abs(e.delta), reverse=True)
        return matches[:limit]

    def count(self) -> int:
        """Get total episode count.

        Returns:
            Number of episodes
        """
        return len(self._cache)

    def get_all(self) -> List[EpisodeRecord]:
        """Get all episodes (use with caution for large memories).

        Returns:
            All episodes
        """
        # Return a view instead of copy to avoid memory overhead
        return list(self._cache)

    # =============================================================================
    # Disk Management Methods
    # =============================================================================

    def get_disk_size_mb(self) -> float:
        """Get the size of the disk file in MB.

        Returns:
            File size in megabytes, or 0.0 if no file exists
        """
        if not self.episodes_path or not self.episodes_path.exists():
            return 0.0
        return self.episodes_path.stat().st_size / (1024 * 1024)

    def prune_disk_by_salience(
        self,
        salience_threshold: float = 0.3,
        keep_recent_ratio: float = 0.15,
        backup: bool = True
    ) -> Dict[str, int]:
        """Prune disk file by removing low-salience episodes.

        Keeps:
        - Episodes with |delta| > salience_threshold
        - Most recent keep_recent_ratio of episodes

        Args:
            salience_threshold: Minimum |delta| to keep
            keep_recent_ratio: Fraction of recent episodes to always keep
            backup: Whether to create backup before pruning

        Returns:
            Dict with 'total', 'kept', 'pruned' counts
        """
        if not self.episodes_path or not self.episodes_path.exists():
            return {"total": 0, "kept": 0, "pruned": 0}

        # Create backup if requested
        if backup:
            backup_path = self.episodes_path.with_suffix('.jsonl.bak')
            shutil.copy2(self.episodes_path, backup_path)

        # Read all episodes
        all_episodes = list(read_jsonl(self.episodes_path))
        total = len(all_episodes)

        if total == 0:
            return {"total": 0, "kept": 0, "pruned": 0}

        # Calculate keep count for recent episodes
        keep_recent_count = max(1, int(total * keep_recent_ratio))

        # Filter episodes
        kept = []
        pruned = 0

        # Sort by tick to identify recent episodes
        sorted_episodes = sorted(all_episodes, key=lambda e: e.get('tick', 0))

        for i, ep in enumerate(sorted_episodes):
            # Always keep most recent episodes
            if i >= total - keep_recent_count:
                kept.append(ep)
                continue

            # Keep high-salience episodes
            delta = ep.get('delta', 0.0)
            if abs(delta) > salience_threshold:
                kept.append(ep)
            else:
                pruned += 1

        # Write back kept episodes
        if HAS_ORJSON:
            with open(self.episodes_path, 'wb') as f:
                for ep in kept:
                    json_bytes = orjson.dumps(
                        ep,
                        option=orjson.OPT_APPEND_NEWLINE | orjson.OPT_SERIALIZE_NUMPY
                    )
                    f.write(json_bytes)
        else:
            import json
            with open(self.episodes_path, 'w', encoding='utf-8') as f:
                for ep in kept:
                    f.write(json.dumps(ep, ensure_ascii=False) + '\n')

        # Rebuild cache
        self._cache.clear()
        self._by_tick.clear()
        self._sorted_ticks.clear()
        self._load_from_disk()

        return {"total": total, "kept": len(kept), "pruned": pruned}

    def archive_old_episodes(
        self,
        archive_before_tick: int,
        archive_path: Optional[Path] = None
    ) -> int:
        """Archive episodes older than a tick to a separate file.

        Args:
            archive_before_tick: Archive episodes with tick < this value
            archive_path: Optional custom archive path (default: episodes_archive_TICK.jsonl)

        Returns:
            Number of episodes archived
        """
        if not self.episodes_path or not self.episodes_path.exists():
            return 0

        # Default archive path
        if archive_path is None:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            archive_path = self.episodes_path.parent / f"episodes_archive_{timestamp}_before_{archive_before_tick}.jsonl"

        # Read and split episodes
        to_keep = []
        to_archive = []

        for ep in read_jsonl(self.episodes_path):
            if ep.get('tick', 0) < archive_before_tick:
                to_archive.append(ep)
            else:
                to_keep.append(ep)

        if not to_archive:
            return 0

        # Write archive
        if HAS_ORJSON:
            with open(archive_path, 'wb') as f:
                for ep in to_archive:
                    json_bytes = orjson.dumps(
                        ep,
                        option=orjson.OPT_APPEND_NEWLINE | orjson.OPT_SERIALIZE_NUMPY
                    )
                    f.write(json_bytes)

            # Rewrite main file with kept episodes
            with open(self.episodes_path, 'wb') as f:
                for ep in to_keep:
                    json_bytes = orjson.dumps(
                        ep,
                        option=orjson.OPT_APPEND_NEWLINE | orjson.OPT_SERIALIZE_NUMPY
                    )
                    f.write(json_bytes)
        else:
            import json
            with open(archive_path, 'w', encoding='utf-8') as f:
                for ep in to_archive:
                    f.write(json.dumps(ep, ensure_ascii=False) + '\n')
            with open(self.episodes_path, 'w', encoding='utf-8') as f:
                for ep in to_keep:
                    f.write(json.dumps(ep, ensure_ascii=False) + '\n')

        # Rebuild cache
        self._cache.clear()
        self._by_tick.clear()
        self._sorted_ticks.clear()
        self._load_from_disk()

        return len(to_archive)

    # =============================================================================
    # Associative Memory Integration (联想记忆集成)
    # =============================================================================

    def _get_or_create_associative_memory(self) -> Optional["AssociativeMemory"]:
        """获取或创建联想记忆"""
        if not self.enable_associative:
            return None

        if self._associative_memory is None:
            try:
                from .familiarity import create_associative_memory
                self._associative_memory = create_associative_memory()
            except ImportError:
                logger.warning("Associative memory not available")
                self.enable_associative = False

        return self._associative_memory

    def _add_to_associative(self, episode: EpisodeRecord):
        """添加episode到联想记忆"""
        assoc = self._get_or_create_associative_memory()
        if assoc is None:
            return

        # 获取状态快照中的情绪/压力信息
        state = getattr(episode, 'state_snapshot', {}) or {}
        mood = state.get('mood', 0.5)
        stress = state.get('stress', 0.2)

        # 添加到联想网络
        assoc.add_episode_memory(
            episode_id=episode.tick,
            tick=episode.tick,
            observation=getattr(episode, 'observation', None),
            action=getattr(episode, 'action', None),
            result=getattr(episode, 'result', None),
            mood=mood,
            stress=stress,
            salience=abs(getattr(episode, 'delta', 0.0)),
        )

    def retrieve_by_association(
        self,
        query: str,
        top_k: int = 5,
        mood: Optional[float] = None,
        stress: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """基于联想检索记忆

        Args:
            query: 查询文本
            top_k: 返回数量
            mood: 可选的情绪上下文
            stress: 可选的压力上下文

        Returns:
            检索结果列表
        """
        assoc = self._get_or_create_associative_memory()
        if assoc is None:
            return []

        return assoc.retrieve_by_association(
            query_text=query,
            top_k=top_k,
            mood=mood,
            stress=stress
        )

    def get_associative_memory(self) -> Optional["AssociativeMemory"]:
        """获取联想记忆实例"""
        return self._get_or_create_associative_memory()

    def enable_associative_memory(self, enable: bool = True):
        """启用或禁用联想记忆"""
        self.enable_associative = enable
        if not enable:
            self._associative_memory = None
