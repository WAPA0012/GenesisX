"""
Tests for Axiology module (Value System)
"""

import pytest
from axiology.reward import RewardCalculator
from axiology.gaps import GapCalculator
from axiology.weights import WeightUpdater
from axiology.value_learning import (
    ValueLearner,
    ValueLearnerConfig,
    FeedbackSignal,
    FeedbackType,
    ValueParameters,
)


class TestRewardCalculator:
    """Test reward calculation"""

    def test_calculate_reward_basic(self, sample_config):
        """Test basic reward calculation"""
        calculator = RewardCalculator(sample_config.get("axiology", {}))

        gaps = {
            "homeostasis": 0.5,
            "integrity": 0.3,
            "curiosity": 0.8,
        }

        weights = {
            "homeostasis": 0.4,
            "integrity": 0.3,
            "curiosity": 0.3,
        }

        reward = calculator.calculate_reward(gaps, weights)

        assert isinstance(reward, float)
        assert -1.0 <= reward <= 1.0

    def test_reward_components(self, sample_config):
        """Test reward calculation with components"""
        calculator = RewardCalculator(sample_config.get("axiology", {}))

        gaps = {
            "homeostasis": 0.2,
            "curiosity": 0.9,
        }

        weights = {
            "homeostasis": 0.5,
            "curiosity": 0.5,
        }

        reward, components = calculator.calculate_reward_with_components(gaps, weights)

        assert isinstance(components, dict)
        assert "homeostasis" in components
        assert "curiosity" in components

    def test_negative_reward(self, sample_config):
        """Test that high gaps produce negative rewards"""
        calculator = RewardCalculator(sample_config.get("axiology", {}))

        # All high gaps should produce negative reward
        gaps = {dim: 0.9 for dim in sample_config["axiology"]["dimensions"]}
        weights = {dim: 1.0/8 for dim in sample_config["axiology"]["dimensions"]}

        reward = calculator.calculate_reward(gaps, weights)

        assert reward < 0


class TestGapCalculator:
    """Test gap calculation"""

    def test_calculate_gaps_basic(self, sample_config):
        """Test basic gap calculation"""
        calculator = GapCalculator(sample_config.get("axiology", {}))

        state = {
            "homeostasis": {"value": 0.5},
            "integrity": {"value": 0.8},
            "curiosity": {"value": 0.3},
        }

        gaps = calculator.calculate_gaps(state)

        assert isinstance(gaps, dict)
        assert all(0 <= g <= 1 for g in gaps.values())

    def test_gap_setpoints(self, sample_config):
        """Test that gaps reflect distance from setpoints"""
        calculator = GapCalculator(sample_config.get("axiology", {}))

        # Set homeostasis setpoint to 0.5
        calculator.setpoints["homeostasis"] = 0.5

        state = {
            "homeostasis": {"value": 0.5},  # At setpoint
        }

        gaps = calculator.calculate_gaps(state)

        # Gap should be zero or very small when at setpoint
        assert gaps["homeostasis"] < 0.1

    def test_bounded_gaps(self, sample_config):
        """Test that gaps are properly bounded"""
        calculator = GapCalculator(sample_config.get("axiology", {}))

        state = {
            "homeostasis": {"value": 2.0},  # Out of bounds
            "integrity": {"value": -1.0},  # Out of bounds
        }

        gaps = calculator.calculate_gaps(state)

        # All gaps should still be in [0, 1]
        assert all(0 <= g <= 1 for g in gaps.values())


class TestWeightUpdater:
    """Test weight update mechanism"""

    def test_update_weights_basic(self, sample_config):
        """Test basic weight update"""
        updater = WeightUpdater(sample_config.get("axiology", {}))

        current_weights = {dim: 0.125 for dim in sample_config["axiology"]["dimensions"]}
        gaps = {
            "homeostasis": 0.8,  # High gap
            "curiosity": 0.2,  # Low gap
        }

        new_weights = updater.update_weights(current_weights, gaps)

        # Homeostasis weight should increase
        assert new_weights["homeostasis"] > current_weights["homeostasis"]

    def test_weights_sum_to_one(self, sample_config):
        """Test that weights always sum to 1 (simplex constraint)"""
        updater = WeightUpdater(sample_config.get("axiology", {}))

        current_weights = {dim: 0.125 for dim in sample_config["axiology"]["dimensions"]}
        gaps = {dim: 0.5 for dim in sample_config["axiology"]["dimensions"]}

        new_weights = updater.update_weights(current_weights, gaps)

        weight_sum = sum(new_weights.values())
        assert 0.99 <= weight_sum <= 1.01  # Allow floating point error

    def test_priority_override(self, sample_config):
        """Test priority override for critical drives"""
        updater = WeightUpdater(sample_config.get("axiology", {}))

        current_weights = {dim: 0.125 for dim in sample_config["axiology"]["dimensions"]}
        gaps = {
            "homeostasis": 0.95,  # Critical
            "curiosity": 0.1,
        }

        # With priority override
        new_weights = updater.update_weights(current_weights, gaps, priority_dim="homeostasis")

        # Homeostasis should dominate
        assert new_weights["homeostasis"] > 0.5

    def test_weight_inertia(self, sample_config):
        """Test that weights change gradually (not instantly)"""
        updater = WeightUpdater(sample_config.get("axiology", {}))

        current_weights = {dim: 0.125 for dim in sample_config["axiology"]["dimensions"]}
        gaps = {
            "homeostasis": 0.5,  # Moderate gap (not triggering override)
            "curiosity": 0.1,
        }

        new_weights = updater.update_weights(current_weights, gaps)

        # Change should be gradual (with inertia)
        weight_change = abs(new_weights["homeostasis"] - current_weights["homeostasis"])
        assert weight_change < 0.5  # Not instant jump


class TestValueLearner:
    """Test value learning mechanism (Paper Section 3.12)"""

    def test_value_learner_initialization(self):
        """Test basic initialization"""
        learner = ValueLearner()
        assert learner.params is not None
        assert len(learner.params.setpoints) == 8
        assert learner.config.epsilon < 0.1  # ε << 1

    def test_add_rpe_signal_positive(self):
        """Test adding positive RPE signal"""
        learner = ValueLearner()
        initial_count = len(learner._feedback_buffer)

        # Add positive RPE
        learner.add_rpe_signal(rpe=0.5, active_dimension="homeostasis")

        assert len(learner._feedback_buffer) > initial_count

    def test_add_explicit_feedback(self):
        """Test adding explicit user feedback"""
        learner = ValueLearner()

        # Positive rating
        learner.add_explicit_feedback(rating=0.8, active_dimension="curiosity")
        assert len(learner._feedback_buffer) == 1

        # Negative rating
        learner.add_explicit_feedback(rating=-0.5, active_dimension="efficiency")
        assert len(learner._feedback_buffer) == 2

    def test_slow_learning_rate(self):
        """Test that learning rate ε is small (paper requirement)"""
        import time
        config = ValueLearnerConfig(epsilon=0.01)
        learner = ValueLearner(config)
        current_time = time.time()

        initial_setpoint = learner.params.setpoints["homeostasis"]

        # Add strong positive feedback (5 times to meet minimum)
        for _ in range(5):
            learner.add_explicit_feedback(rating=1.0, active_dimension="homeostasis", timestamp=current_time)

        learner.update(current_time)
        new_setpoint = learner.params.setpoints["homeostasis"]

        # Change should be small (slow learning)
        change = abs(new_setpoint - initial_setpoint)
        assert change < 0.1  # Small change due to ε << 1

    def test_update_requires_minimum_feedback(self):
        """Test that update requires minimum feedback count"""
        import time
        learner = ValueLearner()
        current_time = time.time()

        # Add only 1 feedback (less than min_feedback_count=5)
        learner.add_rpe_signal(rpe=0.5, active_dimension="homeostasis", timestamp=current_time)

        assert not learner.should_update(current_time)

        # Add more feedback to reach minimum (5 total)
        learner.add_rpe_signal(rpe=0.5, active_dimension="homeostasis", timestamp=current_time)
        learner.add_rpe_signal(rpe=0.5, active_dimension="homeostasis", timestamp=current_time)
        learner.add_rpe_signal(rpe=0.5, active_dimension="homeostasis", timestamp=current_time)
        learner.add_rpe_signal(rpe=0.5, active_dimension="homeostasis", timestamp=current_time)

        assert learner.should_update(current_time)

    def test_setpoint_bounds(self):
        """Test that setpoints stay in valid range"""
        import time
        learner = ValueLearner()
        current_time = time.time()

        # Add many negative feedbacks
        for _ in range(10):
            learner.add_explicit_feedback(-1.0, "homeostasis", timestamp=current_time)

        learner.update(current_time)

        # Setpoint should stay >= 0
        assert learner.params.setpoints["homeostasis"] >= 0.0
        assert learner.params.setpoints["homeostasis"] <= 1.0
