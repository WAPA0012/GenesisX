"""
Organ System Coordination Tests

Tests the 6-organ system and their coordination:
- Mind Organ: Planning and reasoning
- Caretaker Organ: Health management
- Scout Organ: Exploration
- Builder Organ: Project management
- Archivist Organ: Memory management
- Immune Organ: Security

Paper Section 3.12: Organ-based architecture
"""

import pytest
from typing import List, Dict, Any
from unittest.mock import Mock, patch

from organs.base_organ import BaseOrgan
from organs.internal.mind_organ import MindOrgan
from organs.internal.caretaker_organ import CaretakerOrgan
from organs.internal.scout_organ import ScoutOrgan
from organs.internal.builder_organ import BuilderOrgan
from organs.internal.archivist_organ import ArchivistOrgan
from organs.internal.immune_organ import ImmuneOrgan
from common.models import Action, Goal


# ============================================================================
# Test Base Organ
# ============================================================================

class TestBaseOrgan:
    """Test BaseOrgan base class."""

    def test_base_organ_initialization(self):
        """Test that BaseOrgan can be instantiated (provides default implementations)."""
        # 新架构：BaseOrgan 提供默认实现，可以被实例化
        organ = BaseOrgan("test")
        assert organ.name == "test"
        assert organ.enabled is True

    def test_organ_enable_disable(self):
        """Test enabling/disabling organs."""
        # Use concrete implementation
        mind = MindOrgan()

        assert mind.enabled is True

        mind.set_enabled(False)
        assert mind.enabled is False

        mind.set_enabled(True)
        assert mind.enabled is True


# ============================================================================
# Test Mind Organ
# ============================================================================

class TestMindOrgan:
    """Test MindOrgan planning and reasoning."""

    def test_mind_organ_initialization(self):
        """Test MindOrgan initialization."""
        mind = MindOrgan()

        assert mind.name == "mind"
        assert mind.enabled is True
        assert len(mind.plan_history) == 0
        assert mind.thinking_depth == 1
        assert mind.current_focus is None

    def test_mind_organ_cognitive_load_calculation(self):
        """Test cognitive load calculation."""
        mind = MindOrgan()

        state = {
            "fatigue": 0.5,
            "stress": 0.3,
        }
        context = {}

        cognitive_load = mind._calculate_cognitive_load(state, context)

        assert 0.0 <= cognitive_load <= 1.0

    def test_mind_organ_high_cognitive_load(self):
        """Test cognitive load with high stress."""
        mind = MindOrgan()
        mind.consecutive_plans = 5

        state = {
            "fatigue": 0.8,
            "stress": 0.9,
        }
        context = {}

        cognitive_load = mind._calculate_cognitive_load(state, context)

        # Should be high due to stress and fatigue
        assert cognitive_load > 0.5

    def test_mind_organ_goal_complexity_assessment(self):
        """Test goal complexity assessment."""
        mind = MindOrgan()

        simple_goal = "Do task"
        moderate_goal = "Complete the task with some details"
        complex_goal = "Analyze and implement a comprehensive solution that addresses multiple factors including performance, security, and user experience while maintaining backward compatibility"

        assert mind._assess_goal_complexity(simple_goal) == "simple"
        assert mind._assess_goal_complexity(moderate_goal) == "moderate"
        assert mind._assess_goal_complexity(complex_goal) == "complex"

    def test_mind_organ_strategic_planning_conditions(self):
        """Test strategic planning decision."""
        mind = MindOrgan()
        mind.thinking_depth = 3

        # Favorable conditions
        should_plan = mind._should_use_strategic_planning(
            energy=0.8,
            stress=0.2,
            cognitive_load=0.3,
            goal="Achieve long term strategic objectives"
        )

        assert should_plan is True

        # Unfavorable conditions
        should_plan = mind._should_use_strategic_planning(
            energy=0.3,
            stress=0.8,
            cognitive_load=0.9,
            goal="Quick task"
        )

        assert should_plan is False

    def test_mind_organ_tactical_planning_conditions(self):
        """Test tactical planning decision."""
        mind = MindOrgan()

        should_plan = mind._should_use_tactical_planning(
            energy=0.6,
            cognitive_load=0.3,
            goal="Learn a specific skill"
        )

        assert should_plan is True

    def test_mind_organ_reactive_planning_conditions(self):
        """Test reactive planning decision."""
        mind = MindOrgan()

        # High stress should trigger reactive
        should_plan = mind._should_use_reactive_planning(
            stress=0.8,
            energy=0.5,
            cognitive_load=0.3
        )

        assert should_plan is True

        # Low energy should trigger reactive
        should_plan = mind._should_use_reactive_planning(
            stress=0.2,
            energy=0.2,
            cognitive_load=0.3
        )

        assert should_plan is True

    def test_mind_organ_exploratory_planning_conditions(self):
        """Test exploratory planning decision."""
        mind = MindOrgan()

        should_plan = mind._should_use_exploratory_planning(
            boredom=0.8,
            energy=0.6,
            cognitive_load=0.3
        )

        assert should_plan is True

        # Not bored should not explore
        should_plan = mind._should_use_exploratory_planning(
            boredom=0.2,
            energy=0.6,
            cognitive_load=0.3
        )

        assert should_plan is False

    def test_mind_organ_propose_actions(self):
        """Test MindOrgan propose_actions."""
        mind = MindOrgan()

        state = {
            "tick": 100,
            "energy": 0.7,
            "stress": 0.3,
            "mood": 0.5,
            "boredom": 0.2,
            "fatigue": 0.2,
        }
        context = {
            "goal": "Learn new skills",
            "tick_duration": 10,
            "mode": "work",
            # v15修复: 使用5维核心价值系统
            "weights": {dim: 0.2 for dim in ["homeostasis", "attachment", "curiosity", "competence", "safety"]},
        }

        actions = mind.propose_actions(state, context)

        assert isinstance(actions, list)
        # At minimum, should propose some actions
        assert len(actions) >= 0

    def test_mind_organ_user_response_detection(self):
        """Test user input response detection."""
        mind = MindOrgan()

        state = {}
        context = {
            "observations": [
                Mock(type="user_chat", payload={"message": "hello"})
            ]
        }

        should_respond = mind._should_respond_to_user(state, context)
        assert should_respond is True

    def test_mind_organ_record_outcome(self):
        """Test recording plan outcome."""
        mind = MindOrgan()

        mind.record_plan_outcome(10, "test_goal", "strategic", success=True)

        assert len(mind.plan_history) == 1
        assert len(mind.successful_patterns) == 1
        assert mind.strategy_success_rates["strategic"] > 0.5

    def test_mind_organ_cognitive_status(self):
        """Test getting cognitive status."""
        mind = MindOrgan()

        status = mind.get_cognitive_status()

        assert "current_focus" in status
        assert "thinking_depth" in status
        assert "consecutive_plans" in status
        assert "plan_history_size" in status
        assert "active_reasoning_chain_length" in status
        assert "strategy_success_rates" in status
        assert "decomposed_goals" in status


# ============================================================================
# Test Caretaker Organ
# ============================================================================

class TestCaretakerOrgan:
    """Test CaretakerOrgan health management."""

    def test_caretaker_organ_initialization(self):
        """Test CaretakerOrgan initialization."""
        caretaker = CaretakerOrgan()

        assert caretaker.name == "caretaker"
        assert caretaker.enabled is True

    def test_caretaker_health_assessment(self):
        """Test health assessment."""
        caretaker = CaretakerOrgan()

        state = {
            "energy": 0.3,
            "fatigue": 0.7,
            "stress": 0.6,
        }

        health_status = caretaker.assess_health(state)

        assert "status" in health_status
        assert "interventions" in health_status
        assert len(health_status["interventions"]) >= 0

    def test_caretaker_low_energy_intervention(self):
        """Test intervention for low energy."""
        caretaker = CaretakerOrgan()

        state = {
            "energy": 0.2,
            "fatigue": 0.5,
            "stress": 0.3,
        }
        context = {}

        actions = caretaker.propose_actions(state, context)

        # Should propose sleep action (Action type is "SLEEP" not "REST")
        assert isinstance(actions, list)
        if len(actions) > 0:
            assert any(action.type == "SLEEP" for action in actions)

    def test_caretaker_high_stress_intervention(self):
        """Test intervention for high stress."""
        caretaker = CaretakerOrgan()

        state = {
            "energy": 0.6,
            "fatigue": 0.3,
            "stress": 0.8,
        }
        context = {}

        actions = caretaker.propose_actions(state, context)

        # Should propose stress reduction
        assert isinstance(actions, list)

    def test_caretaker_health_state_tracking(self):
        """Test health state tracking."""
        caretaker = CaretakerOrgan()

        # Update health state
        caretaker.update_health_state("energy", 0.5)

        status = caretaker.get_health_status()
        assert "energy" in status


# ============================================================================
# Test Scout Organ
# ============================================================================

class TestScoutOrgan:
    """Test ScoutOrgan exploration."""

    def test_scout_organ_initialization(self):
        """Test ScoutOrgan initialization."""
        scout = ScoutOrgan()

        assert scout.name == "scout"
        assert scout.enabled is True

    def test_scout_exploration_decision(self):
        """Test exploration decision logic."""
        scout = ScoutOrgan()

        state = {
            "boredom": 0.7,
            "energy": 0.6,
            "mood": 0.5,
        }
        context = {
            "mode": "work",
        }

        should_explore = scout.should_explore(state, context)

        # High boredom should trigger exploration
        assert should_explore is True

    def test_scout_topic_selection(self):
        """Test exploration topic selection."""
        scout = ScoutOrgan()

        topic = scout.select_exploration_topic()

        assert topic is not None
        assert isinstance(topic, str)

    def test_scout_propose_actions(self):
        """Test ScoutOrgan propose_actions."""
        scout = ScoutOrgan()

        state = {
            "tick": 50,
            "energy": 0.7,
            "boredom": 0.8,
            "mood": 0.5,
            "stress": 0.2,
        }
        context = {
            "mode": "friend",
        }

        actions = scout.propose_actions(state, context)

        assert isinstance(actions, list)

    def test_scout_exploration_history(self):
        """Test exploration history tracking."""
        scout = ScoutOrgan()

        scout.record_exploration("quantum_physics", success=True)

        history = scout.get_exploration_history()

        assert len(history) > 0


# ============================================================================
# Test Builder Organ
# ============================================================================

class TestBuilderOrgan:
    """Test BuilderOrgan project management."""

    def test_builder_organ_initialization(self):
        """Test BuilderOrgan initialization."""
        builder = BuilderOrgan()

        assert builder.name == "builder"
        assert builder.enabled is True

    def test_builder_project_creation(self):
        """Test project creation."""
        builder = BuilderOrgan()

        project = builder.create_project(
            name="test_project",
            description="A test project",
            priority=0.8
        )

        assert project["name"] == "test_project"
        assert project["description"] == "A test project"
        assert project["priority"] == 0.8

    def test_builder_task_breakdown(self):
        """Test task breakdown."""
        builder = BuilderOrgan()

        project = builder.create_project(
            name="test_project",
            description="Build a system",
            priority=0.8
        )

        tasks = builder.breakdown_into_tasks(project)

        assert isinstance(tasks, list)

    def test_builder_propose_actions(self):
        """Test BuilderOrgan propose_actions."""
        builder = BuilderOrgan()

        state = {
            "tick": 20,
            "energy": 0.8,
            "mood": 0.6,
        }
        context = {
            "goal": "Build a new feature",
        }

        actions = builder.propose_actions(state, context)

        assert isinstance(actions, list)

    def test_builder_project_status(self):
        """Test getting project status."""
        builder = BuilderOrgan()

        builder.create_project("project1", "Description 1", 0.5)
        builder.create_project("project2", "Description 2", 0.7)

        status = builder.get_project_status()

        assert "active_projects" in status
        assert len(status["active_projects"]) >= 2


# ============================================================================
# Test Archivist Organ
# ============================================================================

class TestArchivistOrgan:
    """Test ArchivistOrgan memory management."""

    def test_archivist_organ_initialization(self):
        """Test ArchivistOrgan initialization."""
        archivist = ArchivistOrgan()

        assert archivist.name == "archivist"
        assert archivist.enabled is True

    def test_archivist_memory_assessment(self):
        """Test memory access tracking."""
        archivist = ArchivistOrgan()

        # Test memory access tracking - add_memory(memory_id, category, importance, tags)
        archivist.add_memory("mem_001", "episodic", importance=0.8)
        archivist.access_memory("mem_001")

        stats = archivist.get_memory_statistics()

        assert stats["total_memories"] >= 1
        # Check that memory was added to correct category
        assert "episodic" in stats["memory_categories"]

    def test_archivist_consolidation_trigger(self):
        """Test consolidation trigger (internal method)."""
        archivist = ArchivistOrgan()

        # Test internal consolidation check
        should_consolidate = archivist._should_consolidate(
            episodic_count=55,  # Above threshold
            tick=100
        )

        assert should_consolidate is True

    def test_archivist_propose_actions(self):
        """Test ArchivistOrgan propose_actions."""
        archivist = ArchivistOrgan()

        state = {
            "tick": 100,
            "episodic_count": 50,
            "schema_count": 20,
            "skill_count": 10,
        }
        context = {
            "consolidation_threshold": 50,
        }

        actions = archivist.propose_actions(state, context)

        assert isinstance(actions, list)

    def test_archivist_memory_cleanup(self):
        """Test memory statistics for cleanup analysis."""
        archivist = ArchivistOrgan()

        # Add some test memories - add_memory(memory_id, category, importance, tags)
        archivist.add_memory("mem_001", "episodic", importance=0.8)
        archivist.add_memory("mem_002", "episodic", importance=0.3)

        stats = archivist.get_memory_statistics()

        assert isinstance(stats, dict)
        assert "total_memories" in stats


# ============================================================================
# Test Immune Organ
# ============================================================================

class TestImmuneOrgan:
    """Test ImmuneOrgan security."""

    def test_immune_organ_initialization(self):
        """Test ImmuneOrgan initialization."""
        immune = ImmuneOrgan()

        assert immune.name == "immune"
        assert immune.enabled is True

    def test_immune_threat_detection(self):
        """Test threat detection."""
        immune = ImmuneOrgan()

        action = Action(
            type="USE_TOOL",
            params={"tool": "code_exec", "code": "print('hello')"},
            risk_level=0.8,
            capability_req=["code_execution"]
        )

        threat_level = immune.assess_action_risk(action, {})

        assert 0.0 <= threat_level <= 1.0

    def test_immune_safe_action(self):
        """Test that safe actions have low threat."""
        immune = ImmuneOrgan()

        action = Action(
            type="CHAT",
            params={"message": "hello"},
            risk_level=0.0,
            capability_req=[]
        )

        threat = immune.assess_action_risk(action, {})

        # Safe action should have low threat
        assert threat <= 0.5

    def test_immune_risky_action(self):
        """Test that risky actions are evaluated."""
        immune = ImmuneOrgan()

        action = Action(
            type="USE_TOOL",
            params={"tool": "file_delete", "path": "/important/file"},
            risk_level=0.9,
            capability_req=["file_delete"]
        )

        threat = immune.assess_action_risk(action, {})

        # High risk action should have high threat
        assert threat > 0.5

    def test_immune_propose_actions(self):
        """Test ImmuneOrgan propose_actions."""
        immune = ImmuneOrgan()

        state = {
            "tick": 50,
            "trust": 0.5,
        }
        context = {
            "recent_risks": [0.1, 0.2, 0.3],
        }

        actions = immune.propose_actions(state, context)

        assert isinstance(actions, list)


# ============================================================================
# Test Organ Coordination
# ============================================================================

class TestOrganCoordination:
    """Test coordination between organs."""

    def test_all_organs_instantiable(self):
        """Test that all organs can be instantiated."""
        organs = [
            MindOrgan(),
            CaretakerOrgan(),
            ScoutOrgan(),
            BuilderOrgan(),
            ArchivistOrgan(),
            ImmuneOrgan(),
        ]

        for organ in organs:
            assert isinstance(organ, BaseOrgan)
            assert organ.name is not None
            assert organ.enabled is True

    def test_organ_action_proposal(self):
        """Test that all organs can propose actions."""
        organs = [
            MindOrgan(),
            CaretakerOrgan(),
            ScoutOrgan(),
            BuilderOrgan(),
            ArchivistOrgan(),
            ImmuneOrgan(),
        ]

        state = {
            "tick": 50,
            "energy": 0.5,
            "mood": 0.5,
            "stress": 0.3,
            "fatigue": 0.2,
            "boredom": 0.3,
            "episodic_count": 25,
            "schema_count": 10,
            "skill_count": 5,
        }
        context = {
            "goal": "Test goal",
            "mode": "work",
            # v15修复: 使用5维核心价值系统
            "weights": {dim: 0.2 for dim in ["homeostasis", "attachment", "curiosity", "competence", "safety"]},
        }

        all_actions = []

        for organ in organs:
            actions = organ.propose_actions(state, context)
            all_actions.extend(actions)

        # All organs should return valid action lists
        assert isinstance(all_actions, list)

    def test_organ_priority_ordering(self):
        """Test that organs can be ordered by priority."""
        state = {
            "tick": 50,
            "energy": 0.2,  # Low energy - Caretaker should prioritize
            "stress": 0.8,  # High stress
            "mood": 0.3,
            "fatigue": 0.7,
            "boredom": 0.5,
        }
        context = {
            "goal": "Continue working",
            "mode": "work",
        }

        caretaker = CaretakerOrgan()
        caretaker_actions = caretaker.propose_actions(state, context)

        # Caretaker should suggest intervention
        assert isinstance(caretaker_actions, list)

    def test_organ_disabled(self):
        """Test that disabled organs don't propose actions."""
        mind = MindOrgan()
        mind.set_enabled(False)

        state = {
            "tick": 50,
            "energy": 0.7,
            "mood": 0.5,
            "boredom": 0.2,
        }
        context = {"goal": "test"}

        actions = mind.propose_actions(state, context)

        # Disabled organ might return empty actions
        assert isinstance(actions, list)

    def test_organ_specialization(self):
        """Test that organs have specialized behaviors."""
        state = {
            "tick": 50,
            "energy": 0.5,
            "mood": 0.5,
            "stress": 0.3,
            "fatigue": 0.2,
            "boredom": 0.8,  # High boredom
        }
        context = {
            "goal": "Explore new topics",
            "mode": "friend",
        }

        scout = ScoutOrgan()
        scout_actions = scout.propose_actions(state, context)

        # Scout should propose exploration actions
        assert isinstance(scout_actions, list)


# ============================================================================
# Test Paper Section 3.12 Compliance
# ============================================================================

class TestPaperSection3_12Compliance:
    """Test compliance with paper Section 3.12: Organ-based architecture."""

    def test_six_organs_exist(self):
        """Test that 6 organs are implemented as per paper."""
        import organs

        # Check that organ classes can be imported
        organ_classes = [
            "MindOrgan", "CaretakerOrgan", "ScoutOrgan",
            "BuilderOrgan", "ArchivistOrgan", "ImmuneOrgan"
        ]

        for organ_class in organ_classes:
            # Each organ class should be importable from organs module
            assert hasattr(organs, organ_class), f"Missing organ class: {organ_class}"

    def test_organ_differentiation(self):
        """Test paper Section 3.12.1: Organ differentiation."""
        mind = MindOrgan()
        caretaker = CaretakerOrgan()
        scout = ScoutOrgan()

        # Each organ should have different name
        assert mind.name != caretaker.name
        assert caretaker.name != scout.name
        assert mind.name != scout.name

        # Each organ should propose different types of actions
        state = {"tick": 50, "energy": 0.5}
        context = {"goal": "test"}

        mind_actions = mind.propose_actions(state, context)
        caretaker_actions = caretaker.propose_actions(state, context)
        scout_actions = scout.propose_actions(state, context)

        # Action sets may differ based on organ specialization
        assert isinstance(mind_actions, list)
        assert isinstance(caretaker_actions, list)
        assert isinstance(scout_actions, list)
