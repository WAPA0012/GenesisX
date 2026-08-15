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
# 注：dream.py（DreamDirector 第二套实现）和 personality_encoding.py（论文§3.4.4 孤立实现）
# 已删除——前者与 consolidation.DreamConsolidator 重复且零运行时引用，
# 后者写好但从未接入 episodic.append 写入路径。详见 CODE_MAP P3-13/P3-20。

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

# 肢体使用指南目录（memory/limb_guides/data/ 存 organ_guides.json）
# 注：原 limb_guides 包的 4 个指南文件与 memory/skills/ 逐字节重复且导入即崩，
# 已删除（CODE_MAP P3-22）。limb_guides/ 现仅作为 organ_guide_manager 的数据目录。

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

# Personality-modulated memory encoding (论文 3.4.4) — personality_encoding.py 已删除（孤立，见上注）

