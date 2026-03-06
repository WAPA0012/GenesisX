"""Tests for Goal Compiler."""
import pytest
from cognition.goal_compiler import GoalCompiler
from common.models import ValueDimension, Goal


class TestGoalCompiler:
    """Test goal compilation from value gaps."""

    def test_compile_basic(self):
        """Test basic goal compilation."""
        compiler = GoalCompiler()

        gaps = {
            ValueDimension.HOMEOSTASIS: 0.6,
            ValueDimension.CURIOSITY: 0.3,
        }

        weights = {
            ValueDimension.HOMEOSTASIS: 0.7,
            ValueDimension.CURIOSITY: 0.3,
        }

        state = {}

        goal = compiler.compile(gaps, weights, state)

        assert isinstance(goal, Goal)
        assert goal.goal_type in ["rest_and_recover", "explore_and_learn"]
        assert 0.0 <= goal.priority <= 1.0

    def test_compile_highest_priority(self):
        """Test that highest priority dimension wins."""
        compiler = GoalCompiler()

        gaps = {
            ValueDimension.HOMEOSTASIS: 0.8,  # High gap
            ValueDimension.CURIOSITY: 0.2,    # Low gap
        }

        weights = {
            ValueDimension.HOMEOSTASIS: 0.9,  # High weight
            ValueDimension.CURIOSITY: 0.1,
        }

        state = {}

        goal = compiler.compile(gaps, weights, state)

        # Homeostasis should win
        assert goal.goal_type == "rest_and_recover"
        assert goal.priority > 0.5

    def test_compile_idle_when_no_gaps(self):
        """Test idle goal when no significant gaps."""
        compiler = GoalCompiler()

        gaps = {
            ValueDimension.HOMEOSTASIS: 0.05,
            ValueDimension.CURIOSITY: 0.08,
        }

        weights = {
            ValueDimension.HOMEOSTASIS: 0.5,
            ValueDimension.CURIOSITY: 0.5,
        }

        state = {}

        goal = compiler.compile(gaps, weights, state)

        assert goal.goal_type == "maintain"

    def test_goal_owner(self):
        """Test goal owner field."""
        compiler = GoalCompiler()

        # 修复 v14: 使用5维核心价值向量
        gaps = {ValueDimension.ATTACHMENT: 0.7}
        weights = {ValueDimension.ATTACHMENT: 0.8}
        state = {}

        # Self-generated goal
        goal_self = compiler.compile(gaps, weights, state, owner="self")
        assert goal_self.owner == "self"

        # User-directed goal
        goal_user = compiler.compile(gaps, weights, state, owner="user")
        assert goal_user.owner == "user"

    def test_compute_progress(self):
        """Test progress computation."""
        compiler = GoalCompiler()

        # Rest goal - Enhanced test with full state
        goal = Goal(
            goal_type="rest_and_recover",
            priority=0.7,
            owner="self",
            description="Rest"
        )

        # Provide complete state for accurate progress calculation
        state = {
            "energy": 0.7,
            "energy_setpoint": 0.7,
            "fatigue": 0.3,  # At setpoint
            "fatigue_setpoint": 0.3
        }
        progress = compiler.compute_progress(goal, state)

        # At setpoint (energy=0.7, fatigue=0.3), progress should be high
        assert 0.9 <= progress <= 1.0  # At setpoint

    def test_goal_context(self):
        """Test that goal includes context."""
        compiler = GoalCompiler()

        gaps = {ValueDimension.COMPETENCE: 0.5}
        weights = {ValueDimension.COMPETENCE: 0.6}
        state = {}

        goal = compiler.compile(gaps, weights, state)

        assert "dimension" in goal.context
        assert "gap" in goal.context
