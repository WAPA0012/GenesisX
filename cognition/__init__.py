"""Cognition system - Goal compilation, planning, and evaluation."""
from .goal_compiler import GoalCompiler
from .planner import Planner
from .plan_evaluator import PlanEvaluator
from .verifier import Verifier
# 注：goal_progress.py（ProgressCalculator/GoalTracker，P4-22 整模块死）和
# insight_quality.py（InsightQualityAssessor，P4-19 整模块死，Q^insight 三重实现之一）
# 已删除——零运行时引用，活路径用 consolidation.InsightQualityEvaluator。

__all__ = [
    "GoalCompiler",
    "Planner",
    "PlanEvaluator",
    "Verifier",
]
