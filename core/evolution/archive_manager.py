"""Archive Manager - 存档管理器

负责进化系统中旧躯体的存档操作。

存档是进化完成后的重要步骤：
- 将旧躯体完整打包保存
- 记录进化元数据
- 便于回滚和历史追踪

存档内容：
- 完整的项目代码
- 配置文件
- 记忆数据
- 进化元数据

存档命名格式：
- generation_{X}_end_{timestamp}.zip

注意：此模块默认关闭，因为还不够成熟。
"""

import time
import zipfile
import json
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime

from common.logger import get_logger
from .models import EvolutionMetrics, EvolutionProposal, EVOLUTION_ENABLED

logger = get_logger(__name__)


class ArchiveManager:
    """存档管理器

    负责：
    1. 存档旧躯体
    2. 管理存档元数据
    3. 清理旧存档
    4. 存档检索

    使用方式：
        manager = ArchiveManager(archive_dir)
        archive_path = manager.archive(old_body_path, proposal, metrics)
    """

    # 存档时排除的模式
    SKIP_PATTERNS = [
        '__pycache__',
        '.pyc',
        '.pytest_cache',
        '*.log',
        '.DS_Store',
        'evolution_instances',
        'evolution_archives',
        '.git',
        '.idea',
        '.vscode',
        'node_modules',
        '*.pyo',
    ]

    def __init__(
        self,
        archive_dir: Path,
        config: Dict[str, Any] = None
    ):
        """初始化存档管理器

        Args:
            archive_dir: 存档目录
            config: 配置
        """
        self.archive_dir = Path(archive_dir).resolve()
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self.config = config or {}

        # 当前代际（从配置或元数据加载）
        self._generation = 0
        self._generation_log: List[Dict[str, Any]] = []

        # 加载代际历史
        self._load_generation_log()

        logger.info("ArchiveManager initialized")
        logger.info(f"  Archive dir: {self.archive_dir}")
        logger.info(f"  Current generation: {self._generation}")

    def _load_generation_log(self):
        """加载代际历史"""
        log_path = self.archive_dir / "generation_log.json"
        if log_path.exists():
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._generation = data.get("current_generation", 0)
                    self._generation_log = data.get("log", [])
                logger.info(f"Loaded generation log: generation {self._generation}")
            except Exception as e:
                logger.warning(f"Failed to load generation log: {e}")

    def _save_generation_log(self):
        """保存代际历史"""
        log_path = self.archive_dir / "generation_log.json"
        try:
            data = {
                "current_generation": self._generation,
                "log": self._generation_log,
                "last_updated": datetime.now().isoformat(),
            }
            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save generation log: {e}")

    def archive(
        self,
        old_body_path: Path,
        proposal: EvolutionProposal,
        metrics: EvolutionMetrics
    ) -> Optional[Path]:
        """存档旧躯体

        Args:
            old_body_path: 旧躯体路径
            proposal: 进化提案
            metrics: 评估指标

        Returns:
            存档文件路径，如果失败返回 None
        """
        old_body_path = Path(old_body_path).resolve()

        # 安全检查
        if old_body_path == self.archive_dir:
            logger.error("Cannot archive the archive directory itself!")
            return None

        # 生成存档文件名
        end_date = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"generation_{self._generation}_end_{end_date}.zip"
        archive_path = self.archive_dir / archive_name

        logger.info(f"Archiving old body: {old_body_path}")
        logger.info(f"Archive destination: {archive_name}")

        try:
            # 创建压缩包
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                file_count = 0

                for file_path in old_body_path.rglob('*'):
                    if not file_path.is_file():
                        continue

                    # 跳过不需要的文件
                    if any(skip in str(file_path) for skip in self.SKIP_PATTERNS):
                        continue

                    # 计算相对路径
                    try:
                        rel_path = file_path.relative_to(old_body_path)
                    except ValueError:
                        continue

                    # 添加到压缩包
                    zipf.write(file_path, rel_path)
                    file_count += 1

                logger.info(f"Archived {file_count} files")

            # 创建元数据
            metadata = self._create_metadata(proposal, metrics, end_date)

            # 附加元数据到压缩包
            metadata_path = self.archive_dir / f"temp_metadata_{end_date}.json"
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

            with zipfile.ZipFile(archive_path, 'a', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(metadata_path, "metadata.json")

            # 删除临时文件
            metadata_path.unlink()

            # 更新代际日志
            self._generation_log.append({
                "generation": self._generation,
                "end_date": end_date,
                "archive_path": str(archive_path),
                "archive_size_mb": archive_path.stat().st_size / 1024 / 1024,
                "proposal": proposal.description,
                "metrics_score": metrics.overall_score(),
            })

            # 递增代际
            self._generation += 1
            self._save_generation_log()

            logger.info(
                f"Archive completed: {archive_path.name} "
                f"({archive_path.stat().st_size / 1024 / 1024:.1f} MB)"
            )

            return archive_path

        except Exception as e:
            logger.error(f"Archive failed: {e}")
            return None

    def _create_metadata(
        self,
        proposal: EvolutionProposal,
        metrics: EvolutionMetrics,
        end_date: str
    ) -> Dict[str, Any]:
        """创建存档元数据

        Args:
            proposal: 进化提案
            metrics: 评估指标
            end_date: 结束日期

        Returns:
            元数据字典
        """
        return {
            "generation": self._generation,
            "end_date": end_date,
            "end_timestamp": time.time(),
            "evolution_proposal": {
                "type": proposal.mutation_type.value,
                "description": proposal.description,
                "target_files": proposal.target_files,
                "expected_benefit": proposal.expected_benefit,
                "risk_level": proposal.risk_level,
            },
            "final_metrics": metrics.to_dict(),
            "archive_created_at": time.time(),
        }

    def list_archives(self) -> List[Dict[str, Any]]:
        """列出所有存档

        Returns:
            存档列表
        """
        archives = []

        for archive_file in self.archive_dir.glob("generation_*.zip"):
            try:
                stat = archive_file.stat()
                archives.append({
                    "path": str(archive_file),
                    "name": archive_file.name,
                    "size_mb": stat.st_size / 1024 / 1024,
                    "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
            except Exception as e:
                logger.warning(f"Failed to read archive {archive_file}: {e}")

        # 按创建时间排序（最新的在前）
        archives.sort(key=lambda x: x["created_at"], reverse=True)
        return archives

    def get_archive_metadata(self, archive_path: Path) -> Optional[Dict[str, Any]]:
        """获取存档元数据

        Args:
            archive_path: 存档路径

        Returns:
            元数据字典，如果失败返回 None
        """
        try:
            with zipfile.ZipFile(archive_path, 'r') as zipf:
                if "metadata.json" in zipf.namelist():
                    with zipf.open("metadata.json") as f:
                        return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read archive metadata: {e}")

        return None

    def cleanup_old_archives(self, keep_count: int = 10):
        """清理旧存档

        Args:
            keep_count: 保留的存档数量
        """
        try:
            archives = sorted(
                self.archive_dir.glob("generation_*.zip"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )

            for old_archive in archives[keep_count:]:
                old_archive.unlink()
                logger.info(f"Removed old archive: {old_archive}")

        except Exception as e:
            logger.error(f"Archive cleanup failed: {e}")

    def get_generation_info(self) -> Dict[str, Any]:
        """获取代际信息

        Returns:
            代际信息字典
        """
        return {
            "current_generation": self._generation,
            "total_archives": len(self._generation_log),
            "archives": self._generation_log[-5:] if self._generation_log else [],
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        archives = self.list_archives()
        total_size = sum(a["size_mb"] for a in archives)

        return {
            "archive_dir": str(self.archive_dir),
            "current_generation": self._generation,
            "total_archives": len(archives),
            "total_size_mb": total_size,
        }
