"""Test utility normalization (论文 Section 3.5.2).

验证所有 5 维核心效用函数的输出范围确实在 [-1, 1]，并校验关键方向性不变量。

历史：此文件原测 axiology/__init__.py 的 fallback `UtilityCalculator`/`StateSnapshot`
类（utility.py 删除后保留的兼容层），但 fallback 的 5 维公式与论文 v15 的
utilities_unified.py 完全不一致（homeostasis 用旧 energy/stress/fatigue、attachment
拆 bond/trust、curiosity 丢 insight、competence 无失败惩罚、safety 用
personality_drift 当代理），旧断言只验证 clip 范围恒成立而无法验证公式正确性。

2026-07-21 重写：fallback 已删（CODE_MAP P2-1），本文件改为直接验证
utilities_unified 的 5 维纯函数 + 补论文不变量断言。
"""

import math
import random

import pytest

from axiology.utilities_unified import (
    compute_utilities,
    utility_attachment,
    utility_competence,
    utility_curiosity,
    utility_homeostasis,
    utility_safety,
    verify_utility_normalization,
)
from common.models import ValueDimension


# 论文 Section 3.5.2(1): 数字原生 homeostasis setpoint（子分量）
HOMEOSTASIS_SETPOINTS = {"compute": 0.8, "memory": 0.8, "stress": 0.2}


class TestHomeostasisUtility:
    """论文 Section 3.5.2(1): u^homeo = (||H_t - H*||_1 - ||H_{t+1} - H*||_1) / D_max, H=(Compute,Memory,1-Stress)."""

    def test_range_normalized(self):
        """随机 100 次采样，所有输出 ∈ [-1, 1]."""
        for _ in range(100):
            u = utility_homeostasis(
                compute_current=random.random(),
                compute_next=random.random(),
                memory_current=random.random(),
                memory_next=random.random(),
                stress_current=random.random(),
                stress_next=random.random(),
                setpoints=HOMEOSTASIS_SETPOINTS,
            )
            assert -1.0 <= u <= 1.0, f"Homeostasis utility {u} out of range"

    def test_improvement_is_positive(self):
        """t→t+1 向 setpoint 靠近时，效用为正（论文方向性）."""
        # t 远离 setpoint，t+1 精确命中 setpoint → 距离缩小 → u > 0
        u = utility_homeostasis(
            compute_current=0.2,   # 远离 0.8
            compute_next=0.8,      # 命中
            memory_current=0.2,
            memory_next=0.8,
            stress_current=0.9,    # 远离 0.2
            stress_next=0.2,
            setpoints=HOMEOSTASIS_SETPOINTS,
        )
        assert u > 0.0, f"Improvement should yield positive utility, got {u}"

    def test_deterioration_is_negative(self):
        """t→t+1 远离 setpoint 时，效用为负."""
        u = utility_homeostasis(
            compute_current=0.8,
            compute_next=0.2,
            memory_current=0.8,
            memory_next=0.2,
            stress_current=0.2,
            stress_next=0.9,
            setpoints=HOMEOSTASIS_SETPOINTS,
        )
        assert u < 0.0, f"Deterioration should yield negative utility, got {u}"


class TestAttachmentUtility:
    """论文 Section 3.5.2(2)(3): u^attach = α·ΔRelationship - γ·Neglect(Δt), Neglect 半衰期 T_half=24h."""

    def test_range_normalized(self):
        for _ in range(100):
            u = utility_attachment(
                relationship_current=random.random(),
                relationship_next=random.random(),
                time_since_interaction=random.random() * 100000,
            )
            assert -1.0 <= u <= 1.0, f"Attachment utility {u} out of range"

    def test_neglect_half_life_invariant(self):
        """论文不变量：t_half=24h, dt=24h → neglect=0.5；dt=0 → neglect=0.

        通过控制 relationship_current == relationship_next（ΔRelationship=0）让
        utility 完全由 -γ·Neglect 主导，验证 Neglect 的半衰期公式。
        """
        # dt = t_half → neglect = 0.5
        t_half = 24.0 * 3600.0
        u_at_halflife = utility_attachment(
            relationship_current=0.5,
            relationship_next=0.5,   # Δ=0
            time_since_interaction=t_half,
            t_half=t_half,
            alpha=0.5,
            gamma=0.15,
        )
        # u = 0 - γ·0.5 = -0.075
        assert u_at_halflife == pytest.approx(-0.15 * 0.5, abs=1e-9), \
            f"At half-life, neglect should be 0.5; got u={u_at_halflife}"

        # dt = 0 → neglect = 0
        u_at_zero = utility_attachment(
            relationship_current=0.5,
            relationship_next=0.5,
            time_since_interaction=0.0,
            t_half=t_half,
            alpha=0.5,
            gamma=0.15,
        )
        assert u_at_zero == pytest.approx(0.0, abs=1e-9), \
            f"At dt=0, neglect should be 0; got u={u_at_zero}"

    def test_default_t_half_is_24h(self):
        """utility_attachment 默认参数 t_half=24*3600s（论文 Section 3.5.2）."""
        import inspect
        sig = inspect.signature(utility_attachment)
        assert sig.parameters["t_half"].default == 24.0 * 3600.0


class TestCompetenceUtility:
    """论文 Section 3.5.2(4): u^comp = η1·Success + η2·Q + κ·ΔCover - η3·(1-Success)."""

    def test_range_normalized(self):
        for _ in range(100):
            u = utility_competence(
                success=random.choice([True, False]),
                quality=random.random(),
                skill_coverage_delta=random.uniform(-1, 1),
            )
            assert -1.0 <= u <= 1.0, f"Competence utility {u} out of range"

    def test_failure_is_negative(self):
        """失败时 η3·(1-Success) 触发惩罚，低质量失败 u<0（论文 M2）."""
        u = utility_competence(
            success=False,
            quality=0.0,
            skill_coverage_delta=0.0,
        )
        assert u < 0.0, f"Failure should yield negative utility (η3 penalty), got {u}"

    def test_high_quality_success_is_positive(self):
        """高质量成功 u>0."""
        u = utility_competence(
            success=True,
            quality=1.0,
            skill_coverage_delta=0.0,
        )
        assert u > 0.0, f"High-quality success should yield positive utility, got {u}"


class TestCuriosityUtility:
    """论文 Section 3.5.2(3): u^curio = ΔNovelty + α_insight·Q·1(insight), Meaning 已并入."""

    def test_range_normalized(self):
        for _ in range(100):
            u = utility_curiosity(
                novelty_current=random.random(),
                novelty_next=random.random(),
                insight_quality=random.random(),
                insight_formed=random.choice([True, False]),
            )
            assert -1.0 <= u <= 1.0, f"Curiosity utility {u} out of range"

    def test_insight_bonus_strictly_positive(self):
        """形成洞察比无洞察效用更高（论文 Meaning 并入 Curiosity 的奖励项）."""
        base = utility_curiosity(
            novelty_current=0.5,
            novelty_next=0.5,
            insight_quality=0.0,
            insight_formed=False,
        )
        with_insight = utility_curiosity(
            novelty_current=0.5,
            novelty_next=0.5,
            insight_quality=0.8,
            insight_formed=True,
        )
        assert with_insight > base, \
            f"Insight should add bonus; base={base}, with_insight={with_insight}"


class TestSafetyUtility:
    """论文 Section 3.5.2(5): u^safety = f^safe(S_{t+1}) - f^safe(S_t), f^safe=1-RiskScore."""

    def test_range_normalized(self):
        for _ in range(100):
            u = utility_safety(
                risk_score_current=random.random(),
                risk_score_next=random.random(),
            )
            assert -1.0 <= u <= 1.0, f"Safety utility {u} out of range"

    def test_risk_reduction_is_positive(self):
        """风险下降（t+1 风险更低）→ 安全效用为正."""
        u = utility_safety(
            risk_score_current=0.9,
            risk_score_next=0.1,
        )
        assert u > 0.0, f"Risk reduction should yield positive utility, got {u}"


class TestVerifyUtilityNormalization:
    """测试 verify_utility_normalization 工具函数本身（已删除 calculator 自指分支）."""

    def test_returns_tuple_for_utilities_dict(self):
        """新版签名：直接接受 utilities dict，返回 (bool, report) 元组."""
        utilities = {
            ValueDimension.HOMEOSTASIS: 0.3,
            ValueDimension.SAFETY: -0.2,
        }
        result = verify_utility_normalization(utilities)
        # 必须返回 (bool, dict) 元组
        assert isinstance(result, tuple) and len(result) == 2
        ok, report = result
        assert ok is True
        assert report["all_normalized"] is True
        assert report["count"] == 0

    def test_detects_violation(self):
        """超出范围的 utility 应被检出."""
        utilities = {ValueDimension.HOMEOSTASIS: 1.5}
        ok, report = verify_utility_normalization(utilities, u_max=1.0)
        assert ok is False
        assert report["count"] == 1
        assert "homeostasis" in report["violations"]


class TestLegacyComputeUtilities:
    """legacy compute_utilities 是 -|feature-setpoint| 的简单代理，保留向后兼容."""

    def test_range_normalized(self):
        features = {dim: random.random() for dim in ValueDimension}
        setpoints = {dim: random.random() for dim in ValueDimension}
        utilities = compute_utilities(features, setpoints)
        for dim, u in utilities.items():
            assert -1.0 <= u <= 1.0, f"Legacy utility for {dim} is {u}, out of range"


if __name__ == "__main__":
    print("Testing utility normalization (论文 Section 3.5.2)...")
    pytest.main([__file__, "-v", "--tb=short"])
