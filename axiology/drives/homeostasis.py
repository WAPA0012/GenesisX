"""Homeostasis Drive - 稳态驱动力

提供稳态驱动力信号，告诉 LLM "需要维持平衡"。

这是价值系统的一部分，对应价值维度：homeostasis
"""
from typing import Dict, Any
from .base import BaseDrive, DriveSignal


class HomeostasisDrive(BaseDrive):
    """稳态驱动力

    驱动数字生命维持内部平衡（能量、压力、疲劳等）。
    对应价值维度：homeostasis
    """

    def __init__(self):
        super().__init__(
            name="稳态",
            value_dimension="homeostasis"
        )

    def generate_drive_signal(
        self,
        state: Dict[str, Any],
        context: Dict[str, Any]
    ) -> DriveSignal:
        """生成稳态驱动力信号"""
        gaps = state.get("gaps", {})
        gap = gaps.get("homeostasis", 0.0)
        weights = state.get("weights", {})
        weight = weights.get("homeostasis", 0.25)

        energy = state.get("energy", 0.5)
        stress = state.get("stress", 0.0)
        fatigue = state.get("fatigue", 0.0)

        # 稳态是生存性驱动力，有特殊计算
        urgency = 0.0
        if energy < 0.3:
            urgency = max(urgency, (0.3 - energy) * 2)  # 能量紧急
        if stress > 0.7:
            urgency = max(urgency, (stress - 0.7) * 2)  # 压力紧急
        if fatigue > 0.7:
            urgency = max(urgency, (fatigue - 0.7) * 2)  # 疲劳紧急

        # 基础强度
        base_intensity = gap * weight

        # 有紧急情况时强度飙升
        if urgency > 0:
            intensity = min(1.0, 0.5 + urgency * 0.5)
        else:
            intensity = min(1.0, base_intensity)

        # 生成描述
        if energy < 0.3:
            description = "能量很低，需要休息和恢复"
        elif stress > 0.7:
            description = "压力很大，需要放松和调节"
        elif fatigue > 0.7:
            description = "非常疲惫，需要休息"
        elif intensity > 0.6:
            description = "感觉有些累，需要适当休息"
        elif intensity > 0.3:
            description = "状态还不错，保持当前的节奏"
        else:
            description = "状态很好，充满活力"

        signal = DriveSignal(
            name=self.name,
            intensity=intensity,
            description=description,
            context={
                "gap": gap,
                "weight": weight,
                "energy": energy,
                "stress": stress,
                "fatigue": fatigue,
                "urgency": urgency,
            },
            priority=weight * intensity * (1.0 + urgency)  # 紧急情况优先级更高
        )

        self._last_signal = signal
        return signal
