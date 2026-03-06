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
    verify_utility_normalization as _verify_utility_normalization_base,
    verify_utility_normalization_with_calculator,
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
# 向后兼容层 (Backward Compatibility Layer)
# ============================================================================
# 注意: utility.py 已被移除，以下类在此提供向后兼容支持
# TODO: 在下一个主版本中移除此兼容层，直接使用 utilities_unified.py
# ============================================================================

try:
    from .utility import UtilityCalculator, StateSnapshot, UtilityConfig
except ImportError:
    # utility.py 已移除，提供完整的兼容类
    from dataclasses import dataclass, field
    from typing import Dict, Any, Optional
    from common.models import CostVector

    @dataclass
    class UtilityConfig:
        """Configuration for utility computation."""
        clip_range: float = 1.0
        normalization: str = "tanh"
        # 论文Section 3.5.2(3): T_half 默认24小时（以秒为单位）
        t_half_neglect: float = 24.0 * 3600.0  # 24 hours in seconds
        # 依恋效用系数（论文Section 3.5.2）
        alpha: float = 1.0  # Bond 增长系数
        beta: float = 1.0   # Trust 增长系数
        gamma: float = 1.0   # 忽视惩罚系数
        # Additional config attributes for tests
        alpha_bond: float = 1.0
        beta_trust: float = 1.0
        gamma_neglect: float = 1.0
        eta_success: float = 0.7
        eta_quality: float = 0.3
        kappa_skill: float = 0.4
        max_drift_penalty: float = 0.8
        max_error_penalty: float = 0.3
        cost_normalization_factor: float = 8000.0

        @classmethod
        def from_global_config(cls, global_config: Dict[str, Any]) -> 'UtilityConfig':
            """Create UtilityConfig from global config dict."""
            config = cls()

            # Parse axiology section
            axiology = global_config.get("axiology", {})

            # Attachment config
            attachment = axiology.get("attachment", {})
            if attachment:
                config.alpha_bond = attachment.get("alpha", config.alpha_bond)
                config.beta_trust = attachment.get("beta", config.beta_trust)
                config.gamma_neglect = attachment.get("gamma", config.gamma_neglect)
                t_half_hours = attachment.get("t_half_hours", 24.0)
                config.t_half_neglect = t_half_hours * 3600.0

            # Competence config
            competence = axiology.get("competence", {})
            if competence:
                config.eta_success = competence.get("eta_success", config.eta_success)
                config.eta_quality = competence.get("eta_quality", config.eta_quality)
                config.kappa_skill = competence.get("kappa_skill", config.kappa_skill)

            # Integrity config
            integrity = axiology.get("integrity", {})
            if integrity:
                config.max_drift_penalty = integrity.get("max_drift_penalty", config.max_drift_penalty)
                config.max_error_penalty = integrity.get("max_error_penalty", config.max_error_penalty)

            # Tool costs
            tool_costs = global_config.get("tool_costs", {})
            if tool_costs:
                config.cost_normalization_factor = float(tool_costs.get("tokens_cap", config.cost_normalization_factor))

            return config

    @dataclass
    class StateSnapshot:
        """Snapshot of system state for utility computation."""
        # Basic homeostasis
        energy: float = 0.8
        mood: float = 0.5
        stress: float = 0.2
        fatigue: float = 0.1
        # Attachment
        bond: float = 0.0
        trust: float = 0.5
        boredom: float = 0.0
        dt_since_user: float = 0.0
        # Integrity
        personality_drift: float = 0.0
        error_count: int = 0
        # Contract
        has_active_command: bool = False
        command_progress: float = 0.0
        # Competence
        success_rate: float = 0.5
        quality_score: float = 0.5
        skill_coverage: float = 0.5
        # Curiosity
        novelty: float = 0.5
        # Meaning
        insight_formed: bool = False
        insight_quality: float = 0.0

        @classmethod
        def from_dict(cls, data: Dict[str, Any]) -> 'StateSnapshot':
            """Create StateSnapshot from dict, using defaults for missing fields."""
            import dataclasses as _dc
            fields = cls.__dataclass_fields__
            kwargs = {}
            for field_name, field_info in fields.items():
                if field_name in data:
                    kwargs[field_name] = data[field_name]
                elif field_info.default is not _dc.MISSING:
                    kwargs[field_name] = field_info.default
                elif field_info.default_factory is not _dc.MISSING:
                    kwargs[field_name] = field_info.default_factory()
                # else: field has no default, skip (will use constructor default if any)
            return cls(**kwargs)

    class UtilityCalculator:
        """Utility calculator with normalization support."""

        def __init__(self, config: UtilityConfig = None):
            self.config = config or UtilityConfig()

        def normalize(self, value: float, min_val: float = -1.0, max_val: float = 1.0) -> float:
            """Normalize value to [-1, 1] range."""
            return max(min_val, min(max_val, value))

        def compute_homeostasis(self, state_t: StateSnapshot, state_t1: StateSnapshot) -> float:
            """Compute homeostasis utility between two states."""
            # Use improvement in energy-stress-fatigue balance
            energy_delta = (state_t1.energy - state_t.energy)
            stress_delta = (state_t.stress - state_t1.stress)  # stress decrease is good
            fatigue_delta = (state_t.fatigue - state_t1.fatigue)  # fatigue decrease is good

            utility = (energy_delta + stress_delta + fatigue_delta) / 3.0
            return self.normalize(utility, -1.0, 1.0)

        def compute_integrity(self, state_t: StateSnapshot, state_t1: StateSnapshot) -> float:
            """Compute integrity utility (penalty for drift and errors)."""
            drift_penalty = -state_t1.personality_drift * self.config.max_drift_penalty
            error_penalty = -state_t1.error_count * self.config.max_error_penalty / 10.0

            utility = drift_penalty + error_penalty
            return self.normalize(utility, -1.0, 0.0)

        def compute_attachment(self, state_t: StateSnapshot, state_t1: StateSnapshot) -> float:
            """Compute attachment utility (bond and trust changes minus neglect)."""
            bond_delta = state_t1.bond - state_t.bond
            trust_delta = state_t1.trust - state_t.trust

            # Neglect penalty
            t_half = self.config.t_half_neglect / 3600.0  # Convert to hours
            neglect = 1.0 - (2.0 ** (-state_t1.dt_since_user / t_half))
            neglect_penalty = -self.config.gamma_neglect * neglect

            utility = (self.config.alpha_bond * bond_delta +
                      self.config.beta_trust * trust_delta +
                      neglect_penalty)
            return self.normalize(utility, -1.0, 1.0)

        def compute_contract(self, state_t: StateSnapshot, state_t1: StateSnapshot) -> float:
            """Compute contract utility (progress change)."""
            progress_delta = state_t1.command_progress - state_t.command_progress
            return self.normalize(progress_delta, -0.5, 0.5)

        def compute_competence(self, state_t: StateSnapshot, state_t1: StateSnapshot) -> float:
            """Compute competence utility."""
            utility = (self.config.eta_success * state_t1.success_rate +
                      self.config.eta_quality * state_t1.quality_score +
                      self.config.kappa_skill * state_t1.skill_coverage)
            return self.normalize(utility, 0.0, 1.0)

        def compute_curiosity(self, state_t: StateSnapshot, state_t1: StateSnapshot) -> float:
            """Compute curiosity utility (novelty change)."""
            novelty_delta = state_t1.novelty - state_t.novelty
            return self.normalize(novelty_delta, -0.5, 0.5)

        def compute_meaning(self, state_t: StateSnapshot, state_t1: StateSnapshot) -> float:
            """Compute meaning utility (insight quality if insight formed)."""
            if not state_t1.insight_formed:
                return 0.0
            return self.normalize(state_t1.insight_quality, 0.0, 1.0)

        def compute_efficiency(self, cost: Optional[CostVector] = None) -> float:
            """Compute efficiency utility (negative cost)."""
            if cost is None:
                return 0.0

            # Normalize cost to [0, 1] and negate
            total_cost = cost.total_cost() if hasattr(cost, 'total_cost') else (
                cost.cpu_tokens + cost.io_ops / 5 + cost.net_bytes / 1000 + cost.latency_ms / 10
            )
            normalized_cost = min(1.0, total_cost / self.config.cost_normalization_factor)
            return -normalized_cost

        def compute_all_utilities(self, state_t: StateSnapshot, state_t1: StateSnapshot,
                                 cost: Optional[CostVector] = None) -> Dict[str, float]:
            """Compute all utilities for testing (5维核心价值系统)."""
            return {
                "homeostasis": self.compute_homeostasis(state_t, state_t1),
                "attachment": self.compute_attachment(state_t, state_t1),
                "curiosity": self.compute_curiosity(state_t, state_t1),
                "competence": self.compute_competence(state_t, state_t1),
                "safety": self.compute_safety(state_t, state_t1),
            }

        def compute_safety(self, state_t: StateSnapshot, state_t1: StateSnapshot) -> float:
            """Compute safety utility (新增5维核心价值)."""
            # Safety utility = improvement in risk profile
            # Simplified: use personality_drift as proxy for risk
            risk_t = state_t.personality_drift
            risk_t1 = state_t1.personality_drift
            utility = risk_t - risk_t1  # risk reduction is positive
            return self.normalize(utility, -1.0, 1.0)

# Wrapper for verify_utility_normalization - must be defined after classes
def verify_utility_normalization(*args, **kwargs):
    """Flexible verification function for utility normalization.

    Supports two signatures for backward compatibility:
    1. verify_utility_normalization(utilities, u_min=-1.0, u_max=1.0) -> (bool, dict)
    2. verify_utility_normalization(calculator, num_samples=100) -> dict
    """
    # Detect which signature is being used
    if len(args) > 0 and hasattr(args[0], 'compute_homeostasis'):
        # Signature 2: calculator-based
        calculator = args[0]
        num_samples = kwargs.get('num_samples', 100)
        return verify_utility_normalization_with_calculator(calculator, num_samples)
    else:
        # Signature 1: utilities dict
        return _verify_utility_normalization_base(*args, **kwargs)


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
    # Backward compatibility
    "UtilityCalculator",
    "StateSnapshot",
    "UtilityConfig",
]
