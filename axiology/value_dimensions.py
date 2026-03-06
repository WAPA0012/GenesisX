"""Value Dimensions: Paper-Compliant Feature Extractors for 5 Core Dimensions

This module implements the complete feature extraction functions for all 5 value
dimensions as specified in the paper (v14, Section 3.5.1 and 3.5.2, Appendix A.4).

Paper References:
- Section 3.5.1: 5维核心价值向量定义
- Section 3.5.2: 局部效用函数
- Appendix A.4: Setpoints and Feature Definitions

Each dimension's feature function f^{(i)}(S_t) returns a value in [0, 1] where
higher values indicate better satisfaction of that dimension.

Author: Genesis X v14
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import math
import time


class ValueDimension(str, Enum):
    """5维核心价值向量 (v14)

    论文 Section 3.5.1:
    "定义价值维度数 n=5，本文采用核心5维集合"
    """
    HOMEOSTASIS = "homeostasis"  # 稳态：资源平衡、压力管理、系统稳定
    ATTACHMENT = "attachment"    # 依恋：社交连接、信任建立、忽视回避
    CURIOSITY = "curiosity"      # 好奇：新奇探索、信息增益、规律发现
    COMPETENCE = "competence"    # 胜任：任务成功、技能成长、效能感
    SAFETY = "safety"            # 安全：风险回避、损失预防、安全边际


@dataclass
class DimensionConfig:
    """配置参数 for a single dimension.

    包含论文中定义的所有参数默认值。
    """
    setpoint: float = 0.7        # f^{(i)*} 设定点
    weight: float = 0.2          # w^{(i)} 基础权重
    drift_limit: float = 0.05    # 每日漂移限制


# ============================================================================
# Default Setpoints (论文 Appendix A.4)
# ============================================================================

DEFAULT_SETPOINTS: Dict[ValueDimension, float] = {
    # 论文 Appendix A.4: Homeostasis setpoints
    # H_t = (Compute_t, Memory_t, 1-Stress_t), H*=(0.70, 0.70, 0.80)
    # 注意：这里使用 0.70 与 value_setpoints.yaml 保持一致
    # 0.70 是用户期望的资源稳态设定点
    ValueDimension.HOMEOSTASIS: 0.70,  # f^{homeo*} 默认 0.70（与配置文件一致）

    # Attachment: 通常接近 1（理想关系状态）
    ValueDimension.ATTACHMENT: 0.70,

    # Curiosity: 中等设定点（平衡探索与稳定）
    ValueDimension.CURIOSITY: 0.60,

    # Competence: 高设定点（追求高成功率）
    ValueDimension.COMPETENCE: 0.75,

    # Safety: 高设定点（风险回避优先）
    ValueDimension.SAFETY: 0.80,
}


# ============================================================================
# (1) HOMEOSTASIS: 资源稳态（数字原生版本）
# ============================================================================

def extract_homeostasis_feature(
    state: Dict[str, Any],
    setpoints: Optional[Dict[str, float]] = None
) -> float:
    """Extract Homeostasis feature f^{homeo}(S_t).

    论文 Section 3.5.2 (1) & Appendix A.4:

    H_t = (Compute_t, Memory_t, 1-Stress_t), H*=(Compute*, Memory*, 1-Stress*)

    f^{homeo}(S_t) = 1/3 * (Compute_t/Compute* + Memory_t/Memory* + (1-Stress_t)/(1-Stress*))

    Args:
        state: 必须包含 compute, memory, stress
        setpoints: 可选的设定点字典，默认使用论文值

    Returns:
        f^{homeo}(S_t) ∈ [0, 1], 越高表示稳态越满足
    """
    # 论文默认设定值 (Appendix A.4)
    # H* = (0.70, 0.70, 0.80) 其中第三项是 1-Stress*
    defaults = {
        "compute": 0.70,
        "memory": 0.70,
        "stress": 0.20,  # 1 - 0.80 = 0.20
    }
    if setpoints:
        defaults.update(setpoints)

    compute_star = defaults["compute"]
    memory_star = defaults["memory"]
    stress_star = defaults["stress"]  # 这是 Stress*，不是 1-Stress*

    # 当前状态值
    compute_t = state.get("compute", state.get("energy", 0.5))
    memory_t = state.get("memory", 0.5)
    stress_t = state.get("stress", 0.0)

    # 论文公式: f^{homeo}(S_t) = (1/3) * (Compute/Compute* + Memory/Memory* + (1-Stress)/(1-Stress*))
    # 注意: 1-Stress* = 1 - 0.20 = 0.80
    one_minus_stress_star = 1.0 - stress_star

    # 计算每个分项，限制在合理范围避免除零
    compute_ratio = min(2.0, compute_t / max(0.01, compute_star))
    memory_ratio = min(2.0, memory_t / max(0.01, memory_star))
    stress_ratio = min(2.0, (1.0 - stress_t) / max(0.01, one_minus_stress_star))

    # 加权平均
    feature = (compute_ratio + memory_ratio + stress_ratio) / 3.0

    return max(0.0, min(1.0, feature))


def compute_homeostasis_utility(
    state_t: Dict[str, Any],
    state_t1: Dict[str, Any],
    setpoints: Optional[Dict[str, float]] = None
) -> float:
    """Compute Homeostasis utility u^{homeo}_t.

    论文 Section 3.5.2 (1):

    u^{homeo}_t = ||H_t - H*||_1 - ||H_{t+1} - H*||_1

    为与统一的缺口定义一致，使用特征差值:
    u^{homeo}_t = f^{homeo}(S_{t+1}) - f^{homeo}(S_t)

    Args:
        state_t: 当前状态 S_t
        state_t1: 下一状态 S_{t+1}
        setpoints: 可选设定点

    Returns:
        u^{homeo}_t ∈ [-1, 1], 正值表示稳态改善
    """
    feature_t = extract_homeostasis_feature(state_t, setpoints)
    feature_t1 = extract_homeostasis_feature(state_t1, setpoints)

    utility = feature_t1 - feature_t
    return max(-1.0, min(1.0, utility))


# ============================================================================
# (2) ATTACHMENT: 关系增长 + 忽视惩罚
# ============================================================================

def compute_neglect_penalty(
    time_since_interaction: float,
    half_life_hours: float = 24.0
) -> float:
    """Compute neglect penalty using exponential decay.

    论文 Section 3.5.2 (2) & Appendix A.4:

    Neglect(Δt) = 1 - 2^(-Δt/T_half), T_half ≈ 24 hours

    Args:
        time_since_interaction: 距离上次交互的时间（小时）
        half_life_hours: 半衰期，默认24小时

    Returns:
        Neglect(Δt) ∈ [0, 1], 越高表示被忽视越久
    """
    if time_since_interaction <= 0:
        return 0.0

    # 论文公式: 1 - 2^(-t/half_life)
    neglect = 1.0 - (2.0 ** (-time_since_interaction / half_life_hours))
    return max(0.0, min(1.0, neglect))


def extract_attachment_feature(
    state: Dict[str, Any],
    time_since_interaction: Optional[float] = None,
    half_life_hours: float = 24.0
) -> float:
    """Extract Attachment feature f^{attach}(S_t).

    论文 Section 3.5.2 (2) & Appendix A.4:

    f^{attach}(S_t) = Relationship_t * (1 - Neglect(Δt_since))

    其中:
    - Relationship_t ∈ [0, 1] 合并了 Bond 和 Trust
    - Neglect(Δt) = 1 - 2^(-Δt/T_half)

    Args:
        state: 必须包含 relationship (或 bond/trust)
        time_since_interaction: 距离上次交互时间（小时），如果为None则从state获取
        half_life_hours: 忽视半衰期，默认24小时

    Returns:
        f^{attach}(S_t) ∈ [0, 1], 越高表示关系越稳固
    """
    # 获取 Relationship_t (合并了 Bond 和 Trust)
    relationship_t = state.get("relationship")
    if relationship_t is None:
        # 回退: 使用 bond 和 trust 的平均
        bond = state.get("bond", 0.0)
        trust = state.get("trust", 0.5)
        relationship_t = (bond + trust) / 2.0

    # 获取时间差
    if time_since_interaction is None:
        time_since_interaction = state.get("time_since_interaction", 0.0)

    # 计算忽视惩罚
    neglect = compute_neglect_penalty(time_since_interaction, half_life_hours)

    # 论文公式: f^{attach}(S_t) = Relationship_t * (1 - Neglect(Δt_since))
    feature = relationship_t * (1.0 - neglect)

    return max(0.0, min(1.0, feature))


def compute_attachment_utility(
    state_t: Dict[str, Any],
    state_t1: Dict[str, Any],
    time_since_interaction_t: Optional[float] = None,
    time_since_interaction_t1: Optional[float] = None,
    half_life_hours: float = 24.0,
    alpha: float = 0.5,
    beta: float = 0.5,
    gamma: float = 0.15
) -> float:
    """Compute Attachment utility u^{attach}_t.

    论文 Section 3.5.2 (2) (简化版本，直接使用特征差值):

    u^{attach}_t = f^{attach}(S_{t+1}) - f^{attach}(S_t)

    早期版本包含忽视惩罚项，但特征函数已包含忽视，直接差值即可。

    Args:
        state_t: 当前状态 S_t
        state_t1: 下一状态 S_{t+1}
        time_since_interaction_t: 当前时间差（小时）
        time_since_interaction_t1: 下一时间差（小时）
        half_life_hours: 半衰期
        alpha: Bond 变化权重
        beta: Trust 变化权重
        gamma: 忽视惩罚系数（论文 Appendix A.5: μ_att = 0.15）

    Returns:
        u^{attach}_t ∈ [-1, 1], 正值表示关系改善
    """
    feature_t = extract_attachment_feature(
        state_t, time_since_interaction_t, half_life_hours
    )
    feature_t1 = extract_attachment_feature(
        state_t1, time_since_interaction_t1, half_life_hours
    )

    utility = feature_t1 - feature_t
    return max(-1.0, min(1.0, utility))


# ============================================================================
# (3) CURIOSITY: 新奇 + 顿悟
# ============================================================================

def extract_curiosity_feature(
    state: Dict[str, Any],
    context: Dict[str, Any],
    novelty_weight: float = 0.7,
    insight_weight: float = 0.3
) -> float:
    """Extract Curiosity feature f^{cur}(S_t).

    论文 Section 3.5.2 (3) & Appendix A.4:

    f^{cur}(S_t) = 0.7 * Novelty_t + 0.3 * EMA_α(Q^{insight}_t)

    其中:
    - Novelty_t = 1 - max_{m∈M_t} sim(o_t, m) 为记忆相似度的补数
    - Q^{insight}_t 为洞察质量 EMA
    - α 为 EMA 系数（默认 0.1）

    **重要**: 这里需要使用语义新颖度而非简单的 boredom 反向代理。

    Args:
        state: 必须包含 novelty（或计算从记忆相似度）
        context: 包含 insight_quality_ema, 可选的记忆集合
        novelty_weight: Novelty 权重，默认 0.7
        insight_weight: 洞察质量权重，默认 0.3

    Returns:
        f^{cur}(S_t) ∈ [0, 1], 越高表示好奇驱动越满足
    """
    # 获取 Novelty_t
    novelty = state.get("novelty")

    if novelty is None and "observation_text" in state and "recent_memories" in context:
        # 如果没有预计算的新颖度，尝试从记忆计算
        novelty = _compute_semantic_novelty(
            state["observation_text"],
            context["recent_memories"]
        )

    if novelty is None:
        # 最后的回退: 使用 boredom 反向代理
        # 注意: 这不是论文公式，仅为兼容性保留
        boredom = state.get("boredom", 0.0)
        novelty = 1.0 - boredom

    novelty = max(0.0, min(1.0, novelty))

    # 获取洞察质量 EMA
    insight_quality_ema = context.get("insight_quality_ema", 0.5)
    insight_quality_ema = max(0.0, min(1.0, insight_quality_ema))

    # 论文公式: f^{cur}(S_t) = 0.7 * Novelty_t + 0.3 * EMA(Q^{insight}_t)
    feature = novelty_weight * novelty + insight_weight * insight_quality_ema

    return max(0.0, min(1.0, feature))


def _compute_semantic_novelty(
    observation_text: str,
    recent_memories: List[str],
    threshold: float = 0.85
) -> float:
    """Compute semantic novelty from observation and memories.

    论文 Section 3.5.2 (3):

    Novelty_t = 1 - max_{m∈M_t} sim(o_t, m)

    这里 sim 应该是语义相似度（余弦相似度）。

    Args:
        observation_text: 当前观察文本
        recent_memories: 最近记忆文本列表
        threshold: 新颖度阈值

    Returns:
        Novelty_t ∈ [0, 1], 越高表示越新奇
    """
    if not recent_memories:
        return 1.0  # 无记忆时完全新奇

    # 使用简单的词汇相似度作为回退
    # 实际部署应该使用嵌入向量
    max_similarity = 0.0
    obs_words = set(observation_text.lower().split())

    for memory in recent_memories:
        mem_words = set(memory.lower().split())
        if not obs_words or not mem_words:
            similarity = 0.0
        else:
            intersection = len(obs_words & mem_words)
            union = len(obs_words | mem_words)
            similarity = intersection / union if union > 0 else 0.0

        max_similarity = max(max_similarity, similarity)

    novelty = 1.0 - max_similarity
    return max(0.0, min(1.0, novelty))


def compute_curiosity_utility(
    state_t: Dict[str, Any],
    state_t1: Dict[str, Any],
    context_t: Dict[str, Any],
    context_t1: Dict[str, Any],
    novelty_weight: float = 0.7,
    insight_weight: float = 0.3
) -> float:
    """Compute Curiosity utility u^{curiosity}_t.

    论文 Section 3.5.2 (3):

    u^{curiosity}_t = f^{cur}(S_{t+1}) - f^{cur}(S_t) + Q^{insight}_t * 1(insight at t)

    Args:
        state_t: 当前状态 S_t
        state_t1: 下一状态 S_{t+1}
        context_t: 当前上下文（包含 insight_quality_ema, insight_formed）
        context_t1: 下一上下文
        novelty_weight: Novelty 权重
        insight_weight: 洞察权重

    Returns:
        u^{curiosity}_t ∈ [-1, 1], 正值表示好奇满足
    """
    feature_t = extract_curiosity_feature(state_t, context_t, novelty_weight, insight_weight)
    feature_t1 = extract_curiosity_feature(state_t1, context_t1, novelty_weight, insight_weight)

    # 检查是否有新洞察形成
    insight_formed = context_t1.get("insight_formed", False)
    insight_quality = context_t1.get("insight_quality", 0.0)

    # 洞察奖励
    insight_bonus = insight_quality if insight_formed else 0.0

    utility = (feature_t1 - feature_t) + insight_bonus
    return max(-1.0, min(1.0, utility))


# ============================================================================
# (4) COMPETENCE: 成功质量 + 技能固化
# ============================================================================

def extract_competence_feature(
    state: Dict[str, Any],
    context: Dict[str, Any],
    ema_alpha: float = 0.1
) -> float:
    """Extract Competence feature f^{cmp}(S_t).

    论文 Section 3.5.2 (4) & Appendix A.4:

    f^{cmp}(S_t) = EMA_{α_Q}(Q_t)

    即质量得分的指数移动平均。

    Args:
        state: 状态字典
        context: 必须包含 quality_score 或 success_rate
        ema_alpha: EMA 系数，默认 0.1

    Returns:
        f^{cmp}(S_t) ∈ [0, 1], 越高表示胜任感越强
    """
    # 尝试获取预计算的 EMA
    quality_ema = context.get("quality_score_ema")

    if quality_ema is not None:
        return max(0.0, min(1.0, quality_ema))

    # 否则从当前质量推断
    quality_score = context.get("quality_score")
    success_rate = context.get("success_rate")

    if quality_score is not None:
        return max(0.0, min(1.0, quality_score))

    if success_rate is not None:
        return max(0.0, min(1.0, success_rate))

    # 回退: 中等值
    return 0.5


def compute_competence_utility(
    state_t: Dict[str, Any],
    state_t1: Dict[str, Any],
    context_t: Dict[str, Any],
    context_t1: Dict[str, Any],
    eta1: float = 0.4,
    eta2: float = 0.4,
    kappa: float = 0.2,
    eta3: float = 0.3
) -> float:
    """Compute Competence utility u^{competence}_t.

    论文 Section 3.5.2 (4):

    u^{competence}_t = η1 * Success_t + η2 * Q_t + κ * (Cover(K_{t+1}) - Cover(K_t))

    其中:
    - η1 + η2 ≤ 1 (默认 η1=0.4, η2=0.4, κ=0.2)
    - η3 是失败惩罚系数（论文v4修正）

    Args:
        state_t: 当前状态
        state_t1: 下一状态
        context_t: 当前上下文
        context_t1: 下一上下文
        eta1: 成功奖励系数
        eta2: 质量奖励系数
        kappa: 技能覆盖系数
        eta3: 失败惩罚系数

    Returns:
        u^{competence}_t ∈ [-1, 1]
    """
    # 成功标志
    success = context_t1.get("success", 1.0)  # 默认成功
    success_val = 1.0 if success else 0.0

    # 质量得分
    quality = context_t1.get("quality_score", 0.5)

    # 技能覆盖变化
    skill_count_t = context_t.get("skill_count", 0)
    skill_count_t1 = context_t1.get("skill_count", skill_count_t)
    max_skills = context_t.get("max_skills", 20)

    cover_t = min(1.0, skill_count_t / max(1, max_skills))
    cover_t1 = min(1.0, skill_count_t1 / max(1, max_skills))
    cover_delta = cover_t1 - cover_t

    # 论文v4公式: η1*Success + η2*Q + κ*ΔCover - η3*(1-Success)
    failure = 1.0 - success_val
    utility = (
        eta1 * success_val +
        eta2 * quality +
        kappa * cover_delta -
        eta3 * failure
    )

    return max(-1.0, min(1.0, utility))


# ============================================================================
# (5) SAFETY: 风险回避（新增）
# ============================================================================

def compute_risk_score(
    state: Dict[str, Any],
    action: Optional[Dict[str, Any]] = None,
    tool_manifest: Optional[Dict[str, Any]] = None
) -> float:
    """Compute risk score RiskScore(S_t, a_t).

    论文 Section 3.5.2 (5) & Appendix A.6:

    RiskScore(a_t) ∈ {0, 0.5, 1} 由工具风险等级、资源消耗、不确定性综合确定

    本实现使用更细粒度的 [0, 1] 连续值。

    Args:
        state: 当前状态
        action: 执行的动作（可选）
        tool_manifest: 工具清单（可选）

    Returns:
        RiskScore ∈ [0, 1], 越高表示风险越大
    """
    # 基础风险来自最近错误
    recent_errors = state.get("recent_errors", 0)
    error_penalty = min(0.5, recent_errors * 0.1)

    # 工具风险
    tool_risk = 0.0
    if action and "tool_id" in action:
        tool_id = action["tool_id"]
        # 从工具清单获取风险等级
        if tool_manifest and "tools" in tool_manifest:
            tool_info = tool_manifest["tools"].get(tool_id, {})
            tool_risk = tool_info.get("risk_level", 0.0)
        else:
            # 默认风险映射
            risk_map = {
                "chat": 0.0,
                "file_read": 0.2,
                "file_write": 0.5,
                "web_search": 0.5,
                "code_exec": 1.0,
            }
            tool_risk = risk_map.get(tool_id, 0.3)

    # 资源压力风险
    resource_pressure = state.get("resource_pressure", 0.0)
    resource_risk = resource_pressure * 0.3

    # 不确定性（压力水平）
    stress = state.get("stress", 0.0)
    uncertainty_risk = stress * 0.2

    # 综合风险
    risk_score = (
        0.3 * error_penalty +
        0.4 * tool_risk +
        0.2 * resource_risk +
        0.1 * uncertainty_risk
    )

    return max(0.0, min(1.0, risk_score))


def extract_safety_feature(
    state: Dict[str, Any],
    context: Dict[str, Any]
) -> float:
    """Extract Safety feature f^{safe}(S_t).

    论文 Section 3.5.2 (5):

    f^{safe}(S_t) = 1 - RiskScore(S_t, a_t)

    Args:
        state: 当前状态
        context: 上下文（包含 action, tool_manifest）

    Returns:
        f^{safe}(S_t) ∈ [0, 1], 越高表示越安全
    """
    action = context.get("last_action")
    tool_manifest = context.get("tool_manifest")

    risk_score = compute_risk_score(state, action, tool_manifest)

    return 1.0 - risk_score


def compute_safety_utility(
    state_t: Dict[str, Any],
    state_t1: Dict[str, Any],
    context_t: Dict[str, Any],
    context_t1: Dict[str, Any]
) -> float:
    """Compute Safety utility u^{safety}_t.

    论文 Section 3.5.2 (5):

    u^{safety}_t = f^{safe}(S_{t+1}) - f^{safe}(S_t)

    Args:
        state_t: 当前状态
        state_t1: 下一状态
        context_t: 当前上下文
        context_t1: 下一上下文

    Returns:
        u^{safety}_t ∈ [-1, 1], 正值表示安全性提升
    """
    feature_t = extract_safety_feature(state_t, context_t)
    feature_t1 = extract_safety_feature(state_t1, context_t1)

    utility = feature_t1 - feature_t
    return max(-1.0, min(1.0, utility))


# ============================================================================
# 统一接口
# ============================================================================

def extract_all_features(
    state: Dict[str, Any],
    context: Dict[str, Any]
) -> Dict[ValueDimension, float]:
    """Extract features for all 5 dimensions.

    论文 Section 3.5.1 & 3.5.2

    Args:
        state: 当前状态 S_t
        context: 上下文信息

    Returns:
        Dict mapping each dimension to its feature value f^{(i)}(S_t) ∈ [0, 1]
    """
    return {
        ValueDimension.HOMEOSTASIS: extract_homeostasis_feature(state),
        ValueDimension.ATTACHMENT: extract_attachment_feature(state),
        ValueDimension.CURIOSITY: extract_curiosity_feature(state, context),
        ValueDimension.COMPETENCE: extract_competence_feature(state, context),
        ValueDimension.SAFETY: extract_safety_feature(state, context),
    }


def compute_all_utilities(
    state_t: Dict[str, Any],
    state_t1: Dict[str, Any],
    context_t: Dict[str, Any],
    context_t1: Dict[str, Any],
) -> Dict[ValueDimension, float]:
    """Compute utilities for all 5 dimensions.

    论文 Section 3.5.2

    Args:
        state_t: 当前状态 S_t
        state_t1: 下一状态 S_{t+1}
        context_t: 当前上下文
        context_t1: 下一上下文

    Returns:
        Dict mapping each dimension to its utility u^{(i)}_t ∈ [-1, 1]
    """
    return {
        ValueDimension.HOMEOSTASIS: compute_homeostasis_utility(state_t, state_t1),
        ValueDimension.ATTACHMENT: compute_attachment_utility(state_t, state_t1),
        ValueDimension.CURIOSITY: compute_curiosity_utility(
            state_t, state_t1, context_t, context_t1
        ),
        ValueDimension.COMPETENCE: compute_competence_utility(
            state_t, state_t1, context_t, context_t1
        ),
        ValueDimension.SAFETY: compute_safety_utility(
            state_t, state_t1, context_t, context_t1
        ),
    }


# ============================================================================
# 缺口计算 (用于动态权重)
# ============================================================================

def compute_drive_gaps(
    features: Dict[ValueDimension, float],
    setpoints: Dict[ValueDimension, float]
) -> Dict[ValueDimension, float]:
    """Compute drive gaps for all dimensions.

    论文 Section 3.6.1:

    d^{(i)}_t = max(0, f^{(i)*} - f^{(i)}(S_t))

    Args:
        features: 当前特征值 f^{(i)}(S_t)
        setpoints: 设定点 f^{(i)*}

    Returns:
        Dict mapping each dimension to its drive gap d^{(i)}_t ∈ [0, 1]
    """
    gaps = {}
    for dim in ValueDimension:
        feature = features.get(dim, 0.5)
        setpoint = setpoints.get(dim, DEFAULT_SETPOINTS.get(dim, 0.7))
        gap = max(0.0, setpoint - feature)
        gaps[dim] = gap
    return gaps


# ============================================================================
# 验证和测试
# ============================================================================

def validate_feature_ranges(features: Dict[ValueDimension, float]) -> bool:
    """Validate that all features are in [0, 1] range.

    论文要求: 所有特征 f^{(i)}(S_t) ∈ [0, 1]
    """
    for dim, value in features.items():
        if not (0.0 <= value <= 1.0):
            return False
    return True


def validate_utility_ranges(utilities: Dict[ValueDimension, float]) -> bool:
    """Validate that all utilities are in [-1, 1] range.

    论文要求: 所有效用 u^{(i)}_t ∈ [-1, 1]
    """
    for dim, value in utilities.items():
        if not (-1.0 <= value <= 1.0):
            return False
    return True


if __name__ == "__main__":
    # 测试基本功能
    print("Genesis X Value Dimensions (v14) - Paper-Compliant Implementation")
    print("=" * 60)

    # 示例状态
    state = {
        "compute": 0.8,
        "memory": 0.7,
        "stress": 0.2,
        "relationship": 0.6,
        "boredom": 0.3,
        "time_since_interaction": 2.0,  # 2小时
    }

    context = {
        "insight_quality_ema": 0.5,
        "quality_score": 0.7,
        "success": True,
        "skill_count": 10,
        "last_action": {"tool_id": "chat"},
    }

    # 提取特征
    features = extract_all_features(state, context)
    print("\nFeatures f^{(i)}(S_t):")
    for dim, value in features.items():
        print(f"  {dim.value:15s}: {value:.3f}")

    # 验证范围
    valid = validate_feature_ranges(features)
    print(f"\nFeature range validation: {'✓ PASS' if valid else '✗ FAIL'}")

    # 计算缺口
    setpoints = DEFAULT_SETPOINTS.copy()
    gaps = compute_drive_gaps(features, setpoints)
    print("\nDrive gaps d^{(i)}_t:")
    for dim, value in gaps.items():
        print(f"  {dim.value:15s}: {value:.3f} (setpoint: {setpoints[dim]:.2f})")
