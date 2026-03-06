"""Metabolism system - Resource management and body dynamics.

论文 Appendix A.3: η-coefficient body dynamics.
论文 v14 Section 3.2: 数字原生模型 (Compute_t, Memory_t)

注意:
- Energy_t 和 Fatigue_t 已被数字原生模型替代，不再使用
- Stress 现在由 affect/ 模块管理
- Homeostasis 现在由 axiology/ 模块管理
"""
from .boredom import update_boredom, BoredomConfig, configure_boredom, compute_effective_boredom
from .recovery import compute_recovery_rate, needs_recovery, suggest_recovery_mode, RecoveryConfig
from .circadian import CircadianRhythm, CircadianPhase
from .resource_pressure import (
    compute_resource_pressure,
    is_emergency_state,
    compute_effective_boredom as rp_compute_effective_boredom,
    ResourcePressureConfig,
    configure_resource_pressure,
    get_resource_pressure_report,
    rp_from_state,
)

# 向后兼容: Stress 相关函数从 affect 导入
from affect.stress_affect import update_stress

__all__ = [
    # Boredom
    "update_boredom",
    "BoredomConfig",
    "configure_boredom",
    "compute_effective_boredom",
    # Recovery
    "compute_recovery_rate",
    "needs_recovery",
    "suggest_recovery_mode",
    "RecoveryConfig",
    # Circadian
    "CircadianRhythm",
    "CircadianPhase",
    # Resource Pressure (RP_t) - 论文 v14 新增
    "compute_resource_pressure",
    "is_emergency_state",
    "ResourcePressureConfig",
    "configure_resource_pressure",
    "get_resource_pressure_report",
    "rp_from_state",
    # 向后兼容
    "update_stress",
]
