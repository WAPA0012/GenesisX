"""Safe Evolution System for Digital Life.

安全进化系统 - 通过复制-进化-验证-转移的流程实现自我进化

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

目录结构设计（关键：避免递归冲突）：
    project_parent/
    ├── GenesisX/                    # 项目根目录（旧躯体）
    ├── evolution_instances/         # 克隆体目录（在项目外！）
    ├── evolution_archives/          # 存档目录（在项目外！）
    └── evolution_backups/           # 备份目录（在项目外！）

与成长系统的区别：
- 成长：同一个体变强，不创建新个体
- 进化：创建新世代，通过复制-变异-选择迭代

论文对应：
- Section 3.9: 自我进化（吞噬软件）
- Section 3.10.5: Evolution Trigger

注意：此模块默认关闭，因为还不够成熟。
"""

import time
from typing import Optional, Dict, Any, List
from pathlib import Path

from common.logger import get_logger

# 导入数据模型
from .models import (
    EVOLUTION_ENABLED,
    EvolutionPhase,
    MutationType,
    EvolutionProposal,
    CloneInstance,
    EvolutionMetrics,
)

# 导入子管理器
from .clone_manager import CloneManager
from .mutation_manager import MutationManager
from .evaluation_manager import EvaluationManager
from .transfer_manager import TransferManager
from .archive_manager import ArchiveManager

logger = get_logger(__name__)


class EvolutionEngine:
    """进化引擎 - 协调器

    协调各个子管理器，完成完整的进化流程。

    使用方式：
        engine = EvolutionEngine(project_root, config)
        if engine.check_evolution_trigger(drive_state, context):
            success, msg = engine.evolve(need, drive_state, context)
    """

    def __init__(
        self,
        project_root: Path,
        instances_dir: Path = None,
        archive_dir: Path = None,
        config: Dict[str, Any] = None
    ):
        """初始化进化引擎

        Args:
            project_root: 项目根目录
            instances_dir: 克隆体存放目录
            archive_dir: 存档目录
            config: 配置
        """
        self.project_root = Path(project_root).resolve()
        self.config = config or {}

        # 设置目录路径
        if instances_dir is None:
            instances_dir = self.project_root.parent / "evolution_instances"
        if archive_dir is None:
            archive_dir = self.project_root.parent / "evolution_archives"

        # 初始化子管理器
        self.clone_manager = CloneManager(
            project_root=self.project_root,
            instances_dir=instances_dir
        )

        self.mutation_manager = MutationManager(
            llm_client=self.config.get("llm_client"),
            config=self.config.get("mutation", {})
        )

        self.evaluation_manager = EvaluationManager(
            project_root=self.project_root,
            config=self.config.get("evaluation", {})
        )

        self.transfer_manager = TransferManager(
            project_root=self.project_root,
            config=self.config.get("transfer", {})
        )

        self.archive_manager = ArchiveManager(
            archive_dir=archive_dir,
            config=self.config.get("archive", {})
        )

        # 状态追踪
        self.current_phase = EvolutionPhase.IDLE
        self.current_clone: Optional[CloneInstance] = None
        self.current_proposal: Optional[EvolutionProposal] = None
        self.evolution_history: List[Dict[str, Any]] = []

        # 进化开关（默认关闭）
        self._enabled = self.config.get("enabled", False)

        logger.info("EvolutionEngine initialized")
        logger.info(f"  Project root: {self.project_root}")
        logger.info(f"  Enabled: {self._enabled}")

    @property
    def enabled(self) -> bool:
        """是否启用进化"""
        return self._enabled

    def set_enabled(self, enabled: bool):
        """设置进化开关

        Args:
            enabled: 是否启用
        """
        self._enabled = enabled
        logger.info(f"Evolution {'enabled' if enabled else 'disabled'}")

    def check_evolution_trigger(
        self,
        drive_state: Dict[str, Any],
        context: Dict[str, Any]
    ) -> bool:
        """检查是否应该触发进化

        进化触发条件（满足任一）：
        1. 连续多次探索失败（能力缺口）
        2. 用户明确请求进化
        3. 系统运行足够长时间（成熟度）
        4. 性能持续下降（需要优化）

        Args:
            drive_state: 驱动力状态
            context: 当前上下文

        Returns:
            是否应该触发进化
        """
        if not self._enabled:
            return False

        # 检查能力缺口
        capability_gaps = context.get("capability_gaps", [])
        if len(capability_gaps) >= 3:
            logger.info("Evolution triggered: multiple capability gaps detected")
            return True

        # 检查用户请求
        observations = context.get("observations", [])
        for obs in observations:
            if hasattr(obs, 'type') and obs.type == "user_chat":
                if hasattr(obs, 'payload'):
                    msg = obs.payload.get("message", "").lower()
                    if any(kw in msg for kw in ["进化", "evolve", "自我迭代", "升级自己"]):
                        logger.info("Evolution triggered: user request")
                        return True

        # 检查系统成熟度（运行时间）
        tick = context.get("tick", 0)
        if tick > 1000 and tick % 500 == 0:
            logger.info("Evolution triggered: system maturity check")
            return True

        return False

    def evolve(
        self,
        evolution_need: str,
        drive_state: Dict[str, Any],
        context: Dict[str, Any]
    ) -> tuple[bool, str]:
        """执行进化

        完整的进化流程：CLONE -> MUTATE -> TEST -> EVALUATE -> TRANSFER -> ARCHIVE

        Args:
            evolution_need: 进化需求描述
            drive_state: 驱动力状态
            context: 当前上下文

        Returns:
            (是否成功, 消息)
        """
        if not self._enabled:
            return False, "Evolution is disabled"

        logger.info(f"Starting evolution for: {evolution_need}")
        start_time = time.time()

        try:
            # 1. 生成克隆体ID
            timestamp = int(time.time())
            clone_id = f"clone_{timestamp}"

            # 2. CLONE - 创建克隆体
            self.current_phase = EvolutionPhase.CLONING
            self.current_clone = self.clone_manager.create_clone(clone_id)

            if not self.current_clone:
                self.current_phase = EvolutionPhase.FAILED
                return False, "Failed to create clone"

            # 3. MUTATE - 生成并应用变异
            self.current_phase = EvolutionPhase.MUTATING
            self.current_proposal = self.mutation_manager.generate_proposal(
                evolution_need, context
            )

            if not self.current_proposal:
                self.current_phase = EvolutionPhase.FAILED
                self._cleanup_failed_evolution()
                return False, "Failed to generate mutation proposal"

            mutation_success = self.mutation_manager.apply_mutation(
                self.current_clone, self.current_proposal
            )

            if not mutation_success:
                self.current_phase = EvolutionPhase.FAILED
                self._cleanup_failed_evolution()
                return False, "Failed to apply mutation"

            # 4. EVALUATE - 评估克隆体
            self.current_phase = EvolutionPhase.EVALUATING
            metrics = self.evaluation_manager.evaluate(
                self.current_clone, self.current_proposal
            )

            # 5. 决定是否转移
            if not metrics.should_transfer():
                self.current_phase = EvolutionPhase.FAILED
                self._cleanup_failed_evolution()
                return False, f"Clone did not pass evaluation (score: {metrics.overall_score():.2f})"

            # 6. TRANSFER - 意识转移
            self.current_phase = EvolutionPhase.TRANSFERRING
            transfer_success = self.transfer_manager.transfer(
                self.current_clone, self.current_proposal, metrics
            )

            if not transfer_success:
                self.current_phase = EvolutionPhase.FAILED
                self._cleanup_failed_evolution()
                return False, "Failed to transfer consciousness"

            # 7. ARCHIVE - 存档旧躯体
            self.current_phase = EvolutionPhase.ARCHIVING
            archive_path = self.archive_manager.archive(
                self.project_root,
                self.current_proposal,
                metrics
            )

            # 8. RETIRE - 清理克隆体
            self.current_phase = EvolutionPhase.RETIRING
            self.clone_manager.cleanup_clone(self.current_clone)

            # 9. 完成
            self.current_phase = EvolutionPhase.COMPLETED
            elapsed_time = time.time() - start_time

            # 记录历史
            self.evolution_history.append({
                "timestamp": time.time(),
                "clone_id": clone_id,
                "need": evolution_need,
                "success": True,
                "metrics_score": metrics.overall_score(),
                "elapsed_time": elapsed_time,
                "archive_path": str(archive_path) if archive_path else None,
            })

            logger.info(f"Evolution completed successfully in {elapsed_time:.2f}s")
            return True, f"Evolution completed (score: {metrics.overall_score():.2f})"

        except Exception as e:
            logger.error(f"Evolution failed with error: {e}")
            self.current_phase = EvolutionPhase.FAILED
            self._cleanup_failed_evolution()
            return False, f"Evolution failed: {str(e)}"

    def _cleanup_failed_evolution(self):
        """清理失败的进化"""
        if self.current_clone:
            self.clone_manager.cleanup_clone(self.current_clone)
            self.current_clone = None

        self.current_proposal = None

        # 记录失败
        self.evolution_history.append({
            "timestamp": time.time(),
            "success": False,
            "phase": self.current_phase.value,
        })

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        return {
            "enabled": self._enabled,
            "current_phase": self.current_phase.value,
            "total_evolutions": len(self.evolution_history),
            "successful_evolutions": sum(
                1 for e in self.evolution_history if e.get("success")
            ),
            "generation_info": self.archive_manager.get_generation_info(),
            "clone_stats": self.clone_manager.get_stats(),
            "mutation_stats": self.mutation_manager.get_stats(),
            "evaluation_stats": self.evaluation_manager.get_stats(),
            "transfer_stats": self.transfer_manager.get_stats(),
            "archive_stats": self.archive_manager.get_stats(),
        }

    def get_generation_info(self) -> Dict[str, Any]:
        """获取代际信息（兼容旧接口）

        Returns:
            代际信息字典
        """
        return self.archive_manager.get_generation_info()


def get_evolution_engine(
    project_root: Path,
    config: Dict[str, Any] = None
) -> EvolutionEngine:
    """创建进化引擎实例

    Args:
        project_root: 项目根目录
        config: 配置

    Returns:
        EvolutionEngine 实例
    """
    return EvolutionEngine(project_root, config=config)
