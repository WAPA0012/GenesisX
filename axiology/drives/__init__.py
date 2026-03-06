"""Drives System - 驱动力系统

驱动力系统负责产生"驱动力信号"，告诉 LLM "现在想要什么"。

这是价值系统 (axiology) 的一部分，负责将价值维度转化为具体的驱动力信号。

驱动力类型（5维价值系统）：
- curiosity: 好奇心驱动 - "我想探索新事物"
- competence: 胜任力驱动 - "我想变得更强"
- homeostasis: 稳态驱动 - "我需要平衡"
- attachment: 依恋驱动 - "我想和用户建立连接"
- safety: 安全驱动 - "我要保持安全，规避风险"
"""
from .base import BaseDrive, DriveSignal
from .curiosity import CuriosityDrive
from .competence import CompetenceDrive
from .homeostasis import HomeostasisDrive
from .attachment import AttachmentDrive
from .safety import SafetyDrive

__all__ = [
    "BaseDrive",
    "DriveSignal",
    "CuriosityDrive",
    "CompetenceDrive",
    "HomeostasisDrive",
    "AttachmentDrive",
    "SafetyDrive",
]
