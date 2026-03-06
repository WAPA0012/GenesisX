"""Signal Bus - Half-life decay signals for Genesis X.

Implements temporary signals that decay over time, useful for:
- Short-term mood adjustments
- Transient priorities
- Event-driven modulation
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone


@dataclass
class Signal:
    """A time-decaying signal.

    Attributes:
        value: Current signal value
        start_time: When the signal was created
        half_life: Time for signal to halve (in seconds)
        decay_type: Type of decay ("exponential", "linear")
    """
    value: float
    # 修复 M49: 使用 timezone-aware UTC datetime
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    half_life: float = 3600.0  # Default: 1 hour
    decay_type: str = "exponential"

    def age(self) -> float:
        """Get age of signal in seconds."""
        return (datetime.now(timezone.utc) - self.start_time).total_seconds()

    def decay(self, age: Optional[float] = None) -> float:
        """Compute decayed value.

        Args:
            age: Age in seconds (uses current age if None)

        Returns:
            Decayed signal value
        """
        if age is None:
            age = self.age()

        if self.decay_type == "exponential":
            # Exponential decay: value * (0.5)^(age / half_life)
            decay_factor = 0.5 ** (age / self.half_life)
            return self.value * decay_factor
        elif self.decay_type == "linear":
            # Linear decay to zero over 2 * half_life
            decay_factor = max(0.0, 1.0 - age / (2.0 * self.half_life))
            return self.value * decay_factor
        else:
            return self.value

    def is_expired(self, threshold: float = 0.01) -> bool:
        """Check if signal has decayed below threshold.

        Args:
            threshold: Minimum value to consider signal active

        Returns:
            True if signal is essentially zero
        """
        return self.decay() < threshold


class SignalBus:
    """Manages multiple time-decaying signals.

    Provides a central registry for transient signals that
    automatically decay over time.

    修复 M15+: 使用模拟时间偏移量而非修改 start_time，避免序列化/反序列化问题。
    """

    def __init__(self):
        """Initialize signal bus."""
        self._signals: Dict[str, Signal] = {}
        # 模拟时间偏移量（秒），用于模拟时间推进而不修改 start_time
        self._sim_time_offset: float = 0.0

    def _get_signal_age(self, signal: Signal) -> float:
        """Get signal age considering simulation time offset.

        Args:
            signal: Signal to get age for

        Returns:
            Age in seconds (including simulation offset)
        """
        real_age = (datetime.now(timezone.utc) - signal.start_time).total_seconds()
        return real_age + self._sim_time_offset

    def set(
        self,
        key: str,
        value: float,
        half_life: float = 3600.0,
        decay_type: str = "exponential"
    ) -> None:
        """Set a new signal.

        Args:
            key: Signal identifier
            value: Initial signal value
            half_life: Half-life in seconds
            decay_type: Type of decay
        """
        self._signals[key] = Signal(
            value=value,
            half_life=half_life,
            decay_type=decay_type
        )

    def get(self, key: str, default: float = 0.0) -> float:
        """Get current (decayed) signal value.

        Note: This is a pure read operation. Expired signals are cleaned up
        separately via cleanup_expired() or tick(), not during get().

        Args:
            key: Signal identifier
            default: Value if signal doesn't exist

        Returns:
            Current decayed value
        """
        if key not in self._signals:
            return default

        signal = self._signals[key]
        # 使用考虑模拟时间偏移的 age 计算
        age = self._get_signal_age(signal)
        decayed = signal.decay(age)

        # Return decayed value even if below threshold;
        # cleanup is done explicitly via cleanup_expired() / tick()
        return decayed

    def add(self, key: str, delta: float) -> None:
        """Add to existing signal or create new one.

        If the signal already exists, its value is updated in-place
        (preserving start_time and half_life). If not, a new signal
        is created with default parameters.

        Args:
            key: Signal identifier
            delta: Amount to add (can be negative)
        """
        if key in self._signals:
            signal = self._signals[key]
            # Compute current decayed value considering sim time offset
            age = self._get_signal_age(signal)
            signal.value = signal.decay(age) + delta
            signal.start_time = datetime.now(timezone.utc)
            # 重置偏移量对此信号的影响（因为它现在有了新的 start_time）
            # 注意：这是简化处理，更精确的做法是单独跟踪每个信号的偏移
        else:
            self._signals[key] = Signal(value=delta)

    def clear(self, key: str) -> None:
        """Remove a signal.

        Args:
            key: Signal identifier
        """
        self._signals.pop(key, None)

    def clear_all(self) -> None:
        """Remove all signals."""
        self._signals.clear()

    def cleanup_expired(self, threshold: float = 0.01) -> int:
        """Remove expired signals.

        Args:
            threshold: Minimum value to consider signal active

        Returns:
            Number of signals removed
        """
        expired_keys = []
        for key, signal in self._signals.items():
            # 使用考虑模拟时间偏移的 age 计算
            age = self._get_signal_age(signal)
            if signal.decay(age) < threshold:
                expired_keys.append(key)

        for key in expired_keys:
            del self._signals[key]

        return len(expired_keys)

    def tick(self, dt: float) -> None:
        """Advance simulation time by dt seconds and decay signals.

        修复 M15+: 使用模拟时间偏移量而非修改 start_time。
        这样可以避免序列化/反序列化后的时区问题。

        Args:
            dt: Simulation time delta in seconds
        """
        # 累积模拟时间偏移量，而不是修改 start_time
        if dt > 0:
            self._sim_time_offset += dt

        self.cleanup_expired()

    def get_all(self) -> Dict[str, float]:
        """Get all current (decayed) signal values.

        Returns:
            Dict of signal key to current value
        """
        result = {}
        for key in list(self._signals.keys()):
            result[key] = self.get(key)
        return result

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict.

        Returns:
            Dict representation of all signals including sim time offset
        """
        return {
            "_sim_time_offset": self._sim_time_offset,
            "signals": {
                key: {
                    "value": signal.value,
                    "start_time": signal.start_time.isoformat(),
                    "half_life": signal.half_life,
                    "decay_type": signal.decay_type,
                }
                for key, signal in self._signals.items()
            }
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Restore from dict.

        修复 M15+: 支持模拟时间偏移量的反序列化，并确保 datetime 是 timezone-aware 的。

        Args:
            data: Dict representation from to_dict()
        """
        # 恢复模拟时间偏移量
        self._sim_time_offset = data.get("_sim_time_offset", 0.0)

        # 恢复信号
        signals_data = data.get("signals", data)  # 兼容旧格式
        for key, signal_data in signals_data.items():
            if key == "_sim_time_offset":
                continue  # 跳过元数据字段

            start_time_str = signal_data["start_time"]
            # 确保 datetime 是 timezone-aware 的
            start_time = datetime.fromisoformat(start_time_str)
            if start_time.tzinfo is None:
                # 如果是 naive datetime，假设它是 UTC 时间
                start_time = start_time.replace(tzinfo=timezone.utc)

            self._signals[key] = Signal(
                value=signal_data["value"],
                start_time=start_time,
                half_life=signal_data["half_life"],
                decay_type=signal_data.get("decay_type", "exponential")
            )
