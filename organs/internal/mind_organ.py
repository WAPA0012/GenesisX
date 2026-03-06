"""Mind Organ - handles planning and reasoning.

支持两种模式：
1. LLM 模式：使用 LLM 进行真正的思考和决策
2. 规则模式：使用预设规则进行决策（LLM 不可用时的 fallback）
"""
from typing import List, Dict, Any, Optional, Union, TYPE_CHECKING
from ..base_organ import BaseOrgan
from common.models import Action, Goal
import random

if TYPE_CHECKING:
    from ..organ_llm_session import OrganLLMSession


class MindOrgan(BaseOrgan):
    """Mind organ for planning and reasoning.

    Sophisticated cognitive system that handles:
    - Multi-strategy planning (strategic, tactical, reactive, exploratory)
    - Goal decomposition and milestone tracking
    - Reasoning complexity assessment
    - Cognitive load management
    - Learning from past plans
    - Adaptive decision-making based on context

    新功能 (v2.0):
    - 支持使用 LLM 进行真正的思考
    - 独立的 LLM 会话，与其他器官隔离
    """

    # Planning complexity thresholds
    SIMPLE_GOAL_WORDS = 5  # Goals with <= 5 words are simple
    COMPLEX_GOAL_WORDS = 15  # Goals with >= 15 words are complex

    def propose_actions(
        self,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[Action]:
        """Propose actions using sophisticated planning strategies.

        This is the main entry point called by the LifeLoop.

        Args:
            state: Current state
            context: Current context

        Returns:
            List of proposed actions
        """
        # 如果有 LLM 会话，优先使用 LLM 思考
        if self._llm_session:
            return self._propose_actions_with_llm(state, context)
        else:
            return self._propose_actions_impl(state, context)

    # Cognitive load thresholds
    HIGH_COGNITIVE_LOAD = 0.7
    MODERATE_COGNITIVE_LOAD = 0.4

    # Planning strategy weights
    STRATEGY_WEIGHTS = {
        "strategic": 0.3,    # Long-term, high-level planning
        "tactical": 0.25,    # Medium-term, specific steps
        "reactive": 0.15,    # Immediate responses
        "exploratory": 0.15, # Discovery and learning
        "reflective": 0.1,   # Meta-cognition
        "creative": 0.05,    # Novel approaches
    }

    def __init__(self, llm_session: Optional["OrganLLMSession"] = None):
        """Initialize mind organ.

        Args:
            llm_session: LLM 会话（可选，用于真正的思考）
        """
        super().__init__("mind")

        # LLM 会话
        self._llm_session = llm_session

        # 最后的思考（用于选择性记忆）
        self._last_thought: Optional[str] = None

        # Track planning history
        self.plan_history = []  # List of (tick, goal, strategy, outcome)
        self.goal_decompositions = {}  # goal -> [subgoals]
        self.strategy_success_rates = {k: 0.5 for k in self.STRATEGY_WEIGHTS.keys()}

        # Current cognitive state
        self.current_focus = None
        self.thinking_depth = 1  # 1=shallow, 5=deep
        self.last_planning_tick = 0
        self.consecutive_plans = 0

        # Learning mechanisms
        self.successful_patterns = []  # Store successful (context, strategy) pairs
        self.failed_patterns = []      # Store failed (context, strategy) pairs

        # Reasoning chains
        self.active_reasoning_chain = []
        self.max_chain_length = 10

    def set_llm_session(self, session: "OrganLLMSSession"):
        """设置 LLM 会话"""
        self._llm_session = session

    def _propose_actions_with_llm(
        self,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[Action]:
        """使用 LLM 进行思考并提议动作"""
        actions = []

        # 构建思考提示
        prompt = self._build_thinking_prompt(state, context)

        # 调用 LLM 思考
        thought = self._llm_session.think(prompt)

        if thought:
            # 保存最后的思考（用于选择性记忆）
            self._last_thought = thought

            # 解析 LLM 的思考结果为 Action
            actions = self._parse_llm_thought_to_actions(thought, state, context)

        # 如果 LLM 没有返回有效的动作，fallback 到规则模式
        if not actions:
            actions = self._propose_actions_impl(state, context)

        return actions

    def get_last_thought(self) -> Optional[str]:
        """获取最后的思考内容（用于选择性记忆）"""
        return self._last_thought

    def clear_last_thought(self):
        """清除最后的思考"""
        self._last_thought = None

    def _build_thinking_prompt(self, state: Dict[str, Any], context: Dict[str, Any]) -> str:
        """构建思考提示"""
        # 提取关键状态
        energy = state.get("energy", 0.5)
        mood = state.get("mood", 0.5)
        stress = state.get("stress", 0.0)
        boredom = state.get("boredom", 0.0)
        tick = state.get("tick", 0)

        goal = context.get("goal", "无明确目标")

        # 提取最近的价值缺口
        gaps = context.get("value_gaps", {})

        prompt = f"""请基于我的当前状态，独立思考并提出你认为最值得做的事。

【我的当前状态】
- 精力: {energy:.1%}
- 心情: {mood:.1%}
- 压力: {stress:.1%}
- 无聊感: {boredom:.1%}
- 当前tick: {tick}

【当前目标】
{goal}

【价值缺口】
{self._format_gaps(gaps)}

【我的最近关注】
{self.current_focus or "无"}

请回答以下问题：
1. 基于我的状态，我现在最想做什么？（不是应该做什么，而是想做什么）
2. 为什么我想做这件事？
3. 我打算怎么开始？

请直接告诉我你的思考，不要使用列表格式。"""
        return prompt

    def _format_gaps(self, gaps: Dict[str, float]) -> str:
        """格式化价值缺口"""
        if not gaps:
            return "无显著缺口"

        lines = []
        for dim, gap in sorted(gaps.items(), key=lambda x: -x[1])[:5]:
            if gap > 0.1:
                lines.append(f"- {dim}: 缺口 {gap:.1%}")
        return "\n".join(lines) if lines else "无显著缺口"

    def _parse_llm_thought_to_actions(
        self,
        thought: str,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[Action]:
        """将 LLM 的思考解析为 Action"""
        actions = []
        thought_lower = thought.lower()

        # 检测用户响应需求
        if self._should_respond_to_user(state, context):
            actions.extend(self._generate_user_response(state, context))

        # 根据 LLM 的思考内容推断意图
        # 探索意图
        if any(kw in thought_lower for kw in ["探索", "了解", "学习", "研究", "发现", "好奇"]):
            topic = self._extract_topic_from_thought(thought)
            actions.append(Action(
                type="EXPLORE",
                params={
                    "topic": topic,
                    "depth": "medium",
                    "source": "llm_thinking",
                    "thought": thought[:200],
                },
                risk_level=0.2,
                capability_req=["llm_access"],
            ))

        # 反思意图
        if any(kw in thought_lower for kw in ["反思", "回顾", "思考", "分析", "理解"]):
            actions.append(Action(
                type="REFLECT",
                params={
                    "purpose": "self_initiated",
                    "depth": 2,
                    "source": "llm_thinking",
                    "thought": thought[:200],
                },
                risk_level=0.1,
                capability_req=[],
            ))

        # 构建意图
        if any(kw in thought_lower for kw in ["构建", "实现", "创建", "写代码", "生成"]):
            actions.append(Action(
                type="GROW",
                params={
                    "task": thought[:100],
                    "source": "llm_thinking",
                },
                risk_level=0.3,
                capability_req=["llm_access"],
            ))

        # 如果没有匹配到任何意图，创建一个通用的思考动作
        if not actions:
            actions.append(Action(
                type="THINK",
                params={
                    "thought": thought,
                    "source": "llm_thinking",
                },
                risk_level=0.0,
                capability_req=[],
            ))

        return actions

    def _extract_topic_from_thought(self, thought: str) -> str:
        """从思考中提取探索主题"""
        # 简单的关键词提取
        keywords = []
        stop_words = {"的", "是", "在", "和", "了", "我", "想", "要", "会", "可以", "这个", "那个"}

        words = thought.split()
        for word in words:
            if len(word) >= 2 and word not in stop_words:
                keywords.append(word)
                if len(keywords) >= 3:
                    break

        return "_".join(keywords) if keywords else "未知主题"

    def _propose_actions_impl(
        self,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[Action]:
        """Propose reasoning-based actions with sophisticated planning.

        Args:
            state: Current state
            context: Current context

        Returns:
            List of proposed actions, prioritized by strategy
        """
        actions = []

        # Extract relevant state
        goal = context.get("goal", "")
        tick = state.get("tick", 0)
        energy = state.get("energy", 0.5)
        stress = state.get("stress", 0.0)
        mood = state.get("mood", 0.5)
        boredom = state.get("boredom", 0.0)

        # Calculate cognitive load
        cognitive_load = self._calculate_cognitive_load(state, context)

        # Update internal state
        self._update_cognitive_state(tick, goal, cognitive_load)

        # === STRATEGY 1: USER INPUT RESPONSE (最高优先级) ===
        # 如果有用户输入，优先生成聊天回复
        if self._should_respond_to_user(state, context):
            user_actions = self._generate_user_response(state, context)
            actions.extend(user_actions)

        # === STRATEGY 2: STRATEGIC PLANNING ===
        # Long-term, goal-oriented planning when conditions are favorable
        if self._should_use_strategic_planning(energy, stress, cognitive_load, goal):
            strategic_actions = self._plan_strategically(goal, state, context)
            actions.extend(strategic_actions)

        # === STRATEGY 3: TACTICAL PLANNING ===
        # Medium-term planning with specific actionable steps
        if self._should_use_tactical_planning(energy, cognitive_load, goal):
            tactical_actions = self._plan_tactically(goal, state, context)
            actions.extend(tactical_actions)

        # === STRATEGY 4: REACTIVE PLANNING ===
        # Quick responses to immediate conditions
        if self._should_use_reactive_planning(stress, energy, cognitive_load):
            reactive_actions = self._plan_reactively(state, context)
            actions.extend(reactive_actions)

        # === STRATEGY 5: EXPLORATORY PLANNING ===
        # Discovery-oriented when bored or stuck
        if self._should_use_exploratory_planning(boredom, energy, cognitive_load):
            exploratory_actions = self._plan_exploratively(state, context)
            actions.extend(exploratory_actions)

        # === STRATEGY 6: REFLECTIVE PLANNING ===
        # Meta-cognitive review and learning
        if self._should_use_reflective_planning(tick, cognitive_load):
            reflective_actions = self._plan_reflectively(state, context)
            actions.extend(reflective_actions)

        # === STRATEGY 7: CREATIVE PLANNING ===
        # Novel approaches when traditional methods aren't working
        if self._should_use_creative_planning(state, context):
            creative_actions = self._plan_creatively(state, context)
            actions.extend(creative_actions)

        # === STRATEGY 8: GOAL DECOMPOSITION ===
        # Break down complex goals into manageable pieces
        if self._should_decompose_goal(goal):
            decomposition_actions = self._decompose_goal(goal, state, context)
            actions.extend(decomposition_actions)

        # === STRATEGY 9: ADAPTIVE PLANNING ===
        # Learn from past successes and failures
        if len(self.plan_history) > 10:
            adaptive_actions = self._adapt_from_history(state, context)
            actions.extend(adaptive_actions)

        # Update last_planning_tick AFTER all strategy checks
        # so _should_use_reflective_planning can detect time gaps
        self.last_planning_tick = tick

        return actions

    def _calculate_cognitive_load(self, state: Dict[str, Any], context: Dict[str, Any]) -> float:
        """Calculate current cognitive load based on multiple factors.

        Args:
            state: Current state
            context: Current context

        Returns:
            Cognitive load (0.0-1.0)
        """
        # Base load from fatigue and stress
        fatigue = state.get("fatigue", 0.0)
        stress = state.get("stress", 0.0)
        base_load = (fatigue * 0.4 + stress * 0.6)

        # Add complexity from active reasoning chains
        chain_load = min(len(self.active_reasoning_chain) / self.max_chain_length, 1.0) * 0.3

        # Add load from consecutive planning
        consecutive_load = min(self.consecutive_plans / 10, 1.0) * 0.2

        total_load = min(base_load + chain_load + consecutive_load, 1.0)
        return total_load

    def _update_cognitive_state(self, tick: int, goal: Union[Goal, str, None], cognitive_load: float):
        """Update internal cognitive state.

        Args:
            tick: Current tick
            goal: Current goal (can be Goal object or string)
            cognitive_load: Current cognitive load
        """
        # Convert Goal object to string for comparison
        goal_str = self._goal_to_string(goal)

        # Update focus
        if goal_str != self.current_focus:
            self.current_focus = goal_str
            self.consecutive_plans = 0
        else:
            self.consecutive_plans += 1

        # Adjust thinking depth based on cognitive load
        if cognitive_load > self.HIGH_COGNITIVE_LOAD:
            self.thinking_depth = max(1, self.thinking_depth - 1)
        elif cognitive_load < self.MODERATE_COGNITIVE_LOAD:
            self.thinking_depth = min(5, self.thinking_depth + 1)

        # Note: last_planning_tick is updated AFTER propose_actions checks,
        # not here, so that _should_use_reflective_planning can detect
        # time gaps correctly.

    def _goal_to_string(self, goal: Union[Goal, str, None]) -> str:
        """Convert Goal object or string to string.

        Args:
            goal: Goal object or string

        Returns:
            String representation
        """
        if goal is not None and hasattr(goal, 'description'):
            return goal.description
        elif goal is not None:
            return str(goal)
        else:
            return "idle"

    # === PLANNING STRATEGY METHODS ===

    def _should_use_strategic_planning(
        self, energy: float, stress: float, cognitive_load: float, goal
    ) -> bool:
        """Determine if strategic planning is appropriate."""
        # Convert Goal object to string if needed
        goal_str = self._goal_to_string(goal)
        return (
            energy > 0.5 and
            stress < 0.6 and
            cognitive_load < self.HIGH_COGNITIVE_LOAD and
            len(goal_str) > 10 and
            self.thinking_depth >= 3
        )

    def _plan_strategically(
        self, goal, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Create strategic long-term plan."""
        actions = []

        # Convert Goal object to string if needed
        goal_str = self._goal_to_string(goal)

        # Analyze goal structure
        goal_complexity = self._assess_goal_complexity(goal_str)

        if goal_complexity == "complex":
            # Propose high-level strategic thinking
            actions.append(Action(
                type="REFLECT",
                params={
                    "purpose": "strategic_planning",
                    "depth": 3,
                    "goal": goal_str,
                    "planning_horizon": "long_term",
                    "focus_areas": ["goals", "milestones", "dependencies"]
                },
                risk_level=0.1,
                capability_req=["llm_access"],
            ))

        return actions

    def _should_use_tactical_planning(
        self, energy: float, cognitive_load: float, goal
    ) -> bool:
        """Determine if tactical planning is appropriate."""
        # Convert Goal object to string if needed
        goal_str = self._goal_to_string(goal)
        return (
            energy > 0.3 and
            cognitive_load < self.HIGH_COGNITIVE_LOAD and
            len(goal_str) > 0
        )

    def _plan_tactically(
        self, goal, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Plan tactically with medium-term actionable steps."""
        # Convert Goal object to string if needed
        goal_str = self._goal_to_string(goal)
        actions = []

        if goal_str and "learn" in goal_str.lower():
            actions.append(Action(
                type="LEARN_SKILL",
                params={
                    "skill": self._extract_skill_from_goal(goal_str),
                    "practice_rounds": 3,
                    "approach": "tactical"
                },
                risk_level=0.1,
                capability_req=["llm_access"],
            ))
        elif goal_str and "explore" in goal_str.lower():
            actions.append(Action(
                type="EXPLORE",
                params={
                    "topic": self._extract_topic_from_goal(goal_str),
                    "depth": "medium",
                    "approach": "systematic"
                },
                risk_level=0.2,
                capability_req=["llm_access"],
            ))

        return actions

    def _should_use_reactive_planning(
        self, stress: float, energy: float, cognitive_load: float
    ) -> bool:
        """Determine if reactive planning is appropriate."""
        return (
            stress > 0.5 or
            energy < 0.3 or
            cognitive_load > self.HIGH_COGNITIVE_LOAD
        )

    def _plan_reactively(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Create quick reactive responses."""
        actions = []

        stress = state.get("stress", 0.0)
        energy = state.get("energy", 0.5)

        # React to high stress
        if stress > 0.6:
            actions.append(Action(
                type="REFLECT",
                params={
                    "purpose": "quick_assessment",
                    "depth": 1,
                    "focus": "immediate_concerns"
                },
                risk_level=0.0,
                capability_req=[],
            ))

        # React to low energy
        elif energy < 0.3:
            # Suggest low-cognitive-load activities
            actions.append(Action(
                type="EXPLORE",
                params={
                    "topic": "light_reading",
                    "depth": "shallow",
                    "cognitive_load": "low"
                },
                risk_level=0.1,
                capability_req=["llm_access"],
            ))

        return actions

    def _should_use_exploratory_planning(
        self, boredom: float, energy: float, cognitive_load: float
    ) -> bool:
        """Determine if exploratory planning is appropriate."""
        return (
            boredom > 0.5 and
            energy > 0.4 and
            cognitive_load < self.MODERATE_COGNITIVE_LOAD
        )

    def _plan_exploratively(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Create exploratory discovery plan."""
        actions = []

        # Choose random exploration topic
        topics = [
            "new_concepts", "uncharted_territory", "novel_connections",
            "alternative_perspectives", "creative_synthesis"
        ]
        topic = random.choice(topics)

        actions.append(Action(
            type="EXPLORE",
            params={
                "topic": topic,
                "depth": "variable",
                "purpose": "discovery",
                "allow_tangents": True
            },
            risk_level=0.3,
            capability_req=["llm_access"],
        ))

        return actions

    def _should_use_reflective_planning(
        self, tick: int, cognitive_load: float
    ) -> bool:
        """Determine if reflective planning is appropriate."""
        ticks_since_last = tick - self.last_planning_tick
        return (
            ticks_since_last > 100 and
            cognitive_load < self.HIGH_COGNITIVE_LOAD and
            len(self.plan_history) > 5
        )

    def _plan_reflectively(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Create reflective meta-cognitive plan."""
        actions = []

        # Review recent planning success
        if len(self.plan_history) > 0:
            actions.append(Action(
                type="REFLECT",
                params={
                    "purpose": "meta_cognition",
                    "depth": 2,
                    "focus": "planning_effectiveness",
                    "review_history": True
                },
                risk_level=0.0,
                capability_req=[],
            ))

        return actions

    def _should_use_creative_planning(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> bool:
        """Determine if creative planning is appropriate."""
        # Use creative planning if stuck (same goal for many ticks)
        return (
            self.consecutive_plans > 15 and
            state.get("energy", 0.5) > 0.4 and
            state.get("mood", 0.5) > 0.3
        )

    def _plan_creatively(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Create creative novel approaches."""
        actions = []

        goal = context.get("goal", "")
        goal_str = self._goal_to_string(goal)

        # Try unconventional approach
        actions.append(Action(
            type="EXPLORE",
            params={
                "topic": f"creative_approach_to_{goal_str[:20]}",
                "depth": "deep",
                "mode": "lateral_thinking",
                "constraints": "minimal"
            },
            risk_level=0.4,
            capability_req=["llm_access"],
        ))

        return actions

    def _should_decompose_goal(self, goal: Union[Goal, str, None]) -> bool:
        """Determine if goal should be decomposed."""
        goal_str = self._goal_to_string(goal)
        complexity = self._assess_goal_complexity(goal_str)
        return complexity == "complex" and goal_str not in self.goal_decompositions

    def _decompose_goal(
        self, goal, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Decompose complex goal into subgoals."""
        goal_str = self._goal_to_string(goal)
        actions = []

        # Create decomposition action
        actions.append(Action(
            type="REFLECT",
            params={
                "purpose": "goal_decomposition",
                "depth": 2,
                "goal": goal_str,
                "output": "subgoal_list"
            },
            risk_level=0.1,
            capability_req=["llm_access"],
        ))

        # Mark as decomposed
        self.goal_decompositions[goal_str] = []

        return actions

    def _adapt_from_history(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Adapt planning based on historical success."""
        actions = []

        # Analyze which strategies have been most successful
        best_strategy = self._get_best_strategy()

        # If current approach isn't the best, suggest switching
        if best_strategy and best_strategy != "strategic":
            actions.append(Action(
                type="REFLECT",
                params={
                    "purpose": "strategy_adaptation",
                    "depth": 1,
                    "recommended_strategy": best_strategy,
                    "reason": "historical_success"
                },
                risk_level=0.0,
                capability_req=[],
            ))

        return actions

    # === HELPER METHODS ===

    def _assess_goal_complexity(self, goal: str) -> str:
        """Assess complexity of a goal.

        Args:
            goal: Goal string

        Returns:
            Complexity level: "simple", "moderate", or "complex"
        """
        if not goal:
            return "simple"

        word_count = len(goal.split())

        if word_count <= self.SIMPLE_GOAL_WORDS:
            return "simple"
        elif word_count >= self.COMPLEX_GOAL_WORDS:
            return "complex"
        else:
            return "moderate"

    def _extract_skill_from_goal(self, goal: str) -> str:
        """Extract skill to learn from goal text."""
        # Simple keyword extraction
        skills = ["problem_solving", "creativity", "analysis", "communication", "reasoning"]

        for skill in skills:
            if skill.replace("_", " ") in goal.lower():
                return skill

        return "general_learning"

    def _extract_topic_from_goal(self, goal: str) -> str:
        """Extract exploration topic from goal text."""
        # Remove common words and extract key terms
        words = goal.lower().split()
        stopwords = {"the", "a", "an", "to", "in", "for", "of", "and", "or"}
        key_words = [w for w in words if w not in stopwords]

        if key_words:
            return "_".join(key_words[:3])
        return "general_knowledge"

    def _get_best_strategy(self) -> Optional[str]:
        """Get the most successful planning strategy from history.

        Returns:
            Name of best strategy, or None if insufficient data
        """
        if len(self.successful_patterns) < 5:
            return None

        # Count strategy occurrences in successful patterns
        strategy_counts = {}
        for context, strategy in self.successful_patterns[-20:]:
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1

        if strategy_counts:
            return max(strategy_counts, key=strategy_counts.get)
        return None

    def record_plan_outcome(
        self, tick: int, goal: str, strategy: str, success: bool
    ):
        """Record outcome of a planning action for learning.

        Args:
            tick: Tick when plan was executed
            goal: Goal that was being pursued
            strategy: Strategy that was used
            success: Whether the plan was successful
        """
        self.plan_history.append((tick, goal, strategy, success))

        # Keep history manageable
        if len(self.plan_history) > 100:
            self.plan_history.pop(0)

        # Update success rates
        if success:
            self.successful_patterns.append((goal, strategy))
            if len(self.successful_patterns) > 100:
                self.successful_patterns = self.successful_patterns[-100:]
            self.strategy_success_rates[strategy] = min(
                1.0, self.strategy_success_rates.get(strategy, 0.5) + 0.05
            )
        else:
            self.failed_patterns.append((goal, strategy))
            if len(self.failed_patterns) > 100:
                self.failed_patterns = self.failed_patterns[-100:]
            self.strategy_success_rates[strategy] = max(
                0.0, self.strategy_success_rates.get(strategy, 0.5) - 0.05
            )

    def get_cognitive_status(self) -> Dict[str, Any]:
        """Get current cognitive status for debugging/monitoring.

        Returns:
            Dict with cognitive state information
        """
        return {
            "current_focus": self.current_focus,
            "thinking_depth": self.thinking_depth,
            "consecutive_plans": self.consecutive_plans,
            "plan_history_size": len(self.plan_history),
            "active_reasoning_chain_length": len(self.active_reasoning_chain),
            "strategy_success_rates": self.strategy_success_rates.copy(),
            "decomposed_goals": list(self.goal_decompositions.keys()),
        }

    def _should_respond_to_user(self, state: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Check if should respond to user input."""
        # 检查 context 中是否有用户输入观察
        if "observations" in context:
            for obs in context.get("observations", []):
                if hasattr(obs, 'type') and obs.type == "user_chat":
                    return True
        return False

    def _generate_user_response(self, state: Dict[str, Any], context: Dict[str, Any]) -> List[Action]:
        """Generate chat response to user input."""

        # 提取用户消息
        user_message = ""
        if "observations" in context:
            for obs in context.get("observations", []):
                if hasattr(obs, 'type') and obs.type == "user_chat":
                    if hasattr(obs, 'payload'):
                        user_message = obs.payload.get("message", "")
                    break

        # 生成 CHAT 动作
        action = Action(
            type="CHAT",
            params={
                "message": "",  # 消息将由 chat.py 生成
                "user_message": user_message,
                "mood": state.get("mood", 0.5),
                "bond": state.get("bond", 0.0),
                "goal": context.get("goal", "")
            },
            risk_level=0.0,
            capability_req=[],  # CHAT 不需要特殊能力
        )

        return [action]
