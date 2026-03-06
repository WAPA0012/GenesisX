"""Personality-Modulated Memory Encoding - Paper Section 3.4.4

人格调制的记忆编码 - GenesisX 个性化记忆机制

特性:
- 人格调节的情绪标记 (Personality-Modulated Emotional Tagging)
- 跨域联想概率调整 (Cross-Domain Association Probability)
- 保守倾向调节的巩固阈值 (CT_t-Modulated Consolidation Threshold)
- 探索倾向调节的新颖性敏感度 (ET_t-Modulated Novelty Sensitivity)
"""

import math
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import numpy as np

from common.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# 人格中间变量定义
# ============================================================================

@dataclass
class PersonalityMiddleVars:
    """人格中间变量 Personality Middle Variables

    论文定义:
    - ET_t: Exploration Tendency (探索倾向)
    - CT_t: Conservation Tendency (保守倾向)
    - ES_t: Emotional Sensitivity (情绪敏感度)
    """

    et: float = 0.5      # 探索倾向 [0, 1]
    ct: float = 0.5      # 保守倾向 [0, 1]
    es: float = 0.5      # 情绪敏感度 [0, 1]

    # 资源压力（影响配置选择）
    rp: float = 0.0      # 资源压力 [0, 1]

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        # 确保 ET_t + CT_t ≈ 1（归一化）
        total = self.et + self.ct
        if total > 0:
            self.et = self.et / total
            self.ct = self.ct / total
        else:
            # 如果两者都为0，设置为默认值
            self.et = 0.5
            self.ct = 0.5

        # 裁剪到有效范围
        self.et = max(0.0, min(1.0, self.et))
        self.ct = max(0.0, min(1.0, self.ct))
        self.es = max(0.0, min(1.0, self.es))
        self.rp = max(0.0, min(1.0, self.rp))


# ============================================================================
# 记忆域类型
# ============================================================================

class MemoryDomain(str, Enum):
    """记忆域类型"""
    EPISODIC = "episodic"       # 情节记忆
    SCHEMA = "schema"           # 图式记忆
    SEMANTIC = "semantic"       # 语义记忆
    PROCEDURAL = "procedural"   # 程序记忆
    EMOTIONAL = "emotional"     # 情绪记忆


# ============================================================================
# 人格调制的情绪标记
# ============================================================================

@dataclass
class EmotionalTag:
    """情绪标签

    论文 3.4.4:
    tag_emotional = f_es(mood, stress) × ES_t
    """
    mood: float = 0.5            # 情绪愉快度 [-1, 1] → [0, 1]
    stress: float = 0.2          # 压力 [0, 1]
    arousal: float = 0.5         # 唤醒度 [0, 1]

    # 人格调节后的强度
    modulated_intensity: float = 0.5

    # 时间戳
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mood": self.mood,
            "stress": self.stress,
            "arousal": self.arousal,
            "modulated_intensity": self.modulated_intensity,
            "timestamp": self.timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmotionalTag":
        return cls(
            mood=data.get("mood", 0.5),
            stress=data.get("stress", 0.2),
            arousal=data.get("arousal", 0.5),
            modulated_intensity=data.get("modulated_intensity", 0.5)
        )


class PersonalityModulatedTagging:
    """人格调制的情绪标记器

    论文 3.4.4:
    tag_intensity = base_intensity × (1 + λ_es × ES_t)

    其中:
    - base_intensity: 基础情绪强度
    - λ_es: 情绪敏感度系数
    - ES_t: 情绪敏感度中间变量
    """

    def __init__(
        self,
        lambda_es: float = 0.8,        # 情绪敏感度系数
        base_threshold: float = 0.3,    # 基础标记阈值
    ):
        self.lambda_es = lambda_es
        self.base_threshold = base_threshold

    def compute_tag_intensity(
        self,
        mood: float,
        stress: float,
        personality: PersonalityMiddleVars
    ) -> EmotionalTag:
        """计算人格调制的情绪标签强度

        公式:
        intensity = |mood| × (1 + stress) × (1 + λ_es × ES_t)

        Args:
            mood: 情绪 [-1, 1]
            stress: 压力 [0, 1]
            personality: 人格中间变量

        Returns:
            情绪标签
        """
        # 基础强度（情绪绝对值）
        base_intensity = abs(mood)

        # 压力放大
        stress_amplification = 1.0 + stress

        # 人格调制（情绪敏感度）
        personality_modulation = 1.0 + (self.lambda_es * personality.es)

        # 综合强度
        modulated_intensity = base_intensity * stress_amplification * personality_modulation
        modulated_intensity = max(0.0, min(1.0, modulated_intensity))

        # 标准化 mood 到 [0, 1]
        mood_normalized = (mood + 1) / 2

        return EmotionalTag(
            mood=mood_normalized,
            stress=stress,
            arousal=0.5 + (modulated_intensity * 0.5),  # 简化映射
            modulated_intensity=modulated_intensity
        )

    def should_tag(self, tag: EmotionalTag) -> bool:
        """判断是否应该标记（强度是否足够）"""
        return tag.modulated_intensity >= self.base_threshold


# ============================================================================
# 跨域联想概率调整
# ============================================================================

@dataclass
class CrossDomainAssociation:
    """跨域联想"""
    source_domain: MemoryDomain
    target_domain: MemoryDomain
    base_probability: float = 0.3       # 基础概率
    modulated_probability: float = 0.3  # 调制后概率
    strength: float = 0.5               # 联想强度


class CrossDomainAssociationCalculator:
    """跨域联想概率计算器

    论文 3.4.4:
    P_cross(source, target) = P_base × (1 + λ_et × ET_t)

    高 ET_t（探索倾向）的人更可能建立跨域联想
    """

    # 默认的域间基础概率矩阵
    DEFAULT_DOMAIN_PROBABILITIES = {
        (MemoryDomain.EPISODIC, MemoryDomain.SCHEMA): 0.6,
        (MemoryDomain.EPISODIC, MemoryDomain.EMOTIONAL): 0.8,
        (MemoryDomain.EPISODIC, MemoryDomain.SEMANTIC): 0.4,
        (MemoryDomain.SCHEMA, MemoryDomain.PROCEDURAL): 0.7,
        (MemoryDomain.EMOTIONAL, MemoryDomain.EPISODIC): 0.9,
        (MemoryDomain.SEMANTIC, MemoryDomain.SCHEMA): 0.5,
    }

    def __init__(
        self,
        lambda_et: float = 0.6,        # 探索倾向系数
        domain_probabilities: Optional[Dict[Tuple[MemoryDomain, MemoryDomain], float]] = None
    ):
        self.lambda_et = lambda_et
        self.domain_probabilities = domain_probabilities or self.DEFAULT_DOMAIN_PROBABILITIES.copy()

    def compute_cross_domain_probability(
        self,
        source: MemoryDomain,
        target: MemoryDomain,
        personality: PersonalityMiddleVars
    ) -> CrossDomainAssociation:
        """计算跨域联想概率

        公式:
        P_modulated = P_base × (1 + λ_et × ET_t)

        Args:
            source: 源记忆域
            target: 目标记忆域
            personality: 人格中间变量

        Returns:
            跨域联想
        """
        # 获取基础概率
        key = (source, target)
        base_prob = self.domain_probabilities.get(key, 0.2)

        # ET_t 调制（探索倾向增强跨域联想）
        modulation = 1.0 + (self.lambda_et * personality.et)
        modulated_prob = min(1.0, base_prob * modulation)

        # 联想强度与概率相关
        strength = modulated_prob

        return CrossDomainAssociation(
            source_domain=source,
            target_domain=target,
            base_probability=base_prob,
            modulated_probability=modulated_prob,
            strength=strength
        )

    def should_associate(self, association: CrossDomainAssociation) -> bool:
        """判断是否应该建立跨域联想"""
        # 使用调制后的概率进行随机决策（实际实现中可以使用确定性规则）
        return association.modulated_probability > 0.4


# ============================================================================
# 保守倾向调节的巩固阈值
# ============================================================================

class PersonalityModulatedConsolidation:
    """人格调制的记忆巩固

    论文 3.4.4:
    θ_consolidation = θ_base × (1 + λ_ct × CT_t)

    高 CT_t（保守倾向）的人需要更高的显著性才能巩固记忆
    """

    def __init__(
        self,
        lambda_ct: float = 0.7,        # 保守倾向系数
        base_threshold: float = 0.5,    # 基础巩固阈值
    ):
        self.lambda_ct = lambda_ct
        self.base_threshold = base_threshold

    def compute_consolidation_threshold(
        self,
        personality: PersonalityMiddleVars
    ) -> float:
        """计算巩固阈值

        公式:
        θ_consolidation = θ_base × (1 + λ_ct × CT_t)

        高 CT_t → 更高的阈值 → 更保守的记忆巩固

        Args:
            personality: 人格中间变量

        Returns:
            巩固阈值 [0, 1]
        """
        # CT_t 调制
        modulation = 1.0 + (self.lambda_ct * personality.ct)

        threshold = self.base_threshold * modulation
        return min(1.0, threshold)

    def should_consolidate(
        self,
        salience: float,
        personality: PersonalityMiddleVars
    ) -> bool:
        """判断是否应该巩固记忆

        Args:
            salience: 显著性分数
            personality: 人格中间变量

        Returns:
            是否巩固
        """
        threshold = self.compute_consolidation_threshold(personality)
        return salience >= threshold

    def compute_consolidation_rate(
        self,
        personality: PersonalityMiddleVars,
        base_rate: float = 0.1
    ) -> float:
        """计算巩固速率

        低 CT_t → 更快的巩固速率
        高 CT_t → 更慢的巩固速率

        公式:
        rate = base_rate × (1 - 0.5 × CT_t)
        """
        rate = base_rate * (1.0 - 0.5 * personality.ct)
        return max(0.01, rate)


# ============================================================================
# 探索倾向调节的新颖性敏感度
# ============================================================================

class NoveltySensitivityCalculator:
    """新颖性敏感度计算器

    论文 3.4.4:
    sensitivity = base_sensitivity × (1 + λ_et × ET_t)

    高 ET_t → 更高的新颖性敏感度 → 更容易注意到新事物
    """

    def __init__(
        self,
        lambda_et: float = 0.8,        # 探索倾向系数
        base_sensitivity: float = 0.5,  # 基础敏感度
    ):
        self.lambda_et = lambda_et
        self.base_sensitivity = base_sensitivity

    def compute_novelty_sensitivity(
        self,
        personality: PersonalityMiddleVars
    ) -> float:
        """计算新颖性敏感度

        公式:
        sensitivity = base_sensitivity × (1 + λ_et × ET_t)

        Args:
            personality: 人格中间变量

        Returns:
            敏感度 [0, 1]
        """
        modulation = 1.0 + (self.lambda_et * personality.et)
        sensitivity = self.base_sensitivity * modulation
        return min(1.0, sensitivity)

    def compute_perceived_novelty(
        self,
        raw_novelty: float,
        personality: PersonalityMiddleVars
    ) -> float:
        """计算感知的新颖性

        高 ET_t 的人会感知到更高的新颖性

        公式:
        perceived = raw_novelty × (1 + λ_et × ET_t)

        Args:
            raw_novelty: 原始新颖性分数
            personality: 人格中间变量

        Returns:
            感知新颖性 [0, 1]
        """
        sensitivity = self.compute_novelty_sensitivity(personality)
        perceived = raw_novelty * (1.0 + sensitivity)
        return min(1.0, perceived)


# ============================================================================
# 人格调制的记忆编码器（整合）
# ============================================================================

@dataclass
class EncodingContext:
    """记忆编码上下文"""
    # 情绪状态
    mood: float = 0.5
    stress: float = 0.2
    arousal: float = 0.5

    # 新颖性
    novelty: float = 0.5

    # 显著性
    salience: float = 0.5

    # 记忆域
    domain: MemoryDomain = MemoryDomain.EPISODIC


@dataclass
class EncodingResult:
    """编码结果"""
    # 情绪标签
    emotional_tag: Optional[EmotionalTag] = None

    # 巩固决策
    should_consolidate: bool = False
    consolidation_threshold: float = 0.5

    # 新颖性感知
    perceived_novelty: float = 0.5
    novelty_sensitivity: float = 0.5

    # 跨域联想
    cross_domain_associations: List[CrossDomainAssociation] = field(default_factory=list)

    # 元数据
    encoding_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class PersonalityModulatedEncoder:
    """人格调制的记忆编码器

    整合论文 3.4.4 的所有人格调制机制:

    1. 情绪标记: tag_intensity × ES_t
    2. 巩固阈值: θ_base × (1 + λ_ct × CT_t)
    3. 新颖性敏感度: sensitivity × (1 + λ_et × ET_t)
    4. 跨域联想: P_cross × (1 + λ_et × ET_t)
    """

    def __init__(
        self,
        # 情绪调制参数
        lambda_es: float = 0.8,
        tag_threshold: float = 0.3,
        # 巩固参数
        lambda_ct: float = 0.7,
        consolidation_threshold: float = 0.5,
        # 新颖性参数
        lambda_et: float = 0.8,
        base_novelty_sensitivity: float = 0.5,
        # 跨域联想参数
        association_lambda_et: float = 0.6,
    ):
        # 子模块
        self.tagging = PersonalityModulatedTagging(
            lambda_es=lambda_es,
            base_threshold=tag_threshold
        )
        self.consolidation = PersonalityModulatedConsolidation(
            lambda_ct=lambda_ct,
            base_threshold=consolidation_threshold
        )
        self.novelty_calc = NoveltySensitivityCalculator(
            lambda_et=lambda_et,
            base_sensitivity=base_novelty_sensitivity
        )
        self.association_calc = CrossDomainAssociationCalculator(
            lambda_et=association_lambda_et
        )

    def encode(
        self,
        context: EncodingContext,
        personality: PersonalityMiddleVars,
        target_domains: Optional[List[MemoryDomain]] = None
    ) -> EncodingResult:
        """执行人格调制的记忆编码

        Args:
            context: 编码上下文
            personality: 人格中间变量
            target_domains: 目标联想域（默认所有域）

        Returns:
            编码结果
        """
        result = EncodingResult()

        # 1. 情绪标记
        result.emotional_tag = self.tagging.compute_tag_intensity(
            context.mood, context.stress, personality
        )

        # 2. 巩固决策
        result.consolidation_threshold = self.consolidation.compute_consolidation_threshold(personality)
        result.should_consolidate = self.consolidation.should_consolidate(
            context.salience, personality
        )

        # 3. 新颖性感知
        result.novelty_sensitivity = self.novelty_calc.compute_novelty_sensitivity(personality)
        result.perceived_novelty = self.novelty_calc.compute_perceived_novelty(
            context.novelty, personality
        )

        # 4. 跨域联想
        target_domains = target_domains or list(MemoryDomain)
        for target in target_domains:
            if target != context.domain:
                association = self.association_calc.compute_cross_domain_probability(
                    context.domain, target, personality
                )
                if self.association_calc.should_associate(association):
                    result.cross_domain_associations.append(association)

        return result

    def update_personality_from_experience(
        self,
        personality: PersonalityMiddleVars,
        novelty: float,
        positive_outcome: bool
    ) -> PersonalityMiddleVars:
        """从经验中更新人格中间变量

        论文暗示人格可以通过经验缓慢调整

        Args:
            personality: 当前人格
            novelty: 经验新颖性
            positive_outcome: 是否为积极结果

        Returns:
            更新后的人格
        """
        # 学习率（很小的值，表示人格变化缓慢）
        learning_rate = 0.01

        if positive_outcome:
            # 积极的新经验增加探索倾向
            personality.et += learning_rate * novelty * personality.et
            # 同时减少保守倾向
            personality.ct = max(0.0, personality.ct - learning_rate * novelty * 0.5)
        else:
            # 消极经验增加保守倾向
            personality.ct += learning_rate * (1 - novelty) * (1 - personality.ct)

        # 重新归一化
        total = personality.et + personality.ct
        if total > 0:
            personality.et = personality.et / total
            personality.ct = personality.ct / total

        return personality


# ============================================================================
# 工厂函数
# ============================================================================

def create_personality_vars(
    et: float = 0.5,
    ct: float = 0.5,
    es: float = 0.5,
    rp: float = 0.0
) -> PersonalityMiddleVars:
    """创建人格中间变量"""
    return PersonalityMiddleVars(et=et, ct=ct, es=es, rp=rp)


def create_encoder(
    lambda_es: float = 0.8,
    lambda_ct: float = 0.7,
    lambda_et: float = 0.8
) -> PersonalityModulatedEncoder:
    """创建人格调制编码器"""
    return PersonalityModulatedEncoder(
        lambda_es=lambda_es,
        lambda_ct=lambda_ct,
        lambda_et=lambda_et
    )


def create_encoding_context(
    mood: float,
    stress: float,
    novelty: float,
    salience: float,
    domain: MemoryDomain = MemoryDomain.EPISODIC
) -> EncodingContext:
    """创建编码上下文"""
    return EncodingContext(
        mood=mood,
        stress=stress,
        novelty=novelty,
        salience=salience,
        domain=domain
    )
