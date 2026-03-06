"""Axiology Configuration Loader - Load value system parameters from YAML files.

This module provides functions to load and validate value system configuration
from YAML files (value_setpoints.yaml, default_genome.yaml, etc.).

This ensures that parameters like setpoints, weight_bias, and idle_bias are
read from configuration files rather than hardcoded.

Author: Genesis X Team
"""

from pathlib import Path
from typing import Dict, Any, Optional
import yaml

from common.models import ValueDimension
from common.logger import get_logger

logger = get_logger(__name__)


# Default configuration directory
DEFAULT_CONFIG_DIR = Path("config")

# Default configuration values (used as fallback when config files are missing)
DEFAULT_SETPOINTS = {
    "homeostasis": 0.70,
    "attachment": 0.70,
    "curiosity": 0.60,
    "competence": 0.75,
    "safety": 0.80,
}

DEFAULT_WEIGHT_BIAS = {
    "homeostasis": 1.0,
    "attachment": 0.8,
    "curiosity": 0.7,
    "competence": 1.0,
    "safety": 1.2,
}

DEFAULT_IDLE_BIAS = {
    ValueDimension.HOMEOSTASIS: 0.10,
    ValueDimension.ATTACHMENT: 0.15,
    ValueDimension.CURIOSITY: 0.40,
    ValueDimension.COMPETENCE: 0.20,
    ValueDimension.SAFETY: 0.15,
}

DEFAULT_IDLE_EPSILON = 0.02

DEFAULT_TAU = 4.0  # Temperature for softmax


class AxiologyConfig:
    """Value system configuration loaded from YAML files.

    Attributes:
        setpoints: Target values for each dimension
        weight_bias: Personality bias for each dimension
        idle_bias: Bias vector when all needs are satisfied
        idle_epsilon: Threshold for idle state detection
        tau: Softmax temperature parameter
    """

    def __init__(
        self,
        setpoints: Optional[Dict[str, float]] = None,
        weight_bias: Optional[Dict[str, float]] = None,
        idle_bias: Optional[Dict[ValueDimension, float]] = None,
        idle_epsilon: float = DEFAULT_IDLE_EPSILON,
        tau: float = DEFAULT_TAU,
    ):
        """Initialize axiology configuration.

        Args:
            setpoints: Target values for each dimension
            weight_bias: Personality bias for each dimension
            idle_bias: Bias vector when all needs are satisfied
            idle_epsilon: Threshold for idle state detection
            tau: Softmax temperature parameter
        """
        self.setpoints = setpoints or DEFAULT_SETPOINTS.copy()
        self.weight_bias = weight_bias or DEFAULT_WEIGHT_BIAS.copy()
        self.idle_bias = idle_bias or DEFAULT_IDLE_BIAS.copy()
        self.idle_epsilon = idle_epsilon
        self.tau = tau

        # Validate
        self._validate()

    def _validate(self):
        """Validate configuration values."""
        # Validate setpoints are in [0, 1]
        for dim, value in self.setpoints.items():
            if not (0.0 <= value <= 1.0):
                raise ValueError(f"Setpoint for {dim} must be in [0, 1], got {value}")

        # Validate weight_bias are positive
        for dim, value in self.weight_bias.items():
            if value < 0:
                raise ValueError(f"Weight bias for {dim} must be non-negative, got {value}")

        # Validate idle_bias are in [0, 1]
        for dim, value in self.idle_bias.items():
            if not (0.0 <= value <= 1.0):
                raise ValueError(f"Idle bias for {dim} must be in [0, 1], got {value}")

        # Validate tau is positive
        if self.tau <= 0:
            raise ValueError(f"Tau must be positive, got {self.tau}")

        # Validate idle_epsilon is non-negative
        if self.idle_epsilon < 0:
            raise ValueError(f"Idle epsilon must be non-negative, got {self.idle_epsilon}")

    def get_setpoint(self, dimension: str) -> float:
        """Get setpoint for a dimension.

        Args:
            dimension: Dimension name

        Returns:
            Setpoint value
        """
        return self.setpoints.get(dimension, 0.5)

    def get_weight_bias(self, dimension: str) -> float:
        """Get weight bias for a dimension.

        Args:
            dimension: Dimension name

        Returns:
            Weight bias value
        """
        return self.weight_bias.get(dimension, 1.0)

    @classmethod
    def from_yaml(cls, config_dir: Optional[Path] = None) -> 'AxiologyConfig':
        """Load configuration from YAML files in config directory.

        Loads from:
        - value_setpoints.yaml (setpoints, weight_bias, idle_bias, tau)

        Args:
            config_dir: Configuration directory path (default: "config")

        Returns:
            AxiologyConfig instance
        """
        config_dir = config_dir or DEFAULT_CONFIG_DIR

        # Initialize with defaults
        setpoints = DEFAULT_SETPOINTS.copy()
        weight_bias = DEFAULT_WEIGHT_BIAS.copy()
        idle_bias = {}
        idle_epsilon = DEFAULT_IDLE_EPSILON
        tau = DEFAULT_TAU

        # Load value_setpoints.yaml
        setpoints_file = config_dir / "value_setpoints.yaml"
        if setpoints_file.exists():
            try:
                with open(setpoints_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}

                # Read setpoints
                value_dims = data.get("value_dimensions", {})
                for dim_name, dim_config in value_dims.items():
                    if "setpoint" in dim_config:
                        setpoints[dim_name] = float(dim_config["setpoint"])
                    if "weight_bias" in dim_config:
                        weight_bias[dim_name] = float(dim_config["weight_bias"])

                # Read tau
                if "tau" in data:
                    tau = float(data["tau"])

                # Read idle_bias
                idle_bias_config = data.get("idle_bias", {})
                for dim_name, value in idle_bias_config.items():
                    # Convert string to ValueDimension enum
                    # ValueDimension values are lowercase (e.g., "homeostasis")
                    try:
                        dim = ValueDimension(dim_name.lower())
                        idle_bias[dim] = float(value)
                    except ValueError:
                        logger.warning(f"Invalid dimension name in idle_bias: {dim_name}")

                # Read idle_epsilon
                if "idle_epsilon" in data:
                    idle_epsilon = float(data["idle_epsilon"])

                logger.info(f"Loaded value configuration from {setpoints_file}")

            except Exception as e:
                logger.error(f"Error loading {setpoints_file}: {e}, using defaults")
        else:
            logger.warning(f"{setpoints_file} not found, using default configuration")

        # Convert idle_bias string keys to ValueDimension if needed
        if idle_bias and all(isinstance(k, str) for k in idle_bias.keys()):
            enum_idle_bias = {}
            for dim_name, value in idle_bias.items():
                try:
                    # ValueDimension values are lowercase (e.g., "homeostasis")
                    dim = ValueDimension(dim_name.lower())
                    enum_idle_bias[dim] = value
                except ValueError:
                    # Use default for invalid dimension
                    logger.warning(f"Invalid dimension in idle_bias: {dim_name}, using default")
            idle_bias = enum_idle_bias if enum_idle_bias else DEFAULT_IDLE_BIAS.copy()

        return cls(
            setpoints=setpoints,
            weight_bias=weight_bias,
            idle_bias=idle_bias,
            idle_epsilon=idle_epsilon,
            tau=tau,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "setpoints": self.setpoints.copy(),
            "weight_bias": self.weight_bias.copy(),
            "idle_bias": {k.value if hasattr(k, 'value') else str(k): v
                         for k, v in self.idle_bias.items()},
            "idle_epsilon": self.idle_epsilon,
            "tau": self.tau,
        }


# Global configuration cache
_global_config: Optional[AxiologyConfig] = None


def get_axiology_config(config_dir: Optional[Path] = None, reload: bool = False) -> AxiologyConfig:
    """Get global axiology configuration.

    Args:
        config_dir: Configuration directory path
        reload: Force reload from YAML files

    Returns:
        AxiologyConfig instance
    """
    global _global_config

    if _global_config is None or reload:
        _global_config = AxiologyConfig.from_yaml(config_dir)

    return _global_config


def reset_global_config():
    """Reset global configuration (mainly for testing)."""
    global _global_config
    _global_config = None


if __name__ == "__main__":
    # Test loading configuration
    print("Testing AxiologyConfig loading...")

    try:
        config = AxiologyConfig.from_yaml()
        print("\nLoaded configuration:")
        print(f"  Setpoints: {config.setpoints}")
        print(f"  Weight bias: {config.weight_bias}")
        print(f"  Idle bias: {config.idle_bias}")
        print(f"  Idle epsilon: {config.idle_epsilon}")
        print(f"  Tau: {config.tau}")
        print("\n✓ Configuration loaded successfully")
    except Exception as e:
        print(f"\n✗ Error loading configuration: {e}")
