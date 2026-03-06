"""Core runtime modules for Genesis X."""

from .tick import TickContext
from .invariants import check_invariants
from .stores.fields import FieldStore, BoundedScalar, Valence, Prob
from .stores.slots import SlotStore
from .stores.ledger import MetabolicLedger
from .resource_config import ResourceConfig, get_resource_config

# Define __all__ first before any extend operations
__all__ = [
    "TickContext",
    "check_invariants",
    "FieldStore",
    "BoundedScalar",
    "Valence",
    "Prob",
    "SlotStore",
    "MetabolicLedger",
    # Resource configuration (支持无限Token模式)
    "ResourceConfig",
    "get_resource_config",
]

# Autonomous scheduler - 需求驱动的事件触发
try:
    from .autonomous_scheduler import (
        AutonomousScheduler,
        NeedType,
        Need,
        AutonomousDecision,
        AdaptiveSleep,
    )
    __all__.extend([
        "AutonomousScheduler",
        "NeedType",
        "Need",
        "AutonomousDecision",
        "AdaptiveSleep",
    ])
except ImportError:
    pass

# Limb Generator - 自主肢体生成 (已移动到 growth 模块)
try:
    from .growth import (
        LimbGenerator,
        LimbRequirement,
        GeneratedLimb,
        GenerationType,
        LimbTemplate,
        GrowthManager,
        GrowthEvent,
        create_growth_manager,
    )
    __all__.extend([
        "LimbGenerator",
        "LimbRequirement",
        "GeneratedLimb",
        "GenerationType",
        "LimbTemplate",
        "GrowthManager",
        "GrowthEvent",
        "create_growth_manager",
    ])
except ImportError:
    pass

# Note: LifeLoop is in core.life_loop, GlobalState is in core.state
# Use: from core.life_loop import LifeLoop
# Use: from core.state import GlobalState

# Capability Gap Detector - 能力缺口检测
try:
    from .capability_gap_detector import (
        CapabilityGapDetector,
        CapabilityGap,
        GapType,
        ExplorationDiscovery,
        create_capability_gap_detector,
    )
    __all__.extend([
        "CapabilityGapDetector",
        "CapabilityGap",
        "GapType",
        "ExplorationDiscovery",
        "create_capability_gap_detector",
    ])
except ImportError:
    pass

# Limb Builder - 容器构建和部署 (已移动到 growth 模块)
try:
    from .growth import (
        LimbBuilder,
        BuildConfig,
        BuildResult,
        LimbDeployment,
        create_limb_builder,
        build_and_deploy,
    )
    __all__.extend([
        "LimbBuilder",
        "BuildConfig",
        "BuildResult",
        "LimbDeployment",
        "create_limb_builder",
        "build_and_deploy",
    ])
except ImportError:
    pass

# Evolution System - 进化系统 (自我复制迭代)
try:
    from .evolution import (
        EvolutionEngine,
        EvolutionPhase,
        EvolutionProposal,
        EvolutionMetrics,
        CloneInstance,
        MutationType,
        EVOLUTION_ENABLED,
        get_evolution_engine,
    )
    __all__.extend([
        "EvolutionEngine",
        "EvolutionPhase",
        "EvolutionProposal",
        "EvolutionMetrics",
        "CloneInstance",
        "MutationType",
        "EVOLUTION_ENABLED",
        "get_evolution_engine",
    ])
except ImportError:
    pass

# Abstract state layer (论文 3.4.2)
try:
    from .abstract_state import (
        EmotionState,
        AbstractEmotionalState,
        AbstractGoal,
        AbstractMemoryPointer,
        AbstractContextSummary,
        AbstractState,
        SwitchEvent,
        StateTransitionManager,
        BlackboardWithAbstractState,
        # Factory functions
        get_blackboard_with_abstract_state,
        create_abstract_state,
        create_transition_manager,
    )
    __all__.extend([
        "EmotionState",
        "AbstractEmotionalState",
        "AbstractGoal",
        "AbstractMemoryPointer",
        "AbstractContextSummary",
        "AbstractState",
        "SwitchEvent",
        "StateTransitionManager",
        "BlackboardWithAbstractState",
        "get_blackboard_with_abstract_state",
        "create_abstract_state",
        "create_transition_manager",
    ])
except ImportError:
    pass

# Fine-grained emotion decay (论文 3.7.3)
try:
    from .emotion_decay import (
        EmotionDimension,
        DecayConfig,
        EmotionalState,
        EmotionDecayFunction,
        EmotionTransitionTrigger,
        MemoryEmotionalContext,
        ProustEffectTrigger,
        DecayResult,
        FineGrainedEmotionDecay,
        # Factory functions
        create_decay_config,
        create_emotion_decay,
        create_emotional_state,
        create_memory_context,
    )
    __all__.extend([
        "EmotionDimension",
        "DecayConfig",
        "EmotionalState",
        "EmotionDecayFunction",
        "EmotionTransitionTrigger",
        "MemoryEmotionalContext",
        "ProustEffectTrigger",
        "DecayResult",
        "FineGrainedEmotionDecay",
        "create_decay_config",
        "create_emotion_decay",
        "create_emotional_state",
        "create_memory_context",
    ])
except ImportError:
    pass
