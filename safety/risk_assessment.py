"""Risk assessment for actions."""
from common.models import Action, ActionType
from typing import Dict, Any


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
        # Check for code execution patterns (avoid false positives like "executive")
        exec_patterns = ["exec(", "eval(", "os.system(", "subprocess", "code_exec"]
        tool_id = getattr(action, 'tool_id', '') or ''
        if tool_id == "code_exec" or any(p in params_str for p in exec_patterns):
            base_risk = max(base_risk, 0.8)

    # Additional risk factors based on context
    stress = context.get("stress", 0.0)
    if isinstance(stress, (int, float)) and stress > 0.8:
        # Higher stress increases risk
        base_risk = min(1.0, base_risk + 0.1)

    energy = context.get("energy", 1.0)
    if isinstance(energy, (int, float)) and energy < 0.2:
        # Low energy increases risk
        base_risk = min(1.0, base_risk + 0.15)

    return max(0.0, min(1.0, base_risk))  # Ensure result is in [0, 1]
