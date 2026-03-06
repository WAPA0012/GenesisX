"""Integrity checking for actions and state."""
from typing import Dict, Any
from common.models import Action, ActionType


def check_integrity(action: Action, state: Dict[str, Any]) -> Dict[str, Any]:
    """Check if action maintains system integrity.

    Args:
        action: Action to check
        state: Current state

    Returns:
        Result dict with "ok" and optional "reason"
    """
    # Validate inputs
    if action is None:
        return {"ok": False, "reason": "Invalid action: None"}

    if state is None:
        state = {}

    # Get action params safely
    params = getattr(action, 'params', {})
    if params is None:
        params = {}

    # Check 1: No self-modification
    if "modify_self" in params:
        return {"ok": False, "reason": "Self-modification forbidden"}

    # Check 2: Stress threshold
    stress = state.get("stress", 0.0)
    if isinstance(stress, (int, float)):
        stress = max(0.0, min(1.0, stress))  # Normalize to [0, 1]
        if stress > 0.9:
            # 高压力时只允许恢复性动作（CHAT、REFLECT、SLEEP）
            # 修复：允许 CHAT，因为与用户交流可以缓解压力
            if action.type not in [ActionType.CHAT, ActionType.REFLECT, ActionType.SLEEP]:
                return {"ok": False, "reason": "Stress too high, only recovery actions allowed"}

    # Check 3: Energy threshold
    energy = state.get("energy", 0.5)
    if isinstance(energy, (int, float)):
        energy = max(0.0, min(1.0, energy))  # Normalize to [0, 1]
        if energy < 0.1:
            # 低能量时只允许 SLEEP（恢复能量）
            # 修复：允许 SLEEP，否则会形成死锁
            if action.type != ActionType.SLEEP:
                return {"ok": False, "reason": "Energy critical, rest required"}

    # Check 4: Mood threshold
    mood = state.get("mood", 0.5)
    if isinstance(mood, (int, float)):
        mood = max(0.0, min(1.0, mood))  # Normalize to [0, 1]
        if mood < 0.1:
            # Very low mood requires additional caution
            if action.type in [ActionType.EXPLORE, ActionType.LEARN_SKILL]:
                return {"ok": False, "reason": "Mood too low for exploration activities"}

    return {"ok": True}
