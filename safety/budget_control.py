"""Budget control and monitoring."""
from typing import Dict, Any
from common.models import Action, CostVector


# Default budget constants
DEFAULT_CPU_TOKENS_BUDGET = 1000
DEFAULT_MONEY_BUDGET = 1.0
DEFAULT_IO_OPS_BUDGET = 1000
DEFAULT_NET_BYTES_BUDGET = 10_000_000
DEFAULT_RISK_SCORE_BUDGET = 0.5


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

    # --- P7-5 修复: 检查全部 5 维预算 (原只查 cpu_tokens + money) ---
    # latency_ms 不检查——它是单次调用的质量指标，非累积预算

    # 通用检查函数：某个维度是否超预算
    def _check_dim(cost_val: float, budget_key: str, default_budget: float, label: str):
        if cost_val < 0:
            return {"ok": False, "reason": f"Invalid cost: {label} cannot be negative ({cost_val})"}
        remaining = budget_remaining.get(budget_key, default_budget)
        if remaining < 0:
            return {"ok": False, "reason": f"Invalid budget: {label} remaining cannot be negative ({remaining})"}
        if cost_val > remaining:
            return {"ok": False, "reason": f"Insufficient {label}: need {cost_val}, have {remaining}"}
        return None

    # 逐维检查
    for cost_val, budget_key, default_budget, label in [
        (cost.cpu_tokens, "cpu_tokens", DEFAULT_CPU_TOKENS_BUDGET, "cpu_tokens"),
        (cost.io_ops, "io_ops", DEFAULT_IO_OPS_BUDGET, "io_ops"),
        (cost.net_bytes, "net_bytes", DEFAULT_NET_BYTES_BUDGET, "net_bytes"),
        (cost.risk_score, "risk_score", DEFAULT_RISK_SCORE_BUDGET, "risk_score"),
        (cost.money, "money", DEFAULT_MONEY_BUDGET, "money"),
    ]:
        result = _check_dim(cost_val, budget_key, default_budget, label)
        if result is not None:
            return result

    return {"ok": True}
