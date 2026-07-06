"""Metabolism system - Resource management and body dynamics.

论文 Appendix A.3: η-coefficient body dynamics.
论文 v14 Section 3.2: 数字原生模型 (Compute_t, Memory_t)

注意:
- Energy_t 和 Fatigue_t 已被数字原生模型替代，不再使用
- Stress 现在由 affect/ 模块管理
- Homeostasis 现在由 axiology/ 模块管理

P4-61/P4-58 修复（2026-07）：resource_pressure.py 和 recovery.py 已删除。
- resource_pressure.py（论文版 RP 公式）与 state.py（生产版，自洽反转语义）并存
  造成混淆，且 life_loop 从不调用 resource_pressure（boredom 的资源覆盖因
  compute/memory 恒为默认 1.0 从不触发 P4-50）。资源紧急判断统一由
  state.py:get_effective_boredom 基于真实 psutil 采样实现。
- recovery.py（恢复速率/模式建议）被 life_loop 内联恢复公式绕过（P4-58），
  零运行时引用。
"""
from .boredom import update_boredom, BoredomConfig, configure_boredom, compute_effective_boredom
from .circadian import CircadianRhythm, CircadianPhase

# 向后兼容: Stress 相关函数从 affect 导入
from affect.stress_affect import update_stress

__all__ = [
    # Boredom
    "update_boredom",
    "BoredomConfig",
    "configure_boredom",
    "compute_effective_boredom",
    # Circadian
    "CircadianRhythm",
    "CircadianPhase",
    # 向后兼容
    "update_stress",
]
