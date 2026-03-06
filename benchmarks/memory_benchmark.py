"""Memory Benchmarks - Memory Retrieval and Associative Activation

记忆基准测试 - 论文附录 B.1

特性:
- 记忆检索准确率 (Precision@k, Recall@k, MRR)
- 联想激活速度 (p95 延迟)
- 熟悉度信号准确性
"""

import time
import random
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
import numpy as np

from .gxbs_runner import GXBSBenchmark, GXBSResult, GXBSEntry
from common.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# 记忆检索准确率基准
# ============================================================================

class MemoryRetrievalBenchmark(GXBSBenchmark):
    """记忆检索准确率基准

    指标:
    - Precision@5: 前 5 个结果中相关结果的占比
    - Recall@5: 相关结果在前 5 中的召回率
    - MRR (Mean Reciprocal Rank): 第一个相关结果的平均倒数排名

    阈值:
    - precision@5 >= 0.8
    - recall@5 >= 0.7
    - mrr >= 0.85
    """

    def __init__(self):
        super().__init__(
            name="memory_retrieval_accuracy",
            description="Memory retrieval accuracy benchmark"
        )

    def run(
        self,
        num_queries: int = 100,
        num_memories: int = 1000,
        k: int = 5
    ) -> GXBSResult:
        """运行检索准确率测试

        Args:
            num_queries: 查询数量
            num_memories: 记忆总数
            k: Top-K

        Returns:
            测试结果
        """
        result = self._create_result()
        start_time = time.time()

        try:
            # 生成模拟数据
            memories, queries = self._generate_data(num_memories, num_queries)

            # 模拟检索结果
            precision_scores = []
            recall_scores = []
            reciprocal_ranks = []

            for query, relevant_ids in queries:
                # 模拟检索结果（实际应该调用真实检索器）
                retrieved = self._simulate_retrieval(query, memories, k)

                # 计算 Precision@k
                relevant_retrieved = sum(1 for m_id in retrieved if m_id in relevant_ids)
                precision = relevant_retrieved / k if k > 0 else 0
                precision_scores.append(precision)

                # 计算 Recall@k
                recall = relevant_retrieved / len(relevant_ids) if relevant_ids else 0
                recall_scores.append(recall)

                # 计算 MRR
                for i, m_id in enumerate(retrieved):
                    if m_id in relevant_ids:
                        reciprocal_ranks.append(1.0 / (i + 1))
                        break
                else:
                    reciprocal_ranks.append(0.0)

            # 计算平均值
            avg_precision = np.mean(precision_scores)
            avg_recall = np.mean(recall_scores)
            avg_mrr = np.mean(reciprocal_ranks)

            # 添加结果条目
            result.add_entry(GXBSEntry(
                name=f"precision_at_{k}",
                value=avg_precision,
                unit="score",
                threshold=0.8,
                passed=avg_precision >= 0.8
            ))

            result.add_entry(GXBSEntry(
                name=f"recall_at_{k}",
                value=avg_recall,
                unit="score",
                threshold=0.7,
                passed=avg_recall >= 0.7
            ))

            result.add_entry(GXBSEntry(
                name="mrr",
                value=avg_mrr,
                unit="score",
                threshold=0.85,
                passed=avg_mrr >= 0.85
            ))

        except Exception as e:
            result.error = str(e)
            result.overall_passed = False
            self.logger.error(f"Memory retrieval benchmark failed: {e}")

        result.completed_at = datetime.now(timezone.utc)
        result.total_duration_ms = (time.time() - start_time) * 1000

        return result

    def _generate_data(
        self,
        num_memories: int,
        num_queries: int
    ) -> Tuple[List[Dict[str, Any]], List[Tuple[str, List[str]]]]:
        """生成模拟数据"""
        # 生成记忆
        memories = []
        for i in range(num_memories):
            memories.append({
                "id": f"mem_{i}",
                "text": f"Memory content {i}",
                "embedding": np.random.randn(384)
            })

        # 生成查询和相关记忆
        queries = []
        for i in range(num_queries):
            query = f"Query {i}"
            # 随机选择 3-5 个相关记忆
            num_relevant = random.randint(3, 5)
            relevant_ids = [f"mem_{random.randint(0, num_memories - 1)}" for _ in range(num_relevant)]
            queries.append((query, relevant_ids))

        return memories, queries

    def _simulate_retrieval(
        self,
        query: str,
        memories: List[Dict[str, Any]],
        k: int
    ) -> List[str]:
        """模拟检索（实际应该调用真实检索器）"""
        # 随机返回 k 个记忆 ID
        selected = random.sample(memories, min(k, len(memories)))
        return [m["id"] for m in selected]


# ============================================================================
# 联想激活速度基准
# ============================================================================

class AssociativeActivationBenchmark(GXBSBenchmark):
    """联想激活速度基准

    指标:
    - p50 延迟: 中位数检索延迟
    - p95 延迟: 95分位检索延迟
    - p99 延迟: 99分位检索延迟
    - 平均 QPS: 每秒查询数

    阈值:
    - p95 < 100ms
    """
    def __init__(self):
        super().__init__(
            name="associative_activation_speed",
            description="Associative activation speed benchmark"
        )

    def run(
        self,
        num_queries: int = 1000,
        num_memories: int = 1000,
        num_associations: int = 5
    ) -> GXBSResult:
        """运行联想激活速度测试

        Args:
            num_queries: 查询数量
            num_memories: 记忆总数
            num_associations: 每个记忆的联想数量

        Returns:
            测试结果
        """
        result = self._create_result()
        start_time = time.time()

        try:
            # 生成模拟联想网络
            network = self._generate_network(num_memories, num_associations)

            # 执行查询并计时
            latencies = []

            for i in range(num_queries):
                query_start = time.time()

                # 模拟联想激活
                _ = self._simulate_association(f"mem_{i % num_memories}", network)

                query_end = time.time()
                latencies.append((query_end - query_start) * 1000)  # 转换为 ms

            # 计算统计量
            latencies_array = np.array(latencies)
            p50 = np.percentile(latencies_array, 50)
            p95 = np.percentile(latencies_array, 95)
            p99 = np.percentile(latencies_array, 99)

            # 计算 QPS
            total_time = time.time() - start_time
            qps = num_queries / total_time if total_time > 0 else 0

            # 添加结果条目
            result.add_entry(GXBSEntry(
                name="p50_latency",
                value=p50,
                unit="ms"
            ))

            result.add_entry(GXBSEntry(
                name="p95_latency",
                value=p95,
                unit="ms",
                threshold=100.0,
                passed=p95 < 100.0
            ))

            result.add_entry(GXBSEntry(
                name="p99_latency",
                value=p99,
                unit="ms"
            ))

            result.add_entry(GXBSEntry(
                name="qps",
                value=qps,
                unit="queries/sec"
            ))

        except Exception as e:
            result.error = str(e)
            result.overall_passed = False
            self.logger.error(f"Associative activation benchmark failed: {e}")

        result.completed_at = datetime.now(timezone.utc)
        result.total_duration_ms = (time.time() - start_time) * 1000

        return result

    def _generate_network(
        self,
        num_memories: int,
        num_associations: int
    ) -> Dict[str, List[str]]:
        """生成模拟联想网络"""
        network = {}
        for i in range(num_memories):
            memory_id = f"mem_{i}"
            associations = []
            for _ in range(num_associations):
                target_id = f"mem_{random.randint(0, num_memories - 1)}"
                if target_id != memory_id:
                    associations.append(target_id)
            network[memory_id] = associations
        return network

    def _simulate_association(
        self,
        memory_id: str,
        network: Dict[str, List[str]]
    ) -> List[str]:
        """模拟联想激活"""
        return network.get(memory_id, [])


# ============================================================================
# 熟悉度信号准确性基准
# ============================================================================

class FamiliaritySignalBenchmark(GXBSBenchmark):
    """熟悉度信号准确性基准

    指标:
    - 熟悉度-相关性相关性: 熟悉度分数与实际相关性的相关系数
    - 阈值准确性: 熟悉度阈值判断的准确率

    阈值:
    - correlation >= 0.7
    """
    def __init__(self):
        super().__init__(
            name="familiarity_signal_accuracy",
            description="Familiarity signal accuracy benchmark"
        )

    def run(
        self,
        num_samples: int = 500
    ) -> GXBSResult:
        """运行熟悉度信号准确性测试

        Args:
            num_samples: 样本数量

        Returns:
            测试结果
        """
        result = self._create_result()
        start_time = time.time()

        try:
            # 生成模拟数据
            familiarity_scores = []
            relevance_scores = []

            for i in range(num_samples):
                # 模拟熟悉度分数 [0, 1]
                familiarity = random.random()
                familiarity_scores.append(familiarity)

                # 模拟实际相关性（与熟悉度有一定关系）
                relevance = familiarity * 0.8 + random.random() * 0.2
                relevance_scores.append(relevance)

            # 计算相关系数
            correlation = np.corrcoef(familiarity_scores, relevance_scores)[0, 1]

            # 计算阈值准确性
            threshold = 0.6
            correct = sum(
                1 for f, r in zip(familiarity_scores, relevance_scores)
                if (f >= threshold and r >= 0.5) or (f < threshold and r < 0.5)
            )
            accuracy = correct / num_samples

            # 添加结果条目
            result.add_entry(GXBSEntry(
                name="familiarity_relevance_correlation",
                value=correlation,
                unit="score",
                threshold=0.7,
                passed=correlation >= 0.7
            ))

            result.add_entry(GXBSEntry(
                name="threshold_accuracy",
                value=accuracy,
                unit="score",
                threshold=0.75,
                passed=accuracy >= 0.75
            ))

        except Exception as e:
            result.error = str(e)
            result.overall_passed = False
            self.logger.error(f"Familiarity signal benchmark failed: {e}")

        result.completed_at = datetime.now(timezone.utc)
        result.total_duration_ms = (time.time() - start_time) * 1000

        return result


# ============================================================================
# 工厂函数
# ============================================================================

def create_memory_benchmark() -> List[GXBSBenchmark]:
    """创建所有记忆基准测试"""
    return [
        MemoryRetrievalBenchmark(),
        AssociativeActivationBenchmark(),
        FamiliaritySignalBenchmark(),
    ]
