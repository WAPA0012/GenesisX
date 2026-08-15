"""Risk assessment for actions."""
from common.models import Action, ActionType
from typing import Dict, Any


# P7-4: 提取魔术数到模块常量（原内联硬编码）
CODE_EXEC_RISK = 0.8                  # 代码执行类动作的最低风险等级
HIGH_STRESS_THRESHOLD = 0.8           # 压力高于此值增加风险
HIGH_STRESS_RISK_BONUS = 0.1          # 高压力时的风险增量
LOW_ENERGY_THRESHOLD = 0.2            # 能量低于此值增加风险
LOW_ENERGY_RISK_BONUS = 0.15          # 低能量时的风险增量

# 代码执行模式（避免 "executive" 等误报）
CODE_EXEC_PATTERNS = ("exec(", "eval(", "os.system(", "subprocess", "code_exec")


def assess_risk(action: Action, context: Dict[str, Any] = None) -> float:
    """Assess risk level of an action.

    Args:
        action: Action to assess
        context: Optional context dict for additional info

    Returns:
        Risk score [0,1]
    """
    context = context or {}

    # Use action's declared risk level
    base_risk = getattr(action, 'risk_level', 0.0)

    # Validate base_risk is within valid range
    if not isinstance(base_risk, (int, float)):
        base_risk = 0.0
    else:
        base_risk = max(0.0, min(1.0, base_risk))  # Clamp to [0, 1]

    # Increase risk for certain action types
    action_type = getattr(action, 'type', '')
    params = getattr(action, 'params', {})

    if action_type == ActionType.USE_TOOL:
        params_str = str(params).lower()
        tool_id = getattr(action, 'tool_id', '') or ''
        if tool_id == "code_exec" or any(p in params_str for p in CODE_EXEC_PATTERNS):
            base_risk = max(base_risk, CODE_EXEC_RISK)

    # Additional risk factors based on context
    stress = context.get("stress", 0.0)
    if isinstance(stress, (int, float)) and stress > HIGH_STRESS_THRESHOLD:
        # Higher stress increases risk
        base_risk = min(1.0, base_risk + HIGH_STRESS_RISK_BONUS)

    energy = context.get("energy", 1.0)
    if isinstance(energy, (int, float)) and energy < LOW_ENERGY_THRESHOLD:
        # Low energy increases risk
        base_risk = min(1.0, base_risk + LOW_ENERGY_RISK_BONUS)

    return max(0.0, min(1.0, base_risk))  # Ensure result is in [0, 1]
