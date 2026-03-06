"""Handlers - LifeLoop 功能拆分模块

将 LifeLoop 中的大型方法拆分为独立的处理器类，
提高代码可维护性和可测试性。

模块:
- ActionExecutor: 行为执行器 (最大，~700行)
- ChatHandler: 聊天处理器 (~350行)
- CaretakerMode: 管家模式 (~50行)
- GapDetectorMixin: 能力缺口检测 (~300行)
"""

from .action_executor import ActionExecutor
from .chat_handler import ChatHandler
from .caretaker_mode import CaretakerMode
from .gap_detector import GapDetectorMixin

__all__ = [
    "ActionExecutor",
    "ChatHandler",
    "CaretakerMode",
    "GapDetectorMixin",
]
