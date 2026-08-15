"""Episodic Memory - event-sourcing view of episodes."""
from typing import List, Dict, Any, Optional, Iterator, TYPE_CHECKING
from pathlib import Path
from common.models import EpisodeRecord
from common.jsonl import JSONLWriter, read_jsonl
from common.logger import get_logger
import bisect
import shutil
from collections import deque

logger = get_logger(__name__)

# 延迟导入联想记忆
if TYPE_CHECKING:
    from .familiarity import AssociativeMemory


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
        enable_associative: bool = True,
        max_rebuild_episodes: int = 1000
    ):
        """Initialize episodic memory.

        Args:
            episodes_path: Path to episodes.jsonl (if None, in-memory only)
            max_cache_size: Maximum number of episodes to keep in cache
            enable_associative: Enable associative memory (联想记忆)
            max_rebuild_episodes: P3-15 重启时重建联想网络的最大 episode 数（性能保护）。
                默认 1000（避免 50000 条全重建的 50-250s 延迟）。重建优先选高 |delta|
                的 episode（按 RPE 幅值排序），而非纯时间窗——这样保留高价值记忆的联想链接。
        """
        self.max_rebuild_episodes = max_rebuild_episodes
        self.episodes_path = episodes_path
        self._cache: deque = deque()  # Ordered episodes for iteration/eviction
        self._by_tick: Dict[int, EpisodeRecord] = {}  # tick -> episode (O(1) lookup)
        self._sorted_ticks: List[int] = []  # Sorted list of ticks for binary search
        self.max_cache_size = max_cache_size

        # 联想记忆
        self.enable_associative = enable_associative
        self._associative_memory: Optional["AssociativeMemory"] = None

        # P3-1/P3-2 修复：常驻 JSONLWriter（open 一次写多次），替代原每 tick 一次
        # open/append/close 的手写 orjson/json 代码。序列化语义与原实现等价（同 orjson
        # option），且额外获得 fsync 崩溃恢复保证。life_loop shutdown 时调 close()。
        self._writer: Optional[JSONLWriter] = None
        if episodes_path:
            self._writer = JSONLWriter(episodes_path)
            self._writer.open()

        if episodes_path and episodes_path.exists():
            self._load_from_disk()

    def _load_from_disk(self):
        """Load episodes from disk into cache."""
        for record in read_jsonl(self.episodes_path):
            try:
                episode = EpisodeRecord(**record)
                self._cache.append(episode)
                # 同 tick 多条记录先到先得（如 task_completed 固化总结与真实 episode 同 tick），
                # 保证 get_by_tick 拿到的是真实经历而非派生总结
                self._by_tick.setdefault(episode.tick, episode)
                self._sorted_ticks.append(episode.tick)
            except Exception as e:
                logger.warning(f"Failed to load episode: {e}")

        # Sort ticks for binary search
        self._sorted_ticks.sort()

        # P3-15 修复：重建联想网络（原 import_state 是 pass，重启丢失全部联想链接）。
        # 路径：重放历史 episodes 重建联想图（复用 _add_to_associative 逻辑）。
        # 性能保护：只重建有限的 episodes（默认 1000，可配 max_rebuild_episodes），避免
        # 50000 条全重建的 50-250s 延迟。
        # P3-15 改进：选择策略从"纯时间窗（最近 N 条）"改为"高价值优先"——按 |delta|
        # （RPE 幅值）降序排序后取 top N，这样高冲击记忆的联想链接优先恢复，比纯时间窗
        # 更有意义。时间相近性仍保留（同 tick 区间的共现关系仍能建立）。
        if self.enable_associative and len(self._cache) > 0:
            assoc = self._get_or_create_associative_memory()
            if assoc is not None:
                all_eps = list(self._cache)
                # 按 |delta| 降序选 top N（高 RPE 幅值 = 高价值记忆）
                all_eps_sorted = sorted(all_eps, key=lambda e: abs(getattr(e, 'delta', 0.0)), reverse=True)
                episodes_to_rebuild = all_eps_sorted[:self.max_rebuild_episodes]
                rebuilt = 0
                for episode in episodes_to_rebuild:
                    try:
                        self._add_to_associative(episode)
                        rebuilt += 1
                    except Exception:
                        pass  # 个别 episode 重建失败不阻断
                if rebuilt > 0:
                    logger.info(f"联想网络重建: {rebuilt} episodes (按 |delta| 选 top {self.max_rebuild_episodes}) → {len(assoc.network._nodes)} nodes")

    def append(self, episode: EpisodeRecord):
        """Append new episode to memory and persist to disk (修复 H22).

        Args:
            episode: Episode to append
        """
        self._cache.append(episode)
        # 先到先得：工作记忆固化总结与同 tick 的真实 episode 共存时，真实经历保留索引位
        self._by_tick.setdefault(episode.tick, episode)

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
        """Persist a single episode to disk via the resident JSONLWriter.

        Args:
            episode: Episode to persist
        """
        if not self._writer:
            logger.error(f"No writer, cannot persist episode {episode.tick}")
            return  # 没有设置路径，跳过持久化

        logger.debug(f"Persisting episode {episode.tick} to {self.episodes_path}")
        try:
            self._writer.write(episode.model_dump())
            logger.debug(f"Successfully persisted episode {episode.tick}")
        except Exception as e:
            # 持久化失败不应该阻塞主循环，但需要记录
            logger.error(f"Failed to persist episode {episode.tick}: {e}", exc_info=True)

    def close(self):
        """Close the resident JSONLWriter. Called by life_loop.shutdown()."""
        if self._writer:
            self._writer.close()
            self._writer = None

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

    def query_by_rpe_magnitude(self, threshold: float = 0.7, limit: int = 20) -> List[EpisodeRecord]:
        """Query episodes by RPE magnitude (|delta|).

        Note: This uses raw |delta| (RPE magnitude) as the filter, NOT the paper's
        salience formula (memory/salience.py:compute_salience which combines
        a_δ·|δ| + a_u·competence_gap + a_n·curiosity_gap with sigmoid normalization).
        The two are different physical quantities.

        Renamed from query_high_salience (P3-19): the old name implied it used the
        paper Sal formula, which was misleading.

        Args:
            threshold: Minimum |delta| to keep
            limit: Maximum episodes to return

        Returns:
            List of episodes sorted by |delta| descending
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

    def prune_disk_by_delta_magnitude(
        self,
        min_delta_to_keep: float = 0.3,
        keep_recent_ratio: float = 0.15,
        backup: bool = True
    ) -> Dict[str, int]:
        """Prune disk file by removing low-impact episodes (by |delta|, NOT paper Sal formula).

        P3-12 命名澄清：原名 prune_disk_by_salience / 参数 salience_threshold 误导——
        实际用的是原始 |delta|（RPE 幅值），与论文 §3.10.4 的 Sal 公式
        （a_δ·|δ| + a_u·(1-Prog) + a_n·Novelty，sigmoid 归一化）无关。
        两阶段用不同指标是合理设计（采样用 Sal 选高价值进 schema，剪枝用 |delta| 清
        低冲击出磁盘），此处只是把命名改清楚。

        Keeps:
        - Episodes with |delta| > min_delta_to_keep
        - Most recent keep_recent_ratio of episodes

        Args:
            min_delta_to_keep: Minimum |delta| (RPE magnitude) to keep
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
            if abs(delta) > min_delta_to_keep:
                kept.append(ep)
            else:
                pruned += 1

        # Write back kept episodes via resident writer's rewrite (non-append mode)
        if self._writer:
            self._writer.rewrite(kept)
        else:
            # Fallback: 无常驻 writer（理论上不会发生，episodes_path 设了就有 writer）
            logger.warning("No resident writer during prune; skipping disk rewrite")

        # Rebuild cache
        self._cache.clear()
        self._by_tick.clear()
        self._sorted_ticks.clear()
        self._load_from_disk()

        return {"total": total, "kept": len(kept), "pruned": pruned}

    # P3-12: 向后兼容别名（原方法名误导，已改名。保留别名防外部调用方）
    def prune_disk_by_salience(self, salience_threshold: float = 0.3, **kwargs):
        """Deprecated alias for prune_disk_by_delta_magnitude (P3-12 rename)."""
        return self.prune_disk_by_delta_magnitude(min_delta_to_keep=salience_threshold, **kwargs)

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
