"""Test suite for 5 value dimensions (Paper-Compliant v14).

Tests each dimension's feature extraction and utility computation against
the paper formulas (Section 3.5.1, 3.5.2, Appendix A.4).

Paper References:
- Section 3.5.1: 5维核心价值向量定义
- Section 3.5.2: 局部效用函数
- Appendix A.4: Setpoints and Feature Definitions
- Appendix A.5: Default Hyperparameters

Each test validates:
1. Feature values are in [0, 1]
2. Utility values are in [-1, 1]
3. Formulas match the paper exactly
"""

import pytest
import math
from axiology.feature_extractors import (
    extract_homeostasis,
    extract_attachment,
    compute_neglect_penalty,
    extract_curiosity,
    extract_competence,
    extract_safety,
    compute_risk_score,
    extract_all_features,
    DEFAULT_SETPOINTS,
)
from axiology.value_dimensions import (
    ValueDimension,
    compute_drive_gaps,
    validate_feature_ranges,
    validate_utility_ranges,
)
from common.models import ValueDimension as CommonValueDimension
from common.constants import VALUE_SYSTEM


class TestHomeostasisDimension:
    """Test Homeostasis dimension (Section 3.5.2 (1))."""

    def test_homeostasis_formula(self):
        """Test paper formula: f^{homeo}(S_t) = (1/3) * (C/C* + M/M* + (1-S)/(1-S*))"""
        # 论文设定点: H* = (0.70, 0.70, 0.80)
        # 其中第三项是 1-Stress* = 0.80, 所以 Stress* = 0.20

        state = {
            "compute": 0.70,  # 正好在设定点
            "memory": 0.70,   # 正好在设定点
            "stress": 0.20,   # 正好在设定点
        }

        feature = extract_homeostasis(state)

        # 当所有值都在设定点时，特征应该接近 1.0
        assert feature == pytest.approx(1.0, abs=0.01), \
            f"Expected ~1.0 at setpoint, got {feature}"

    def test_homeostasis_low_resources(self):
        """Test homeostasis with low resources."""
        state = {
            "compute": 0.3,   # 低于设定点
            "memory": 0.4,    # 低于设定点
            "stress": 0.6,    # 高于设定点
        }

        feature = extract_homeostasis(state)

        # 低资源/高压力应该产生较低的特征值
        assert feature < 0.7, f"Expected low feature for poor state, got {feature}"
        assert 0.0 <= feature <= 1.0

    def test_homeostasis_range(self):
        """Test that homeostasis feature is always in [0, 1]."""
        for compute in [0.0, 0.2, 0.5, 0.8, 1.0]:
            for memory in [0.0, 0.2, 0.5, 0.8, 1.0]:
                for stress in [0.0, 0.2, 0.5, 0.8, 1.0]:
                    state = {"compute": compute, "memory": memory, "stress": stress}
                    feature = extract_homeostasis(state)
                    assert 0.0 <= feature <= 1.0, \
                        f"Feature out of range: C={compute}, M={memory}, S={stress} -> {feature}"

    def test_homeostasis_memory_included(self):
        """Test that Memory is included in homeostasis (v14 fix)."""
        # 论文 Appendix A.4: H_t = (Compute_t, Memory_t, 1-Stress_t)
        state = {
            "compute": 0.8,
            "memory": 0.3,   # Memory 显著低于设定点 0.7
            "stress": 0.2,
        }

        feature = extract_homeostasis(state)

        # 低 Memory 应该降低特征值
        # 计算: (0.8/0.7 + 0.3/0.7 + 0.8/0.8) / 3
        # = (1.14 + 0.43 + 1.0) / 3 = 2.57 / 3 = 0.86
        assert feature < 0.9, f"Memory should affect homeostasis feature, got {feature}"


class TestAttachmentDimension:
    """Test Attachment dimension (Section 3.5.2 (2))."""

    def test_neglect_formula(self):
        """Test paper formula: Neglect(Δt) = 1 - 2^(-Δt/T_half)"""
        # T_half = 24 hours

        # 0 小时无忽视
        assert compute_neglect_penalty(0.0) == 0.0

        # 24 小时半衰期: Neglect = 1 - 2^(-1) = 1 - 0.5 = 0.5
        neglect_24h = compute_neglect_penalty(24.0, 24.0)
        assert neglect_24h == pytest.approx(0.5, abs=0.01), \
            f"Expected 0.5 at 24h, got {neglect_24h}"

        # 48 小时: Neglect = 1 - 2^(-2) = 1 - 0.25 = 0.75
        neglect_48h = compute_neglect_penalty(48.0, 24.0)
        assert neglect_48h == pytest.approx(0.75, abs=0.01), \
            f"Expected 0.75 at 48h, got {neglect_48h}"

    def test_attachment_formula(self):
        """Test paper formula: f^{attach}(S_t) = Relationship_t * (1 - Neglect(Δt))"""
        # 高关系，无忽视
        state = {"relationship": 0.8, "time_since_interaction": 0.0}
        feature = extract_attachment(state)
        assert feature == pytest.approx(0.8, abs=0.01), \
            f"Expected 0.8 (no neglect), got {feature}"

        # 高关系，24小时忽视
        state = {"relationship": 0.8, "time_since_interaction": 24.0}
        feature = extract_attachment(state)
        # f = 0.8 * (1 - 0.5) = 0.8 * 0.5 = 0.4
        expected = 0.8 * 0.5
        assert feature == pytest.approx(expected, abs=0.01), \
            f"Expected {expected}, got {feature}"

    def test_attachment_range(self):
        """Test that attachment feature is always in [0, 1]."""
        for relationship in [0.0, 0.3, 0.5, 0.7, 1.0]:
            for time_delta in [0.0, 6.0, 12.0, 24.0, 48.0, 96.0]:
                state = {
                    "relationship": relationship,
                    "time_since_interaction": time_delta
                }
                feature = extract_attachment(state)
                assert 0.0 <= feature <= 1.0, \
                    f"Feature out of range: R={relationship}, t={time_delta} -> {feature}"

    def test_attachment_fallback_to_bond_trust(self):
        """Test fallback when relationship is not available."""
        state = {
            "bond": 0.6,
            "trust": 0.8,
            "time_since_interaction": 0.0
        }
        feature = extract_attachment(state)
        # 应该使用 (bond + trust) / 2 = 0.7
        expected = 0.7
        assert feature == pytest.approx(expected, abs=0.01), \
            f"Expected {expected}, got {feature}"


class TestCuriosityDimension:
    """Test Curiosity dimension (Section 3.5.2 (3))."""

    def test_curiosity_formula(self):
        """Test paper formula: f^{cur}(S_t) = 0.7 * Novelty_t + 0.3 * EMA(Q^{insight})"""
        # 高新颖度，中等洞察
        state = {"novelty": 0.9, "boredom": 0.1}
        context = {"insight_quality_ema": 0.5}
        feature = extract_curiosity(state, context)

        expected = 0.7 * 0.9 + 0.3 * 0.5  # = 0.63 + 0.15 = 0.78
        assert feature == pytest.approx(expected, abs=0.01), \
            f"Expected {expected}, got {feature}"

    def test_curiosity_with_semantic_novelty(self):
        """Test curiosity uses semantic novelty when available."""
        state = {
            "observation_text": "A completely new topic",
            "boredom": 0.5
        }
        context = {
            "recent_memories": ["Old memories about weather"],
            "insight_quality_ema": 0.5
        }
        feature = extract_curiosity(state, context)

        # 应该计算语义新颖度而非简单的 1-boredom
        assert 0.0 <= feature <= 1.0
        # 由于新话题与旧记忆不同，新颖度应该较高
        assert feature > 0.3

    def test_curiosity_boredom_fallback(self):
        """Test curiosity falls back to boredom when no other data."""
        state = {"boredom": 0.7}  # 高无聊
        context = {}
        feature = extract_curiosity(state, context)

        # 回退: novelty = 1 - boredom = 0.3
        # EMA 默认 0.5
        expected = 0.7 * 0.3 + 0.3 * 0.5  # = 0.21 + 0.15 = 0.36
        assert feature == pytest.approx(expected, abs=0.1), \
            f"Expected ~{expected}, got {feature}"

    def test_curiosity_range(self):
        """Test that curiosity feature is always in [0, 1]."""
        for novelty in [0.0, 0.3, 0.5, 0.7, 1.0]:
            for insight_ema in [0.0, 0.3, 0.5, 0.7, 1.0]:
                state = {"novelty": novelty}
                context = {"insight_quality_ema": insight_ema}
                feature = extract_curiosity(state, context)
                assert 0.0 <= feature <= 1.0, \
                    f"Feature out of range: N={novelty}, I={insight_ema} -> {feature}"


class TestCompetenceDimension:
    """Test Competence dimension (Section 3.5.2 (4))."""

    def test_competence_formula(self):
        """Test paper formula: f^{cmp}(S_t) = EMA_{α_Q}(Q_t)"""
        # 预计算的 EMA
        state = {}
        context = {"quality_score_ema": 0.8}
        feature = extract_competence(state, context)

        assert feature == pytest.approx(0.8, abs=0.01), \
            f"Expected 0.8, got {feature}"

    def test_competence_fallback_to_quality(self):
        """Test competence falls back to quality_score when no EMA."""
        state = {}
        context = {"quality_score": 0.7}
        feature = extract_competence(state, context)

        assert feature == pytest.approx(0.7, abs=0.01), \
            f"Expected 0.7, got {feature}"

    def test_competence_fallback_to_success_rate(self):
        """Test competence falls back to success_rate."""
        state = {}
        context = {"success_rate": 0.6}
        feature = extract_competence(state, context)

        assert feature == pytest.approx(0.6, abs=0.01), \
            f"Expected 0.6, got {feature}"

    def test_competence_default(self):
        """Test competence default when no data available."""
        state = {}
        context = {}
        feature = extract_competence(state, context)

        assert feature == 0.5, "Default competence should be 0.5"

    def test_competence_range(self):
        """Test that competence feature is always in [0, 1]."""
        for quality in [0.0, 0.3, 0.5, 0.7, 1.0]:
            state = {}
            context = {"quality_score": quality}
            feature = extract_competence(state, context)
            assert 0.0 <= feature <= 1.0


class TestSafetyDimension:
    """Test Safety dimension (Section 3.5.2 (5))."""

    def test_safety_formula(self):
        """Test paper formula: f^{safe}(S_t) = 1 - RiskScore(S_t, a_t)"""
        # 无风险状态
        state = {"recent_errors": 0, "resource_pressure": 0.0, "stress": 0.0}
        context = {"last_action": None}
        feature = extract_safety(state, context)

        # 应该接近 1.0（高安全）
        assert feature > 0.8, f"Expected high safety, got {feature}"

    def test_risk_score_with_tool(self):
        """Test risk score considers tool risk level."""
        # 高风险工具
        action = {"tool_id": "code_exec"}
        state = {"recent_errors": 0, "resource_pressure": 0.0, "stress": 0.0}
        risk = compute_risk_score(state, action)

        # code_exec 工具风险权重是 1.0，但在无错误时
        # risk = 0.3*0 + 0.4*1.0 + 0.2*0 + 0.1*0 = 0.4
        assert risk >= 0.3, f"Expected high risk for code_exec, got {risk}"

        # 低风险工具
        action = {"tool_id": "chat"}
        risk = compute_risk_score(state, action)
        # chat 工具风险是 0.0
        assert risk < 0.2, f"Expected low risk for chat, got {risk}"

    def test_risk_score_with_errors(self):
        """Test risk score considers recent errors."""
        state = {
            "recent_errors": 5,  # 多个错误
            "resource_pressure": 0.0,
            "stress": 0.0
        }
        risk = compute_risk_score(state)

        # 错误惩罚上限是 0.5: error_penalty = min(0.5, 5*0.1) = 0.5
        # risk = 0.3*0.5 + 0.4*0 + 0.2*0 + 0.1*0 = 0.15
        # 但这实际上限制了误差的最大影响
        assert risk >= 0.1, f"Errors should increase risk, got {risk}"

    def test_safety_range(self):
        """Test that safety feature is always in [0, 1]."""
        for errors in [0, 1, 3, 5, 10]:
            for pressure in [0.0, 0.3, 0.6, 0.9]:
                for stress in [0.0, 0.3, 0.6, 0.9]:
                    state = {
                        "recent_errors": errors,
                        "resource_pressure": pressure,
                        "stress": stress
                    }
                    feature = extract_safety(state, {})
                    assert 0.0 <= feature <= 1.0, \
                        f"Feature out of range: e={errors}, p={pressure}, s={stress} -> {feature}"


class TestSetpoints:
    """Test setpoint definitions match paper (Appendix A.4)."""

    def test_setpoint_values(self):
        """Test that setpoints match paper Appendix A.4."""
        # 论文 Appendix A.4 默认设定点
        expected = {
            ValueDimension.HOMEOSTASIS: 0.85,
            ValueDimension.ATTACHMENT: 0.70,
            ValueDimension.CURIOSITY: 0.60,
            ValueDimension.COMPETENCE: 0.75,
            ValueDimension.SAFETY: 0.80,
        }

        for dim, expected_value in expected.items():
            actual = DEFAULT_SETPOINTS[dim]
            assert actual == expected_value, \
                f"{dim}: expected {expected_value}, got {actual}"

    def test_constants_setpoints(self):
        """Test that constants.py has correct setpoints."""
        # Homeostasis
        assert VALUE_SYSTEM.HOMEOSTASIS_SETPOINT_COMPUTE == 0.70
        assert VALUE_SYSTEM.HOMEOSTASIS_SETPOINT_MEMORY == 0.70
        assert VALUE_SYSTEM.HOMEOSTASIS_SETPOINT_STRESS == 0.20
        assert VALUE_SYSTEM.HOMEOSTASIS_SETPOINT_FEATURE == 0.85

        # Other dimensions
        assert VALUE_SYSTEM.ATTACHMENT_SETPOINT_FEATURE == 0.70
        assert VALUE_SYSTEM.CURIOSITY_SETPOINT_FEATURE == 0.60
        assert VALUE_SYSTEM.COMPETENCE_SETPOINT_FEATURE == 0.75
        assert VALUE_SYSTEM.SAFETY_SETPOINT_FEATURE == 0.80


class TestUtilityCoefficients:
    """Test utility function coefficients match paper (Appendix A.5)."""

    def test_competence_coefficients(self):
        """Test Competence utility coefficients match Appendix A.5."""
        # 论文: η1=0.4, η2=0.4, κ=0.2, η3=0.3 (失败惩罚)
        assert VALUE_SYSTEM.UTILITY_ETA_1 == 0.4
        assert VALUE_SYSTEM.UTILITY_ETA_2 == 0.4  # 修正: 论文是 0.4
        assert VALUE_SYSTEM.UTILITY_KAPPA == 0.2  # 修正: 论文是 0.2
        assert VALUE_SYSTEM.UTILITY_ETA_3 == 0.3

    def test_curiosity_coefficients(self):
        """Test Curiosity coefficients match paper."""
        # 论文: 0.7 * Novelty + 0.3 * EMA(insight)
        assert VALUE_SYSTEM.CURIOSITY_NOVELTY_WEIGHT == 0.7
        assert VALUE_SYSTEM.CURIOSITY_INSIGHT_WEIGHT == 0.3
        assert VALUE_SYSTEM.CURIOSITY_INSIGHT_EMA_ALPHA == 0.1

    def test_attachment_coefficients(self):
        """Test Attachment coefficients match paper."""
        # 论文: T_half = 24 hours
        assert VALUE_SYSTEM.ATTACHMENT_HALF_LIFE_HOURS == 24.0
        # 论文 Appendix A.5: μ_att = 0.15
        assert VALUE_SYSTEM.ATTACHMENT_MU_ATT == 0.15


class TestDriveGaps:
    """Test drive gap computation (Section 3.6.1)."""

    def test_gap_formula(self):
        """Test paper formula: d^{(i)}_t = max(0, f^{(i)*} - f^{(i)}(S_t))"""
        features = {
            ValueDimension.HOMEOSTASIS: 0.5,  # 低于设定点 0.85
            ValueDimension.ATTACHMENT: 0.7,    # 等于设定点
            ValueDimension.CURIOSITY: 0.8,    # 高于设定点 0.6
        }
        setpoints = DEFAULT_SETPOINTS.copy()

        gaps = compute_drive_gaps(features, setpoints)

        # Homeostasis: gap = 0.85 - 0.5 = 0.35
        assert gaps[ValueDimension.HOMEOSTASIS] == pytest.approx(0.35, abs=0.01)

        # Attachment: gap = 0.7 - 0.7 = 0.0
        assert gaps[ValueDimension.ATTACHMENT] == pytest.approx(0.0, abs=0.01)

        # Curiosity: feature > setpoint, so gap = 0
        assert gaps[ValueDimension.CURIOSITY] == 0.0

    def test_gaps_non_negative(self):
        """Test that gaps are always non-negative."""
        features = {
            ValueDimension.HOMEOSTASIS: 1.0,  # 高于设定点
            ValueDimension.ATTACHMENT: 0.0,    # 低于设定点
        }
        setpoints = DEFAULT_SETPOINTS.copy()

        gaps = compute_drive_gaps(features, setpoints)

        for dim, gap in gaps.items():
            assert gap >= 0.0, f"Gap should be non-negative, got {gap} for {dim}"


class TestIntegration:
    """Integration tests for all dimensions."""

    def test_all_features_extracted(self):
        """Test that all 5 dimensions are extracted."""
        state = {
            "compute": 0.7,
            "memory": 0.7,
            "stress": 0.2,
            "relationship": 0.6,
            "boredom": 0.3,
            "time_since_interaction": 2.0,
        }
        context = {
            "recent_memories": ["Memory 1", "Memory 2"],
            "insight_quality_ema": 0.5,
            "quality_score": 0.7,
        }

        features = extract_all_features(state, context)

        # 检查所有5个维度都存在
        assert len(features) == 5
        assert CommonValueDimension.HOMEOSTASIS in features
        assert CommonValueDimension.ATTACHMENT in features
        assert CommonValueDimension.CURIOSITY in features
        assert CommonValueDimension.COMPETENCE in features
        assert CommonValueDimension.SAFETY in features

    def test_all_features_in_range(self):
        """Test that all features are in [0, 1] range."""
        state = {
            "compute": 0.5,
            "memory": 0.5,
            "stress": 0.3,
            "relationship": 0.5,
            "boredom": 0.5,
        }
        context = {
            "recent_memories": [],
            "insight_quality_ema": 0.5,
            "quality_score": 0.5,
        }

        features = extract_all_features(state, context)
        valid = validate_feature_ranges(features)

        assert valid, "All features should be in [0, 1] range"

    def test_extreme_states(self):
        """Test feature extraction with extreme states."""
        # 所有值都在极端
        test_cases = [
            {  # 最低资源，高压力
                "compute": 0.0, "memory": 0.0, "stress": 1.0,
                "relationship": 0.0, "boredom": 1.0,
            },
            {  # 最高资源，低压力
                "compute": 1.0, "memory": 1.0, "stress": 0.0,
                "relationship": 1.0, "boredom": 0.0,
            },
        ]

        for state in test_cases:
            context = {
                "recent_memories": [],
                "insight_quality_ema": 0.5,
                "quality_score": 0.5,
            }
            features = extract_all_features(state, context)

            # 即使在极端状态下，特征也应该在有效范围内
            for dim, feature in features.items():
                assert 0.0 <= feature <= 1.0, \
                    f"Extreme state produced invalid feature: {dim} = {feature}"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
