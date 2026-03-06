"""Clone Manager - 克隆体管理器

负责进化系统中克隆体的创建、管理和生命周期管理。

核心功能：
- 创建克隆体（复制项目目录）
- 分配独立端口
- 管理克隆体进程
- 清理克隆体目录

设计原则：
- 克隆目录必须在项目根目录之外，避免递归冲突
- 克隆体使用独立端口，避免运行时冲突

注意：此模块默认关闭，因为还不够成熟。
"""

import shutil
from typing import Optional, Set, Dict, Any
from pathlib import Path

from common.logger import get_logger
from .models import CloneInstance, EVOLUTION_ENABLED

logger = get_logger(__name__)


class CloneManager:
    """克隆体管理器

    负责：
    1. 创建克隆体（复制项目目录）
    2. 分配独立端口
    3. 管理克隆体进程
    4. 清理克隆体目录

    使用方式：
        manager = CloneManager(project_root, instances_dir)
        clone = manager.create_clone("clone_001")
        # ... 使用克隆体 ...
        manager.cleanup_clone(clone)
    """

    # 克隆时排除的目录和文件
    SKIP_PATTERNS = [
        "__pycache__",
        "*.pyc",
        ".pytest_cache",
        "evolution_instances",
        "evolution_archives",
        "*.log",
        ".git",
        ".idea",
        ".vscode",
        "node_modules",
        "*.pyo",
        ".DS_Store",
    ]

    def __init__(
        self,
        project_root: Path,
        instances_dir: Path = None,
        base_port: int = 8000
    ):
        """初始化克隆体管理器

        Args:
            project_root: 项目根目录
            instances_dir: 克隆体存放目录（默认在项目父目录下）
            base_port: 基础端口号
        """
        self.project_root = Path(project_root).resolve()

        # 克隆目录默认在项目根目录的父目录下
        if instances_dir is None:
            self.instances_dir = self.project_root.parent / "evolution_instances"
        else:
            self.instances_dir = Path(instances_dir).resolve()

        # 确保目录存在
        self.instances_dir.mkdir(parents=True, exist_ok=True)

        # 端口分配
        self._base_port = base_port
        self._allocated_ports: Set[int] = set()

        # 活跃的克隆体
        self._active_clones: Dict[str, CloneInstance] = {}

        # 验证路径独立性
        self._validate_path_independence()

        logger.info(f"CloneManager initialized")
        logger.info(f"  Project root: {self.project_root}")
        logger.info(f"  Instances dir: {self.instances_dir}")

    def _validate_path_independence(self):
        """验证关键路径的独立性，防止递归冲突"""
        try:
            self.instances_dir.relative_to(self.project_root)
            logger.warning(
                f"WARNING: instances_dir ({self.instances_dir}) is inside "
                f"project_root ({self.project_root}). This could cause recursive conflicts."
            )
        except ValueError:
            # 路径独立，这是安全的
            logger.info("Path independence verified: instances_dir is outside project_root")

    def _allocate_port(self) -> int:
        """为克隆体分配唯一端口

        Returns:
            分配的端口号
        """
        port = self._base_port + len(self._allocated_ports)
        while port in self._allocated_ports:
            port += 1
        self._allocated_ports.add(port)
        return port

    def _release_port(self, port: int):
        """释放端口

        Args:
            port: 要释放的端口号
        """
        self._allocated_ports.discard(port)

    def create_clone(self, clone_id: str) -> CloneInstance:
        """创建克隆体

        复制项目目录到克隆目录，排除不必要的文件。

        Args:
            clone_id: 克隆体ID

        Returns:
            CloneInstance: 创建的克隆体实例
        """
        clone_path = self.instances_dir / clone_id

        logger.info(f"Creating clone: {clone_id}")
        logger.info(f"  Parent (old body): {self.project_root}")
        logger.info(f"  Clone (new body): {clone_path}")

        # 安全检查：如果目录已存在，先删除
        if clone_path.exists():
            logger.warning(f"Existing clone directory found, removing: {clone_path}")
            shutil.rmtree(clone_path)

        # 复制项目到克隆目录
        shutil.copytree(
            self.project_root,
            clone_path,
            ignore=shutil.ignore_patterns(*self.SKIP_PATTERNS)
        )

        # 分配端口
        allocated_port = self._allocate_port()

        # 创建克隆体实例
        clone = CloneInstance(
            clone_id=clone_id,
            clone_path=clone_path,
            parent_path=self.project_root,
            port=allocated_port
        )

        # 记录活跃克隆体
        self._active_clones[clone_id] = clone

        logger.info(f"Clone created successfully. Port allocated: {allocated_port}")
        return clone

    def get_clone(self, clone_id: str) -> Optional[CloneInstance]:
        """获取克隆体

        Args:
            clone_id: 克隆体ID

        Returns:
            CloneInstance 或 None
        """
        return self._active_clones.get(clone_id)

    def list_clones(self) -> Dict[str, CloneInstance]:
        """列出所有活跃的克隆体

        Returns:
            克隆体字典
        """
        return self._active_clones.copy()

    def cleanup_clone(self, clone: CloneInstance):
        """清理克隆体

        停止进程并删除目录。

        Args:
            clone: 要清理的克隆体
        """
        logger.info(f"Cleaning up clone: {clone.clone_id}")

        # 停止进程
        clone.stop()

        # 释放端口
        if clone.port:
            self._release_port(clone.port)

        # 删除目录
        if clone.clone_path.exists():
            try:
                shutil.rmtree(clone.clone_path)
                logger.info(f"Clone directory removed: {clone.clone_path}")
            except Exception as e:
                logger.error(f"Failed to remove clone directory: {e}")

        # 从活跃列表移除
        self._active_clones.pop(clone.clone_id, None)

    def cleanup_all(self):
        """清理所有克隆体"""
        for clone_id in list(self._active_clones.keys()):
            clone = self._active_clones[clone_id]
            self.cleanup_clone(clone)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        return {
            "active_clones": len(self._active_clones),
            "allocated_ports": list(self._allocated_ports),
            "instances_dir": str(self.instances_dir),
            "project_root": str(self.project_root),
        }
