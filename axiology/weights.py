"""Dynamic weight computation via softmax over gaps with personality biases.

Implements paper Section 3.6: 动态权重：驱动缺口 → 权重（再叠加人格偏置）

Enhanced: Load default parameters from configuration files (value_setpoints.yaml)
instead of hardcoding weight_bias and idle_bias values.
"""
from typing import Dict, Any, Optional, Set
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from common.models import ValueDimension


# Import configuration loader
try:
    from .axiology_config import get_axiology_config, DEFAULT_IDLE_BIAS, DEFAULT_IDLE_EPSILON, DEFAULT_TAU
    _CONFIG_AVAILABLE = True
except ImportError:
    _CONFIG_AVAILABLE = False
    DEFAULT_IDLE_BIAS = {
        ValueDimension.HOMEOSTASIS: 0.10,
        ValueDimension.ATTACHMENT: 0.15,
        ValueDimension.CURIOSITY: 0.40,
        ValueDimension.COMPETENCE: 0.20,
        ValueDimension.SAFETY: 0.15,
    }
    DEFAULT_IDLE_EPSILON = 0.02
    DEFAULT_TAU = 4.0


@dataclass
class PriorityOverrideConfig:
    """Configuration for priority override and hysteresis.

    Paper Section 3.6.4: 稳定性：关键驱动的优先级覆盖与滞回

    Enhanced: Supports soft override that preserves learned preferences.
    新增：滞回超时机制防止永久覆盖
    """
    # Critical dimensions that can override
    critical_dimensions: Set[str] = None

    # Thresholds
    high_threshold: float = 0.8  # θ_hi: trigger override
    low_threshold: float = 0.4   # θ_lo: release override

    # Minimum weights when overridden
    min_weights: Dict[str, float] = None  # α_i

    # Soft override: blend learned weights with override (0=hard, 1=soft)
    # 论文Section 3.6.4: λ_soft 默认值为 0.3
    soft_override_factor: float = 0.3

    # Whether to persist override state
    persist_state: bool = True

    # 新增：滞回超时机制（论文P1-6扩展）
    # 最长覆盖持续时间（秒），超时后自动释放
    max_override_duration: float = 3600.0  # 1 hour default

    # 滞回参数验证范围
    def __post_init__(self):
        if self.critical_dimensions is None:
            # 论文 Section 3.6.4: 关键维度集合
            # 修复: 使用5维价值系统的关键维度
            self.critical_dimensions = {"homeostasis", "safety"}

        if self.min_weights is None:
            self.min_weights = {
                "homeostasis": 0.7,
                "safety": 0.6
            }

        # 验证软覆盖因子范围 [0, 1]
        self.soft_override_factor = max(0.0, min(1.0, self.soft_override_factor))

        # 验证阈值合理性
        if self.high_threshold <= self.low_threshold:
            raise ValueError(f"high_threshold ({self.high_threshold}) must be > low_threshold ({self.low_threshold})")

        # 验证超时时间
        self.max_override_duration = max(60.0, self.max_override_duration)


# Paper Section 3.6.3: Idle state bias vector b_idle
# When all gaps < epsilon, shift to exploration/meaning-seeking behavior
# 论文 Section 3.5.1: 5维价值系统的空闲偏置
DEFAULT_IDLE_BIAS = {
    ValueDimension.HOMEOSTASIS: 0.10,
    ValueDimension.ATTACHMENT: 0.15,
    ValueDimension.CURIOSITY: 0.40,
    ValueDimension.COMPETENCE: 0.20,
    ValueDimension.SAFETY: 0.15,
}

# Idle detection threshold (epsilon_idle)
DEFAULT_IDLE_EPSILON = 0.02


def compute_weights(
    gaps: Dict[ValueDimension, float],
    biases: Dict[ValueDimension, float],
    temperature: float = 4.0,  # 论文Appendix A.5默认值
    idle_bias: Dict[ValueDimension, float] = None,
    idle_epsilon: float = DEFAULT_IDLE_EPSILON,
) -> Dict[ValueDimension, float]:
    """Compute dynamic weights: w = softmax(gap * bias, tau).

    Paper formula (3.6.2, 3.6.3):
    d̃_i = d_i * g_i(θ)
    w_i = exp(τ * d̃_i) / Σ_j exp(τ * d̃_j)

    Paper Section 3.6.3: When all gaps < epsilon_idle, use idle bias vector
    to promote curiosity and meaning-seeking in satisfied state.

    Args:
        gaps: Drive gaps d_i
        biases: Personality biases g_i(θ)
        temperature: Softmax temperature τ
        idle_bias: Idle state bias vector b_idle (uses default if None)
        idle_epsilon: Threshold below which all gaps are considered "satisfied"

    Returns:
        Normalized weights (sum = 1.0)
    """
    # Apply personality biases: d̃_i = d_i * g_i(θ)
    biased_gaps = {}
    for dim in ValueDimension:
        gap = gaps.get(dim, 0.0)
        bias = biases.get(dim, 1.0)
        biased_gaps[dim] = gap * bias

    # Paper Section 3.6.3: Check idle state (all gaps below epsilon)
    max_biased_gap = max(biased_gaps.values()) if biased_gaps else 0.0
    if max_biased_gap < idle_epsilon:
        # All needs satisfied - use idle bias vector for exploration/meaning
        b_idle = idle_bias or DEFAULT_IDLE_BIAS
        # Apply softmax to idle bias
        max_b = max(b_idle.values()) if b_idle else 0.0
        exp_idle = {}
        for dim in ValueDimension:
            score = temperature * (b_idle.get(dim, 0.025) - max_b)
            score = max(-50.0, min(50.0, score))
            exp_idle[dim] = math.exp(score)
        total_idle = sum(exp_idle.values())
        if total_idle > 0:
            return {dim: v / total_idle for dim, v in exp_idle.items()}
        return {dim: 1.0 / len(ValueDimension) for dim in ValueDimension}

    # Softmax with temperature: w_i = exp(τ * d̃_i) / Σ exp(τ * d̃_j)
    # 论文公式3.6.3: 温度τ是乘数，不是除数
    # 使用 log-sum-exp 技巧避免数值溢出
    max_score = max(biased_gaps.values()) if biased_gaps else 0.0

    exp_scores = {}
    for dim, biased_gap in biased_gaps.items():
        # 数值稳定版本：exp(τ*(d̃_i - max)) = exp(τ*d̃_i) / exp(τ*max)
        # 这保持了softmax的比例关系不变
        adjusted_score = temperature * (biased_gap - max_score)
        # 限制范围避免溢出到无穷大
        adjusted_score = max(-50.0, min(50.0, adjusted_score))
        exp_scores[dim] = math.exp(adjusted_score)

    total = sum(exp_scores.values())
    if total == 0:
        # Uniform weights if all gaps are zero
        return {dim: 1.0 / len(ValueDimension) for dim in ValueDimension}

    # Normalize
    weights = {dim: exp_val / total for dim, exp_val in exp_scores.items()}

    return weights


class WeightUpdater:
    """Updater for dynamic value weights with personality biases and priority override.

    Implements:
    - Paper 3.6.2: Personality biases g_i(θ)
    - Paper 3.6.3: Softmax normalization
    - Paper 3.6.4: Priority override and hysteresis
    """

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize weight updater.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        # 论文Appendix A.5: τ默认值为4.0
        self.temperature = self.config.get("temperature", 4.0)
        self.inertia = self.config.get("inertia", 0.3)
        # 论文 Section 3.5.1: 5维核心价值向量
        self.dimensions = self.config.get("dimensions", [
            "homeostasis", "attachment", "curiosity", "competence", "safety"
        ])

        # Priority override configuration
        self.priority_config = PriorityOverrideConfig()

        # Track which dimensions are currently in override
        self._override_active: Set[str] = set()

        # Track override timestamps for timeout mechanism (论文P1-6)
        self._override_trigger_times: Dict[str, float] = {}

        # Track gaps at trigger time
        self._gaps_at_trigger: Dict[str, float] = {}

    def update_weights(
        self,
        current_weights: Dict[str, float],
        gaps: Dict[str, float],
        biases: Optional[Dict[str, float]] = None,
        priority_dim: Optional[str] = None,
        # 新增: 契约信号支持 (方案 B 补偿机制)
        contract_signal: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, float]:
        """Update weights based on gaps with personality biases.

        Paper formula:
        1. Apply personality bias: d̃_i = d_i * g_i(θ)
        2. Compute target weights: w_i = softmax(τ * d̃_i)
        3. Apply inertia: w_new = w_old * λ + w_target * (1-λ)
        4. Check priority override (Section 3.6.4)
        5. Apply contract signal boost (方案 B: CONTRACT 维度补偿)

        Enhanced: Soft override preserves learned biases during emergencies.
        修复：支持ValueDimension枚举键输入 (兼容字符串键)

        Args:
            current_weights: Current weight values (枚举或字符串键)
            gaps: Current gap values d_i (枚举或字符串键)
            biases: Personality biases g_i(θ) (learned preferences)
            priority_dim: Optional manual priority dimension override
            contract_signal: Optional contract signal for task-driven weight boost
                             {"is_active": bool, "priority": int, "urgency": float}

        Returns:
            Updated weights (sum = 1.0) 使用字符串键以保证兼容性
        """
        if biases is None:
            biases = {dim: 1.0 for dim in self.dimensions}

        # 标准化输入：将所有键转换为字符串
        def normalize_to_str(input_dict: Dict) -> Dict[str, float]:
            result = {}
            for k, v in input_dict.items():
                key = k.value if hasattr(k, 'value') else str(k)
                result[key] = float(v) if v is not None else 0.0
            return result

        current_weights_str = normalize_to_str(current_weights)
        gaps_str = normalize_to_str(gaps)
        biases_str = normalize_to_str(biases)

        # Step 1: Apply personality biases d̃_i = d_i * g_i(θ)
        biased_gaps = {}
        for dim in self.dimensions:
            gap = gaps_str.get(dim, 0.0)
            bias = biases_str.get(dim, 1.0)
            biased_gaps[dim] = gap * bias

        # Step 2: Compute target weights from biased gaps
        # 使用 log-sum-exp 技巧避免数值溢出
        max_score = max(biased_gaps.values()) if biased_gaps else 0.0

        exp_scores = {}
        for dim in self.dimensions:
            score = biased_gaps[dim]
            # Manual priority boost if specified
            if dim == priority_dim:
                score *= 10.0
            # 论文公式3.6.3: w_i = exp(τ * d̃_i)
            # 减去最大值避免溢出
            adjusted_score = self.temperature * (score - max_score)
            # 限制范围避免溢出到无穷大
            adjusted_score = max(-50.0, min(50.0, adjusted_score))
            exp_scores[dim] = math.exp(adjusted_score)

        total = sum(exp_scores.values())
        if total == 0:
            target_weights = {dim: 1.0 / len(self.dimensions) for dim in self.dimensions}
        else:
            target_weights = {dim: exp_val / total for dim, exp_val in exp_scores.items()}

        # Step 3: Check priority override (Paper 3.6.4)
        # Enhanced: soft override blends learned preferences with safety constraints
        override_weights = self._check_priority_override(gaps_str, target_weights, biases_str)

        if override_weights:
            # Priority override active - use (possibly blended) weights
            return override_weights

        # Step 4: Apply inertia (gradual change)
        new_weights = {}
        for dim in self.dimensions:
            current = current_weights_str.get(dim, 1.0 / len(self.dimensions))
            target = target_weights[dim]
            new_weights[dim] = current * self.inertia + target * (1 - self.inertia)

        # Step 5: Clamp non-negative THEN normalize to ensure sum = 1
        # Clamp first so normalization produces valid distribution
        new_weights = {dim: max(0.0, w) for dim, w in new_weights.items()}
        weight_sum = sum(new_weights.values())
        if weight_sum > 0 and abs(weight_sum - 1.0) > 1e-10:
            new_weights = {dim: w / weight_sum for dim, w in new_weights.items()}

        # Step 6: Apply contract signal boost (方案 B: CONTRACT 维度补偿)
        # 论文 Section 3.5.1: "删除 CONTRACT：重定位为影响权重的外部输入"
        if contract_signal and contract_signal.get("is_active", False):
            new_weights = self._apply_contract_boost(new_weights, contract_signal)

        return new_weights

    def _check_priority_override(
        self,
        gaps: Dict[str, float],
        learned_weights: Optional[Dict[str, float]] = None,
        biases: Optional[Dict[str, float]] = None
    ) -> Optional[Dict[str, float]]:
        """Check if priority override should be triggered.

        Paper Section 3.6.4:
        - When any critical dimension exceeds θ_hi, force minimum weight α_i
        - Keep override active until gap drops below θ_lo (hysteresis)
        - Redistribute remaining weight among other dimensions

        Enhanced: Soft override blends learned preferences with safety constraints
        to preserve value learning during emergencies.

        新增：滞回超时机制 (论文P1-6) - 防止覆盖状态永久存在

        Args:
            gaps: Current gaps
            learned_weights: Weights computed from learned biases
            biases: Personality biases for soft blending

        Returns:
            Override weights if triggered, None otherwise
        """
        import time
        cfg = self.priority_config
        current_time = time.time()

        # Check for new overrides
        for dim in cfg.critical_dimensions:
            gap = gaps.get(dim, 0.0)
            if gap >= cfg.high_threshold and dim not in self._override_active:
                self._override_active.add(dim)
                self._override_trigger_times[dim] = current_time
                self._gaps_at_trigger[dim] = gap

        # Check for override release (hysteresis + timeout)
        to_release = set()
        for dim in self._override_active:
            gap = gaps.get(dim, 0.0)

            # Check hysteresis condition
            hysteresis_release = gap < cfg.low_threshold

            # Check timeout condition (论文P1-6)
            trigger_time = self._override_trigger_times.get(dim, current_time)
            timeout_release = (current_time - trigger_time) >= cfg.max_override_duration

            if hysteresis_release or timeout_release:
                to_release.add(dim)
                # Clean up tracking data
                self._override_trigger_times.pop(dim, None)
                self._gaps_at_trigger.pop(dim, None)

        self._override_active -= to_release

        # If no override active, return None
        if not self._override_active:
            return None

        # Construct override weights with soft blending
        weights = {}
        reserved_weight = 0.0

        # Assign soft-blended weights to critical dimensions
        # Paper formula: w^(i)_override = α_i + λ_soft * max(0, w^(i)_learned - α_i)
        # This guarantees w_override >= α_i (safety floor is never breached)
        # 修复: 当 soft_override_factor = 0 时，仍然确保不低于 min_weight
        for dim in self.dimensions:
            if dim in self._override_active:
                min_weight = cfg.min_weights.get(dim, 0.7)
                learned_weight = learned_weights.get(dim, min_weight) if learned_weights else min_weight

                # 修复: 无论 soft_override_factor 是否为 0，都确保权重不低于 min_weight
                # 当 soft_override_factor = 0 时，权重 = min_weight（硬覆盖）
                # 当 soft_override_factor > 0 时，权重 = min_weight + factor * (learned - min_weight)（软覆盖）
                if learned_weights:
                    # 有学习到的权重，使用软覆盖公式
                    # 当 factor = 0 时，结果就是 min_weight
                    weights[dim] = min_weight + cfg.soft_override_factor * max(0.0, learned_weight - min_weight)
                else:
                    # 没有学习到的权重，使用硬覆盖
                    weights[dim] = min_weight

                reserved_weight += weights[dim]
            else:
                weights[dim] = 0.0

        # Fix: normalize override weights if they exceed 1.0
        # (can happen when multiple critical dimensions are active)
        if reserved_weight > 1.0:
            scale = 1.0 / reserved_weight
            for dim in self._override_active:
                if dim in weights:
                    weights[dim] *= scale
            reserved_weight = 1.0

        # Distribute remaining weight among non-critical dimensions
        remaining_weight = max(0.0, 1.0 - reserved_weight)
        non_critical_dims = [d for d in self.dimensions if d not in self._override_active]

        if non_critical_dims and remaining_weight > 0:
            # Enhanced: Use learned weights to distribute remaining weight
            if learned_weights and cfg.soft_override_factor > 0:
                # Get learned weights for non-critical dims
                non_critical_learned = {
                    d: learned_weights.get(d, 1.0 / len(non_critical_dims))
                    for d in non_critical_dims
                }
                learned_sum = sum(non_critical_learned.values())
                if learned_sum > 0:
                    # Normalize and apply
                    for dim in non_critical_dims:
                        learned_ratio = non_critical_learned[dim] / learned_sum
                        weights[dim] = remaining_weight * learned_ratio
                else:
                    # Fallback to uniform
                    weight_per_dim = remaining_weight / len(non_critical_dims)
                    for dim in non_critical_dims:
                        weights[dim] = weight_per_dim
            else:
                # Hard override: uniform distribution
                weight_per_dim = remaining_weight / len(non_critical_dims)
                for dim in non_critical_dims:
                    weights[dim] = weight_per_dim

        return weights

    def get_override_state(self) -> Dict[str, Any]:
        """Get current override state for persistence (论文P1-6: 滞回状态持久化).

        Returns:
            State dictionary with active overrides and trigger information
        """
        import time
        return {
            "override_active": list(self._override_active),
            "trigger_times": self._override_trigger_times.copy(),
            "gaps_at_trigger": self._gaps_at_trigger.copy(),
            "timestamp": datetime.now(timezone.utc).isoformat() if self._override_active else None,
            "current_time": time.time(),
        }

    def set_override_state(self, state: Dict[str, Any]):
        """Restore override state from persistence (论文P1-6: 滞回状态持久化).

        Args:
            state: State dictionary from get_override_state
        """
        if state and "override_active" in state:
            self._override_active = set(state["override_active"])

        # Restore trigger times and gaps (论文P1-6)
        if state and "trigger_times" in state:
            self._override_trigger_times = state["trigger_times"].copy()

        if state and "gaps_at_trigger" in state:
            self._gaps_at_trigger = state["gaps_at_trigger"].copy()

    def _apply_contract_boost(
        self,
        weights: Dict[str, float],
        contract_signal: Dict[str, Any]
    ) -> Dict[str, float]:
        """Apply contract signal boost to weights (方案 B: CONTRACT 维度补偿).

        论文 Section 3.5.1: "删除 CONTRACT：重定位为影响权重的外部输入"

        当存在活跃用户任务时，临时提升 COMPETENCE 和 HOMEOSTASIS 的权重。

        Args:
            weights: Current normalized weights
            contract_signal: Contract signal dict with keys:
                - is_active: bool
                - priority: int (1-6)
                - urgency: float (0-1)
                - progress: float (0-1)
                - task_type: str

        Returns:
            Boosted and re-normalized weights
        """
        if not contract_signal.get("is_active", False):
            return weights

        # 确定增强系数
        priority = contract_signal.get("priority", 3)
        urgency = contract_signal.get("urgency", 0.0)
        progress = contract_signal.get("progress", 0.0)

        # 默认增强系数
        gamma_contract = 1.5

        # 紧急或高优先级任务使用更高增强
        if priority >= 5 or urgency > 0.7:
            gamma_contract = 2.0

        # 根据进度衰减（接近完成时不再需要强驱动）
        if progress > 0.8:
            decay_factor = 1.0 - (progress - 0.8) / 0.2
            gamma_contract = 1.0 + (gamma_contract - 1.0) * decay_factor

        # 确定要提升的维度
        task_type = contract_signal.get("task_type", "")
        boost_dimensions = ["competence", "homeostasis"]

        if task_type in ["exploration", "learning"]:
            boost_dimensions = ["curiosity", "competence"]
        elif task_type in ["maintenance", "optimization"]:
            boost_dimensions = ["homeostasis"]
        elif task_type in ["social", "interaction"]:
            boost_dimensions = ["attachment"]

        # 应用提升
        boosted_weights = weights.copy()
        for dim in boost_dimensions:
            if dim in boosted_weights:
                boosted_weights[dim] *= gamma_contract

        # 重新归一化
        total = sum(boosted_weights.values())
        if total > 0:
            boosted_weights = {dim: w / total for dim, w in boosted_weights.items()}

        return boosted_weights
