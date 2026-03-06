"""Growth System - 成长系统

成长系统负责同一个体获取新能力，包括：
- 生成新肢体（自主写代码）
- 构建和部署容器
- 学习新技能
- 能力扩展

与进化系统的区别：
- 成长：同一个体变强，不创建新个体
- 进化：创建新世代，通过复制-变异-选择迭代

论文对应：
- Section 3.8: 动态器官分化
- Section 3.10.4: Dream-Reflect-Insight (能力学习)
"""

from .limb_generator import (
    LimbGenerator,
    LimbRequirement,
    GeneratedLimb,
    LimbTemplate,
    GenerationType,
)
from .limb_builder import (
    LimbBuilder,
    BuildConfig,
    BuildResult,
    LimbDeployment,
    create_limb_builder,
    build_and_deploy,
)
from .growth_manager import (
    GrowthManager,
    GrowthEvent,
    create_growth_manager,
)

__all__ = [
    # 肢体生成
    "LimbGenerator",
    "LimbRequirement",
    "GeneratedLimb",
    "LimbTemplate",
    "GenerationType",
    # 肢体构建
    "LimbBuilder",
    "BuildConfig",
    "BuildResult",
    "LimbDeployment",
    "create_limb_builder",
    "build_and_deploy",
    # 成长管理
    "GrowthManager",
    "GrowthEvent",
    "create_growth_manager",
]
