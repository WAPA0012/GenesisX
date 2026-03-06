"""Curiosity Drive - 好奇心驱动力

提供好奇心驱动力信号，告诉 LLM "想要探索新事物"。

这是价值系统的一部分，对应价值维度：curiosity
"""
from typing import Dict, Any, Set
from .base import BaseDrive, DriveSignal


class CuriosityDrive(BaseDrive):
    """好奇心驱动力

    驱动数字生命去探索、学习新事物。
    对应价值维度：curiosity
    """

    def __init__(self):
        super().__init__(
            name="好奇心",
            value_dimension="curiosity"
        )
        self._explored_topics: Set[str] = set()
        self._novelty_history = []

    def generate_drive_signal(
        self,
        state: Dict[str, Any],
        context: Dict[str, Any]
    ) -> DriveSignal:
        """生成好奇心驱动力信号"""
        # 获取状态
        gaps = state.get("gaps", {})
        gap = gaps.get("curiosity", 0.0)
        weights = state.get("weights", {})
        weight = weights.get("curiosity", 0.25)
        mood = state.get("mood", 0.5)
        energy = state.get("energy", 0.5)
        stress = state.get("stress", 0.0)
        boredom = state.get("boredom", 0.0)

        # 计算强度
        base_intensity = gap * weight
        boredom_bonus = boredom * 0.4
        stress_penalty = stress * 0.2
        energy_factor = energy * 0.3

        intensity = min(1.0, max(0.0, base_intensity + boredom_bonus - stress_penalty + energy_factor))

        # 生成描述
        if intensity > 0.8:
            if boredom > 0.6:
                description = "非常渴望探索新事物，感觉有些无聊，需要新鲜刺激"
            else:
                description = "对未知充满强烈好奇，想要深入了解某个领域"
        elif intensity > 0.5:
            if boredom > 0.4:
                description = "有点无聊，想找点新东西学习或探索"
            else:
                description = "对某些话题感兴趣，愿意了解更多"
        elif intensity > 0.3:
            description = "有轻微的好奇心，如果有趣的话题可以探索一下"
        else:
            description = "当前好奇心较低，暂时满足于已知的知识"

        signal = DriveSignal(
            name=self.name,
            intensity=intensity,
            description=description,
            context={
                "gap": gap,
                "weight": weight,
                "boredom": boredom,
            },
            priority=weight * intensity
        )

        self._last_signal = signal
        return signal
