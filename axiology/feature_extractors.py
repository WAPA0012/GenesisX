"""Feature extractors for 5 value dimensions (Paper-Compliant v14).

This module provides feature extraction functions that strictly follow the paper
formulas in Section 3.5.1, 3.5.2, and Appendix A.4.

Each dimension's feature function f^{(i)}(S_t) returns a value in [0, 1].

Paper References:
- Section 3.5.1: 5维核心价值向量定义
- Section 3.5.2: 局部效用函数
- Appendix A.4: Setpoints and Feature Definitions

Migration Notes:
- v14: 简化到5维核心价值系统
- 旧版8维度的特征函数保留为 legacy 函数
"""

from typing import Dict, Any, Optional, List
from common.models import ValueDimension
import math


# ============================================================================
# Default Setpoints (论文 Appendix A.4)
# ============================================================================

DEFAULT_SETPOINTS = {
    ValueDimension.HOMEOSTASIS: 0.85,  # f^{homeo*} 默认 0.85
    ValueDimension.ATTACHMENT: 0.70,
    ValueDimension.CURIOSITY: 0.60,
    ValueDimension.COMPETENCE: 0.75,
    ValueDimension.SAFETY: 0.80,
}


# ============================================================================
# (1) HOMEOSTASIS: 资源稳态（数字原生版本）
# ============================================================================

def extract_homeostasis(
    state: Dict,
    setpoints: Optional[Dict[str, float]] = None
) -> float:
    """Extract Homeostasis feature f^{homeo}(S_t).

    论文 Section 3.5.2 (1) & Appendix A.4:

    H_t = (Compute_t, Memory_t, 1-Stress_t)
    H* = (Compute*, Memory*, 1-Stress*) = (0.70, 0.70, 0.80)

    f^{homeo}(S_t) = (1/3) * (Compute_t/Compute* + Memory_t/Memory* + (1-Stress_t)/(1-Stress*))

    Args:
        state: 必须包含 compute, memory, stress
        setpoints: 可选的设定点，默认使用论文值

    Returns:
        f^{homeo}(S_t) ∈ [0, 1]
    """
    # 论文默认设定值
    compute_star = 0.70
    memory_star = 0.70
    stress_star = 0.20  # 1 - 0.80 = 0.20

    if setpoints:
        compute_star = setpoints.get("compute", compute_star)
        memory_star = setpoints.get("memory", memory_star)
        stress_star = setpoints.get("stress", stress_star)

    # 当前状态
    compute_t = state.get("compute", state.get("energy", 0.5))
    memory_t = state.get("memory", 0.5)
    stress_t = state.get("stress", 0.0)

    # 论文公式
    one_minus_stress_star = 1.0 - stress_star
    compute_ratio = min(2.0, compute_t / max(0.01, compute_star))
    memory_ratio = min(2.0, memory_t / max(0.01, memory_star))
    stress_ratio = min(2.0, (1.0 - stress_t) / max(0.01, one_minus_stress_star))

    feature = (compute_ratio + memory_ratio + stress_ratio) / 3.0
    return max(0.0, min(1.0, feature))


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
        half_life_hours: 半衰期

    Returns:
        Neglect(Δt) ∈ [0, 1]
    """
    if time_since_interaction <= 0:
        return 0.0

    neglect = 1.0 - (2.0 ** (-time_since_interaction / half_life_hours))
    return max(0.0, min(1.0, neglect))


def extract_attachment(
    state: Dict,
    time_since_interaction: Optional[float] = None,
    half_life_hours: float = 24.0
) -> float:
    """Extract Attachment feature f^{attach}(S_t).

    论文 Section 3.5.2 (2) & Appendix A.4:

    f^{attach}(S_t) = Relationship_t * (1 - Neglect(Δt_since))

    Args:
        state: 必须包含 relationship (或 bond/trust)
        time_since_interaction: 距离上次交互时间（小时）
        half_life_hours: 半衰期

    Returns:
        f^{attach}(S_t) ∈ [0, 1]
    """
    # 获取 Relationship_t
    relationship_t = state.get("relationship")
    if relationship_t is None:
        bond = state.get("bond", 0.0)
        trust = state.get("trust", 0.5)
        relationship_t = (bond + trust) / 2.0

    # 获取时间差
    if time_since_interaction is None:
        time_since_interaction = state.get("time_since_interaction", 0.0)

    # 计算忽视惩罚
    neglect = compute_neglect_penalty(time_since_interaction, half_life_hours)

    # 论文公式
    feature = relationship_t * (1.0 - neglect)
    return max(0.0, min(1.0, feature))


# ============================================================================
# (3) CURIOSITY: 新奇 + 顿悟
# ============================================================================

def _compute_semantic_novelty(
    observation_text: str,
    recent_memories: List[str],
    threshold: float = 0.85
) -> float:
    """Compute semantic novelty from observation and memories.

    论文 Section 3.5.2 (3):

    Novelty_t = 1 - max_{m∈M_t} sim(o_t, m)

    使用嵌入向量计算语义相似度。如果不可用，回退到词汇相似度。
    """
    if not recent_memories:
        return 1.0

    # 尝试使用语义新颖度计算器
    try:
        from memory.semantic_novelty import SemanticNoveltyCalculator, EmbeddingConfig

        calc = SemanticNoveltyCalculator(EmbeddingConfig.for_tfidf())
        novelty, _ = calc.compute_novelty(observation_text, recent_memories, threshold)
        return max(0.0, min(1.0, novelty))
    except Exception:
        # 回退到词汇相似度
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


def extract_curiosity(
    state: Dict,
    context: Dict,
    novelty_weight: float = 0.7,
    insight_weight: float = 0.3
) -> float:
    """Extract Curiosity feature f^{cur}(S_t).

    论文 Section 3.5.2 (3) & Appendix A.4:

    f^{cur}(S_t) = 0.7 * Novelty_t + 0.3 * EMA_α(Q^{insight}_t)

    其中 Novelty_t = 1 - max_{m∈M_t} sim(o_t, m)

    Args:
        state: 必须包含 novelty 或 observation_text
        context: 包含 insight_quality_ema, recent_memories
        novelty_weight: Novelty 权重，默认 0.7
        insight_weight: 洞察权重，默认 0.3

    Returns:
        f^{cur}(S_t) ∈ [0, 1]
    """
    # 获取 Novelty_t
    novelty = state.get("novelty")

    if novelty is None:
        # 尝试从观察和记忆计算
        observation = state.get("observation_text", state.get("current_observation", ""))
        recent_memories = context.get("recent_memories", [])

        if observation and recent_memories:
            novelty = _compute_semantic_novelty(observation, recent_memories)
        else:
            # 最后回退: boredom 反向代理
            boredom = state.get("boredom", 0.0)
            novelty = 1.0 - boredom

    novelty = max(0.0, min(1.0, novelty))

    # 获取洞察质量 EMA
    insight_quality_ema = context.get("insight_quality_ema", 0.5)
    insight_quality_ema = max(0.0, min(1.0, insight_quality_ema))

    # 论文公式
    feature = novelty_weight * novelty + insight_weight * insight_quality_ema
    return max(0.0, min(1.0, feature))


# ============================================================================
# (4) COMPETENCE: 成功质量 + 技能固化
# ============================================================================

def extract_competence(
    state: Dict,
    context: Dict
) -> float:
    """Extract Competence feature f^{cmp}(S_t).

    论文 Section 3.5.2 (4) & Appendix A.4:

    f^{cmp}(S_t) = EMA_{α_Q}(Q_t)

    即质量得分的指数移动平均。

    Args:
        state: 状态字典
        context: 包含 quality_score_ema, quality_score, success_rate

    Returns:
        f^{cmp}(S_t) ∈ [0, 1]
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

    return 0.5


# ============================================================================
# (5) SAFETY: 风险回避
# ============================================================================

def compute_risk_score(
    state: Dict,
    action: Optional[Dict] = None,
    tool_manifest: Optional[Dict] = None
) -> float:
    """Compute risk score RiskScore(S_t, a_t).

    论文 Section 3.5.2 (5) & Appendix A.6:

    RiskScore(a_t) ∈ {0, 0.5, 1} 由工具风险等级、资源消耗、不确定性综合确定

    Args:
        state: 当前状态
        action: 执行的动作
        tool_manifest: 工具清单

    Returns:
        RiskScore ∈ [0, 1]
    """
    # 基础风险来自最近错误
    recent_errors = state.get("recent_errors", 0)
    error_penalty = min(0.5, recent_errors * 0.1)

    # 工具风险
    tool_risk = 0.0
    if action and "tool_id" in action:
        tool_id = action["tool_id"]
        if tool_manifest and "tools" in tool_manifest:
            tool_info = tool_manifest["tools"].get(tool_id, {})
            tool_risk = tool_info.get("risk_level", 0.0)
        else:
            # 默认风险映射
            risk_map = {
                "chat": 0.0,
                "qianwen_chat": 0.0,
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


def extract_safety(
    state: Dict,
    context: Dict
) -> float:
    """Extract Safety feature f^{safe}(S_t).

    论文 Section 3.5.2 (5):

    f^{safe}(S_t) = 1 - RiskScore(S_t, a_t)

    Args:
        state: 当前状态
        context: 包含 action, tool_manifest

    Returns:
        f^{safe}(S_t) ∈ [0, 1]
    """
    action = context.get("last_action")
    tool_manifest = context.get("tool_manifest")

    risk_score = compute_risk_score(state, action, tool_manifest)
    return 1.0 - risk_score


# ============================================================================
# 统一接口
# ============================================================================

def extract_all_features(
    state: Dict,
    context: Dict
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
        ValueDimension.HOMEOSTASIS: extract_homeostasis(state),
        ValueDimension.ATTACHMENT: extract_attachment(state),
        ValueDimension.CURIOSITY: extract_curiosity(state, context),
        ValueDimension.COMPETENCE: extract_competence(state, context),
        ValueDimension.SAFETY: extract_safety(state, context),
    }


# ============================================================================
# Legacy functions (向后兼容)
# ============================================================================

def extract_integrity(state: Dict, context: Dict) -> float:
    """Legacy integrity feature extraction.

    DEPRECATED: Use extract_safety instead.
    Integrity was replaced by Safety in v14.
    """
    return extract_safety(state, context)


def extract_contract(state: Dict, context: Dict) -> float:
    """Legacy contract feature extraction.

    DEPRECATED: Contract is no longer a value dimension in v14.
    Returns attachment-related value for backward compatibility.
    """
    has_command = state.get("has_active_command", False)
    if not has_command:
        return 0.8
    progress = state.get("command_progress", 0.0)
    return max(0.0, min(1.0, progress))


def extract_meaning(state: Dict, context: Dict) -> float:
    """Legacy meaning feature extraction.

    DEPRECATED: Meaning is merged into Curiosity in v14.
    """
    return extract_curiosity(state, context)


def extract_efficiency(state: Dict, context: Dict) -> float:
    """Legacy efficiency feature extraction.

    DEPRECATED: Efficiency is merged into Homeostasis in v14.
    """
    tokens_used = state.get("tokens_used", 0)
    budget_tokens = context.get("budget_tokens", 10000)
    usage_ratio = tokens_used / max(1, budget_tokens)
    return max(0.0, min(1.0, 1.0 - usage_ratio))


if __name__ == "__main__":
    # 测试
    print("Feature Extractors (v14 Paper-Compliant)")
    print("=" * 50)

    state = {
        "compute": 0.8,
        "memory": 0.7,
        "stress": 0.2,
        "relationship": 0.6,
        "boredom": 0.3,
        "time_since_interaction": 2.0,
        "observation_text": "User asks about the weather",
    }

    context = {
        "recent_memories": ["User asked about food", "System responded"],
        "insight_quality_ema": 0.5,
        "quality_score": 0.7,
    }

    features = extract_all_features(state, context)
    for dim, value in features.items():
        print(f"{dim.value:15s}: {value:.3f}")
