"""Tick Loop - 17-phase tick execution system.

Implements Paper Section 3.13: Algorithm 1 Genesis X Life Loop
Each tick executes 17 phases in sequence.

修复 v15: 使用5维核心价值向量 (论文 Section 3.5.1)
- HOMEOSTASIS: 稳态 - 资源平衡、压力管理、系统稳定
- ATTACHMENT: 依恋 - 社交连接、信任建立、忽视回避
- CURIOSITY: 好奇 - 新奇探索、信息增益、规律发现
- COMPETENCE: 胜任 - 任务成功、技能成长、效能感
- SAFETY: 安全 - 风险回避、损失预防、安全边际

删除的维度及其理由：
- 删除 INTEGRITY：作为硬约束而非价值维度 (论文 Section 3.5.1)
- 删除 CONTRACT：重定位为影响权重的外部输入
- 删除 EFFICIENCY：并入 HOMEOSTASIS (资源节约本质上是稳态维持)
- 删除 MEANING：并入 CURIOSITY (高阶规律学习是好奇的高级满足形式)
"""

from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timezone
from pathlib import Path
import uuid
import random
import math


class TickLoop:
    """17-phase tick loop for Genesis X.

    论文 Section 3.13 Algorithm 1 的实现。
    """

    # The 17 phases of each tick (论文 Section 3.13)
    PHASES = [
        # 1. Body Update: 更新生命体征
        "body_update",
        # 2. Observe: 收集观察
        "observe",
        # 3. Compute Middle Variables: 计算ET_t, CT_t, ES_t
        "compute_middle_vars",
        # 4. Compute Effective States: 计算effective_boredom_t
        "compute_effective_states",
        # 5. Retrieve: 记忆检索
        "retrieve",
        # 6. Axiology: 计算缺口和权重
        "axiology",
        # 7. Goal Compile: 生成并选择目标
        "goal_compile",
        # 8. Model Config Check: 检查是否需要切换模型配置
        "model_config_check",
        # 9. Plan Propose: 生成候选计划
        "plan_propose",
        # 10. Plan Evaluate: 评估计划
        "plan_evaluate",
        # 11. Execute: 执行选定的计划
        "execute",
        # 12. Reward/Affect Update: 计算奖励和RPE
        "reward_affect_update",
        # 13. Memory Write: 写入记忆
        "memory_write",
        # 14. Value Learn: 价值学习
        "value_learn",
        # 15. Soul Learn: 人格学习
        "soul_learn",
        # 16. Compress/Reflect Trigger: 检查是否需要巩固
        "consolidate_trigger",
        # 17. Persist: 持久化状态
        "persist",
    ]

    def __init__(self, config: Dict[str, Any]):
        """Initialize tick loop.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.tick = 0
        self.session_id = f"session_{uuid.uuid4().hex[:8]}"

        # Data directory
        self.data_dir = Path(config.get("data_dir", "artifacts"))
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # State
        self.state = self._init_state()

        # Phase execution tracking
        self.phase_results = {}

    # 论文 Section 3.2: 核心内部状态 (数字原生定义)
    # X_t = ⟨Compute_t, Memory_t, Mood_t, Stress_t, Relationship_t, Arousal_t, Boredom_t⟩
    # 采用算力/内存双资源模型，摒弃生物学隐喻的"能量/疲劳"概念

    # 论文 Section 3.5.1: 5维价值向量默认权重
    DEFAULT_WEIGHTS = {
        "homeostasis": 0.2,
        "attachment": 0.2,
        "curiosity": 0.2,
        "competence": 0.2,
        "safety": 0.2,
    }

    # 论文 Section 3.5.1: 价值维度设定点 (f^(i)*)
    VALUE_SETPOINTS = {
        "homeostasis": 0.85,
        "attachment": 0.70,
        "curiosity": 0.60,
        "competence": 0.75,
        "safety": 0.70,
    }

    def _init_state(self) -> Dict[str, Any]:
        """Initialize state dictionary.

        论文 Section 3.2 形式化定义:
        S_t = ⟨O_t, X_t, M_t, K_t, ω_t, θ_t, 𝕊_t⟩

        内部状态 X_t 采用数字原生模型：
        - Compute_t: 算力可用度 [0,1]
        - Memory_t: 内存可用度 [0,1]
        - Mood_t: 情绪愉快度 [-1,1]
        - Stress_t: 压力/负荷 [0,1]
        - Relationship_t: 关系强度 [0,1]
        - Arousal_t: 唤醒度 [0,1]
        - Boredom_t: 无聊度 [0,1]
        """
        return {
            # 基础信息
            "tick": 0,
            "session_id": self.session_id,
            "timestamp": None,

            # === 内部状态 X_t (数字原生) ===
            # 资源状态 (论文 Section 3.2)
            "compute": 0.8,      # 算力可用度
            "memory": 0.8,       # 内存可用度
            "stress": 0.2,       # 压力 [0,1]

            # 情绪状态 (论文 Section 3.7)
            "mood": 0.0,         # 愉快度 [-1,1]
            "arousal": 0.5,      # 唤醒度 [0,1]
            "boredom": 0.0,      # 无聊度 [0,1]

            # 关系状态 (论文 Section 3.5.2)
            "relationship": 0.5,  # 关系强度 [0,1]
            "neglect_time": 0.0, # 被忽视时间 (秒)

            # === 价值系统 ω_t ===
            # 5维价值权重 (论文 Section 3.5.1)
            "weights": self.DEFAULT_WEIGHTS.copy(),

            # 价值维度缺口 (论文 Section 3.6.1)
            "gaps": {
                "homeostasis": 0.0,
                "attachment": 0.0,
                "curiosity": 0.0,
                "competence": 0.0,
                "safety": 0.0,
            },

            # 价值维度特征 f^{(i)}(S_t) (论文 Section 3.5.2)
            "features": {
                "homeostasis": 0.8,
                "attachment": 0.5,
                "curiosity": 0.5,
                "competence": 0.5,
                "safety": 0.5,
            },

            # === 人格系统 θ_t (Soul Field) ===
            # 大五人格 (论文 Section 3.4.1)
            "personality": {
                "openness": 0.5,        # O_t: 开放性
                "conscientiousness": 0.5, # C_t: 尽责性
                "extraversion": 0.5,     # E_t: 外向性
                "agreeableness": 0.5,    # A_t: 宜人性
                "neuroticism": 0.5,      # N_t: 神经质
            },

            # 交互风格参数 (论文 Section 3.4.1)
            "interaction_style": {
                "initiative": 0.5,     # 主动性
                "expressiveness": 0.5,  # 表达性
                "humor": 0.5,          # 幽默感
                "formality": 0.5,      # 正式度
            },

            # === 中间变量 (论文 Section 3.4.1) ===
            "middle_vars": {
                "exploration_tendency": 0.5,  # ET_t: 探索倾向
                "conservation_tendency": 0.5, # CT_t: 保守倾向
                "emotional_sensitivity": 0.5,  # ES_t: 情绪敏感度
            },

            # === 抽象状态层 𝕊_t (论文 Section 3.4.2) ===
            "abstract_state": {
                "emo": None,   # 抽象情绪状态
                "goal": None,  # 抽象目标表示
                "mem": None,   # 抽象记忆指针
                "ctx": None,   # 抽象上下文摘要
            },

            # === Dream系统 (论文 Section 3.10.4) ===
            "dream_state": {
                "cooldown_ticks": 0,        # 冷却计数器
                "attempt_count": 0,         # 尝试计数器
                "consecutive_failures": 0,  # 连续失败计数
            },

            # === 模型配置 ===
            "model_config": "Single",  # 当前模型配置 (Single/Core5/Full7/Adaptive)
            "last_switch_tick": 0,     # 上次切换tick

            # === 其他 ===
            "observations": [],
            "retrieved_memories": [],
            "current_goal": None,
            "active_plan": None,
        }

    def run_tick(self, observations: List[Any] = None) -> Dict[str, Any]:
        """Execute one tick (all 17 phases).

        论文 Section 3.13 Algorithm 1 的完整实现。

        Args:
            observations: 外部观察输入 O_t

        Returns:
            Tick result with state and executed phases
        """
        self.tick += 1
        self.state["tick"] = self.tick
        self.state["timestamp"] = datetime.now(timezone.utc)

        if observations is not None:
            self.state["observations"] = observations

        executed_phases = []
        phase_errors = {}

        for phase in self.PHASES:
            try:
                result = self._execute_phase(phase)
                self.phase_results[phase] = result
                executed_phases.append(phase)
            except Exception as e:
                import traceback
                error_info = {"error": str(e), "traceback": traceback.format_exc()}
                self.phase_results[phase] = error_info
                phase_errors[phase] = error_info

        return {
            "tick": self.tick,
            "state": self.state.copy(),
            "phases": executed_phases,
            "errors": phase_errors,
        }

    def _execute_phase(self, phase: str) -> Dict[str, Any]:
        """Execute a single phase.

        论文 Section 3.13 Algorithm 1 各相位的具体实现。

        Args:
            phase: Phase name

        Returns:
            Phase result
        """
        # Phase 1: Body Update - 更新生命体征
        if phase == "body_update":
            return self._phase_body_update()

        # Phase 2: Observe - 收集观察 (已在 run_tick 中处理)
        elif phase == "observe":
            return {"observations": self.state.get("observations", [])}

        # Phase 3: Compute Middle Variables - 计算ET_t, CT_t, ES_t
        elif phase == "compute_middle_vars":
            return self._phase_compute_middle_vars()

        # Phase 4: Compute Effective States - 计算有效状态
        elif phase == "compute_effective_states":
            return self._phase_compute_effective_states()

        # Phase 5: Retrieve - 记忆检索
        elif phase == "retrieve":
            return self._phase_retrieve()

        # Phase 6: Axiology - 计算缺口和权重
        elif phase == "axiology":
            return self._phase_axiology()

        # Phase 7: Goal Compile - 生成并选择目标
        elif phase == "goal_compile":
            return self._phase_goal_compile()

        # Phase 8: Model Config Check - 检查模型配置
        elif phase == "model_config_check":
            return self._phase_model_config_check()

        # Phase 9: Plan Propose - 生成候选计划
        elif phase == "plan_propose":
            return self._phase_plan_propose()

        # Phase 10: Plan Evaluate - 评估计划
        elif phase == "plan_evaluate":
            return self._phase_plan_evaluate()

        # Phase 11: Execute - 执行计划
        elif phase == "execute":
            return self._phase_execute()

        # Phase 12: Reward/Affect Update - 计算奖励和RPE
        elif phase == "reward_affect_update":
            return self._phase_reward_affect_update()

        # Phase 13: Memory Write - 写入记忆
        elif phase == "memory_write":
            return self._phase_memory_write()

        # Phase 14: Value Learn - 价值学习
        elif phase == "value_learn":
            return self._phase_value_learn()

        # Phase 15: Soul Learn - 人格学习
        elif phase == "soul_learn":
            return self._phase_soul_learn()

        # Phase 16: Consolidate Trigger - 巩固触发检查
        elif phase == "consolidate_trigger":
            return self._phase_consolidate_trigger()

        # Phase 17: Persist - 持久化
        elif phase == "persist":
            return self._phase_persist()

        else:
            return {"status": "unknown_phase", "phase": phase}

    # ==================== Phase 实现方法 ====================

    def _phase_body_update(self) -> Dict[str, Any]:
        """Phase 1: Body Update.

        论文 Section 3.13 Step 1:
        更新 Compute_t, Memory_t, Mood_t, Stress_t, Relationship_t, Arousal_t, Boredom_t
        (Mood/Stress 带衰减)
        """
        state = self.state

        # 情绪衰减 (论文 Section 3.7.3)
        decay = 0.99  # 每个tick衰减1%
        state["mood"] = decay * state["mood"]

        # 情绪更新将在 reward_affect_update 阶段基于RPE完成

        return {
            "compute": state["compute"],
            "memory": state["memory"],
            "mood": state["mood"],
            "stress": state["stress"],
            "arousal": state["arousal"],
            "boredom": state["boredom"],
        }

    def _phase_compute_middle_vars(self) -> Dict[str, Any]:
        """Phase 3: Compute Middle Variables.

        论文 Section 3.4.1:
        计算三个中间变量 ET_t, CT_t, ES_t
        """
        state = self.state
        p = state["personality"]

        # 探索倾向 ET_t = 0.4*O + 0.3*E + 0.3*(1-C)
        et = 0.4 * p["openness"] + 0.3 * p["extraversion"] + 0.3 * (1 - p["conscientiousness"])

        # 保守倾向 CT_t = 0.5*C + 0.3*N + 0.2*A
        ct = 0.5 * p["conscientiousness"] + 0.3 * p["neuroticism"] + 0.2 * p["agreeableness"]

        # 情绪敏感度 ES_t = 0.6*N + 0.2*O + 0.2*(1-C)
        es = 0.6 * p["neuroticism"] + 0.2 * p["openness"] + 0.2 * (1 - p["conscientiousness"])

        self.state["middle_vars"] = {
            "exploration_tendency": et,
            "conservation_tendency": ct,
            "emotional_sensitivity": es,
        }

        return self.state["middle_vars"]

    def _phase_compute_effective_states(self) -> Dict[str, Any]:
        """Phase 4: Compute Effective States.

        论文 Section 3.2:
        - Arousal 只依赖资源和刺激
        - 有效Boredom: effective_boredom_t = Boredom_t · 1[RP_t < θ_emergency]
        """
        state = self.state

        # 资源压力指数 RP_t
        alpha, beta = 0.6, 0.4
        rp = max(0, 1 - (alpha * state["compute"] + beta * state["memory"]))

        # 外部刺激强度 (简化实现)
        stimulus = min(1.0, len(state.get("observations", [])) * 0.2)

        # Arousal_t = σ*(1-RP_t) + (1-σ)*Stimulus_t
        sigma = 0.7
        state["arousal"] = sigma * (1 - rp) + (1 - sigma) * stimulus

        # 有效Boredom (资源优先级覆盖)
        theta_emergency = 0.85
        if rp >= theta_emergency:
            effective_boredom = 0.0  # 紧急模式抑制Boredom
        else:
            effective_boredom = state["boredom"]

        state["effective_boredom"] = effective_boredom
        state["resource_pressure"] = rp

        return {
            "arousal": state["arousal"],
            "effective_boredom": effective_boredom,
            "resource_pressure": rp,
        }

    def _phase_retrieve(self) -> Dict[str, Any]:
        """Phase 5: Retrieve.

        论文 Section 3.13 Step 5:
        使用情绪敏感度进行记忆检索

        TODO: 实现双阶段检索 (熟悉度 + 联想激活)
        """
        # 简化实现: 返回空检索结果
        retrieved = []
        self.state["retrieved_memories"] = retrieved
        return {"retrieved_count": len(retrieved)}

    def _phase_axiology(self) -> Dict[str, Any]:
        """Phase 6: Axiology.

        论文 Section 3.13 Step 6:
        计算缺口 d^(i)_t、加中间变量偏置、计算权重 w^(i)_t
        """
        state = self.state
        gaps = {}
        mv = state.get("middle_vars", {
            "exploration_tendency": 0.5,
            "conservation_tendency": 0.5,
            "emotional_sensitivity": 0.5,
        })

        # 计算各维度缺口
        for dim, setpoint in self.VALUE_SETPOINTS.items():
            feature = state["features"].get(dim, 0.5)
            gap = max(0, setpoint - feature)
            gaps[dim] = gap

        state["gaps"] = gaps

        # 人格偏置 (论文 Section 3.6.2)
        ct = mv["conservation_tendency"]
        lambda_i = 0.3  # 人格影响强度
        biased_gaps = {}
        for dim, gap in gaps.items():
            g_base = 1.0  # 基准敏感度
            g_i = g_base * (1 + lambda_i * (ct - 0.5))
            biased_gaps[dim] = gap * g_i

        # Softmax 归一化 (论文 Section 3.6.3)
        tau = 2.0  # 动机集中度
        exp_values = {dim: math.exp(tau * gap) for dim, gap in biased_gaps.items()}
        total = sum(exp_values.values())
        weights = {dim: val / total for dim, val in exp_values.items()}

        state["weights"] = weights

        return {
            "gaps": gaps,
            "biased_gaps": biased_gaps,
            "weights": weights,
        }

    def _phase_goal_compile(self) -> Dict[str, Any]:
        """Phase 7: Goal Compile.

        论文 Section 3.8.2:
        生成目标 (五源驱动)，按优先级排序，选择 g*
        """
        # 简化实现: 保持当前目标或生成默认目标
        current_goal = self.state.get("current_goal")

        if current_goal is None:
            # 根据最大缺口生成目标
            gaps = self.state.get("gaps", {})
            max_gap_dim = max(gaps.items(), key=lambda x: x[1])[0] if gaps else "homeostasis"

            goal_map = {
                "homeostasis": "rest_and_recover",
                "attachment": "strengthen_bond",
                "curiosity": "explore_and_learn",
                "competence": "improve_skills",
                "safety": "verify_and_correct",
            }

            current_goal = goal_map.get(max_gap_dim, "idle")
            self.state["current_goal"] = current_goal

        return {"current_goal": current_goal}

    def _phase_model_config_check(self) -> Dict[str, Any]:
        """Phase 8: Model Config Check.

        论文 Section 3.4.2:
        根据 ET_t, CT_t, RP_t 确定是否需要切换配置
        """
        state = self.state
        mv = state["middle_vars"]
        rp = state.get("resource_pressure", 0.0)

        et = mv["exploration_tendency"]
        ct = mv["conservation_tendency"]

        # 配置选择函数 (论文 Section 3.4.2)
        if et > 0.7 and rp < 0.4:
            new_config = "Full7"
        elif et >= 0.3 and rp < 0.7:
            new_config = "Core5"
        else:
            new_config = "Single"

        # 检查是否需要切换
        current_config = state.get("model_config", "Single")
        last_switch = state.get("last_switch_tick", 0)
        cooldown = 100  # 切换冷却期

        if new_config != current_config and (self.tick - last_switch) >= cooldown:
            state["model_config"] = new_config
            state["last_switch_tick"] = self.tick
            return {"switched": True, "new_config": new_config}

        return {"switched": False, "current_config": current_config}

    def _phase_plan_propose(self) -> Dict[str, Any]:
        """Phase 9: Plan Propose.

        论文 Section 3.9.1:
        由 Mind 生成候选计划集合 P_t
        """
        # 简化实现: 生成单个默认计划
        goal = self.state.get("current_goal", "idle")

        plan = {
            "actions": [{"type": "CHAT", "params": {"message": "Processing..."}}],
            "goal": goal,
            "estimated_reward": 0.5,
        }

        self.state["candidate_plans"] = [plan]
        return {"plan_count": 1}

    def _phase_plan_evaluate(self) -> Dict[str, Any]:
        """Phase 10: Plan Evaluate.

        论文 Section 3.9.2:
        估计每个计划 J(p|S_t)，过滤不可行
        """
        plans = self.state.get("candidate_plans", [])

        # 简化实现: 选择第一个计划
        selected = plans[0] if plans else None
        self.state["active_plan"] = selected

        return {"selected_plan": selected}

    def _phase_execute(self) -> Dict[str, Any]:
        """Phase 11: Execute.

        论文 Section 3.13 Step 12:
        执行 p* 的第一步 a_t
        """
        plan = self.state.get("active_plan")

        if plan and plan.get("actions"):
            action = plan["actions"][0]
            self.state["last_action"] = action
            return {"executed": True, "action": action}

        return {"executed": False, "action": None}

    def _phase_reward_affect_update(self) -> Dict[str, Any]:
        """Phase 12: Reward/Affect Update.

        论文 Section 3.13 Step 13:
        计算 r_t、δ_t，更新情绪 (带衰减)
        """
        # 简化实现: 使用默认奖励
        reward = 0.0
        delta = 0.0

        # 基于RPE更新Mood (论文 Section 3.7.3)
        # Mood_{t+1} = decay * Mood_t + sign(δ_t) * log(1 + k|δ_t|)
        k = 0.1
        decay = 0.99
        mood_delta = math.copysign(math.log(1 + k * abs(delta)), delta) if delta != 0 else 0

        self.state["mood"] = decay * self.state["mood"] + mood_delta
        self.state["last_reward"] = reward
        self.state["last_delta"] = delta

        return {
            "reward": reward,
            "delta": delta,
            "mood": self.state["mood"],
        }

    def _phase_memory_write(self) -> Dict[str, Any]:
        """Phase 13: Memory Write.

        论文 Section 3.13 Step 14:
        写入 episode (ES_t 调节情绪标签)，必要时固化 skill
        """
        # 简化实现: 不实际写入
        return {"written": False}

    def _phase_value_learn(self) -> Dict[str, Any]:
        """Phase 14: Value Learn.

        论文 Section 3.13 Step 15:
        根据反馈类型选择 ε_ω(t) 更新 ω
        """
        # 简化实现: 不实际更新
        return {"updated": False}

    def _phase_soul_learn(self) -> Dict[str, Any]:
        """Phase 15: Soul Learn.

        论文 Section 3.13 Step 16:
        根据事件类型选择 ε_θ(t) 更新 θ
        """
        # 简化实现: 不实际更新
        return {"updated": False}

    def _phase_consolidate_trigger(self) -> Dict[str, Any]:
        """Phase 16: Consolidate Trigger.

        论文 Section 3.13 Step 17:
        检查人格调节的触发条件 → 进入 Dream–Reflect–Insight
        """
        state = self.state
        dream = state.get("dream_state", {})

        # 检查冷却和尝试限制
        if dream.get("cooldown_ticks", 0) > 0:
            dream["cooldown_ticks"] -= 1
            return {"triggered": False, "reason": "cooldown"}

        if dream.get("attempt_count", 0) >= 3:
            return {"triggered": False, "reason": "max_attempts"}

        # 检查触发条件 (论文 Section 3.10.4)
        rp = state.get("resource_pressure", 0.0)
        mv = state.get("middle_vars", {})

        # 资源压力触发 或 好奇心缺口触发
        trigger = (rp > 0.75) or (state.get("gaps", {}).get("curiosity", 0) > 0.4)

        if trigger:
            dream["cooldown_ticks"] = 30
            dream["attempt_count"] += 1
            return {"triggered": True}

        return {"triggered": False}

    def _phase_persist(self) -> Dict[str, Any]:
        """Phase 17: Persist.

        持久化状态到存储
        """
        # 简化实现: 不实际持久化
        return {"persisted": False}

    def run(self, max_ticks: int = 100):
        """Run multiple ticks.

        Args:
            max_ticks: Maximum ticks to run
        """
        for _ in range(max_ticks):
            self.run_tick()

    def get_state(self) -> Dict[str, Any]:
        """Get current state.

        Returns:
            Current state dictionary
        """
        return self.state.copy()
