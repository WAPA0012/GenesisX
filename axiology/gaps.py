"""Compute drive gaps from features and setpoints.

Enhanced: Load default setpoints from configuration files (value_setpoints.yaml)
instead of hardcoding values.
"""
from typing import Dict, Any
from pathlib import Path
from common.models import ValueDimension

# Try to import configuration loader
try:
    from .axiology_config import get_axiology_config
    _CONFIG_AVAILABLE = True
except ImportError:
    _CONFIG_AVAILABLE = False


def compute_gaps(
    features: Dict[ValueDimension, float],
    setpoints: Dict[ValueDimension, float],
) -> Dict[ValueDimension, float]:
    """Compute drive gaps: d_i = max(0, setpoint - feature).

    Args:
        features: Current feature values
        setpoints: Target setpoint values

    Returns:
        Drive gaps for each dimension
    """
    gaps = {}

    for dim in ValueDimension:
        feature = features.get(dim, 0.5)
        setpoint = setpoints.get(dim, 0.5)

        # Gap is positive when below setpoint
        gap = max(0.0, setpoint - feature)
        gaps[dim] = gap

    return gaps


class GapCalculator:
    """Calculator for value dimension gaps.

    Enhanced: Load default setpoints from value_setpoints.yaml instead of hardcoding.
    """

    def __init__(self, config: Dict[str, Any] = None, config_dir: Path = None):
        """Initialize gap calculator.

        Args:
            config: Configuration dictionary with setpoints (overrides file config)
            config_dir: Configuration directory path (default: "config")
        """
        self.config = config or {}

        # Try to load from configuration file first
        if _CONFIG_AVAILABLE:
            try:
                axiology_config = get_axiology_config(config_dir)
                self.setpoints = axiology_config.setpoints.copy()
            except Exception:
                # Fall back to defaults if loading fails
                self.setpoints = self._get_default_setpoints()
        else:
            self.setpoints = self._get_default_setpoints()

        # Update with provided config if specified
        if "setpoints" in self.config:
            self.setpoints.update(self.config["setpoints"])

    def _get_default_setpoints(self) -> Dict[str, float]:
        """Get default setpoints.

        论文 Section 3.5.1: 5维核心价值向量
        与 state.py / value_learning.py / setpoints.py / value_setpoints.yaml 保持一致
        """
        return {
            "homeostasis": 0.70,
            "attachment": 0.70,
            "curiosity": 0.60,
            "competence": 0.75,
            "safety": 0.80,
        }

    def calculate_gaps(self, state: Dict[str, Any]) -> Dict[str, float]:
        """Calculate gaps for all value dimensions.

        Args:
            state: Current state with dimension values

        Returns:
            Dictionary of gaps for each dimension
        """
        gaps = {}

        for dim_name, setpoint in self.setpoints.items():
            # Extract current value from state
            if dim_name in state and isinstance(state[dim_name], dict):
                current_value = state[dim_name].get("value", 0.5)
            elif dim_name in state:
                current_value = float(state[dim_name])
            else:
                current_value = 0.5

            # Clip to [0, 1]
            current_value = max(0.0, min(1.0, current_value))

            # Calculate gap (positive when below setpoint)
            gap = max(0.0, setpoint - current_value)

            gaps[dim_name] = gap

        return gaps
