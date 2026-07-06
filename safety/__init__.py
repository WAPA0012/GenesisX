"""Safety System - integrity, risk, and budget control.

PHASE 9 五重安全检查里只有 9a/9c/9d 三个函数级模块接入 life_loop：
  - check_integrity (9a 完整性)
  - assess_risk (9c 风险)
  - check_budget (9d 预算)
（9b 验证器在 cognition/verifier.py，9e 能力缺口在 core/capability_manager.py）

注：contract_guard.py / hallucination_check.py / sandbox.py 已删除——
三者共 988 行，零运行时引用（论文§3.13 契约/幻觉/沙箱机制在生产未接线）。
详见 CODE_MAP P7-7/P7-10/P7-13。
"""
from .integrity_check import check_integrity
from .risk_assessment import assess_risk
from .budget_control import check_budget

__all__ = [
    "check_integrity",
    "assess_risk",
    "check_budget",
]
