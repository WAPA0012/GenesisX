"""Test utility normalization (P2-8).

验证所有效用函数的输出范围确实在 [-1, 1] 或 [0, 1]。

论文 Section 3.5.2 要求:
"推荐将每个 u^(i) 限制在 [-1, 1] 或 [0, 1] 区间"
"""

import pytest
import random
from axiology import (
    UtilityCalculator,
    UtilityConfig,
    StateSnapshot,
)
from axiology.utilities_unified import compute_utilities, verify_utility_normalization
from common.models import ValueDimension


def test_homeostasis_normalization():
    """测试 Homeostasis 效用归一化到 [-1, 1]."""
    calc = UtilityCalculator()

    # 生成随机状态测试
    for _ in range(100):
        state_t = StateSnapshot(
            energy=random.random(),
            stress=random.random(),
            fatigue=random.random(),
        )
        state_t1 = StateSnapshot(
            energy=random.random(),
            stress=random.random(),
            fatigue=random.random(),
        )

        utility = calc.compute_homeostasis(state_t, state_t1)

        # 验证范围
        assert -1.0 <= utility <= 1.0, f"Homeostasis utility {utility} out of range [-1, 1]"


def test_integrity_normalization():
    """测试 Integrity 效用归一化到 [-1, 1] (P2-8)."""
    calc = UtilityCalculator()

    for _ in range(100):
        state_t = StateSnapshot(
            personality_drift=random.random(),
            error_count=random.randint(0, 10),
        )
        state_t1 = StateSnapshot(
            personality_drift=random.random(),
            error_count=random.randint(0, 10),
        )

        utility = calc.compute_integrity(state_t, state_t1)

        # 验证范围
        assert -1.0 <= utility <= 1.0, f"Integrity utility {utility} out of range [-1, 1]"


def test_attachment_normalization():
    """测试 Attachment 效用归一化到 [-1, 1] (P2-8)."""
    calc = UtilityCalculator()

    for _ in range(100):
        state_t = StateSnapshot(
            bond=random.random(),
            trust=random.random(),
            dt_since_user=random.random() * 100000,
        )
        state_t1 = StateSnapshot(
            bond=random.random(),
            trust=random.random(),
            dt_since_user=random.random() * 100000,
        )

        utility = calc.compute_attachment(state_t, state_t1)

        # 验证范围
        assert -1.0 <= utility <= 1.0, f"Attachment utility {utility} out of range [-1, 1]"


def test_contract_normalization():
    """测试 Contract 效用归一化到 [-1, 1] (P2-8)."""
    calc = UtilityCalculator()

    for _ in range(100):
        state_t = StateSnapshot(
            has_active_command=True,
            command_progress=random.random(),
        )
        state_t1 = StateSnapshot(
            has_active_command=True,
            command_progress=random.random(),
        )

        utility = calc.compute_contract(state_t, state_t1)

        # 验证范围
        assert -1.0 <= utility <= 1.0, f"Contract utility {utility} out of range [-1, 1]"


def test_competence_normalization():
    """测试 Competence 效用归一化到 [-1, 1] (P2-8)."""
    calc = UtilityCalculator()

    for _ in range(100):
        state_t = StateSnapshot(
            success_rate=random.random(),
            quality_score=random.random(),
            skill_coverage=random.random(),
        )
        state_t1 = StateSnapshot(
            success_rate=random.random(),
            quality_score=random.random(),
            skill_coverage=random.random(),
        )

        utility = calc.compute_competence(state_t, state_t1)

        # 验证范围
        assert -1.0 <= utility <= 1.0, f"Competence utility {utility} out of range [-1, 1]"


def test_curiosity_normalization():
    """测试 Curiosity 效用归一化到 [-1, 1] (P2-8)."""
    calc = UtilityCalculator()

    for _ in range(100):
        state_t = StateSnapshot(novelty=random.random())
        state_t1 = StateSnapshot(novelty=random.random())

        utility = calc.compute_curiosity(state_t, state_t1)

        # 验证范围
        assert -1.0 <= utility <= 1.0, f"Curiosity utility {utility} out of range [-1, 1]"


def test_meaning_normalization():
    """测试 Meaning 效用在 [0, 1]."""
    calc = UtilityCalculator()

    # insight_formed = False
    utility = calc.compute_meaning(
        StateSnapshot(insight_formed=False),
        StateSnapshot(insight_formed=False),
    )
    assert utility == 0.0, "Meaning utility should be 0 when no insight formed"

    # insight_formed = True
    utility = calc.compute_meaning(
        StateSnapshot(insight_formed=False),
        StateSnapshot(insight_formed=True, insight_quality=random.random()),
    )
    assert 0.0 <= utility <= 1.0, f"Meaning utility {utility} out of range [0, 1]"


def test_efficiency_normalization():
    """测试 Efficiency 效用归一化到 [-1, 0] (P2-8)."""
    calc = UtilityCalculator()
    from common.models import CostVector

    for _ in range(100):
        cost = CostVector(
            cpu_tokens=random.randint(0, 5000),
            io_tokens=random.randint(0, 1000),
            net_bytes=random.randint(0, 1000000),
            time_ms=random.randint(0, 10000),
        )

        utility = calc.compute_efficiency(cost)

        # 验证范围 [-1, 0]
        assert -1.0 <= utility <= 0.0, f"Efficiency utility {utility} out of range [-1, 0]"

    # 无成本时应该返回 0
    utility = calc.compute_efficiency(None)
    assert utility == 0.0, "Efficiency utility should be 0 when no cost"


def test_all_utilities_normalization():
    """测试所有效用函数同时归一化 (P2-8)."""
    calc = UtilityCalculator()

    results = verify_utility_normalization(calc, num_samples=500)

    assert results["all_normalized"], f"Utility normalization violations found: {results['violations']}"

    # 打印范围信息
    print("\nUtility ranges:")
    for dim, (min_val, max_val) in results["ranges"].items():
        print(f"  {dim}: [{min_val:.4f}, {max_val:.4f}]")


def test_legacy_utility_normalization():
    """测试 legacy compute_utilities 函数归一化 (P2-8)."""
    features = {dim: random.random() for dim in ValueDimension}
    setpoints = {dim: random.random() for dim in ValueDimension}

    utilities = compute_utilities(features, setpoints)

    for dim, utility in utilities.items():
        assert -1.0 <= utility <= 1.0, f"Legacy utility for {dim} is {utility}, out of range [-1, 1]"


def test_utility_config_from_global_config():
    """测试从全局配置创建 UtilityConfig (P2-10)."""
    global_config = {
        "axiology": {
            "attachment": {
                "alpha": 1.5,
                "beta": 0.9,
                "gamma": 0.3,
                "t_half_hours": 12.0,
            },
            "competence": {
                "eta_success": 0.7,
                "eta_quality": 0.3,
                "kappa_skill": 0.4,
            },
            "integrity": {
                "max_drift_penalty": 0.8,
                "max_error_penalty": 0.3,
            },
        },
        "tool_costs": {
            "tokens_cap": 8000,
        },
    }

    config = UtilityConfig.from_global_config(global_config)

    # 验证参数被正确读取
    assert config.alpha_bond == 1.5
    assert config.beta_trust == 0.9
    assert config.gamma_neglect == 0.3
    assert config.t_half_neglect == 12.0 * 3600.0
    assert config.eta_success == 0.7
    assert config.eta_quality == 0.3
    assert config.kappa_skill == 0.4
    assert config.max_drift_penalty == 0.8
    assert config.max_error_penalty == 0.3
    assert config.cost_normalization_factor == 8000.0


if __name__ == "__main__":
    print("Testing utility normalization (P2-8)...")
    test_all_utilities_normalization()
    print("\n✓ All utility normalization tests passed!")
