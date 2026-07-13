"""Global State - S_t = ⟨O_t, X_t, M_t, K_t, θ, ω_t⟩"""
from typing import Dict, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from common.models import ValueDimension

if TYPE_CHECKING:
    from core.stores.fields import FieldStore


def _get_real_system_resources() -> Dict[str, float]:
    """获取真实的系统资源占用率.

    Returns:
        Dict with:
        - compute: CPU占用率 [0, 1]
        - memory: 内存占用率 [0, 1]
    """
    try:
        import psutil
        # CPU占用率（百分比转0-1）
        cpu_percent = psutil.cpu_percent(interval=0.1) / 100.0
        # 内存占用率
        memory_percent = psutil.virtual_memory().percent / 100.0
        return {
            "compute": cpu_percent,
            "memory": memory_percent,
        }
    except Exception:
        # psutil 不可用时返回默认值
        return {"compute": 0.2, "memory": 0.15}


@dataclass
class GlobalState:
    """Global state of the Genesis X system.

    资源模型修正:
    - compute/memory 是真实的系统占用率（通过 psutil 检测）
    - 不再模拟，而是直接读取系统状态
    - 每次调用 update_resources() 会刷新真实值
    """

    # P8-4: 7 个情感标量改为 FieldStore 单一真相源委托。
    # 注入 field_store 时读写 FieldStore；未注入时（tests/独立构造）用 _xxx_local fallback。
    field_store: Optional["FieldStore"] = field(default=None, repr=False, compare=False)

    # Internal state X_t - 论文 Section 3.2 数字原生模型
    # 计算资源占用率: Compute_t ∈ [0,1] - 真实的CPU占用率
    # 内存占用率: Memory_t ∈ [0,1] - 真实的内存占用率
    # 初始值会在第一次 update_resources() 时被真实值覆盖
    compute: float = 0.20
    memory: float = 0.15

    # 是否使用真实系统资源检测
    use_real_resources: bool = True

    # 活动疲劳度 - 独立于系统资源占用率（非情感标量，不做 FieldStore 委托）
    # 基于 ticks 和处理的活动累积，用于决定何时做梦/休息
    activity_fatigue: float = 0.0  # 从0开始，随活动增加，休息后减少

    # P8-4: mood/stress/boredom 不再是 dataclass 字段，改为 property 委托 FieldStore。
    # fallback 私有字段（仅 field_store=None 时用）。
    _mood_local: float = field(default=0.0, repr=False)      # Mood_0=0.0 (论文默认中性)
    _stress_local: float = field(default=0.15, repr=False)    # Stress_0=0.15
    _boredom_local: float = field(default=0.30, repr=False)   # Boredom_0=0.30
    _energy_local: float = field(default=0.80, repr=False)    # Energy_0=0.80 (1 - activity_fatigue 初始)
    _fatigue_local: float = field(default=0.0, repr=False)    # Fatigue_0=0.0 (= activity_fatigue 初始)
    _bond_local: float = field(default=0.20, repr=False)      # Bond_0=0.20
    _trust_local: float = field(default=0.20, repr=False)     # Trust_0=0.20

    # 关系与唤醒: Relationship_t ∈ [0,1], Arousal_t ∈ [0,1]
    # 注: P8-4 后 bond/trust 不再折叠到 relationship（各自独立委托 FieldStore）。
    # relationship 保留为普通字段供遗留 to_dict/from_dict 兼容，但不再被 bond/trust 派生。
    relationship: float = 0.20  # Relationship_0=0.20 (遗留兼容)
    arousal: float = 0.50  # Arousal_0=0.50

    # 资源压力指数 RP_t (论文 Section 3.2)
    # RP_t = α·Compute_t + β·Memory_t
    resource_pressure: float = 0.0  # 初始无压力

    # ========================================================================
    # P8-4: 7 个情感标量 property —— FieldStore 单一真相源委托
    # ========================================================================
    # 注意三种不同的"疲劳/能量"概念:
    # 1. compute/memory: 真实系统资源占用率（psutil检测）
    # 2. activity_fatigue: 活动疲劳度（基于ticks累积，用于决定做梦）——独立字段，不委托
    # 3. energy/fatigue: 情感标量，委托 FieldStore（与 activity_fatigue 解耦）
    def _field_get(self, name: str, local_attr: str) -> float:
        """委托读取：注入 FieldStore 时读 FieldStore，否则读本地 fallback。"""
        if self.field_store is not None:
            return self.field_store.get(name)
        return getattr(self, local_attr)

    def _field_set(self, name: str, local_attr: str, value: float) -> None:
        """委托写入：注入 FieldStore 时写 FieldStore（自动 clip），否则写本地 fallback（手动 clip）。"""
        clamped = max(0.0, min(1.0, value))
        if self.field_store is not None:
            self.field_store.set(name, clamped)
        else:
            setattr(self, local_attr, clamped)

    @property
    def energy(self) -> float:
        return self._field_get("energy", "_energy_local")

    @energy.setter
    def energy(self, value: float):
        self._field_set("energy", "_energy_local", value)

    @property
    def fatigue(self) -> float:
        return self._field_get("fatigue", "_fatigue_local")

    @fatigue.setter
    def fatigue(self, value: float):
        self._field_set("fatigue", "_fatigue_local", value)

    @property
    def mood(self) -> float:
        """Mood_t ∈ [0,1] (论文实际实现：affect/mood.py clamp 到 [0,1])."""
        return self._field_get("mood", "_mood_local")

    @mood.setter
    def mood(self, value: float):
        self._field_set("mood", "_mood_local", value)

    @property
    def stress(self) -> float:
        return self._field_get("stress", "_stress_local")

    @stress.setter
    def stress(self, value: float):
        self._field_set("stress", "_stress_local", value)

    @property
    def bond(self) -> float:
        return self._field_get("bond", "_bond_local")

    @bond.setter
    def bond(self, value: float):
        self._field_set("bond", "_bond_local", value)

    @property
    def trust(self) -> float:
        return self._field_get("trust", "_trust_local")

    @trust.setter
    def trust(self, value: float):
        # P8-4: 不再平均到 relationship，直接委托 FieldStore（与 bond 独立）
        self._field_set("trust", "_trust_local", value)

    @property
    def boredom(self) -> float:
        return self._field_get("boredom", "_boredom_local")

    @boredom.setter
    def boredom(self, value: float):
        self._field_set("boredom", "_boredom_local", value)

    # Working memory slots
    current_goal: str = ""
    current_plan: str = ""
    last_user_interaction: float = 0.0  # time since last interaction

    # Value system state
    value_pred: float = 0.0  # V(s_t) - value function prediction
    weights: Dict[ValueDimension, float] = field(default_factory=lambda: {
        # 论文 Section 3.5.1: 5维核心价值向量
        # 初始权重均匀分布: 1/5 = 0.2
        ValueDimension.HOMEOSTASIS: 0.20,
        ValueDimension.ATTACHMENT: 0.20,
        ValueDimension.CURIOSITY: 0.20,
        ValueDimension.COMPETENCE: 0.20,
        ValueDimension.SAFETY: 0.20,
    })
    gaps: Dict[ValueDimension, float] = field(default_factory=lambda: {
        # 论文 Section 3.6.1: d_i = max(0, f^(i)* - f^(i)(S_t))
        # 初始无驱动缺口
        ValueDimension.HOMEOSTASIS: 0.0,
        ValueDimension.ATTACHMENT: 0.0,
        ValueDimension.CURIOSITY: 0.0,
        ValueDimension.COMPETENCE: 0.0,
        ValueDimension.SAFETY: 0.0,
    })
    setpoints: Dict[ValueDimension, float] = field(default_factory=lambda: {
        # 论文 Appendix A.4: 默认设定点
        ValueDimension.HOMEOSTASIS: 0.70,
        ValueDimension.ATTACHMENT: 0.70,
        ValueDimension.CURIOSITY: 0.60,
        ValueDimension.COMPETENCE: 0.75,
        ValueDimension.SAFETY: 0.80,
    })

    # Memory counters
    episodic_count: int = 0
    schema_count: int = 0
    skill_count: int = 0

    # Resource ledger
    tokens_used: int = 0
    io_ops: int = 0
    net_bytes: int = 0
    money_spent: float = 0.0

    # Mode and stage
    mode: str = "work"  # work, friend, sleep
    stage: str = "adult"  # embryo, juvenile, adult, elder

    # Tick counter
    tick: int = 0

    # Priority override state Ω_t (论文 Section 3.6.4)
    # 用于持久化软优先级覆盖的滞回状态
    # override_active: 当前处于覆盖状态的维度集合 {dim_1, dim_2, ...}
    # 修复: 使用 set 而非 list 以与 weights.py 中的用法保持一致
    override_active: set = field(default_factory=set)
    override_trigger_time: float = 0.0  # 覆盖触发时间
    gaps_at_trigger: Dict[str, float] = field(default_factory=dict)  # 触发时的缺口值

    # Value learning state (论文 Section 3.12)
    # 用于价值学习参数的持久化
    value_learning_enabled: bool = True
    last_value_learning_tick: int = 0
    value_learning_interval: int = 50  # 每50tick检查一次是否需要学习

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for serialization."""
        return {
            "tick": self.tick,
            # 数字原生字段（真实系统资源）
            "compute": self.compute,
            "memory": self.memory,
            "use_real_resources": self.use_real_resources,
            # 活动疲劳度（独立于系统资源）
            "activity_fatigue": self.activity_fatigue,
            "mood": self.mood,
            "stress": self.stress,
            "relationship": self.relationship,
            "arousal": self.arousal,
            "boredom": self.boredom,
            "resource_pressure": self.resource_pressure,
            # 兼容字段
            "energy": self.energy,
            "fatigue": self.fatigue,
            "bond": self.bond,
            "trust": self.trust,
            # Working memory
            "current_goal": self.current_goal,
            "current_plan": self.current_plan,
            "last_user_interaction": self.last_user_interaction,
            # Value system
            "value_pred": self.value_pred,
            "weights": {k.value: v for k, v in self.weights.items()},
            "gaps": {k.value: v for k, v in self.gaps.items()},
            "setpoints": {k.value: v for k, v in self.setpoints.items()},
            # Memory counters
            "episodic_count": self.episodic_count,
            "schema_count": self.schema_count,
            "skill_count": self.skill_count,
            # Resource ledger
            "tokens_used": self.tokens_used,
            "io_ops": self.io_ops,
            "net_bytes": self.net_bytes,
            "money_spent": self.money_spent,
            # Mode and stage
            "mode": self.mode,
            "stage": self.stage,
            # 论文 Section 3.6.4: 优先级覆盖状态持久化
            "override_active": list(self.override_active),
            "override_trigger_time": self.override_trigger_time,
            "gaps_at_trigger": self.gaps_at_trigger,
            # 论文 Section 3.12: 价值学习状态
            "value_learning_enabled": self.value_learning_enabled,
            "last_value_learning_tick": self.last_value_learning_tick,
            "value_learning_interval": self.value_learning_interval,
        }

    def update_body(self, dt: float):
        """Update body state (metabolism).

        修正: 使用真实系统资源 + 活动疲劳度分离

        Args:
            dt: Time delta in ticks (should be non-negative)
        """
        # Validate dt
        if dt <= 0:
            return

        # 更新真实的系统资源占用率（不影响活动疲劳度）
        self.update_resources()

        # ✓ 活动疲劳度随时间自然累积（每个tick增加）
        # 做梦/休息后会重置
        self.activity_fatigue = min(1.0, self.activity_fatigue + 0.01 * dt)
        # P8-4: 同步到 FieldStore 的 fatigue（情感标量），保持两者数值一致
        self.fatigue = self.activity_fatigue

        # ✓ Stress 自然衰减（心理压力会随时间缓解）
        self.stress = max(0.0, self.stress - 0.01 * dt)

        # ✓ Boredom 随时间增加（不活动时会无聊）
        self.boredom = min(1.0, self.boredom + 0.005 * dt)

        # 更新资源压力指数 RP_t
        self._update_resource_pressure()

    def reset_activity_fatigue(self, amount: float = 1.0):
        """重置活动疲劳度（做梦/休息后调用）.

        Args:
            amount: 减少量，默认1.0（完全重置）
        """
        self.activity_fatigue = max(0.0, self.activity_fatigue - amount)
        # P8-4: 同步重置 FieldStore 的 fatigue
        self.fatigue = self.activity_fatigue

    def update_resources(self):
        """从真实系统更新资源占用率.

        使用 psutil 检测真实的 CPU 和内存占用率。
        如果 psutil 不可用，保持当前值不变。
        """
        if self.use_real_resources:
            real_resources = _get_real_system_resources()
            self.compute = real_resources["compute"]
            self.memory = real_resources["memory"]

    # 注意: consume/release 方法已移除
    # 真实系统资源不需要手动模拟消耗/释放
    # update_resources() 会自动从 psutil 获取当前占用率

    def _update_resource_pressure(self):
        """更新资源压力指数 RP_t.

        修正后语义:
        RP_t = α·Compute_t + β·Memory_t

        - 占用率越高，压力越大
        - 默认: α=0.6, β=0.4
        - 范围: [0, 1]，超过0.35为紧急状态
        """
        alpha = 0.6
        beta = 0.4
        # 占用率越高 = 资源压力越大
        self.resource_pressure = alpha * self.compute + beta * self.memory

    def get_effective_boredom(self) -> float:
        """获取有效无聊度.

        论文公式 (Section 3.6.4):
        effective_boredom_t = Boredom_t · 1[RP_t < θ_emergency]

        当资源紧急时 (RP_t >= 0.35)，返回 0。

        Returns:
            有效无聊度 [0, 1]
        """
        emergency_threshold = 0.35
        if self.resource_pressure >= emergency_threshold:
            return 0.0
        return self.boredom

    def is_emergency_state(self) -> bool:
        """判断是否处于资源紧急状态.

        当占用率过高时进入紧急状态:
        - compute > 50% 或 memory > 50% 时触发（大约）

        Returns:
            True 如果 RP_t >= θ_emergency (0.35)
        """
        return self.resource_pressure >= 0.35

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GlobalState':
        """Create GlobalState from dictionary.

        Args:
            data: Dictionary representation of state

        Returns:
            GlobalState instance
        """
        # Convert string keys back to ValueDimension enums
        weights = {}
        for k, v in data.get("weights", {}).items():
            try:
                weights[ValueDimension(k)] = v
            except (ValueError, KeyError):
                pass  # Skip invalid dimensions (兼容旧维度)

        gaps = {}
        for k, v in data.get("gaps", {}).items():
            try:
                gaps[ValueDimension(k)] = v
            except (ValueError, KeyError):
                pass

        setpoints = {}
        for k, v in data.get("setpoints", {}).items():
            try:
                setpoints[ValueDimension(k)] = v
            except (ValueError, KeyError):
                pass

        return cls(
            tick=data.get("tick", 0),
            # 数字原生字段（真实系统资源）
            compute=data.get("compute", 0.20),
            memory=data.get("memory", 0.15),
            use_real_resources=data.get("use_real_resources", True),
            # 活动疲劳度
            activity_fatigue=data.get("activity_fatigue", 0.0),
            # P8-4: 情感标量写入本地 fallback（from_dict 不注入 FieldStore；
            # 生产路径由 life_loop 注入 FieldStore 后这些值自动从 FieldStore 读）
            # P8-6: from_dict fallback 默认值与 dataclass 默认值对齐
            # （原 mood=0.5/stress=0.2/boredom=0.0 与 dataclass 的 0.0/0.15/0.30 不一致，
            # 导致部分序列化的 dict round-trip 后状态被静默改写）
            _mood_local=data.get("mood", 0.0),
            _stress_local=data.get("stress", 0.15),
            _boredom_local=data.get("boredom", 0.30),
            _energy_local=data.get("energy", 1.0 - data.get("activity_fatigue", 0.0)),
            _fatigue_local=data.get("fatigue", data.get("activity_fatigue", 0.0)),
            _bond_local=data.get("bond", data.get("relationship", 0.2)),
            _trust_local=data.get("trust", data.get("relationship", 0.2)),
            relationship=data.get("relationship", data.get("bond", 0.2)),
            arousal=data.get("arousal", 0.5),
            resource_pressure=data.get("resource_pressure", 0.0),
            # Working memory
            current_goal=data.get("current_goal", ""),
            current_plan=data.get("current_plan", ""),
            last_user_interaction=data.get("last_user_interaction", 0.0),
            # Value system
            value_pred=data.get("value_pred", 0.0),
            weights=weights,
            gaps=gaps,
            setpoints=setpoints,
            # Memory counters
            episodic_count=data.get("episodic_count", 0),
            schema_count=data.get("schema_count", 0),
            skill_count=data.get("skill_count", 0),
            # Resource ledger
            tokens_used=data.get("tokens_used", 0),
            io_ops=data.get("io_ops", 0),
            net_bytes=data.get("net_bytes", 0),
            money_spent=data.get("money_spent", 0.0),
            # Mode and stage
            mode=data.get("mode", "work"),
            stage=data.get("stage", "adult"),
            # Priority override
            override_active=set(data.get("override_active", [])),
            override_trigger_time=data.get("override_trigger_time", 0.0),
            gaps_at_trigger=data.get("gaps_at_trigger", {}),
            # Value learning
            value_learning_enabled=data.get("value_learning_enabled", True),
            last_value_learning_tick=data.get("last_value_learning_tick", 0),
            value_learning_interval=data.get("value_learning_interval", 50),
        )
