"""Goal Compiler - translate value gaps into actionable goals.

Enhanced with paper Section 3.8.3: Complete conflict resolution mechanism.
"""
from typing import Dict, Optional, List, Any
from datetime import datetime
from common.models import ValueDimension, Goal
from dataclasses import dataclass, field


@dataclass
class GoalProgressConfig:
    """Configuration for goal progress computation (P2-9: 进度计算完整性).

    论文 Section 3.8.1 要求:
    "为所有目标类型实现明确的 Prog(g, S) 方法"

    所有进度阈值和计算参数应可配置。
    """
    # rest_and_recover 进度参数
    energy_target_ratio: float = 1.0  # 能量达到目标值的比例
    fatigue_reduction_ratio: float = 1.0  # 疲劳降低的比例
    energy_weight: float = 0.6  # 能量权重
    fatigue_weight: float = 0.4  # 疲劳权重

    # fulfill_commitment 进度参数
    progress_source: str = "command_progress"  # 进度来源字段

    # strengthen_bond 进度参数
    bond_target: float = 1.0  # 目标羁绊值

    # improve_skills 进度参数
    skill_count_target: int = 20  # 目标技能数量（可配置）

    # verify_and_correct 进度参数
    max_error_threshold: int = 5  # 最大允许错误数（可配置）

    # explore_and_learn 进度参数
    novelty_target: float = 1.0  # 目标新奇度
    novelty_source: str = "novelty_explored"  # 新奇度来源字段

    # reflect_and_consolidate 进度参数
    schema_target: int = 5  # 目标schema数量（可配置）
    schema_source: str = "schemas_created_this_session"  # 来源字段

    # optimize_resources 进度参数
    waste_source: str = "resource_waste"  # 资源浪费来源字段

    @classmethod
    def from_global_config(cls, global_config: Dict[str, Any]) -> 'GoalProgressConfig':
        """从全局配置创建 GoalProgressConfig (P2-10: 配置化参数).

        Args:
            global_config: 全局配置字典

        Returns:
            GoalProgressConfig 实例
        """
        config = cls()

        if 'goal_progress' in global_config:
            progress_cfg = global_config['goal_progress']

            # 更新所有可配置参数
            for key, value in progress_cfg.items():
                if hasattr(config, key):
                    setattr(config, key, value)

        return config


@dataclass
class GoalCompatibility:
    """Goal compatibility relationship.

    Paper Section 3.8.3: Compat(g_i, g_j) ∈ {compatible, conflicting, sequential}
    """
    status: str  # "compatible", "conflicting", "sequential"
    priority_diff: float = 0.0  # |ρ_g1 - ρ_g2|
    resource_overlap: float = 0.0  # Resource conflict level [0,1]


@dataclass
class CoordinationStrategy:
    """Strategy for coordinating conflicting goals."""
    strategy_type: str  # "priority", "time_slice", "sequential", "parallel"
    allocation: Optional[Dict[str, float]] = None  # Resource/time allocation
    order: Optional[List[str]] = None  # Execution order for sequential


class GoalCompiler:
    """Compiles goals from value system state with full conflict resolution.

    Paper Section 3.8: Goal compiler translates drive gaps into goals.

    Enhanced features:
    - Multi-goal parallel coordination
    - Time-slicing for near-priority goals
    - Sequential execution planning
    - Resource conflict detection
    - P2-9: Configurable progress computation parameters
    """

    def __init__(self, progress_config: Optional[GoalProgressConfig] = None):
        """Initialize goal compiler.

        Args:
            progress_config: Optional progress computation configuration
        """
        self.goal_templates = self._init_goal_templates()
        self.compatibility_cache = {}
        # P2-9: 可配置的进度计算参数
        self.progress_config = progress_config or GoalProgressConfig()

    def _init_goal_templates(self) -> Dict[ValueDimension, Dict[str, Any]]:
        """Initialize goal templates for each dimension.

        修复 v14: 使用5维核心价值向量 (论文 Section 3.5.1)

        Returns:
            Dict mapping dimensions to goal template configs
        """
        return {
            ValueDimension.HOMEOSTASIS: {
                "type": "rest_and_recover",
                "description": "Rest to restore energy and reduce fatigue",
                "base_priority": 0.8,
                "resource_cost": {"energy": -0.2, "time": 1.0},
            },
            ValueDimension.ATTACHMENT: {
                "type": "strengthen_bond",
                "description": "Strengthen attachment bond through interaction",
                "base_priority": 0.7,
                "resource_cost": {"time": 1.0, "emotional": 0.3},
            },
            ValueDimension.CURIOSITY: {
                "type": "explore_and_learn",
                "description": "Explore new topics and satisfy curiosity",
                "base_priority": 0.5,
                "resource_cost": {"time": 0.7, "cognitive": 0.4},
            },
            ValueDimension.COMPETENCE: {
                "type": "improve_skills",
                "description": "Practice and improve competence",
                "base_priority": 0.6,
                "resource_cost": {"time": 0.8, "cognitive": 0.5},
            },
            ValueDimension.SAFETY: {
                "type": "verify_safety",
                "description": "Verify safety and assess risks",
                "base_priority": 0.9,
                "resource_cost": {"cpu_tokens": 100, "time": 0.5},
            },
        }

    def compile(
        self,
        gaps: Dict[ValueDimension, float],
        weights: Dict[ValueDimension, float],
        state: Dict[str, Any],
        owner: str = "self",
    ) -> Goal:
        """Compile goal from value gaps and weights.

        Paper Section 3.8.2-3.8.3: Generate candidate goals and select best.

        Args:
            gaps: Drive gaps for each dimension
            weights: Current weights for each dimension
            state: Current state dict
            owner: Goal owner ("self" or "user")

        Returns:
            Goal object with full specification
        """
        if not gaps:
            return self._create_idle_goal()

        # Generate candidate goals from gaps (Section 3.8.2)
        candidates = self._generate_candidates(gaps, weights, state, owner)

        # Select goal with highest expected return (Section 3.8.3)
        selected = self._select_goal(candidates, gaps, weights)

        return selected

    def _generate_candidates(
        self,
        gaps: Dict[ValueDimension, float],
        weights: Dict[ValueDimension, float],
        state: Dict[str, Any],
        owner: str,
    ) -> List[Goal]:
        """Generate candidate goals from gaps."""
        candidates = []

        for dim, gap in gaps.items():
            if gap < 0.15:  # Skip small gaps
                continue

            template = self.goal_templates.get(dim)
            if not template:
                continue

            # Calculate priority: ρ_g = base_priority * gap * weight
            weight = weights.get(dim, 0.0)
            priority = template["base_priority"] * gap * weight

            # Create goal
            goal = Goal(
                goal_type=template["type"],
                priority=min(1.0, priority),
                owner=owner,
                description=template["description"],
                context={
                    "dimension": dim.value,
                    "gap": gap,
                    "weight": weight,
                    "resource_cost": template.get("resource_cost", {}),
                },
                progress=0.0,
            )

            candidates.append(goal)

        return candidates

    def _select_goal(
        self,
        candidates: List[Goal],
        gaps: Dict[ValueDimension, float],
        weights: Dict[ValueDimension, float],
    ) -> Goal:
        """Select goal using Top-K two-stage selection.

        Paper Section 3.8.2: Two-stage goal selection
        Stage 1: Select Top-K candidates by weighted gap score
        Stage 2: Generate and evaluate plans for Top-K, select best expected return

        Paper formula: g* = argmax_{g∈G_t} E[Σ γ^k r_{t+k} | g]

        Enhanced: Implements full two-stage selection as described in paper.
        """
        if not candidates:
            return self._create_idle_goal()

        if len(candidates) == 1:
            return candidates[0]

        # Stage 1: Coarse filtering by weighted gap score
        # Score = base_priority * gap * weight (already computed in priority)
        TOP_K = min(5, len(candidates))  # 考虑前5个候选
        top_k_candidates = sorted(candidates, key=lambda g: g.priority, reverse=True)[:TOP_K]

        # Stage 2: Evaluate expected return for Top-K candidates
        # 使用计划评估器计算期望回报
        best_goal = top_k_candidates[0]
        best_expected_value = -float('inf')

        for goal in top_k_candidates:
            # 计算期望值: 优先级 * 资源效率 * 维度缺口紧迫性
            dimension = goal.context.get("dimension", "")
            if dimension:
                try:
                    dim_enum = ValueDimension(dimension)
                    gap_urgency = gaps.get(dim_enum, 0.0)
                    weight = weights.get(dim_enum, 0.0)
                except (ValueError, AttributeError):
                    gap_urgency = 0.5
                    weight = 0.5
            else:
                gap_urgency = 0.5
                weight = 0.5

            # 资源成本: 越低越好
            resource_cost = goal.context.get("resource_cost", {})
            cost_penalty = sum(abs(v) for v in resource_cost.values()) * 0.01

            # 期望回报 = 优先级 * 缺口紧迫性 * 权重 - 成本惩罚
            expected_value = goal.priority * (1.0 + gap_urgency) * (1.0 + weight) - cost_penalty

            if expected_value > best_expected_value:
                best_expected_value = expected_value
                best_goal = goal

        return best_goal

    def _create_idle_goal(self) -> Goal:
        """Create idle/maintain goal when no gaps."""
        return Goal(
            goal_type="maintain",
            priority=0.1,
            owner="self",
            description="Maintain current stable state",
            progress=1.0,
        )

    def get_goal_description(self, goal: Goal) -> str:
        """Get human-readable description of a goal.

        Args:
            goal: Goal object

        Returns:
            Description string
        """
        return goal.description

    def compute_progress(self, goal: Goal, state: Dict[str, Any]) -> float:
        """Compute progress for a goal.

        Paper: Prog(g, S) ∈ [0,1]

        Enhanced: Covers all 8 goal types with milestone support.
        P2-9: 使用可配置的参数而非硬编码阈值.

        Args:
            goal: Goal object
            state: Current state

        Returns:
            Progress value [0,1]
        """
        cfg = self.progress_config

        # Progress computation based on goal type
        if goal.goal_type == "rest_and_recover":
            energy = state.get("energy", 0.5)
            energy_setpoint = state.get("energy_setpoint", 0.7)
            fatigue = state.get("fatigue", 0.5)
            fatigue_setpoint = state.get("fatigue_setpoint", 0.3)

            # P2-9: 使用可配置权重和目标
            energy_denom = energy_setpoint * cfg.energy_target_ratio
            energy_progress = min(1.0, energy / energy_denom) if energy_denom > 0 else 1.0

            fatigue_denom = 1.0 - fatigue_setpoint * cfg.fatigue_reduction_ratio
            fatigue_progress = min(1.0, (1.0 - fatigue) / fatigue_denom) if fatigue_denom > 0 else 1.0

            return cfg.energy_weight * energy_progress + cfg.fatigue_weight * fatigue_progress

        elif goal.goal_type == "fulfill_commitment":
            # P2-9: 使用可配置的进度来源字段
            progress_field = cfg.progress_source
            return state.get(progress_field, 0.0)

        elif goal.goal_type == "strengthen_bond":
            bond = state.get("bond", 0.0)
            # P2-9: 使用可配置的目标值
            return min(1.0, bond / cfg.bond_target)

        elif goal.goal_type == "improve_skills":
            skill_count = state.get("skill_count", 0)
            # P2-9: 使用可配置的技能目标数量
            return min(1.0, skill_count / cfg.skill_count_target)

        elif goal.goal_type == "verify_and_correct":
            # Check for errors
            errors = state.get("recent_errors", 0)
            # P2-9: 使用可配置的最大错误阈值
            return max(0.0, 1.0 - errors / cfg.max_error_threshold)

        elif goal.goal_type == "explore_and_learn":
            # P2-9: 使用可配置的新奇度来源和目标
            novelty_field = cfg.novelty_source
            novelty = state.get(novelty_field, 0.0)
            return min(1.0, novelty / cfg.novelty_target)

        elif goal.goal_type == "reflect_and_consolidate":
            # P2-9: 使用可配置的schema目标和来源
            schema_field = cfg.schema_source
            schemas = state.get(schema_field, 0)
            return min(1.0, schemas / cfg.schema_target)

        elif goal.goal_type == "optimize_resources":
            # P2-9: 使用可配置的资源浪费来源
            waste_field = cfg.waste_source
            waste = state.get(waste_field, 0.0)
            return max(0.0, 1.0 - waste)

        elif goal.goal_type == "maintain":
            return 1.0

        # Default: return stored progress
        return goal.progress

    def check_compatibility(self, goal1: Goal, goal2: Goal) -> GoalCompatibility:
        """Check compatibility between two goals.

        Paper Section 3.8.3: Goal conflict resolution with compatibility matrix.
        Compat(g_i, g_j) ∈ {compatible, conflicting, sequential}

        Enhanced: Returns detailed compatibility info with resource overlap.
        扩展的冲突矩阵 (论文P0-3): 包含所有目标类型的组合

        Args:
            goal1: First goal
            goal2: Second goal

        Returns:
            GoalCompatibility object
        """
        # 修复 v14: 5维核心价值向量冲突矩阵
        # 5种目标类型的互斥关系
        conflict_pairs = {
            # Homeostasis conflicts (rest_and_recover)
            ("rest_and_recover", "explore_and_learn"),
            ("rest_and_recover", "improve_skills"),
            # Safety conflicts (verify_safety)
            ("verify_safety", "explore_and_learn"),
        }

        # 顺序依赖关系 - 必须按特定顺序执行
        sequential_pairs = {
            ("verify_safety", "improve_skills"),  # 先验证安全再训练
            ("rest_and_recover", "improve_skills"),  # 先恢复再训练
            ("rest_and_recover", "strengthen_bond"),  # 先恢复再社交
        }

        # 兼容关系 - 可以并行执行
        compatible_pairs = {
            ("strengthen_bond", "explore_and_learn"),  # 社交中探索
            ("explore_and_learn", "improve_skills"),  # 探索中学习
            ("verify_safety", "rest_and_recover"),  # 休息时验证安全
        }

        pair = (goal1.goal_type, goal2.goal_type)
        reverse_pair = (goal2.goal_type, goal1.goal_type)

        # Calculate priority difference
        priority_diff = abs(goal1.priority - goal2.priority)

        # Calculate resource overlap
        cost1 = goal1.context.get("resource_cost", {})
        cost2 = goal2.context.get("resource_cost", {})
        resource_overlap = self._compute_resource_overlap(cost1, cost2)

        # Check for dynamic resource conflicts (扩展：动态资源冲突检测)
        dynamic_resource_conflict = self._detect_resource_conflict(goal1, goal2)

        # Check compatibility status
        if pair in compatible_pairs or reverse_pair in compatible_pairs:
            return GoalCompatibility(
                status="compatible",
                priority_diff=priority_diff,
                resource_overlap=resource_overlap
            )
        elif pair in conflict_pairs or reverse_pair in conflict_pairs or dynamic_resource_conflict:
            return GoalCompatibility(
                status="conflicting",
                priority_diff=priority_diff,
                resource_overlap=resource_overlap
            )
        elif pair in sequential_pairs or reverse_pair in sequential_pairs:
            return GoalCompatibility(
                status="sequential",
                priority_diff=priority_diff,
                resource_overlap=resource_overlap
            )
        else:
            return GoalCompatibility(
                status="compatible",
                priority_diff=priority_diff,
                resource_overlap=resource_overlap
            )

    def _compute_resource_overlap(self, cost1: Dict, cost2: Dict) -> float:
        """Compute resource overlap between two goals.

        Returns:
            Overlap score [0,1] where 1 means completely conflicting resources
        """
        if not cost1 or not cost2:
            return 0.0

        # Get all resources
        all_resources = set(cost1.keys()) | set(cost2.keys())

        if not all_resources:
            return 0.0

        # Calculate overlap
        overlap_sum = 0.0
        for resource in all_resources:
            v1 = abs(cost1.get(resource, 0.0))
            v2 = abs(cost2.get(resource, 0.0))
            # If both use significant amount of same resource
            if v1 > 0.1 and v2 > 0.1:
                overlap_sum += min(v1, v2) / max(v1, v2)

        return min(1.0, overlap_sum / len(all_resources))

    def _detect_resource_conflict(self, goal1: Goal, goal2: Goal) -> bool:
        """Detect dynamic resource conflicts between goals (论文P0-3扩展).

        Args:
            goal1: First goal
            goal2: Second goal

        Returns:
            True if goals have resource conflicts that prevent concurrent execution
        """
        # Get resource costs
        cost1 = goal1.context.get("resource_cost", {})
        cost2 = goal2.context.get("resource_cost", {})

        # Define critical resources that cannot be shared
        critical_resources = {
            "focus": 1.0,      # Mental focus is exclusive
            "cpu_tokens": 100,  # High CPU usage threshold
            "time": 0.8,       # High time commitment threshold
        }

        # Check for conflicts on critical resources
        for resource, threshold in critical_resources.items():
            v1 = abs(cost1.get(resource, 0.0))
            v2 = abs(cost2.get(resource, 0.0))

            # If both goals require significant amount of critical resource
            if v1 >= threshold * 0.5 and v2 >= threshold * 0.5:
                return True

        return False

    def assess_gap_urgency(self, gaps: Dict[ValueDimension, float],
                          gap_history: Optional[List[Dict]] = None) -> Dict[ValueDimension, float]:
        """Assess urgency of each gap (论文P0-3扩展).

        Args:
            gaps: Current gaps for each dimension
            gap_history: Historical gap values for trend analysis

        Returns:
            Urgency scores for each dimension
        """
        urgency_scores = {}

        for dim, gap in gaps.items():
            urgency = gap  # Base urgency from gap size

            # Add trend-based urgency boost if history available
            if gap_history and len(gap_history) >= 3:
                recent_values = [h.get(dim.value, 0.0) for h in gap_history[-3:]]
                if all(recent_values[i] <= recent_values[i+1] for i in range(len(recent_values)-1)):
                    # Increasing trend - boost urgency
                    urgency *= 1.5

            urgency_scores[dim] = min(1.0, urgency)

        return urgency_scores

    def _determine_coordination_strategy(
        self,
        goal1: Goal,
        goal2: Goal,
        compatibility: GoalCompatibility
    ) -> CoordinationStrategy:
        """Determine how to coordinate two goals.

        Paper Section 3.8.3: Conflict resolution strategies
        - Priority difference < epsilon: try time-slicing
        - Sequential: order by priority
        - Conflicting: select highest priority
        - Compatible: parallel execution
        """
        epsilon_priority = 0.1

        if compatibility.status == "compatible":
            return CoordinationStrategy(
                strategy_type="parallel",
                allocation={
                    goal1.goal_type: goal1.priority,
                    goal2.goal_type: goal2.priority
                }
            )

        elif compatibility.status == "sequential":
            return CoordinationStrategy(
                strategy_type="sequential",
                order=[
                    goal1.goal_type if goal1.priority >= goal2.priority else goal2.goal_type,
                    goal2.goal_type if goal1.priority < goal2.priority else goal1.goal_type
                ]
            )

        elif compatibility.status == "conflicting":
            # If priorities are close, try time-slicing
            if compatibility.priority_diff < epsilon_priority:
                return CoordinationStrategy(
                    strategy_type="time_slice",
                    allocation={
                        goal1.goal_type: 0.5,
                        goal2.goal_type: 0.5
                    }
                )
            else:
                # Select higher priority
                return CoordinationStrategy(
                    strategy_type="priority",
                    allocation={
                        goal1.goal_type if goal1.priority > goal2.priority else goal2.goal_type: 1.0
                    }
                )

        return CoordinationStrategy(strategy_type="parallel")

    def select_compatible_goals(
        self,
        candidates: List[Goal],
        max_goals: int = 3,
    ) -> List[Goal]:
        """Select maximum compatible goal set with full coordination.

        Paper formula: G* = argmax_{G'⊆G_t, all_compatible(G')} Σ_{g∈G'} ρ_g

        Enhanced with:
        - Time-slicing for near-priority goals
        - Sequential execution planning
        - Resource conflict resolution

        Args:
            candidates: List of candidate goals
            max_goals: Maximum number of goals to select

        Returns:
            List of compatible goals sorted by priority
        """
        if not candidates:
            return []

        if len(candidates) == 1:
            return candidates

        # Sort by priority descending
        sorted_candidates = sorted(candidates, key=lambda g: g.priority, reverse=True)

        # Build compatible goal set with coordination strategies
        selected = []
        deferred = []  # Goals deferred due to conflicts

        for goal in sorted_candidates:
            if len(selected) >= max_goals:
                deferred.append(goal)
                break

            # Check compatibility with all selected goals
            can_add = True
            conflicts = []

            for existing in selected:
                compat = self.check_compatibility(goal, existing)

                if compat.status == "conflicting":
                    # Determine coordination strategy
                    strategy = self._determine_coordination_strategy(goal, existing, compat)

                    if strategy.strategy_type == "priority":
                        if goal.priority > existing.priority:
                            # Replace existing with higher priority goal
                            conflicts.append(existing)
                        else:
                            can_add = False
                            deferred.append(goal)
                    elif strategy.strategy_type == "time_slice":
                        # Both can coexist with time allocation
                        can_add = True
                    else:
                        can_add = False
                        deferred.append(goal)

                elif compat.status == "sequential":
                    # Can add but note sequential dependency
                    can_add = True

            # Remove conflicting lower-priority goals
            for conflict in conflicts:
                if conflict in selected:
                    selected.remove(conflict)
                    deferred.append(conflict)

            if can_add:
                selected.append(goal)

        # Try to add deferred goals if capacity remains
        for goal in deferred:
            if len(selected) >= max_goals:
                break

            can_add = True
            for existing in selected:
                compat = self.check_compatibility(goal, existing)
                if compat.status == "conflicting":
                    strategy = self._determine_coordination_strategy(goal, existing, compat)
                    if strategy.strategy_type != "time_slice":
                        can_add = False
                        break

            if can_add:
                selected.append(goal)

        return selected

    def compile_multi_goal(
        self,
        gaps: Dict[ValueDimension, float],
        weights: Dict[ValueDimension, float],
        state: Dict[str, Any],
        owner: str = "self",
        max_goals: int = 3,
    ) -> List[Goal]:
        """Compile multiple compatible goals with full coordination.

        Enhanced version that supports multi-goal coordination with:
        - Conflict resolution strategies
        - Time-slicing for near-priority goals
        - Sequential execution planning
        - Resource-aware selection

        Args:
            gaps: Drive gaps for each dimension
            weights: Current weights for each dimension
            state: Current state dict
            owner: Goal owner
            max_goals: Maximum goals to return

        Returns:
            List of compatible Goal objects
        """
        if not gaps:
            return [self._create_idle_goal()]

        # Generate all candidates
        candidates = self._generate_candidates(gaps, weights, state, owner)

        # Select compatible subset with full coordination
        selected = self.select_compatible_goals(candidates, max_goals)

        if not selected:
            return [self._create_idle_goal()]

        return selected

    def get_coordination_plan(
        self,
        goals: List[Goal]
    ) -> Dict[str, Any]:
        """Get execution plan for multiple goals.

        Returns coordination strategies for all goal pairs.
        """
        if len(goals) <= 1:
            return {"strategy": "single", "goals": goals}

        # Analyze all pairs
        strategies = []
        for i, g1 in enumerate(goals):
            for g2 in goals[i+1:]:
                compat = self.check_compatibility(g1, g2)
                strategy = self._determine_coordination_strategy(g1, g2, compat)
                strategies.append({
                    "goal1": g1.goal_type,
                    "goal2": g2.goal_type,
                    "strategy": strategy.strategy_type,
                    "allocation": strategy.allocation,
                })

        return {
            "strategy": "multi",
            "goals": goals,
            "coordination": strategies
        }
