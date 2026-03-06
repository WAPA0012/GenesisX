"""Affect System - RPE and emotion dynamics.

Based on Section 3.7 of the paper.
"""
from .value_function import ValueFunction
from .rpe import compute_rpe, RPEComputer, compute_per_dimension_rpe, compute_weighted_rpe
from .mood import (
    update_mood,
    update_mood_per_dimension,
    update_affect,
    update_affect_per_dimension,
)
from .stress_affect import update_stress
from .modulation import AffectModulation

__all__ = [
    "ValueFunction",
    "compute_rpe",
    "RPEComputer",
    "compute_per_dimension_rpe",
    "compute_weighted_rpe",
    "update_mood",
    "update_mood_per_dimension",
    "update_affect",
    "update_affect_per_dimension",
    "update_stress",
    "AffectModulation",
]
