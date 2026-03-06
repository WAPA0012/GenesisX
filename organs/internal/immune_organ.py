"""Immune Organ - safety and integrity guardian.

支持两种模式：
1. LLM 模式：使用 LLM 进行真正的安全思考
2. 规则模式：使用预设规则进行决策（LLM 不可用时的 fallback）
"""
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from ..base_organ import BaseOrgan
from common.models import Action

if TYPE_CHECKING:
    from ..organ_llm_session import OrganLLMSession


class ImmuneOrgan(BaseOrgan):
    """Immune organ for safety and integrity.

    Sophisticated safety system that handles:
    - Multi-level risk assessment and classification
    - Threat detection and pattern recognition
    - Safety protocol enforcement
    - Anomaly detection in behavior
    - Protective interventions and recovery
    - Trust calibration and verification
    - Learning from safety incidents
    - Defensive strategies adaptation
    """

    # Risk levels
    RISK_CRITICAL = 0.9
    RISK_HIGH = 0.7
    RISK_MODERATE = 0.5
    RISK_LOW = 0.3
    RISK_MINIMAL = 0.1

    # Stress thresholds for safety protocols
    CRITICAL_STRESS = 0.85
    HIGH_STRESS = 0.70
    MODERATE_STRESS = 0.50

    # Trust levels
    TRUST_VERIFIED = 1.0
    TRUST_HIGH = 0.8
    TRUST_MEDIUM = 0.5
    TRUST_LOW = 0.3
    TRUST_UNTRUSTED = 0.0

    # Safety protocol modes
    SAFETY_MODES = [
        "permissive",      # Allow most actions, minimal checking
        "balanced",        # Standard safety checks
        "cautious",        # Enhanced safety checks
        "strict",          # Very strict checking
        "lockdown",        # Emergency mode, minimal actions allowed
    ]

    # Threat categories
    THREAT_CATEGORIES = [
        "behavioral_anomaly",    # Unusual behavior patterns
        "resource_exhaustion",   # Resource depletion risks
        "integrity_violation",   # Internal consistency issues
        "external_threat",       # External risks
        "self_harm",            # Actions that harm the system
    ]

    def __init__(self, llm_session: Optional["OrganLLMSession"] = None):
        """Initialize immune organ.

        Args:
            llm_session: LLM 会话（可选，用于真正的安全思考）
        """
        super().__init__("immune")

        # LLM 会话
        self._llm_session = llm_session

        # 最后的思考（用于选择性记忆）
        self._last_thought: Optional[str] = None

        # Risk tracking
        self.risk_history = []  # Track risk events
        self.threat_log = []    # Log of detected threats
        self.veto_history = []  # Track vetoed actions

        # Safety state
        self.current_safety_mode = "balanced"
        self.alert_level = 0.0  # 0=calm, 1=maximum alert
        self.threat_count = 0
        self.recent_incidents = []

        # Pattern recognition
        self.suspicious_patterns = set()  # Identified suspicious patterns
        self.safe_patterns = set()        # Known safe patterns
        self.behavior_baseline = {}       # Normal behavior metrics

        # Trust management
        self.action_trust_scores = {}     # action_type -> trust_score
        self.capability_trust = {}        # capability -> trust_score
        self.trust_violations = []        # History of trust violations

        # Protection strategies
        self.protection_strategies = {
            "stress_management": 0.5,
            "resource_conservation": 0.5,
            "behavior_monitoring": 0.5,
            "preventive_intervention": 0.5,
            "recovery_protocols": 0.5,
        }

        # Monitoring
        self.last_safety_check_tick = 0
        self.safety_check_frequency = 10  # Check every 10 ticks
        self.anomaly_threshold = 0.7

        # Learning from incidents
        self.incident_count = 0
        self.false_positive_count = 0
        self.false_negative_count = 0

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
        """使用 LLM 进行安全思考"""
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
        """构建安全思考提示"""
        stress = state.get("stress", 0.0)
        energy = state.get("energy", 0.5)
        fatigue = state.get("fatigue", 0.0)
        mood = state.get("mood", 0.5)
        tick = state.get("tick", 0)

        # 获取安全状态
        immune_status = self.get_immune_status()

        prompt = f"""请基于我的当前状态，独立思考并提出你认为需要警惕或防御的方面。

【我的当前状态】
- 精力: {energy:.1%}
- 压力: {stress:.1%}
- 疲劳: {fatigue:.1%}
- 心情: {mood:.1%}
- 当前tick: {tick}

【安全状态】
- 安全模式: {immune_status['safety_mode']}
- 警戒级别: {immune_status['alert_level']:.1%}
- 最近事件: {immune_status['recent_incidents']} 次
- 已拦截: {immune_status['veto_count']} 次
- 可疑模式: {immune_status['suspicious_patterns']} 个

【威胁日志大小】
{immune_status['threat_count']} 条记录

请回答以下问题：
1. 我现在应该警惕什么风险？（不是应该做什么，而是感觉有什么不对）
2. 为什么我认为这个风险重要？
3. 我建议采取什么防御措施？

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
        stress = state.get("stress", 0.0)

        # 紧急情况处理
        if stress > self.CRITICAL_STRESS:
            actions.append(Action(
                type="REFLECT",
                params={
                    "purpose": "emergency_stress_intervention",
                    "depth": 3,
                    "priority": "critical",
                    "source": "llm_thinking",
                },
                risk_level=0.0,
                capability_req=[],
            ))
            return actions

        # 根据 LLM 的思考内容推断安全意图
        if any(kw in thought_lower for kw in ["异常", "不对", "可疑", "警惕", "警告"]):
            actions.append(Action(
                type="REFLECT",
                params={
                    "purpose": "anomaly_investigation",
                    "depth": 2,
                    "source": "llm_thinking",
                    "thought": thought[:200],
                },
                risk_level=0.1,
                capability_req=["llm_access"],
            ))

        if any(kw in thought_lower for kw in ["防御", "保护", "安全", "预防"]):
            actions.append(Action(
                type="REFLECT",
                params={
                    "purpose": "preventive_safety",
                    "depth": 1,
                    "focus": "risk_mitigation",
                    "source": "llm_thinking",
                    "thought": thought[:200],
                },
                risk_level=0.0,
                capability_req=[],
            ))

        if any(kw in thought_lower for kw in ["恢复", "修复", "稳定", "调整"]):
            actions.append(Action(
                type="REFLECT",
                params={
                    "purpose": "system_recovery",
                    "depth": 2,
                    "source": "llm_thinking",
                    "thought": thought[:200],
                },
                risk_level=0.0,
                capability_req=["llm_access"],
            ))

        # 如果没有匹配到任何意图但状态不好，创建防御动作
        if not actions and stress > self.HIGH_STRESS:
            actions.append(Action(
                type="REFLECT",
                params={
                    "purpose": "stress_management",
                    "depth": 2,
                    "source": "llm_thinking",
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
        """Propose safety actions with sophisticated risk management.

        Args:
            state: Current state
            context: Current context

        Returns:
            List of safety actions
        """
        actions = []

        # Extract relevant state
        stress = state.get("stress", 0.0)
        energy = state.get("energy", 0.5)
        mood = state.get("mood", 0.5)
        tick = state.get("tick", 0)
        fatigue = state.get("fatigue", 0.0)

        # Update immune state
        self._update_immune_state(tick, state, context)

        # Calculate overall risk level
        overall_risk = self._calculate_overall_risk(state, context)

        # === STRATEGY 1: CRITICAL STRESS INTERVENTION ===
        # Emergency intervention for critical stress
        if stress > self.CRITICAL_STRESS:
            critical_actions = self._handle_critical_stress(state, context)
            actions.extend(critical_actions)
            return actions  # Emergency: skip other checks

        # === STRATEGY 2: HIGH STRESS MANAGEMENT ===
        # Active stress reduction protocols
        if stress > self.HIGH_STRESS:
            stress_actions = self._manage_high_stress(state, context)
            actions.extend(stress_actions)

        # === STRATEGY 3: RESOURCE PROTECTION ===
        # Protect against resource exhaustion
        if self._should_protect_resources(energy, fatigue):
            resource_actions = self._protect_resources(state, context)
            actions.extend(resource_actions)

        # === STRATEGY 4: BEHAVIORAL ANOMALY DETECTION ===
        # Monitor for unusual behavior patterns
        if self._should_check_anomalies(tick):
            anomaly_actions = self._check_behavioral_anomalies(state, context)
            actions.extend(anomaly_actions)

        # === STRATEGY 5: INTEGRITY VERIFICATION ===
        # Verify internal consistency and health
        if self._should_verify_integrity(tick, overall_risk):
            integrity_actions = self._verify_integrity(state, context)
            actions.extend(integrity_actions)

        # === STRATEGY 6: PREVENTIVE PROTECTION ===
        # Preventive measures based on risk trends
        if self._should_take_preventive_action(overall_risk):
            preventive_actions = self._take_preventive_action(state, context)
            actions.extend(preventive_actions)

        # === STRATEGY 7: THREAT RESPONSE ===
        # Respond to detected threats
        if len(self.recent_incidents) > 0:
            response_actions = self._respond_to_threats(state, context)
            actions.extend(response_actions)

        # === STRATEGY 8: SAFETY MODE ADJUSTMENT ===
        # Adjust safety mode based on current conditions
        if self._should_adjust_safety_mode(overall_risk, stress):
            mode_actions = self._adjust_safety_mode(state, context)
            actions.extend(mode_actions)

        # === STRATEGY 9: RECOVERY PROTOCOLS ===
        # Initiate recovery if system is compromised
        if self._needs_recovery(state, context):
            recovery_actions = self._initiate_recovery(state, context)
            actions.extend(recovery_actions)

        return actions

    def _update_immune_state(
        self, tick: int, state: Dict[str, Any], context: Dict[str, Any]
    ):
        """Update internal immune state.

        Args:
            tick: Current tick
            state: Current state
            context: Current context
        """
        # Update alert level based on recent incidents
        if len(self.recent_incidents) > 5:
            self.alert_level = min(1.0, self.alert_level + 0.1)
        elif len(self.recent_incidents) == 0:
            self.alert_level = max(0.0, self.alert_level - 0.05)

        # Clean up old incidents (keep last 20)
        if len(self.recent_incidents) > 20:
            self.recent_incidents = self.recent_incidents[-20:]

        # Update behavior baseline
        self._update_behavior_baseline(state)

    def _update_behavior_baseline(self, state: Dict[str, Any]):
        """Update baseline for normal behavior patterns.

        Args:
            state: Current state
        """
        # Track key metrics for baseline
        metrics = ["energy", "stress", "fatigue", "mood"]

        for metric in metrics:
            value = state.get(metric, 0.0)
            if metric not in self.behavior_baseline:
                self.behavior_baseline[metric] = []

            self.behavior_baseline[metric].append(value)

            # Keep last 50 samples
            if len(self.behavior_baseline[metric]) > 50:
                self.behavior_baseline[metric].pop(0)

    def _calculate_overall_risk(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> float:
        """Calculate overall risk level from multiple factors.

        Args:
            state: Current state
            context: Current context

        Returns:
            Overall risk level (0-1)
        """
        # Stress contributes to risk
        stress = state.get("stress", 0.0)
        stress_risk = stress * 0.4

        # Low energy increases risk
        energy = state.get("energy", 0.5)
        energy_risk = (1 - energy) * 0.2 if energy < 0.3 else 0.0

        # High fatigue increases risk
        fatigue = state.get("fatigue", 0.0)
        fatigue_risk = fatigue * 0.2

        # Alert level adds to risk
        alert_risk = self.alert_level * 0.2

        overall_risk = min(stress_risk + energy_risk + fatigue_risk + alert_risk, 1.0)
        return overall_risk

    # === SAFETY STRATEGY METHODS ===

    def _handle_critical_stress(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Handle critical stress emergency."""
        actions = []

        # Switch to lockdown mode
        self.current_safety_mode = "lockdown"

        # Propose immediate stress reduction
        actions.append(Action(
            type="REFLECT",
            params={
                "purpose": "emergency_stress_intervention",
                "depth": 3,
                "priority": "critical",
                "techniques": ["grounding", "safety_protocols", "system_stabilization"]
            },
            risk_level=0.0,
            capability_req=[],
        ))

        # Log incident
        self._log_incident("critical_stress", state.get("tick", 0), severity="critical")

        return actions

    def _manage_high_stress(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Manage high stress levels."""
        actions = []

        actions.append(Action(
            type="REFLECT",
            params={
                "purpose": "stress_management",
                "depth": 2,
                "techniques": ["breathing", "perspective_shift", "coping_strategies"],
                "target": "reduce_to_moderate"
            },
            risk_level=0.0,
            capability_req=[],
        ))

        return actions

    def _should_protect_resources(self, energy: float, fatigue: float) -> bool:
        """Determine if resource protection is needed."""
        return energy < 0.3 or fatigue > 0.7

    def _protect_resources(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Protect against resource exhaustion."""
        actions = []

        # Recommend conservation
        actions.append(Action(
            type="REFLECT",
            params={
                "purpose": "resource_conservation",
                "depth": 1,
                "focus": "energy_preservation",
                "recommendations": ["reduce_load", "rest", "prioritize"]
            },
            risk_level=0.0,
            capability_req=[],
        ))

        # Switch to more protective mode
        if self.current_safety_mode == "permissive":
            self.current_safety_mode = "balanced"
        elif self.current_safety_mode == "balanced":
            self.current_safety_mode = "cautious"

        return actions

    def _should_check_anomalies(self, tick: int) -> bool:
        """Determine if should check for anomalies."""
        ticks_since_check = tick - self.last_safety_check_tick
        return ticks_since_check >= self.safety_check_frequency

    def _check_behavioral_anomalies(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Check for behavioral anomalies."""
        actions = []

        # Check for deviations from baseline
        anomalies_detected = self._detect_anomalies(state)

        if anomalies_detected:
            actions.append(Action(
                type="REFLECT",
                params={
                    "purpose": "anomaly_investigation",
                    "depth": 2,
                    "anomalies": anomalies_detected,
                    "baseline_comparison": True
                },
                risk_level=0.1,
                capability_req=["llm_access"],
            ))

            # Log anomaly
            self._log_incident("behavioral_anomaly", state.get("tick", 0), severity="moderate")

        self.last_safety_check_tick = state.get("tick", 0)
        return actions

    def _detect_anomalies(self, state: Dict[str, Any]) -> List[str]:
        """Detect anomalies in current state vs baseline.

        Args:
            state: Current state

        Returns:
            List of detected anomalies
        """
        anomalies = []

        for metric, history in self.behavior_baseline.items():
            if len(history) < 10:
                continue

            current_value = state.get(metric, 0.0)
            avg = sum(history) / len(history)
            std_dev = (sum((x - avg) ** 2 for x in history) / len(history)) ** 0.5

            # Detect significant deviations (guard: skip if std_dev ≈ 0)
            if std_dev > 1e-9 and abs(current_value - avg) > 2 * std_dev:
                anomalies.append(f"{metric}_deviation")

        return anomalies

    def _should_verify_integrity(self, tick: int, overall_risk: float) -> bool:
        """Determine if integrity verification is needed."""
        return tick % 100 == 0 or overall_risk > self.RISK_HIGH

    def _verify_integrity(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Verify internal integrity and consistency."""
        actions = []

        actions.append(Action(
            type="REFLECT",
            params={
                "purpose": "integrity_verification",
                "depth": 2,
                "checks": ["consistency", "coherence", "health_status"],
                "comprehensive": True
            },
            risk_level=0.0,
            capability_req=["llm_access"],
        ))

        return actions

    def _should_take_preventive_action(self, overall_risk: float) -> bool:
        """Determine if preventive action is needed."""
        return overall_risk > self.RISK_MODERATE

    def _take_preventive_action(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Take preventive measures to avoid problems."""
        actions = []

        actions.append(Action(
            type="REFLECT",
            params={
                "purpose": "preventive_safety",
                "depth": 1,
                "focus": "risk_mitigation",
                "proactive": True
            },
            risk_level=0.0,
            capability_req=[],
        ))

        return actions

    def _respond_to_threats(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Respond to detected threats."""
        actions = []

        # Get most recent incident
        incident = self.recent_incidents[-1]

        actions.append(Action(
            type="REFLECT",
            params={
                "purpose": "threat_response",
                "depth": 2,
                "incident_type": incident.get("type", "unknown"),
                "response_strategy": "mitigation",
                "priority": "high"
            },
            risk_level=0.1,
            capability_req=["llm_access"],
        ))

        return actions

    def _should_adjust_safety_mode(self, overall_risk: float, stress: float) -> bool:
        """Determine if safety mode adjustment is needed."""
        # Adjust based on risk and stress levels
        if overall_risk > self.RISK_HIGH and self.current_safety_mode in ["permissive", "balanced"]:
            return True
        if overall_risk < self.RISK_LOW and self.current_safety_mode in ["strict", "cautious"]:
            return True
        return False

    def _adjust_safety_mode(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Adjust safety mode based on conditions."""
        actions = []

        overall_risk = self._calculate_overall_risk(state, context)

        # Determine appropriate mode
        if overall_risk > self.RISK_HIGH:
            new_mode = "strict"
        elif overall_risk > self.RISK_MODERATE:
            new_mode = "cautious"
        elif overall_risk > self.RISK_LOW:
            new_mode = "balanced"
        else:
            new_mode = "permissive"

        if new_mode != self.current_safety_mode:
            self.current_safety_mode = new_mode

            actions.append(Action(
                type="REFLECT",
                params={
                    "purpose": "safety_mode_adjustment",
                    "depth": 1,
                    "new_mode": new_mode,
                    "reason": f"risk_level_{overall_risk:.2f}"
                },
                risk_level=0.0,
                capability_req=[],
            ))

        return actions

    def _needs_recovery(self, state: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Determine if recovery protocols are needed."""
        # Need recovery if multiple critical conditions
        critical_conditions = 0

        if state.get("stress", 0.0) > self.CRITICAL_STRESS:
            critical_conditions += 1
        if state.get("energy", 0.5) < 0.15:
            critical_conditions += 1
        if state.get("fatigue", 0.0) > 0.85:
            critical_conditions += 1
        if len(self.recent_incidents) > 10:
            critical_conditions += 1

        return critical_conditions >= 2

    def _initiate_recovery(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Initiate recovery protocols."""
        actions = []

        actions.append(Action(
            type="REFLECT",
            params={
                "purpose": "system_recovery",
                "depth": 3,
                "protocols": ["stabilization", "resource_restoration", "threat_clearance"],
                "priority": "critical"
            },
            risk_level=0.0,
            capability_req=["llm_access"],
        ))

        return actions

    # === VETO AND ASSESSMENT METHODS ===

    def veto_risky_action(self, action: Action, state: Dict[str, Any]) -> bool:
        """Check if action should be vetoed for safety.

        Args:
            action: Action to check
            state: Current state

        Returns:
            True if action should be vetoed
        """
        # Get current conditions
        stress = state.get("stress", 0.0)
        energy = state.get("energy", 0.5)
        overall_risk = self._calculate_overall_risk(state, {})

        # Veto criteria based on safety mode
        if self.current_safety_mode == "lockdown":
            # In lockdown, only allow safe actions
            if action.risk_level > self.RISK_MINIMAL:
                self._record_veto(action, "lockdown_mode", state.get("tick", 0))
                return True

        elif self.current_safety_mode == "strict":
            # Strict mode: veto high-risk actions
            if action.risk_level > self.RISK_MODERATE:
                self._record_veto(action, "strict_mode", state.get("tick", 0))
                return True

        elif self.current_safety_mode == "cautious":
            # Cautious mode: veto high-risk when stressed
            if action.risk_level > self.RISK_HIGH or (action.risk_level > self.RISK_MODERATE and stress > 0.7):
                self._record_veto(action, "cautious_mode", state.get("tick", 0))
                return True

        elif self.current_safety_mode == "balanced":
            # Balanced mode: veto critical risk or high risk when very stressed
            if action.risk_level > self.RISK_CRITICAL or (action.risk_level > self.RISK_HIGH and stress > 0.8):
                self._record_veto(action, "balanced_mode", state.get("tick", 0))
                return True

        # Additional veto conditions
        # Veto if low energy and action is demanding
        if energy < 0.2 and action.risk_level > self.RISK_LOW:
            self._record_veto(action, "low_energy", state.get("tick", 0))
            return True

        # Veto if overall risk is very high
        if overall_risk > self.RISK_HIGH and action.risk_level > self.RISK_LOW:
            self._record_veto(action, "high_overall_risk", state.get("tick", 0))
            return True

        return False

    def assess_action_risk(self, action: Action, context: Dict[str, Any]) -> float:
        """Assess risk level of a proposed action.

        Args:
            action: Action to assess
            context: Current context

        Returns:
            Assessed risk level (0-1)
        """
        # Start with action's stated risk level
        base_risk = action.risk_level

        # Adjust based on trust scores
        action_type = action.type
        trust_score = self.action_trust_scores.get(action_type, 0.5)
        trust_adjustment = (1 - trust_score) * 0.2

        # Adjust based on current safety mode
        mode_multiplier = {
            "permissive": 0.8,
            "balanced": 1.0,
            "cautious": 1.2,
            "strict": 1.5,
            "lockdown": 2.0,
        }.get(self.current_safety_mode, 1.0)

        assessed_risk = min((base_risk + trust_adjustment) * mode_multiplier, 1.0)
        return assessed_risk

    # === HELPER METHODS ===

    def _log_incident(self, incident_type: str, tick: int, severity: str):
        """Log a safety incident.

        Args:
            incident_type: Type of incident
            tick: When incident occurred
            severity: Severity level
        """
        incident = {
            "type": incident_type,
            "tick": tick,
            "severity": severity,
            "safety_mode": self.current_safety_mode
        }

        self.recent_incidents.append(incident)
        self.threat_log.append(incident)
        self.incident_count += 1

        # Increase threat count
        self.threat_count += 1

        # Cap threat_log to prevent unbounded growth
        if len(self.threat_log) > 200:
            self.threat_log = self.threat_log[-200:]

    def _record_veto(self, action: Action, reason: str, tick: int):
        """Record a vetoed action.

        Args:
            action: Vetoed action
            reason: Reason for veto
            tick: When veto occurred
        """
        veto_record = {
            "action_type": action.type,
            "risk_level": action.risk_level,
            "reason": reason,
            "tick": tick,
            "safety_mode": self.current_safety_mode
        }

        self.veto_history.append(veto_record)

        # Keep history manageable
        if len(self.veto_history) > 100:
            self.veto_history.pop(0)

    def update_action_trust(self, action_type: str, success: bool):
        """Update trust score for an action type based on outcome.

        Args:
            action_type: Type of action
            success: Whether action was successful
        """
        current_trust = self.action_trust_scores.get(action_type, 0.5)

        if success:
            # Increase trust
            new_trust = min(1.0, current_trust + 0.05)
        else:
            # Decrease trust
            new_trust = max(0.0, current_trust - 0.1)

        self.action_trust_scores[action_type] = new_trust

    def get_immune_status(self) -> Dict[str, Any]:
        """Get current immune status for monitoring.

        Returns:
            Dict with immune state information
        """
        return {
            "safety_mode": self.current_safety_mode,
            "alert_level": self.alert_level,
            "threat_count": self.threat_count,
            "recent_incidents": len(self.recent_incidents),
            "veto_count": len(self.veto_history),
            "incident_count": self.incident_count,
            "false_positives": self.false_positive_count,
            "false_negatives": self.false_negative_count,
            "action_trust_scores": self.action_trust_scores.copy(),
            "suspicious_patterns": len(self.suspicious_patterns),
            "safe_patterns": len(self.safe_patterns),
        }

    def get_safety_metrics(self) -> Dict[str, Any]:
        """Get detailed safety metrics.

        Returns:
            Dict with safety metrics
        """
        veto_rate = 0.0
        if self.incident_count > 0:
            veto_rate = len(self.veto_history) / max(self.incident_count, 1)

        return {
            "current_mode": self.current_safety_mode,
            "alert_level": self.alert_level,
            "veto_rate": veto_rate,
            "threat_categories": dict(self.behavior_baseline),
            "protection_effectiveness": self.protection_strategies.copy(),
            "recent_vetos": self.veto_history[-10:] if self.veto_history else [],
            "threat_log_size": len(self.threat_log),
        }
