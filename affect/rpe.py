"""Reward Prediction Error (RPE) computation.

Implements paper Section 3.7.2: Per-dimension RPE for multi-dimensional value system.
"""
from typing import Dict, Optional, Any, Tuple


def compute_rpe(
    reward: float,
    value_current: float,
    value_next: float,
    gamma: float = 0.97,  # 论文Appendix A.5默认值
    clip_range: Tuple[float, float] = (-2.0, 2.0),  # 边界保护
) -> float:
    """Compute scalar RPE: δ = r + γV(s') - V(s).

    Args:
        reward: Current reward r_t
        value_current: V(s_t)
        value_next: V(s_{t+1})
        gamma: Discount factor
        clip_range: (min, max) range for clipping RPE to prevent overflow

    Returns:
        RPE δ_t (clipped to prevent extreme values)
    """
    delta = reward + gamma * value_next - value_current
    # 边界保护：防止RPE过大导致Mood/Stress越界
    delta = max(clip_range[0], min(clip_range[1], delta))
    return delta


def compute_per_dimension_rpe(
    utilities: Dict[str, float],
    values_current: Dict[str, float],
    values_next: Dict[str, float],
    gamma: float = 0.97,  # 论文Appendix A.5默认值
    clip_range: Tuple[float, float] = (-2.0, 2.0),  # 修复 H21: 与标量RPE相同裁剪
) -> Dict[str, float]:
    """Compute per-dimension RPE: δ^(i) = u^(i) + γV^(i)(s') - V^(i)(s).

    Paper Section 3.7.2: For each dimension, compute independent RPE to track
    which dimensions are exceeding or falling below expectations.

    修复 H21: 添加与标量RPE相同的裁剪范围 [-2, 2]，防止溢出。

    Args:
        utilities: Per-dimension utilities u^(i)_t
        values_current: Per-dimension value predictions V^(i)(s_t)
        values_next: Per-dimension value predictions V^(i)(s_{t+1})
        gamma: Discount factor
        clip_range: (min, max) range for clipping per-dimension RPE

    Returns:
        Per-dimension RPE δ^(i)_t (clipped)
    """
    rpe_per_dim = {}
    for dim in utilities:
        u = utilities.get(dim, 0.0)
        v_current = values_current.get(dim, 0.0)
        v_next = values_next.get(dim, 0.0)
        delta_i = u + gamma * v_next - v_current
        # 修复 H21: 裁剪维度级RPE，与标量RPE保持一致
        delta_i = max(clip_range[0], min(clip_range[1], delta_i))
        rpe_per_dim[dim] = delta_i
    return rpe_per_dim


def compute_weighted_rpe(
    rpe_per_dim: Dict[str, float],
    weights: Dict[str, float],
) -> float:
    """Compute global RPE as weighted sum of per-dimension RPEs.

    Paper formula: δ_t = Σ w^(i)_t · δ^(i)_t

    Args:
        rpe_per_dim: Per-dimension RPEs δ^(i)_t
        weights: Current dimension weights w^(i)_t

    Returns:
        Global weighted RPE δ_t
    """
    total = 0.0
    for dim, rpe in rpe_per_dim.items():
        w = weights.get(dim, 0.0)
        total += w * rpe
    return total


class RPEComputer:
    """RPE computation with per-dimension tracking.

    Implements paper Section 3.7 with:
    - Per-dimension value predictions V^(i)(s)
    - Per-dimension RPE δ^(i)_t
    - Weighted global RPE δ_t
    """

    def __init__(self, dimensions: list = None, gamma: float = 0.97):
        """Initialize RPE computer.

        Args:
            dimensions: List of value dimensions
            gamma: Discount factor (论文默认0.97)
        """
        # 论文 Section 3.5.1: 5维核心价值向量
        self.dimensions = dimensions or [
            "homeostasis", "attachment", "curiosity", "competence", "safety"
        ]
        self.gamma = gamma

        # Per-dimension value predictions (EMA-based)
        self._value_predictions: Dict[str, float] = {
            dim: 0.0 for dim in self.dimensions
        }
        self._ema_alpha = 0.05  # Paper Appendix A.5: alpha_V = 0.05

    def compute(
        self,
        utilities: Dict[str, float],
        weights: Dict[str, float],
        next_state_values: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Compute RPE for current tick.

        Args:
            utilities: Per-dimension utilities u^(i)_t
            weights: Current dimension weights w^(i)_t
            next_state_values: Optional explicit V^(i)(s_{t+1})

        Returns:
            Dict with per_dimension RPEs and global RPE
        """
        # Use current predictions as V^(i)(s_t)
        values_current = self._value_predictions.copy()

        # Estimate V^(i)(s_{t+1})
        if next_state_values is None:
            # 使用当前预测作为 V^(i)(s_{t+1}) 的自举估计 (修复 M18)
            # 之前用 V + u 估算不正确；应使用纯自举
            values_next = values_current.copy()
        else:
            values_next = next_state_values

        # Compute per-dimension RPE (修复 H21: 含裁剪)
        rpe_per_dim = compute_per_dimension_rpe(
            utilities, values_current, values_next, self.gamma
        )

        # Compute weighted global RPE
        global_rpe = compute_weighted_rpe(rpe_per_dim, weights)

        # 论文 Appendix A.5: V^(i)(S_t) ← (1-α_V)V^(i)(S_t) + α_V(u^(i)_t + γV^(i)(S_{t+1}))
        # 修复 H20: 使用 TD target 包含效用信号 (维度级奖励)
        for dim in self.dimensions:
            old_v = self._value_predictions.get(dim, 0.0)
            u_i = utilities.get(dim, 0.0)
            v_next = values_next.get(dim, 0.0)
            td_target = u_i + self.gamma * v_next
            self._value_predictions[dim] = (
                (1 - self._ema_alpha) * old_v + self._ema_alpha * td_target
            )

        return {
            "per_dimension": rpe_per_dim,
            "global": global_rpe,
            "values_current": values_current,
            "values_next": values_next,
        }

    def get_value_predictions(self) -> Dict[str, float]:
        """Get current value predictions."""
        return self._value_predictions.copy()

    def set_value_predictions(self, values: Dict[str, float]):
        """Set value predictions (for persistence)."""
        self._value_predictions = values.copy()

