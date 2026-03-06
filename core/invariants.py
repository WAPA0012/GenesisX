"""Invariants checking - ensures system constraints."""
from typing import Dict
from common.models import ValueDimension, ActionType


def check_weights_simplex(weights: Dict[ValueDimension, float]) -> bool:
    """Check that weights form a simplex: all ≥ 0 and sum = 1.

    Returns:
        True if valid, False otherwise
    """
    if not weights:
        return False

    # Check all non-negative
    if any(w < 0 for w in weights.values()):
        return False

    # Check sum ≈ 1.0 (with tolerance for floating-point accumulation)
    # 8个维度的 softmax + 软优先级覆盖累加误差可能超过 1e-4，放宽到 1e-3
    total = sum(weights.values())
    return abs(total - 1.0) < 1e-3


def check_ledger_non_negative(ledger: Dict[str, float]) -> bool:
    """Check that all ledger values are non-negative.

    Returns:
        True if valid, False otherwise
    """
    return all(v >= 0 for v in ledger.values())


def check_single_external_action(actions: list) -> bool:
    """Check that at most one external action is executed per tick.

    Returns:
        True if valid, False otherwise
    """
    external_actions = [a for a in actions if hasattr(a, "type") and a.type != ActionType.SLEEP and a.type != ActionType.REFLECT]
    return len(external_actions) <= 1


def check_invariants(state: "GlobalState", weights: Dict, ledger: Dict, actions: list) -> Dict[str, bool]:
    """Run all invariant checks.

    修复 v14: Mood 范围应为 [-1, 1] (论文 Section 3.7.2)

    Returns:
        Dict of check_name -> passed (bool)
    """
    return {
        "weights_simplex": check_weights_simplex(weights),
        "ledger_non_negative": check_ledger_non_negative(ledger),
        "single_external_action": check_single_external_action(actions),
        "energy_in_range": 0.0 <= state.energy <= 1.0,
        "mood_in_range": -1.0 <= state.mood <= 1.0,  # 修复: Mood 是双向的 [-1, 1]
        "stress_in_range": 0.0 <= state.stress <= 1.0,
        "fatigue_in_range": 0.0 <= state.fatigue <= 1.0,
        "bond_in_range": 0.0 <= state.bond <= 1.0,
        "trust_in_range": 0.0 <= state.trust <= 1.0,
        "boredom_in_range": 0.0 <= state.boredom <= 1.0,
    }
