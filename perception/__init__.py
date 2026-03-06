"""Perception System - observation and context building."""
from .observer import observe_environment
from .context_builder import build_context
from .novelty import NoveltyDetector
from .signal_filter import SignalFilter, FilteredSignal, Signal  # Signal is alias for backward compatibility
from .command_parser import CommandParser

# 新增感知能力
try:
    from .time_perception import (
        TimePerception,
        get_time_perception,
        get_current_time,
        get_time_info,
    )
except ImportError:
    TimePerception = None
    get_time_perception = None
    get_current_time = None
    get_time_info = None

try:
    from .self_perception import (
        SelfPerception,
        get_self_perception,
        read_logs,
        get_system_stats,
        get_health_status,
    )
except ImportError:
    SelfPerception = None
    get_self_perception = None
    read_logs = None
    get_system_stats = None
    get_health_status = None

__all__ = [
    "observe_environment",
    "build_context",
    "NoveltyDetector",
    "SignalFilter",
    "FilteredSignal",
    "Signal",  # Backward compatibility alias
    "CommandParser",
    # Time perception
    "TimePerception",
    "get_time_perception",
    "get_current_time",
    "get_time_info",
    # Self perception
    "SelfPerception",
    "get_self_perception",
    "read_logs",
    "get_system_stats",
    "get_health_status",
]
