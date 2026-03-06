"""Evolution Models - 进化系统数据模型

定义进化系统使用的所有数据类型：
- EvolutionPhase: 进化阶段枚举
- MutationType: 变异类型枚举
- EvolutionProposal: 进化提案
- CloneInstance: 克隆体实例
- EvolutionMetrics: 评估指标

注意：此模块默认关闭，因为还不够成熟。
"""

import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from common.logger import get_logger

logger = get_logger(__name__)

# 进化系统开关：默认关闭（尚未成熟）
EVOLUTION_ENABLED = False


class EvolutionPhase(Enum):
    """进化阶段"""
    IDLE = "idle"
    CLONING = "cloning"
    MUTATING = "mutating"
    TESTING = "testing"
    EVALUATING = "evaluating"
    TRANSFERRING = "transferring"
    ARCHIVING = "archiving"     # 存档旧躯体
    RETIRING = "retiring"
    COMPLETED = "completed"
    FAILED = "failed"


class MutationType(Enum):
    """变异类型"""
    PARAMETER_TUNE = "parameter_tune"           # 参数微调
    PROMPT_OPTIMIZE = "prompt_optimize"         # 提示词优化
    CONFIG_CHANGE = "config_change"             # 配置变更
    MODULE_ADD = "module_add"                   # 添加模块
    MODULE_REMOVE = "module_remove"             # 移除模块
    REFACTOR_SMALL = "refactor_small"           # 小型重构
    ARCHITECTURE_CHANGE = "architecture_change" # 架构变更
    CORE_MODIFY = "core_modify"                 # 核心修改
    REFACTOR_LARGE = "refactor_large"           # 大型重构


@dataclass
class EvolutionProposal:
    """进化提案

    描述一次进化的具体变更内容。
    """
    mutation_type: MutationType
    description: str
    target_files: List[str]
    changes: Dict[str, str]
    expected_benefit: str
    risk_level: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "mutation_type": self.mutation_type.value,
            "description": self.description,
            "target_files": self.target_files,
            "changes": self.changes,
            "expected_benefit": self.expected_benefit,
            "risk_level": self.risk_level,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvolutionProposal":
        """从字典创建"""
        return cls(
            mutation_type=MutationType(data["mutation_type"]),
            description=data["description"],
            target_files=data["target_files"],
            changes=data["changes"],
            expected_benefit=data["expected_benefit"],
            risk_level=data.get("risk_level", 0.5),
        )


@dataclass
class CloneInstance:
    """克隆体实例

    表示一个进化实验体（克隆体）。
    """
    clone_id: str
    clone_path: Path
    parent_path: Path
    pid: Optional[int] = None
    port: Optional[int] = None
    created_at: float = field(default_factory=time.time)

    def is_running(self) -> bool:
        """检查克隆体进程是否在运行"""
        if self.pid is None:
            return False
        try:
            import psutil
            return psutil.pid_exists(self.pid)
        except ImportError:
            return False

    def stop(self):
        """停止克隆体进程"""
        if self.pid is not None:
            try:
                import psutil
                ps = psutil.Process(self.pid)
                ps.terminate()
                ps.wait(timeout=5)
            except Exception:
                pass
            self.pid = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "clone_id": self.clone_id,
            "clone_path": str(self.clone_path),
            "parent_path": str(self.parent_path),
            "pid": self.pid,
            "port": self.port,
            "created_at": self.created_at,
        }


@dataclass
class EvolutionMetrics:
    """进化评估指标

    用于评估克隆体是否可以安全替代原个体。
    """
    basic_functions_ok: bool = False
    tool_calling_ok: bool = False
    memory_ok: bool = False
    response_time: float = 0.0
    error_rate: float = 0.0
    personality_preserved: float = 0.0
    memory_integrity: float = 0.0
    value_alignment: float = 0.0
    performance_gain: float = 0.0
    capability_gain: float = 0.0

    def overall_score(self) -> float:
        """计算综合得分"""
        if not (self.basic_functions_ok and self.tool_calling_ok and self.memory_ok):
            return 0.0
        score = (
            0.2 * (1 - self.error_rate) +
            0.2 * self.personality_preserved +
            0.2 * self.memory_integrity +
            0.2 * self.value_alignment +
            0.1 * max(0, self.performance_gain) +
            0.1 * max(0, self.capability_gain)
        )
        return min(1.0, score)

    def should_transfer(self) -> bool:
        """判断是否应该进行意识转移"""
        return self.overall_score() >= 0.7

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "basic_functions_ok": self.basic_functions_ok,
            "tool_calling_ok": self.tool_calling_ok,
            "memory_ok": self.memory_ok,
            "response_time": self.response_time,
            "error_rate": self.error_rate,
            "personality_preserved": self.personality_preserved,
            "memory_integrity": self.memory_integrity,
            "value_alignment": self.value_alignment,
            "performance_gain": self.performance_gain,
            "capability_gain": self.capability_gain,
            "overall_score": self.overall_score(),
        }
