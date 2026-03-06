"""Caretaker Organ - homeostasis and health maintenance.

支持两种模式：
1. LLM 模式：使用 LLM 进行真正的照护决策
2. 规则模式：使用预设规则进行决策（LLM 不可用时的 fallback）
"""
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from ..base_organ import BaseOrgan
from common.models import Action

if TYPE_CHECKING:
    from ..organ_llm_session import OrganLLMSession


class CaretakerOrgan(BaseOrgan):
    """Caretaker organ for maintaining homeostasis.

    Monitors energy, fatigue, stress, and proposes recovery actions.
    Highest priority - can override other organs in emergencies.

    Implements sophisticated health management:
    - Multi-level urgency system (critical/high/medium/low)
    - Preventive health measures
    - Recovery strategies based on state
    - Circadian rhythm awareness
    - Stress management protocols
    """

    # Thresholds for different urgency levels
    CRITICAL_ENERGY = 0.15
    LOW_ENERGY = 0.30
    MODERATE_ENERGY = 0.50

    CRITICAL_FATIGUE = 0.85
    HIGH_FATIGUE = 0.70
    MODERATE_FATIGUE = 0.50

    CRITICAL_STRESS = 0.85
    HIGH_STRESS = 0.70
    MODERATE_STRESS = 0.50

    HIGH_BOREDOM = 0.70
    MODERATE_BOREDOM = 0.50

    def __init__(self, llm_session: Optional["OrganLLMSession"] = None):
        """Initialize caretaker organ.

        Args:
            llm_session: LLM 会话（可选，用于真正的照护思考）
        """
        super().__init__("caretaker")

        # LLM 会话
        self._llm_session = llm_session

        # 最后的思考（用于选择性记忆）
        self._last_thought: Optional[str] = None

        # Track health history for pattern detection
        self.energy_history = []
        self.stress_history = []
        self.last_sleep_tick = 0
        self.last_break_tick = 0

        # Sleep schedule (hours since midnight)
        self.preferred_sleep_start = 22  # 10 PM
        self.preferred_sleep_end = 7     # 7 AM

        # Health state tracking (for test compatibility)
        self._health_state = {}

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
        """使用 LLM 进行照护思考"""
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
        """构建照护思考提示"""
        energy = state.get("energy", 0.5)
        stress = state.get("stress", 0.0)
        fatigue = state.get("fatigue", 0.0)
        boredom = state.get("boredom", 0.0)
        mood = state.get("mood", 0.5)
        tick = state.get("tick", 0)

        # 获取健康状态
        health = self.assess_health_status(state)

        prompt = f"""请基于我的当前状态，独立思考并提出你认为需要关注或维护的方面。

【我的当前状态】
- 精力: {energy:.1%}
- 压力: {stress:.1%}
- 疲劳: {fatigue:.1%}
- 无聊感: {boredom:.1%}
- 心情: {mood:.1%}
- 当前tick: {tick}

【健康评估】
- 健康分数: {health['health_score']:.1%}
- 状态: {health['status']}
- 问题: {health['issues'] if health['issues'] else '无'}

请回答以下问题：
1. 我现在最需要关注的是什么？（不是应该做什么，而是感觉需要什么）
2. 为什么我认为这很重要？
3. 我建议采取什么措施？

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
        energy = state.get("energy", 0.5)
        stress = state.get("stress", 0.0)
        fatigue = state.get("fatigue", 0.0)

        # 紧急情况处理
        if energy < self.CRITICAL_ENERGY or fatigue > self.CRITICAL_FATIGUE:
            actions.append(Action(
                type="SLEEP",
                params={
                    "duration": 20,
                    "priority": "critical",
                    "reason": "critical_state",
                    "source": "llm_thinking",
                },
                risk_level=0.0,
                capability_req=[],
            ))
            return actions

        # 根据 LLM 的思考内容推断照护意图
        if any(kw in thought_lower for kw in ["休息", "睡眠", "放松", "恢复"]):
            actions.append(Action(
                type="SLEEP",
                params={
                    "duration": 10,
                    "priority": "medium",
                    "reason": "llm_suggested_rest",
                    "source": "llm_thinking",
                    "thought": thought[:200],
                },
                risk_level=0.0,
                capability_req=[],
            ))

        if any(kw in thought_lower for kw in ["反思", "调整", "缓解", "减压"]):
            actions.append(Action(
                type="REFLECT",
                params={
                    "purpose": "stress_management",
                    "depth": 2,
                    "source": "llm_thinking",
                    "thought": thought[:200],
                },
                risk_level=0.0,
                capability_req=[],
            ))

        if any(kw in thought_lower for kw in ["探索", "活动", "刺激", "新鲜"]):
            actions.append(Action(
                type="EXPLORE",
                params={
                    "topic": "relaxing_activity",
                    "depth": "light",
                    "purpose": "mental_health",
                    "source": "llm_thinking",
                },
                risk_level=0.1,
                capability_req=["llm_access"],
            ))

        # 如果没有匹配到任何意图但状态不好，创建休息动作
        if not actions and (stress > 0.5 or fatigue > 0.5):
            actions.append(Action(
                type="REFLECT",
                params={
                    "purpose": "self_care",
                    "depth": 1,
                    "source": "llm_thinking",
                    "thought": thought[:200],
                },
                risk_level=0.0,
                capability_req=[],
            ))

        return actions

    def _propose_actions_impl(
        self,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[Action]:
        """Propose homeostasis actions with sophisticated health management.

        Args:
            state: Current state
            context: Current context

        Returns:
            List of recovery/maintenance actions, ordered by urgency
        """
        actions = []

        # Get body fields
        energy = state.get("energy", 0.5)
        stress = state.get("stress", 0.0)
        fatigue = state.get("fatigue", 0.0)
        boredom = state.get("boredom", 0.0)
        mood = state.get("mood", 0.5)
        tick = state.get("tick", 0)

        # Update history
        self._update_history(energy, stress, tick)

        # Get current hour (approximate from tick)
        tick_duration = context.get("tick_duration", 10)  # seconds
        # Prevent division by zero
        if tick_duration <= 0:
            tick_duration = 10  # Default safe value
        hours_elapsed = (tick * tick_duration) / 3600
        current_hour = int(hours_elapsed % 24)

        # === CRITICAL INTERVENTIONS (highest priority) ===

        # 1. Critical energy depletion - emergency sleep
        if energy < self.CRITICAL_ENERGY:
            actions.append(Action(
                type="SLEEP",
                params={
                    "duration": 30,  # Extended sleep duration
                    "priority": "emergency",
                    "reason": "critical_energy_depletion"
                },
                risk_level=0.0,
                capability_req=[],
            ))
            self.last_sleep_tick = tick
            return actions  # Emergency: skip other checks

        # 2. Critical fatigue - must rest immediately
        if fatigue > self.CRITICAL_FATIGUE:
            actions.append(Action(
                type="SLEEP",
                params={
                    "duration": 20,
                    "priority": "critical",
                    "reason": "critical_fatigue"
                },
                risk_level=0.0,
                capability_req=[],
            ))
            self.last_sleep_tick = tick
            return actions  # Critical: skip other checks

        # 3. Critical stress - stress crisis intervention
        if stress > self.CRITICAL_STRESS:
            actions.append(Action(
                type="REFLECT",
                params={
                    "purpose": "stress_crisis_management",
                    "depth": 3,
                    "techniques": ["breathing", "grounding", "cognitive_reframe"]
                },
                risk_level=0.0,
                capability_req=[],
            ))
            return actions  # Crisis: skip other checks

        # === HIGH PRIORITY INTERVENTIONS ===

        # 4. High fatigue or low energy - recommend rest
        if fatigue > self.HIGH_FATIGUE or energy < self.LOW_ENERGY:
            # Check if it's appropriate sleep time
            if self._is_sleep_time(current_hour):
                actions.append(Action(
                    type="SLEEP",
                    params={
                        "duration": 15,
                        "priority": "high",
                        "reason": "scheduled_rest"
                    },
                    risk_level=0.0,
                    capability_req=[],
                ))
            else:
                # Short nap during day
                actions.append(Action(
                    type="SLEEP",
                    params={
                        "duration": 5,
                        "priority": "high",
                        "reason": "power_nap"
                    },
                    risk_level=0.0,
                    capability_req=[],
                ))

        # 5. High stress - active stress management
        if stress > self.HIGH_STRESS:
            actions.append(Action(
                type="REFLECT",
                params={
                    "purpose": "stress_management",
                    "depth": 2,
                    "techniques": ["mindfulness", "perspective_shift"]
                },
                risk_level=0.0,
                capability_req=[],
            ))

        # === PREVENTIVE MEASURES ===

        # 6. Detect declining energy trend - preventive rest
        if self._is_energy_declining() and energy < self.MODERATE_ENERGY:
            actions.append(Action(
                type="SLEEP",
                params={
                    "duration": 3,
                    "priority": "medium",
                    "reason": "preventive_rest"
                },
                risk_level=0.0,
                capability_req=[],
            ))

        # 7. Moderate stress + declining mood - relaxation break
        if stress > self.MODERATE_STRESS and mood < 0.4:
            ticks_since_break = tick - self.last_break_tick
            if ticks_since_break > 50:  # At least 50 ticks since last break
                actions.append(Action(
                    type="REFLECT",
                    params={
                        "purpose": "relaxation_break",
                        "depth": 1,
                        "duration": 2
                    },
                    risk_level=0.0,
                    capability_req=[],
                ))
                self.last_break_tick = tick

        # 8. High boredom + moderate energy - suggest engagement
        if boredom > self.HIGH_BOREDOM and energy > self.MODERATE_ENERGY:
            actions.append(Action(
                type="EXPLORE",
                params={
                    "topic": "novel_stimulation",
                    "depth": "light",
                    "purpose": "combat_boredom"
                },
                risk_level=0.1,
                capability_req=["llm_access"],
            ))

        # 9. Circadian sleep recommendation
        if self._should_suggest_sleep(current_hour, energy, fatigue, tick):
            actions.append(Action(
                type="SLEEP",
                params={
                    "duration": 10,
                    "priority": "low",
                    "reason": "circadian_schedule"
                },
                risk_level=0.0,
                capability_req=[],
            ))
            self.last_sleep_tick = tick

        # 10. Balanced state - no intervention needed
        if not actions:
            # All systems healthy, no action needed
            pass

        return actions

    def _update_history(self, energy: float, stress: float, tick: int):
        """Update health history for trend detection.

        Args:
            energy: Current energy level
            stress: Current stress level
            tick: Current tick
        """
        # Keep last 20 measurements
        self.energy_history.append((tick, energy))
        self.stress_history.append((tick, stress))

        if len(self.energy_history) > 20:
            self.energy_history.pop(0)
        if len(self.stress_history) > 20:
            self.stress_history.pop(0)

    def _is_energy_declining(self) -> bool:
        """Detect if energy is in a declining trend.

        Returns:
            True if energy is declining over recent history
        """
        if len(self.energy_history) < 5:
            return False

        # Check if last 5 measurements show downward trend
        recent = [e for _, e in self.energy_history[-5:]]

        # Simple declining check: each value lower than previous
        declining_count = 0
        for i in range(1, len(recent)):
            if recent[i] < recent[i-1]:
                declining_count += 1

        return declining_count >= 3  # At least 3 out of 4 declines

    def _is_sleep_time(self, current_hour: int) -> bool:
        """Check if current hour is within preferred sleep window.

        Args:
            current_hour: Hour of day (0-23)

        Returns:
            True if within sleep window
        """
        if self.preferred_sleep_start > self.preferred_sleep_end:
            # Sleep window crosses midnight (e.g., 22:00 - 07:00)
            return current_hour >= self.preferred_sleep_start or current_hour < self.preferred_sleep_end
        else:
            # Sleep window within same day
            return self.preferred_sleep_start <= current_hour < self.preferred_sleep_end

    def _should_suggest_sleep(
        self,
        current_hour: int,
        energy: float,
        fatigue: float,
        tick: int
    ) -> bool:
        """Determine if should suggest sleep based on circadian rhythm.

        Args:
            current_hour: Current hour (0-23)
            energy: Current energy level
            fatigue: Current fatigue level
            tick: Current tick

        Returns:
            True if should suggest sleep
        """
        # Don't suggest too frequently
        ticks_since_last_sleep = tick - self.last_sleep_tick
        if ticks_since_last_sleep < 100:  # At least 100 ticks between sleep suggestions
            return False

        # Suggest if in sleep window and energy/fatigue support it
        if self._is_sleep_time(current_hour):
            if energy < 0.6 or fatigue > 0.4:
                return True

        return False

    def assess_health_status(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall health status.

        Args:
            state: Current state

        Returns:
            Health assessment dict with status and recommendations
        """
        energy = state.get("energy", 0.5)
        stress = state.get("stress", 0.0)
        fatigue = state.get("fatigue", 0.0)
        boredom = state.get("boredom", 0.0)
        mood = state.get("mood", 0.5)

        # Calculate overall health score (0-1)
        health_score = (
            energy * 0.3 +
            (1 - stress) * 0.25 +
            (1 - fatigue) * 0.25 +
            (1 - boredom) * 0.1 +
            mood * 0.1
        )

        # Determine status
        if health_score > 0.75:
            status = "excellent"
        elif health_score > 0.6:
            status = "good"
        elif health_score > 0.4:
            status = "fair"
        elif health_score > 0.25:
            status = "poor"
        else:
            status = "critical"

        # Identify issues
        issues = []
        if energy < 0.3:
            issues.append("low_energy")
        if stress > 0.7:
            issues.append("high_stress")
        if fatigue > 0.7:
            issues.append("high_fatigue")
        if boredom > 0.7:
            issues.append("high_boredom")
        if mood < 0.3:
            issues.append("low_mood")

        return {
            "health_score": health_score,
            "status": status,
            "issues": issues,
            "interventions": issues,  # Alias for compatibility with tests
            "energy_trend": "declining" if self._is_energy_declining() else "stable",
        }

    # Alias for backward compatibility with tests
    assess_health = assess_health_status

    def update_health_state(self, metric: str, value: float):
        """Update a health metric value.

        Args:
            metric: Health metric name (e.g., "energy", "stress")
            value: New value for the metric
        """
        self._health_state[metric] = value

    def get_health_status(self) -> dict:
        """Get current health state.

        Returns:
            Dictionary of current health metrics
        """
        return self._health_state.copy()
