"""Fine-Grained Emotion Decay Mechanism - Paper Section 3.7.3

精细情绪衰减机制 - GenesisX 高保真情绪动力学

特性:
- 多维度情绪衰减率（愉悦度、压力、唤醒度各有衰减率）
- 阈值触发的情绪转换（情绪状态转移）
- 记忆触发的情绪重激活（普鲁斯特效应）
- 时间衰减曲线（指数衰减 + 情绪惯性）
"""

import math
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import numpy as np

from common.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# 情绪维度定义
# ============================================================================

class EmotionDimension(str, Enum):
    """情绪维度"""
    VALENCE = "valence"       # 愉悦度
    STRESS = "stress"         # 压力
    AROUSAL = "arousal"       # 唤醒度
    BOREDOM = "boredom"       # 无聊度


# ============================================================================
# 衰减配置
# ============================================================================

@dataclass
class DecayConfig:
    """情绪衰减配置

    论文 3.7.3:
    - λ_v: 愉悦度衰减率
    - λ_s: 压力衰减率
    - λ_a: 唤醒度衰减率
    - λ_b: 无聊度衰减率
    """

    # 基础衰减率（每 tick）
    lambda_valence: float = 0.05     # 愉悦度衰减率
    lambda_stress: float = 0.08      # 压力衰减率（压力通常消散更快）
    lambda_arousal: float = 0.1      # 唤醒度衰减率
    lambda_boredom: float = 0.03     # 无聊度衰减率

    # 情绪惯性（阻尼系数）
    inertia: float = 0.7             # 情绪惯性 [0, 1]

    # 阈值配置
    valence_threshold: float = 0.1   # 愉悦度转换阈值
    stress_threshold: float = 0.1    # 压力转换阈值
    arousal_threshold: float = 0.15  # 唤醒度转换阈值

    # 时间常数（秒）
    time_constant_valence: float = 300.0   # 愉悦度时间常数
    time_constant_stress: float = 180.0    # 压力时间常数
    time_constant_arousal: float = 120.0   # 唤醒度时间常数


# ============================================================================
# 情绪状态
# ============================================================================

@dataclass
class EmotionalState:
    """情绪状态

    论文 3.7.3:
    S_emotion(t) = ⟨V_t, S_t, A_t, B_t⟩
    """

    valence: float = 0.5       # 愉悦度 [0, 1] (从 [-1,1] 转换)
    stress: float = 0.2        # 压力 [0, 1]
    arousal: float = 0.5       # 唤醒度 [0, 1]
    boredom: float = 0.0       # 无聊度 [0, 1]

    # 导数（变化率）
    valence_delta: float = 0.0
    stress_delta: float = 0.0
    arousal_delta: float = 0.0
    boredom_delta: float = 0.0

    # 时间戳
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_update: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def clamp(self) -> None:
        """将值裁剪到有效范围"""
        self.valence = max(0.0, min(1.0, self.valence))
        self.stress = max(0.0, min(1.0, self.stress))
        self.arousal = max(0.0, min(1.0, self.arousal))
        self.boredom = max(0.0, min(1.0, self.boredom))

    def to_dict(self) -> Dict[str, Any]:
        """序列化"""
        return {
            "valence": self.valence,
            "stress": self.stress,
            "arousal": self.arousal,
            "boredom": self.boredom,
            "valence_delta": self.valence_delta,
            "stress_delta": self.stress_delta,
            "arousal_delta": self.arousal_delta,
            "boredom_delta": self.boredom_delta,
            "timestamp": self.timestamp.isoformat(),
            "last_update": self.last_update.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmotionalState":
        """反序列化"""
        return cls(
            valence=data.get("valence", 0.5),
            stress=data.get("stress", 0.2),
            arousal=data.get("arousal", 0.5),
            boredom=data.get("boredom", 0.0),
            valence_delta=data.get("valence_delta", 0.0),
            stress_delta=data.get("stress_delta", 0.0),
            arousal_delta=data.get("arousal_delta", 0.0),
            boredom_delta=data.get("boredom_delta", 0.0),
        )

    def to_concrete(self) -> Dict[str, float]:
        """转换为具体状态格式（与黑板兼容）"""
        # valence [0,1] → mood [-1, 1]
        mood = (self.valence * 2) - 1
        return {
            "mood": mood,
            "stress": self.stress,
            "arousal": self.arousal,
            "boredom": self.boredom
        }

    @classmethod
    def from_concrete(cls, concrete: Dict[str, float]) -> "EmotionalState":
        """从具体状态创建"""
        # mood [-1, 1] → valence [0, 1]
        mood = concrete.get("mood", 0.0)
        valence = (mood + 1) / 2
        return cls(
            valence=valence,
            stress=concrete.get("stress", 0.2),
            arousal=concrete.get("arousal", 0.5),
            boredom=concrete.get("boredom", 0.0)
        )


# ============================================================================
# 衰减函数
# ============================================================================

class EmotionDecayFunction:
    """情绪衰减函数

    论文 3.7.3:
    decay(x, λ, Δt) = x · e^(-λ·Δt) · (1 - I) + I · x_prev

    其中:
    - x: 当前情绪值
    - λ: 衰减率
    - Δt: 时间差
    - I: 惯性系数
    """

    def __init__(self, config: Optional[DecayConfig] = None):
        self.config = config or DecayConfig()

    def exponential_decay(
        self,
        current: float,
        decay_rate: float,
        time_delta: float,
        inertia: Optional[float] = None
    ) -> float:
        """指数衰减函数

        公式: x(t) = x₀ · e^(-λ·t)

        Args:
            current: 当前值
            decay_rate: 衰减率 λ
            time_delta: 时间差
            inertia: 惯性系数（可选）

        Returns:
            衰减后的值
        """
        # 边界检查：防止负的衰减率和时间差
        decay_rate = max(0.0, decay_rate)
        time_delta = max(0.0, time_delta)

        # 指数衰减
        decayed = current * math.exp(-decay_rate * time_delta)

        # 应用惯性
        if inertia is not None:
            inertia = max(0.0, min(1.0, inertia))  # 确保惯性在 [0, 1]
            inertia_factor = 1.0 - inertia
            decayed = decayed * inertia_factor + current * inertia

        return decayed

    def compute_decay(
        self,
        dimension: EmotionDimension,
        current: float,
        time_delta: float,
        inertia_override: Optional[float] = None
    ) -> float:
        """计算指定维度的衰减

        Args:
            dimension: 情绪维度
            current: 当前值
            time_delta: 时间差（秒）
            inertia_override: 覆盖惯性系数

        Returns:
            衰减后的值
        """
        # 获取衰减率
        decay_rates = {
            EmotionDimension.VALENCE: self.config.lambda_valence,
            EmotionDimension.STRESS: self.config.lambda_stress,
            EmotionDimension.AROUSAL: self.config.lambda_arousal,
            EmotionDimension.BOREDOM: self.config.lambda_boredom,
        }

        decay_rate = decay_rates.get(dimension, 0.05)
        inertia = inertia_override if inertia_override is not None else self.config.inertia

        return self.exponential_decay(current, decay_rate, time_delta, inertia)

    def compute_multi_dimension_decay(
        self,
        state: EmotionalState,
        time_delta: float
    ) -> EmotionalState:
        """计算多维度的衰减

        Args:
            state: 当前情绪状态
            time_delta: 时间差（秒）

        Returns:
            衰减后的情绪状态
        """
        new_state = EmotionalState(
            valence=self.compute_decay(EmotionDimension.VALENCE, state.valence, time_delta),
            stress=self.compute_decay(EmotionDimension.STRESS, state.stress, time_delta),
            arousal=self.compute_decay(EmotionDimension.AROUSAL, state.arousal, time_delta),
            boredom=self.compute_decay(EmotionDimension.BOREDOM, state.boredom, time_delta),
            timestamp=datetime.now(timezone.utc),
            last_update=state.last_update
        )

        # 计算变化率
        new_state.valence_delta = new_state.valence - state.valence
        new_state.stress_delta = new_state.stress - state.stress
        new_state.arousal_delta = new_state.arousal - state.arousal
        new_state.boredom_delta = new_state.boredom - state.boredom

        return new_state


# ============================================================================
# 阈值触发的情绪转换
# ============================================================================

class EmotionTransitionTrigger:
    """情绪转换触发器

    论文 3.7.3:
    当情绪跨越阈值时触发状态转换
    """

    def __init__(self, config: Optional[DecayConfig] = None):
        self.config = config or DecayConfig()

    def check_transition(
        self,
        old_state: EmotionalState,
        new_state: EmotionalState
    ) -> List[str]:
        """检查情绪转换

        Args:
            old_state: 旧状态
            new_state: 新状态

        Returns:
            触发的转换事件列表
        """
        transitions = []

        # 愉悦度阈值检查
        if abs(old_state.valence - new_state.valence) > self.config.valence_threshold:
            if new_state.valence > old_state.valence:
                transitions.append("valence_increase")
            else:
                transitions.append("valence_decrease")

        # 愉悦度极值检查
        if new_state.valence > 0.8 and old_state.valence <= 0.8:
            transitions.append("enter_very_positive")
        elif new_state.valence < 0.2 and old_state.valence >= 0.2:
            transitions.append("enter_very_negative")

        # 压力阈值检查
        if abs(old_state.stress - new_state.stress) > self.config.stress_threshold:
            if new_state.stress > old_state.stress:
                transitions.append("stress_increase")
            else:
                transitions.append("stress_decrease")

        # 高压预警
        if new_state.stress > 0.7 and old_state.stress <= 0.7:
            transitions.append("high_stress_warning")

        # 唤醒度阈值检查
        if abs(old_state.arousal - new_state.arousal) > self.config.arousal_threshold:
            if new_state.arousal > old_state.arousal:
                transitions.append("arousal_increase")
            else:
                transitions.append("arousal_decrease")

        return transitions


# ============================================================================
# 记忆触发的情绪重激活（普鲁斯特效应）
# ============================================================================

@dataclass
class MemoryEmotionalContext:
    """记忆的情绪上下文"""
    memory_id: str
    valence: float
    stress: float
    arousal: float
    timestamp: datetime

    # 重激活强度
    reactivation_strength: float = 0.5

    def similarity(self, other: "MemoryEmotionalContext") -> float:
        """计算情绪上下文相似度"""
        v_diff = abs(self.valence - other.valence)
        s_diff = abs(self.stress - other.stress)
        a_diff = abs(self.arousal - other.arousal)

        # 综合相似度
        return 1.0 - (v_diff * 0.5 + s_diff * 0.3 + a_diff * 0.2)


class ProustEffectTrigger:
    """普鲁斯特效应触发器

    论文 3.7.3:
    当检索到具有强烈情绪标记的记忆时，重激活相关情绪
    """

    def __init__(
        self,
        activation_threshold: float = 0.7,    # 激活阈值
        decay_factor: float = 0.3,            # 衰减因子
    ):
        self.activation_threshold = activation_threshold
        self.decay_factor = decay_factor

    def compute_reactivation(
        self,
        current_state: EmotionalState,
        memory_context: MemoryEmotionalContext
    ) -> Tuple[EmotionalState, float]:
        """计算情绪重激活

        公式:
        S_new = (1 - α) · S_current + α · S_memory

        其中 α 由记忆强度和相似度决定

        Args:
            current_state: 当前情绪状态
            memory_context: 记忆的情绪上下文

        Returns:
            (重激活后的状态, 激活强度)
        """
        # 计算时间衰减（越近的记忆影响越大）
        time_diff = (datetime.now(timezone.utc) - memory_context.timestamp).total_seconds()
        time_decay = math.exp(-self.decay_factor * time_diff / 3600)  # 每小时衰减

        # 激活强度
        activation = memory_context.reactivation_strength * time_decay

        if activation < self.activation_threshold:
            return current_state, 0.0

        # 重激活
        new_state = EmotionalState(
            valence=current_state.valence * (1 - activation) + memory_context.valence * activation,
            stress=current_state.stress * (1 - activation) + memory_context.stress * activation,
            arousal=current_state.arousal * (1 - activation) + memory_context.arousal * activation,
            boredom=current_state.boredom,  # 无聊度不受记忆影响
            timestamp=datetime.now(timezone.utc),
            last_update=current_state.last_update
        )

        new_state.clamp()

        return new_state, activation


# ============================================================================
# 精细情绪衰减管理器
# ============================================================================

@dataclass
class DecayResult:
    """衰减结果"""
    new_state: EmotionalState
    time_delta: float
    transitions: List[str] = field(default_factory=list)
    reactivation_occurred: bool = False
    reactivation_strength: float = 0.0


class FineGrainedEmotionDecay:
    """精细情绪衰减管理器

    整合论文 3.7.3 的所有情绪衰减机制:

    1. 多维度指数衰减
    2. 阈值触发的情绪转换
    3. 记忆触发的情绪重激活
    4. 情绪惯性
    """

    def __init__(self, config: Optional[DecayConfig] = None):
        self.config = config or DecayConfig()
        self.decay_func = EmotionDecayFunction(config)
        self.transition_trigger = EmotionTransitionTrigger(config)
        self.proust_trigger = ProustEffectTrigger()

        # 当前状态
        self._current_state: Optional[EmotionalState] = None

    def get_state(self) -> EmotionalState:
        """获取当前情绪状态"""
        if self._current_state is None:
            self._current_state = EmotionalState()
        return self._current_state

    def set_state(self, state: EmotionalState) -> None:
        """设置当前情绪状态"""
        self._current_state = state

    def tick(
        self,
        time_delta: float,
        memory_contexts: Optional[List[MemoryEmotionalContext]] = None
    ) -> DecayResult:
        """执行一个 tick 的情绪衰减

        Args:
            time_delta: 时间差（秒）
            memory_contexts: 检索到的记忆情绪上下文列表

        Returns:
            衰减结果
        """
        current = self.get_state()

        # 1. 基础衰减
        new_state = self.decay_func.compute_multi_dimension_decay(current, time_delta)

        # 2. 检查阈值转换
        transitions = self.transition_trigger.check_transition(current, new_state)

        # 3. 处理记忆重激活（普鲁斯特效应）
        reactivation_occurred = False
        reactivation_strength = 0.0

        if memory_contexts:
            for mem_ctx in memory_contexts:
                new_state, strength = self.proust_trigger.compute_reactivation(
                    new_state, mem_ctx
                )
                if strength > 0:
                    reactivation_occurred = True
                    reactivation_strength = max(reactivation_strength, strength)

        # 更新状态
        self._current_state = new_state

        return DecayResult(
            new_state=new_state,
            time_delta=time_delta,
            transitions=transitions,
            reactivation_occurred=reactivation_occurred,
            reactivation_strength=reactivation_strength
        )

    def apply_impulse(
        self,
        dimension: EmotionDimension,
        impulse: float
    ) -> EmotionalState:
        """应用情绪脉冲（外部刺激）

        Args:
            dimension: 情绪维度
            impulse: 脉冲值 [-1, 1]

        Returns:
            更新后的状态
        """
        current = self.get_state()
        new_state = EmotionalState(
            valence=current.valence,
            stress=current.stress,
            arousal=current.arousal,
            boredom=current.boredom,
            valence_delta=current.valence_delta,
            stress_delta=current.stress_delta,
            arousal_delta=current.arousal_delta,
            boredom_delta=current.boredom_delta,
            timestamp=datetime.now(timezone.utc),
            last_update=current.last_update
        )

        # 应用脉冲
        if dimension == EmotionDimension.VALENCE:
            new_state.valence = max(0.0, min(1.0, current.valence + impulse * 0.5))
            new_state.valence_delta = new_state.valence - current.valence
        elif dimension == EmotionDimension.STRESS:
            new_state.stress = max(0.0, min(1.0, current.stress + impulse * 0.3))
            new_state.stress_delta = new_state.stress - current.stress
        elif dimension == EmotionDimension.AROUSAL:
            new_state.arousal = max(0.0, min(1.0, current.arousal + impulse * 0.4))
            new_state.arousal_delta = new_state.arousal - current.arousal
        elif dimension == EmotionDimension.BOREDOM:
            new_state.boredom = max(0.0, min(1.0, current.boredom + impulse * 0.2))
            new_state.boredom_delta = new_state.boredom - current.boredom

        self._current_state = new_state
        return new_state


# ============================================================================
# 工厂函数
# ============================================================================

def create_decay_config(
    lambda_valence: float = 0.05,
    lambda_stress: float = 0.08,
    lambda_arousal: float = 0.1,
    lambda_boredom: float = 0.03
) -> DecayConfig:
    """创建衰减配置"""
    return DecayConfig(
        lambda_valence=lambda_valence,
        lambda_stress=lambda_stress,
        lambda_arousal=lambda_arousal,
        lambda_boredom=lambda_boredom
    )


def create_emotion_decay(config: Optional[DecayConfig] = None) -> FineGrainedEmotionDecay:
    """创建精细情绪衰减管理器"""
    return FineGrainedEmotionDecay(config)


def create_emotional_state(
    valence: float = 0.5,
    stress: float = 0.2,
    arousal: float = 0.5,
    boredom: float = 0.0
) -> EmotionalState:
    """创建情绪状态"""
    return EmotionalState(
        valence=valence,
        stress=stress,
        arousal=arousal,
        boredom=boredom
    )


def create_memory_context(
    memory_id: str,
    valence: float,
    stress: float,
    arousal: float,
    timestamp: Optional[datetime] = None
) -> MemoryEmotionalContext:
    """创建记忆情绪上下文"""
    return MemoryEmotionalContext(
        memory_id=memory_id,
        valence=valence,
        stress=stress,
        arousal=arousal,
        timestamp=timestamp or datetime.now(timezone.utc)
    )
