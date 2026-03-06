"""GXBS Runner - Core Benchmark Execution System

Genesis X Benchmark Suite 运行器 - 论文附录 B
"""

import time
import json
from typing import Dict, Any, List, Optional, Callable, Type
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from abc import ABC, abstractmethod
import traceback

from common.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# 基准测试结果
# ============================================================================

@dataclass
class GXBSEntry:
    """单次测试条目"""
    name: str
    value: float
    unit: str
    threshold: Optional[float] = None
    passed: Optional[bool] = None

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "threshold": self.threshold,
            "passed": self.passed,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class GXBSResult:
    """基准测试结果"""
    suite_name: str
    benchmark_name: str

    # 指标
    entries: List[GXBSEntry] = field(default_factory=list)

    # 总体状态
    overall_passed: bool = True
    total_duration_ms: float = 0.0

    # 错误信息
    error: Optional[str] = None
    traceback: Optional[str] = None

    # 时间戳
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def add_entry(self, entry: GXBSEntry) -> None:
        """添加测试条目"""
        self.entries.append(entry)
        # 更新总体状态
        if entry.passed is False:
            self.overall_passed = False

    def to_dict(self) -> Dict[str, Any]:
        """序列化"""
        return {
            "suite_name": self.suite_name,
            "benchmark_name": self.benchmark_name,
            "entries": [e.to_dict() for e in self.entries],
            "overall_passed": self.overall_passed,
            "total_duration_ms": self.total_duration_ms,
            "error": self.error,
            "traceback": self.traceback,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    def get_summary(self) -> str:
        """获取摘要"""
        passed_count = sum(1 for e in self.entries if e.passed)
        total_count = len(self.entries)
        return f"{self.benchmark_name}: {passed_count}/{total_count} passed ({self.total_duration_ms:.2f}ms)"


# ============================================================================
# 基准测试基类
# ============================================================================

class GXBSBenchmark(ABC):
    """基准测试基类"""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.logger = get_logger(f"benchmark.{name}")

    @abstractmethod
    def run(self, **kwargs) -> GXBSResult:
        """运行基准测试

        Args:
            **kwargs: 测试参数

        Returns:
            测试结果
        """
        pass

    def _create_result(self) -> GXBSResult:
        """创建空结果"""
        return GXBSResult(
            suite_name="GXBS",
            benchmark_name=self.name,
            started_at=datetime.now(timezone.utc)
        )


# ============================================================================
# 基准测试套件
# ============================================================================

class GXBSSuite:
    """基准测试套件"""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.benchmarks: Dict[str, GXBSBenchmark] = {}

    def register(self, benchmark: GXBSBenchmark) -> None:
        """注册基准测试"""
        self.benchmarks[benchmark.name] = benchmark

    def run(self, benchmark_names: Optional[List[str]] = None) -> Dict[str, GXBSResult]:
        """运行套件中的测试

        Args:
            benchmark_names: 要运行的测试名称列表（None = 全部）

        Returns:
            测试结果字典
        """
        results = {}

        if benchmark_names is None:
            benchmark_names = list(self.benchmarks.keys())

        for name in benchmark_names:
            if name in self.benchmarks:
                try:
                    result = self.benchmarks[name].run()
                    results[name] = result
                except Exception as e:
                    self.logger.error(f"Benchmark {name} failed: {e}")
                    result = GXBSResult(
                        suite_name=self.name,
                        benchmark_name=name,
                        overall_passed=False,
                        error=str(e),
                        traceback=traceback.format_exc()
                    )
                    results[name] = result
            else:
                self.logger.warning(f"Benchmark {name} not found")

        return results


# ============================================================================
# GXBS 运行器
# ============================================================================

class GXBSRunner:
    """GXBS 主运行器

    论文附录 B 定义的基准测试套件:

    1. 记忆检索准确率 (Memory Retrieval Accuracy)
       - 指标: precision@k, recall@k, MRR
       - 阈值: precision@5 >= 0.8

    2. 联想激活速度 (Associative Activation Speed)
       - 指标: 平均检索延迟
       - 阈值: p95 < 100ms

    3. 情绪衰减保真度 (Emotion Decay Fidelity)
       - 指标: 衰减曲线误差
       - 阈值: MAE < 0.05

    4. 模型切换连续性 (Model Switching Continuity)
       - 指标: 状态迁移误差
       - 阈值: state_diff < 0.1

    5. 人格调制效果 (Personality Modulation Effectiveness)
       - 指标: 调制后差异度
       - 阈值: modulation_effect > 0.2
    """

    # 默认阈值配置
    DEFAULT_THRESHOLDS = {
        # Memory benchmarks
        "precision_at_5": 0.8,
        "recall_at_5": 0.7,
        "mrr": 0.85,
        "retrieval_p95_latency_ms": 100.0,

        # Emotion benchmarks
        "decay_mae": 0.05,
        "proust_reactivation_strength": 0.5,

        # Personality benchmarks
        "modulation_effect": 0.2,
        "consolidation_threshold_diff": 0.1,

        # Multi-model benchmarks
        "state_transition_error": 0.1,
        "switch_latency_ms": 200.0,
    }

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir) if output_dir else Path("./benchmarks/results")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.suites: Dict[str, GXBSSuite] = {}
        self.thresholds = self.DEFAULT_THRESHOLDS.copy()

    def register_suite(self, suite: GXBSSuite) -> None:
        """注册测试套件"""
        self.suites[suite.name] = suite

    def set_threshold(self, name: str, value: float) -> None:
        """设置阈值"""
        self.thresholds[name] = value

    def get_threshold(self, name: str, default: Optional[float] = None) -> Optional[float]:
        """获取阈值"""
        return self.thresholds.get(name, default)

    def run_all(self) -> Dict[str, Dict[str, GXBSResult]]:
        """运行所有套件

        Returns:
            {suite_name: {benchmark_name: result}}
        """
        all_results = {}

        for suite_name, suite in self.suites.items():
            self.logger.info(f"Running suite: {suite_name}")
            suite_results = suite.run()
            all_results[suite_name] = suite_results

        return all_results

    def run_suite(self, suite_name: str, benchmark_names: Optional[List[str]] = None) -> Dict[str, GXBSResult]:
        """运行指定套件

        Args:
            suite_name: 套件名称
            benchmark_names: 要运行的测试列表

        Returns:
            测试结果字典
        """
        if suite_name not in self.suites:
            self.logger.error(f"Suite {suite_name} not found")
            return {}

        return self.suites[suite_name].run(benchmark_names)

    def save_results(
        self,
        results: Dict[str, Dict[str, GXBSResult]],
        filename: Optional[str] = None
    ) -> Path:
        """保存结果到文件

        Args:
            results: 测试结果
            filename: 文件名（默认自动生成）

        Returns:
            保存的文件路径
        """
        if filename is None:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"gxbs_results_{timestamp}.json"

        output_path = self.output_dir / filename

        # 转换为可序列化格式
        serializable = {}
        for suite_name, suite_results in results.items():
            serializable[suite_name] = {
                bench_name: result.to_dict()
                for bench_name, result in suite_results.items()
            }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(serializable, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Results saved to {output_path}")
        return output_path

    def generate_report(
        self,
        results: Dict[str, Dict[str, GXBSResult]],
        output_format: str = "text"
    ) -> str:
        """生成测试报告

        Args:
            results: 测试结果
            output_format: 输出格式 (text, markdown, json)

        Returns:
            报告内容
        """
        if output_format == "json":
            return json.dumps({
                suite_name: {
                    bench_name: result.to_dict()
                    for bench_name, result in suite_results.items()
                }
                for suite_name, suite_results in results.items()
            }, indent=2)

        lines = []
        lines.append("=" * 60)
        lines.append("Genesis X Benchmark Suite (GXBS) Report")
        lines.append("=" * 60)
        lines.append("")

        total_passed = 0
        total_failed = 0

        for suite_name, suite_results in results.items():
            lines.append(f"Suite: {suite_name}")
            lines.append("-" * 40)

            for bench_name, result in suite_results.items():
                summary = result.get_summary()
                lines.append(f"  {summary}")

                if result.overall_passed:
                    total_passed += 1
                else:
                    total_failed += 1

                # 详细信息
                for entry in result.entries:
                    status = "✓" if entry.passed else "✗"
                    lines.append(f"    {status} {entry.name}: {entry.value:.4f} {entry.unit}")
                    if entry.threshold is not None:
                        lines.append(f"       (threshold: {entry.threshold:.4f})")

            lines.append("")

        # 总体统计
        lines.append("=" * 60)
        lines.append("Summary")
        lines.append("-" * 40)
        lines.append(f"  Total Passed: {total_passed}")
        lines.append(f"  Total Failed: {total_failed}")

        if total_passed + total_failed > 0:
            pass_rate = total_passed / (total_passed + total_failed) * 100
            lines.append(f"  Pass Rate: {pass_rate:.1f}%")

        lines.append("=" * 60)

        return "\n".join(lines)


# ============================================================================
# 工厂函数
# ============================================================================

def create_gxbs_runner(output_dir: Optional[str] = None) -> GXBSRunner:
    """创建 GXBS 运行器"""
    return GXBSRunner(output_dir=output_dir)
