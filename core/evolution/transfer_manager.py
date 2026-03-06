"""Transfer Manager - 意识转移管理器

负责进化系统中的意识转移操作。

意识转移是进化的关键步骤：
- 将经过验证的克隆体的变更复制回原个体
- 保留原有的记忆和个性
- 确保转移过程的安全性

转移流程：
1. 验证克隆体评估结果
2. 备份当前状态
3. 复制变更文件
4. 验证转移完整性
5. 记录转移历史

注意：此模块默认关闭，因为还不够成熟。
"""

import time
import shutil
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime

from common.logger import get_logger
from .models import CloneInstance, EvolutionMetrics, EvolutionProposal, EVOLUTION_ENABLED

logger = get_logger(__name__)


class TransferManager:
    """意识转移管理器

    负责：
    1. 验证转移条件
    2. 执行意识转移
    3. 验证转移结果
    4. 管理转移历史

    使用方式：
        manager = TransferManager(project_root)
        if manager.can_transfer(clone, metrics):
            success = manager.transfer(clone, proposal, metrics)
    """

    def __init__(
        self,
        project_root: Path,
        config: Dict[str, Any] = None
    ):
        """初始化转移管理器

        Args:
            project_root: 项目根目录（原个体）
            config: 配置
        """
        self.project_root = Path(project_root).resolve()
        self.config = config or {}

        # 转移历史
        self._transfer_history: List[Dict[str, Any]] = []

        # 备份目录
        self._backup_dir = self.project_root.parent / "evolution_backups"
        self._backup_dir.mkdir(parents=True, exist_ok=True)

        logger.info("TransferManager initialized")

    def can_transfer(self, metrics: EvolutionMetrics) -> bool:
        """检查是否可以进行转移

        Args:
            metrics: 评估指标

        Returns:
            是否可以转移
        """
        return metrics.should_transfer()

    def transfer(
        self,
        clone: CloneInstance,
        proposal: EvolutionProposal,
        metrics: EvolutionMetrics
    ) -> bool:
        """执行意识转移

        将克隆体中的变更复制回原个体。

        Args:
            clone: 克隆体实例
            proposal: 进化提案
            metrics: 评估指标

        Returns:
            是否成功
        """
        logger.info(f"Starting consciousness transfer from clone {clone.clone_id}")

        # 1. 验证转移条件
        if not self.can_transfer(metrics):
            logger.warning(f"Clone {clone.clone_id} did not pass evaluation, transfer denied")
            return False

        # 2. 创建备份
        backup_path = self._create_backup()
        if backup_path:
            logger.info(f"Backup created at: {backup_path}")

        # 3. 执行转移
        try:
            transferred_files = []

            for file_path in proposal.target_files:
                source = clone.clone_path / file_path
                target = self.project_root / file_path

                if source.exists():
                    # 确保目标目录存在
                    target.parent.mkdir(parents=True, exist_ok=True)

                    # 复制文件
                    shutil.copy2(source, target)
                    transferred_files.append(file_path)
                    logger.debug(f"Transferred: {file_path}")

            logger.info(f"Transferred {len(transferred_files)} files")

            # 4. 记录转移历史
            self._transfer_history.append({
                "timestamp": time.time(),
                "clone_id": clone.clone_id,
                "success": True,
                "files_transferred": transferred_files,
                "backup_path": str(backup_path) if backup_path else None,
                "metrics_score": metrics.overall_score(),
            })

            logger.info("Consciousness transfer completed successfully")
            return True

        except Exception as e:
            logger.error(f"Transfer failed: {e}")

            # 记录失败
            self._transfer_history.append({
                "timestamp": time.time(),
                "clone_id": clone.clone_id,
                "success": False,
                "error": str(e),
                "backup_path": str(backup_path) if backup_path else None,
            })

            # 尝试恢复备份
            if backup_path:
                logger.info("Attempting to restore from backup...")
                self._restore_backup(backup_path)

            return False

    def _create_backup(self) -> Optional[Path]:
        """创建当前状态备份

        Returns:
            备份路径，如果失败返回 None
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"pre_transfer_{timestamp}"
            backup_path = self._backup_dir / backup_name

            # 复制核心目录
            core_dirs = ["core", "config", "memory"]
            for dir_name in core_dirs:
                src = self.project_root / dir_name
                if src.exists():
                    dst = backup_path / dir_name
                    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(
                        "__pycache__", "*.pyc", "*.pyo"
                    ))

            logger.info(f"Backup created: {backup_path}")
            return backup_path

        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            return None

    def _restore_backup(self, backup_path: Path) -> bool:
        """从备份恢复

        Args:
            backup_path: 备份路径

        Returns:
            是否成功
        """
        try:
            if not backup_path.exists():
                logger.error(f"Backup not found: {backup_path}")
                return False

            # 恢复核心目录
            core_dirs = ["core", "config", "memory"]
            for dir_name in core_dirs:
                src = backup_path / dir_name
                dst = self.project_root / dir_name

                if src.exists():
                    # 删除当前目录
                    if dst.exists():
                        shutil.rmtree(dst)

                    # 恢复备份
                    shutil.copytree(src, dst)

            logger.info(f"Restored from backup: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"Backup restore failed: {e}")
            return False

    def get_transfer_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取转移历史

        Args:
            limit: 最大返回数量

        Returns:
            转移历史列表
        """
        return self._transfer_history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        successful = sum(1 for t in self._transfer_history if t.get("success"))
        failed = len(self._transfer_history) - successful

        return {
            "total_transfers": len(self._transfer_history),
            "successful_transfers": successful,
            "failed_transfers": failed,
            "backup_dir": str(self._backup_dir),
        }

    def cleanup_old_backups(self, keep_count: int = 5):
        """清理旧备份

        Args:
            keep_count: 保留的备份数量
        """
        try:
            backups = sorted(
                self._backup_dir.glob("pre_transfer_*"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )

            for old_backup in backups[keep_count:]:
                shutil.rmtree(old_backup)
                logger.info(f"Removed old backup: {old_backup}")

        except Exception as e:
            logger.error(f"Backup cleanup failed: {e}")
