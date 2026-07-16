"""Perception System - observation and context building."""
from .observer import observe_environment
from .context_builder import build_context

# Self perception (used by tool_executor)
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

# P4-36/43/45 已删除: novelty.py / signal_filter.py / command_parser.py / time_perception.py
# 四者均仅被 __init__.py re-export，无运行时消费者（life_loop 只用 observe_environment + build_context）

__all__ = [
    "observe_environment",
    "build_context",
    # Self perception
    "SelfPerception",
    "get_self_perception",
    "read_logs",
    "get_system_stats",
    "get_health_status",
]
