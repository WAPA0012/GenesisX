"""Value Learning Module - slow adaptation of value parameters.

Implements paper Section 3.12: 价值学习：让偏好"长出来"但变化慢

Key formula:
    ω_{t+1} = (1-ε)ω_t + ε·Δω_t, where ε << 1

Learning signals:
    1. Explicit feedback: ratings/likes/corrections
    2. Implicit feedback: response speed, conversation length, topic continuation
    3. Internal feedback: RPE (δ_t)
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import math


class FeedbackType(Enum):
    """Types of learning signals."""
    EXPLICIT_POSITIVE = "explicit_positive"  # Rating/like
    EXPLICIT_NEGATIVE = "explicit_negative"  # Dislike/correction
    IMPLICIT_ENGAGEMENT = "implicit_engagement"  # Long conversation
    IMPLICIT_DISENGAGEMENT = "implicit_disengagement"  # Short/abandoned
    INTERNAL_POSITIVE_RPE = "internal_positive_rpe"  # δ > threshold
    INTERNAL_NEGATIVE_RPE = "internal_negative_rpe"  # δ < -threshold


@dataclass
class FeedbackSignal:
    """A feedback signal for value learning."""
    feedback_type: FeedbackType
    dimension: str  # Which value dimension this affects
    magnitude: float = 1.0  # Strength of the signal
    timestamp: float = 0.0  # When the feedback was received (for time decay)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValueParameters:
    """Value parameters ω_t that can be learned.

    Paper Section 3.12.1:
    - Setpoints f^(i)* for each dimension
    - Temperature τ for gap-to-weight
    - Personality bias coefficients g_i(θ)
    - Interaction style parameters

    修复 v15: 使用5维核心价值向量 (论文 Section 3.5.1)
    """
    # Dimension setpoints (5维价值向量)
    setpoints: Dict[str, float] = field(default_factory=dict)

    # Softmax temperature (paper Appendix A.5: τ = 4.0)
    temperature: float = 4.0

    # Personality biases (multipliers for each dimension)
    personality_biases: Dict[str, float] = field(default_factory=dict)

    # Interaction style (0=passive, 1=proactive)
    proactivity: float = 0.5

    def __post_init__(self):
        if not self.setpoints:
            # 修复 v15: 5维价值向量设定点 (论文 Section 3.5.1)
            self.setpoints = {
                "homeostasis": 0.85,  # 资源稳态设定点较高
                "attachment": 0.70,   # 关系维持
                "curiosity": 0.60,    # 好奇探索
                "competence": 0.75,   # 胜任目标
                "safety": 0.70,       # 安全边际
            }
        if not self.personality_biases:
            self.personality_biases = {dim: 1.0 for dim in self.setpoints}


@dataclass
class ValueLearnerConfig:
    """Configuration for value learning.

    论文 Section 3.12.3: Time window and decay for feedback aggregation.
    """
    # Learning rate ε (must be << 1 for slow change)
    # 论文Appendix A.5: 默认0.001
    epsilon: float = 0.001

    # RPE thresholds for triggering learning
    rpe_positive_threshold: float = 0.3
    rpe_negative_threshold: float = -0.3

    # Maximum change per update (safety bound)
    max_delta_setpoint: float = 0.05
    max_delta_bias: float = 0.1

    # Minimum feedback count before learning
    min_feedback_count: int = 5  # N_min from paper

    # Time window for feedback (seconds) - T_window from paper
    # 修复 M4: 论文要求 7 天时间窗口 (Section 3.12.3)
    time_window: float = 7 * 24 * 3600  # 7 days in seconds (论文默认值)

    # Decay rate λ_decay for time-based weighting
    decay_lambda: float = 0.1

    # Minimum weighted feedback sum required
    min_weighted_feedback: float = 5.0


class ValueLearner:
    """Value learning system for slow, robust parameter adaptation.

    Implements paper Section 3.12 with three learning signals:
    1. Explicit feedback (ratings/corrections)
    2. Implicit feedback (engagement patterns)
    3. Internal feedback (RPE signals)

    Update rule: ω_{t+1} = (1-ε)ω_t + ε·Δω_t
    """

    def __init__(self, config: Optional[ValueLearnerConfig] = None):
        """Initialize value learner.

        Args:
            config: Learning configuration
        """
        self.config = config or ValueLearnerConfig()

        # Current value parameters
        self.params = ValueParameters()

        # Feedback buffer for aggregating signals
        self._feedback_buffer: List[FeedbackSignal] = []

        # Learning statistics
        self._update_count = 0
        self._total_feedback = 0

    def add_feedback(self, feedback: FeedbackSignal, timestamp: float = None):
        """Add a feedback signal to the buffer.

        Args:
            feedback: Feedback signal to add
            timestamp: Timestamp of feedback (uses current time if None)
        """
        import time
        if timestamp is None:
            timestamp = time.time()
        feedback.timestamp = timestamp
        self._feedback_buffer.append(feedback)
        self._total_feedback += 1

        # Cap buffer size to prevent unbounded memory growth
        # Even if update() is never called, keep at most 10000 entries
        if len(self._feedback_buffer) > 10000:
            self._feedback_buffer = self._feedback_buffer[-5000:]

    def add_rpe_signal(self, rpe: float, active_dimension: str, timestamp: float = None):
        """Add internal feedback from RPE (legacy method for backward compatibility).

        Paper Section 3.12.2: 内在反馈 RPE (δ_t)

        Args:
            rpe: Reward prediction error δ_t
            active_dimension: Which dimension was most active
            timestamp: When the RPE occurred
        """
        import time
        if timestamp is None:
            timestamp = time.time()

        cfg = self.config

        if rpe >= cfg.rpe_positive_threshold:
            # Positive surprise - reinforce current behavior
            feedback = FeedbackSignal(
                feedback_type=FeedbackType.INTERNAL_POSITIVE_RPE,
                dimension=active_dimension,
                magnitude=min(1.0, rpe / cfg.rpe_positive_threshold),
                timestamp=timestamp,
            )
            self.add_feedback(feedback, timestamp)

        elif rpe <= cfg.rpe_negative_threshold:
            # Negative surprise - reduce current tendency
            feedback = FeedbackSignal(
                feedback_type=FeedbackType.INTERNAL_NEGATIVE_RPE,
                dimension=active_dimension,
                magnitude=min(1.0, abs(rpe) / abs(cfg.rpe_negative_threshold)),
                timestamp=timestamp,
            )
            self.add_feedback(feedback, timestamp)

    def add_rpe_signals_vector(self, rpe_vector: Dict[str, float], timestamp: float = None):
        """Add per-dimension RPE signals (论文P0-2: 维度级RPE).

        Paper Section 3.7.2: 维度级RPE定义
        δ^(i)_t = u^(i)_t + γV^(i)(S_{t+1}) - V^(i)(S_t)

        Each dimension has independent RPE, allowing the system to distinguish
        which dimension's expectations were violated.

        Args:
            rpe_vector: Dictionary mapping dimension names to their RPE values
                        e.g., {"homeostasis": 0.2, "integrity": -0.1, ...}
            timestamp: When the RPEs occurred

        Example:
            >>> learner.add_rpe_signals_vector({
            ...     "homeostasis": 0.3,   # Positive surprise: energy recovered
            ...     "curiosity": -0.2,    # Negative surprise: exploration failed
            ...     "attachment": 0.1     # Mild positive: good interaction
            ... })
        """
        import time
        if timestamp is None:
            timestamp = time.time()

        cfg = self.config

        # Process each dimension's RPE independently
        for dimension, rpe in rpe_vector.items():
            if rpe >= cfg.rpe_positive_threshold:
                # Positive surprise - reinforce this dimension
                feedback = FeedbackSignal(
                    feedback_type=FeedbackType.INTERNAL_POSITIVE_RPE,
                    dimension=dimension,
                    magnitude=min(1.0, rpe / cfg.rpe_positive_threshold),
                    timestamp=timestamp,
                    context={"per_dimension_rpe": True},
                )
                self.add_feedback(feedback, timestamp)

            elif rpe <= cfg.rpe_negative_threshold:
                # Negative surprise - reduce this dimension's tendency
                feedback = FeedbackSignal(
                    feedback_type=FeedbackType.INTERNAL_NEGATIVE_RPE,
                    dimension=dimension,
                    magnitude=min(1.0, abs(rpe) / abs(cfg.rpe_negative_threshold)),
                    timestamp=timestamp,
                    context={"per_dimension_rpe": True},
                )
                self.add_feedback(feedback, timestamp)

    def get_dimension_rpe_summary(self, current_time: float = None) -> Dict[str, Dict[str, float]]:
        """Get summary of recent RPE by dimension.

        Args:
            current_time: Current timestamp for filtering

        Returns:
            Dictionary with dimension stats:
            {
                "homeostasis": {"positive_count": 5, "negative_count": 2, "avg_rpe": 0.15},
                "curiosity": {"positive_count": 3, "negative_count": 8, "avg_rpe": -0.08},
                ...
            }
        """
        import time
        if current_time is None:
            current_time = time.time()

        cfg = self.config
        dimension_stats: Dict[str, Dict[str, float]] = {}

        # Initialize stats for all dimensions
        # v15修复: 使用5维核心价值系统
        for dim in ["homeostasis", "attachment", "curiosity", "competence", "safety"]:
            dimension_stats[dim] = {
                "positive_count": 0,
                "negative_count": 0,
                "total_magnitude": 0.0,
                "avg_rpe": 0.0,
            }

        # Aggregate recent RPE signals
        valid_feedback = [
            f for f in self._feedback_buffer
            if (current_time - f.timestamp) <= cfg.time_window
            and f.feedback_type in [
                FeedbackType.INTERNAL_POSITIVE_RPE,
                FeedbackType.INTERNAL_NEGATIVE_RPE
            ]
        ]

        for feedback in valid_feedback:
            dim = feedback.dimension
            if dim in dimension_stats:
                if feedback.feedback_type == FeedbackType.INTERNAL_POSITIVE_RPE:
                    dimension_stats[dim]["positive_count"] += 1
                    dimension_stats[dim]["total_magnitude"] += feedback.magnitude
                else:
                    dimension_stats[dim]["negative_count"] += 1
                    dimension_stats[dim]["total_magnitude"] -= feedback.magnitude

        # Calculate average for each dimension
        for dim, stats in dimension_stats.items():
            total_count = stats["positive_count"] + stats["negative_count"]
            if total_count > 0:
                stats["avg_rpe"] = stats["total_magnitude"] / total_count

        return dimension_stats

    def add_explicit_feedback(self, rating: float, active_dimension: str, timestamp: float = None):
        """Add explicit user feedback.

        Paper Section 3.12.2: 显式反馈（评分/点赞/纠正）

        Args:
            rating: User rating (e.g., -1 to 1)
            active_dimension: Dimension that was active when feedback given
            timestamp: When feedback was given
        """
        import time
        if timestamp is None:
            timestamp = time.time()

        if rating > 0:
            feedback = FeedbackSignal(
                feedback_type=FeedbackType.EXPLICIT_POSITIVE,
                dimension=active_dimension,
                magnitude=abs(rating),
                timestamp=timestamp,
            )
        elif rating < 0:
            feedback = FeedbackSignal(
                feedback_type=FeedbackType.EXPLICIT_NEGATIVE,
                dimension=active_dimension,
                magnitude=abs(rating),
                timestamp=timestamp,
            )
        else:
            # Zero rating is neutral - ignore
            return
        self.add_feedback(feedback, timestamp)

    def add_implicit_feedback(
        self,
        conversation_length: int,
        response_speed: float,
        topic_continued: bool,
        active_dimension: str,
        timestamp: float = None
    ):
        """Add implicit feedback from interaction patterns.

        Paper Section 3.12.2: 隐式反馈（回复速度、对话长度、是否继续话题）

        Args:
            conversation_length: Number of turns in conversation
            response_speed: User response time (seconds)
            topic_continued: Whether user continued the topic
            active_dimension: Dimension that was active
            timestamp: When interaction occurred
        """
        import time
        if timestamp is None:
            timestamp = time.time()

        # Engagement heuristic
        engagement_score = 0.0

        # Long conversation = positive
        if conversation_length > 5:
            engagement_score += 0.3

        # Fast response = positive
        if response_speed < 10.0:
            engagement_score += 0.3

        # Topic continuation = positive
        if topic_continued:
            engagement_score += 0.4

        if engagement_score > 0.5:
            feedback = FeedbackSignal(
                feedback_type=FeedbackType.IMPLICIT_ENGAGEMENT,
                dimension=active_dimension,
                magnitude=engagement_score,
                timestamp=timestamp,
            )
        else:
            feedback = FeedbackSignal(
                feedback_type=FeedbackType.IMPLICIT_DISENGAGEMENT,
                dimension=active_dimension,
                magnitude=1.0 - engagement_score,
                timestamp=timestamp,
            )
        self.add_feedback(feedback, timestamp)

    def _compute_feedback_weight(self, current_time: float, feedback_time: float) -> float:
        """Compute time-decayed weight for feedback.

        Paper Section 3.12.3: w_feedback(t, t_feedback) = exp(-λ_decay * (t - t_feedback) / T_window)

        Args:
            current_time: Current timestamp
            feedback_time: When feedback was received

        Returns:
            Decay weight in [0, 1]
        """
        cfg = self.config
        time_diff = current_time - feedback_time
        if time_diff < 0:
            return 1.0
        return math.exp(-cfg.decay_lambda * time_diff / cfg.time_window)

    def should_update(self, current_time: float = None) -> bool:
        """Check if we have enough weighted feedback to trigger an update.

        Paper Section 3.12.3: Σ w_feedback ≥ N_min

        Args:
            current_time: Current timestamp (uses time.time() if None)

        Returns:
            True if update should be performed
        """
        import time
        if current_time is None:
            current_time = time.time()

        # Filter feedback within time window
        cfg = self.config
        valid_feedback = [
            f for f in self._feedback_buffer
            if (current_time - f.timestamp) <= cfg.time_window
        ]

        if len(valid_feedback) < cfg.min_feedback_count:
            return False

        # Check weighted sum
        weighted_sum = sum(
            self._compute_feedback_weight(current_time, f.timestamp)
            for f in valid_feedback
        )
        return weighted_sum >= cfg.min_weighted_feedback

    def compute_delta_omega(self, current_time: float = None) -> Dict[str, Dict[str, float]]:
        """Compute Δω from accumulated feedback with time decay.

        Paper Section 3.12.3:
        - Time-weighted feedback aggregation
        - Positive feedback → increase setpoint/bias
        - Negative feedback → decrease setpoint/bias

        Args:
            current_time: Current timestamp

        Returns:
            Delta updates for setpoints and biases
        """
        import time
        if current_time is None:
            current_time = time.time()

        delta_setpoints: Dict[str, float] = {}
        delta_biases: Dict[str, float] = {}
        cfg = self.config

        # Filter feedback within time window
        valid_feedback = [
            f for f in self._feedback_buffer
            if (current_time - f.timestamp) <= cfg.time_window
        ]

        # Aggregate feedback by dimension with time weighting
        dim_scores: Dict[str, float] = {}
        dim_weights: Dict[str, float] = {}

        for feedback in valid_feedback:
            dim = feedback.dimension
            weight = self._compute_feedback_weight(current_time, feedback.timestamp)

            if dim not in dim_scores:
                dim_scores[dim] = 0.0
                dim_weights[dim] = 0.0

            # Determine direction based on feedback type
            if feedback.feedback_type in [
                FeedbackType.EXPLICIT_POSITIVE,
                FeedbackType.IMPLICIT_ENGAGEMENT,
                FeedbackType.INTERNAL_POSITIVE_RPE,
            ]:
                dim_scores[dim] += feedback.magnitude * weight
            else:
                dim_scores[dim] -= feedback.magnitude * weight

            dim_weights[dim] += weight

        # Convert scores to deltas
        for dim, score in dim_scores.items():
            # Normalize by weighted count
            total_weight = dim_weights.get(dim, 1.0)
            normalized = score / max(0.1, total_weight)

            # Clamp to max delta
            delta_setpoints[dim] = max(
                -cfg.max_delta_setpoint,
                min(cfg.max_delta_setpoint, normalized * 0.1)
            )
            delta_biases[dim] = max(
                -cfg.max_delta_bias,
                min(cfg.max_delta_bias, normalized * 0.2)
            )

        return {
            "setpoints": delta_setpoints,
            "biases": delta_biases,
        }

    def update(self, current_time: float = None) -> bool:
        """Perform value learning update with time-weighted feedback.

        Paper formula: ω_{t+1} = (1-ε)ω_t + ε·Δω_t

        Args:
            current_time: Current timestamp

        Returns:
            True if update was performed
        """
        import time
        if current_time is None:
            current_time = time.time()

        if not self.should_update(current_time):
            return False

        # Compute delta from time-weighted feedback
        delta_omega = self.compute_delta_omega(current_time)

        # Apply update with learning rate ε
        epsilon = self.config.epsilon

        # Update setpoints using additive form: ω_{t+1} = ω_t + ε·Δω_t
        # Note: The paper formula ω_{t+1} = (1-ε)ω_t + ε·Δω_t was incorrect here
        # because Δω_t is a *delta* (small adjustment), not a target value.
        # Using the EMA form with a delta causes: (1-ε)*old + ε*small_delta → slow decay to 0.
        # The correct additive form preserves the current value and adds a small adjustment.
        for dim, delta in delta_omega["setpoints"].items():
            if dim in self.params.setpoints:
                old_value = self.params.setpoints[dim]
                new_value = old_value + epsilon * delta
                # Clamp to [0, 1]
                self.params.setpoints[dim] = max(0.0, min(1.0, new_value))

        # Update personality biases (same additive form)
        for dim, delta in delta_omega["biases"].items():
            if dim in self.params.personality_biases:
                old_value = self.params.personality_biases[dim]
                new_value = old_value + epsilon * delta
                # Clamp to [0.1, 3.0] (reasonable bias range)
                self.params.personality_biases[dim] = max(0.1, min(3.0, new_value))

        # Remove expired feedback and clear processed ones
        cfg = self.config
        self._feedback_buffer = [
            f for f in self._feedback_buffer
            if (current_time - f.timestamp) <= cfg.time_window
        ]
        # Note: _feedback_buffer is already a new list, no need to clear()
        self._update_count += 1

        return True

    def get_parameters(self) -> ValueParameters:
        """Get current value parameters.

        Returns:
            Current ω_t
        """
        return self.params

    def set_parameters(self, params: ValueParameters):
        """Set value parameters (for initialization).

        Args:
            params: New parameters to set
        """
        self.params = params

    def get_statistics(self) -> Dict[str, Any]:
        """Get learning statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "update_count": self._update_count,
            "total_feedback": self._total_feedback,
            "pending_feedback": len(self._feedback_buffer),
            "current_setpoints": self.params.setpoints.copy(),
            "current_biases": self.params.personality_biases.copy(),
        }

