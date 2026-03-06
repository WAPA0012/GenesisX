"""Unified utility computation module for 5-dimensional value system.

修复 v15: 使用5维核心价值向量 (论文 Section 3.5.1)
- HOMEOSTASIS: 稳态 - 资源平衡、压力管理、系统稳定
- ATTACHMENT: 依恋 - 社交连接、信任建立、忽视回避
- CURIOSITY: 好奇 - 新奇探索、信息增益、规律发现
- COMPETENCE: 胜任 - 任务成功、技能成长、效能感
- SAFETY: 安全 - 风险回避、损失预防、安全边际

删除的维度及其理由 (论文 Section 3.5.1):
- 删除 INTEGRITY：作为硬约束而非价值维度
- 删除 CONTRACT：重定位为影响权重的外部输入
- 删除 EFFICIENCY：并入 HOMEOSTASIS (资源节约本质上是稳态维持)
- 删除 MEANING：并入 CURIOSITY (高阶规律学习是好奇的高级满足形式)

Implements paper Section 3.5.2: 效用函数尺度归一化
All utility functions normalized to [-1, 1] range.
"""
from typing import Dict, Any, Optional, Tuple, List, Union
from dataclasses import dataclass
import math
from common.models import ValueDimension, CostVector


# ===== Utility Normalization Functions =====

def clip_utility(value: float, min_val: float = -1.0, max_val: float = 1.0) -> float:
    """Clip utility value to specified range.

    论文Section 3.5.2: 推荐将每个 u^(i) 限制在 [-1, 1] 或 [0, 1] 区间

    Args:
        value: Raw utility value
        min_val: Minimum allowed value (default -1.0)
        max_val: Maximum allowed value (default 1.0)

    Returns:
        Clipped utility in [min_val, max_val]
    """
    return max(min_val, min(max_val, value))


def normalize_utility(
    value: float,
    min_range: float,
    max_range: float,
    output_min: float = -1.0,
    output_max: float = 1.0,
) -> float:
    """Normalize utility value to output range.

    Args:
        value: Raw utility value
        min_range: Expected minimum input value
        max_range: Expected maximum input value
        output_min: Output minimum (default -1.0)
        output_max: Output maximum (default 1.0)

    Returns:
        Normalized utility in [output_min, output_max]
    """
    if max_range == min_range:
        return (output_min + output_max) / 2.0

    normalized = (value - min_range) / (max_range - min_range)
    output = output_min + normalized * (output_max - output_min)

    return clip_utility(output, output_min, output_max)


def tanh_normalize(value: float, scale: float = 1.0) -> float:
    """Normalize using tanh for smooth bounded output in [-1, 1].

    Args:
        value: Raw utility value
        scale: Scaling factor for input

    Returns:
        Normalized utility in [-1, 1]
    """
    return math.tanh(value / scale) if scale != 0 else 0.0


# ===== Utility Functions for Each Value Dimension (5维) =====

def utility_homeostasis(
    compute_current: float,
    compute_next: float,
    memory_current: float,
    memory_next: float,
    stress_current: float,
    stress_next: float,
    setpoints: Dict[str, float],
    d_max: float = 3.0,
) -> float:
    """Compute Homeostasis utility (论文 Section 3.5.2 (1)).

    数字原生版本：使用算力/内存双资源模型

    u^homeo_t = clip((||H_t - H*||_1 - ||H_{t+1} - H*||_1) / D_max, -1, 1)

    Where H = (Compute, Memory, 1-Stress) and H* = (C*, M*, 1-S*)

    Args:
        compute_current, compute_next: 算力可用度 [0, 1]
        memory_current, memory_next: 内存可用度 [0, 1]
        stress_current, stress_next: 压力 [0, 1]
        setpoints: Dict with "compute", "memory", "stress" setpoints
        d_max: Maximum L1 distance for normalization (default 3.0)

    Returns:
        Utility in [-1, 1]
    """
    c_star = setpoints.get("compute", 0.8)
    m_star = setpoints.get("memory", 0.8)
    s_star = setpoints.get("stress", 0.2)  # 压力设定点较低
    # 使用 (1-stress) 使得压力越小越好
    inv_s_star = 1.0 - s_star

    # Current distance: ||H_t - H*||_1
    dist_current = (
        abs(compute_current - c_star) +
        abs(memory_current - m_star) +
        abs((1.0 - stress_current) - inv_s_star)
    )

    # Next distance: ||H_{t+1} - H*||_1
    dist_next = (
        abs(compute_next - c_star) +
        abs(memory_next - m_star) +
        abs((1.0 - stress_next) - inv_s_star)
    )

    # Utility: improvement in homeostasis
    utility = (dist_current - dist_next) / d_max

    return clip_utility(utility, -1.0, 1.0)


def utility_attachment(
    relationship_current: float,
    relationship_next: float,
    time_since_interaction: float,
    t_half: float = 24.0 * 3600.0,  # 论文Section 3.5.2: T_half默认24小时（秒）
    alpha: float = 0.5,
    gamma: float = 0.15,  # 修复 M1: μ_att = 0.15
) -> float:
    """Compute Attachment utility (论文 Section 3.5.2 (2)).

    u^attach_t = α·ΔRelationship - γ·Neglect(Δt)

    其中 Relationship_t = Bond_t · (1 - Neglect(Δt_since))

    Args:
        relationship_current, relationship_next: 关系强度 [0, 1]
        time_since_interaction: 距上次交互时间（秒）
        t_half: 忽视半衰期（秒）
        alpha: 关系增长系数
        gamma: 忽视惩罚系数

    Returns:
        Utility in [-1, 1]
    """
    # 关系变化
    relationship_delta = relationship_next - relationship_current

    # 忽视惩罚 (converts time to [0, 1])
    neglect = 1.0 - (2.0 ** (-time_since_interaction / t_half))
    neglect = max(0.0, min(1.0, neglect))

    # Combined utility
    utility = alpha * relationship_delta - gamma * neglect

    return clip_utility(utility, -1.0, 1.0)


def utility_curiosity(
    novelty_current: float,
    novelty_next: float,
    insight_quality: float = 0.0,
    insight_formed: bool = False,
    novelty_ema_baseline: float = None,
    alpha_insight: float = 0.3,
) -> float:
    """Compute Curiosity utility (论文 Section 3.5.2 (3)).

    u^curiosity_t = ΔNovelty + α_insight · Q^insight · 1(insight formed)

    修复 M3: 使用EMA基线 N_bar 而非时间步差值
    Meaning 维度已并入 Curiosity (论文 Section 3.5.1)

    Args:
        novelty_current, novelty_next: 新奇度 [0, 1]
        insight_quality: 洞察质量 [0, 1]
        insight_formed: 是否形成洞察
        novelty_ema_baseline: EMA基线
        alpha_insight: 洞察权重

    Returns:
        Utility in [-1, 1]
    """
    # 新奇度变化
    baseline = novelty_ema_baseline if novelty_ema_baseline is not None else novelty_current
    novelty_utility = novelty_next - baseline

    # 洞察奖励 (Meaning 并入 Curiosity)
    insight_bonus = 0.0
    if insight_formed:
        insight_bonus = alpha_insight * insight_quality

    utility = novelty_utility + insight_bonus

    return clip_utility(utility, -1.0, 1.0)


def utility_competence(
    success: bool,
    quality: float,
    skill_coverage_delta: float = 0.0,
    eta1: float = 0.4,
    eta2: float = 0.3,
    kappa: float = 0.3,
    eta3: float = 0.30,  # 修复 M2: 论文v4 失败惩罚系数 η_3=0.30
) -> float:
    """Compute Competence utility (论文 Section 3.5.2 (4)).

    u^competence_t = clip(η1·Success + η2·Q + κ·ΔCover - η_3·(1-Success), -1, 1)

    修复 M2: 添加失败惩罚项 -η_3·(1-Success)，使效用对称到 [-1, 1]。

    Args:
        success: Whether action succeeded
        quality: Quality score [0, 1]
        skill_coverage_delta: Change in skill coverage
        eta1: Success coefficient
        eta2: Quality coefficient
        kappa: Skill coefficient
        eta3: Failure penalty coefficient (论文默认 0.30)

    Returns:
        Utility in [-1, 1]
    """
    success_val = 1.0 if success else 0.0
    failure_val = 1.0 - success_val  # 1 if failed, 0 if succeeded

    utility = eta1 * success_val + eta2 * quality + kappa * skill_coverage_delta - eta3 * failure_val

    return clip_utility(utility, -1.0, 1.0)


def utility_safety(
    risk_score_current: float,
    risk_score_next: float,
) -> float:
    """Compute Safety utility (论文 Section 3.5.2 (5)).

    u^safety_t = f^{safe}(S_{t+1}) - f^{safe}(S_t)

    其中 f^{safe}(S_t) = 1 - RiskScore(S_t, a_t)

    RiskScore ∈ [0, 1] 综合了工具风险等级、资源消耗、不确定性

    Args:
        risk_score_current: 当前风险分数 [0, 1]
        risk_score_next: 下一步风险分数 [0, 1]

    Returns:
        Utility in [-1, 1]
    """
    # 安全特征 = 1 - 风险分数
    safety_current = 1.0 - risk_score_current
    safety_next = 1.0 - risk_score_next

    # 效用 = 安全特征变化
    utility = safety_next - safety_current

    return clip_utility(utility, -1.0, 1.0)


# ===== Legacy utility functions for backward compatibility =====

def utility_integrity(
    personality_drift: float,
    max_drift: float = 0.1,
    action_feasible: bool = True,
) -> float:
    """Compute Integrity utility.

    DEPRECATED: Integrity 已删除，重定向到 Safety (论文 Section 3.5.1)
    """
    # Integrity 作为硬约束，通过 Safety 实现
    # 如果人格漂移过大，风险分数增加
    risk = min(1.0, personality_drift / max_drift) if max_drift > 0 else 0.0
    if not action_feasible:
        risk = 1.0
    return utility_safety(0.0, risk)


def utility_contract(
    progress_current: float,
    progress_next: float,
) -> float:
    """Compute Contract utility.

    DEPRECATED: Contract 已删除，重定向到 Attachment (论文 Section 3.5.1)
    """
    # 契约完成可视为关系维护的一种方式
    return utility_attachment(progress_current, progress_next, 0.0)


def utility_meaning(
    insight_formed: bool,
    insight_quality: float = 0.0,
) -> float:
    """Compute Meaning utility.

    DEPRECATED: Meaning 已并入 Curiosity (论文 Section 3.5.1)
    """
    return utility_curiosity(0.0, 0.0, insight_quality, insight_formed)


def utility_efficiency(
    cost_time: float,
    cost_io: float,
    cost_net: float,
    cost_tokens: float,
    caps: Dict[str, Any],
) -> float:
    """Compute Efficiency utility.

    DEPRECATED: Efficiency 已并入 Homeostasis (论文 Section 3.5.1)
    """
    # 资源效率可视为稳态维持的一部分
    # 计算总成本并返回负效用
    time_cost = min(1.0, cost_time / caps.get("time", 10.0))
    io_cost = min(1.0, cost_io / caps.get("io", 20))
    net_cost = min(1.0, cost_net / caps.get("net", 2 * 1024 * 1024))
    token_cost = min(1.0, cost_tokens / caps.get("tokens", 4000))

    total_cost = (time_cost + io_cost + net_cost + token_cost) / 4.0
    return -total_cost


# ===== Simplified utility computation for state-based usage =====

def compute_utility(
    dimension: ValueDimension,
    feature: float,
    setpoint: float,
    prev_feature: float = None,
    cost: CostVector = None,
    state: Dict = None,
    context: Dict = None,
) -> float:
    """Compute normalized utility for a dimension.

    论文Section 3.5.2: Each dimension has specific utility function.

    All utilities normalized to [-1, 1] range.

    Args:
        dimension: Value dimension
        feature: Current feature value f^(i)(S_t)
        setpoint: Target setpoint f^(i)*
        prev_feature: Previous feature value f^(i)(S_{t-1})
        cost: Resource cost (for Efficiency dimension)
        state: Current state dict
        context: Current context dict

    Returns:
        Normalized utility u^(i) ∈ [-1, 1]
    """
    if state is None:
        state = {}
    if context is None:
        context = {}

    if dimension == ValueDimension.HOMEOSTASIS:
        return _utility_homeostasis_simple(feature, setpoint, state)
    elif dimension == ValueDimension.ATTACHMENT:
        return _utility_attachment_simple(feature, setpoint, prev_feature, state, context)
    elif dimension == ValueDimension.CURIOSITY:
        return _utility_curiosity_simple(feature, setpoint, prev_feature, context)
    elif dimension == ValueDimension.COMPETENCE:
        return _utility_competence_simple(feature, setpoint, prev_feature, context)
    elif dimension == ValueDimension.SAFETY:
        return _utility_safety_simple(feature, setpoint, context)

    # Legacy dimensions for backward compatibility
    elif isinstance(dimension, str):
        dim_lower = dimension.lower()
        if dim_lower == "integrity":
            return _utility_safety_simple(feature, setpoint, context)
        elif dim_lower == "contract":
            return _utility_attachment_simple(feature, setpoint, prev_feature, state, context)
        elif dim_lower == "meaning":
            return _utility_curiosity_simple(feature, setpoint, prev_feature, context)
        elif dim_lower == "efficiency":
            return _utility_homeostasis_simple(feature, setpoint, state)

    return 0.0


def _utility_homeostasis_simple(feature: float, setpoint: float, state: Dict) -> float:
    """Paper-compliant homeostasis utility (数字原生版本)."""
    if state is None:
        state = {}

    # 使用数字原生资源模型
    compute = state.get("compute", 0.8)
    memory = state.get("memory", 0.8)
    stress = state.get("stress", 0.2)

    # 计算当前特征
    current_feature = (compute + memory + (1.0 - stress)) / 3.0

    # 效用 = 特征变化
    utility = feature - current_feature

    return clip_utility(utility, -1.0, 1.0)


def _utility_safety_simple(feature: float, setpoint: float, context: Dict) -> float:
    """Paper-compliant safety utility."""
    if context is None:
        context = {}

    # 获取当前风险分数
    risk_current = context.get("risk_score", 0.0)
    safety_current = 1.0 - risk_current

    # 安全特征 = 1 - 风险分数
    safety_next = feature  # feature 就是 safety

    # 效用 = 安全特征变化
    utility = safety_next - safety_current

    return clip_utility(utility, -1.0, 1.0)


def _utility_attachment_simple(
    feature: float,
    setpoint: float,
    prev_feature: float = None,
    state: Dict = None,
    context: Dict = None,
) -> float:
    """Simplified attachment utility."""
    if state is None:
        state = {}
    if context is None:
        context = {}

    relationship = state.get("relationship", feature)
    prev_relationship = state.get("prev_relationship", relationship)

    # 忽视惩罚
    neglect_hours = context.get("neglect_hours", 0.0) / 3600.0  # 转换为小时
    half_life_hours = context.get("neglect_half_life", 24.0)
    neglect = 1.0 - (2.0 ** (-neglect_hours / half_life_hours))

    # Compute utility
    alpha = 0.5
    mu_att = 0.15  # 论文默认: μ_att = 0.15
    u = alpha * (relationship - prev_relationship) - mu_att * neglect

    return clip_utility(u, -1.0, 1.0)


def _utility_curiosity_simple(
    feature: float,
    setpoint: float,
    prev_feature: float = None,
    context: Dict = None,
) -> float:
    """Paper-compliant curiosity utility (包含Meaning)."""
    if context is None:
        context = {}

    # 新奇度变化
    if prev_feature is not None:
        delta_feature = feature - prev_feature
    else:
        delta_feature = 0.0

    # 洞察奖励 (Meaning 并入 Curiosity)
    insight_formed = context.get("insight_formed", False)
    insight_quality = context.get("insight_quality", 0.0)

    insight_bonus = 0.0
    if insight_formed:
        insight_bonus = 0.3 * insight_quality

    utility = delta_feature + insight_bonus

    return clip_utility(utility, -1.0, 1.0)


def _utility_competence_simple(
    feature: float,
    setpoint: float,
    prev_feature: float = None,
    context: Dict = None,
) -> float:
    """Simplified competence utility (修复 M2: 含失败惩罚)."""
    if context is None:
        context = {}

    success = context.get("success", 0.0)
    quality = context.get("quality_score", feature)
    skill_delta = context.get("skill_coverage_delta", 0.0)

    eta1, eta2, kappa = 0.4, 0.3, 0.3
    eta3 = 0.30  # 修复 M2: 论文v4 失败惩罚系数
    failure = 1.0 - success
    u = eta1 * success + eta2 * quality + kappa * skill_delta - eta3 * failure

    return clip_utility(u, -1.0, 1.0)


# ===== Batch computation =====

def compute_all_utilities(
    features: Dict[ValueDimension, float],
    setpoints: Dict[ValueDimension, float],
    state: Dict = None,
    context: Dict = None,
) -> Dict[ValueDimension, float]:
    """Compute utilities for all 5 dimensions.

    论文Section 3.5.2: 所有效用函数归一化到可比范围

    Args:
        features: Feature values f^(i)(S_t) for each dimension
        setpoints: Setpoint values f^(i)* for each dimension
        state: Current state
        context: Current context

    Returns:
        Dictionary of normalized utilities u^(i) ∈ [-1, 1]
    """
    if state is None:
        state = {}
    if context is None:
        context = {}

    utilities = {}

    for dim in ValueDimension:
        feature = features.get(dim, 0.5)
        setpoint = setpoints.get(dim, 0.5)

        prev_feature_key = f"prev_{dim.value}"
        prev_feature = state.get(prev_feature_key, None)

        cost = context.get("cost", None)

        utilities[dim] = compute_utility(
            dimension=dim,
            feature=feature,
            setpoint=setpoint,
            prev_feature=prev_feature,
            cost=cost,
            state=state,
            context=context,
        )

    return utilities


# ===== Legacy compute_utilities for backward compatibility =====

def compute_utilities(
    features: Dict[ValueDimension, float],
    setpoints: Dict[ValueDimension, float],
) -> Dict[ValueDimension, float]:
    """Legacy simplified utility computation.

    DEPRECATED: Use compute_all_utilities for paper-compliant computation.
    """
    utilities = {}

    for dim in ValueDimension:
        feature = features.get(dim, 0.5)
        setpoint = setpoints.get(dim, 0.5)

        distance = abs(feature - setpoint)
        utility = -distance
        utility = max(-1.0, min(1.0, utility))

        utilities[dim] = utility

    return utilities


# ===== Verification function =====

def verify_utility_normalization(
    utilities_or_calculator,
    u_min: float = -1.0,
    u_max: float = 1.0,
    num_samples: int = 100,
) -> Union[Tuple[bool, Dict[str, Any]], Dict[str, Any]]:
    """Verify that all utilities are within normalized range.

    论文Section 3.5.2: 效用函数尺度归一化
    """
    # Detect if first arg is a calculator
    if hasattr(utilities_or_calculator, 'compute_homeostasis'):
        return verify_utility_normalization_with_calculator(utilities_or_calculator, num_samples)

    # Original utilities dict signature
    utilities = utilities_or_calculator
    violations = {}
    all_normalized = True

    for dim, u in utilities.items():
        dim_name = dim.value if hasattr(dim, 'value') else str(dim)

        if u < u_min or u > u_max:
            all_normalized = False
            violations[dim_name] = {
                "value": u,
                "min": u_min,
                "max": u_max,
                "diff_min": u_min - u if u < u_min else 0,
                "diff_max": u - u_max if u > u_max else 0,
            }

    report = {
        "all_normalized": all_normalized,
        "violations": violations,
        "count": len(violations),
        "utilities": {dim.value if hasattr(dim, 'value') else str(dim): u for dim, u in utilities.items()},
    }

    return all_normalized, report


def verify_utility_normalization_with_calculator(
    calculator,
    num_samples: int = 100,
) -> Dict[str, Any]:
    """Verify utility normalization using a UtilityCalculator instance."""
    import random
    from common.models import CostVector

    utility_ranges = {}
    violations = []

    for _ in range(num_samples):
        state_kwargs = {
            "compute": random.random(),
            "memory": random.random(),
            "stress": random.random(),
            "relationship": random.random(),
            "neglect_hours": random.random() * 100000,
            "success": random.choice([True, False]),
            "quality_score": random.random(),
            "skill_coverage_delta": random.random() - 0.5,
            "novelty": random.random(),
            "insight_formed": random.choice([True, False]),
            "insight_quality": random.random() if random.random() > 0.5 else 0.0,
            "risk_score": random.random(),
        }

        state_t_kwargs = state_kwargs.copy()
        state_t1_kwargs = state_kwargs.copy()

        cost = CostVector(
            cpu_tokens=random.randint(0, 5000),
            io_ops=random.randint(0, 1000),
            net_bytes=random.randint(0, 1000000),
            latency_ms=random.randint(0, 10000),
        )

        # Test each utility function (5维)
        utilities = {
            "homeostasis": calculator.compute_homeostasis(
                type('StateSnapshot', (), state_t_kwargs)(),
                type('StateSnapshot', (), state_t1_kwargs)()
            ),
            "attachment": calculator.compute_attachment(
                type('StateSnapshot', (), state_t_kwargs)(),
                type('StateSnapshot', (), state_t1_kwargs)()
            ),
            "curiosity": calculator.compute_curiosity(
                type('StateSnapshot', (), state_t_kwargs)(),
                type('StateSnapshot', (), state_t1_kwargs)()
            ),
            "competence": calculator.compute_competence(
                type('StateSnapshot', (), state_t_kwargs)(),
                type('StateSnapshot', (), state_t1_kwargs)()
            ),
            "safety": calculator.compute_safety(
                type('StateSnapshot', (), state_t_kwargs)(),
                type('StateSnapshot', (), state_t1_kwargs)()
            ),
        }

        for dim, u in utilities.items():
            if dim not in utility_ranges:
                utility_ranges[dim] = [u, u]
            else:
                utility_ranges[dim][0] = min(utility_ranges[dim][0], u)
                utility_ranges[dim][1] = max(utility_ranges[dim][1], u)

            if u < -1.0 or u > 1.0:
                violations.append(f"{dim}: {u} out of [-1, 1]")

    return {
        "all_normalized": len(violations) == 0,
        "violations": violations,
        "ranges": {k: (v[0], v[1]) for k, v in utility_ranges.items()},
    }


__all__ = [
    # Normalization functions
    "clip_utility",
    "normalize_utility",
    "tanh_normalize",
    # 5维效用函数
    "utility_homeostasis",
    "utility_attachment",
    "utility_curiosity",
    "utility_competence",
    "utility_safety",
    # Legacy效用函数 (已废弃)
    "utility_integrity",
    "utility_contract",
    "utility_meaning",
    "utility_efficiency",
    # 批量计算
    "compute_utility",
    "compute_all_utilities",
    "compute_utilities",
    # 验证
    "verify_utility_normalization",
    "verify_utility_normalization_with_calculator",
]
