"""Constants for Genesis X system.

This module contains all magic numbers and hardcoded values that should be
configurable rather than hardcoded throughout the codebase.
"""

from typing import Dict, Any, Final
from dataclasses import dataclass


# =============================================================================
# Memory System Constants
# =============================================================================

@dataclass
class MemoryConstants:
    """Constants for memory system."""

    # Episode memory
    EPISODIC_MAX_CACHE_SIZE: Final[int] = 50000
    EPISODIC_DECAY_TICKS: Final[int] = 1000  # Age decay over this many ticks
    EPISODIC_QUERY_LIMIT: Final[int] = 20

    # Schema memory
    SCHEMA_MAX_COUNT: Final[int] = 1000
    SCHEMA_CONFIDENCE_THRESHOLD: Final[float] = 0.5
    SCHEMA_HIGH_CONFIDENCE_THRESHOLD: Final[float] = 0.8

    # Skill memory
    SKILL_MAX_COUNT: Final[int] = 300
    SKILL_MIN_INVOCATIONS: Final[int] = 3
    SKILL_MIN_SUCCESS_RATE: Final[float] = 0.7
    SKILL_MAX_FAILURE_RATE: Final[float] = 0.8

    # Salience computation
    SALIENCE_KAPPA: Final[float] = 3.0
    SALIENCE_A_DELTA: Final[float] = 1.0
    SALIENCE_A_UNMET: Final[float] = 0.5
    SALIENCE_A_NOVELTY: Final[float] = 0.3

    # Consolidation
    CONSOLIDATION_SAMPLE_LIMIT: Final[int] = 20
    CONSOLIDATION_MIN_EPISODES: Final[int] = 2
    CONSOLIDATION_MIN_SKILL_INVOCATIONS: Final[int] = 3

    # Pruning
    PRUNE_DELTA_THRESHOLD: Final[float] = 0.30
    PRUNE_RECENT_KEEP: Final[float] = 0.15
    PRUNE_SIMILARITY_THRESHOLD: Final[float] = 0.92


# =============================================================================
# Value System Constants
# =============================================================================

@dataclass
class ValueSystemConstants:
    """Constants for value system.

    论文 Section 3.5, 3.6, Appendix A.4, A.5
    """

    # ============================================================================
    # 维度设定点 f^{(i)*} (论文 Appendix A.4)
    # ============================================================================

    # Homeostasis: H* = (Compute*, Memory*, 1-Stress*) = (0.70, 0.70, 0.80)
    HOMEOSTASIS_SETPOINT_COMPUTE: Final[float] = 0.70
    HOMEOSTASIS_SETPOINT_MEMORY: Final[float] = 0.70
    HOMEOSTASIS_SETPOINT_STRESS: Final[float] = 0.20  # 1 - 0.80 = 0.20
    HOMEOSTASIS_SETPOINT_FEATURE: Final[float] = 0.85  # f^{homeo*} 默认

    # Attachment
    ATTACHMENT_SETPOINT_RELATIONSHIP: Final[float] = 0.70
    ATTACHMENT_SETPOINT_FEATURE: Final[float] = 0.70

    # Curiosity
    CURIOSITY_SETPOINT_FEATURE: Final[float] = 0.60

    # Competence
    COMPETENCE_SETPOINT_FEATURE: Final[float] = 0.75

    # Safety
    SAFETY_SETPOINT_FEATURE: Final[float] = 0.80

    # ============================================================================
    # 权重计算 (论文 Section 3.6)
    # ============================================================================

    # Weight computation
    WEIGHT_TEMPERATURE: Final[float] = 2.0  # τ (tau): 动机集中度 (论文默认2.0)
    WEIGHT_INERTIA: Final[float] = 0.3

    # Priority override (论文 Section 3.6.4)
    OVERRIDE_HIGH_THRESHOLD: Final[float] = 0.6  # θ_hi (论文默认0.6)
    OVERRIDE_LOW_THRESHOLD: Final[float] = 0.3   # θ_lo (论文默认0.3)
    OVERRIDE_SOFT_FACTOR: Final[float] = 0.3

    # Minimum weights for critical dimensions
    HOMEOSTASIS_MIN_WEIGHT: Final[float] = 0.5  # homeo override α (论文0.5)
    SAFETY_MIN_WEIGHT: Final[float] = 0.6        # safety override α (论文0.6)

    # Weight normalization tolerance
    WEIGHT_SUM_TOLERANCE: Final[float] = 1e-10

    # Gap computation
    GAP_MAX_DISTANCE: Final[float] = 3.0  # For homeostasis L1 distance

    # ============================================================================
    # 效用函数系数 (论文 Section 3.5.2)
    # ============================================================================

    # Competence utility: η1*Success + η2*Q + κ*ΔCover
    UTILITY_ETA_1: Final[float] = 0.4  # Success weight η1 (论文0.4)
    UTILITY_ETA_2: Final[float] = 0.4  # Quality weight η2 (论文0.4，修正)
    UTILITY_KAPPA: Final[float] = 0.2  # Skill coverage weight κ (论文0.2，修正)
    UTILITY_ETA_3: Final[float] = 0.3  # Failure penalty η3 (论文v4)

    # Curiosity coefficients
    CURIOSITY_NOVELTY_WEIGHT: Final[float] = 0.7    # Novelty 权重 (论文0.7)
    CURIOSITY_INSIGHT_WEIGHT: Final[float] = 0.3    # 洞察权重 (论文0.3)
    CURIOSITY_INSIGHT_EMA_ALPHA: Final[float] = 0.1  # EMA 系数 α

    # Attachment coefficients
    ATTACHMENT_ALPHA: Final[float] = 0.5  # Bond 变化权重 (论文简化)
    ATTACHMENT_BETA: Final[float] = 0.5   # Trust 变化权重 (论文简化)
    ATTACHMENT_MU_ATT: Final[float] = 0.15  # 忽视惩罚系数 μ_att (论文 Appendix A.5)
    ATTACHMENT_HALF_LIFE_HOURS: Final[float] = 24.0  # T_half (忽视半衰期)

    # Competence feature extraction
    COMPETENCE_MAX_SKILLS: Final[int] = 20  # For normalization
    COMPETENCE_EMA_ALPHA: Final[float] = 0.1  # EMA 系数 α_Q


# =============================================================================
# Affect System Constants
# =============================================================================

@dataclass
class AffectConstants:
    """Constants for affect (mood/stress) system."""

    # Mood update
    MOOD_K_PLUS: Final[float] = 0.25  # Positive RPE gain
    MOOD_K_MINUS: Final[float] = 0.30  # Negative RPE loss

    # Stress update
    STRESS_GAIN: Final[float] = 0.20   # Stress increase for negative RPE
    STRESS_RELIEF: Final[float] = 0.10  # Stress relief for positive RPE

    # RPE clipping
    RPE_CLIP_MIN: Final[float] = -2.0
    RPE_CLIP_MAX: Final[float] = 2.0

    # Mood/Stress range
    MOOD_MIN: Final[float] = 0.0
    MOOD_MAX: Final[float] = 1.0
    STRESS_MIN: Final[float] = 0.0
    STRESS_MAX: Final[float] = 1.0


# =============================================================================
# Metabolism Constants
# =============================================================================

@dataclass
class MetabolismConstants:
    """Constants for metabolic system."""

    # Energy update rates
    ENERGY_BASE_DECAY: Final[float] = 0.01
    ENERGY_ACTION_COST: Final[float] = 0.05
    ENERGY_SLEEP_GAIN: Final[float] = 0.15

    # Fatigue update rates
    FATIGUE_BASE_ACCUMULATION: Final[float] = 0.01
    FATIGUE_ACTION_COST: Final[float] = 0.03
    FATIGUE_SLEEP_REDUCTION: Final[float] = 0.20

    # Stress decay rates (by stress level)
    STRESS_DECAY_LOW: Final[float] = 0.02   # stress < 0.3
    STRESS_DECAY_MEDIUM: Final[float] = 0.05  # stress 0.3-0.7
    STRESS_DECAY_HIGH: Final[float] = 0.10   # stress > 0.7

    # Boredom update rates
    BOREDOM_ACCUMULATION: Final[float] = 0.005
    BOREDOM_REDUCTION_NOVELTY: Final[float] = 0.10
    BOREDOM_REDUCTION_SOCIAL: Final[float] = 0.05


# =============================================================================
# Tool Cost Constants
# =============================================================================

@dataclass
class ToolCostConstants:
    """Constants for tool cost normalization."""

    # Time cap in seconds
    TIME_CAP_SECONDS: Final[float] = 10.0

    # Network cap in bytes
    NET_CAP_BYTES: Final[int] = 2 * 1024 * 1024  # 2MB

    # File I/O operations cap
    IO_CAP_OPS: Final[int] = 20

    # LLM tokens cap
    TOKENS_CAP: Final[int] = 4000

    # Risk scores
    RISK_SAFE: Final[float] = 0.0
    RISK_LOW: Final[float] = 0.2
    RISK_MEDIUM: Final[float] = 0.5
    RISK_HIGH: Final[float] = 1.0


# =============================================================================
# Learning and Development Constants
# =============================================================================

@dataclass
class LearningConstants:
    """Constants for learning and development."""

    # Value learning
    VALUE_LEARNING_INTERVAL: Final[int] = 50  # Check every N ticks
    VALUE_LEARNING_ALPHA: Final[float] = 0.1  # EMA for value predictions
    VALUE_EPSILON: Final[float] = 0.001  # Learning rate

    # Schema/Skill quality thresholds
    INSIGHT_QUALITY_MIN: Final[float] = 0.65
    SKILL_SUCCESS_RATE_MIN: Final[float] = 0.5

    # Developmental stages
    STAGE_EMBRYO_MAX_TICKS: Final[int] = 100
    STAGE_JUVENILE_MAX_TICKS: Final[int] = 500
    STAGE_ADULT_MAX_TICKS: Final[int] = 5000

    # Neglect half-life
    NEGLECT_HALFLIFE_HOURS: Final[float] = 24.0
    NEGLECT_DECAY_FACTOR: Final[float] = 1.0


# =============================================================================
# Consolidation and Sleep Triggers
# =============================================================================

@dataclass
class ConsolidationConstants:
    """Constants for memory consolidation."""

    # Fatigue/Boredom sleep triggers
    FATIGUE_SLEEP_THRESHOLD: Final[float] = 0.75
    BOREDOM_SLEEP_THRESHOLD: Final[float] = 0.80
    MEANING_GAP_REFLECT_THRESHOLD: Final[float] = 0.40
    EFFICIENCY_GAP_REFLECT_THRESHOLD: Final[float] = 0.60

    # Energy threshold for low energy warning
    ENERGY_LOW_THRESHOLD: Final[float] = 0.3

    # Minimum episodes for consolidation
    MIN_EPISODES_FOR_CONSOLIDATION: Final[int] = 10


# =============================================================================
# Scheduler Constants
# =============================================================================

@dataclass
class SchedulerConstants:
    """Constants for online/offline thread scheduling."""

    # Offline interval
    OFFLINE_INTERVAL_DEFAULT: Final[int] = 100

    # Offline budget
    OFFLINE_MAX_TOKENS: Final[int] = 10000
    OFFLINE_MAX_TIME_SECONDS: Final[int] = 300

    # Offline risk threshold
    OFFLINE_MAX_RISK: Final[float] = 0.3

    # Forbidden tools in offline mode
    OFFLINE_FORBIDDEN_TOOLS = {"web_search", "code_exec", "file_write", "api_call"}


# =============================================================================
# Safe Mode Constants
# =============================================================================

@dataclass
class SafeModeConstants:
    """Constants for safe mode degradation."""

    # Max consecutive errors before entering safe mode
    MAX_CONSECUTIVE_ERRORS: Final[int] = 3

    # Stress threshold for safe mode
    STRESS_SAFE_MODE_THRESHOLD: Final[float] = 0.9

    # Mood threshold for restricting exploration
    MOOD_EXPLORATION_THRESHOLD: Final[float] = 0.1


# =============================================================================
# Cognition Constants
# =============================================================================

@dataclass
class CognitionConstants:
    """Constants for cognition system."""

    # LLM timeout and retry
    LLM_TIMEOUT: Final[float] = 30.0
    MAX_LLM_RETRIES: Final[int] = 3

    # Planning defaults
    PLANNING_DEPTH_DEFAULT: Final[int] = 3
    NUM_PLANS_DEFAULT: Final[int] = 3


# =============================================================================
# Tool Constants
# =============================================================================

@dataclass
class ToolConstants:
    """Constants for tool system."""

    # Embedding cache
    MAX_EMBEDDING_CACHE_SIZE: Final[int] = 1000

    # Tool timeout
    TOOL_TIMEOUT_DEFAULT: Final[float] = 10.0


# =============================================================================
# Global Constants Instance
# =============================================================================

# Default constants
MEMORY: Final[MemoryConstants] = MemoryConstants()
VALUE_SYSTEM: Final[ValueSystemConstants] = ValueSystemConstants()
AFFECT: Final[AffectConstants] = AffectConstants()
METABOLISM: Final[MetabolismConstants] = MetabolismConstants()
TOOL_COST: Final[ToolCostConstants] = ToolCostConstants()
LEARNING: Final[LearningConstants] = LearningConstants()
CONSOLIDATION: Final[ConsolidationConstants] = ConsolidationConstants()
SCHEDULER: Final[SchedulerConstants] = SchedulerConstants()
SAFE_MODE: Final[SafeModeConstants] = SafeModeConstants()
COGNITION: Final[CognitionConstants] = CognitionConstants()
TOOL: Final[ToolConstants] = ToolConstants()


def get_all_constants() -> Dict[str, Any]:
    """Get all constants as a dictionary.

    Returns:
        Dictionary mapping constant names to values
    """
    return {
        "memory": MEMORY,
        "value_system": VALUE_SYSTEM,
        "affect": AFFECT,
        "metabolism": METABOLISM,
        "tool_cost": TOOL_COST,
        "learning": LEARNING,
        "consolidation": CONSOLIDATION,
        "scheduler": SCHEDULER,
        "safe_mode": SAFE_MODE,
        "cognition": COGNITION,
        "tool": TOOL,
    }


# Example usage and validation
if __name__ == "__main__":
    import json

    constants = get_all_constants()

    # Convert to dict for JSON serialization
    constants_dict = {
        name: {
            k: v for k, v in vars(cls).items()
            if not k.startswith("_")
        }
        for name, cls in constants.items()
    }

    print("Genesis X System Constants")
    print("=" * 60)
    print(json.dumps(constants_dict, indent=2))
    print("\n✓ All constants centralized and documented")
