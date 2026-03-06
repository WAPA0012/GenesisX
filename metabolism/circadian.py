"""
Circadian Rhythm Manager: Daily Cycle and Offline Windows

Manages:
- 24-hour circadian rhythm simulation
- Optimal offline consolidation windows
- Energy/fatigue modulation

References:
- 代码大纲架构 metabolism/circadian.py
- Sleep-wake cycle research
"""

from datetime import datetime, time, timedelta, timezone
from typing import Dict, Any, Optional, Tuple
import math


class CircadianPhase:
    """Circadian phase constants"""
    MORNING = "morning"      # 06:00-12:00
    AFTERNOON = "afternoon"  # 12:00-18:00
    EVENING = "evening"      # 18:00-22:00
    NIGHT = "night"          # 22:00-06:00


class CircadianRhythm:
    """
    Manages circadian rhythm and offline consolidation windows.

    Simulates a 24-hour cycle affecting:
    - Energy levels
    - Optimal learning windows
    - Offline consolidation timing

    Supports both simulation time (tick-based) and real-world time:
    - Simulation mode: Use tick number to calculate simulated time
    - Real-time mode: Use system time (for live systems)
    """

    # Seconds per tick (configurable, default 1 second per tick)
    DEFAULT_SECONDS_PER_TICK = 1.0

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.cycle_length = config.get("cycle_length_hours", 24)
        self.start_time = datetime.now(timezone.utc)

        # Time mode: "realtime" or "simulation"
        self.time_mode = config.get("time_mode", "realtime")

        # Simulation parameters
        self.seconds_per_tick = config.get("seconds_per_tick", self.DEFAULT_SECONDS_PER_TICK)
        self.sim_start_hour = config.get("sim_start_hour", 6)  # Start at 6 AM

        # Capture simulation base time once at init (not on each call)
        self._sim_base_time = self.start_time.replace(
            hour=self.sim_start_hour,
            minute=0,
            second=0,
            microsecond=0
        )

        # Offline windows (when consolidation is most effective)
        self.offline_windows = config.get("offline_windows", [
            {"start": "01:00", "end": "04:00", "weight": 1.0},  # Deep sleep window
            {"start": "14:00", "end": "15:00", "weight": 0.6},  # Afternoon dip
        ])

    def _get_simulated_time(self, tick: int) -> datetime:
        """
        Get simulated time based on tick number.

        Args:
            tick: Current tick number

        Returns:
            Simulated datetime
        """
        # Calculate elapsed seconds in simulation
        elapsed_seconds = tick * self.seconds_per_tick

        # Use captured base time (fixed at init, no midnight discontinuity)
        sim_time = self._sim_base_time + timedelta(seconds=elapsed_seconds)

        return sim_time

    def _get_current_time(self, tick: Optional[int] = None) -> datetime:
        """
        Get appropriate current time based on time mode.

        Args:
            tick: Current tick (for simulation mode)

        Returns:
            Current datetime for circadian calculations
        """
        if self.time_mode == "simulation" and tick is not None:
            return self._get_simulated_time(tick)
        else:
            # Real-time mode: use system time
            return datetime.now(timezone.utc)

    def get_current_phase(self, tick: Optional[int] = None, current_time: Optional[datetime] = None) -> str:
        """
        Get current circadian phase.

        Args:
            tick: Current tick number (for simulation mode)
            current_time: Explicit current time (overrides mode)

        Returns:
            Phase name (morning/afternoon/evening/night)
        """
        if current_time is not None:
            time_to_use = current_time
        else:
            time_to_use = self._get_current_time(tick)

        hour = time_to_use.hour

        if 6 <= hour < 12:
            return CircadianPhase.MORNING
        elif 12 <= hour < 18:
            return CircadianPhase.AFTERNOON
        elif 18 <= hour < 22:
            return CircadianPhase.EVENING
        else:
            return CircadianPhase.NIGHT

    def get_energy_level(self, tick: Optional[int] = None, current_time: Optional[datetime] = None) -> float:
        """
        Calculate energy level based on circadian rhythm.

        Uses a cosine wave with peak at 10:00 and trough at 03:00.

        Args:
            tick: Current tick number (for simulation mode)
            current_time: Explicit current time (overrides mode)

        Returns:
            Energy level [0, 1]
        """
        if current_time is not None:
            time_to_use = current_time
        else:
            time_to_use = self._get_current_time(tick)

        # Hours since midnight
        hours_since_midnight = time_to_use.hour + time_to_use.minute / 60.0

        # Peak at 10:00 (10 hours), trough at 03:00 (3 hours)
        # Shift cosine wave: peak at 10, period = 24
        phase_shift = 10.0  # Peak at 10:00

        # Cosine wave: cos(2π * (t - phase_shift) / period)
        angle = 2 * math.pi * (hours_since_midnight - phase_shift) / 24.0

        # Map [-1, 1] to [0.3, 1.0] (never fully zero)
        energy = 0.65 + 0.35 * math.cos(angle)

        return max(0.3, min(1.0, energy))

    def is_offline_window(self, tick: Optional[int] = None, current_time: Optional[datetime] = None) -> Tuple[bool, float]:
        """
        Check if current time is in an offline consolidation window.

        Args:
            tick: Current tick number (for simulation mode)
            current_time: Explicit current time (overrides mode)

        Returns:
            (is_window, weight) tuple
        """
        if current_time is not None:
            time_to_use = current_time
        else:
            time_to_use = self._get_current_time(tick)

        current_hour = time_to_use.hour
        current_minute = time_to_use.minute
        current_total_minutes = current_hour * 60 + current_minute

        for window in self.offline_windows:
            start_time = self._parse_time(window["start"])
            end_time = self._parse_time(window["end"])

            start_minutes = start_time.hour * 60 + start_time.minute
            end_minutes = end_time.hour * 60 + end_time.minute

            # Handle overnight windows
            if end_minutes < start_minutes:
                # Window crosses midnight
                if current_total_minutes >= start_minutes or current_total_minutes <= end_minutes:
                    return True, window["weight"]
            else:
                if start_minutes <= current_total_minutes <= end_minutes:
                    return True, window["weight"]

        return False, 0.0

    def should_consolidate(
        self,
        fatigue: float,
        meaning_gap: float,
        tick: Optional[int] = None,
        current_time: Optional[datetime] = None
    ) -> bool:
        """
        Determine if offline consolidation should be triggered.

        Args:
            fatigue: Current fatigue level [0, 1]
            meaning_gap: Current meaning gap [0, 1]
            tick: Current tick number (for simulation mode)
            current_time: Explicit current time (overrides mode)

        Returns:
            True if consolidation should run
        """
        is_window, window_weight = self.is_offline_window(tick, current_time)

        if not is_window:
            return False

        # Trigger if fatigue or meaning gap high
        threshold = self.config.get("consolidation_threshold", 0.6)

        # Weight by window importance
        effective_fatigue = fatigue * window_weight
        effective_gap = meaning_gap * window_weight

        return effective_fatigue > threshold or effective_gap > threshold

    def get_optimal_consolidation_duration(
        self,
        fatigue: float,
        budget_tokens: int
    ) -> int:
        """
        Calculate optimal consolidation duration in ticks.

        Args:
            fatigue: Current fatigue level [0, 1]
            budget_tokens: Available token budget

        Returns:
            Number of ticks to consolidate
        """
        base_duration = self.config.get("base_consolidation_ticks", 10)

        # Scale by fatigue (higher fatigue = longer consolidation)
        duration = int(base_duration * (0.5 + 0.5 * fatigue))

        # Cap by budget (assume ~100 tokens per tick)
        max_ticks_by_budget = budget_tokens // 100

        return min(duration, max_ticks_by_budget)

    @staticmethod
    def _parse_time(time_str: str) -> time:
        """Parse time string 'HH:MM' to time object"""
        hour, minute = map(int, time_str.split(":"))
        return time(hour=hour, minute=minute)

    def get_fatigue_recovery_rate(self, tick: Optional[int] = None, current_time: Optional[datetime] = None) -> float:
        """
        Get fatigue recovery rate based on circadian phase.

        Args:
            tick: Current tick number (for simulation mode)
            current_time: Explicit current time (overrides mode)

        Returns:
            Recovery rate multiplier [0.5, 2.0]
        """
        phase = self.get_current_phase(tick, current_time)

        # Recovery faster during night/early morning
        recovery_rates = {
            CircadianPhase.NIGHT: 2.0,
            CircadianPhase.MORNING: 1.5,
            CircadianPhase.AFTERNOON: 0.8,
            CircadianPhase.EVENING: 1.0,
        }

        return recovery_rates.get(phase, 1.0)
