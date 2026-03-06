"""
Dynamic Setpoint Learning System

论文暗示: 系统可以根据环境自适应调整价值设定点 (f*)
使系统能适应不同环境和长期经验。

核心思想:
1. 观察长期特征值分布
2. 根据RPE (奖励预测误差) 调整设定点
3. 保持设定点稳定性，避免过度波动

References:
- 论文 Section 3.5: Axiology Engine
- 论文 Section 3.7: Reward Prediction Error
- 代码大纲 axiology/dynamic_setpoints.py
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import numpy as np

from common.logger import get_logger

logger = get_logger(__name__)


class SetpointAdjustmentMode(str, Enum):
    """设定点调整模式."""
    # 经验驱动: 根据观察到的长期特征值分布调整
    EXPERIENCE_DRIVEN = "experience_driven"

    # RPE驱动: 根据奖励预测误差调整 (系统性偏差)
    RPE_DRIVEN = "rpe_driven"

    # 混合模式: 结合两者
    HYBRID = "hybrid"


@dataclass
class SetpointLearningConfig:
    """动态设定点学习配置."""
    # 学习率
    base_learning_rate: float = 0.01  # 基础学习率 α
    rpe_learning_rate: float = 0.005  # RPE驱动的学习率 (更保守)

    # 观察窗口
    experience_window_size: int = 100  # 经验窗口大小
    min_samples_for_learning: int = 20  # 最小样本数

    # 调整阈值
    rpe_bias_threshold: float = 0.1  # RPE系统性偏差阈值
    experience_variance_threshold: float = 0.05  # 经验方差阈值

    # 稳定性约束
    max_daily_drift: Dict[str, float] = field(default_factory=lambda: {
        "homeostasis": 0.05,
        "attachment": 0.10,
        "curiosity": 0.15,
        "competence": 0.08,
        "safety": 0.05,
    })

    # 调整模式
    adjustment_mode: SetpointAdjustmentMode = SetpointAdjustmentMode.HYBRID


@dataclass
class DimensionLearner:
    """单个维度的学习器."""
    dimension: str
    current_setpoint: float
    feature_history: List[float] = field(default_factory=list)
    rpe_history: List[float] = field(default_factory=list)

    # 统计信息
    mean_observed: float = 0.0
    std_observed: float = 0.0
    mean_rpe: float = 0.0

    # 调整历史
    adjustment_history: List[Tuple[float, float]] = field(default_factory=list)  # (tick, delta)

    def add_observation(self, feature: float, rpe: float):
        """添加观察值."""
        self.feature_history.append(feature)
        self.rpe_history.append(rpe)

        # 限制历史大小
        max_history = 200
        if len(self.feature_history) > max_history:
            self.feature_history = self.feature_history[-max_history:]
            self.rpe_history = self.rpe_history[-max_history:]

        # 更新统计
        if self.feature_history:
            self.mean_observed = np.mean(self.feature_history)
            self.std_observed = np.std(self.feature_history)
        if self.rpe_history:
            self.mean_rpe = np.mean(self.rpe_history)

    def should_adjust(self, config: SetpointLearningConfig) -> Tuple[bool, str]:
        """判断是否需要调整设定点.

        Returns:
            (should_adjust, reason)
        """
        if len(self.feature_history) < config.min_samples_for_learning:
            return False, "insufficient_samples"

        mode = config.adjustment_mode

        if mode == SetpointAdjustmentMode.EXPERIENCE_DRIVEN:
            return self._should_adjust_experience(config)
        elif mode == SetpointAdjustmentMode.RPE_DRIVEN:
            return self._should_adjust_rpe(config)
        else:  # HYBRID
            exp_should, exp_reason = self._should_adjust_experience(config)
            rpe_should, rpe_reason = self._should_adjust_rpe(config)

            if exp_should and rpe_should:
                return True, f"hybrid: {exp_reason} & {rpe_reason}"
            elif exp_should:
                return True, f"hybrid: {exp_reason}"
            elif rpe_should:
                return True, f"hybrid: {rpe_reason}"
            return False, "no_adjustment_needed"

    def _should_adjust_experience(self, config: SetpointLearningConfig) -> Tuple[bool, str]:
        """基于经验分布判断是否调整."""
        # 计算当前设定点与观察均值的差距
        gap = abs(self.current_setpoint - self.mean_observed)

        # 如果差距超过标准差的一半，可能需要调整
        if gap > max(0.1, self.std_observed * 0.5):
            direction = "up" if self.mean_observed > self.current_setpoint else "down"
            return True, f"experience_gap: {direction} (gap={gap:.3f})"

        return False, "experience_stable"

    def _should_adjust_rpe(self, config: SetpointLearningConfig) -> Tuple[bool, str]:
        """基于RPE判断是否调整."""
        # 如果平均RPE持续为正，说明设定点可能太低
        # 如果平均RPE持续为负，说明设定点可能太高
        if abs(self.mean_rpe) > config.rpe_bias_threshold:
            if self.mean_rpe > 0:
                return True, f"positive_rpe_bias: {self.mean_rpe:.3f} (setpoint too low)"
            else:
                return True, f"negative_rpe_bias: {self.mean_rpe:.3f} (setpoint too high)"

        return False, "rpe_balanced"

    def compute_adjustment(self, config: SetpointLearningConfig) -> float:
        """计算设定点调整量.

        Returns:
            调整量 delta (可为正或负)
        """
        mode = config.adjustment_mode
        delta = 0.0

        if mode in (SetpointAdjustmentMode.EXPERIENCE_DRIVEN, SetpointAdjustmentMode.HYBRID):
            # 经验驱动调整
            if len(self.feature_history) >= config.min_samples_for_learning:
                target = self.mean_observed
                exp_delta = (target - self.current_setpoint) * config.base_learning_rate
                delta += exp_delta * 0.5  # 混合模式下权重为0.5

        if mode in (SetpointAdjustmentMode.RPE_DRIVEN, SetpointAdjustmentMode.HYBRID):
            # RPE驱动调整
            if len(self.rpe_history) >= config.min_samples_for_learning:
                rpe_delta = -self.mean_rpe * config.rpe_learning_rate
                weight = 1.0 if mode == SetpointAdjustmentMode.RPE_DRIVEN else 0.5
                delta += rpe_delta * weight

        return delta


class DynamicSetpointSystem:
    """
    动态设定点学习系统.

    功能:
    1. 跟踪各维度的特征值和RPE历史
    2. 检测设定点偏差
    3. 计算并应用调整
    4. 保持设定点稳定性
    """

    # 默认设定点 (与 constants.py 保持一致)
    DEFAULT_SETPOINTS = {
        "homeostasis": 0.70,
        "attachment": 0.70,
        "curiosity": 0.60,
        "competence": 0.75,
        "safety": 0.80,
    }

    def __init__(self, config: Optional[SetpointLearningConfig] = None):
        """初始化动态设定点系统.

        Args:
            config: 学习配置
        """
        self.config = config or SetpointLearningConfig()

        # 当前设定点
        self.setpoints = self.DEFAULT_SETPOINTS.copy()

        # 各维度学习器
        self.learners: Dict[str, DimensionLearner] = {}

        for dim, value in self.setpoints.items():
            self.learners[dim] = DimensionLearner(
                dimension=dim,
                current_setpoint=value
            )

        # 每日累计调整量
        self.daily_drift: Dict[str, float] = {dim: 0.0 for dim in self.setpoints}

        # 系统统计
        self.total_adjustments: int = 0
        self.last_adjustment_tick: int = 0

    def get_setpoint(self, dimension: str) -> float:
        """获取当前设定点."""
        return self.setpoints.get(dimension, 0.5)

    def get_all_setpoints(self) -> Dict[str, float]:
        """获取所有设定点."""
        return self.setpoints.copy()

    def observe(
        self,
        tick: int,
        features: Dict[str, float],
        rpes: Dict[str, float]
    ):
        """观察当前状态的特征值和RPE.

        Args:
            tick: 当前时间步
            features: 各维度特征值 f(S_t)
            rpes: 各维度RPE δ_t
        """
        for dim in self.setpoints.keys():
            if dim in features or dim in rpes:
                feature = features.get(dim, 0.5)
                rpe = rpes.get(dim, 0.0)
                self.learners[dim].add_observation(feature, rpe)

    def compute_adjustments(self, tick: int) -> Dict[str, float]:
        """计算各维度的设定点调整量.

        Args:
            tick: 当前时间步

        Returns:
            各维度的调整量 delta
        """
        adjustments = {}

        for dim, learner in self.learners.items():
            should_adjust, reason = learner.should_adjust(self.config)

            if should_adjust:
                delta = learner.compute_adjustment(self.config)

                # 检查每日漂移限制
                max_drift = self.config.max_daily_drift.get(dim, 0.1)
                remaining = max_drift - abs(self.daily_drift.get(dim, 0.0))

                if remaining > 0:
                    # 限制调整量
                    delta = np.clip(delta, -remaining, remaining)

                    if abs(delta) > 1e-6:  # 忽略微小调整
                        adjustments[dim] = delta
                        logger.debug(
                            f"[{dim}] Adjusting setpoint: {learner.current_setpoint:.3f} "
                            f"+ {delta:+.4f} - Reason: {reason}"
                        )

        return adjustments

    def apply_adjustments(
        self,
        tick: int,
        adjustments: Dict[str, float],
        force: bool = False
    ) -> Dict[str, Tuple[float, float]]:
        """应用设定点调整.

        Args:
            tick: 当前时间步
            adjustments: 各维度调整量
            force: 是否强制应用（忽略限制）

        Returns:
            各维度 (旧设定点, 新设定点) 元组
        """
        results = {}

        for dim, delta in adjustments.items():
            old_value = self.setpoints[dim]

            # 检查每日漂移限制
            if not force:
                max_drift = self.config.max_daily_drift.get(dim, 0.1)
                current_drift = self.daily_drift.get(dim, 0.0)
                remaining = max_drift - current_drift

                # 限制调整量
                if abs(delta) > remaining:
                    delta = np.clip(delta, -remaining, remaining)

            new_value = old_value + delta

            # 限制在 [0, 1] 范围
            new_value = np.clip(new_value, 0.0, 1.0)

            # 计算实际变化量
            actual_delta = new_value - old_value

            self.setpoints[dim] = new_value
            self.learners[dim].current_setpoint = new_value

            # 记录调整（使用实际变化量）
            self.learners[dim].adjustment_history.append((tick, actual_delta))
            self.daily_drift[dim] = self.daily_drift.get(dim, 0.0) + abs(actual_delta)

            results[dim] = (old_value, new_value)
            self.total_adjustments += 1
            self.last_adjustment_tick = tick

        if results:
            logger.info(f"Applied {len(results)} setpoint adjustments at tick {tick}")

        return results

    def reset_daily_drift(self):
        """重置每日漂移累计.

        在每天开始时调用。
        """
        self.daily_drift = {dim: 0.0 for dim in self.setpoints}
        logger.debug("Daily setpoint drift reset")

    def get_stats(self) -> Dict[str, Any]:
        """获取系统统计信息."""
        stats = {
            "setpoints": self.setpoints.copy(),
            "daily_drift": self.daily_drift.copy(),
            "total_adjustments": self.total_adjustments,
            "last_adjustment_tick": self.last_adjustment_tick,
            "learners": {}
        }

        for dim, learner in self.learners.items():
            stats["learners"][dim] = {
                "current_setpoint": learner.current_setpoint,
                "sample_count": len(learner.feature_history),
                "mean_observed": learner.mean_observed,
                "std_observed": learner.std_observed,
                "mean_rpe": learner.mean_rpe,
                "adjustment_count": len(learner.adjustment_history),
            }

        return stats

    def export_state(self) -> Dict[str, Any]:
        """导出当前状态（用于持久化）."""
        return {
            "setpoints": self.setpoints.copy(),
            "daily_drift": self.daily_drift.copy(),
            "learners": {
                dim: {
                    "current_setpoint": learner.current_setpoint,
                    "feature_history": learner.feature_history[-50:],  # 保留最近50个
                    "rpe_history": learner.rpe_history[-50:],
                    "mean_observed": learner.mean_observed,
                    "std_observed": learner.std_observed,
                    "mean_rpe": learner.mean_rpe,
                }
                for dim, learner in self.learners.items()
            },
            "total_adjustments": self.total_adjustments,
            "last_adjustment_tick": self.last_adjustment_tick,
        }

    def import_state(self, state: Dict[str, Any]):
        """导入状态（用于恢复）."""
        self.setpoints = state.get("setpoints", self.DEFAULT_SETPOINTS.copy())
        self.daily_drift = state.get("daily_drift", {dim: 0.0 for dim in self.setpoints})
        self.total_adjustments = state.get("total_adjustments", 0)
        self.last_adjustment_tick = state.get("last_adjustment_tick", 0)

        learners_data = state.get("learners", {})
        for dim, data in learners_data.items():
            if dim in self.learners:
                learner = self.learners[dim]
                learner.current_setpoint = data.get("current_setpoint", self.setpoints[dim])
                learner.feature_history = data.get("feature_history", [])
                learner.rpe_history = data.get("rpe_history", [])
                learner.mean_observed = data.get("mean_observed", 0.0)
                learner.std_observed = data.get("std_observed", 0.0)
                learner.mean_rpe = data.get("mean_rpe", 0.0)


# 便利函数
def create_dynamic_setpoint_system(
    mode: str = "hybrid",
    learning_rate: float = 0.01
) -> DynamicSetpointSystem:
    """创建动态设定点系统.

    Args:
        mode: 调整模式 ("experience_driven", "rpe_driven", "hybrid")
        learning_rate: 基础学习率

    Returns:
        DynamicSetpointSystem 实例
    """
    try:
        adjustment_mode = SetpointAdjustmentMode(mode)
    except ValueError:
        adjustment_mode = SetpointAdjustmentMode.HYBRID

    config = SetpointLearningConfig(
        adjustment_mode=adjustment_mode,
        base_learning_rate=learning_rate
    )

    return DynamicSetpointSystem(config)


# 测试
if __name__ == "__main__":
    import matplotlib.pyplot as plt

    # 创建系统
    system = create_dynamic_setpoint_system(mode="hybrid", learning_rate=0.02)

    # 模拟运行
    np.random.seed(42)

    ticks = list(range(500))
    setpoint_history = {dim: [] for dim in system.setpoints}
    feature_history = {dim: [] for dim in system.setpoints}

    for tick in ticks:
        # 模拟特征值 (真实值在0.6附近波动)
        features = {
            "homeostasis": 0.55 + 0.1 * np.sin(tick / 50) + np.random.randn() * 0.05,
            "attachment": 0.65 + np.random.randn() * 0.08,
            "curiosity": 0.50 + 0.05 * np.cos(tick / 30) + np.random.randn() * 0.05,
            "competence": 0.70 + 0.1 * (tick / 500) + np.random.randn() * 0.05,  # 上升趋势
            "safety": 0.75 + np.random.randn() * 0.03,
        }

        # 计算RPE (当前设定点 - 特征值)
        rpes = {
            dim: system.get_setpoint(dim) - features[dim]
            for dim in system.setpoints
        }

        # 观察
        system.observe(tick, features, rpes)

        # 每10步计算调整
        if tick % 10 == 0:
            adjustments = system.compute_adjustments(tick)
            if adjustments:
                system.apply_adjustments(tick, adjustments)

        # 记录历史
        for dim in system.setpoints:
            setpoint_history[dim].append(system.get_setpoint(dim))
            feature_history[dim].append(features[dim])

    # 打印统计
    stats = system.get_stats()
    print("\n动态设定点学习系统统计:")
    print(f"总调整次数: {stats['total_adjustments']}")
    print(f"最后调整时间步: {stats['last_adjustment_tick']}")
    print("\n各维度设定点变化:")
    for dim in system.setpoints:
        learner_stats = stats['learners'][dim]
        print(f"  {dim}: {system.DEFAULT_SETPOINTS[dim]:.3f} -> {stats['setpoints'][dim]:.3f} "
              f"(观察均值: {learner_stats['mean_observed']:.3f})")

    # 绘图
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    axes = axes.flatten()

    for i, dim in enumerate(system.setpoints):
        ax = axes[i]
        ax.plot(ticks, feature_history[dim], alpha=0.3, label="Feature (observed)")
        ax.plot(ticks, setpoint_history[dim], linewidth=2, label="Setpoint (learned)")
        ax.axhline(system.DEFAULT_SETPOINTS[dim], linestyle='--', color='red',
                   alpha=0.5, label="Initial setpoint")
        ax.set_title(f"{dim.capitalize()}")
        ax.set_xlabel("Tick")
        ax.set_ylabel("Value")
        ax.legend()
        ax.set_ylim([0, 1])

    axes[5].axis('off')
    plt.tight_layout()
    plt.savefig("dynamic_setpoints_demo.png", dpi=100)
    print("\n图表保存到: dynamic_setpoints_demo.png")
