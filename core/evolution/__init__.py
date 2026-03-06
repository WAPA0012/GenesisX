"""Evolution System - 进化系统

进化系统负责创建新世代，通过复制-变异-选择实现自我迭代。

核心流程：
1. CLONE: 复制当前个体，创建进化实验体
2. MUTATE: 在实验体上进行代码/架构修改
3. TEST: 让实验体实际运行，进行全面测试
4. EVALUATE: 评估实验体的表现
5. TRANSFER: 如果评估通过，转移意识和记忆到新个体
6. ARCHIVE: 将旧躯体完整打包存档
7. RETIRE: 关闭旧躯体，启用新个体

架构设计（模块化）：
    EvolutionEngine (协调器)
    ├── CloneManager (克隆体管理)
    ├── MutationManager (变异管理)
    ├── EvaluationManager (评估管理)
    ├── TransferManager (意识转移)
    └── ArchiveManager (存档管理)

与成长系统的区别：
- 成长：同一个体变强，不创建新个体
- 进化：创建新世代，通过复制-变异-选择迭代

论文对应：
- Section 3.9: 自我进化（吞噬软件）
- Section 3.10.5: Evolution Trigger

注意：此系统默认关闭，因为还不够成熟。
"""

# 数据模型
from .models import (
    EVOLUTION_ENABLED,
    EvolutionPhase,
    MutationType,
    EvolutionProposal,
    CloneInstance,
    EvolutionMetrics,
)

# 子管理器
from .clone_manager import CloneManager
from .mutation_manager import MutationManager
from .evaluation_manager import EvaluationManager
from .transfer_manager import TransferManager
from .archive_manager import ArchiveManager

# 主引擎
from .evolution_engine import EvolutionEngine, get_evolution_engine

__all__ = [
    # 数据模型
    "EVOLUTION_ENABLED",
    "EvolutionPhase",
    "MutationType",
    "EvolutionProposal",
    "CloneInstance",
    "EvolutionMetrics",
    # 子管理器
    "CloneManager",
    "MutationManager",
    "EvaluationManager",
    "TransferManager",
    "ArchiveManager",
    # 主引擎
    "EvolutionEngine",
    "get_evolution_engine",
]
