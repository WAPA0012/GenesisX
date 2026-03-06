"""Goal progress tracking.

Implements paper Section 3.8.1 requirement:
"进度计算完整性: 要求为所有目标类型实现明确的进度计算方法 Prog(g,S)"

Note: This module provides ProgressCalculator class for calculating progress.
The Goal class is defined in common.models.py and uses goal_type attribute.
"""
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum

# Import Goal from common.models to use consistent definition
from common.models import Goal as CommonGoal


class GoalType(Enum):
    """Types of goals."""
    # Maintenance goals (keep value above threshold)
    MAINTAIN = "maintain"
    # Achievement goals (reach specific target)
    ACHIEVE = "achieve"
    # Exploration goals (discover N items)
    EXPLORE = "explore"
    # Practice goals (complete N repetitions)
    PRACTICE = "practice"
    # Reflect goals (process M episodes)
    REFLECT = "reflect"
    # Social goals (interact with user)
    SOCIAL = "social"
    # Contract goals (complete user task)
    CONTRACT = "contract"
    # Optimize goals (improve resource efficiency)
    OPTIMIZE = "optimize"


class GoalStatus(Enum):
    """Goal execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# For backward compatibility, create a local alias
# In new code, use common.models.Goal directly
Goal = CommonGoal


class ProgressCalculator:
    """Calculate goal progress Prog(g,S).

    论文Section 3.8.1: 要求为所有目标类型实现明确的进度计算方法

    Enhanced: Supports custom calculator registration (P2-9扩展).
    """

    def __init__(self):
        """Initialize calculator with custom calculator registry."""
        self._custom_calculators: Dict[str, Callable] = {}

    def register_custom_calculator(self, goal_type: str, calculator_func: Callable):
        """Register a custom progress calculator for a goal type (论文P2-9: 自定义进度计算接口).

        Args:
            goal_type: Goal type identifier (e.g., "custom_task", "complex_project")
            calculator_func: Function that takes (goal, state) and returns progress [0,1]

        Example:
            >>> def my_calculator(goal: Goal, state: Dict) -> float:
            ...     # Custom logic
            ...     return 0.5
            >>> calculator = ProgressCalculator()
            >>> calculator.register_custom_calculator("my_type", my_calculator)
        """
        self._custom_calculators[goal_type] = calculator_func

    def unregister_custom_calculator(self, goal_type: str):
        """Remove a custom calculator.

        Args:
            goal_type: Goal type to remove
        """
        self._custom_calculators.pop(goal_type, None)

    def has_custom_calculator(self, goal_type: str) -> bool:
        """Check if a custom calculator exists for the goal type.

        Args:
            goal_type: Goal type to check

        Returns:
            True if custom calculator exists
        """
        return goal_type in self._custom_calculators

    @staticmethod
    def calculate_maintain(
        current_value: float,
        target_value: float,
        min_threshold: float = 0.0,
    ) -> float:
        """Calculate progress for MAINTAIN goals.

        Progress is how close we are to maintaining the target.
        If current >= target, progress = 1.0
        Otherwise, progress scales from min_threshold to target.

        Formula:
        If current >= target: 1.0
        Else: (current - min_threshold) / (target - min_threshold)
        """
        if current_value >= target_value:
            return 1.0

        if target_value <= min_threshold:
            return 1.0 if current_value >= target_value else 0.0

        progress = (current_value - min_threshold) / (target_value - min_threshold)
        return max(0.0, min(1.0, progress))

    @staticmethod
    def calculate_achieve(
        current_value: float,
        target_value: float,
        start_value: Optional[float] = None,
    ) -> float:
        """Calculate progress for ACHIEVE goals.

        Progress is how close we are to reaching the target.

        Formula:
        If start_value provided: (current - start) / (target - start)
        Else: current / target (for absolute targets from 0)
        """
        if start_value is not None:
            if target_value <= start_value:
                return 1.0 if current_value >= target_value else 0.0
            progress = (current_value - start_value) / (target_value - start_value)
        else:
            if target_value <= 0:
                return 1.0 if current_value >= target_value else 0.0
            progress = current_value / target_value

        return max(0.0, min(1.0, progress))

    @staticmethod
    def calculate_explore(
        discovered_count: int,
        target_count: int,
    ) -> float:
        """Calculate progress for EXPLORE goals.

        Formula: discovered / target
        """
        if target_count <= 0:
            return 1.0

        progress = discovered_count / target_count
        return max(0.0, min(1.0, progress))

    @staticmethod
    def calculate_practice(
        completed_reps: int,
        target_reps: int,
    ) -> float:
        """Calculate progress for PRACTICE goals.

        Formula: completed / target
        """
        if target_reps <= 0:
            return 1.0

        progress = completed_reps / target_reps
        return max(0.0, min(1.0, progress))

    @staticmethod
    def calculate_reflect(
        processed_episodes: int,
        target_episodes: int,
    ) -> float:
        """Calculate progress for REFLECT goals.

        Formula: processed / target
        """
        if target_episodes <= 0:
            return 1.0

        progress = processed_episodes / target_episodes
        return max(0.0, min(1.0, progress))

    @staticmethod
    def calculate_social(
        interaction_count: int,
        target_count: int = 1,
    ) -> float:
        """Calculate progress for SOCIAL goals.

        Formula: interactions / target
        """
        if target_count <= 0:
            return 1.0

        progress = interaction_count / target_count
        return max(0.0, min(1.0, progress))

    @staticmethod
    def calculate_contract(
        steps_completed: int,
        total_steps: int,
        step_weights: Optional[list] = None,
    ) -> float:
        """Calculate progress for CONTRACT goals.

        Can use weighted steps if provided.

        Formula with weights: sum(weights[:completed]) / sum(all_weights)
        Formula without weights: completed / total
        """
        if total_steps <= 0:
            return 1.0

        if step_weights:
            # Weighted progress
            completed_weight = sum(step_weights[:steps_completed])
            total_weight = sum(step_weights)
            if total_weight <= 0:
                return 1.0
            progress = completed_weight / total_weight
        else:
            # Unweighted progress
            progress = steps_completed / total_steps

        return max(0.0, min(1.0, progress))

    @staticmethod
    def calculate_from_milestones(
        current_milestone: int,
        total_milestones: int,
        milestone_values: Optional[list] = None,
    ) -> float:
        """Calculate progress from milestones.

        论文Section 3.8.1: 对于难以量化的目标，可采用里程碑检查点

        Args:
            current_milestone: Current milestone index (0-based)
            total_milestones: Total number of milestones
            milestone_values: Optional progress values for each milestone

        Returns:
            Progress in [0, 1]
        """
        if total_milestones <= 0:
            return 1.0

        if milestone_values and current_milestone < len(milestone_values):
            return milestone_values[current_milestone]

        # Default: linear milestone progress
        # 0/0.25/0.5/0.75/1.0 pattern (current_milestone is 0-based completed count)
        progress = current_milestone / total_milestones
        return max(0.0, min(1.0, progress))

    @classmethod
    def calculate(cls, goal: Goal, state: Dict[str, Any]) -> float:
        """Calculate progress for a goal given current state.

        论文Section 3.8.1: Prog(g,S) must be implemented for all goal types

        Enhanced: Checks for custom calculators first (P2-9).

        Args:
            goal: The goal to calculate progress for
            state: Current state S

        Returns:
            Progress in [0, 1]
        """
        # Note: For custom calculators, use instance method calculate_with_custom
        # This classmethod remains for backward compatibility
        goal_type = goal.goal_type
        context = goal.context

        if goal_type in (GoalType.MAINTAIN.value, "maintain"):
            current = state.get(context.get("state_key", "value"), 0.0)
            target = context.get("target", 0.7)
            minimum = context.get("minimum", 0.0)
            return cls.calculate_maintain(current, target, minimum)

        elif goal_type in (GoalType.ACHIEVE.value, "achieve"):
            current = state.get(context.get("state_key", "value"), 0.0)
            target = context.get("target", 1.0)
            start = context.get("start_value")
            return cls.calculate_achieve(current, target, start)

        elif goal_type in (GoalType.EXPLORE.value, "explore"):
            discovered = state.get(context.get("state_key", "discovered"), 0)
            target = context.get("target", 10)
            return cls.calculate_explore(discovered, target)

        elif goal_type in (GoalType.PRACTICE.value, "practice"):
            completed = state.get(context.get("state_key", "reps"), 0)
            target = context.get("target", 5)
            return cls.calculate_practice(completed, target)

        elif goal_type in (GoalType.REFLECT.value, "reflect"):
            processed = state.get(context.get("state_key", "processed"), 0)
            target = context.get("target", 20)
            return cls.calculate_reflect(processed, target)

        elif goal_type in (GoalType.SOCIAL.value, "social"):
            interactions = state.get(context.get("state_key", "interactions"), 0)
            target = context.get("target", 1)
            return cls.calculate_social(interactions, target)

        elif goal_type in (GoalType.CONTRACT.value, "contract"):
            steps = state.get(context.get("state_key", "steps_done"), 0)
            total = context.get("total_steps", 5)
            weights = context.get("step_weights")
            return cls.calculate_contract(steps, total, weights)

        elif goal_type in (GoalType.OPTIMIZE.value, "optimize"):
            # Optimization progress: reduction in resource waste
            waste = state.get(context.get("state_key", "resource_waste"), 0.0)
            return max(0.0, min(1.0, 1.0 - waste))

        else:
            # Default: use milestones if available
            if goal.milestones:
                current_idx = state.get("current_milestone", 0)
                return cls.calculate_from_milestones(
                    current_idx,
                    len(goal.milestones),
                    goal.milestones,
                )
            return goal.progress  # Return cached progress

    def calculate_with_custom(self, goal: Goal, state: Dict[str, Any]) -> float:
        """Calculate progress using custom calculator if available (论文P2-9).

        Args:
            goal: The goal to calculate progress for
            state: Current state S

        Returns:
            Progress in [0, 1]
        """
        # Check for custom calculator by goal type
        goal_type_str = goal.goal_type

        if goal_type_str in self._custom_calculators:
            # Use custom calculator
            try:
                return self._custom_calculators[goal_type_str](goal, state)
            except Exception as e:
                # Fall back to default calculation
                return self.calculate(goal, state)

        # Fall back to default calculation
        return self.calculate(goal, state)


class Milestone:
    """Milestone for progress calculation with dependencies (论文P2-9扩展).

    Attributes:
        name: Milestone identifier
        progress: Progress value [0,1] when this milestone is reached
        weight: Weight for weighted progress calculation
        dependencies: List of milestone names that must be completed first
    """

    def __init__(
        self,
        name: str,
        progress: float,
        weight: float = 1.0,
        dependencies: list = None
    ):
        self.name = name
        self.progress = max(0.0, min(1.0, progress))
        self.weight = max(0.0, weight)
        self.dependencies = dependencies or []


class ProgressCalculatorWithMilestones(ProgressCalculator):
    """Enhanced calculator with milestone dependency support (论文P2-9).

    Supports:
    - Weighted milestone progress
    - Dependency resolution
    - Topological sorting
    """

    def calculate_with_dependencies(
        self,
        milestones: List[Milestone],
        completed_milestones: List[str]
    ) -> float:
        """Calculate progress considering milestone dependencies (论文P2-9).

        Args:
            milestones: All milestones for the goal
            completed_milestones: Names of completed milestones

        Returns:
            Overall progress [0,1]
        """
        if not milestones:
            return 0.0

        completed_set = set(completed_milestones)

        # Build dependency graph and validate
        available = []
        blocked = []

        for ms in milestones:
            if ms.name in completed_set:
                # Already completed
                continue
            elif ms.dependencies:
                # Check if all dependencies are met
                deps_met = all(d in completed_set for d in ms.dependencies)
                if deps_met:
                    available.append(ms)
                else:
                    blocked.append(ms)
            else:
                available.append(ms)

        # Calculate weighted progress from completed milestones
        total_weight = sum(ms.weight for ms in milestones)
        if total_weight == 0:
            return 0.0

        completed_weight = sum(
            ms.weight for ms in milestones if ms.name in completed_set
        )

        return completed_weight / total_weight

    def get_next_milestone(
        self,
        milestones: List[Milestone],
        completed_milestones: List[str]
    ) -> Optional[Milestone]:
        """Get the next achievable milestone.

        Args:
            milestones: All milestones
            completed_milestones: Already completed milestone names

        Returns:
            Next milestone to complete, or None if all done
        """
        completed_set = set(completed_milestones)

        for ms in milestones:
            if ms.name in completed_set:
                continue
            # Check if dependencies are met
            if all(d in completed_set for d in ms.dependencies):
                return ms

        return None


class GoalTracker:
    """Track and manage goals with progress calculation.

    论文Section 3.8: Goal Compiler with Conflict Resolution
    """

    def __init__(self):
        """Initialize goal tracker."""
        self._goals: Dict[str, Goal] = {}
        self._active_goal_id: Optional[str] = None
        self._calculator = ProgressCalculator()

    def add_goal(self, goal: Goal) -> bool:
        """Add a new goal.

        Returns True if goal was added, False if conflict detected.
        """
        # Check for conflicts with active goal
        if self._active_goal_id:
            active_goal = self._goals.get(self._active_goal_id)
            if active_goal and not goal.is_compatible_with(active_goal):
                return False  # Conflict detected

        self._goals[goal.id] = goal
        return True

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Get goal by ID."""
        return self._goals.get(goal_id)

    def set_active_goal(self, goal_id: str) -> bool:
        """Set the active goal.

        Returns True if successful, False if goal not found.
        """
        if goal_id not in self._goals:
            return False

        self._active_goal_id = goal_id
        self._goals[goal_id].status = GoalStatus.IN_PROGRESS.value
        return True

    def get_active_goal(self) -> Optional[Goal]:
        """Get the current active goal."""
        if self._active_goal_id is None:
            return None
        return self._goals.get(self._active_goal_id)

    def update_progress(self, state: Dict[str, Any], current_tick: int):
        """Update progress for all goals.

        Args:
            state: Current system state
            current_tick: Current tick number
        """
        for goal in self._goals.values():
            if goal.status in [GoalStatus.PENDING.value, GoalStatus.IN_PROGRESS.value]:
                # Check expiration
                if goal.is_expired(current_tick):
                    goal.status = GoalStatus.FAILED.value
                    continue

                # Calculate progress
                progress = self._calculator.calculate(goal, state)
                goal.update_progress(progress, current_tick)

    def get_completed_goals(self) -> List[Goal]:
        """Get all completed goals."""
        return [g for g in self._goals.values() if g.status == GoalStatus.COMPLETED.value]

    def get_pending_goals(self) -> List[Goal]:
        """Get all pending goals."""
        return [g for g in self._goals.values() if g.status == GoalStatus.PENDING.value]

    def cleanup_completed(self, current_tick: int, keep_ticks: int = 100):
        """Remove completed goals older than keep_ticks."""
        cutoff_tick = current_tick - keep_ticks

        to_remove = []
        for goal_id, goal in self._goals.items():
            if (
                goal.status == GoalStatus.COMPLETED.value
                and goal.completed_tick is not None
                and goal.completed_tick < cutoff_tick
            ):
                to_remove.append(goal_id)

        for goal_id in to_remove:
            del self._goals[goal_id]

        return len(to_remove)
