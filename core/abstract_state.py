"""Abstract State Layer - Paper Section 3.4.2

抽象状态层 𝕊_t - 保证模型切换时的状态连续性

特性:
- 抽象情绪状态 𝕊_emo^t
- 抽象目标表示 𝕊_goal^t
- 抽象记忆指针 𝕊_mem^t
- 抽象上下文摘要 𝕊_ctx^t
- 状态序列化与反序列化
- 模型切换协议 abstract/concretize
"""

import json
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum

from common.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# 抽象状态定义
# ============================================================================

class EmotionState(str, Enum):
    """情绪状态类型"""
    VERY_NEGATIVE = "very_negative"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    POSITIVE = "positive"
    VERY_POSITIVE = "very_positive"


@dataclass
class AbstractEmotionalState:
    """抽象情绪状态 𝕊_emo^t

    独立于具体模型的情绪表示
    """
    valence: float = 0.5         # 愉悦度 [0, 1] (从 [-1,1] 转换)
    arousal: float = 0.5         # 唤醒度 [0, 1]
    boredom: float = 0.0          # 无聊度 [0, 1]

    # 情绪状态分类
    state: EmotionState = EmotionState.NEUTRAL

    # 时间戳
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        # 根据愉悦度确定情绪状态
        self._update_state()

    def _update_state(self):
        """根据愉悦度更新情绪状态"""
        if self.valence < 0.2:
            self.state = EmotionState.VERY_NEGATIVE
        elif self.valence < 0.4:
            self.state = EmotionState.NEGATIVE
        elif self.valence < 0.6:
            self.state = EmotionState.NEUTRAL
        elif self.valence < 0.8:
            self.state = EmotionState.POSITIVE
        else:
            self.state = EmotionState.VERY_POSITIVE

    @classmethod
    def from_concrete(cls, mood: float, stress: float, arousal: float, boredom: float) -> "AbstractEmotionalState":
        """从具体状态创建抽象状态

        Args:
            mood: 情绪愉快度 [-1, 1]
            stress: 压力 [0, 1]
            arousal: 唤醒度 [0, 1]
            boredom: 无聊度 [0, 1]

        Returns:
            抽象情绪状态
        """
        # 将 mood 从 [-1, 1] 转换到 [0, 1]
        # 添加边界检查
        mood_clamped = max(-1.0, min(1.0, mood))
        valence = (mood_clamped + 1) / 2

        return cls(
            valence=valence,
            arousal=arousal,
            boredom=boredom
        )

    def to_dict(self) -> Dict[str, Any]:
        """序列化"""
        return {
            "valence": self.valence,
            "arousal": self.arousal,
            "boredom": self.boredom,
            "state": self.state.value,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class AbstractGoal:
    """抽象目标表示 𝕊_goal^t"""
    goal_type: str              # 目标类型
    priority: int                # 优先级 [1, 6] (论文 6级层次)
    progress: float = 0.0         # 进度 [0, 1]

    # 目标参数
    description: str = ""
    target_value: Optional[float] = None
    deadline: Optional[datetime] = None

    # 来源
    source: str = "unknown"      # gap/opportunity/personality/user/boredom

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """序列化"""
        return {
            "goal_type": self.goal_type,
            "priority": self.priority,
            "progress": self.progress,
            "description": self.description,
            "target_value": self.target_value,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "source": self.source,
            "timestamp": self.timestamp.isoformat()
        }

    @classmethod
    def from_concrete(cls, goal_dict: Dict[str, Any]) -> "AbstractGoal":
        """从具体目标创建抽象目标"""
        return cls(
            goal_type=goal_dict.get("type", "unknown"),
            priority=goal_dict.get("priority", 3),
            progress=goal_dict.get("progress", 0.0),
            description=goal_dict.get("description", ""),
            source=goal_dict.get("source", "unknown")
        )


@dataclass
class AbstractMemoryPointer:
    """抽象记忆指针 𝕊_mem^t"""
    key_ids: List[str] = field(default_factory=list)     # 关键记忆 ID 列表
    embeddings: List[List[float]] = field(default_factory=list)  # 嵌入向量（简化存储）

    # 检索上下文
    query_context: str = ""
    retrieval_count: int = 0

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """序列化"""
        return {
            "key_ids": self.key_ids,
            "embeddings": self.embeddings,
            "query_context": self.query_context,
            "retrieval_count": self.retrieval_count,
            "timestamp": self.timestamp.isoformat()
        }

    def add_key_id(self, memory_id: str) -> None:
        """添加关键记忆 ID"""
        if memory_id not in self.key_ids:
            self.key_ids.append(memory_id)


@dataclass
class AbstractContextSummary:
    """抽象上下文摘要 𝕊_ctx^t"""
    recent_events: List[str] = field(default_factory=list)    # 最近事件摘要
    active_tools: List[str] = field(default_factory=list)       # 活跃工具
    current_focus: str = ""                                   # 当前关注点

    # 统计信息
    total_tokens: int = 0
    tick: int = 0

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """序列化"""
        return {
            "recent_events": self.recent_events,
            "active_tools": self.active_tools,
            "current_focus": self.current_focus,
            "total_tokens": self.total_tokens,
            "tick": self.tick,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class AbstractState:
    """抽象状态层 𝕊_t

    完整的抽象状态，用于模型切换时保持连续性

    𝕊_t = ⟨𝕊_emo^t, 𝕊_goal^t, 𝕊_mem^t, 𝕊_ctx^t⟩
    """
    emotional: AbstractEmotionalState = field(default_factory=AbstractEmotionalState)
    goal: Optional[AbstractGoal] = None
    memory: AbstractMemoryPointer = field(default_factory=AbstractMemoryPointer)
    context: AbstractContextSummary = field(default_factory=AbstractContextSummary)

    # 版本信息（用于状态迁移）
    version: str = "1.0"
    tick: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """完整序列化"""
        return {
            "emotional": self.emotional.to_dict(),
            "goal": self.goal.to_dict() if self.goal else None,
            "memory": self.memory.to_dict(),
            "context": self.context.to_dict(),
            "version": self.version,
            "tick": self.tick
        }

    def update_from_concrete(self, concrete_state: Dict[str, Any]) -> None:
        """从具体状态更新抽象状态

        Args:
            concrete_state: 具体状态字典 (来自黑板或 GlobalState)
        """
        # 更新情绪状态
        mood = concrete_state.get("mood", 0.5)
        stress = concrete_state.get("stress", 0.2)
        arousal = concrete_state.get("arousal", 0.5)
        boredom = concrete_state.get("boredom", 0.0)

        self.emotional = AbstractEmotionalState.from_concrete(mood, stress, arousal, boredom)

        # 更新目标
        if "current_goal" in concrete_state and concrete_state["current_goal"]:
            self.goal = AbstractGoal.from_concrete(concrete_state["current_goal"])

        # 更新 tick
        self.tick = concrete_state.get("tick", 0)

    def to_concrete(self, target_config: str) -> Dict[str, Any]:
        """将抽象状态转换为目标配置的具体状态

        Args:
            target_config: 目标配置 (single/core5/full7)

        Returns:
            具体状态字典
        """
        # 基础状态
        concrete = {
            "tick": self.tick,
            "version": self.version
        }

        # 从抽象情绪恢复具体情绪
        # valence [0,1] → mood [-1, 1]
        mood = (self.emotional.valence * 2) - 1
        concrete["mood"] = mood
        # 简化映射，添加边界检查
        concrete["stress"] = max(0.0, min(1.0, 1.0 - self.emotional.valence))
        concrete["arousal"] = self.emotional.arousal
        concrete["boredom"] = self.emotional.boredom

        # 从抽象目标恢复具体目标
        if self.goal:
            concrete["current_goal"] = {
                "type": self.goal.goal_type,
                "priority": self.goal.priority,
                "progress": self.goal.progress,
                "description": self.goal.description
            }

        return concrete


# ============================================================================
# 模型切换协议 (论文 3.4.2)
# ============================================================================

@dataclass
class SwitchEvent:
    """模型切换事件"""
    old_config: str
    new_config: str
    tick: int
    reason: str = ""
    abstract_state: Dict[str, Any] = field(default_factory=dict)

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class StateTransitionManager:
    """状态迁移管理器 - 处理模型切换时的状态连续性

    论文 3.4.2:
    on_switch(old_config, new_config):
        1. 保存当前具体状态到抽象层: 𝕊_t ← abstract(S_t^old)
        2. 从抽象层恢复到新配置: S_t^new ← concretize(𝕊_t, new_config)
    """

    def __init__(self):
        self._current_abstract: Optional[AbstractState] = None
        self._switch_history: List[SwitchEvent] = []
        self._tick = 0

    def abstract(self, concrete_state: Dict[str, Any], config: str) -> AbstractState:
        """将具体状态抽象化

        Args:
            concrete_state: 当前具体状态
            config: 当前配置模式

        Returns:
            抽象状态
        """
        abstract = AbstractState()
        abstract.update_from_concrete(concrete_state)
        abstract.version = config
        abstract.tick = self._tick

        self._current_abstract = abstract

        logger.debug(f"Abstracted state from {config}: {len(abstract.to_dict())} fields")
        return abstract

    def concretize(self, abstract: AbstractState, target_config: str) -> Dict[str, Any]:
        """将抽象状态具体化

        Args:
            abstract: 抽象状态
            target_config: 目标配置模式

        Returns:
            具体状态字典
        """
        concrete = abstract.to_concrete(target_config)
        self._current_abstract = abstract

        logger.debug(f"Concretized state to {target_config}: {len(concrete)} fields")
        return concrete

    def record_switch(
        self,
        old_config: str,
        new_config: str,
        reason: str = ""
    ) -> SwitchEvent:
        """记录切换事件"""
        event = SwitchEvent(
            old_config=old_config,
            new_config=new_config,
            tick=self._tick,
            reason=reason,
            abstract_state=self._current_abstract.to_dict() if self._current_abstract else {}
        )
        self._switch_history.append(event)

        return event

    def get_switch_history(self) -> List[SwitchEvent]:
        """获取切换历史"""
        return self._switch_history.copy()

    def set_tick(self, tick: int) -> None:
        """设置当前 tick"""
        self._tick = tick


# ============================================================================
# 与黑板集成
# ============================================================================

class BlackboardWithAbstractState:
    """带抽象状态层的黑板"""

    def __init__(self):
        from tools.blackboard import Blackboard

        # 复用原有的黑板状态
        self.blackboard = Blackboard()

        # 抽象状态层
        self.abstract_state: Optional[AbstractState] = None

        # 状态迁移管理器
        self.transition_manager = StateTransitionManager()

    def read(self):
        """读取黑板状态"""
        return self.blackboard.read()

    def write(self, slot_name: str, value: Any, writer: str = "system") -> None:
        """写入黑板槽位"""
        self.blackboard.write(slot_name, value, writer)

    def abstract_current_state(self, config: str) -> AbstractState:
        """抽象当前状态"""
        concrete = {
            "tick": self.blackboard.state.tick,
            "mood": self.blackboard.state.emotional_state.get("mood", 0.5),
            "stress": self.blackboard.state.emotional_state.get("stress", 0.2),
            "arousal": self.blackboard.state.emotional_state.get("arousal", 0.5),
            "boredom": self.blackboard.state.emotional_state.get("boredom", 0.0),
            "current_goal": self.blackboard.state.current_goal,
            "retrieved_memories": self.blackboard.state.retrieved_memories,
            "resource_state": self.blackboard.state.resource_state,
            "soul_state": self.blackboard.state.soul_state,
            "middle_vars": self.blackboard.state.middle_vars
        }
        return self.transition_manager.abstract(concrete, config)

    def concretize_to_state(self, abstract: AbstractState, target_config: str) -> Dict[str, Any]:
        """将抽象状态具体化"""
        concrete = self.transition_manager.concretize(abstract, target_config)

        # 更新黑板状态
        if "mood" in concrete:
            self.blackboard.state.emotional_state["mood"] = concrete["mood"]
        if "stress" in concrete:
            self.blackboard.state.emotional_state["stress"] = concrete["stress"]
        if "arousal" in concrete:
            self.blackboard.state.emotional_state["arousal"] = concrete["arousal"]
        if "boredom" in concrete:
            self.blackboard.state.emotional_state["boredom"] = concrete["boredom"]
        if "current_goal" in concrete:
            self.blackboard.state.current_goal = concrete["current_goal"]

        return concrete

    def get_middle_vars(self) -> Dict[str, float]:
        """获取中间变量"""
        return self.blackboard.get_middle_vars()

    def update_middle_vars(self, et: float, ct: float, es: float) -> None:
        """更新中间变量"""
        self.blackboard.update_middle_vars(et, ct, es)

    def get_resource_pressure(self) -> float:
        """获取资源压力"""
        return self.blackboard.get_resource_pressure()

    def update_resource_state(self, compute: float, memory: float) -> None:
        """更新资源状态"""
        self.blackboard.update_resource_state(compute, memory)


# ============================================================================
# 导出兼容
# ============================================================================

# 复用原有的黑板类
Blackboard = None  # 将在导入时处理


def get_blackboard_with_abstract_state() -> BlackboardWithAbstractState:
    """获取带抽象状态层的黑板实例"""
    return BlackboardWithAbstractState()


# 工厂函数
def create_abstract_state() -> AbstractState:
    """创建空的抽象状态"""
    return AbstractState()


def create_transition_manager() -> StateTransitionManager:
    """创建状态迁移管理器"""
    return StateTransitionManager()
