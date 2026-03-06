"""Reward computation: r = sum(w_i * u_i)."""
from typing import Dict, Tuple, Any, Optional
from common.models import ValueDimension, CostVector


def compute_reward(
    utilities: Dict[ValueDimension, float],
    weights: Dict[ValueDimension, float],
    cost: Optional[CostVector] = None,
    cost_normalization_factor: Optional[float] = None,
) -> float:
    """Compute scalar reward: r = sum(w_i * u_i).

    Paper Section 3.5.3: r_t = sum(w^(i)_t * u^(i)_t)

    Note: Cost is already included via the Efficiency dimension's utility
    (u^eff = -Cost_res), so it is NOT subtracted separately here.
    The paper specifies lambda_cost = 0 when Efficiency dimension is active.

    Args:
        utilities: Utility values per dimension
        weights: Dynamic weights per dimension
        cost: Cost vector (unused when Efficiency dimension handles cost;
              kept for backward compatibility)
        cost_normalization_factor: Optional custom normalization factor (unused)

    Returns:
        Scalar reward
    """
    # Weighted sum of utilities (paper formula 3.5.3)
    value_reward = 0.0
    for dim in ValueDimension:
        utility = utilities.get(dim, 0.0)
        weight = weights.get(dim, 0.0)
        value_reward += weight * utility

    # Note: cost penalty removed to avoid double-counting with Efficiency utility.
    # If Efficiency dimension is disabled, cost can be added back via:
    #   cost_penalty = cost.total_cost() / norm_factor if cost else 0.0

    return value_reward


class RewardCalculator:
    """Calculator for reward computation from gaps and weights."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize reward calculator.

        Args:
            config: Configuration dictionary (optional)
        """
        self.config = config or {}

    def calculate_reward(self, gaps: Dict[str, float], weights: Dict[str, float]) -> float:
        """Calculate reward from gaps and weights.

        Args:
            gaps: Value dimension gaps
            weights: Dynamic weights

        Returns:
            Scalar reward value
        """
        # Convert gaps to negative utilities (higher gap = more negative)
        reward = 0.0
        for dim_name, gap in gaps.items():
            weight = weights.get(dim_name, 0.0)
            # Negative reward for gaps
            reward -= weight * gap

        return reward

    def calculate_reward_with_components(
        self, gaps: Dict[str, float], weights: Dict[str, float]
    ) -> Tuple[float, Dict[str, float]]:
        """Calculate reward with individual components.

        Args:
            gaps: Value dimension gaps
            weights: Dynamic weights

        Returns:
            Tuple of (total_reward, component_dict)
        """
        components = {}
        total_reward = 0.0

        for dim_name, gap in gaps.items():
            weight = weights.get(dim_name, 0.0)
            component_reward = -weight * gap
            components[dim_name] = component_reward
            total_reward += component_reward

        return total_reward, components
