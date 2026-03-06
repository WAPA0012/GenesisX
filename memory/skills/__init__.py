"""Skills Memory - 外部工具调用技能

存储"怎么调用外部工具/第三方API"的知识。

这些技能是从网上下载的，描述如何调用外部服务（如 OpenAI API、GitHub API 等）。

与 limb_guides/ 的区别：
- skills/ = 怎么调用外部工具/第三方API（网上下载的）
- limb_guides/ = 怎么用自己的肢体（Docker容器，自己生成的）

命名说明：
- "Skill" 在网上的理解：如何使用外部工具完成想做的事
- 这些技能依赖第三方服务，有风险、可能需要付费
"""
from .base import BaseSkill, SkillResult, SkillCost, SkillCostType
from .skill_registry import SkillRegistry, get_global_registry

# 向后兼容：保留旧的肢体相关技能（已废弃，请使用 limb_guides）
from .file_skill import FileSkill
from .web_skill import WebSkill
from .pdf_skill import PDFSkill
from .analysis_skill import AnalysisSkill

__all__ = [
    # 基础类
    "BaseSkill",
    "SkillResult",
    "SkillCost",
    "SkillCostType",
    "SkillRegistry",
    "get_global_registry",
    # 向后兼容（已废弃，请使用 limb_guides）
    "FileSkill",
    "WebSkill",
    "PDFSkill",
    "AnalysisSkill",
]
