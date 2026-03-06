"""Stress dynamics coupled with RPE and failures.

论文 Section 3.7.3:
Stress_{t+1} = clip(Stress_t + s*max(-δ,0) - s'*max(δ,0))
"""

# Default stress increase on failure (configurable)
DEFAULT_FAILURE_STRESS_INCREASE = 0.15


def update_stress(
    stress: float,
    delta: float,
    failed: bool = False,
    s: float = 0.20,        # 论文默认: 负RPE压力增益
    s_prime: float = 0.10,  # 论文默认: 正RPE压力缓解
    decay: float = 0.01,
    failure_penalty: float = DEFAULT_FAILURE_STRESS_INCREASE,  # Configurable failure penalty
) -> float:
    """Update stress level.

    论文公式 Section 3.7.3:
    - 负RPE (δ<0) 增加压力: s * |δ|
    - 正RPE (δ>0) 缓解压力: s' * δ
    - 失败额外增加压力
    - 自然衰减

    Args:
        stress: Current stress [0,1]
        delta: RPE
        failed: Whether action failed
        s: Stress gain coefficient for negative RPE
        s_prime: Stress relief coefficient for positive RPE
        decay: Natural decay rate
        failure_penalty: Stress increase on failure (default: 0.15)

    Returns:
        Updated stress
    """
    # Validate input parameters
    stress = max(0.0, min(1.0, stress))  # Clamp to [0, 1]
    # 修复：统一RPE裁剪范围与rpe.py保持一致为[-2.0, 2.0]
    delta = max(-2.0, min(2.0, delta))  # Clamp to [-2, 2] - 与affect/rpe.py保持一致
    s = max(0.0, min(1.0, s))  # Clamp to [0, 1]
    s_prime = max(0.0, min(1.0, s_prime))  # Clamp to [0, 1]
    decay = max(0.0, min(0.5, decay))  # Clamp to [0, 0.5]
    failure_penalty = max(0.0, min(1.0, failure_penalty))  # Clamp to [0, 1]

    # Natural decay
    stress = max(0.0, stress - decay)

    # 论文公式: Stress_{t+1} = Stress_t + s*max(-δ,0) - s'*max(δ,0)
    if delta < 0:
        # Negative RPE increases stress
        stress = min(1.0, stress + s * abs(delta))
    elif delta > 0:
        # Positive RPE relieves stress (论文要求)
        stress = max(0.0, stress - s_prime * delta)

    # Failures increase stress (now configurable)
    if failed:
        stress = min(1.0, stress + failure_penalty)

    return stress
