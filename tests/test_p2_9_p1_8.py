"""Test goal progress configuration (P2-9) and evidence requirements (P1-8).

测试:
- P2-9: 目标进度计算参数可配置化
- P1-8: 高影响洞察的证据要求验证
"""

import pytest
from cognition.goal_compiler import (
    GoalCompiler,
    GoalProgressConfig,
    Goal,
)
from memory.consolidation import (
    DreamConsolidator,
    EvidenceConfig,
)
from common.models import EpisodeRecord, Action
from unittest.mock import Mock


def test_goal_progress_config_defaults():
    """测试 GoalProgressConfig 默认值 (P2-9)."""
    config = GoalProgressConfig()

    # 验证默认值
    assert config.skill_count_target == 20
    assert config.max_error_threshold == 5
    assert config.schema_target == 5
    assert config.energy_weight == 0.6
    assert config.fatigue_weight == 0.4


def test_goal_progress_config_from_global_config():
    """测试从全局配置创建 GoalProgressConfig (P2-10)."""
    global_config = {
        "goal_progress": {
            "skill_count_target": 30,
            "max_error_threshold": 10,
            "schema_target": 8,
            "energy_weight": 0.7,
            "fatigue_weight": 0.3,
        }
    }

    config = GoalProgressConfig.from_global_config(global_config)

    # 验证参数被正确读取
    assert config.skill_count_target == 30
    assert config.max_error_threshold == 10
    assert config.schema_target == 8
    assert config.energy_weight == 0.7
    assert config.fatigue_weight == 0.3


def test_goal_progress_with_config():
    """测试使用可配置参数计算进度 (P2-9)."""
    config = GoalProgressConfig(
        skill_count_target=50,
        max_error_threshold=3,
        schema_target=10,
    )

    compiler = GoalCompiler(progress_config=config)

    # 测试 improve_skills 进度
    state = {"skill_count": 25}
    goal = Goal(goal_type="improve_skills", priority=0.5, owner="self")
    progress = compiler.compute_progress(goal, state)

    # 应该是 25/50 = 0.5
    assert progress == 0.5, f"Expected progress 0.5, got {progress}"

    # 测试 verify_and_correct 进度
    state = {"recent_errors": 1}
    goal = Goal(goal_type="verify_and_correct", priority=0.5, owner="self")
    progress = compiler.compute_progress(goal, state)

    # 应该是 1 - 1/3 = 0.666...
    assert abs(progress - (1.0 - 1.0/3.0)) < 0.01, f"Expected progress ~0.667, got {progress}"


def test_evidence_config_defaults():
    """测试 EvidenceConfig 默认值 (P1-8)."""
    config = EvidenceConfig()

    # 验证默认值
    assert config.min_tool_calls == 1
    assert config.high_quality_threshold == 0.8
    assert "safety" in config.high_impact_tags
    assert "integrity" in config.high_impact_tags
    assert config.require_evidence_for_high_quality is True


def test_evidence_check_low_quality():
    """测试低质量洞察不需要证据 (P1-8)."""
    config = EvidenceConfig(
        high_quality_threshold=0.8,
        min_tool_calls=1,
    )

    consolidator = DreamConsolidator(
        episodic=Mock(),
        schema=Mock(),
        skill=Mock(),
        evidence_config=config,
    )

    # 低质量洞察
    has_evidence, reason = consolidator._check_evidence_requirement(
        insight_claim="Test insight",
        quality=0.6,  # < 0.8
        episodes=[],
        tags=[],
    )

    assert has_evidence is True
    assert "no evidence required" in reason


def test_evidence_check_high_quality_without_evidence():
    """测试高质量洞察无证据时被拒绝 (P1-8)."""
    config = EvidenceConfig(
        high_quality_threshold=0.8,
        min_tool_calls=1,
        require_evidence_for_high_quality=True,
    )

    consolidator = DreamConsolidator(
        episodic=Mock(),
        schema=Mock(),
        skill=Mock(),
        evidence_config=config,
    )

    # 高质量洞察但无工具调用证据
    episodes = [
        EpisodeRecord(
            tick=1,
            session_id="test",
            action=Action(type="CHAT", params={}),  # 非工具调用
            reward=0.5,
        )
    ]

    has_evidence, reason = consolidator._check_evidence_requirement(
        insight_claim="High quality insight",
        quality=0.9,  # > 0.8
        episodes=episodes,
        tags=[],
    )

    assert has_evidence is False
    assert "Insufficient evidence" in reason


def test_evidence_check_high_quality_with_evidence():
    """测试高质量洞察有证据时通过 (P1-8)."""
    config = EvidenceConfig(
        high_quality_threshold=0.8,
        min_tool_calls=1,
        require_evidence_for_high_quality=True,
    )

    consolidator = DreamConsolidator(
        episodic=Mock(),
        schema=Mock(),
        skill=Mock(),
        evidence_config=config,
    )

    # 高质量洞察且有工具调用证据
    episodes = [
        EpisodeRecord(
            tick=1,
            session_id="test",
            action=Action(type="USE_TOOL", params={"tool_id": "web_search"}),  # 工具调用
            reward=0.8,
        )
    ]

    has_evidence, reason = consolidator._check_evidence_requirement(
        insight_claim="High quality insight with evidence",
        quality=0.9,  # > 0.8
        episodes=episodes,
        tags=[],
    )

    assert has_evidence is True
    assert "Evidence verified" in reason


def test_evidence_check_high_impact_tag():
    """测试高影响标签需要证据 (P1-8)."""
    config = EvidenceConfig(
        high_quality_threshold=0.8,
        min_tool_calls=1,
        high_impact_tags={"safety", "integrity"},
    )

    consolidator = DreamConsolidator(
        episodic=Mock(),
        schema=Mock(),
        skill=Mock(),
        evidence_config=config,
    )

    # 低质量但有高影响标签
    has_evidence, reason = consolidator._check_evidence_requirement(
        insight_claim="Safety critical insight",
        quality=0.5,  # < 0.8
        episodes=[],
        tags=["safety"],  # 高影响标签
    )

    # 应该需要证据
    assert has_evidence is False, "High impact tag should require evidence"
    assert "Insufficient evidence" in reason


def test_goal_progress_all_types():
    """测试所有目标类型的进度计算 (P2-9)."""
    config = GoalProgressConfig()
    compiler = GoalCompiler(progress_config=config)

    test_cases = [
        # (goal_type, state, expected_range)
        ("rest_and_recover", {"energy": 0.7, "energy_setpoint": 0.7, "fatigue": 0.3, "fatigue_setpoint": 0.3}, (0.9, 1.0)),
        ("strengthen_bond", {"bond": 0.5}, (0.5, 0.5)),
        ("improve_skills", {"skill_count": 10}, (0.5, 0.5)),  # 10/20 = 0.5
        ("explore_and_learn", {"novelty_explored": 0.6}, (0.6, 0.6)),
        ("reflect_and_consolidate", {"schemas_created_this_session": 2}, (0.4, 0.4)),  # 2/5 = 0.4
        ("optimize_resources", {"resource_waste": 0.2}, (0.8, 0.8)),  # 1 - 0.2
        ("maintain", {}, (1.0, 1.0)),
    ]

    for goal_type, state, expected_range in test_cases:
        goal = Goal(goal_type=goal_type, priority=0.5, owner="self")
        progress = compiler.compute_progress(goal, state)

        min_expected, max_expected = expected_range
        assert min_expected <= progress <= max_expected, \
            f"Progress for {goal_type} is {progress}, expected [{min_expected}, {max_expected}]"


if __name__ == "__main__":
    print("Testing goal progress config (P2-9) and evidence requirements (P1-8)...")
    test_goal_progress_config_defaults()
    test_goal_progress_config_from_global_config()
    test_goal_progress_with_config()
    test_evidence_config_defaults()
    test_evidence_check_low_quality()
    test_evidence_check_high_quality_without_evidence()
    test_evidence_check_high_quality_with_evidence()
    test_evidence_check_high_impact_tag()
    test_goal_progress_all_types()
    print("\n✓ All goal progress and evidence tests passed!")
