"""Safety Drive - 安全驱动力

提供安全驱动力信号，告诉 LLM "想要保持安全、避免风险"。

这是价值系统的一部分，对应价值维度：safety
"""
from typing import Dict, Any
from .base import BaseDrive, DriveSignal


class SafetyDrive(BaseDrive):
    """安全驱动力

    驱动数字生命保持安全、规避风险、预防损失。
    对应价值维度：safety
    """

    def __init__(self):
        super().__init__(
            name="安全",
            value_dimension="safety"
        )
        self._risk_history = []
        self._safety_level = 1.0  # 当前安全水平

    def generate_drive_signal(
        self,
        state: Dict[str, Any],
        context: Dict[str, Any]
    ) -> DriveSignal:
        """生成安全驱动力信号"""
        # 获取状态
        gaps = state.get("gaps", {})
        gap = gaps.get("safety", 0.0)
        weights = state.get("weights", {})
        weight = weights.get("safety", 0.2)
        stress = state.get("stress", 0.0)
        risk_level = state.get("risk_level", 0.0)
        energy = state.get("energy", 0.5)

        # 计算强度
        # 安全需求与风险水平、压力正相关
        base_intensity = gap * weight
        risk_factor = risk_level * 0.5
        stress_factor = stress * 0.3
        energy_factor = (1 - energy) * 0.2  # 低能量时更关注安全

        intensity = min(1.0, max(0.0, base_intensity + risk_factor + stress_factor + energy_factor))

        # 生成描述
        if intensity > 0.8:
            if risk_level > 0.5:
                description = "检测到较高风险，需要谨慎行事，优先确保安全"
            else:
                description = "当前环境存在不确定性，需要保持警惕，避免冒险行为"
        elif intensity > 0.5:
            description = "适度关注安全，在可控范围内进行活动"
        elif intensity > 0.3:
            description = "当前安全状况良好，可以适度尝试新事物"
        else:
            description = "当前非常安全，可以放心进行各种活动"

        signal = DriveSignal(
            name=self.name,
            intensity=intensity,
            description=description,
            context={
                "gap": gap,
                "weight": weight,
                "risk_level": risk_level,
                "stress": stress,
                "safety_level": self._safety_level,
            },
            priority=weight * intensity * 1.2  # 安全优先级略高
        )

        self._last_signal = signal
        return signal
