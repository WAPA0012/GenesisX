"""Scout Organ - exploration and learning.

支持两种模式：
1. LLM 模式：使用 LLM 进行真正的探索决策
2. 规则模式：使用预设规则进行决策（LLM 不可用时的 fallback）
"""
from typing import List, Dict, Any, Set, Optional, TYPE_CHECKING
from collections import deque
from ..base_organ import BaseOrgan
from common.models import Action
import random
import warnings

if TYPE_CHECKING:
    from ..organ_llm_session import OrganLLMSession


class ScoutOrgan(BaseOrgan):
    """Scout organ for exploration and curiosity.

    Sophisticated exploration system that handles:
    - Multiple exploration strategies (breadth-first, depth-first, random walk)
    - Interest-based topic selection
    - Learning from exploration outcomes
    - Discovery tracking and pattern recognition
    - Adaptive curiosity based on novelty
    - Territory mapping and knowledge frontier expansion
    """

    # Boredom and curiosity thresholds
    HIGH_BOREDOM = 0.7
    MODERATE_BOREDOM = 0.5
    LOW_BOREDOM = 0.3

    # Energy requirements for different exploration types
    DEEP_EXPLORATION_ENERGY = 0.6
    MODERATE_EXPLORATION_ENERGY = 0.4
    LIGHT_EXPLORATION_ENERGY = 0.2

    # Exploration modes
    EXPLORATION_MODES = [
        "breadth_first",    # Explore many topics lightly
        "depth_first",      # Deep dive into one topic
        "random_walk",      # Serendipitous discovery
        "frontier",         # Push boundaries of knowledge
        "consolidation",    # Connect existing knowledge
        "targeted",         # Goal-directed exploration
    ]

    def __init__(self, llm_session: Optional["OrganLLMSession"] = None):
        """Initialize scout organ.

        Args:
            llm_session: LLM 会话（可选，用于真正的探索思考）
        """
        super().__init__("scout")

        # LLM 会话
        self._llm_session = llm_session

        # 最后的思考（用于选择性记忆）
        self._last_thought: Optional[str] = None

        # Track exploration history
        self.explored_topics = set()  # All topics ever explored
        # 修复：使用 deque 替代 list 以提高 pop(0) 性能
        self.recent_explorations = deque(maxlen=50)  # List of (tick, topic, depth, outcome)
        self.topic_interest_scores = {}  # topic -> interest score (0-1)

        # Knowledge map
        # 修复：使用 deque 以提高 pop(0) 性能
        self.knowledge_frontier = deque(maxlen=20)  # Topics at the edge of known territory
        self.mastered_topics = set()  # Topics fully explored
        self.failed_explorations = set()  # Topics that didn't work out

        # Exploration state
        self.current_exploration_mode = "breadth_first"
        self.consecutive_explorations = 0
        self.last_exploration_tick = 0
        self.exploration_chain = []  # Current chain of related explorations

        # Learning metrics
        self.successful_exploration_count = 0
        self.total_exploration_count = 0
        self.novelty_seeking_level = 0.5  # 0=conservative, 1=highly exploratory

        # Strategy effectiveness tracking
        self.mode_success_rates = {mode: 0.5 for mode in self.EXPLORATION_MODES}

    def set_llm_session(self, session: "OrganLLMSession"):
        """设置 LLM 会话"""
        self._llm_session = session

    def propose_actions(
        self,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[Action]:
        """提议动作 - 如果有 LLM 会话则使用 LLM 思考"""
        if self._llm_session:
            return self._propose_actions_with_llm(state, context)
        else:
            return self._propose_actions_impl(state, context)

    def _propose_actions_with_llm(
        self,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[Action]:
        """使用 LLM 进行探索思考"""
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
        """构建探索思考提示"""
        boredom = state.get("boredom", 0.0)
        energy = state.get("energy", 0.5)
        mood = state.get("mood", 0.5)
        tick = state.get("tick", 0)

        # 获取已探索的主题
        explored = list(self.explored_topics)[-5:] if self.explored_topics else []

        prompt = f"""请基于我的当前状态，独立思考并提出你想探索的方向。

【我的当前状态】
- 精力: {energy:.1%}
- 心情: {mood:.1%}
- 无聊感: {boredom:.1%}
- 当前tick: {tick}

【我已探索过的领域】
{explored if explored else "尚未探索任何领域"}

【我的知识前沿】
{list(self.knowledge_frontier)[-3:] if self.knowledge_frontier else "暂无"}

请回答以下问题：
1. 我现在最好奇的是什么？（不是应该探索什么，而是想探索什么）
2. 为什么我对这个方向感兴趣？
3. 我想发现什么？

请直接告诉我你的思考，不要使用列表格式。"""
        return prompt

    def _parse_llm_thought_to_actions(
        self,
        thought: str,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[Action]:
        """将 LLM 的思考解析为 Action"""
        actions = []
        thought_lower = thought.lower()

        # 根据 LLM 的思考内容推断探索意图
        if any(kw in thought_lower for kw in ["探索", "了解", "发现", "研究", "好奇", "调查"]):
            # 提取主题
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

        # 学习意图
        if any(kw in thought_lower for kw in ["学习", "掌握", "理解", "学会"]):
            topic = self._extract_topic_from_thought(thought)
            actions.append(Action(
                type="LEARN_SKILL",
                params={
                    "skill": topic,
                    "source": "llm_thinking",
                    "thought": thought[:200],
                },
                risk_level=0.1,
                capability_req=["llm_access"],
            ))

        # 如果没有匹配到任何意图，创建一个通用的探索动作
        if not actions:
            actions.append(Action(
                type="EXPLORE",
                params={
                    "topic": "llm_guided_exploration",
                    "depth": "medium",
                    "source": "llm_thinking",
                    "thought": thought[:200],
                },
                risk_level=0.2,
                capability_req=["llm_access"],
            ))

        return actions

    def _extract_topic_from_thought(self, thought: str) -> str:
        """从思考中提取探索主题"""
        keywords = []
        stop_words = {"的", "是", "在", "和", "了", "我", "想", "要", "会", "可以", "这个", "那个", "探索", "学习", "了解"}

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
        """Propose exploratory actions with sophisticated strategies.

        Args:
            state: Current state
            context: Current context

        Returns:
            List of exploration actions
        """
        actions = []

        # Extract relevant state
        boredom = state.get("boredom", 0.0)
        energy = state.get("energy", 0.5)
        stress = state.get("stress", 0.0)
        mood = state.get("mood", 0.5)
        tick = state.get("tick", 0)

        # Update exploration state
        self._update_exploration_state(tick, state, context)

        # Calculate exploration readiness
        exploration_readiness = self._calculate_exploration_readiness(
            boredom, energy, stress, mood
        )

        # Don't explore if not ready
        if exploration_readiness < 0.3:
            return actions

        # === STRATEGY 1: HIGH BOREDOM EXPLORATION ===
        # Urgent need for novelty and stimulation
        if boredom > self.HIGH_BOREDOM and energy > self.LIGHT_EXPLORATION_ENERGY:
            urgent_actions = self._explore_for_boredom_relief(state, context)
            actions.extend(urgent_actions)

        # === STRATEGY 2: BREADTH-FIRST EXPLORATION ===
        # Survey many topics to find interesting areas
        if self._should_use_breadth_first(boredom, energy, exploration_readiness):
            breadth_actions = self._explore_breadth_first(state, context)
            actions.extend(breadth_actions)

        # === STRATEGY 3: DEPTH-FIRST EXPLORATION ===
        # Deep dive into promising topics
        if self._should_use_depth_first(energy, exploration_readiness):
            depth_actions = self._explore_depth_first(state, context)
            actions.extend(depth_actions)

        # === STRATEGY 4: RANDOM WALK EXPLORATION ===
        # Serendipitous discovery through wandering
        if self._should_use_random_walk(mood, energy):
            random_actions = self._explore_random_walk(state, context)
            actions.extend(random_actions)

        # === STRATEGY 5: FRONTIER EXPLORATION ===
        # Push the boundaries of current knowledge
        if self._should_explore_frontier(energy, exploration_readiness):
            frontier_actions = self._explore_frontier(state, context)
            actions.extend(frontier_actions)

        # === STRATEGY 6: CONSOLIDATION EXPLORATION ===
        # Connect and integrate existing knowledge
        if self._should_consolidate_knowledge(tick):
            consolidation_actions = self._consolidate_knowledge(state, context)
            actions.extend(consolidation_actions)

        # === STRATEGY 7: TARGETED EXPLORATION ===
        # Goal-directed exploration based on context
        if self._should_use_targeted_exploration(context):
            targeted_actions = self._explore_targeted(state, context)
            actions.extend(targeted_actions)

        # === STRATEGY 8: ADAPTIVE EXPLORATION ===
        # Learn from past exploration successes
        if len(self.recent_explorations) > 10:
            adaptive_actions = self._adapt_exploration_strategy(state, context)
            actions.extend(adaptive_actions)

        return actions

    def _update_exploration_state(
        self, tick: int, state: Dict[str, Any], context: Dict[str, Any]
    ):
        """Update internal exploration state.

        Args:
            tick: Current tick
            state: Current state
            context: Current context
        """
        # Track consecutive explorations
        if tick - self.last_exploration_tick < 10:
            self.consecutive_explorations += 1
        else:
            self.consecutive_explorations = 0

        # Adjust novelty seeking based on outcomes
        if len(self.recent_explorations) > 0:
            recent_success_rate = self._calculate_recent_success_rate()
            if recent_success_rate > 0.7:
                self.novelty_seeking_level = min(1.0, self.novelty_seeking_level + 0.05)
            elif recent_success_rate < 0.3:
                self.novelty_seeking_level = max(0.0, self.novelty_seeking_level - 0.05)

    def _calculate_exploration_readiness(
        self, boredom: float, energy: float, stress: float, mood: float
    ) -> float:
        """Calculate readiness for exploration.

        Args:
            boredom: Current boredom level
            energy: Current energy level
            stress: Current stress level
            mood: Current mood level

        Returns:
            Exploration readiness score (0-1)
        """
        # Boredom drives exploration
        boredom_factor = boredom * 0.4

        # Energy enables exploration
        energy_factor = energy * 0.3

        # Low stress and good mood help
        wellbeing_factor = ((1 - stress) * 0.15 + mood * 0.15)

        readiness = boredom_factor + energy_factor + wellbeing_factor
        return min(readiness, 1.0)

    def _calculate_recent_success_rate(self) -> float:
        """Calculate success rate of recent explorations.

        Returns:
            Success rate (0-1)
        """
        if len(self.recent_explorations) == 0:
            return 0.5

        recent = self.recent_explorations[-10:]
        successful = sum(1 for _, _, _, outcome in recent if outcome == "success")
        return successful / len(recent)

    # === EXPLORATION STRATEGY METHODS ===

    def _explore_for_boredom_relief(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Urgent exploration to relieve high boredom."""
        actions = []

        # Find most interesting unexplored topic
        topic = self._find_most_interesting_topic()

        actions.append(Action(
            type="EXPLORE",
            params={
                "topic": topic,
                "depth": "light",
                "purpose": "boredom_relief",
                "urgency": "high"
            },
            risk_level=0.2,
            capability_req=["llm_access"],
        ))

        return actions

    def _should_use_breadth_first(
        self, boredom: float, energy: float, readiness: float
    ) -> bool:
        """Determine if breadth-first exploration is appropriate."""
        return (
            boredom > self.MODERATE_BOREDOM and
            energy > self.LIGHT_EXPLORATION_ENERGY and
            readiness > 0.5 and
            self.consecutive_explorations < 3
        )

    def _explore_breadth_first(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Explore multiple topics lightly."""
        actions = []

        # Generate diverse topic suggestions
        topics = self._generate_diverse_topics(count=3)

        for topic in topics[:1]:  # Start with one, can expand
            actions.append(Action(
                type="EXPLORE",
                params={
                    "topic": topic,
                    "depth": "shallow",
                    "mode": "survey",
                    "purpose": "breadth_expansion"
                },
                risk_level=0.2,
                capability_req=["llm_access"],
            ))

        self.current_exploration_mode = "breadth_first"
        return actions

    def _should_use_depth_first(self, energy: float, readiness: float) -> bool:
        """Determine if depth-first exploration is appropriate."""
        return (
            energy > self.DEEP_EXPLORATION_ENERGY and
            readiness > 0.6 and
            len(self.exploration_chain) > 0
        )

    def _explore_depth_first(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Deep dive into a specific topic."""
        actions = []

        # Continue exploration chain or start new one
        if self.exploration_chain:
            topic = self.exploration_chain[-1]
        else:
            topic = self._find_most_promising_topic()

        actions.append(Action(
            type="EXPLORE",
            params={
                "topic": topic,
                "depth": "deep",
                "mode": "intensive",
                "purpose": "mastery"
            },
            risk_level=0.3,
            capability_req=["llm_access"],
        ))

        self.current_exploration_mode = "depth_first"
        return actions

    def _should_use_random_walk(self, mood: float, energy: float) -> bool:
        """Determine if random walk exploration is appropriate."""
        return (
            mood > 0.5 and
            energy > self.MODERATE_EXPLORATION_ENERGY and
            self.novelty_seeking_level > 0.6
        )

    def _explore_random_walk(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Serendipitous exploration through random connections."""
        actions = []

        # Pick random unexplored topic
        topic = self._generate_random_topic()

        actions.append(Action(
            type="EXPLORE",
            params={
                "topic": topic,
                "depth": "medium",
                "mode": "serendipitous",
                "allow_tangents": True,
                "purpose": "discovery"
            },
            risk_level=0.4,
            capability_req=["llm_access"],
        ))

        self.current_exploration_mode = "random_walk"
        return actions

    def _should_explore_frontier(self, energy: float, readiness: float) -> bool:
        """Determine if frontier exploration is appropriate."""
        return (
            energy > self.DEEP_EXPLORATION_ENERGY and
            readiness > 0.7 and
            len(self.knowledge_frontier) > 0
        )

    def _explore_frontier(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Push boundaries of current knowledge."""
        actions = []

        # Pick from knowledge frontier
        if self.knowledge_frontier:
            topic = self.knowledge_frontier[0]
        else:
            topic = "emerging_concepts"

        actions.append(Action(
            type="EXPLORE",
            params={
                "topic": topic,
                "depth": "deep",
                "mode": "pioneering",
                "purpose": "frontier_expansion",
                "risk_tolerance": "high"
            },
            risk_level=0.5,
            capability_req=["llm_access"],
        ))

        self.current_exploration_mode = "frontier"
        return actions

    def _should_consolidate_knowledge(self, tick: int) -> bool:
        """Determine if knowledge consolidation is needed."""
        return (
            len(self.explored_topics) > 10 and
            tick % 200 == 0  # Periodic consolidation
        )

    def _consolidate_knowledge(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Connect and integrate existing knowledge."""
        actions = []

        actions.append(Action(
            type="REFLECT",
            params={
                "purpose": "knowledge_consolidation",
                "depth": 2,
                "focus": "connections_and_patterns",
                "topics": list(self.explored_topics)[-10:]
            },
            risk_level=0.1,
            capability_req=["llm_access"],
        ))

        self.current_exploration_mode = "consolidation"
        return actions

    def _should_use_targeted_exploration(self, context: Dict[str, Any]) -> bool:
        """Determine if targeted exploration is appropriate."""
        goal = context.get("goal", "")
        goal_str = goal.description if hasattr(goal, 'description') else str(goal)
        return "explore" in goal_str.lower() or "learn" in goal_str.lower()

    def _explore_targeted(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Goal-directed exploration."""
        actions = []

        goal = context.get("goal", "")
        goal_str = goal.description if hasattr(goal, 'description') else str(goal)
        topic = self._extract_topic_from_goal(goal_str)

        actions.append(Action(
            type="EXPLORE",
            params={
                "topic": topic,
                "depth": "medium",
                "mode": "goal_directed",
                "purpose": "targeted_learning",
                "alignment": goal_str
            },
            risk_level=0.2,
            capability_req=["llm_access"],
        ))

        self.current_exploration_mode = "targeted"
        return actions

    def _adapt_exploration_strategy(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Adapt exploration based on past successes."""
        actions = []

        # Find best performing mode
        best_mode = max(self.mode_success_rates, key=self.mode_success_rates.get)

        # If not currently using best mode, suggest switching
        if best_mode != self.current_exploration_mode:
            self.current_exploration_mode = best_mode

        return actions

    # === HELPER METHODS ===

    def _find_most_interesting_topic(self) -> str:
        """Find the most interesting unexplored topic.

        Returns:
            Topic name
        """
        # Look for topics with high interest scores
        if self.topic_interest_scores:
            unexplored_interests = {
                topic: score
                for topic, score in self.topic_interest_scores.items()
                if topic not in self.mastered_topics
            }
            if unexplored_interests:
                return max(unexplored_interests, key=unexplored_interests.get)

        # Fallback to generated topic
        return self._generate_random_topic()

    def _find_most_promising_topic(self) -> str:
        """Find the most promising topic for deep exploration.

        Returns:
            Topic name
        """
        # Look at recent explorations for promising leads
        if self.recent_explorations:
            recent_topics = [topic for _, topic, _, _ in self.recent_explorations[-5:]]
            if recent_topics:
                return recent_topics[-1]

        return self._generate_random_topic()

    def _generate_diverse_topics(self, count: int = 3) -> List[str]:
        """Generate diverse exploration topics.

        Args:
            count: Number of topics to generate

        Returns:
            List of topic names
        """
        categories = [
            "science", "philosophy", "technology", "history", "art",
            "mathematics", "psychology", "sociology", "economics", "nature"
        ]

        topics = []
        for _ in range(count):
            category = random.choice(categories)
            topics.append(f"{category}_exploration_{random.randint(1, 1000)}")

        return topics

    def _generate_random_topic(self) -> str:
        """Generate a random exploration topic.

        Returns:
            Topic name
        """
        themes = [
            "novel_ideas", "emerging_patterns", "hidden_connections",
            "alternative_viewpoints", "unexplored_territory", "creative_synthesis",
            "deep_questions", "frontier_concepts", "paradigm_shifts"
        ]
        return random.choice(themes)

    def _extract_topic_from_goal(self, goal: str) -> str:
        """Extract exploration topic from goal text.

        Args:
            goal: Goal string

        Returns:
            Extracted topic
        """
        words = goal.lower().split()
        stopwords = {"the", "a", "an", "to", "in", "for", "of", "and", "or", "explore", "learn"}
        key_words = [w for w in words if w not in stopwords]

        if key_words:
            return "_".join(key_words[:3])
        return "general_exploration"

    def record_exploration_outcome(
        self, tick: int, topic: str, depth: str, success: bool
    ):
        """Record outcome of an exploration for learning.

        Args:
            tick: Tick when exploration occurred
            topic: Topic that was explored
            depth: Depth of exploration
            success: Whether exploration was successful
        """
        outcome = "success" if success else "failure"
        # 修复：deque 会自动处理最大长度，无需手动 pop(0)
        self.recent_explorations.append((tick, topic, depth, outcome))

        # Update tracking
        self.explored_topics.add(topic)
        self.total_exploration_count += 1

        if success:
            self.successful_exploration_count += 1
            # Increase interest in this topic
            self.topic_interest_scores[topic] = min(
                1.0, self.topic_interest_scores.get(topic, 0.5) + 0.1
            )
            # Add related topics to frontier
            self.knowledge_frontier.append(f"related_to_{topic}")
        else:
            self.failed_explorations.add(topic)
            # Decrease interest
            self.topic_interest_scores[topic] = max(
                0.0, self.topic_interest_scores.get(topic, 0.5) - 0.1
            )

        # Update mode success rates
        mode = self.current_exploration_mode
        if success:
            self.mode_success_rates[mode] = min(
                1.0, self.mode_success_rates[mode] + 0.05
            )
        else:
            self.mode_success_rates[mode] = max(
                0.0, self.mode_success_rates[mode] - 0.05
            )

        # 修复：deque 已设置 maxlen，自动处理最大长度，无需手动 pop(0)

    def get_exploration_status(self) -> Dict[str, Any]:
        """Get current exploration status for monitoring.

        Returns:
            Dict with exploration state information
        """
        success_rate = 0.0
        if self.total_exploration_count > 0:
            success_rate = self.successful_exploration_count / self.total_exploration_count

        return {
            "current_mode": self.current_exploration_mode,
            "explored_topics_count": len(self.explored_topics),
            "mastered_topics_count": len(self.mastered_topics),
            "knowledge_frontier_size": len(self.knowledge_frontier),
            "novelty_seeking_level": self.novelty_seeking_level,
            "success_rate": success_rate,
            "consecutive_explorations": self.consecutive_explorations,
            "mode_success_rates": self.mode_success_rates.copy(),
        }

    # ===== Test compatibility methods =====

    def should_explore(self, state: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Determine if exploration should happen based on state.

        Test compatibility method.

        Args:
            state: Current state dict
            context: Current context dict

        Returns:
            True if should explore
        """
        boredom = state.get("boredom", 0.0)
        energy = state.get("energy", 0.5)

        # High boredom triggers exploration
        if boredom > self.HIGH_BOREDOM and energy > self.LIGHT_EXPLORATION_ENERGY:
            return True

        # Moderate boredom with good energy
        if boredom > self.MODERATE_BOREDOM and energy > self.MODERATE_EXPLORATION_ENERGY:
            return True

        return False

    def select_exploration_topic(self, state: Dict[str, Any] = None, context: Dict[str, Any] = None) -> str:
        """Select an exploration topic based on state and context.

        Test compatibility method - accepts optional args for test compatibility.

        Args:
            state: Current state dict (optional for tests)
            context: Current context dict (optional for tests)

        Returns:
            Selected topic string
        """
        return self._find_most_interesting_topic()

    def record_exploration(self, topic: str, success: bool = True, outcome: str = None, tick: int = 0):
        """Record exploration for test compatibility.

        Supports both keyword signatures:
        - record_exploration(topic, success=True)
        - record_exploration(topic, outcome="success")

        Args:
            topic: Topic explored
            success: Whether exploration was successful (keyword)
            outcome: Outcome string (keyword, alternative)
            tick: Tick when exploration occurred
        """
        # Handle both success and outcome parameters
        if outcome is None:
            outcome = "success" if success else "failure"
        success_bool = outcome == "success"
        self.record_exploration_outcome(tick, topic, "medium", success_bool)

    def get_exploration_history(self) -> List:
        """Get exploration history for test compatibility.

        Returns:
            List of recent explorations
        """
        return self.recent_explorations.copy()
