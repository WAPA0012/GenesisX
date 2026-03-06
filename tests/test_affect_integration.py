"""
Affect System Integration Tests

Tests the complete affect system flow including:
- RPE computation (scalar and per-dimension)
- Mood updates from RPE
- Stress updates from RPE and failures
- Per-dimension emotional coefficients
- Full affect update cycle

Paper Sections:
- 3.7.2: Per-dimension RPE
- 3.7.3: Mood/Stress dynamics
"""

import pytest
from affect.rpe import (
    compute_rpe,
    compute_per_dimension_rpe,
    compute_weighted_rpe,
    RPEComputer,
)
from affect.mood import (
    update_mood,
    update_mood_per_dimension,
    update_stress_simple,
    update_stress_per_dimension,
    update_affect,
    update_affect_per_dimension,
    AffectConfig,
    DEFAULT_MOOD_COEFFICIENTS,
    DEFAULT_STRESS_COEFFICIENTS,
)
from affect.stress_affect import update_stress, DEFAULT_FAILURE_STRESS_INCREASE


class TestScalarRPE:
    """Test scalar RPE computation."""

    def test_rpe_basic(self):
        """Test basic RPE formula: δ = r + γV(s') - V(s)"""
        reward = 0.5
        value_current = 0.3
        value_next = 0.4
        gamma = 0.97

        rpe = compute_rpe(reward, value_current, value_next, gamma)

        expected = 0.5 + 0.97 * 0.4 - 0.3
        assert rpe == pytest.approx(expected)

    def test_rpe_positive(self):
        """Test positive RPE (better than expected)."""
        rpe = compute_rpe(reward=1.0, value_current=0.0, value_next=0.0, gamma=0.97)
        assert rpe > 0

    def test_rpe_negative(self):
        """Test negative RPE (worse than expected)."""
        rpe = compute_rpe(reward=-1.0, value_current=0.0, value_next=0.0, gamma=0.97)
        assert rpe < 0

    def test_rpe_clipping(self):
        """Test RPE clipping to prevent overflow."""
        # Extreme values should be clipped
        rpe_high = compute_rpe(reward=100, value_current=-100, value_next=100, gamma=0.97)
        rpe_low = compute_rpe(reward=-100, value_current=100, value_next=-100, gamma=0.97)

        assert rpe_high <= 2.0  # Upper clip
        assert rpe_low >= -2.0  # Lower clip


class TestPerDimensionRPE:
    """Test per-dimension RPE computation."""

    def test_per_dimension_rpe_basic(self):
        """Test per-dimension RPE calculation."""
        utilities = {"homeostasis": 0.5, "curiosity": -0.3}
        values_current = {"homeostasis": 0.2, "curiosity": 0.1}
        values_next = {"homeostasis": 0.3, "curiosity": 0.0}

        rpe = compute_per_dimension_rpe(utilities, values_current, values_next)

        # homeostasis: 0.5 + 0.97*0.3 - 0.2 = 0.5 + 0.291 - 0.2 = 0.591
        assert rpe["homeostasis"] == pytest.approx(0.591, rel=1e-3)

        # curiosity: -0.3 + 0.97*0.0 - 0.1 = -0.3 - 0.1 = -0.4
        assert rpe["curiosity"] == pytest.approx(-0.4)

    def test_per_dimension_rpe_missing_dimensions(self):
        """Test handling of missing dimensions in input."""
        utilities = {"homeostasis": 0.5}
        values_current = {}
        values_next = {}

        rpe = compute_per_dimension_rpe(utilities, values_current, values_next)

        # Missing dimensions should default to 0.0
        assert rpe["homeostasis"] == pytest.approx(0.5)


class TestWeightedRPE:
    """Test weighted global RPE computation."""

    def test_weighted_rpe_basic(self):
        """Test weighted sum of per-dimension RPEs."""
        rpe_per_dim = {"homeostasis": 0.5, "curiosity": -0.3}
        weights = {"homeostasis": 0.3, "curiosity": 0.2}

        global_rpe = compute_weighted_rpe(rpe_per_dim, weights)

        expected = 0.3 * 0.5 + 0.2 * (-0.3)  # 0.15 - 0.06 = 0.09
        assert global_rpe == pytest.approx(expected)

    def test_weighted_rpe_missing_weights(self):
        """Test handling of missing weights."""
        rpe_per_dim = {"homeostasis": 0.5, "curiosity": -0.3}
        weights = {"homeostasis": 0.5}  # curiosity missing

        global_rpe = compute_weighted_rpe(rpe_per_dim, weights)

        # Missing weight should default to 0.0
        expected = 0.5 * 0.5 + 0.0 * (-0.3)
        assert global_rpe == pytest.approx(expected)


class TestMoodUpdate:
    """Test mood update from RPE."""

    def test_mood_positive_rpe(self):
        """Test mood increase with positive RPE."""
        initial_mood = 0.5
        delta = 0.3
        k_plus = 0.25

        new_mood = update_mood(initial_mood, delta, k_plus)

        assert new_mood > initial_mood
        assert new_mood == pytest.approx(0.5 + 0.25 * 0.3)

    def test_mood_negative_rpe(self):
        """Test mood decrease with negative RPE."""
        initial_mood = 0.5
        delta = -0.3
        k_minus = 0.30

        new_mood = update_mood(initial_mood, delta, k_minus=k_minus)

        assert new_mood < initial_mood
        assert new_mood == pytest.approx(0.5 + 0.30 * (-0.3))

    def test_mood_upper_bound(self):
        """Test mood clamped to upper bound of 1.0."""
        initial_mood = 0.9
        delta = 1.0  # Large positive RPE

        new_mood = update_mood(initial_mood, delta, k_plus=0.25)

        assert new_mood <= 1.0
        assert new_mood == 1.0

    def test_mood_lower_bound(self):
        """Test mood clamped to lower bound of 0.0."""
        initial_mood = 0.1
        delta = -1.0  # Large negative RPE

        new_mood = update_mood(initial_mood, delta, k_minus=0.30)

        assert new_mood >= 0.0
        assert new_mood == 0.0

    def test_mood_paper_default_parameters(self):
        """Test with paper Appendix A.5 default parameters."""
        initial_mood = 0.5
        delta = 0.2

        # Paper defaults: k_plus = 0.25, k_minus = 0.30
        new_mood = update_mood(initial_mood, delta)

        assert new_mood == pytest.approx(0.5 + 0.25 * 0.2)


class TestMoodUpdatePerDimension:
    """Test per-dimension mood updates."""

    def test_mood_per_dimension_basic(self):
        """Test mood update from per-dimension RPEs."""
        initial_mood = 0.5
        rpe_per_dim = {
            "homeostasis": -0.2,  # Negative impact
            "curiosity": 0.3,      # Positive impact
        }

        new_mood = update_mood_per_dimension(initial_mood, rpe_per_dim)

        # Should change based on weighted coefficients
        assert new_mood != initial_mood
        assert 0.0 <= new_mood <= 1.0

    def test_mood_per_dimension_coefficients(self):
        """Test that different dimensions have different coefficients."""
        rpe_per_dim = {
            "curiosity": 0.5,   # High k_plus (0.15)
            "integrity": 0.5,    # Lower k_plus (0.05)
        }

        delta_curiosity = DEFAULT_MOOD_COEFFICIENTS["curiosity"]["k_plus"] * 0.5
        delta_integrity = DEFAULT_MOOD_COEFFICIENTS["integrity"]["k_plus"] * 0.5

        # Curiosity should have larger mood impact
        assert delta_curiosity > delta_integrity

    def test_mood_per_dimension_bounds(self):
        """Test per-dimension mood updates respect bounds."""
        initial_mood = 0.5
        # Large positive RPEs that would exceed 1.0
        rpe_per_dim = {dim: 1.0 for dim in DEFAULT_MOOD_COEFFICIENTS}

        new_mood = update_mood_per_dimension(initial_mood, rpe_per_dim)

        assert new_mood <= 1.0

        # Large negative RPEs that would go below 0.0
        rpe_per_dim = {dim: -1.0 for dim in DEFAULT_MOOD_COEFFICIENTS}
        new_mood = update_mood_per_dimension(0.5, rpe_per_dim)

        assert new_mood >= 0.0


class TestStressUpdate:
    """Test stress update from RPE."""

    def test_stress_positive_rpe_relief(self):
        """Test stress relief with positive RPE."""
        initial_stress = 0.5
        delta = 0.3
        s_relief = 0.10

        new_stress = update_stress_simple(initial_stress, delta, s_relief=s_relief)

        assert new_stress < initial_stress
        assert new_stress == pytest.approx(0.5 - 0.10 * 0.3)

    def test_stress_negative_rpe_increase(self):
        """Test stress increase with negative RPE."""
        initial_stress = 0.5
        delta = -0.3
        s_gain = 0.20

        new_stress = update_stress_simple(initial_stress, delta, s_gain=s_gain)

        assert new_stress > initial_stress
        assert new_stress == pytest.approx(0.5 + 0.20 * 0.3)

    def test_stress_upper_bound(self):
        """Test stress clamped to upper bound of 1.0."""
        initial_stress = 0.9
        delta = -1.0  # Large negative RPE

        new_stress = update_stress_simple(initial_stress, delta, s_gain=0.20)

        assert new_stress <= 1.0

    def test_stress_lower_bound(self):
        """Test stress clamped to lower bound of 0.0."""
        initial_stress = 0.1
        delta = 1.0  # Large positive RPE

        new_stress = update_stress_simple(initial_stress, delta, s_relief=0.10)

        assert new_stress >= 0.0

    def test_stress_with_failure(self):
        """Test stress increase on failure."""
        initial_stress = 0.3
        delta = 0.0

        # Use decay=0 to test exact failure penalty without natural decay interference
        new_stress = update_stress(initial_stress, delta, failed=True, decay=0)

        assert new_stress > initial_stress
        assert new_stress == pytest.approx(0.3 + DEFAULT_FAILURE_STRESS_INCREASE)

    def test_stress_paper_default_parameters(self):
        """Test with paper Appendix A.5 default parameters."""
        initial_stress = 0.5
        delta = -0.2

        # Paper defaults: s_gain = 0.20, s_relief = 0.10
        # Use decay=0 to test exact RPE impact without natural decay interference
        new_stress = update_stress(initial_stress, delta, decay=0)

        assert new_stress == pytest.approx(0.5 + 0.20 * 0.2)


class TestStressUpdatePerDimension:
    """Test per-dimension stress updates."""

    def test_stress_per_dimension_basic(self):
        """Test stress update from per-dimension RPEs."""
        initial_stress = 0.5
        rpe_per_dim = {
            "homeostasis": -0.2,  # Stress increase
            "meaning": 0.3,        # Stress relief
        }

        new_stress = update_stress_per_dimension(initial_stress, rpe_per_dim)

        # Should change based on weighted coefficients
        assert 0.0 <= new_stress <= 1.0

    def test_stress_per_dimension_coefficients(self):
        """Test that different dimensions have different stress impact."""
        rpe_per_dim = {
            "integrity": -0.5,   # High s_gain (0.20)
            "meaning": -0.5,     # Lower s_gain (0.02)
        }

        delta_integrity = DEFAULT_STRESS_COEFFICIENTS["integrity"]["s_gain"] * 0.5
        delta_meaning = DEFAULT_STRESS_COEFFICIENTS["meaning"]["s_gain"] * 0.5

        # Integrity should have larger stress impact
        assert delta_integrity > delta_meaning


class TestAffectUpdate:
    """Test combined mood and stress updates."""

    def test_affect_update_basic(self):
        """Test updating both mood and stress together."""
        initial_mood = 0.5
        initial_stress = 0.3
        delta = 0.2

        new_mood, new_stress = update_affect(
            initial_mood, initial_stress, delta,
            k_plus=0.25, k_minus=0.30,
            s_gain=0.20, s_relief=0.10
        )

        # Positive RPE: mood up, stress down
        assert new_mood > initial_mood
        assert new_stress < initial_stress

    def test_affect_update_negative_rpe(self):
        """Test affect update with negative RPE."""
        initial_mood = 0.5
        initial_stress = 0.3
        delta = -0.2

        new_mood, new_stress = update_affect(
            initial_mood, initial_stress, delta,
            k_plus=0.25, k_minus=0.30,
            s_gain=0.20, s_relief=0.10
        )

        # Negative RPE: mood down, stress up
        assert new_mood < initial_mood
        assert new_stress > initial_stress

    def test_affect_update_per_dimension(self):
        """Test per-dimension affect update."""
        initial_mood = 0.5
        initial_stress = 0.3
        rpe_per_dim = {
            "homeostasis": -0.3,
            "curiosity": 0.2,
            "meaning": 0.1,
        }

        new_mood, new_stress = update_affect_per_dimension(
            initial_mood, initial_stress, rpe_per_dim
        )

        # Both should be updated
        assert 0.0 <= new_mood <= 1.0
        assert 0.0 <= new_stress <= 1.0


class TestRPEComputer:
    """Test RPEComputer class."""

    def test_rpe_computer_initialization(self):
        """Test RPEComputer initialization."""
        computer = RPEComputer()

        # 论文 Section 3.5.1: 5维核心价值向量
        assert len(computer.dimensions) == 5
        assert computer.gamma == 0.97
        assert all(v == 0.0 for v in computer._value_predictions.values())

    def test_rpe_computer_custom_dimensions(self):
        """Test RPEComputer with custom dimensions."""
        dimensions = ["homeostasis", "curiosity"]
        computer = RPEComputer(dimensions=dimensions)

        assert computer.dimensions == dimensions
        assert set(computer._value_predictions.keys()) == set(dimensions)

    def test_rpe_computer_compute(self):
        """Test RPEComputer compute method."""
        computer = RPEComputer()

        utilities = {
            "homeostasis": 0.5,
            "curiosity": -0.3,
        }
        weights = {
            "homeostasis": 0.3,
            "curiosity": 0.2,
        }

        result = computer.compute(utilities, weights)

        assert "per_dimension" in result
        assert "global" in result
        assert "values_current" in result
        assert "values_next" in result

    def test_rpe_computer_value_prediction_update(self):
        """Test that value predictions are updated after compute."""
        computer = RPEComputer()

        utilities = {"homeostasis": 0.5}
        weights = {"homeostasis": 0.3}

        initial_prediction = computer.get_value_predictions()["homeostasis"]

        computer.compute(utilities, weights)

        new_prediction = computer.get_value_predictions()["homeostasis"]

        # Prediction should be updated (EMA)
        assert new_prediction != initial_prediction

    def test_rpe_computer_set_value_predictions(self):
        """Test setting value predictions."""
        computer = RPEComputer()

        custom_values = {"homeostasis": 0.5, "curiosity": 0.3}
        computer.set_value_predictions(custom_values)

        retrieved = computer.get_value_predictions()

        assert retrieved["homeostasis"] == 0.5
        assert retrieved["curiosity"] == 0.3


class TestAffectConfig:
    """Test AffectConfig configuration."""

    def test_affect_config_defaults(self):
        """Test default affect configuration."""
        config = AffectConfig()

        assert config.k_plus == 0.25
        assert config.k_minus == 0.30
        assert config.s_gain == 0.20
        assert config.s_relief == 0.10
        assert config.mood_coefficients is not None
        assert config.stress_coefficients is not None

    def test_affect_config_custom_values(self):
        """Test custom affect configuration."""
        config = AffectConfig(
            k_plus=0.15,
            k_minus=0.20,
            s_gain=0.25,
            s_relief=0.15,
        )

        assert config.k_plus == 0.15
        assert config.k_minus == 0.20
        assert config.s_gain == 0.25
        assert config.s_relief == 0.15

    def test_affect_config_from_global_config(self):
        """Test creating AffectConfig from global config."""
        global_config = {
            "affect": {
                "k_plus": 0.15,
                "k_minus": 0.20,
                "s_gain": 0.25,
                "s_relief": 0.15,
            }
        }

        config = AffectConfig.from_global_config(global_config)

        assert config.k_plus == 0.15
        assert config.k_minus == 0.20
        assert config.s_gain == 0.25
        assert config.s_relief == 0.15


class TestFullAffectCycle:
    """End-to-end tests of the affect system cycle."""

    def test_full_positive_cycle(self):
        """Test full cycle with positive RPE."""
        # Initial state
        mood = 0.5
        stress = 0.3

        # Positive outcome
        utilities = {"homeostasis": 0.5, "curiosity": 0.3}
        weights = {"homeostasis": 0.3, "curiosity": 0.2}

        # Compute RPE
        computer = RPEComputer()
        rpe_result = computer.compute(utilities, weights)
        delta = rpe_result["global"]

        # Update affect
        new_mood, new_stress = update_affect(mood, stress, delta)

        # Verify: mood up, stress down
        assert new_mood > mood
        assert new_stress < stress

    def test_full_negative_cycle(self):
        """Test full cycle with negative RPE."""
        # Initial state
        mood = 0.5
        stress = 0.3

        # Negative outcome
        utilities = {"homeostasis": -0.5, "integrity": -0.3}
        weights = {"homeostasis": 0.3, "integrity": 0.2}

        # Compute RPE
        computer = RPEComputer()
        rpe_result = computer.compute(utilities, weights)
        delta = rpe_result["global"]

        # Update affect
        new_mood, new_stress = update_affect(mood, stress, delta)

        # Verify: mood down, stress up
        assert new_mood < mood
        assert new_stress > stress

    def test_full_per_dimension_cycle(self):
        """Test full per-dimension affect cycle."""
        # Initial state
        mood = 0.5
        stress = 0.3

        # Mixed outcome
        utilities = {
            "homeostasis": -0.3,  # Negative
            "curiosity": 0.5,      # Positive
            "meaning": 0.2,        # Positive
        }
        weights = {
            "homeostasis": 0.25,
            "curiosity": 0.25,
            "meaning": 0.25,
        }

        # Compute RPE
        computer = RPEComputer()
        rpe_result = computer.compute(utilities, weights)

        # Update affect with per-dimension RPE
        new_mood, new_stress = update_affect_per_dimension(
            mood, stress, rpe_result["per_dimension"]
        )

        # Verify bounds
        assert 0.0 <= new_mood <= 1.0
        assert 0.0 <= new_stress <= 1.0

    def test_affect_system_repeated_updates(self):
        """Test affect stability over multiple updates."""
        mood = 0.5
        stress = 0.3
        computer = RPEComputer()

        # Run for 10 ticks with varying RPE
        for i in range(10):
            # Alternating positive/negative RPE
            delta = 0.2 if i % 2 == 0 else -0.1

            mood, stress = update_affect(mood, stress, delta)

            # Verify bounds maintained
            assert 0.0 <= mood <= 1.0
            assert 0.0 <= stress <= 1.0


class TestPaperFormulaCompliance:
    """Test compliance with paper formulas."""

    def test_mood_formula_section_3_7_3(self):
        """Test mood formula: Mood_{t+1} = clip(Mood_t + k_+ * max(δ,0) - k_- * max(-δ,0))"""
        mood_t = 0.5
        delta = 0.3
        k_plus = 0.25
        k_minus = 0.30

        mood_t1 = update_mood(mood_t, delta, k_plus, k_minus)

        # Manual calculation
        expected = 0.5 + 0.25 * max(0.3, 0) - 0.30 * max(-0.3, 0)
        expected = max(0.0, min(1.0, expected))

        assert mood_t1 == pytest.approx(expected)

    def test_stress_formula_section_3_7_3(self):
        """Test stress formula: Stress_{t+1} = clip(Stress_t + s*max(-δ,0) - s'*max(δ,0))"""
        stress_t = 0.5
        delta = -0.3
        s = 0.20
        s_prime = 0.10

        stress_t1 = update_stress_simple(stress_t, delta, s, s_prime)

        # Manual calculation (without decay)
        expected = 0.5 + 0.20 * max(0.3, 0) - 0.10 * max(-0.3, 0)
        expected = max(0.0, min(1.0, expected))

        assert stress_t1 == pytest.approx(expected)

    def test_rpe_formula_section_3_7_2(self):
        """Test RPE formula: δ^(i) = u^(i) + γV^(i)(s') - V^(i)(s)"""
        utilities = {"homeostasis": 0.5}
        values_current = {"homeostasis": 0.2}
        values_next = {"homeostasis": 0.3}
        gamma = 0.97

        rpe = compute_per_dimension_rpe(utilities, values_current, values_next, gamma)

        # Manual calculation
        expected = 0.5 + 0.97 * 0.3 - 0.2

        assert rpe["homeostasis"] == pytest.approx(expected)
