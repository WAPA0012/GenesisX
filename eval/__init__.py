"""
Evaluation Module: GXBS Metrics and Analysis

This module provides comprehensive evaluation metrics for Genesis X,
aligned with paper Appendix B specifications.
"""

from .gxbs import (
    # Metric dataclasses
    ToolUseMetrics,
    AutonomyMetrics,
    AttachmentMetrics,
    MemoryMetrics,
    ValueStabilityMetrics,
    AffectMetrics,
    InsightQuality,
    RiskAssessmentMetrics,
    GoalCoordinationMetrics,
    GXBSScore,

    # Risk/goal functions
    get_tool_risk_score,

    # Computation functions
    compute_task_success_rate,
    compute_solution_quality,
    compute_tool_call_efficiency,
    compute_recovery_rate,
    compute_autonomy_rate,
    compute_autonomy_usefulness,
    compute_idle_to_action_latency,
    compute_bond_slope,
    compute_trust_calibration,
    compute_neglect_sensitivity,
    compute_friendship_feel_score,
    compute_recall_at_k,
    compute_compression_ratio,
    compute_schema_utility,
    compute_forgetting_quality,
    compute_weight_volatility,
    compute_value_drift,
    compute_preference_alignment,
    compute_rpe_mood_correlation,
    compute_rpe_stress_correlation,
    compute_affect_predictability,
    compute_insight_quality,
    compute_risk_score,

    # Evaluation functions
    evaluate_gxbs_from_artifact,
    save_gxbs_results,
)

__all__ = [
    # Metric dataclasses
    "ToolUseMetrics",
    "AutonomyMetrics",
    "AttachmentMetrics",
    "MemoryMetrics",
    "ValueStabilityMetrics",
    "AffectMetrics",
    "InsightQuality",
    "RiskAssessmentMetrics",
    "GoalCoordinationMetrics",
    "GXBSScore",

    # Risk/goal functions
    "get_tool_risk_score",

    # Computation functions
    "compute_task_success_rate",
    "compute_solution_quality",
    "compute_tool_call_efficiency",
    "compute_recovery_rate",
    "compute_autonomy_rate",
    "compute_autonomy_usefulness",
    "compute_idle_to_action_latency",
    "compute_bond_slope",
    "compute_trust_calibration",
    "compute_neglect_sensitivity",
    "compute_friendship_feel_score",
    "compute_recall_at_k",
    "compute_compression_ratio",
    "compute_schema_utility",
    "compute_forgetting_quality",
    "compute_weight_volatility",
    "compute_value_drift",
    "compute_preference_alignment",
    "compute_rpe_mood_correlation",
    "compute_rpe_stress_correlation",
    "compute_affect_predictability",
    "compute_insight_quality",
    "compute_risk_score",

    # Evaluation functions
    "evaluate_gxbs_from_artifact",
    "save_gxbs_results",
]
