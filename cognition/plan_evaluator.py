"""Plan Evaluator - score and select plans based on value function."""
from typing import List, Dict, Any
from .planner import Plan


class PlanEvaluator:
    """Evaluates candidate plans and selects best one.

    From Section 3.9: Plan evaluator scores plans using value function.
    J(plan) = expected_value_gain - cost - risk_penalty
    """

    def __init__(self):
        """Initialize plan evaluator."""
        pass

    def evaluate_plans(
        self,
        plans: List[Plan],
        weights: Dict[str, float],
        budget_remaining: float,
    ) -> List[tuple]:
        """Evaluate all plans and return scored list.

        Args:
            plans: List of candidate plans
            weights: Current value weights
            budget_remaining: Remaining resource budget

        Returns:
            List of (score, plan) tuples sorted by score descending
        """
        scored = []

        for plan in plans:
            score = self._score_plan(plan, weights, budget_remaining)
            scored.append((score, plan))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        return scored

    def select_best(
        self,
        plans: List[Plan],
        weights: Dict[str, float],
        budget_remaining: float,
    ) -> Plan:
        """Select best plan.

        Args:
            plans: List of candidate plans
            weights: Current value weights
            budget_remaining: Remaining budget

        Returns:
            Best plan
        """
        if not plans:
            # Return default idle plan
            return Plan({
                "actions": [],
                "reasoning": "No plans available",
                "estimated_reward": 0.0,
                "estimated_cost": 0.0,
            })

        scored = self.evaluate_plans(plans, weights, budget_remaining)
        return scored[0][1]  # Return plan with highest score

    def _score_plan(
        self,
        plan: Plan,
        weights: Dict[str, float],
        budget_remaining: float,
    ) -> float:
        """Score a single plan using paper's J(p|S_t) formula.

        修复 M22: 使用论文 Section 3.9.3 的加权评分公式
        J(p|S_t) = Σ_i w_i · E[u^(i)(p)] - λ_cost · Cost(p) - λ_risk · Risk(p)

        Args:
            plan: Plan to score
            weights: Value weights {dim_name: w_i}
            budget_remaining: Remaining resource budget

        Returns:
            Score (higher is better)
        """
        # Extract plan properties
        estimated_reward = plan.get("estimated_reward", 0.0)
        estimated_cost = plan.get("estimated_cost", 0.0)

        # Compute risk penalty from actions
        actions = plan.get("actions", [])
        total_risk = 0.0
        for action in actions:
            if isinstance(action, dict) and "risk_level" in action:
                total_risk += action["risk_level"]
            elif hasattr(action, "risk_level"):
                total_risk += action.risk_level

        # 论文 J(p|S_t) = Σ w_i · E[u^(i)] - λ_cost·Cost - λ_risk·Risk
        # Alpha版：计划只携带单一 estimated_reward，无法提供维度级效用估计。
        # 使用计划关联维度的权重来调制奖励，使得与当前需求匹配的计划得分更高。
        if weights:
            plan_dimension = plan.get("dimension", None)
            if plan_dimension and plan_dimension in weights:
                # 计划关联特定维度：使用该维度权重 * n（因为 Σw=1，单维度权重需放大）
                n_dims = len(weights)
                weighted_value = weights[plan_dimension] * n_dims * estimated_reward
            else:
                # 通用计划：使用最大权重作为调制因子（偏好当前最急需的维度）
                max_weight = max(weights.values()) if weights else 0.0
                n_dims = len(weights)
                weighted_value = max_weight * n_dims * estimated_reward
        else:
            weighted_value = estimated_reward

        # 成本惩罚系数 λ_cost
        lambda_cost = 0.001  # 归一化到与奖励可比的量级
        cost_penalty = lambda_cost * estimated_cost

        # 风险惩罚系数 λ_risk
        lambda_risk = 0.5
        risk_penalty = lambda_risk * total_risk

        # 预算违反惩罚 (硬约束)
        budget_penalty = 0.0
        if estimated_cost > budget_remaining:
            budget_penalty = 2.0

        # J(p|S_t)
        score = weighted_value - cost_penalty - risk_penalty - budget_penalty

        return score
