"""Budget control and monitoring."""
from typing import Dict, Any
from common.models import Action, CostVector


# Default budget constants
DEFAULT_CPU_TOKENS_BUDGET = 1000
DEFAULT_MONEY_BUDGET = 1.0


def check_budget(
    action: Action,
    state: Dict[str, Any],
    budget_remaining: Dict[str, float],
) -> Dict[str, Any]:
    """Check if action is within budget.

    Args:
        action: Action to check
        state: Current state
        budget_remaining: Remaining budgets

    Returns:
        Result dict with "ok" and optional "reason"
    """
    # Get estimated cost
    if action.estimated_cost is not None:
        cost = action.estimated_cost
    else:
        # Default cost estimate
        cost = CostVector(cpu_tokens=100)

    # Validate cost values are non-negative
    if cost.cpu_tokens < 0:
        return {
            "ok": False,
            "reason": f"Invalid cost: cpu_tokens cannot be negative ({cost.cpu_tokens})",
        }

    if cost.money < 0:
        return {
            "ok": False,
            "reason": f"Invalid cost: money cannot be negative (${cost.money:.2f})",
        }

    # Check CPU tokens
    tokens_remaining = budget_remaining.get("cpu_tokens", DEFAULT_CPU_TOKENS_BUDGET)

    # Validate remaining budget is non-negative
    if tokens_remaining < 0:
        return {
            "ok": False,
            "reason": f"Invalid budget: cpu_tokens remaining cannot be negative ({tokens_remaining})",
        }

    if cost.cpu_tokens > tokens_remaining:
        return {
            "ok": False,
            "reason": f"Insufficient tokens: need {cost.cpu_tokens}, have {tokens_remaining}",
        }

    # Check money
    money_remaining = budget_remaining.get("money", DEFAULT_MONEY_BUDGET)

    # Validate remaining money is non-negative
    if money_remaining < 0:
        return {
            "ok": False,
            "reason": f"Invalid budget: money remaining cannot be negative (${money_remaining:.2f})",
        }

    if cost.money > money_remaining:
        return {
            "ok": False,
            "reason": f"Insufficient money: need ${cost.money:.2f}, have ${money_remaining:.2f}",
        }

    return {"ok": True}
