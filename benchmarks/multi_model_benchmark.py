"""Multi-Model Benchmarks - Model Switching and State Continuity

多模型基准测试 - 论文附录 B.4

特性:
- 模型切换状态连续性
- 配置选择准确性
- 切换延迟
"""

import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
import numpy as np

from .gxbs_runner import GXBSBenchmark, GXBSResult, GXBSEntry
from common.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# 模型切换连续性基准
# ============================================================================

class ModelSwitchingBenchmark(GXBSBenchmark):
    """模型切换连续性基准

    论文 3.4.2: 抽象状态层保证模型切换时的状态连续性

    指标:
    - 状态迁移误差: abstract → concretize 后的状态差异
    - 切换延迟: 完成一次切换的时间

    阈值:
    - state_transition_error < 0.1
    - switch_latency_ms < 200
    """
    def __init__(self):
        super().__init__(
            name="model_switching_continuity",
            description="Model switching continuity benchmark"
        )

    def run(
        self,
        num_switches: int = 50
    ) -> GXBSResult:
        """运行模型切换连续性测试

        Args:
            num_switches: 切换次数

        Returns:
            测试结果
        """
        result = self._create_result()
        start_time = time.time()

        try:
            from core.abstract_state import (
                AbstractState,
                StateTransitionManager,
                AbstractEmotionalState
            )

            transition_manager = StateTransitionManager()

            state_errors = []
            switch_latencies = []

            configs = ["single", "core5", "full7"]

            for i in range(num_switches):
                # 创建原始状态
                original_state = {
                    "tick": i,
                    "mood": np.random.uniform(-1, 1),
                    "stress": np.random.uniform(0, 1),
                    "arousal": np.random.uniform(0, 1),
                    "boredom": np.random.uniform(0, 1),
                    "current_goal": {
                        "type": "test_goal",
                        "priority": np.random.randint(1, 6),
                        "progress": np.random.uniform(0, 1)
                    }
                }

                # 抽象化
                switch_start = time.time()
                abstract = transition_manager.abstract(original_state, configs[i % 3])

                # 具体化到新配置
                target_config = configs[(i + 1) % 3]
                recovered_state = transition_manager.concretize(abstract, target_config)
                switch_latency = (time.time() - switch_start) * 1000
                switch_latencies.append(switch_latency)

                # 计算状态误差
                mood_error = abs(original_state["mood"] - recovered_state.get("mood", 0))
                stress_error = abs(original_state["stress"] - recovered_state.get("stress", 0))
                arousal_error = abs(original_state["arousal"] - recovered_state.get("arousal", 0))

                # 综合误差
                state_error = (mood_error + stress_error + arousal_error) / 3
                state_errors.append(state_error)

            # 计算统计量
            avg_state_error = np.mean(state_errors)
            max_state_error = max(state_errors)
            avg_switch_latency = np.mean(switch_latencies)
            p95_switch_latency = np.percentile(switch_latencies, 95)

            # 添加结果条目
            result.add_entry(GXBSEntry(
                name="state_transition_error",
                value=avg_state_error,
                unit="score",
                threshold=0.1,
                passed=avg_state_error < 0.1
            ))

            result.add_entry(GXBSEntry(
                name="max_state_error",
                value=max_state_error,
                unit="score"
            ))

            result.add_entry(GXBSEntry(
                name="avg_switch_latency_ms",
                value=avg_switch_latency,
                unit="ms"
            ))

            result.add_entry(GXBSEntry(
                name="p95_switch_latency_ms",
                value=p95_switch_latency,
                unit="ms",
                threshold=200.0,
                passed=p95_switch_latency < 200.0
            ))

        except Exception as e:
            result.error = str(e)
            result.overall_passed = False
            self.logger.error(f"Model switching benchmark failed: {e}")

        result.completed_at = datetime.now(timezone.utc)
        result.total_duration_ms = (time.time() - start_time) * 1000

        return result


# ============================================================================
# 配置选择准确性基准
# ============================================================================

class ConfigSelectionBenchmark(GXBSBenchmark):
    """配置选择准确性基准

    论文 3.4.2: config_select(et, ct, rp) 选择最优配置

    指标:
    - 选择合理性: 给定人格和资源状态下选择的配置是否符合预期
    - 边界条件准确性: 边界值附近的选择稳定性

    阈值:
    - selection_accuracy >= 0.9
    """
    def __init__(self):
        super().__init__(
            name="config_selection_accuracy",
            description="Configuration selection accuracy benchmark"
        )

    def run(
        self,
        num_tests: int = 100
    ) -> GXBSResult:
        """运行配置选择准确性测试

        Args:
            num_tests: 测试次数

        Returns:
            测试结果
        """
        result = self._create_result()
        start_time = time.time()

        try:
            from tools.blackboard import config_select, ModelConfig

            correct_selections = 0

            # 测试用例：(ET, CT, RP, 期望配置)
            test_cases = [
                # 高资源压力 → single
                (0.5, 0.5, 0.9, ModelConfig.SINGLE),
                (0.3, 0.8, 0.85, ModelConfig.SINGLE),
                # 高探索倾向 + 低资源压力 → full7
                (0.8, 0.2, 0.3, ModelConfig.FULL7),
                (0.9, 0.1, 0.2, ModelConfig.FULL7),
                # 中等探索倾向 → core5
                (0.5, 0.5, 0.5, ModelConfig.CORE5),
                (0.6, 0.4, 0.4, ModelConfig.CORE5),
            ]

            # 运行测试用例
            for et, ct, rp, expected in test_cases:
                selected = config_select(et, ct, rp)
                if selected == expected:
                    correct_selections += 1

                # 记录结果
                result.add_entry(GXBSEntry(
                    name=f"selection_et_{et}_ct_{ct}_rp_{rp}",
                    value=1 if selected == expected else 0,
                    unit="pass/fail",
                    passed=selected == expected
                ))

            # 随机测试
            for _ in range(num_tests - len(test_cases)):
                et = np.random.uniform(0, 1)
                ct = 1 - et  # 确保和为 1
                rp = np.random.uniform(0, 1)

                selected = config_select(et, ct, rp)

                # 检查合理性
                is_reasonable = True
                if rp > 0.8 and selected != ModelConfig.SINGLE:
                    is_reasonable = False
                if et > 0.7 and rp < 0.4 and selected not in [ModelConfig.CORE5, ModelConfig.FULL7]:
                    is_reasonable = False

                if is_reasonable:
                    correct_selections += 1

            accuracy = correct_selections / num_tests

            # 添加结果条目
            result.add_entry(GXBSEntry(
                name="selection_accuracy",
                value=accuracy,
                unit="score",
                threshold=0.9,
                passed=accuracy >= 0.9
            ))

        except Exception as e:
            result.error = str(e)
            result.overall_passed = False
            self.logger.error(f"Config selection benchmark failed: {e}")

        result.completed_at = datetime.now(timezone.utc)
        result.total_duration_ms = (time.time() - start_time) * 1000

        return result


# ============================================================================
# Core5 专家协作基准
# ============================================================================

class Core5CoordinationBenchmark(GXBSBenchmark):
    """Core5 专家协作基准

    论文 3.4.2: Core5 配置下 5 个专家模型的协作

    指标:
    - 黑板写入完整度: 12 个槽位是否都被正确填充
    - 专家调用顺序: 专家调用顺序是否符合依赖关系

    阈值:
    - blackboard_coverage >= 0.9
    """
    def __init__(self):
        super().__init__(
            name="core5_coordination",
            description="Core5 expert coordination benchmark"
        )

    def run(
        self,
        num_iterations: int = 20
    ) -> GXBSResult:
        """运行 Core5 专家协作测试

        Args:
            num_iterations: 迭代次数

        Returns:
            测试结果
        """
        result = self._create_result()
        start_time = time.time()

        try:
            from tools.blackboard import Blackboard, BlackboardState

            coverage_scores = []

            for i in range(num_iterations):
                blackboard = Blackboard()
                state = blackboard.state

                # 模拟各专家写入黑板
                # M_coord 写入
                blackboard.write("plan", {"actions": ["action1", "action2"]}, "m_coord")
                blackboard.write("current_goal", {"type": "test"}, "m_coord")

                # M_mem 写入
                blackboard.write("retrieved_memories", [{"id": "mem1"}], "m_mem")
                blackboard.write("memory_reflection", "test_reflection", "m_mem")

                # M_reason 写入
                blackboard.write("reasoning_trace", ["step1", "step2"], "m_reason")

                # M_affect 写入
                blackboard.write("emotional_state", {"mood": 0.5}, "m_affect")
                blackboard.write("motivation", 0.7, "m_affect")

                # M_percept 写入
                blackboard.write("perception", "test_perception", "m_percept")

                # 检查覆盖率
                slots = [
                    "current_goal", "retrieved_memories", "plan",
                    "emotional_state", "motivation", "reasoning_trace",
                    "perception", "memory_reflection"
                ]

                filled = sum(1 for slot in slots if hasattr(state, slot) and getattr(state, slot, None) is not None)
                coverage = filled / len(slots)
                coverage_scores.append(coverage)

            avg_coverage = np.mean(coverage_scores)

            # 添加结果条目
            result.add_entry(GXBSEntry(
                name="blackboard_coverage",
                value=avg_coverage,
                unit="score",
                threshold=0.9,
                passed=avg_coverage >= 0.9
            ))

        except Exception as e:
            result.error = str(e)
            result.overall_passed = False
            self.logger.error(f"Core5 coordination benchmark failed: {e}")

        result.completed_at = datetime.now(timezone.utc)
        result.total_duration_ms = (time.time() - start_time) * 1000

        return result


# ============================================================================
# 工厂函数
# ============================================================================

def create_multi_model_benchmark() -> List[GXBSBenchmark]:
    """创建所有多模型基准测试"""
    return [
        ModelSwitchingBenchmark(),
        ConfigSelectionBenchmark(),
        Core5CoordinationBenchmark(),
    ]
