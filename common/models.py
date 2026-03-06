"""Core data models for Genesis X.

Based on the paper's formal definitions in Section 3.2.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Literal
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4
from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    """Return timezone-aware UTC datetime (修复 M49)."""
    return datetime.now(timezone.utc)


class ValueDimension(str, Enum):
    """Five-dimensional value vector (论文 Section 3.5.1).

    核心价值向量定义：
    1. HOMEOSTASIS - 稳态：资源平衡、压力管理、系统稳定
    2. ATTACHMENT - 依恋：社交连接、信任建立、忽视回避
    3. CURIOSITY - 好奇：新奇探索、信息增益、规律发现
    4. COMPETENCE - 胜任：任务成功、技能成长、效能感
    5. SAFETY - 安全：风险回避、损失预防、安全边际

    变更说明 (v14 -> v15):
    - 删除 INTEGRITY：作为硬约束而非价值维度
    - 删除 CONTRACT：重定位为影响权重的外部输入
    - 删除 EFFICIENCY：并入 HOMEOSTASIS
    - 删除 MEANING：并入 CURIOSITY (高阶规律学习)
    - 新增 SAFETY：风险回避作为独立维度
    """
    HOMEOSTASIS = "homeostasis"
    ATTACHMENT = "attachment"
    CURIOSITY = "curiosity"
    COMPETENCE = "competence"
    SAFETY = "safety"


class PriorityLevel(int, Enum):
    """6级目标优先级层次 (论文 Section 3.8.1).

    定义了目标的执行优先级，从高到低：
    1. CRITICAL (6): 紧急任务 - 必须立即处理
    2. HIGH (5): 高优先级 - 尽快处理
    3. MEDIUM_HIGH (4): 中高 - 本周期内完成
    4. MEDIUM (3): 中等 - 下一周期处理
    5. LOW (2): 低优先级 - 有时间再做
    6. OPTIONAL (1): 可选 - 空闲时处理

    对应论文中的目标优先级规则:
    - 用户紧急任务 → CRITICAL
    - 临界价值缺口 → HIGH
    - 用户非紧急任务 → MEDIUM_HIGH
    - 人格驱动目标 → MEDIUM
    - 机会驱动目标 → LOW
    - Boredom驱动目标 → OPTIONAL
    """
    CRITICAL = 6
    HIGH = 5
    MEDIUM_HIGH = 4
    MEDIUM = 3
    LOW = 2
    OPTIONAL = 1

    @classmethod
    def from_source(cls, source: str, user_urgent: bool = False) -> 'PriorityLevel':
        """根据目标来源确定优先级 (论文 Section 3.8.1).

        Args:
            source: 目标来源类型
            user_urgent: 是否为用户紧急任务

        Returns:
            对应的优先级等级
        """
        if user_urgent:
            return cls.CRITICAL

        source_mapping = {
            "user_critical": cls.CRITICAL,
            "critical_value_gap": cls.HIGH,
            "user_task": cls.MEDIUM_HIGH,
            "personality_driven": cls.MEDIUM,
            "opportunity_driven": cls.LOW,
            "boredom_driven": cls.OPTIONAL,
        }

        return source_mapping.get(source, cls.MEDIUM)


class ActionType(str, Enum):
    """Action types for Genesis X.

    a_t in the paper's notation. Includes all valid action types.
    """
    CHAT = "CHAT"
    USE_TOOL = "USE_TOOL"
    LEARN_SKILL = "LEARN_SKILL"
    SLEEP = "SLEEP"
    REFLECT = "REFLECT"
    EXPLORE = "EXPLORE"
    OPTIMIZE = "OPTIMIZE"
    GROW = "GROW"  # 构建任务（创建、实现、生成）
    THINK = "THINK"  # 思考任务（通用思考）


class Observation(BaseModel):
    """Observation from the environment at tick t.

    O_t in the paper's notation.
    """
    type: str = Field(..., description="Type of observation")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Observation data")
    source_ref: Optional[str] = Field(None, description="Source reference")
    timestamp: datetime = Field(default_factory=_utcnow)
    tick: int = Field(..., description="Tick number when observed")


class Action(BaseModel):
    """Action to be executed.

    a_t in the paper's notation. Includes: CHAT, USE_TOOL, LEARN_SKILL, SLEEP, REFLECT, EXPLORE, OPTIMIZE
    """
    type: ActionType = Field(default=ActionType.CHAT, description="Action type")
    params: Dict[str, Any] = Field(default_factory=dict)
    risk_level: float = Field(0.0, ge=0.0, le=1.0, description="Risk level [0,1]")
    capability_req: List[str] = Field(default_factory=list, description="Required capabilities")
    estimated_cost: Optional["CostVector"] = None


class Goal(BaseModel):
    """Goal representation (论文 Section 3.8.1: 6级优先级系统).

    g = <Φ_g, ρ_g, deadline, owner, ctx, compat>

    Where:
    - Φ_g(S): Progress/completion predicate
    - ρ_g: Priority (6级离散优先级: CRITICAL=6, HIGH=5, MEDIUM_HIGH=4, MEDIUM=3, LOW=2, OPTIONAL=1)
    - owner ∈ {self, user}
    - ctx: Context (tools/memory/people involved)
    - compat: Compatibility with other goals (论文v3新增)

    6级优先级对应关系 (论文 Section 3.8.1):
    1. CRITICAL (6): 用户紧急任务 - 必须立即处理
    2. HIGH (5): 临界价值缺口 - 尽快处理
    3. MEDIUM_HIGH (4): 用户非紧急任务 - 本周期内
    4. MEDIUM (3): 人格驱动目标 - 下一周期
    5. LOW (2): 机会驱动目标 - 有时间再做
    6. OPTIONAL (1): Boredom驱动目标 - 空闲处理
    """
    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique goal identifier")
    goal_type: str = Field(..., description="Goal type (e.g., rest_and_recover)")
    # 修复 v15: 使用6级离散优先级而非连续值
    priority_level: PriorityLevel = Field(PriorityLevel.MEDIUM, description="Priority level (1-6)")
    # 向后兼容: 保留 priority 字段作为 priority_level/6 的映射
    priority: float = Field(0.5, ge=0.0, le=1.0, description="Legacy priority [0,1] (deprecated)")
    owner: Literal["self", "user"] = Field("self", description="Goal owner")
    deadline: Optional[datetime] = Field(None, description="Deadline if any")
    progress: float = Field(0.0, ge=0.0, le=1.0, description="Current progress Prog(g,S)")
    status: str = Field("pending", description="Goal status: pending/in_progress/completed/failed/cancelled")
    context: Dict[str, Any] = Field(default_factory=dict, description="Context (tools, memories, people)")
    description: str = Field("", description="Human-readable description")
    created_at: datetime = Field(default_factory=_utcnow)
    completed_tick: Optional[int] = Field(None, description="Tick when goal was completed")
    milestones: List[float] = Field(default_factory=list, description="Milestone progress values")
    # 论文3.8.1新增: 目标兼容性标记
    compat: Dict[str, str] = Field(default_factory=dict, description="Compatibility with other goal types: compatible/conflicting/sequential")
    # 目标来源 (用于确定优先级)
    source: str = Field("internal", description="Goal source: user_critical/critical_value_gap/user_task/personality_driven/opportunity_driven/boredom_driven")
    # 是否为用户紧急任务
    is_user_urgent: bool = Field(False, description="Whether this is a user urgent task")

    def get_effective_priority(self) -> int:
        """获取有效的优先级等级 (1-6).

        Returns:
            优先级等级 (1=OPTIONAL, 6=CRITICAL)
        """
        return self.priority_level.value

    def is_compatible_with(self, other: 'Goal') -> bool:
        """Check compatibility with another goal using compat dict.

        Args:
            other: Another goal to check compatibility with

        Returns:
            True if compatible (not conflicting)
        """
        other_type = other.goal_type
        if other_type in self.compat:
            return self.compat[other_type] != "conflicting"
        return True

    def is_expired(self, current_tick: int = 0) -> bool:
        """Check if goal has expired past its deadline.

        Args:
            current_tick: Current tick number (unused, checks datetime deadline)

        Returns:
            True if goal is past deadline
        """
        if self.deadline is None:
            return False
        # 使用 timezone-aware UTC datetime，与 _utcnow() 保持一致
        return datetime.now(timezone.utc) > self.deadline

    def update_progress(self, new_progress: float, tick: int):
        """Update goal progress and mark completed if progress reaches 1.0.

        Args:
            new_progress: New progress value [0, 1]
            tick: Current tick number
        """
        self.progress = max(0.0, min(1.0, new_progress))
        if self.progress >= 1.0 and self.status != "completed":
            self.status = "completed"
            self.completed_tick = tick


class CostVector(BaseModel):
    """Resource cost of an action.

    Contains: cpu_tokens, io_ops, net_bytes, latency_ms, risk_score, money
    """
    cpu_tokens: int = Field(0, ge=0)
    io_ops: int = Field(0, ge=0)
    net_bytes: int = Field(0, ge=0)
    latency_ms: float = Field(0.0, ge=0.0)
    risk_score: float = Field(0.0, ge=0.0, le=1.0)
    money: float = Field(0.0, ge=0.0, description="Cost in dollars")

    def total_cost(self) -> float:
        """Calculate weighted total cost."""
        return (
            self.cpu_tokens * 0.001 +
            self.io_ops * 0.01 +
            self.net_bytes * 0.000001 +
            self.latency_ms * 0.0001 +
            self.risk_score * 10.0 +
            self.money
        )


class Outcome(BaseModel):
    """Outcome of an action execution."""
    ok: bool = Field(..., description="Whether action succeeded")
    status: str = Field("", description="Status message")
    tool_output_ref: Optional[str] = Field(None, description="Reference to tool output")
    cost_vector: CostVector = Field(default_factory=CostVector)
    evidence_refs: List[str] = Field(default_factory=list, description="Evidence references for schema")
    major_error: bool = Field(False, description="Whether a major error occurred")
    error_message: Optional[str] = None


class EpisodeRecord(BaseModel):
    """Complete record of one tick (e_t).

    Essential fields from Section 3.10.2:
    e_t = ⟨t, O_t, a_t, outcome_t, r_t, δ_t, {δ^(i)_t}, tags⟩

    论文v3修订: 增加维度级RPE记录
    """
    # Basic info
    tick: int = Field(..., description="Tick number")
    session_id: str = Field(..., description="Session identifier")
    timestamp: datetime = Field(default_factory=_utcnow)

    # Observation and action
    observation: Optional[Observation] = None
    action: Optional[Action] = None
    outcome: Optional[Outcome] = None

    # Reward and affect
    reward: float = Field(0.0, description="Total reward r_t")
    delta: float = Field(0.0, description="RPE: δ_t = r_t + γV(s_{t+1}) - V(s_t)")
    # 论文3.10.2新增: 维度级RPE记录
    delta_per_dim: Dict[str, float] = Field(default_factory=dict, description="Per-dimension RPE δ^(i)_t")
    value_pred: float = Field(0.0, description="V(s_t)")

    # State snapshot
    state_snapshot: Dict[str, Any] = Field(default_factory=dict, description="Key state variables")

    # Value system (use str keys for serialization)
    weights: Dict[str, float] = Field(default_factory=dict, description="Dynamic weights w_t")
    gaps: Dict[str, float] = Field(default_factory=dict, description="Drive gaps d_t")
    utilities: Dict[str, float] = Field(default_factory=dict, description="Utility values u_t")

    # Goal and plan
    current_goal: Optional[str] = None
    selected_plan: Optional[str] = None

    # Metadata
    tags: List[str] = Field(default_factory=list, description="Tags: dimensions, tools, emotions, topics")
    cost: CostVector = Field(default_factory=CostVector)

    # For replay
    replay_mode: bool = Field(False)
    rng_seed: Optional[int] = None


class CapabilityResult(BaseModel):
    """器官能力执行结果 (统一定义，避免重复).

    修复：将 CapabilityResult 移至 common/models.py 统一管理，
    避免在 base_organ.py 和 limbs/__init__.py 中重复定义。
    """
    success: bool = Field(..., description="操作是否成功")
    message: str = Field("", description="结果消息")
    data: Optional[Dict[str, Any]] = Field(None, description="返回数据")
    error: Optional[str] = Field(None, description="错误信息")
    execution_time: float = Field(0.0, description="执行时间（秒）")
    cost: Optional[CostVector] = Field(None, description="资源消耗")


# Note: Pydantic v2 handles forward references automatically.
# The `from __future__ import annotations` import above enables proper
# forward reference resolution for CostVector in Action model.
