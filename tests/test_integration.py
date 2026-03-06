"""Integration tests for Genesis X.

Tests the complete system flow according to paper specifications.
"""
import pytest
from datetime import datetime
from pathlib import Path
import tempfile

from core.life_loop import LifeLoop
from core.state import GlobalState
from common.models import ValueDimension, Action, Observation
from affect.mood import update_mood, update_stress, update_affect
from affect.rpe import compute_rpe, compute_per_dimension_rpe, RPEComputer
from axiology.weights import compute_weights, WeightUpdater
from axiology.parameters import get_default_parameters
from core.exceptions import (
    ErrorHandler,
    ToolExecutionError,
    CircuitBreaker,
    ErrorSeverity,
)
from memory.semantic_novelty import SemanticNoveltyCalculator


class TestAxiologyParameters:
    """Test paper Appendix A parameter alignment."""

    def test_default_parameters_match_paper(self):
        """Verify default parameters match Appendix A specifications."""
        params = get_default_parameters()

        # Core hyperparameters (Appendix A.5)
        assert params.core.gamma == 0.97, "γ should be 0.97"
        assert params.core.tau == 4.0, "τ should be 4.0"
        assert params.core.k_plus == 0.25, "k_+ should be 0.25"
        assert params.core.k_minus == 0.30, "k_- should be 0.30"
        assert params.core.stress_gain == 0.20, "s should be 0.20"
        assert params.core.stress_relief == 0.10, "s' should be 0.10"
        assert params.core.alpha_V == 0.05, "α_V should be 0.05"
        assert params.core.epsilon == 0.001, "ε should be 0.001"

        # Memory parameters (Appendix A.7)
        assert params.memory.fatigue_sleep_threshold == 0.75
        assert params.memory.Q_min_insight == 0.65

        # Time parameters
        assert params.time.neglect_halflife_hours == 24.0

    def test_parameter_serialization(self):
        """Test parameters can be serialized for reproducibility."""
        params = get_default_parameters()
        param_dict = params.to_dict()

        assert "core" in param_dict
        assert "memory" in param_dict
        assert param_dict["core"]["gamma"] == 0.97


class TestMoodAndStress:
    """Test mood and stress update functions (Paper Section 3.7.3)."""

    def test_mood_update_positive_rpe(self):
        """Test mood increases with positive RPE."""
        initial_mood = 0.5
        delta = 0.5  # Positive RPE

        new_mood = update_mood(initial_mood, delta, k_plus=0.25, k_minus=0.30)

        assert new_mood > initial_mood
        assert new_mood == 0.5 + 0.25 * 0.5

    def test_mood_update_negative_rpe(self):
        """Test mood decreases with negative RPE."""
        initial_mood = 0.5
        delta = -0.5  # Negative RPE

        new_mood = update_mood(initial_mood, delta, k_plus=0.25, k_minus=0.30)

        assert new_mood < initial_mood
        assert new_mood == 0.5 - 0.30 * 0.5

    def test_mood_clipping(self):
        """Test mood is clipped to [0, 1] range."""
        # Test upper bound
        mood = update_mood(0.9, 1.0, k_plus=0.25)
        assert mood <= 1.0

        # Test lower bound
        mood = update_mood(0.1, -1.0, k_minus=0.30)
        assert mood >= 0.0

    def test_stress_update_positive_rpe(self):
        """Test stress decreases with positive RPE."""
        initial_stress = 0.5
        delta = 0.5  # Positive RPE

        new_stress = update_stress(initial_stress, delta, s_gain=0.20, s_relief=0.10, decay=0)

        assert new_stress < initial_stress
        assert new_stress == 0.5 - 0.10 * 0.5

    def test_stress_update_negative_rpe(self):
        """Test stress increases with negative RPE."""
        initial_stress = 0.5
        delta = -0.5  # Negative RPE

        new_stress = update_stress(initial_stress, delta, s_gain=0.20, s_relief=0.10, decay=0)

        assert new_stress > initial_stress
        assert new_stress == 0.5 + 0.20 * 0.5

    def test_update_affect_combined(self):
        """Test combined mood and stress update."""
        mood, stress = 0.5, 0.5
        delta = 0.3

        new_mood, new_stress = update_affect(mood, stress, delta)

        assert new_mood > mood
        assert new_stress < stress


class TestRPEComputation:
    """Test RPE computation (Paper Section 3.7.2)."""

    def test_scalar_rpe(self):
        """Test scalar RPE computation: δ = r + γV(s') - V(s)."""
        reward = 1.0
        value_current = 0.5
        value_next = 0.7
        gamma = 0.97

        delta = compute_rpe(reward, value_current, value_next, gamma)

        expected = 1.0 + 0.97 * 0.7 - 0.5
        assert abs(delta - expected) < 1e-6

    def test_per_dimension_rpe(self):
        """Test per-dimension RPE computation."""
        utilities = {"homeostasis": 0.5, "curiosity": 0.3}
        values_current = {"homeostasis": 0.4, "curiosity": 0.2}
        values_next = {"homeostasis": 0.6, "curiosity": 0.3}

        rpe_per_dim = compute_per_dimension_rpe(utilities, values_current, values_next)

        assert "homeostasis" in rpe_per_dim
        assert "curiosity" in rpe_per_dim

    def test_rpe_computer_state_tracking(self):
        """Test RPEComputer tracks value predictions."""
        computer = RPEComputer(gamma=0.97)

        # Initial value predictions should be zero
        assert all(v == 0.0 for v in computer.get_value_predictions().values())

        # After compute, predictions should update
        utilities = {"homeostasis": 0.5}
        weights = {"homeostasis": 0.5}

        result = computer.compute(utilities, weights)

        # Predictions should have changed
        predictions = computer.get_value_predictions()
        assert predictions["homeostasis"] != 0.0


class TestDynamicWeights:
    """Test dynamic weight computation (Paper Section 3.6)."""

    def test_softmax_weights(self):
        """Test weights are computed via softmax and sum to 1."""
        gaps = {
            ValueDimension.HOMEOSTASIS: 0.5,
            ValueDimension.CURIOSITY: 0.3,
            ValueDimension.ATTACHMENT: 0.2,
        }
        biases = {dim: 1.0 for dim in gaps.keys()}

        weights = compute_weights(gaps, biases, temperature=4.0)

        # All weights should be positive
        assert all(w > 0 for w in weights.values())

        # Weights should sum to 1
        total = sum(weights.values())
        assert abs(total - 1.0) < 1e-6

    def test_weight_influence(self):
        """Test larger gaps result in larger weights."""
        gaps = {
            ValueDimension.HOMEOSTASIS: 0.8,  # Larger gap
            ValueDimension.CURIOSITY: 0.1,   # Smaller gap
        }
        biases = {ValueDimension.HOMEOSTASIS: 1.0, ValueDimension.CURIOSITY: 1.0}

        weights = compute_weights(gaps, biases, temperature=4.0)

        # Homeostasis should have larger weight due to larger gap
        assert weights[ValueDimension.HOMEOSTASIS] > weights[ValueDimension.CURIOSITY]

    def test_personality_bias(self):
        """Test personality bias affects weights."""
        gaps = {
            ValueDimension.HOMEOSTASIS: 0.5,
            ValueDimension.CURIOSITY: 0.5,
        }

        # Bias toward curiosity
        biases = {
            ValueDimension.HOMEOSTASIS: 1.0,
            ValueDimension.CURIOSITY: 2.0,  # Higher bias
        }

        weights = compute_weights(gaps, biases, temperature=4.0)

        # Curiosity should have larger weight due to higher bias
        assert weights[ValueDimension.CURIOSITY] > weights[ValueDimension.HOMEOSTASIS]


class TestWeightUpdater:
    """Test WeightUpdater with priority override and soft override."""

    def test_priority_override_trigger(self):
        """Test priority override triggers when gap exceeds threshold."""
        updater = WeightUpdater()

        current_weights = {
            "homeostasis": 0.1,
            "curiosity": 0.4,
            "attachment": 0.3,
        }

        # High homeostasis gap should trigger override
        gaps = {"homeostasis": 0.9, "curiosity": 0.1, "attachment": 0.1}

        updated = updater.update_weights(current_weights, gaps)

        # Homeostasis should have boosted weight
        assert updated["homeostasis"] > 0.5

    def test_soft_override_preserves_learning(self):
        """Test soft override preserves learned weights partially."""
        updater = WeightUpdater()
        cfg = updater.priority_config
        cfg.soft_override_factor = 0.3  # 保留30%学习权重

        current_weights = {
            "homeostasis": 0.1,
            "curiosity": 0.6,  # Learned preference
            "attachment": 0.3,
        }

        gaps = {"homeostasis": 0.9, "curiosity": 0.1, "attachment": 0.1}

        updated = updater.update_weights(
            current_weights,
            gaps,
            biases={"homeostasis": 1.0, "curiosity": 2.0, "attachment": 1.0}
        )

        # Curiosity should still have some weight due to soft override
        assert updated.get("curiosity", 0) > 0

    def test_override_state_persistence(self):
        """Test override state can be persisted and restored."""
        updater = WeightUpdater()

        # Manually set override state
        updater._override_active = {"homeostasis"}

        state = updater.get_override_state()
        assert "homeostasis" in state["override_active"]

        # Create new updater and restore state
        new_updater = WeightUpdater()
        new_updater.set_override_state(state)

        assert "homeostasis" in new_updater._override_active


class TestErrorHandling:
    """Test error handling (Paper Section 3.13)."""

    def test_tool_execution_error_retry(self):
        """Test tool error triggers retry strategy."""
        handler = ErrorHandler()

        error = ToolExecutionError(
            "API timeout",
            tool_id="web_search",
            attempt=1,
            max_attempts=3,
        )

        response = handler.handle(error, context={})

        assert response["action"] == "retry"
        assert response["tool_id"] == "web_search"

    def test_consecutive_errors_trigger_disable(self):
        """Test consecutive errors disable tool."""
        handler = ErrorHandler()

        # Simulate multiple errors
        for _ in range(5):
            error = ToolExecutionError(
                "API timeout",
                tool_id="web_search",
                attempt=1,
                max_attempts=3,
            )
            handler.handle(error, context={})

        # Fifth error should trigger disable
        response = handler.handle(error, context={})
        assert response["action"] == "disable_tool"

    def test_circuit_breaker(self):
        """Test circuit breaker opens after threshold."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)

        # Should allow requests initially
        assert cb.allow_request() is True

        # Record failures
        for _ in range(3):
            cb.on_failure()

        # Should now be open
        assert cb.allow_request() is False
        assert cb.get_state()["state"] == "open"

    def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovers after timeout."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        # Trigger circuit breaker
        for _ in range(2):
            cb.on_failure()

        assert cb.allow_request() is False

        # Wait for recovery timeout
        import time
        time.sleep(0.15)

        # Should allow request in half-open state
        assert cb.allow_request() is True


class TestSemanticNovelty:
    """Test semantic embedding novelty (Paper Section 3.10.4)."""

    def test_novelty_calculation(self):
        """Test novelty score computation."""
        calculator = SemanticNoveltyCalculator()

        insight = "Users prefer short responses"
        existing = [
            "Users like concise answers",
            "Long responses are unpopular",
        ]

        novelty, is_novel = calculator.compute_novelty(insight, existing, threshold=0.85)

        # Novelty should be in [0, 1]
        assert 0 <= novelty <= 1

    def test_novelty_with_empty_existing(self):
        """Test novelty is 1.0 when no existing texts."""
        calculator = SemanticNoveltyCalculator()

        insight = "Users prefer short responses"
        novelty, is_novel = calculator.compute_novelty(insight, [], threshold=0.85)

        assert novelty == 1.0
        assert is_novel is True

    def test_cosine_similarity(self):
        """Test cosine similarity computation."""
        import numpy as np

        calculator = SemanticNoveltyCalculator()

        # Identical vectors
        v1 = np.array([1.0, 0.0, 0.0])
        v2 = np.array([1.0, 0.0, 0.0])
        sim = calculator.cosine_similarity(v1, v2)
        assert abs(sim - 1.0) < 1e-6

        # Orthogonal vectors
        v3 = np.array([1.0, 0.0, 0.0])
        v4 = np.array([0.0, 1.0, 0.0])
        sim = calculator.cosine_similarity(v3, v4)
        assert abs(sim - 0.0) < 1e-6


class TestLifeLoopIntegration:
    """Integration tests for the main life loop."""

    @pytest.fixture
    def temp_run_dir(self):
        """Create temporary directory for run artifacts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def basic_config(self):
        """Basic configuration for testing."""
        return {
            "runtime": {"max_ticks": 10, "tick_dt": 1.0},
            "value_setpoints": {
                "tau": 4.0,
                "value_dimensions": {
                    "homeostasis": {"setpoint": 0.7},
                    "attachment": {"setpoint": 0.7},
                }
            },
            "genome": {
                "affect": {
                    "gamma": 0.97,
                    "stress_gain": 0.20,
                    "stress_relief": 0.10,
                }
            },
        }

    def test_lifeloop_initialization(self, temp_run_dir, basic_config):
        """Test life loop initializes correctly."""
        loop = LifeLoop(basic_config, temp_run_dir)

        assert loop.state is not None
        assert loop.session_id is not None
        assert loop.organs is not None
        assert loop.weight_updater is not None
        assert loop.value_learner is not None

    def test_lifeloop_single_tick(self, temp_run_dir, basic_config):
        """Test executing a single tick."""
        loop = LifeLoop(basic_config, temp_run_dir)

        episode = loop.tick(0)

        assert episode.tick == 0
        assert episode.session_id == loop.session_id
        assert episode.action is not None

    def test_lifeloop_session(self, temp_run_dir, basic_config):
        """Test running a complete session."""
        loop = LifeLoop(basic_config, temp_run_dir)

        loop.run_session(max_ticks=5)

        # Check episode file was created
        episode_file = temp_run_dir / "episodes.jsonl"
        assert episode_file.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
