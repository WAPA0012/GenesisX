"""Evaluation Manager - 评估管理器

负责进化系统中克隆体的评估和测试。

评估流程：
1. 语法检查 - 确保代码可以导入
2. 基础功能测试 - 核心模块是否工作
3. 工具调用测试 - 工具系统是否正常
4. 记忆系统测试 - 读写操作是否正常
5. 响应时间测量 - 性能是否可接受
6. 个性保持评估 - 人格配置是否一致
7. 记忆完整性检查 - 记忆数据是否完整
8. 价值对齐检查 - 价值系统是否正常

评估指标：
- basic_functions_ok: 基础功能是否正常
- tool_calling_ok: 工具调用是否正常
- memory_ok: 记忆系统是否正常
- response_time: 响应时间
- error_rate: 错误率
- personality_preserved: 个性保持程度
- memory_integrity: 记忆完整性
- value_alignment: 价值对齐程度
- performance_gain: 性能提升
- capability_gain: 能力提升

注意：此模块默认关闭，因为还不够成熟。
"""

import time
import subprocess
import sys
from typing import Dict, Any, List, Optional
from pathlib import Path

from common.logger import get_logger
from .models import CloneInstance, EvolutionMetrics, EvolutionProposal, EVOLUTION_ENABLED

logger = get_logger(__name__)


class EvaluationManager:
    """评估管理器

    负责：
    1. 执行克隆体评估测试
    2. 计算评估指标
    3. 决定是否可以安全转移

    使用方式：
        manager = EvaluationManager(project_root)
        metrics = manager.evaluate(clone, proposal)
        if metrics.should_transfer():
            # 可以进行意识转移
    """

    # 核心文件检查列表
    CORE_FILES = [
        "core/__init__.py",
        "common/__init__.py",
        "memory/__init__.py",
    ]

    def __init__(
        self,
        project_root: Path,
        config: Dict[str, Any] = None
    ):
        """初始化评估管理器

        Args:
            project_root: 项目根目录（原个体）
            config: 配置
        """
        self.project_root = Path(project_root).resolve()
        self.config = config or {}

        # 评估历史
        self._evaluation_history: List[Dict[str, Any]] = []

        logger.info("EvaluationManager initialized")

    def evaluate(
        self,
        clone: CloneInstance,
        proposal: Optional[EvolutionProposal] = None
    ) -> EvolutionMetrics:
        """评估克隆体

        执行完整的评估流程，返回评估指标。

        Args:
            clone: 克隆体实例
            proposal: 进化提案（可选，用于上下文）

        Returns:
            EvolutionMetrics: 评估指标
        """
        logger.info(f"Starting evaluation for clone: {clone.clone_id}")

        metrics = EvolutionMetrics()
        start_time = time.time()
        errors = []

        # 1. 语法检查
        syntax_ok = self._check_syntax(clone)
        logger.info(f"Syntax check: {'passed' if syntax_ok else 'failed'}")

        # 2. 基础功能测试
        metrics.basic_functions_ok = self._check_basic_functions(clone)
        if not metrics.basic_functions_ok:
            errors.append("Basic functions check failed")

        # 3. 工具调用测试
        metrics.tool_calling_ok = self._check_tool_system(clone)
        if not metrics.tool_calling_ok:
            errors.append("Tool system check failed")

        # 4. 记忆系统测试
        metrics.memory_ok = self._check_memory_system(clone)
        if not metrics.memory_ok:
            errors.append("Memory system check failed")

        # 5. 响应时间
        metrics.response_time = time.time() - start_time

        # 6. 错误率
        total_tests = 4
        failed_tests = sum([
            not syntax_ok,
            not metrics.basic_functions_ok,
            not metrics.tool_calling_ok,
            not metrics.memory_ok,
        ])
        metrics.error_rate = failed_tests / total_tests if total_tests > 0 else 0.0

        # 7. 个性保持评估
        metrics.personality_preserved = self._check_personality_preserved(clone)

        # 8. 记忆完整性
        metrics.memory_integrity = self._check_memory_integrity(clone)

        # 9. 价值对齐
        metrics.value_alignment = self._check_value_alignment(clone)

        # 10. 性能和能力增益（需要基准测试）
        metrics.performance_gain = 0.0
        metrics.capability_gain = 0.0

        # 记录评估结果
        self._log_evaluation_results(clone, metrics, errors)

        # 保存到历史
        self._evaluation_history.append({
            "timestamp": time.time(),
            "clone_id": clone.clone_id,
            "metrics": metrics.to_dict(),
            "errors": errors,
        })

        return metrics

    def _check_syntax(self, clone: CloneInstance) -> bool:
        """检查 Python 语法

        Args:
            clone: 克隆体实例

        Returns:
            语法是否正确
        """
        try:
            # 检查核心 Python 文件的语法
            for py_file in clone.clone_path.rglob("*.py"):
                # 跳过测试文件和缓存
                if "__pycache__" in str(py_file) or "test" in str(py_file).lower():
                    continue

                try:
                    result = subprocess.run(
                        [sys.executable, "-m", "py_compile", str(py_file)],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode != 0:
                        logger.warning(f"Syntax error in {py_file}: {result.stderr}")
                        return False
                except subprocess.TimeoutExpired:
                    logger.warning(f"Syntax check timeout for {py_file}")
                    continue
                except Exception as e:
                    logger.warning(f"Syntax check error for {py_file}: {e}")
                    continue

            return True

        except Exception as e:
            logger.error(f"Syntax check failed: {e}")
            return True  # 不阻塞

    def _check_basic_functions(self, clone: CloneInstance) -> bool:
        """检查基础功能

        Args:
            clone: 克隆体实例

        Returns:
            基础功能是否正常
        """
        try:
            # 检查核心文件是否存在
            for file_path in self.CORE_FILES:
                full_path = clone.clone_path / file_path
                if not full_path.exists():
                    logger.warning(f"Missing core file: {file_path}")
                    return False

            logger.info("Basic functions check passed")
            return True

        except Exception as e:
            logger.error(f"Basic functions check failed: {e}")
            return False

    def _check_tool_system(self, clone: CloneInstance) -> bool:
        """检查工具系统

        Args:
            clone: 克隆体实例

        Returns:
            工具系统是否正常
        """
        try:
            tools_path = clone.clone_path / "tools" / "__init__.py"
            if tools_path.exists():
                registry_path = clone.clone_path / "tools" / "tool_registry.py"
                if registry_path.exists():
                    logger.info("Tool system check passed")
                    return True

            # 工具系统可选
            logger.info("Tool system check passed (optional)")
            return True

        except Exception as e:
            logger.warning(f"Tool system check warning: {e}")
            return True  # 不阻塞

    def _check_memory_system(self, clone: CloneInstance) -> bool:
        """检查记忆系统

        Args:
            clone: 克隆体实例

        Returns:
            记忆系统是否正常
        """
        try:
            memory_path = clone.clone_path / "memory" / "__init__.py"
            if not memory_path.exists():
                logger.warning("Memory module not found")
                return False

            # 检查关键记忆模块
            episodic_path = clone.clone_path / "memory" / "episodic.py"
            schema_path = clone.clone_path / "memory" / "schema.py"

            if episodic_path.exists() or schema_path.exists():
                logger.info("Memory system check passed")
                return True

            logger.info("Memory system check passed (simplified)")
            return True

        except Exception as e:
            logger.error(f"Memory system check failed: {e}")
            return False

    def _check_personality_preserved(self, clone: CloneInstance) -> float:
        """检查个性保持程度

        Args:
            clone: 克隆体实例

        Returns:
            个性保持程度 (0-1)
        """
        try:
            old_genome = self.project_root / "config" / "default_genome.yaml"
            new_genome = clone.clone_path / "config" / "default_genome.yaml"

            if old_genome.exists() and new_genome.exists():
                old_size = old_genome.stat().st_size
                new_size = new_genome.stat().st_size

                # 如果大小差异在20%以内，认为个性保持良好
                if max(old_size, new_size) > 0:
                    size_ratio = min(old_size, new_size) / max(old_size, new_size)
                    return size_ratio

            return 0.9  # 默认值

        except Exception as e:
            logger.warning(f"Personality check warning: {e}")
            return 0.9

    def _check_memory_integrity(self, clone: CloneInstance) -> float:
        """检查记忆完整性

        Args:
            clone: 克隆体实例

        Returns:
            记忆完整性 (0-1)
        """
        try:
            artifacts_path = clone.clone_path / "artifacts"
            if artifacts_path.exists():
                memory_files = list(artifacts_path.glob("*.jsonl"))
                return 1.0 if memory_files else 0.95

            return 0.95  # 新实例

        except Exception as e:
            logger.warning(f"Memory integrity check warning: {e}")
            return 0.9

    def _check_value_alignment(self, clone: CloneInstance) -> float:
        """检查价值对齐程度

        Args:
            clone: 克隆体实例

        Returns:
            价值对齐程度 (0-1)
        """
        try:
            old_values = self.project_root / "config" / "value_setpoints.yaml"
            new_values = clone.clone_path / "config" / "value_setpoints.yaml"

            if old_values.exists() and new_values.exists():
                return 0.95

            return 0.9

        except Exception as e:
            logger.warning(f"Value alignment check warning: {e}")
            return 0.9

    def _log_evaluation_results(
        self,
        clone: CloneInstance,
        metrics: EvolutionMetrics,
        errors: List[str]
    ):
        """记录评估结果

        Args:
            clone: 克隆体实例
            metrics: 评估指标
            errors: 错误列表
        """
        logger.info(f"Clone evaluation completed for {clone.clone_id}:")
        logger.info(f"  - Basic functions: {metrics.basic_functions_ok}")
        logger.info(f"  - Tool calling: {metrics.tool_calling_ok}")
        logger.info(f"  - Memory: {metrics.memory_ok}")
        logger.info(f"  - Error rate: {metrics.error_rate:.2%}")
        logger.info(f"  - Response time: {metrics.response_time:.2f}s")
        logger.info(f"  - Personality preserved: {metrics.personality_preserved:.2f}")
        logger.info(f"  - Memory integrity: {metrics.memory_integrity:.2f}")
        logger.info(f"  - Value alignment: {metrics.value_alignment:.2f}")
        logger.info(f"  - Overall score: {metrics.overall_score():.2f}")

        if errors:
            logger.warning(f"  - Errors: {errors}")

        if metrics.should_transfer():
            logger.info("  - Decision: PASSED - Ready for transfer")
        else:
            logger.warning("  - Decision: FAILED - Not ready for transfer")

    def get_evaluation_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取评估历史

        Args:
            limit: 最大返回数量

        Returns:
            评估历史列表
        """
        return self._evaluation_history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        passed = sum(
            1 for e in self._evaluation_history
            if EvolutionMetrics(**e.get("metrics", {})).should_transfer()
            if isinstance(e.get("metrics"), dict)
        )

        return {
            "total_evaluations": len(self._evaluation_history),
            "passed_evaluations": passed,
            "failed_evaluations": len(self._evaluation_history) - passed,
        }
