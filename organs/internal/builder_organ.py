"""Builder Organ - milestone-driven project execution.

支持两种模式：
1. LLM 模式：使用 LLM 进行真正的构建决策
2. 规则模式：使用预设规则进行决策（LLM 不可用时的 fallback）
"""
from typing import List, Dict, Any, Optional, Union, TYPE_CHECKING
from ..base_organ import BaseOrgan
from common.models import Action, Goal
from datetime import datetime, timezone

if TYPE_CHECKING:
    from ..organ_llm_session import OrganLLMSession


class BuilderOrgan(BaseOrgan):
    """Builder organ for long-term project execution.

    Sophisticated project management system that handles:
    - Milestone tracking and progress monitoring
    - Task decomposition and dependency management
    - Resource allocation and prioritization
    - Adaptive planning based on progress
    - Risk assessment and mitigation
    - Quality assurance and review cycles
    - Learning from project outcomes
    """

    # Project status levels
    STATUS_NOT_STARTED = "not_started"
    STATUS_PLANNING = "planning"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_BLOCKED = "blocked"
    STATUS_REVIEW = "review"
    STATUS_COMPLETED = "completed"
    STATUS_ABANDONED = "abandoned"

    # Energy requirements for different work types
    HIGH_COMPLEXITY_ENERGY = 0.6
    MODERATE_COMPLEXITY_ENERGY = 0.4
    LOW_COMPLEXITY_ENERGY = 0.2

    # Progress thresholds
    MILESTONE_COMPLETION_THRESHOLD = 0.8
    CRITICAL_DELAY_THRESHOLD = 0.3  # < 30% expected progress

    # Work strategies
    WORK_STRATEGIES = [
        "focused_sprint",      # Intensive work on single task
        "parallel_execution",  # Multiple tasks simultaneously
        "incremental",         # Small steady progress
        "iterative",          # Build, review, refine cycles
        "exploratory",        # Experimental approach
        "systematic",         # Methodical step-by-step
    ]

    def __init__(self, llm_session: Optional["OrganLLMSession"] = None):
        """Initialize builder organ.

        Args:
            llm_session: LLM 会话（可选，用于真正的构建思考）
        """
        super().__init__("builder")

        # LLM 会话
        self._llm_session = llm_session

        # 最后的思考（用于选择性记忆）
        self._last_thought: Optional[str] = None

        # Project tracking
        self.active_projects = {}  # project_id -> project_data
        self.completed_projects = []  # Historical record
        self.current_milestone = None
        self.milestone_history = []  # Track all milestones

        # Task management
        self.task_queue = []  # Prioritized list of tasks
        self.completed_tasks = []
        self.blocked_tasks = []
        self.task_dependencies = {}  # task_id -> [dependency_ids]

        # Progress tracking
        self.work_sessions = []  # Track work periods
        self.productivity_scores = []  # Historical productivity
        self.last_work_tick = 0
        self.consecutive_work_sessions = 0

        # Strategy and learning
        self.current_strategy = "incremental"
        self.strategy_effectiveness = {s: 0.5 for s in self.WORK_STRATEGIES}

        # Quality metrics
        self.quality_checks_enabled = True
        self.review_frequency = 5  # Review every 5 work sessions

    def set_llm_session(self, session: "OrganLLMSession"):
        """设置 LLM 会话"""
        self._llm_session = session

    def propose_actions(
        self,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[Action]:
        """提议动作 - 如果有 LLM 会话则使用 LLM 思考"""
        if self._llm_session:
            return self._propose_actions_with_llm(state, context)
        else:
            return self._propose_actions_impl(state, context)

    def _propose_actions_with_llm(
        self,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[Action]:
        """使用 LLM 进行构建思考"""
        actions = []

        # 构建思考提示
        prompt = self._build_thinking_prompt(state, context)

        # 调用 LLM 思考
        thought = self._llm_session.think(prompt)

        if thought:
            # 保存最后的思考（用于选择性记忆）
            self._last_thought = thought

            # 解析 LLM 的思考结果为 Action
            actions = self._parse_llm_thought_to_actions(thought, state, context)

        # 如果 LLM 没有返回有效的动作，fallback 到规则模式
        if not actions:
            actions = self._propose_actions_impl(state, context)

        return actions

    def get_last_thought(self) -> Optional[str]:
        """获取最后的思考内容（用于选择性记忆）"""
        return self._last_thought

    def clear_last_thought(self):
        """清除最后的思考"""
        self._last_thought = None

    def _build_thinking_prompt(self, state: Dict[str, Any], context: Dict[str, Any]) -> str:
        """构建构建思考提示"""
        energy = state.get("energy", 0.5)
        stress = state.get("stress", 0.0)
        focus = state.get("focus", 0.5)
        tick = state.get("tick", 0)

        goal = context.get("goal", "无明确目标")

        # 获取活跃项目
        active = [p["goal"] for p in self.active_projects.values()
                  if p["status"] in [self.STATUS_IN_PROGRESS, self.STATUS_PLANNING]]

        prompt = f"""请基于我的当前状态，独立思考并提出你想构建或实现的东西。

【我的当前状态】
- 精力: {energy:.1%}
- 压力: {stress:.1%}
- 专注度: {focus:.1%}
- 当前tick: {tick}

【当前目标】
{goal}

【我正在做的项目】
{active if active else "暂无活跃项目"}

【我的已完成项目】
{len(self.completed_projects)} 个

请回答以下问题：
1. 我现在想构建或实现什么？（不是应该做什么，而是想做什么）
2. 为什么我想做这件事？
3. 我打算怎么开始？

请直接告诉我你的思考，不要使用列表格式。"""
        return prompt

    def _parse_llm_thought_to_actions(
        self,
        thought: str,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[Action]:
        """将 LLM 的思考解析为 Action"""
        actions = []
        thought_lower = thought.lower()

        # 根据 LLM 的思考内容推断构建意图
        if any(kw in thought_lower for kw in ["构建", "实现", "创建", "写代码", "生成", "开发"]):
            actions.append(Action(
                type="GROW",
                params={
                    "task": thought[:100],
                    "source": "llm_thinking",
                    "thought": thought[:200],
                },
                risk_level=0.3,
                capability_req=["llm_access"],
            ))

        # 学习意图
        if any(kw in thought_lower for kw in ["学习", "掌握", "练习", "提高"]):
            actions.append(Action(
                type="LEARN_SKILL",
                params={
                    "skill": "problem_solving",
                    "source": "llm_thinking",
                    "thought": thought[:200],
                },
                risk_level=0.1,
                capability_req=["llm_access"],
            ))

        # 如果没有匹配到任何意图，创建一个通用的构建动作
        if not actions:
            actions.append(Action(
                type="GROW",
                params={
                    "task": "llm_guided_building",
                    "source": "llm_thinking",
                    "thought": thought[:200],
                },
                risk_level=0.3,
                capability_req=["llm_access"],
            ))

        return actions

    def _propose_actions_impl(
        self,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[Action]:
        """Propose project-advancing actions with sophisticated management.

        Args:
            state: Current state
            context: Current context

        Returns:
            List of builder actions
        """
        actions = []

        # Extract relevant state
        goal = state.get("current_goal", context.get("goal", ""))
        tick = state.get("tick", 0)
        energy = state.get("energy", 0.5)
        stress = state.get("stress", 0.0)
        focus = state.get("focus", 0.5)

        # Update builder state
        self._update_builder_state(tick, state, context)

        # === STRATEGY 1: PROJECT INITIALIZATION ===
        # Start new project if goal suggests building something
        if self._should_start_new_project(goal, state):
            init_actions = self._initialize_project(goal, state, context)
            actions.extend(init_actions)

        # === STRATEGY 2: MILESTONE PLANNING ===
        # Break down project into milestones
        if self._should_plan_milestones(state):
            planning_actions = self._plan_milestones(state, context)
            actions.extend(planning_actions)

        # === STRATEGY 3: FOCUSED SPRINT WORK ===
        # Intensive work on critical tasks
        if self._should_do_focused_sprint(energy, stress, focus):
            sprint_actions = self._execute_focused_sprint(state, context)
            actions.extend(sprint_actions)

        # === STRATEGY 4: PARALLEL EXECUTION ===
        # Work on multiple tasks when appropriate
        if self._should_do_parallel_work(energy, focus):
            parallel_actions = self._execute_parallel_work(state, context)
            actions.extend(parallel_actions)

        # === STRATEGY 5: INCREMENTAL PROGRESS ===
        # Steady small steps forward
        if self._should_do_incremental_work(energy):
            incremental_actions = self._execute_incremental_work(state, context)
            actions.extend(incremental_actions)

        # === STRATEGY 6: QUALITY REVIEW ===
        # Review and refine completed work
        if self._should_do_quality_review(tick):
            review_actions = self._execute_quality_review(state, context)
            actions.extend(review_actions)

        # === STRATEGY 7: UNBLOCK TASKS ===
        # Address blocked tasks and dependencies
        if len(self.blocked_tasks) > 0:
            unblock_actions = self._unblock_tasks(state, context)
            actions.extend(unblock_actions)

        # === STRATEGY 8: ADAPTIVE STRATEGY ADJUSTMENT ===
        # Learn from past work sessions and adapt
        if len(self.work_sessions) > 10:
            adaptive_actions = self._adapt_work_strategy(state, context)
            actions.extend(adaptive_actions)

        # === STRATEGY 9: MILESTONE COMPLETION ===
        # Finalize and mark milestones complete
        if self._should_complete_milestone():
            completion_actions = self._complete_milestone(state, context)
            actions.extend(completion_actions)

        return actions

    def _update_builder_state(
        self, tick: int, state: Dict[str, Any], context: Dict[str, Any]
    ):
        """Update internal builder state.

        Args:
            tick: Current tick
            state: Current state
            context: Current context
        """
        # Track work sessions
        if tick - self.last_work_tick < 5:
            self.consecutive_work_sessions += 1
        else:
            self.consecutive_work_sessions = 0

        # Update progress on active projects
        for project_id, project in self.active_projects.items():
            if project["status"] == self.STATUS_IN_PROGRESS:
                # Calculate progress based on completed tasks
                self._update_project_progress(project_id)

    def _update_project_progress(self, project_id: str):
        """Update progress for a specific project.

        Args:
            project_id: Project identifier
        """
        if project_id not in self.active_projects:
            return

        project = self.active_projects[project_id]
        total_tasks = len(project.get("tasks", []))

        if total_tasks == 0:
            project["progress"] = 0.0
            return

        completed = sum(1 for task in project["tasks"] if task.get("status") == "completed")
        project["progress"] = completed / total_tasks

    # === PROJECT LIFECYCLE METHODS ===

    def _should_start_new_project(self, goal: Union[Goal, str, None], state: Dict[str, Any]) -> bool:
        """Determine if should start a new project."""
        # Convert Goal object to string if needed
        goal_str = goal.description if hasattr(goal, 'description') else str(goal)
        # Look for project-oriented keywords
        project_keywords = ["build", "create", "develop", "implement", "construct", "design"]
        has_project_goal = any(keyword in goal_str.lower() for keyword in project_keywords)

        # Don't start if already have active projects
        active_count = sum(
            1 for p in self.active_projects.values()
            if p["status"] in [self.STATUS_IN_PROGRESS, self.STATUS_PLANNING]
        )

        return has_project_goal and active_count < 3

    def _initialize_project(
        self, goal, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Initialize a new project."""
        goal_str = goal.description if hasattr(goal, 'description') else str(goal)
        actions = []

        # Create project structure
        project_id = f"project_{len(self.active_projects) + 1}"
        self.active_projects[project_id] = {
            "id": project_id,
            "goal": goal_str,
            "status": self.STATUS_PLANNING,
            "start_tick": state.get("tick", 0),
            "progress": 0.0,
            "tasks": [],
            "milestones": [],
        }

        # Propose initial planning action
        actions.append(Action(
            type="REFLECT",
            params={
                "purpose": "project_planning",
                "depth": 2,
                "goal": goal_str,
                "output": "project_plan",
                "focus": ["requirements", "milestones", "resources"]
            },
            risk_level=0.1,
            capability_req=["llm_access"],
        ))

        return actions

    def _should_plan_milestones(self, state: Dict[str, Any]) -> bool:
        """Determine if milestone planning is needed."""
        for project in self.active_projects.values():
            if project["status"] == self.STATUS_PLANNING and len(project.get("milestones", [])) == 0:
                return True
        return False

    def _plan_milestones(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Plan milestones for active projects."""
        actions = []

        for project in self.active_projects.values():
            if project["status"] == self.STATUS_PLANNING:
                actions.append(Action(
                    type="REFLECT",
                    params={
                        "purpose": "milestone_decomposition",
                        "depth": 2,
                        "project": project["goal"],
                        "output": "milestone_list",
                    },
                    risk_level=0.1,
                    capability_req=["llm_access"],
                ))

                # Move to in_progress after planning
                project["status"] = self.STATUS_IN_PROGRESS
                # Set current_milestone so _should_complete_milestone can trigger
                self.current_milestone = project["id"]

        return actions

    # === WORK EXECUTION METHODS ===

    def _should_do_focused_sprint(
        self, energy: float, stress: float, focus: float
    ) -> bool:
        """Determine if focused sprint work is appropriate."""
        return (
            energy > self.HIGH_COMPLEXITY_ENERGY and
            stress < 0.5 and
            focus > 0.6 and
            len(self.task_queue) > 0
        )

    def _execute_focused_sprint(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Execute intensive focused work."""
        actions = []

        # Pick highest priority task
        if self.task_queue:
            task = self.task_queue[0]

            actions.append(Action(
                type="LEARN_SKILL",
                params={
                    "skill": task.get("skill", "problem_solving"),
                    "practice_rounds": 5,
                    "approach": "intensive",
                    "focus": "deep_work"
                },
                risk_level=0.2,
                capability_req=["llm_access"],
            ))

            self.current_strategy = "focused_sprint"

        return actions

    def _should_do_parallel_work(self, energy: float, focus: float) -> bool:
        """Determine if parallel work is appropriate."""
        return (
            energy > self.MODERATE_COMPLEXITY_ENERGY and
            focus > 0.5 and
            len(self.task_queue) > 2
        )

    def _execute_parallel_work(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Execute work on multiple tasks."""
        actions = []

        # Work on multiple low-complexity tasks
        for task in self.task_queue[:2]:
            if task.get("complexity", "high") == "low":
                actions.append(Action(
                    type="LEARN_SKILL",
                    params={
                        "skill": task.get("skill", "general"),
                        "practice_rounds": 2,
                        "approach": "parallel",
                    },
                    risk_level=0.1,
                    capability_req=["llm_access"],
                ))

        self.current_strategy = "parallel_execution"
        return actions

    def _should_do_incremental_work(self, energy: float) -> bool:
        """Determine if incremental work is appropriate."""
        return (
            energy > self.LOW_COMPLEXITY_ENERGY and
            len(self.task_queue) > 0
        )

    def _execute_incremental_work(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Execute steady incremental progress."""
        actions = []

        goal = state.get("current_goal", "")
        goal_str = goal.description if hasattr(goal, 'description') else str(goal)
        if goal_str and "improve" in goal_str.lower():
            actions.append(Action(
                type="LEARN_SKILL",
                params={
                    "skill": "problem_solving",
                    "practice_rounds": 3,
                    "approach": "incremental",
                    "consistency": "high"
                },
                risk_level=0.1,
                capability_req=["llm_access"],
            ))

        self.current_strategy = "incremental"
        return actions

    def _should_do_quality_review(self, tick: int) -> bool:
        """Determine if quality review is needed."""
        return (
            self.quality_checks_enabled and
            len(self.work_sessions) > 0 and
            len(self.work_sessions) % self.review_frequency == 0
        )

    def _execute_quality_review(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Execute quality review and refinement."""
        actions = []

        actions.append(Action(
            type="REFLECT",
            params={
                "purpose": "quality_review",
                "depth": 2,
                "focus": ["correctness", "completeness", "improvements"],
                "recent_work": len(self.work_sessions)
            },
            risk_level=0.0,
            capability_req=["llm_access"],
        ))

        return actions

    def _unblock_tasks(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Address blocked tasks and dependencies."""
        actions = []

        if self.blocked_tasks:
            task = self.blocked_tasks[0]

            actions.append(Action(
                type="REFLECT",
                params={
                    "purpose": "unblock_task",
                    "depth": 2,
                    "task": task.get("name", "unknown"),
                    "blocker": task.get("blocker", "unknown"),
                    "focus": "solutions"
                },
                risk_level=0.1,
                capability_req=["llm_access"],
            ))

        return actions

    def _adapt_work_strategy(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Adapt work strategy based on past performance."""
        actions = []

        # Find best performing strategy
        best_strategy = max(
            self.strategy_effectiveness,
            key=self.strategy_effectiveness.get
        )

        # Switch if current strategy isn't performing well
        if (best_strategy != self.current_strategy and
            self.strategy_effectiveness[self.current_strategy] < 0.4):
            self.current_strategy = best_strategy

            actions.append(Action(
                type="REFLECT",
                params={
                    "purpose": "strategy_adjustment",
                    "depth": 1,
                    "new_strategy": best_strategy,
                    "reason": "performance_optimization"
                },
                risk_level=0.0,
                capability_req=[],
            ))

        return actions

    def _should_complete_milestone(self) -> bool:
        """Determine if a milestone should be marked complete."""
        if not self.current_milestone:
            return False

        for project in self.active_projects.values():
            if project["progress"] >= self.MILESTONE_COMPLETION_THRESHOLD:
                return True

        return False

    def _complete_milestone(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Complete and celebrate milestone achievement."""
        actions = []

        for project in self.active_projects.values():
            if project["progress"] >= self.MILESTONE_COMPLETION_THRESHOLD:
                # Mark milestone complete
                self.milestone_history.append({
                    "project": project["id"],
                    "tick": state.get("tick", 0),
                    "progress": project["progress"]
                })

                # Propose reflection on achievement
                actions.append(Action(
                    type="REFLECT",
                    params={
                        "purpose": "milestone_completion",
                        "depth": 1,
                        "project": project["goal"],
                        "achievements": "milestone_reached",
                        "next_steps": True
                    },
                    risk_level=0.0,
                    capability_req=[],
                ))

        return actions

    # === HELPER METHODS ===

    def add_task(
        self, name: str, complexity: str = "medium",
        dependencies: Optional[List[str]] = None
    ):
        """Add a task to the work queue.

        Args:
            name: Task name
            complexity: Task complexity (low/medium/high)
            dependencies: List of task IDs this depends on
        """
        task = {
            "name": name,
            "complexity": complexity,
            "status": "pending",
            "skill": self._infer_skill_from_task(name),
        }

        self.task_queue.append(task)

        if dependencies:
            self.task_dependencies[name] = dependencies

    def complete_task(self, task_name: str, success: bool):
        """Mark a task as complete and update metrics.

        Args:
            task_name: Name of completed task
            success: Whether task was successful
        """
        # Find and remove from queue
        for i, task in enumerate(self.task_queue):
            if task["name"] == task_name:
                task["status"] = "completed"
                self.completed_tasks.append(task)
                self.task_queue.pop(i)
                break

        # Update strategy effectiveness
        if success:
            self.strategy_effectiveness[self.current_strategy] = min(
                1.0, self.strategy_effectiveness[self.current_strategy] + 0.05
            )
        else:
            self.strategy_effectiveness[self.current_strategy] = max(
                0.0, self.strategy_effectiveness[self.current_strategy] - 0.05
            )

    def block_task(self, task_name: str, blocker: str):
        """Mark a task as blocked.

        Args:
            task_name: Name of blocked task
            blocker: Description of what's blocking it
        """
        for i, task in enumerate(self.task_queue):
            if task["name"] == task_name:
                task["status"] = "blocked"
                task["blocker"] = blocker
                self.blocked_tasks.append(task)
                self.task_queue.pop(i)
                break

    def _infer_skill_from_task(self, task_name: str) -> str:
        """Infer required skill from task name.

        Args:
            task_name: Task name

        Returns:
            Skill name
        """
        skill_keywords = {
            "problem_solving": ["solve", "fix", "debug", "troubleshoot"],
            "design": ["design", "architect", "plan", "structure"],
            "implementation": ["implement", "code", "build", "create"],
            "analysis": ["analyze", "evaluate", "assess", "review"],
            "optimization": ["optimize", "improve", "enhance", "refine"],
        }

        task_lower = task_name.lower()
        for skill, keywords in skill_keywords.items():
            if any(keyword in task_lower for keyword in keywords):
                return skill

        return "general"

    def record_work_session(self, tick: int, duration: int, productivity: float):
        """Record a work session for tracking.

        Args:
            tick: Tick when session occurred
            duration: Duration of session
            productivity: Productivity score (0-1)
        """
        self.work_sessions.append({
            "tick": tick,
            "duration": duration,
            "productivity": productivity,
            "strategy": self.current_strategy
        })

        self.productivity_scores.append(productivity)
        self.last_work_tick = tick

        # Keep history manageable
        if len(self.work_sessions) > 100:
            self.work_sessions.pop(0)
        if len(self.productivity_scores) > 100:
            self.productivity_scores.pop(0)

    def get_builder_status(self) -> Dict[str, Any]:
        """Get current builder status for monitoring.

        Returns:
            Dict with builder state information
        """
        avg_productivity = 0.0
        if self.productivity_scores:
            avg_productivity = sum(self.productivity_scores) / len(self.productivity_scores)

        active_count = sum(
            1 for p in self.active_projects.values()
            if p["status"] == self.STATUS_IN_PROGRESS
        )

        return {
            "active_projects": active_count,
            "completed_projects": len(self.completed_projects),
            "tasks_in_queue": len(self.task_queue),
            "completed_tasks": len(self.completed_tasks),
            "blocked_tasks": len(self.blocked_tasks),
            "current_strategy": self.current_strategy,
            "consecutive_work_sessions": self.consecutive_work_sessions,
            "average_productivity": avg_productivity,
            "strategy_effectiveness": self.strategy_effectiveness.copy(),
            "milestones_completed": len(self.milestone_history),
        }

    # ===== Test compatibility methods =====

    def create_project(self, name: str, description: str = "", priority: float = 0.5) -> Dict[str, Any]:
        """Create a new project for test compatibility.

        Args:
            name: Project name/ID
            description: Project description
            priority: Project priority (0-1)

        Returns:
            Project dict
        """
        project_id = name
        project = {
            "name": name,
            "description": description,
            "priority": priority,
            "status": self.STATUS_NOT_STARTED,
            "progress": 0.0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "tasks": [],
            "milestones": [],
        }
        self.active_projects[project_id] = project
        return project

    def break_down_tasks(self, project) -> List[str]:
        """Break down a project into tasks.

        Args:
            project: Project ID string or project dict

        Returns:
            List of task IDs
        """
        # Handle both dict and string inputs
        if isinstance(project, dict):
            project_id = project.get("name", "")
        else:
            project_id = project

        if project_id not in self.active_projects:
            return []

        # Generate some default tasks as dicts (consistent with _update_project_progress)
        task_names = [
            f"{project_id}_task_1",
            f"{project_id}_task_2",
            f"{project_id}_task_3",
        ]

        task_dicts = []
        for task_name in task_names:
            task_dict = {
                "name": task_name,
                "complexity": "medium",
                "status": "pending",
                "skill": self._infer_skill_from_task(task_name),
            }
            task_dicts.append(task_dict)
            self.task_queue.append(task_dict)

        self.active_projects[project_id]["tasks"] = task_dicts

        return task_names

    def breakdown_into_tasks(self, project) -> List[str]:
        """Alias for break_down_tasks for test compatibility."""
        return self.break_down_tasks(project)

    def get_project_status(self, project_id: str = None) -> Any:
        """Get status of projects.

        Args:
            project_id: Optional project ID. If None, returns overall status.

        Returns:
            Project status dict, overall status dict, or None if not found
        """
        if project_id is None:
            # Return overall status with list of active projects (for test compatibility)
            return {
                "active_projects": list(self.active_projects.values()),
                "total_projects": len(self.active_projects),
                "status": "ok"
            }
        return self.active_projects.get(project_id)
