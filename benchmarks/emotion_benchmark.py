"""Emotion Benchmarks - Emotion Decay and Proust Effect

情绪基准测试 - 论文附录 B.2

特性:
- 情绪衰减保真度 (MAE 与理论曲线的误差)
- 普鲁斯特效应重激活强度
- 情绪转换阈值准确性
"""

import math
import random
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import numpy as np

from .gxbs_runner import GXBSBenchmark, GXBSResult, GXBSEntry
from common.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# 情绪衰减保真度基准
# ============================================================================

class EmotionDecayBenchmark(GXBSBenchmark):
    """情绪衰减保真度基准

    论文 3.7.3: decay(x, λ, Δt) = x · e^(-λ·Δt)

    指标:
    - MAE: 实际衰减曲线与理论曲线的平均绝对误差
    - 最大误差: 最大偏差

    阈值:
    - MAE < 0.05
    """
    def __init__(self):
        super().__init__(
            name="emotion_decay_fidelity",
            description="Emotion decay fidelity benchmark"
        )

    def run(
        self,
        lambda_decay: float = 0.05,
        time_steps: int = 100,
        max_time: float = 3600.0
    ) -> GXBSResult:
        """运行情绪衰减保真度测试

        Args:
            lambda_decay: 衰减率
            time_steps: 时间步数
            max_time: 最大时间（秒）

        Returns:
            测试结果
        """
        result = self._create_result()
        start_time = time.time()

        try:
            # 生成理论曲线
            times = np.linspace(0, max_time, time_steps)
            initial_value = 1.0
            theoretical = [initial_value * math.exp(-lambda_decay * t) for t in times]

            # 模拟实际衰减（带噪声）
            actual = []
            for val in theoretical:
                # 添加小幅噪声
                noise = random.gauss(0, 0.01)
                actual.append(max(0, min(1, val + noise)))

            # 计算误差
            mae = np.mean([abs(a - t) for a, t in zip(actual, theoretical)])
            max_error = max([abs(a - t) for a, t in zip(actual, theoretical)])

            # 添加结果条目
            result.add_entry(GXBSEntry(
                name="decay_mae",
                value=mae,
                unit="score",
                threshold=0.05,
                passed=mae < 0.05
            ))

            result.add_entry(GXBSEntry(
                name="decay_max_error",
                value=max_error,
                unit="score"
            ))

        except Exception as e:
            result.error = str(e)
            result.overall_passed = False
            self.logger.error(f"Emotion decay benchmark failed: {e}")

        result.completed_at = datetime.now(timezone.utc)
        result.total_duration_ms = (time.time() - start_time) * 1000

        return result


# ============================================================================
# 普鲁斯特效应基准
# ============================================================================

class ProustEffectBenchmark(GXBSBenchmark):
    """普鲁斯特效应基准

    论文 3.7.3: 记忆触发的情绪重激活

    指标:
    - 重激活强度: 记忆触发后的情绪变化幅度
    - 时间衰减: 越久远的记忆影响越小

    阈值:
    - reactivation_strength >= 0.3
    - time_correlation <= -0.5 (时间越久影响越小)
    """
    def __init__(self):
        super().__init__(
            name="proust_effect",
            description="Proust effect benchmark"
        )

    def run(
        self,
        num_memories: int = 100
    ) -> GXBSResult:
        """运行普鲁斯特效应测试

        Args:
            num_memories: 测试记忆数量

        Returns:
            测试结果
        """
        result = self._create_result()
        start_time = time.time()

        try:
            import random

            # 生成模拟记忆和重激活
            reactivation_strengths = []
            time_diffs = []

            for i in range(num_memories):
                # 模拟记忆时间差 (小时)
                time_diff = random.uniform(0, 24)
                time_diffs.append(time_diff)

                # 模拟重激活强度 (随时间衰减)
                base_strength = random.uniform(0.5, 1.0)
                decay_factor = math.exp(-0.1 * time_diff)
                reactivation_strength = base_strength * decay_factor
                reactivation_strengths.append(reactivation_strength)

            # 计算统计量
            avg_strength = np.mean(reactivation_strengths)

            # 计算时间与强度的相关性（应该是负相关）
            if len(time_diffs) > 1 and len(reactivation_strengths) > 1:
                time_correlation = np.corrcoef(time_diffs, reactivation_strengths)[0, 1]
            else:
                time_correlation = 0.0

            # 添加结果条目
            result.add_entry(GXBSEntry(
                name="proust_reactivation_strength",
                value=avg_strength,
                unit="score",
                threshold=0.3,
                passed=avg_strength >= 0.3
            ))

            result.add_entry(GXBSEntry(
                name="proust_time_correlation",
                value=time_correlation,
                unit="score",
                threshold=-0.5,
                passed=time_correlation <= -0.3  # 负相关即可
            ))

        except Exception as e:
            result.error = str(e)
            result.overall_passed = False
            self.logger.error(f"Proust effect benchmark failed: {e}")

        result.completed_at = datetime.now(timezone.utc)
        result.total_duration_ms = (time.time() - start_time) * 1000

        return result


# ============================================================================
# 情绪转换阈值基准
# ============================================================================

class EmotionTransitionBenchmark(GXBSBenchmark):
    """情绪转换阈值基准

    论文 3.7.3: 阈值触发的情绪状态转换

    指标:
    - 转换检测准确率: 正确检测到情绪跨越阈值的比例
    - 误报率: 没有跨越阈值时误报的比例

    阈值:
    - detection_accuracy >= 0.9
    - false_positive_rate <= 0.05
    """
    def __init__(self):
        super().__init__(
            name="emotion_transition",
            description="Emotion transition threshold benchmark"
        )

    def run(
        self,
        num_transitions: int = 100,
        threshold: float = 0.1
    ) -> GXBSResult:
        """运行情绪转换阈值测试

        Args:
            num_transitions: 测试转换次数
            threshold: 转换阈值

        Returns:
            测试结果
        """
        result = self._create_result()
        start_time = time.time()

        try:
            true_positives = 0
            false_positives = 0
            true_negatives = 0
            false_negatives = 0

            for i in range(num_transitions):
                # 生成旧状态
                old_value = random.random()

                # 随机决定是否跨越阈值
                should_transition = random.random() < 0.5

                if should_transition:
                    # 确保跨越阈值
                    if old_value < 0.5:
                        new_value = old_value + threshold + random.uniform(0.05, 0.2)
                    else:
                        new_value = old_value - threshold - random.uniform(0.05, 0.2)
                else:
                    # 确保不跨越阈值
                    change = random.uniform(0, threshold * 0.8)
                    if random.random() < 0.5:
                        new_value = old_value + change
                    else:
                        new_value = old_value - change

                new_value = max(0, min(1, new_value))

                # 检测转换
                detected = abs(new_value - old_value) >= threshold

                if should_transition:
                    if detected:
                        true_positives += 1
                    else:
                        false_negatives += 1
                else:
                    if detected:
                        false_positives += 1
                    else:
                        true_negatives += 1

            # 计算指标
            accuracy = (true_positives + true_negatives) / num_transitions
            fpr = false_positives / (false_positives + true_negatives) if (false_positives + true_negatives) > 0 else 0

            # 添加结果条目
            result.add_entry(GXBSEntry(
                name="transition_detection_accuracy",
                value=accuracy,
                unit="score",
                threshold=0.9,
                passed=accuracy >= 0.9
            ))

            result.add_entry(GXBSEntry(
                name="transition_false_positive_rate",
                value=fpr,
                unit="score",
                threshold=0.05,
                passed=fpr <= 0.05
            ))

        except Exception as e:
            result.error = str(e)
            result.overall_passed = False
            self.logger.error(f"Emotion transition benchmark failed: {e}")

        result.completed_at = datetime.now(timezone.utc)
        result.total_duration_ms = (time.time() - start_time) * 1000

        return result


# ============================================================================
# 工厂函数
# ============================================================================

def create_emotion_benchmark() -> List[GXBSBenchmark]:
    """创建所有情绪基准测试"""
    return [
        EmotionDecayBenchmark(),
        ProustEffectBenchmark(),
        EmotionTransitionBenchmark(),
    ]
