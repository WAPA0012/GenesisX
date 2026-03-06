"""Mood dynamics based on RPE.

Implements paper Section 3.7.3: Mood/Stress update from RPE.
Enhanced with per-dimension RPE support (Section 3.7.2).

修复 v15: 使用5维核心价值向量 (论文 Section 3.5.1)
- HOMEOSTASIS: 稳态 - 资源平衡、压力管理、系统稳定
- ATTACHMENT: 依恋 - 社交连接、信任建立、忽视回避
- CURIOSITY: 好奇 - 新奇探索、信息增益、规律发现
- COMPETENCE: 胜任 - 任务成功、技能成长、效能感
- SAFETY: 安全 - 风险回避、损失预防、安全边际

论文公式:
Mood_{t+1} = clip(Mood_t + k_+ * max(δ,0) - k_- * max(-δ,0))
Stress_{t+1} = clip(Stress_t + s * max(-δ,0) - s' * max(δ,0))

默认参数 (Appendix A.5):
- k_+ = 0.25 (正RPE的mood增益)
- k_- = 0.30 (负RPE的mood损失)
- s = 0.20 (负RPE的压力增长)
- s' = 0.10 (正RPE的压力缓解)

P1-1: 维度级情绪影响系数可配置
"""
from typing import Dict, Optional, Any, Tuple
from dataclasses import dataclass

# Import at module level to avoid circular import issues
# The full update_stress function with failure handling and decay is in stress_affect.py
# We use a lazy import in update_stress() wrapper to avoid import cycle
try:
    from .stress_affect import update_stress as _update_stress_full
    _stress_affect_available = True
except ImportError:
    _stress_affect_available = False


@dataclass
class AffectConfig:
    """情绪系统配置 (P1-1, P2-10).

    支持维度级情绪影响系数配置化。
    """
    # 全局默认系数
    k_plus: float = 0.25   # 正RPE的mood增益
    k_minus: float = 0.30  # 负RPE的mood损失
    s_gain: float = 0.20   # 负RPE的压力增长
    s_relief: float = 0.10 # 正RPE的压力缓解

    # 维度级mood系数 (P1-1)
    mood_coefficients: Dict[str, Dict[str, float]] = None

    # 维度级stress系数 (P1-1)
    stress_coefficients: Dict[str, Dict[str, float]] = None

    def __post_init__(self):
        import copy
        if self.mood_coefficients is None:
            self.mood_coefficients = copy.deepcopy(DEFAULT_MOOD_COEFFICIENTS)
        if self.stress_coefficients is None:
            self.stress_coefficients = copy.deepcopy(DEFAULT_STRESS_COEFFICIENTS)

    @classmethod
    def from_global_config(cls, global_config: Dict[str, Any]) -> 'AffectConfig':
        """从全局配置创建 AffectConfig (P2-10: 配置化参数)."""
        config = cls()

        if 'affect' in global_config:
            affect_cfg = global_config['affect']

            # 更新全局默认系数
            if 'k_plus' in affect_cfg:
                config.k_plus = affect_cfg['k_plus']
            if 'k_minus' in affect_cfg:
                config.k_minus = affect_cfg['k_minus']
            if 's_gain' in affect_cfg:
                config.s_gain = affect_cfg['s_gain']
            if 's_relief' in affect_cfg:
                config.s_relief = affect_cfg['s_relief']

            # 更新维度级系数
            if 'mood_coefficients' in affect_cfg:
                config.mood_coefficients.update(affect_cfg['mood_coefficients'])

            if 'stress_coefficients' in affect_cfg:
                config.stress_coefficients.update(affect_cfg['stress_coefficients'])

        return config


# Default per-dimension mood coefficients (5维核心价值系统)
# 论文3.7.3增强: 不同维度对情绪影响不同
# 修复 v15: 从8维映射到5维，整合相关维度的情绪影响
DEFAULT_MOOD_COEFFICIENTS = {
    # Homeostasis 整合了 efficiency (资源效率对情绪影响较小)
    "homeostasis": {"k_plus": 0.08, "k_minus": 0.12},   # 稳态负RPE影响较大
    # Attachment 整合了 contract (契约履行影响关系)
    "attachment": {"k_plus": 0.12, "k_minus": 0.08},     # 关系正RPE影响更大
    # Curiosity 整合了 meaning (洞察和意义满足好奇心)
    "curiosity": {"k_plus": 0.18, "k_minus": 0.03},     # 好奇心正RPE影响大，包含meaning的0.18
    "competence": {"k_plus": 0.10, "k_minus": 0.06},
    # Safety 替代了 integrity (完整性问题影响安全感)
    "safety": {"k_plus": 0.05, "k_minus": 0.15},        # 安全问题负RPE影响最大，包含integrity的0.15
}

# Legacy 8D coefficients for backward compatibility
LEGACY_8D_MOOD_COEFFICIENTS = {
    "homeostasis": {"k_plus": 0.08, "k_minus": 0.12},
    "integrity": {"k_plus": 0.05, "k_minus": 0.15},     # → safety
    "attachment": {"k_plus": 0.12, "k_minus": 0.08},
    "contract": {"k_plus": 0.10, "k_minus": 0.08},      # → attachment
    "competence": {"k_plus": 0.10, "k_minus": 0.06},
    "curiosity": {"k_plus": 0.15, "k_minus": 0.03},
    "meaning": {"k_plus": 0.18, "k_minus": 0.02},       # → curiosity
    "efficiency": {"k_plus": 0.05, "k_minus": 0.04},    # → homeostasis
}

# Dimension mapping for legacy compatibility
LEGACY_DIMENSION_MAPPING = {
    "integrity": "safety",
    "contract": "attachment",
    "efficiency": "homeostasis",
    "meaning": "curiosity",
}

# Default per-dimension stress coefficients (5维核心价值系统)
# 论文3.7.3: Stress更新也支持维度级差异
DEFAULT_STRESS_COEFFICIENTS = {
    "homeostasis": {"s_gain": 0.15, "s_relief": 0.08},  # 稳态问题增加压力，包含efficiency
    "attachment": {"s_gain": 0.08, "s_relief": 0.10},    # 关系缓解压力，包含contract
    "curiosity": {"s_gain": 0.03, "s_relief": 0.05},    # 好奇探索，包含meaning的缓解效果
    "competence": {"s_gain": 0.08, "s_relief": 0.10},
    "safety": {"s_gain": 0.20, "s_relief": 0.05},       # 安全问题压力最大，包含integrity
}

# Legacy 8D stress coefficients for backward compatibility
LEGACY_8D_STRESS_COEFFICIENTS = {
    "homeostasis": {"s_gain": 0.15, "s_relief": 0.08},
    "integrity": {"s_gain": 0.20, "s_relief": 0.05},     # → safety
    "attachment": {"s_gain": 0.08, "s_relief": 0.10},
    "contract": {"s_gain": 0.10, "s_relief": 0.08},      # → attachment
    "competence": {"s_gain": 0.08, "s_relief": 0.10},
    "curiosity": {"s_gain": 0.03, "s_relief": 0.05},
    "meaning": {"s_gain": 0.02, "s_relief": 0.12},      # → curiosity
    "efficiency": {"s_gain": 0.06, "s_relief": 0.06},    # → homeostasis
}


def map_legacy_dimension(dim: str) -> str:
    """Map legacy 8D dimension names to 5D system.

    Args:
        dim: Legacy dimension name (may be old 8D or current 5D)

    Returns:
        Current 5D dimension name
    """
    return LEGACY_DIMENSION_MAPPING.get(dim, dim)


def update_mood(
    mood: float,
    delta: float,
    k_plus: float = 0.25,   # 论文Appendix A.5默认值
    k_minus: float = 0.30,  # 论文Appendix A.5默认值
) -> float:
    """Update mood based on scalar RPE.

    论文公式 Section 3.7.3:
    Mood_{t+1} = clip(Mood_t + k_+ * max(δ,0) - k_- * max(-δ,0))

    Args:
        mood: Current mood [0,1]
        delta: RPE
        k_plus: Gain for positive RPE (论文默认0.25)
        k_minus: Loss for negative RPE (论文默认0.30)

    Returns:
        Updated mood
    """
    if delta > 0:
        mood = min(1.0, mood + k_plus * delta)
    else:
        # delta为负数，加上负数等于减去绝对值
        # 公式：mood + k_minus * delta (delta < 0) 等价于 mood - k_minus * |delta|
        mood = max(0.0, mood + k_minus * delta)
    return mood


def update_mood_per_dimension(
    mood: float,
    rpe_per_dim: Dict[str, float],
    coefficients: Optional[Dict[str, Dict[str, float]]] = None,
) -> float:
    """Update mood based on per-dimension RPE.

    Paper Section 3.7.3 (enhanced):
    Mood_{t+1} = Mood_t + Σ_i k^(i)_+ max(δ^(i),0) - Σ_i k^(i)_- max(-δ^(i),0)

    Different dimensions have different emotional impact:
    - Curiosity/Meaning positive RPE → stronger mood boost
    - Integrity negative RPE → stronger mood penalty

    Args:
        mood: Current mood [0,1]
        rpe_per_dim: Per-dimension RPEs δ^(i)_t
        coefficients: Per-dimension k_plus/k_minus coefficients

    Returns:
        Updated mood
    """
    if coefficients is None:
        coefficients = DEFAULT_MOOD_COEFFICIENTS

    delta_mood = 0.0
    for dim, rpe in rpe_per_dim.items():
        coef = coefficients.get(dim, {"k_plus": 0.1, "k_minus": 0.05})
        if rpe > 0:
            delta_mood += coef["k_plus"] * rpe
        else:
            delta_mood += coef["k_minus"] * rpe

    new_mood = max(0.0, min(1.0, mood + delta_mood))
    return new_mood


def update_stress_simple(
    stress: float,
    delta: float,
    s_gain: float = 0.20,    # 论文Appendix A.5默认值
    s_relief: float = 0.10,  # 论文Appendix A.5默认值
) -> float:
    """Update stress based on scalar RPE (simplified version).

    注意：这是一个简化版本，不考虑失败状态和自然衰减。
    对于完整版本（包括失败处理和衰减），请使用 affect.stress_affect.update_stress

    论文公式 Section 3.7.3:
    Stress_{t+1} = clip(Stress_t + s * max(-δ,0) - s' * max(δ,0))

    解释:
    - δ > 0 (超预期): 压力下降
    - δ < 0 (低于预期): 压力上升

    Args:
        stress: Current stress [0,1]
        delta: RPE
        s_gain: Stress increase for negative RPE (论文默认0.20)
        s_relief: Stress decrease for positive RPE (论文默认0.10)

    Returns:
        Updated stress
    """
    if delta > 0:
        # Positive RPE reduces stress
        stress = max(0.0, stress - s_relief * delta)
    else:
        # Negative RPE increases stress (delta is negative, use abs)
        stress = min(1.0, stress + s_gain * abs(delta))
    return stress

# Wrapper for backward compatibility with tests that use s_gain/s_relief parameter names
# The full version with failure handling and decay is in stress_affect.py
def update_stress(
    stress: float,
    delta: float,
    s_gain: float = 0.20,    # 负RPE压力增益
    s_relief: float = 0.10,  # 正RPE压力缓解
    **kwargs  # Forward additional params to stress_affect.update_stress
) -> float:
    """Update stress with s_gain/s_relief parameter names for backward compatibility.

    This wrapper maps the test-friendly parameter names to stress_affect parameters:
    - s_gain -> s (negative RPE stress gain)
    - s_relief -> s_prime (positive RPE stress relief)

    Args:
        stress: Current stress [0,1]
        delta: RPE
        s_gain: Stress increase for negative RPE
        s_relief: Stress decrease for positive RPE
        **kwargs: Additional params passed to stress_affect.update_stress

    Returns:
        Updated stress
    """
    # Use the module-level import to avoid repeated imports
    if _stress_affect_available:
        return _update_stress_full(
            stress=stress,
            delta=delta,
            s=s_gain,
            s_prime=s_relief,
            **kwargs
        )
    else:
        # Fallback to simple version if stress_affect is not available
        if delta > 0:
            return max(0.0, stress - s_relief * delta)
        else:
            return min(1.0, stress + s_gain * abs(delta))


def update_stress_per_dimension(
    stress: float,
    rpe_per_dim: Dict[str, float],
    coefficients: Optional[Dict[str, Dict[str, float]]] = None,
) -> float:
    """Update stress based on per-dimension RPE.

    Paper Section 3.7.3 (enhanced):
    Stress_{t+1} = Stress_t + Σ_i s^(i)_gain max(-δ^(i),0) - Σ_i s^(i)_relief max(δ^(i),0)

    Different dimensions have different stress impact:
    - Homeostasis/Integrity negative RPE → higher stress
    - Meaning positive RPE → more stress relief

    Args:
        stress: Current stress [0,1]
        rpe_per_dim: Per-dimension RPEs δ^(i)_t
        coefficients: Per-dimension s_gain/s_relief coefficients

    Returns:
        Updated stress
    """
    if coefficients is None:
        coefficients = DEFAULT_STRESS_COEFFICIENTS

    delta_stress = 0.0
    for dim, rpe in rpe_per_dim.items():
        coef = coefficients.get(dim, {"s_gain": 0.1, "s_relief": 0.05})
        if rpe > 0:
            # Positive RPE reduces stress
            delta_stress -= coef["s_relief"] * rpe
        else:
            # Negative RPE increases stress
            delta_stress += coef["s_gain"] * abs(rpe)

    new_stress = max(0.0, min(1.0, stress + delta_stress))
    return new_stress


def update_affect(
    mood: float,
    stress: float,
    delta: float,
    k_plus: float = 0.25,
    k_minus: float = 0.30,
    s_gain: float = 0.20,
    s_relief: float = 0.10,
    failed: bool = False,
    decay: float = 0.01,
) -> Tuple[float, float]:
    """Update both mood and stress based on RPE.

    论文Section 3.7.3完整公式:
    Mood_{t+1} = clip(Mood_t + k_+ * max(δ,0) - k_- * max(-δ,0))
    Stress_{t+1} = clip(Stress_t + s * max(-δ,0) - s' * max(δ,0))

    修复: 添加 failed 和 decay 参数支持

    Args:
        mood: Current mood [0,1]
        stress: Current stress [0,1]
        delta: RPE δ_t
        k_plus: Mood gain for positive RPE
        k_minus: Mood loss for negative RPE
        s_gain: Stress increase for negative RPE
        s_relief: Stress decrease for positive RPE
        failed: Whether the action failed (增加额外压力)
        decay: Stress decay rate

    Returns:
        Tuple of (new_mood, new_stress)
    """
    new_mood = update_mood(mood, delta, k_plus, k_minus)
    # 修复: 直接使用参数名，避免 kwargs 冲突
    # update_stress 会将 s_gain 映射到 s，s_relief 映射到 s_prime
    # 然后传递 failed 和 decay
    if _stress_affect_available:
        new_stress = _update_stress_full(
            stress=stress,
            delta=delta,
            s=s_gain,
            s_prime=s_relief,
            failed=failed,
            decay=decay
        )
    else:
        # Fallback to simple version
        new_stress = update_stress_simple(stress, delta, s_gain, s_relief)
    return new_mood, new_stress


def update_affect_per_dimension(
    mood: float,
    stress: float,
    rpe_per_dim: Dict[str, float],
    mood_coefficients: Optional[Dict[str, Dict[str, float]]] = None,
    stress_coefficients: Optional[Dict[str, Dict[str, float]]] = None,
) -> Tuple[float, float]:
    """Update both mood and stress based on per-dimension RPE.

    Enhanced version supporting dimension-specific emotional impact.

    Args:
        mood: Current mood [0,1]
        stress: Current stress [0,1]
        rpe_per_dim: Per-dimension RPEs δ^(i)_t
        mood_coefficients: Per-dimension k_plus/k_minus coefficients
        stress_coefficients: Per-dimension s_gain/s_relief coefficients

    Returns:
        Tuple of (new_mood, new_stress)
    """
    new_mood = update_mood_per_dimension(mood, rpe_per_dim, mood_coefficients)
    new_stress = update_stress_per_dimension(stress, rpe_per_dim, stress_coefficients)
    return new_mood, new_stress
