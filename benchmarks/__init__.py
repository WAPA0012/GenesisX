"""GXBS (Genesis X Benchmark Suite) - Comprehensive Benchmark System

Genesis X 基准测试系统 - 论文附录 B

特性:
- 记忆检索准确率基准 (Memory Retrieval Accuracy)
- 联想激活速度基准 (Associative Activation Speed)
- 情绪衰减 fidelity 基准 (Emotion Decay Fidelity)
- 多模型切换连续性基准 (Model Switching Continuity)
- 人格调制效果基准 (Personality Modulation Effectiveness)
"""

from .gxbs_runner import (
    GXBSRunner,
    GXBSResult,
    GXBSSuite,
    GXBSBenchmark,
    create_gxbs_runner,
)

from .memory_benchmark import (
    MemoryRetrievalBenchmark,
    AssociativeActivationBenchmark,
    create_memory_benchmark,
)

from .emotion_benchmark import (
    EmotionDecayBenchmark,
    ProustEffectBenchmark,
    create_emotion_benchmark,
)

from .personality_benchmark import (
    PersonalityModulationBenchmark,
    create_personality_benchmark,
)

from .multi_model_benchmark import (
    ModelSwitchingBenchmark,
    create_multi_model_benchmark,
)

__all__ = [
    # Core
    "GXBSRunner",
    "GXBSResult",
    "GXBSSuite",
    "GXBSBenchmark",
    "create_gxbs_runner",
    # Memory benchmarks
    "MemoryRetrievalBenchmark",
    "AssociativeActivationBenchmark",
    "create_memory_benchmark",
    # Emotion benchmarks
    "EmotionDecayBenchmark",
    "ProustEffectBenchmark",
    "create_emotion_benchmark",
    # Personality benchmarks
    "PersonalityModulationBenchmark",
    "create_personality_benchmark",
    # Multi-model benchmarks
    "ModelSwitchingBenchmark",
    "create_multi_model_benchmark",
]
