"""Base Drive - 驱动力基类

驱动力是价值系统的一部分，负责产生"驱动力信号"，
告诉 LLM "现在想要什么"。

驱动力与价值维度的对应关系：
- curiosity: 好奇心驱动 - "我想探索新事物"
- competence: 胜任力驱动 - "我想变得更强"
- homeostasis: 稳态驱动 - "我需要平衡"
- attachment: 依恋驱动 - "我想和用户建立连接"
"""
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class DriveSignal:
    """驱动力信号 - 告诉 LLM "现在想要什么"

    Attributes:
        name: 驱动力名称
        intensity: 强度 (0-1)
        description: 描述 (给 LLM 理解)
        context: 额外上下文
        priority: 优先级 (0-1)
    """
    name: str                          # 驱动力名称
    intensity: float                   # 强度 (0-1)
    description: str                   # 描述 (给 LLM 理解)
    context: Dict[str, Any] = field(default_factory=dict)  # 额外上下文
    priority: float = 0.5              # 优先级 (0-1)

    def to_prompt(self) -> str:
        """转换为给 LLM 的提示文本"""
        intensity_desc = self._intensity_to_desc()
        return f"[{self.name}] {intensity_desc}: {self.description}"

    def _intensity_to_desc(self) -> str:
        """强度描述"""
        if self.intensity >= 0.9:
            return "非常强烈"
        elif self.intensity >= 0.7:
            return "强烈"
        elif self.intensity >= 0.5:
            return "中等"
        elif self.intensity >= 0.3:
            return "微弱"
        else:
            return "几乎无"


class BaseDrive(ABC):
    """驱动力基类

    所有驱动力必须继承此类。驱动力有一个核心功能：
    - generate_drive_signal() - 生成驱动力信号（必须实现）
    """

    def __init__(self, name: str, value_dimension: str = None):
        """初始化驱动力

        Args:
            name: 驱动力名称
            value_dimension: 对应的价值维度 (curiosity/competence/homeostasis/attachment)
        """
        self.name = name
        self.value_dimension = value_dimension
        self.enabled = True
        self._last_signal = None

    @abstractmethod
    def generate_drive_signal(
        self,
        state: Dict[str, Any],
        context: Dict[str, Any]
    ) -> DriveSignal:
        """生成驱动力信号

        这是驱动力的核心功能，告诉 LLM "现在想要什么"。

        Args:
            state: 当前状态 (fields, gaps, weights 等)
            context: 当前上下文

        Returns:
            DriveSignal: 驱动力信号
        """
        pass

    def set_enabled(self, enabled: bool):
        """启用或禁用驱动力"""
        self.enabled = enabled

    def get_last_signal(self) -> Optional[DriveSignal]:
        """获取上次生成的驱动力信号"""
        return self._last_signal
