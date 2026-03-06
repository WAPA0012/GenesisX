"""Memory system - Episodic, Schema, and Skill layers.

Implements the three-layer complementary learning system (CLS):
- Episodic: event-sourcing, append-only episodes
- Schema: compressed knowledge with evidence and confidence
- Skill: executable procedures with risk/cost profiles
- Dream: dream-reflect-insight mechanism for consolidation
- Semantic Novelty: embedding-based novelty evaluation

知识分类：
- skills/ = 外部工具调用技能（网上下载的，调用第三方API）
- limb_guides/ = 肢体使用指南（怎么用自己的肢体）
"""
import warnings

# 修复: 可选模块导入时添加日志记录
_module_import_warnings = []
from .episodic import EpisodicMemory
from .schema import SchemaMemory
from .skill import SkillMemory
from .retrieval import MemoryRetrieval
from .consolidation import DreamConsolidator
from .salience import compute_salience
from .dream import DreamEngine, DreamDirector, DreamPhase, DreamReport, create_dream_engine, create_dream_director

# 外部工具调用技能（网上下载的）
try:
    from .skills import (
        BaseSkill,
        SkillResult,
        SkillCost,
        SkillCostType,
        SkillRegistry,
        get_global_registry,
        # 向后兼容
        FileSkill,
        WebSkill,
        PDFSkill,
        AnalysisSkill,
    )
    _skills_available = True
except ImportError as e:
    _skills_available = False
    _module_import_warnings.append(f"Skills module not available: {e}")

# 肢体使用指南（怎么用自己的肢体）
try:
    from .limb_guides import (
        FileOpsGuide,
        WebFetcherGuide,
        DataAnalysisGuide,
        PDFProcessingGuide,
    )
    _limb_guides_available = True
except ImportError as e:
    _limb_guides_available = False
    _module_import_warnings.append(f"Limb guides module not available: {e}")

# 器官指南管理器（自动管理器官使用指南）
try:
    from .organ_guide_manager import (
        OrganGuide,
        OrganGuideManager,
        get_organ_guide_manager,
    )
    _organ_guide_manager_available = True
except ImportError as e:
    _organ_guide_manager_available = False
    _module_import_warnings.append(f"Organ guide manager not available: {e}")

# Semantic novelty (论文 P1-4: 使用语义嵌入评估新颖性)
try:
    from .semantic_novelty import (
        SemanticNoveltyCalculator,
        EmbeddingConfig,
        compute_novelty,
        get_default_calculator,
    )
except ImportError as e:
    SemanticNoveltyCalculator = None
    EmbeddingConfig = None
    compute_novelty = None
    get_default_calculator = None
    _module_import_warnings.append(f"Semantic novelty module not available: {e}")

__all__ = [
    # 核心记忆层
    "EpisodicMemory",
    "SchemaMemory",
    "SkillMemory",
    "MemoryRetrieval",
    "DreamConsolidator",
    "compute_salience",
    "DreamEngine",
    "DreamDirector",
    "DreamPhase",
    "DreamReport",
    "create_dream_engine",
    "create_dream_director",
    # Semantic novelty
    "SemanticNoveltyCalculator",
    "EmbeddingConfig",
    "compute_novelty",
    "get_default_calculator",
    # 外部工具调用技能
    "BaseSkill",
    "SkillResult",
    "SkillCost",
    "SkillCostType",
    "SkillRegistry",
    "get_global_registry",
    # 肢体使用指南
    "FileOpsGuide",
    "WebFetcherGuide",
    "DataAnalysisGuide",
    "PDFProcessingGuide",
    # 器官指南管理器
    "OrganGuide",
    "OrganGuideManager",
    "get_organ_guide_manager",
    # 向后兼容
    "FileSkill",
    "WebSkill",
    "PDFSkill",
    "AnalysisSkill",
]

# Familiarity signal and associative memory (论文 3.4.3)
# 修复: 导入实际存在的类 (familiarity.py 中定义的类)
try:
    from .familiarity import (
        AssociationType,
        AssociationEdge,
        AssociativeNode,  # 修复: 原来错误的 MemoryNode
        AssociativeNetwork,
        AssociativeMemory,
        create_associative_memory,  # 修复: 原来错误的 create_associative_network
    )
    __all__.extend([
        "AssociationType",
        "AssociationEdge",
        "AssociativeNode",  # 修复
        "AssociativeNetwork",
        "AssociativeMemory",
        "create_associative_memory",  # 修复
    ])
except ImportError:
    pass

# Personality-modulated memory encoding (论文 3.4.4)
try:
    from .personality_encoding import (
        PersonalityMiddleVars,
        MemoryDomain,
        EmotionalTag,
        PersonalityModulatedTagging,
        CrossDomainAssociation,
        CrossDomainAssociationCalculator,
        PersonalityModulatedConsolidation,
        NoveltySensitivityCalculator,
        EncodingContext,
        EncodingResult,
        PersonalityModulatedEncoder,
        # Factory functions
        create_personality_vars,
        create_encoder,
        create_encoding_context,
    )
    __all__.extend([
        "PersonalityMiddleVars",
        "MemoryDomain",
        "EmotionalTag",
        "PersonalityModulatedTagging",
        "CrossDomainAssociation",
        "CrossDomainAssociationCalculator",
        "PersonalityModulatedConsolidation",
        "NoveltySensitivityCalculator",
        "EncodingContext",
        "EncodingResult",
        "PersonalityModulatedEncoder",
        "create_personality_vars",
        "create_encoder",
        "create_encoding_context",
    ])
except ImportError:
    pass
