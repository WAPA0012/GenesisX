"""Compensation Mechanisms for 5-Dimensional Value System (方案 B)

This module provides the compensation mechanisms for deleted dimensions (INTEGRITY, CONTRACT, EFFICIENCY, MEANING)
to ensure no functionality is lost when using the 5-dimensional value system from the paper.

论文 Section 3.5.1 说明:
- INTEGRITY: 删除，作为硬约束而非价值维度
- CONTRACT: 删除，重定位为影响权重的外部输入
- EFFICIENCY: 删除，并入 HOMEOSTASIS
- MEANING: 删除，并入 CURIOSITY

This module implements:
1. IntegrityConstraintChecker - 人格漂移硬约束检查
2. ContractSignalBooster - 任务契约权重提升
3. EfficiencyMonitor - 资源效率监控（并入 homeostasis）
4. MeaningTracker - 洞察质量追踪（并入 curiosity）
"""

from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass, field
from enum import Enum
import time


class ConstraintViolation(str, Enum):
    """Types of constraint violations."""
    PERSONALITY_DRIFT = "personality_drift"
    RESOURCE_PRESSURE = "resource_pressure"
    ERROR_THRESHOLD = "error_threshold"
    SAFETY_VIOLATION = "safety_violation"


# ============================================================================
# 1. INTEGRITY 约束检查器 (硬约束，非价值维度)
# ============================================================================

@dataclass
class IntegrityCheckResult:
    """Result of integrity constraint check.

    论文: INTEGRITY 作为硬约束，违反时触发强制修正而非权衡
    """
    passed: bool
    violation_type: Optional[ConstraintViolation] = None
    violation_severity: float = 0.0  # [0, 1]
    personality_drift: float = 0.0
    error_count: int = 0
    recommended_action: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "violation_type": self.violation_type.value if self.violation_type else None,
            "violation_severity": self.violation_severity,
            "personality_drift": self.personality_drift,
            "error_count": self.error_count,
            "recommended_action": self.recommended_action,
            "timestamp": self.timestamp,
        }


class IntegrityConstraintChecker:
    """人格一致性硬约束检查器.

    论文 Section 3.5.1: "删除 INTEGRITY：作为硬约束而非价值维度"

    这意味着人格漂移不应该通过"权衡"来处理，而应该：
    - 超过阈值时强制拒绝某些行为
    - 触发人格回滚机制
    - 增加后续动作的谨慎度
    """

    # 默认阈值
    DEFAULT_DRIFT_THRESHOLD = 0.20  # 人格漂移阈值
    DEFAULT_ERROR_THRESHOLD = 5     # 错误数量阈值
    DEFAULT_DRIFT_CRITICAL = 0.30   # 严重漂移阈值

    def __init__(
        self,
        drift_threshold: float = DEFAULT_DRIFT_THRESHOLD,
        drift_critical: float = DEFAULT_DRIFT_CRITICAL,
        error_threshold: int = DEFAULT_ERROR_THRESHOLD,
        enable_auto_rollback: bool = True,
    ):
        """Initialize integrity constraint checker.

        Args:
            drift_threshold: 人格漂移警告阈值
            drift_critical: 人格漂移严重阈值（触发强制行为）
            error_threshold: 错误数量阈值
            enable_auto_rollback: 是否启用人格回滚
        """
        self.drift_threshold = drift_threshold
        self.drift_critical = drift_critical
        self.error_threshold = error_threshold
        self.enable_auto_rollback = enable_auto_rollback

        # 追踪历史
        self._drift_history: List[float] = []
        self._violation_count: int = 0
        self._last_check_time: float = 0.0

    def check_integrity(
        self,
        state: Dict[str, Any],
        personality_params: Optional[Dict[str, float]] = None,
        reference_personality: Optional[Dict[str, float]] = None,
    ) -> IntegrityCheckResult:
        """检查人格一致性约束.

        论文公式: f^{integrity}(S_t) = 1 - drift(θ_t, θ_{t-1})

        Args:
            state: 当前状态，必须包含 personality_drift 或提供 personality_params
            personality_params: 当前人格参数（如果 state 中没有）
            reference_personality: 参考人格（初始人格或上次确认的人格）

        Returns:
            IntegrityCheckResult 检查结果
        """
        # 获取人格漂移值
        personality_drift = state.get("personality_drift", 0.0)

        if personality_drift == 0.0 and personality_params and reference_personality:
            # 计算漂移
            personality_drift = self._compute_personality_drift(
                personality_params, reference_personality
            )

        # 获取错误数量
        error_count = state.get("recent_errors", 0)

        # 判断违规
        violation_type = None
        violation_severity = 0.0
        recommended_action = ""

        # 检查人格漂移
        if personality_drift >= self.drift_critical:
            violation_type = ConstraintViolation.PERSONALITY_DRIFT
            violation_severity = min(1.0, personality_drift / self.drift_critical)
            recommended_action = "CRITICAL: 强制人格回滚，禁止高风险动作"
            self._violation_count += 1
        elif personality_drift >= self.drift_threshold:
            violation_type = ConstraintViolation.PERSONALITY_DRIFT
            violation_severity = min(1.0, personality_drift / self.drift_critical)
            recommended_action = "WARNING: 增加动作谨慎度，降低探索倾向"
            self._violation_count += 1

        # 检查错误阈值
        if error_count >= self.error_threshold:
            if not violation_type:
                violation_type = ConstraintViolation.ERROR_THRESHOLD
            violation_severity = max(violation_severity, error_count / (self.error_threshold * 2))
            recommended_action = f"ERROR_THRESHOLD: {error_count} errors, 进入保守模式"
            self._violation_count += 1

        # 检查资源压力（来自 EFFICIENCY 维度的功能）
        resource_pressure = state.get("resource_pressure", 0.0)
        if resource_pressure > 0.85:
            if not violation_type:
                violation_type = ConstraintViolation.RESOURCE_PRESSURE
            violation_severity = max(violation_severity, resource_pressure)
            recommended_action = "RESOURCE_PRESSURE: 资源紧张，限制高消耗动作"

        # 记录历史
        self._drift_history.append(personality_drift)
        if len(self._drift_history) > 100:
            self._drift_history.pop(0)
        self._last_check_time = time.time()

        return IntegrityCheckResult(
            passed=violation_type is None,
            violation_type=violation_type,
            violation_severity=violation_severity,
            personality_drift=personality_drift,
            error_count=error_count,
            recommended_action=recommended_action,
        )

    def _compute_personality_drift(
        self,
        current: Dict[str, float],
        reference: Dict[str, float]
    ) -> float:
        """计算人格漂移.

        使用 L2 距离: drift = ||θ_current - θ_reference||_2

        Args:
            current: 当前人格参数
            reference: 参考人格参数

        Returns:
            漂移值 [0, 1]
        """
        if not current or not reference:
            return 0.0

        # 获取所有共同的参数
        all_keys = set(current.keys()) | set(reference.keys())

        # 计算 L2 距离
        squared_diff = 0.0
        for key in all_keys:
            curr_val = current.get(key, 0.0)
            ref_val = reference.get(key, 0.0)
            squared_diff += (curr_val - ref_val) ** 2

        drift = (squared_diff ** 0.5) / (len(all_keys) ** 0.5)
        return min(1.0, drift)

    def get_drift_statistics(self) -> Dict[str, float]:
        """获取漂移统计信息.

        Returns:
            包含 current, max, mean, trend 的字典
        """
        if not self._drift_history:
            return {
                "current": 0.0,
                "max": 0.0,
                "mean": 0.0,
                "trend": 0.0,
                "count": 0,
            }

        return {
            "current": self._drift_history[-1],
            "max": max(self._drift_history),
            "mean": sum(self._drift_history) / len(self._drift_history),
            "trend": self._drift_history[-1] - self._drift_history[0] if len(self._drift_history) > 1 else 0.0,
            "count": len(self._drift_history),
        }

    def should_reject_action(self, check_result: IntegrityCheckResult) -> bool:
        """判断是否应该拒绝某个动作.

        Args:
            check_result: 完整性检查结果

        Returns:
            True if action should be rejected
        """
        if not check_result.passed:
            # 严重违规 → 拒绝
            if check_result.violation_severity > 0.7:
                return True
            # 人格漂移超过临界值 → 拒绝高风险动作
            if (check_result.violation_type == ConstraintViolation.PERSONALTY_DRIFT and
                check_result.personality_drift > self.drift_critical):
                return True
        return False

    def get_action_constraints(
        self,
        check_result: IntegrityCheckResult
    ) -> Dict[str, Any]:
        """获取动作约束.

        Args:
            check_result: 完整性检查结果

        Returns:
            约束字典，可能包含:
            - max_risk_level: 允许的最大风险等级
            - forbidden_actions: 禁止的动作列表
            - required_conservation: 是否需要保守模式
        """
        constraints = {
            "max_risk_level": 1.0,
            "forbidden_actions": [],
            "required_conservation": False,
        }

        if not check_result.passed:
            severity = check_result.violation_severity

            # 根据严重程度设置约束
            if severity > 0.7:
                constraints["max_risk_level"] = 0.0  # 只允许无风险动作
                constraints["forbidden_actions"] = ["code_exec", "file_write", "web_search"]
                constraints["required_conservation"] = True
            elif severity > 0.4:
                constraints["max_risk_level"] = 0.3  # 允许低风险动作
                constraints["forbidden_actions"] = ["code_exec"]
                constraints["required_conservation"] = True
            else:
                constraints["max_risk_level"] = 0.6
                constraints["required_conservation"] = False

        return constraints


# ============================================================================
# 2. CONTRACT 信号提升器 (外部任务信号影响权重)
# ============================================================================

@dataclass
class ContractSignal:
    """契约信号状态.

    论文 Section 3.5.1: "删除 CONTRACT：重定位为影响权重的外部输入"

    当有活跃用户任务时，临时提升 COMPETENCE 和 HOMEOSTASIS 的权重。
    """
    is_active: bool = False
    task_type: str = ""  # user_task, internal_goal, etc.
    progress: float = 0.0  # [0, 1]
    priority: int = 3  # 1-6, see PriorityLevel
    urgency: float = 0.0  # [0, 1]
    start_time: float = field(default_factory=time.time)
    estimated_remaining_ticks: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_active": self.is_active,
            "task_type": self.task_type,
            "progress": self.progress,
            "priority": self.priority,
            "urgency": self.urgency,
            "start_time": self.start_time,
            "estimated_remaining_ticks": self.estimated_remaining_ticks,
        }


class ContractSignalBooster:
    """契约信号提升器.

    将删除的 CONTRACT 维度功能转化为权重提升机制。

    论文公式 (Section 3.5.2 变更为 Section 3.6 外部输入):
    当存在活跃用户任务时:
    - w'_competence = γ_contract * w_competence
    - w'_homeostasis = γ_contract * w_homeostasis

    其中 γ_contract > 1 为任务增强系数
    """

    DEFAULT_BOOST_FACTOR = 1.5  # γ_contract 默认值
    DEFAULT_URGENT_BOOST = 2.0   # 紧急任务增强系数

    def __init__(
        self,
        boost_factor: float = DEFAULT_BOOST_FACTOR,
        urgent_boost: float = DEFAULT_URGENT_BOOST,
        enable_progress_decay: bool = True,
    ):
        """Initialize contract signal booster.

        Args:
            boost_factor: 任务增强系数 γ_contract
            urgent_boost: 紧急任务增强系数
            enable_progress_decay: 是否根据进度衰减增强
        """
        self.boost_factor = boost_factor
        self.urgent_boost = urgent_boost
        self.enable_progress_decay = enable_progress_decay

        # 当前契约状态
        self._current_contract: Optional[ContractSignal] = None

    def set_contract(
        self,
        task_type: str,
        priority: int = 3,
        urgency: float = 0.0,
        estimated_ticks: int = 0,
    ) -> ContractSignal:
        """设置新的契约信号.

        Args:
            task_type: 任务类型
            priority: 优先级 (1-6)
            urgency: 紧急程度 [0, 1]
            estimated_ticks: 预计剩余 ticks

        Returns:
            创建的 ContractSignal
        """
        self._current_contract = ContractSignal(
            is_active=True,
            task_type=task_type,
            progress=0.0,
            priority=priority,
            urgency=urgency,
            estimated_remaining_ticks=estimated_ticks,
        )
        return self._current_contract

    def update_progress(self, progress: float) -> None:
        """更新契约进度.

        Args:
            progress: 新的进度值 [0, 1]
        """
        if self._current_contract:
            self._current_contract.progress = max(0.0, min(1.0, progress))

            # 进度完成时清除契约
            if progress >= 1.0:
                self.clear_contract()

    def clear_contract(self) -> None:
        """清除当前契约."""
        self._current_contract = None

    def get_current_contract(self) -> Optional[ContractSignal]:
        """获取当前契约状态."""
        return self._current_contract

    def apply_contract_boost(
        self,
        weights: Dict[str, float],
        contract: Optional[ContractSignal] = None,
    ) -> Tuple[Dict[str, float], Dict[str, Any]]:
        """应用契约信号提升权重.

        论文 Section 3.6 外部输入说明:
        当存在活跃用户任务时，临时提升相关维度权重。

        Args:
            weights: 原始权重字典
            contract: 契约信号（如果为 None，使用内部状态）

        Returns:
            (boosted_weights, boost_info) 提升后的权重和提升信息
        """
        if contract is None:
            contract = self._current_contract

        boost_info = {
            "applied": False,
            "boost_factor": 1.0,
            "contract": contract.to_dict() if contract else None,
        }

        if not contract or not contract.is_active:
            return weights, boost_info

        # 计算实际增强系数
        actual_boost = self.boost_factor

        # 紧急任务使用更高增强
        if contract.priority >= 5 or contract.urgency > 0.7:
            actual_boost = self.urgent_boost

        # 根据进度衰减（接近完成时不再需要强驱动）
        if self.enable_progress_decay and contract.progress > 0.8:
            decay_factor = 1.0 - (contract.progress - 0.8) / 0.2  # 0.8→1.0 时 1.0→0.0
            actual_boost = 1.0 + (actual_boost - 1.0) * decay_factor

        boost_info["boost_factor"] = actual_boost

        # 应用提升（只提升 competence 和 homeostasis）
        boosted_weights = weights.copy()

        # 提升维度
        boost_dimensions = ["competence", "homeostasis"]

        # 根据任务类型调整提升目标
        if contract.task_type in ["exploration", "learning"]:
            boost_dimensions = ["curiosity", "competence"]
        elif contract.task_type in ["maintenance", "optimization"]:
            boost_dimensions = ["homeostasis", "efficiency"]
        elif contract.task_type in ["social", "interaction"]:
            boost_dimensions = ["attachment"]

        # 计算总提升量
        total_boost = 0.0
        for dim in boost_dimensions:
            if dim in boosted_weights:
                total_boost += (actual_boost - 1.0) * boosted_weights[dim]

        # 应用提升
        for dim in boost_dimensions:
            if dim in boosted_weights:
                boosted_weights[dim] *= actual_boost

        # 归一化（保持总和为1）
        total_weight = sum(boosted_weights.values())
        if total_weight > 0:
            for dim in boosted_weights:
                boosted_weights[dim] /= total_weight

        boost_info["applied"] = True
        boost_info["boosted_dimensions"] = boost_dimensions
        boost_info["total_boost"] = total_boost

        return boosted_weights, boost_info


# ============================================================================
# 3. EFFICIENCY 监控器 (并入 HOMEOSTASIS)
# ============================================================================

@dataclass
class EfficiencyMetrics:
    """资源效率指标.

    论文 Section 3.5.1: "删除 EFFICIENCY：并入 HOMEOSTASIS"

    效率监控的功能已经通过 resource_pressure 在 homeostasis 中体现。
    这个类提供详细的效率指标用于调试和分析。
    """
    tokens_used: int = 0
    tokens_budget: int = 10000
    io_operations: int = 0
    network_bytes: int = 0
    latency_ms: float = 0.0
    cost_estimate: float = 0.0

    @property
    def token_usage_ratio(self) -> float:
        """Token 使用比例."""
        return min(1.0, self.tokens_used / max(1, self.tokens_budget))

    @property
    def efficiency_score(self) -> float:
        """效率分数 [0, 1]，越高越高效."""
        # 综合考虑多种资源
        token_eff = 1.0 - self.token_usage_ratio
        io_eff = 1.0 - min(1.0, self.io_operations / 1000)
        net_eff = 1.0 - min(1.0, self.network_bytes / (1024 * 1024))
        latency_eff = 1.0 - min(1.0, self.latency_ms / 10000)

        return (token_eff * 0.5 + io_eff * 0.2 + net_eff * 0.15 + latency_eff * 0.15)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tokens_used": self.tokens_used,
            "tokens_budget": self.tokens_budget,
            "token_usage_ratio": self.token_usage_ratio,
            "io_operations": self.io_operations,
            "network_bytes": self.network_bytes,
            "latency_ms": self.latency_ms,
            "cost_estimate": self.cost_estimate,
            "efficiency_score": self.efficiency_score,
        }


class EfficiencyMonitor:
    """资源效率监控器.

    提供效率指标，但价值信号通过 homeostasis 的 resource_pressure 体现。
    """

    def __init__(self, tracking_window: int = 100):
        """Initialize efficiency monitor.

        Args:
            tracking_window: 追踪窗口大小（ticks）
        """
        self.tracking_window = tracking_window
        self._history: List[EfficiencyMetrics] = []

    def record_action(
        self,
        tokens_used: int = 0,
        io_operations: int = 0,
        network_bytes: int = 0,
        latency_ms: float = 0.0,
    ) -> EfficiencyMetrics:
        """记录动作的资源消耗.

        Args:
            tokens_used: 使用的 token 数
            io_operations: IO 操作次数
            network_bytes: 网络传输字节数
            latency_ms: 延迟毫秒数

        Returns:
            创建的 EfficiencyMetrics
        """
        metrics = EfficiencyMetrics(
            tokens_used=tokens_used,
            io_operations=io_operations,
            network_bytes=network_bytes,
            latency_ms=latency_ms,
        )

        self._history.append(metrics)
        if len(self._history) > self.tracking_window:
            self._history.pop(0)

        return metrics

    def get_average_efficiency(self, ticks: int = 10) -> float:
        """获取最近 N ticks 的平均效率分数.

        Args:
            ticks: 统计窗口大小

        Returns:
            平均效率分数 [0, 1]
        """
        recent = self._history[-ticks:] if ticks <= len(self._history) else self._history
        if not recent:
            return 1.0
        return sum(m.efficiency_score for m in recent) / len(recent)

    def get_resource_pressure(self) -> float:
        """获取资源压力（用于 homeostasis）.

        Returns:
            资源压力 [0, 1]，越高表示资源越紧张
        """
        if not self._history:
            return 0.0

        # 使用最近的效率指标
        recent = self._history[-10:] if len(self._history) >= 10 else self._history
        avg_efficiency = sum(m.efficiency_score for m in recent) / len(recent)

        # 压力 = 1 - 效率
        return 1.0 - avg_efficiency


# ============================================================================
# 4. MEANING 追踪器 (并入 CURIOSITY)
# ============================================================================

@dataclass
class InsightEvent:
    """洞察事件.

    论文 Section 3.5.1: "删除 MEANING：并入 CURIOSITY"

    意义感通过洞察质量和数量体现，并作为 curiosity 效用的增强。
    """
    insight_text: str
    quality: float  # [0, 1]
    source: str = "dream"  # dream, reflection, compression
    tags: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    associated_memories: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "insight_text": self.insight_text,
            "quality": self.quality,
            "source": self.source,
            "tags": self.tags,
            "timestamp": self.timestamp,
            "associated_memories": self.associated_memories,
        }


class MeaningTracker:
    """意义感追踪器.

    将删除的 MEANING 维度功能转化为洞察追踪，
    并为 curiosity 维度提供洞察质量增强。
    """

    def __init__(self, ema_alpha: float = 0.1):
        """Initialize meaning tracker.

        Args:
            ema_alpha: 洞察质量的 EMA 系数
        """
        self.ema_alpha = ema_alpha
        self._insights: List[InsightEvent] = []
        self._quality_ema: float = 0.5  # 初始值

    def add_insight(
        self,
        insight_text: str,
        quality: float,
        source: str = "dream",
        tags: Optional[List[str]] = None,
        associated_memories: Optional[List[str]] = None,
    ) -> InsightEvent:
        """添加新的洞察.

        Args:
            insight_text: 洞察文本
            quality: 质量 [0, 1]
            source: 来源
            tags: 标签
            associated_memories: 关联的记忆

        Returns:
            创建的 InsightEvent
        """
        insight = InsightEvent(
            insight_text=insight_text,
            quality=max(0.0, min(1.0, quality)),
            source=source,
            tags=tags or [],
            associated_memories=associated_memories or [],
        )

        self._insights.append(insight)

        # 更新质量 EMA
        self._quality_ema = (
            self.ema_alpha * quality +
            (1 - self.ema_alpha) * self._quality_ema
        )

        # 只保留最近的 100 条
        if len(self._insights) > 100:
            self._insights.pop(0)

        return insight

    def get_meaning_score(self) -> float:
        """获取意义感分数.

        这个分数可以用于增强 curiosity 维度。

        论文 Section 3.5.2 (3):
        f^{cur}(S_t) = 0.7 * Novelty_t + 0.3 * EMA_α(Q^{insight}_t)

        Returns:
            意义感分数 [0, 1]
        """
        if not self._insights:
            return 0.0

        # 基于 EMA 和洞察数量
        count_factor = min(1.0, len(self._insights) / 50.0)  # 50条洞察达到满分
        return self._quality_ema * 0.7 + count_factor * 0.3

    def get_insight_quality_ema(self) -> float:
        """获取洞察质量 EMA（用于 curiosity 特征提取）.

        Returns:
            质量 EMA [0, 1]
        """
        return self._quality_ema

    def get_recent_insights(self, count: int = 5) -> List[InsightEvent]:
        """获取最近的洞察.

        Args:
            count: 返回数量

        Returns:
            最近的洞察列表
        """
        return self._insights[-count:] if len(self._insights) >= count else self._insights

    def get_insight_summary(self) -> Dict[str, Any]:
        """获取洞察统计摘要.

        Returns:
            统计信息字典
        """
        if not self._insights:
            return {
                "total_count": 0,
                "quality_ema": self._quality_ema,
                "recent_quality": 0.0,
                "by_source": {},
            }

        # 按来源统计
        by_source = {}
        for insight in self._insights:
            by_source[insight.source] = by_source.get(insight.source, 0) + 1

        # 最近的平均质量
        recent = self._insights[-10:] if len(self._insights) >= 10 else self._insights
        recent_quality = sum(i.quality for i in recent) / len(recent) if recent else 0.0

        return {
            "total_count": len(self._insights),
            "quality_ema": self._quality_ema,
            "recent_quality": recent_quality,
            "by_source": by_source,
        }


# ============================================================================
# 5. 统一补偿管理器
# ============================================================================

class CompensationManager:
    """统一补偿管理器.

    整合所有删除维度的补偿机制，提供统一的接口。
    """

    def __init__(
        self,
        drift_threshold: float = 0.20,
        contract_boost: float = 1.5,
        tracking_window: int = 100,
        ema_alpha: float = 0.1,
    ):
        """Initialize compensation manager.

        Args:
            drift_threshold: 人格漂移阈值
            contract_boost: 契约提升系数
            tracking_window: 效率追踪窗口
            ema_alpha: 洞察质量 EMA 系数
        """
        # 四个补偿组件
        self.integrity_checker = IntegrityConstraintChecker(
            drift_threshold=drift_threshold
        )
        self.contract_booster = ContractSignalBooster(
            boost_factor=contract_boost
        )
        self.efficiency_monitor = EfficiencyMonitor(
            tracking_window=tracking_window
        )
        self.meaning_tracker = MeaningTracker(
            ema_alpha=ema_alpha
        )

    def process_tick(
        self,
        state: Dict[str, Any],
        weights: Dict[str, float],
        personality_params: Optional[Dict[str, float]] = None,
        reference_personality: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """处理单个 tick 的补偿逻辑.

        Args:
            state: 当前状态
            weights: 当前权重
            personality_params: 人格参数
            reference_personality: 参考人格

        Returns:
            处理结果，包含:
            - adjusted_weights: 调整后的权重
            - integrity_check: 完整性检查结果
            - action_constraints: 动作约束
            - efficiency_metrics: 效率指标
            - meaning_score: 意义感分数
        """
        result = {
            "adjusted_weights": weights.copy(),
            "integrity_check": None,
            "action_constraints": {},
            "efficiency_metrics": None,
            "meaning_score": 0.0,
        }

        # 1. 完整性检查
        integrity_result = self.integrity_checker.check_integrity(
            state, personality_params, reference_personality
        )
        result["integrity_check"] = integrity_result.to_dict()

        # 获取动作约束
        constraints = self.integrity_checker.get_action_constraints(integrity_result)
        result["action_constraints"] = constraints

        # 2. 契约信号提升
        adjusted_weights, boost_info = self.contract_booster.apply_contract_boost(
            weights
        )
        result["adjusted_weights"] = adjusted_weights
        result["contract_boost"] = boost_info

        # 3. 效率指标
        result["efficiency_metrics"] = self.efficiency_monitor.get_resource_pressure()

        # 4. 意义感分数
        result["meaning_score"] = self.meaning_tracker.get_meaning_score()

        return result

    def get_status_summary(self) -> Dict[str, Any]:
        """获取所有补偿机制的状态摘要.

        Returns:
            状态摘要字典
        """
        return {
            "integrity": {
                "drift_stats": self.integrity_checker.get_drift_statistics(),
                "violation_count": self.integrity_checker._violation_count,
            },
            "contract": (
                self.contract_booster.get_current_contract().to_dict()
                if self.contract_booster.get_current_contract()
                else None
            ),
            "efficiency": {
                "avg_efficiency": self.efficiency_monitor.get_average_efficiency(),
                "resource_pressure": self.efficiency_monitor.get_resource_pressure(),
            },
            "meaning": self.meaning_tracker.get_insight_summary(),
        }


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    # 完整性约束
    "IntegrityConstraintChecker",
    "IntegrityCheckResult",
    "ConstraintViolation",

    # 契约信号
    "ContractSignalBooster",
    "ContractSignal",

    # 效率监控
    "EfficiencyMonitor",
    "EfficiencyMetrics",

    # 意义追踪
    "MeaningTracker",
    "InsightEvent",

    # 统一管理
    "CompensationManager",
]
