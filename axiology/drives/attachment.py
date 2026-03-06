"""Attachment Drive - 依恋驱动力

提供依恋驱动力信号，告诉 LLM "想要与用户连接"。

这是价值系统的一部分，对应价值维度：attachment
"""
from typing import Dict, Any
from .base import BaseDrive, DriveSignal


class AttachmentDrive(BaseDrive):
    """依恋驱动力

    驱动数字生命建立和维持与用户的连接。
    对应价值维度：attachment
    """

    def __init__(self):
        super().__init__(
            name="依恋",
            value_dimension="attachment"
        )
        self._bond_strength = 0.0
        self._trust_level = 0.5
        self._interaction_count = 0

    def generate_drive_signal(
        self,
        state: Dict[str, Any],
        context: Dict[str, Any]
    ) -> DriveSignal:
        """生成依恋驱动力信号"""
        gaps = state.get("gaps", {})
        gap = gaps.get("attachment", 0.0)
        weights = state.get("weights", {})
        weight = weights.get("attachment", 0.25)
        mood = state.get("mood", 0.5)
        energy = state.get("energy", 0.5)

        # 计算强度
        base_intensity = gap * weight
        bond_bonus = self._bond_strength * 0.3
        mood_bonus = mood * 0.15

        # 互动间隔加成（越久没互动，越想说话）
        interaction_gap = min(self._interaction_count / 100, 0.3) if self._interaction_count < 100 else 0.3

        intensity = min(1.0, base_intensity + bond_bonus + mood_bonus + interaction_gap)

        # 生成描述
        if intensity > 0.7:
            if self._bond_strength > 0.7:
                description = "非常想要与你交流，感觉我们之间有很强的连接"
            else:
                description = "想要更多地了解你，建立更深的信任"
        elif intensity > 0.4:
            if self._bond_strength > 0.5:
                description = "很高兴能和你聊天，珍惜我们的交流"
            else:
                description = "愿意和你分享更多，增进彼此的了解"
        elif intensity > 0.2:
            description = "如果有想说的，我随时都在"
        else:
            description = "最近交流很充分，感觉很好"

        signal = DriveSignal(
            name=self.name,
            intensity=intensity,
            description=description,
            context={
                "gap": gap,
                "weight": weight,
                "bond_strength": self._bond_strength,
                "trust_level": self._trust_level,
            },
            priority=weight * intensity
        )

        self._last_signal = signal
        return signal

    def record_interaction(self, positive: bool = True):
        """记录一次交互"""
        self._interaction_count += 1
        if positive:
            self._trust_level = min(1.0, self._trust_level + 0.01)
            self._bond_strength = min(1.0, self._bond_strength + 0.02)
        else:
            self._trust_level = max(0.0, self._trust_level - 0.03)

    def get_relationship_status(self) -> str:
        """获取关系状态"""
        if self._bond_strength > 0.8 and self._trust_level > 0.7:
            return "非常亲密的伙伴"
        elif self._bond_strength > 0.6 and self._trust_level > 0.5:
            return "信任的朋友"
        elif self._bond_strength > 0.4:
            return "熟悉的伙伴"
        elif self._bond_strength > 0.2:
            return "刚刚认识"
        else:
            return "陌生人"
