"""
Signal Filter: Input Overload Protection with Priority Queue

Implements:
- Priority-based signal filtering
- Overload detection and throttling
- Signal deduplication

References:
- 代码大纲架构 perception/signal_filter.py
- 论文 3.2 SignalBus with half-life decay
"""

from typing import Dict, Any, List, Optional
from collections import deque
import time

from common.hashing import hash_any

# 明确导出的类名，避免与 core/stores/signals.py 中的 Signal 类冲突
# Signal 是 FilteredSignal 的别名，用于向后兼容
Signal = None  # Will be defined after FilteredSignal class

__all__ = ["FilteredSignal", "SignalFilter", "Signal"]


class FilteredSignal:
    """Signal structure with priority and metadata.

    注意: 此类名为 FilteredSignal，以避免与 core/stores/signals.py 中的 Signal 类冲突。
    如需使用核心 Signal 类，请从 core.stores.signals 导入。
    """

    def __init__(
        self,
        signal_id: str,
        signal_type: str,
        data: Any,
        priority: float = 0.5,
        timestamp: Optional[float] = None,
    ):
        self.signal_id = signal_id
        self.signal_type = signal_type
        self.data = data
        self.priority = priority
        self.timestamp = timestamp or time.time()

        # Calculate content hash for deduplication
        self.content_hash = hash_any(data, truncate=16)

    def __lt__(self, other):
        """Compare by priority (higher priority first)"""
        return self.priority > other.priority


# Backward compatibility alias
Signal = FilteredSignal


class SignalFilter:
    """
    Input overload protection with priority queue.

    Features:
    - Priority-based filtering
    - Deduplication within time window
    - Throttling when overloaded
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Max signals per tick
        self.max_signals_per_tick = config.get("max_signals_per_tick", 10)

        # Deduplication window (seconds)
        self.dedup_window = config.get("dedup_window_seconds", 5.0)

        # Recent signals for deduplication
        self.recent_signals: deque = deque(maxlen=100)

        # Priority thresholds
        self.min_priority = config.get("min_priority", 0.1)

        # Overload detection
        self.overload_threshold = config.get("overload_threshold", 0.8)
        self.signal_buffer: List[FilteredSignal] = []

    def add_signal(self, signal: FilteredSignal) -> bool:
        """
        Add signal to filter.

        Args:
            signal: Signal to add

        Returns:
            True if signal accepted, False if filtered out
        """
        # Check minimum priority
        if signal.priority < self.min_priority:
            return False

        # Check for duplicates
        if self._is_duplicate(signal):
            return False

        # Add to buffer
        self.signal_buffer.append(signal)
        self.recent_signals.append({
            "hash": signal.content_hash,
            "timestamp": signal.timestamp,
        })

        return True

    def get_top_signals(self, max_count: Optional[int] = None) -> List[FilteredSignal]:
        """
        Get top priority signals for processing.

        Args:
            max_count: Max signals to return (default: max_signals_per_tick)

        Returns:
            List of signals sorted by priority
        """
        if max_count is None:
            max_count = self.max_signals_per_tick

        # Sort by priority (descending)
        sorted_signals = sorted(
            self.signal_buffer,
            key=lambda s: s.priority,
            reverse=True
        )

        # Return top N
        return sorted_signals[:max_count]

    def clear_processed_signals(self, signals: List[FilteredSignal]):
        """Remove processed signals from buffer"""
        processed_ids = {s.signal_id for s in signals}
        self.signal_buffer = [
            s for s in self.signal_buffer
            if s.signal_id not in processed_ids
        ]

    def is_overloaded(self) -> bool:
        """
        Check if signal buffer is overloaded.

        Returns:
            True if overloaded
        """
        buffer_ratio = len(self.signal_buffer) / max(1, self.max_signals_per_tick * 2)
        return buffer_ratio >= self.overload_threshold

    def get_overload_ratio(self) -> float:
        """
        Get current overload ratio [0, 1+].

        Returns:
            Overload ratio
        """
        max_buffer = self.max_signals_per_tick * 2
        return len(self.signal_buffer) / max(1, max_buffer)

    def _is_duplicate(self, signal: FilteredSignal) -> bool:
        """
        Check if signal is duplicate of recent signal.

        Args:
            signal: Signal to check

        Returns:
            True if duplicate
        """
        current_time = time.time()

        for recent in self.recent_signals:
            # Check if within deduplication window
            if current_time - recent["timestamp"] > self.dedup_window:
                continue

            # Check content hash
            if recent["hash"] == signal.content_hash:
                return True

        return False

    def adjust_priority_threshold(self, factor: float):
        """
        Dynamically adjust minimum priority threshold.

        Args:
            factor: Adjustment factor (1.0 = no change, >1.0 = raise threshold)
        """
        self.min_priority = min(1.0, self.min_priority * factor)

    def get_buffer_stats(self) -> Dict[str, Any]:
        """Get statistics about signal buffer"""
        if not self.signal_buffer:
            return {
                "count": 0,
                "avg_priority": 0.0,
                "overloaded": False,
            }

        priorities = [s.priority for s in self.signal_buffer]

        return {
            "count": len(self.signal_buffer),
            "avg_priority": sum(priorities) / len(priorities),
            "max_priority": max(priorities),
            "min_priority": min(priorities),
            "overloaded": self.is_overloaded(),
            "overload_ratio": self.get_overload_ratio(),
        }

    def reset(self):
        """Clear all buffers"""
        self.signal_buffer.clear()
        self.recent_signals.clear()
