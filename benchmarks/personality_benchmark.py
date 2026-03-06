"""Personality Benchmarks - Personality Modulation Effectiveness

人格调制基准测试 - 论文附录 B.3

特性:
- 人格调制的巩固阈值差异
- 探索倾向的新颖性敏感度调制
- 情绪敏感度的情绪标记调制
"""

import random
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
import numpy as np

from .gxbs_runner import GXBSBenchmark, GXBSResult, GXBSEntry
from common.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# 人格调制巩固阈值基准
# ============================================================================

class PersonalityModulationBenchmark(GXBSBenchmark):
    """人格调制巩固阈值基准

    论文 3.4.4: θ_consolidation = θ_base × (1 + λ_ct × CT_t)

    指标:
    - CT_t 对巩固阈值的影响: 不同 CT_t 下阈值差异
    - 调制有效性: 调制后阈值与预期的符合度

    阈值:
    - modulation_effect >= 0.2
    - modulation_correlation >= 0.95
    """
    def __init__(self):
        super().__init__(
            name="personality_modulation",
            description="Personality modulation effectiveness benchmark"
        )

    def run(
        self,
        base_threshold: float = 0.5,
        lambda_ct: float = 0.7,
        ct_values: Optional[List[float]] = None
    ) -> GXBSResult:
        """运行人格调制测试

        Args:
            base_threshold: 基础巩固阈值
            lambda_ct: 保守倾向系数
            ct_values: 测试的 CT_t 值列表

        Returns:
            测试结果
        """
        result = self._create_result()
        start_time = time.time()

        try:
            if ct_values is None:
                ct_values = [0.0, 0.25, 0.5, 0.75, 1.0]

            # 计算不同 CT_t 下的巩固阈值
            thresholds = []
            for ct in ct_values:
                # 公式: θ_consolidation = θ_base × (1 + λ_ct × CT_t)
                threshold = base_threshold * (1 + lambda_ct * ct)
                threshold = min(1.0, threshold)
                thresholds.append(threshold)

            # 计算调制效果（最大差异）
            modulation_effect = max(thresholds) - min(thresholds)

            # 计算与理论预期的相关性
            expected = [base_threshold * (1 + lambda_ct * ct) for ct in ct_values]
            correlation = np.corrcoef(thresholds, expected)[0, 1] if len(thresholds) > 1 else 1.0

            # 添加结果条目
            result.add_entry(GXBSEntry(
                name="consolidation_modulation_effect",
                value=modulation_effect,
                unit="score",
                threshold=0.2,
                passed=modulation_effect >= 0.2
            ))

            result.add_entry(GXBSEntry(
                name="modulation_correlation",
                value=correlation,
                unit="score",
                threshold=0.95,
                passed=correlation >= 0.95
            ))

            # 添加各 CT_t 下的阈值作为元数据
            for ct, threshold in zip(ct_values, thresholds):
                result.add_entry(GXBSEntry(
                    name=f"threshold_ct_{ct:.2f}",
                    value=threshold,
                    unit="score"
                ))

        except Exception as e:
            result.error = str(e)
            result.overall_passed = False
            self.logger.error(f"Personality modulation benchmark failed: {e}")

        result.completed_at = datetime.now(timezone.utc)
        result.total_duration_ms = (time.time() - start_time) * 1000

        return result


# ============================================================================
# 探索倾向新颖性敏感度基准
# ============================================================================

class ExplorationNoveltyBenchmark(GXBSBenchmark):
    """探索倾向新颖性敏感度基准

    论文 3.4.4: sensitivity = base_sensitivity × (1 + λ_et × ET_t)

    指标:
    - ET_t 对新颖性感知的影响
    - 高 ET_t 个体对新颖性的敏感度差异

    阈值:
    - novelty_sensitivity_diff >= 0.3
    """
    def __init__(self):
        super().__init__(
            name="exploration_novelty_sensitivity",
            description="Exploration tendency novelty sensitivity benchmark"
        )

    def run(
        self,
        base_sensitivity: float = 0.5,
        lambda_et: float = 0.8,
        et_values: Optional[List[float]] = None
    ) -> GXBSResult:
        """运行探索倾向新颖性敏感度测试

        Args:
            base_sensitivity: 基础敏感度
            lambda_et: 探索倾向系数
            et_values: 测试的 ET_t 值列表

        Returns:
            测试结果
        """
        result = self._create_result()
        start_time = time.time()

        try:
            if et_values is None:
                et_values = [0.0, 0.25, 0.5, 0.75, 1.0]

            # 计算不同 ET_t 下的新颖性敏感度
            sensitivities = []
            for et in et_values:
                # 公式: sensitivity = base_sensitivity × (1 + λ_et × ET_t)
                sensitivity = base_sensitivity * (1 + lambda_et * et)
                sensitivity = min(1.0, sensitivity)
                sensitivities.append(sensitivity)

            # 计算高 ET_t 和低 ET_t 的差异
            high_et_sensitivity = sensitivities[-1]  # ET_t = 1.0
            low_et_sensitivity = sensitivities[0]   # ET_t = 0.0
            sensitivity_diff = high_et_sensitivity - low_et_sensitivity

            # 添加结果条目
            result.add_entry(GXBSEntry(
                name="novelty_sensitivity_diff",
                value=sensitivity_diff,
                unit="score",
                threshold=0.3,
                passed=sensitivity_diff >= 0.3
            ))

            result.add_entry(GXBSEntry(
                name="high_et_sensitivity",
                value=high_et_sensitivity,
                unit="score"
            ))

            result.add_entry(GXBSEntry(
                name="low_et_sensitivity",
                value=low_et_sensitivity,
                unit="score"
            ))

        except Exception as e:
            result.error = str(e)
            result.overall_passed = False
            self.logger.error(f"Exploration novelty benchmark failed: {e}")

        result.completed_at = datetime.now(timezone.utc)
        result.total_duration_ms = (time.time() - start_time) * 1000

        return result


# ============================================================================
# 情绪敏感度调制基准
# ============================================================================

class EmotionalSensitivityBenchmark(GXBSBenchmark):
    """情绪敏感度调制基准

    论文 3.4.4: tag_intensity = base_intensity × (1 + λ_es × ES_t)

    指标:
    - ES_t 对情绪标记强度的影响
    - 高 ES_t 个体对情绪的敏感度差异

    阈值:
    - emotional_tagging_diff >= 0.4
    """
    def __init__(self):
        super().__init__(
            name="emotional_sensitivity_modulation",
            description="Emotional sensitivity modulation benchmark"
        )

    def run(
        self,
        base_intensity: float = 0.5,
        lambda_es: float = 0.8,
        es_values: Optional[List[float]] = None
    ) -> GXBSResult:
        """运行情绪敏感度调制测试

        Args:
            base_intensity: 基础情绪强度
            lambda_es: 情绪敏感度系数
            es_values: 测试的 ES_t 值列表

        Returns:
            测试结果
        """
        result = self._create_result()
        start_time = time.time()

        try:
            if es_values is None:
                es_values = [0.0, 0.25, 0.5, 0.75, 1.0]

            # 计算不同 ES_t 下的情绪标记强度
            intensities = []
            for es in es_values:
                # 公式: tag_intensity = base_intensity × (1 + λ_es × ES_t)
                intensity = base_intensity * (1 + lambda_es * es)
                intensity = min(1.0, intensity)
                intensities.append(intensity)

            # 计算高 ES_t 和低 ES_t 的差异
            high_es_intensity = intensities[-1]  # ES_t = 1.0
            low_es_intensity = intensities[0]    # ES_t = 0.0
            intensity_diff = high_es_intensity - low_es_intensity

            # 添加结果条目
            result.add_entry(GXBSEntry(
                name="emotional_tagging_diff",
                value=intensity_diff,
                unit="score",
                threshold=0.4,
                passed=intensity_diff >= 0.4
            ))

            result.add_entry(GXBSEntry(
                name="high_es_intensity",
                value=high_es_intensity,
                unit="score"
            ))

            result.add_entry(GXBSEntry(
                name="low_es_intensity",
                value=low_es_intensity,
                unit="score"
            ))

        except Exception as e:
            result.error = str(e)
            result.overall_passed = False
            self.logger.error(f"Emotional sensitivity benchmark failed: {e}")

        result.completed_at = datetime.now(timezone.utc)
        result.total_duration_ms = (time.time() - start_time) * 1000

        return result


# ============================================================================
# 工厂函数
# ============================================================================

def create_personality_benchmark() -> List[GXBSBenchmark]:
    """创建所有人格调制基准测试"""
    return [
        PersonalityModulationBenchmark(),
        ExplorationNoveltyBenchmark(),
        EmotionalSensitivityBenchmark(),
    ]
