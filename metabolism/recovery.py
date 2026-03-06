"""Recovery system for Digital Life.

论文 Section 3.8.2: 恢复机制
- 能量恢复：休息时能量逐渐回升
- 疲劳恢复：睡眠减少疲劳
- 压力恢复：正向RPE和休息降低压力
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class RecoveryConfig:
    """恢复系统配置 (P2-10: 配置化参数).

    Attributes:
        energy_recovery_rate: 每tick能量恢复速率 (休息时)
        fatigue_recovery_rate: 每tick疲劳恢复速率 (睡眠时)
        stress_recovery_rate: 每tick压力恢复速率 (正向RPE)
        recovery_threshold: 开始恢复的能量阈值
    """
    energy_recovery_rate: float = 0.05  # 每tick恢复5%
    fatigue_recovery_rate: float = 0.08  # 睡眠时每tick恢复8%
    stress_recovery_rate: float = 0.03   # 正向RPE时每tick恢复3%
    recovery_threshold: float = 0.3      # 能量低于30%时进入恢复模式

    @classmethod
    def from_global_config(cls, global_config: Dict[str, Any]) -> 'RecoveryConfig':
        """从全局配置创建 RecoveryConfig (P2-10: 配置化参数)."""
        config = cls()

        if 'recovery' in global_config:
            recovery_cfg = global_config['recovery']

            for key, value in recovery_cfg.items():
                if hasattr(config, key):
                    setattr(config, key, value)

        return config


def compute_recovery_rate(
    energy: float,
    fatigue: float,
    stress: float,
    mode: str = "work",
    config: Optional[RecoveryConfig] = None
) -> Dict[str, float]:
    """计算各维度的恢复速率.

    论文 Section 3.8.2:
    - 工作模式: 仅恢复少量能量
    - 休息模式: 中等恢复
    - 睡眠模式: 最大恢复（能量、疲劳、压力）

    Args:
        energy: 当前能量水平 [0,1]
        fatigue: 当前疲劳水平 [0,1]
        stress: 当前压力水平 [0,1]
        mode: 当前模式 (work/friend/sleep)
        config: 恢复配置

    Returns:
        包含各维度恢复速率的字典:
        - energy_delta: 能量变化 (正值为恢复)
        - fatigue_delta: 疲劳变化 (负值为恢复)
        - stress_delta: 压力变化 (负值为恢复)
    """
    cfg = config or RecoveryConfig()

    # 基础恢复速率
    energy_recovery = cfg.energy_recovery_rate
    fatigue_recovery = cfg.fatigue_recovery_rate
    stress_recovery = cfg.stress_recovery_rate

    # 根据模式调整恢复速率
    if mode == "sleep":
        # 睡眠模式: 最大恢复
        energy_recovery *= 2.0
        fatigue_recovery *= 2.0
        stress_recovery *= 1.5
    elif mode == "friend":
        # 社交模式: 中等恢复
        energy_recovery *= 0.5
        fatigue_recovery *= 0.3
    else:
        # 工作模式: 最小恢复
        energy_recovery *= 0.1
        fatigue_recovery *= 0.0

    # 根据当前状态调整恢复效果
    # 能量越低，恢复越快（生理补偿机制）
    if energy < cfg.recovery_threshold:
        energy_recovery *= 1.5

    # 疲劳越高，恢复越慢（疲劳累积效应）
    if fatigue > 0.7:
        fatigue_recovery *= 0.7

    # 计算变化量
    energy_delta = min(energy_recovery, 1.0 - energy)  # 不超过最大值
    fatigue_delta = -min(fatigue_recovery, fatigue)    # 不低于最小值
    stress_delta = -min(stress_recovery, stress * 0.5)  # 压力恢复较慢

    return {
        "energy_delta": energy_delta,
        "fatigue_delta": fatigue_delta,
        "stress_delta": stress_delta,
    }


def needs_recovery(energy: float, fatigue: float, stress: float, config: Optional[RecoveryConfig] = None) -> bool:
    """判断是否需要进入恢复模式.

    论文 Section 3.8.2: 当能量过低或疲劳/压力过高时，系统应进入恢复模式

    Args:
        energy: 当前能量水平 [0,1]
        fatigue: 当前疲劳水平 [0,1]
        stress: 当前压力水平 [0,1]
        config: 恢复配置

    Returns:
        是否需要恢复
    """
    cfg = config or RecoveryConfig()

    # 能量低于阈值
    if energy < cfg.recovery_threshold:
        return True

    # 疲劳过高
    if fatigue > 0.7:
        return True

    # 压力过高
    if stress > 0.8:
        return True

    return False


def suggest_recovery_mode(energy: float, fatigue: float, stress: float) -> str:
    """建议恢复模式.

    根据当前状态建议最合适的恢复模式:
    - "sleep": 睡眠（高疲劳或低能量时）
    - "friend": 社交放松（高压力时）

    系统有效模式为 work/friend/sleep，不使用 "rest"。

    Args:
        energy: 当前能量水平 [0,1]
        fatigue: 当前疲劳水平 [0,1]
        stress: 当前压力水平 [0,1]

    Returns:
        建议的恢复模式 (sleep/friend)
    """
    # 高疲劳需要睡眠
    if fatigue > 0.6:
        return "sleep"

    # 低能量需要睡眠恢复
    if energy < 0.3:
        return "sleep"

    # 高压力可能从社交中获益
    if stress > 0.6:
        return "friend"

    # 轻微疲劳，睡眠恢复
    return "sleep"
