"""Axiology System - 5-dimensional value field.

Based on Section 3.5 of the paper (v14).

修复 v14: 使用5维核心价值向量 (论文 Section 3.5.1)
- HOMEOSTASIS: 稳态 - 资源平衡、压力管理、系统稳定
- ATTACHMENT: 依恋 - 社交连接、信任建立、忽视回避
- CURIOSITY: 好奇 - 新奇探索、信息增益、规律发现
- COMPETENCE: 胜任 - 任务成功、技能成长、效能感
- SAFETY: 安全 - 风险回避、损失预防、安全边际

Enhanced with paper Section 3.5.2: 效用函数尺度归一化
All utility functions normalized to [-1, 1] range.

COMPENSATION (方案 B):
删除的维度通过补偿机制实现:
- INTEGRITY -> IntegrityConstraintChecker (硬约束检查)
- CONTRACT -> ContractSignalBooster (权重提升)
- EFFICIENCY -> EfficiencyMonitor (并入 homeostasis)
- MEANING -> MeaningTracker (并入 curiosity)

REFACTOR NOTE: This module now uses utilities_unified.py as the single source
of truth for utility computation, eliminating duplication between utility.py,
utility_normalized.py, and utilities.py.

ENHANCED: Load default parameters from configuration files (value_setpoints.yaml)
instead of hardcoding. Use axiology_config.AxiologyConfig to access configuration.
"""
from .feature_extractors import extract_all_features
from .gaps import compute_gaps
from .weights import compute_weights, WeightUpdater
from .axiology_config import (
    AxiologyConfig,
    get_axiology_config,
    reset_global_config,
    DEFAULT_SETPOINTS,
    DEFAULT_WEIGHT_BIAS,
    DEFAULT_IDLE_BIAS,
    DEFAULT_IDLE_EPSILON,
    DEFAULT_TAU,
)
from .utilities_unified import (
    compute_utility,
    compute_all_utilities,
    compute_utilities,  # Legacy, kept for backward compatibility
    normalize_utility,
    verify_utility_normalization,
    # Utility functions for each dimension (5维核心 + 4维废弃)
    utility_homeostasis,
    utility_attachment,
    utility_curiosity,
    utility_competence,
    utility_safety,
    # Legacy utility functions (已废弃，保留向后兼容)
    utility_integrity,
    utility_contract,
    utility_meaning,
    utility_efficiency,
    clip_utility,
    tanh_normalize,
)
from .reward import compute_reward
from .value_learning import (
    ValueLearner,
    ValueParameters,
    ValueLearnerConfig,
    FeedbackSignal,
    FeedbackType,
)
# 驱动力系统（新架构）
from .drives import (
    BaseDrive,
    DriveSignal,
    CuriosityDrive,
    CompetenceDrive,
    HomeostasisDrive,
    AttachmentDrive,
    SafetyDrive,
)
# 补偿机制（方案 B）
from .compensation import (
    CompensationManager,
    IntegrityConstraintChecker,
    IntegrityCheckResult,
    ConstraintViolation,
    ContractSignalBooster,
    ContractSignal,
    EfficiencyMonitor,
    EfficiencyMetrics,
    MeaningTracker,
    InsightEvent,
)

# ============================================================================
# 向后兼容层已移除 (Backward Compatibility Layer REMOVED)
# ============================================================================
# 历史上这里有一段 fallback：当 utility.py 不存在时动态定义
# UtilityCalculator / StateSnapshot / UtilityConfig 三个类（~210 行）。
#
# utility.py 早已被 utilities_unified.py 取代并删除，fallback 每次必走 except 分支，
# 且 fallback 里的 compute_* 公式与论文 v15 的 utilities_unified 完全不一致
# （homeostasis 用旧 energy/stress/fatigue 三件套、attachment 拆 bond/trust、
#  curiosity 丢 insight、competence 无失败惩罚、safety 用 personality_drift 当代理）。
#
# 外部仅 3 个测试/smoke 文件依赖它们（且验证的是过时公式，断言 clip 范围恒成立）。
# 已于 2026-07-21 删除：fallback 块、verify_utility_normalization wrapper、
# verify_utility_normalization_with_calculator 自指依赖函数。详见 CODE_MAP P2-1。
# ============================================================================


__all__ = [
    # Feature extraction
    "extract_all_features",
    # Gap computation
    "compute_gaps",
    # Weight computation
    "compute_weights",
    "WeightUpdater",
    # Configuration (ENHANCED: Load from YAML files)
    "AxiologyConfig",
    "get_axiology_config",
    "reset_global_config",
    "DEFAULT_SETPOINTS",
    "DEFAULT_WEIGHT_BIAS",
    "DEFAULT_IDLE_BIAS",
    "DEFAULT_IDLE_EPSILON",
    "DEFAULT_TAU",
    # Unified utility functions
    "compute_utility",
    "compute_all_utilities",
    "compute_utilities",  # Legacy
    "normalize_utility",
    "verify_utility_normalization",
    # Dimension-specific utilities (5维核心)
    "utility_homeostasis",
    "utility_attachment",
    "utility_curiosity",
    "utility_competence",
    "utility_safety",
    # Legacy utility functions (已废弃)
    "utility_integrity",
    "utility_contract",
    "utility_meaning",
    "utility_efficiency",
    "clip_utility",
    "tanh_normalize",
    # Reward
    "compute_reward",
    # Value learning
    "ValueLearner",
    "ValueParameters",
    "ValueLearnerConfig",
    "FeedbackSignal",
    "FeedbackType",
    # Drives (驱动力系统 - 新架构)
    "BaseDrive",
    "DriveSignal",
    "CuriosityDrive",
    "CompetenceDrive",
    "HomeostasisDrive",
    "AttachmentDrive",
    "SafetyDrive",
    # Compensation (方案 B: 删除维度的补偿机制)
    "CompensationManager",
    "IntegrityConstraintChecker",
    "IntegrityCheckResult",
    "ConstraintViolation",
    "ContractSignalBooster",
    "ContractSignal",
    "EfficiencyMonitor",
    "EfficiencyMetrics",
    "MeaningTracker",
    "InsightEvent",
]
