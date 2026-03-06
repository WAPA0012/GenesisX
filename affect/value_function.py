"""Value function V(s) for RPE computation.

论文 Appendix A.5: V(S_t) ← (1-α_V)V(S_t) + α_V(r_t + γV(S_{t+1}))
默认使用 one-step TD target (论文v4修正#15).
"""


class ValueFunction:
    """Value function using one-step TD target (论文 Appendix A.5).

    论文公式: V(S_t) ← (1-α_V)V(S_t) + α_V(r_t + γV(S_{t+1}))

    修复 H20: 旧版本 update() 仅用 reward，缺少 TD target。
    现在 update() 接收 reward + gamma * V(s') 作为 TD target。
    """

    def __init__(self, alpha: float = 0.05, gamma: float = 0.97):
        """Initialize value function.

        Args:
            alpha: Learning rate α_V (论文默认 0.05)
            gamma: Discount factor γ (论文默认 0.97)
        """
        self.alpha = alpha
        self.gamma = gamma
        self.value = 0.0

    def predict(self) -> float:
        """Get current value prediction V(S_t).

        Returns:
            V(s)
        """
        return self.value

    def update(self, reward: float, value_next: float = None):
        """Update value function using one-step TD target (修复 H20).

        论文公式: V(S_t) ← (1-α_V)V(S_t) + α_V(r_t + γV(S_{t+1}))

        Args:
            reward: Current reward r_t
            value_next: V(S_{t+1}). If None, uses self-prediction (bootstrap).
        """
        if value_next is None:
            # 自举: 使用当前预测作为 V(S_{t+1}) 的近似
            value_next = self.value

        td_target = reward + self.gamma * value_next
        self.value = (1 - self.alpha) * self.value + self.alpha * td_target

    def get(self) -> float:
        """Get current value (alias for predict)."""
        return self.value
