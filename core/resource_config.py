"""Resource Configuration Loader - Load resource budget settings from YAML.

This module provides functions to load resource configuration including:
- Unlimited resources (哪些资源不受限制)
- Budget limits (预算限制)
- Emergency thresholds (紧急阈值)
- Recovery parameters (恢复参数)

Author: Genesis X Team
"""

from pathlib import Path
from typing import Dict, Any, Optional, Set
import yaml

from common.logger import get_logger

logger = get_logger(__name__)


# Default configuration directory
DEFAULT_CONFIG_DIR = Path("config")

# Default configuration values
DEFAULT_UNLIMITED_RESOURCES: Set[str] = {'cpu_tokens'}
DEFAULT_BUDGETS = {
    "cpu_tokens": 100000.0,
    "io_ops": 1000.0,
    "net_bytes": 10000000.0,
    "money": 10.0,
    "risk_score": 0.5,
}

DEFAULT_EMERGENCY_THRESHOLDS = {
    "cpu_tokens": 0.1,
    "compute": 0.3,
    "memory": 0.3,
    "resource_pressure": 0.35,
}

DEFAULT_RECOVERY = {
    "compute_recovery_rate": 0.02,
    "memory_recovery_rate": 0.01,
    "stress_decay_rate": 0.01,
}


class ResourceConfig:
    """Resource configuration loaded from YAML files.

    Attributes:
        unlimited_resources: 资源名称集合，这些资源将不受限制
        budgets: 各资源的预算限制
        emergency_thresholds: 紧急状态阈值
        recovery: 资源恢复参数
    """

    def __init__(
        self,
        unlimited_resources: Optional[Set[str]] = None,
        budgets: Optional[Dict[str, float]] = None,
        emergency_thresholds: Optional[Dict[str, float]] = None,
        recovery: Optional[Dict[str, float]] = None,
    ):
        """Initialize resource configuration.

        Args:
            unlimited_resources: 不受限制的资源名称集合
            budgets: 各资源的预算限制
            emergency_thresholds: 紧急状态阈值
            recovery: 资源恢复参数
        """
        self.unlimited_resources = unlimited_resources or DEFAULT_UNLIMITED_RESOURCES.copy()
        self.budgets = budgets or DEFAULT_BUDGETS.copy()
        self.emergency_thresholds = emergency_thresholds or DEFAULT_EMERGENCY_THRESHOLDS.copy()
        self.recovery = recovery or DEFAULT_RECOVERY.copy()

        # Validate
        self._validate()

    def _validate(self):
        """Validate configuration values."""
        # Validate budgets are positive
        for name, value in self.budgets.items():
            if value < 0:
                raise ValueError(f"Budget for {name} must be non-negative, got {value}")

        # Validate thresholds are in [0, 1]
        for name, value in self.emergency_thresholds.items():
            if not (0.0 <= value <= 1.0):
                raise ValueError(f"Threshold for {name} must be in [0, 1], got {value}")

        # Validate recovery rates are non-negative
        for name, value in self.recovery.items():
            if value < 0:
                raise ValueError(f"Recovery rate for {name} must be non-negative, got {value}")

    def is_unlimited(self, resource: str) -> bool:
        """检查资源是否为无限模式.

        Args:
            resource: 资源名称

        Returns:
            True 如果资源不受限制
        """
        return resource in self.unlimited_resources

    def get_budget(self, resource: str) -> float:
        """获取资源预算.

        Args:
            resource: 资源名称

        Returns:
            预算值
        """
        return self.budgets.get(resource, 0.0)

    def get_threshold(self, resource: str) -> float:
        """获取资源紧急阈值.

        Args:
            resource: 资源名称

        Returns:
            阈值
        """
        return self.emergency_thresholds.get(resource, 0.1)

    @classmethod
    def from_yaml(cls, config_dir: Optional[Path] = None) -> 'ResourceConfig':
        """从YAML文件加载资源配置.

        从 config/resources.yaml 加载配置

        Args:
            config_dir: 配置目录路径 (默认: "config")

        Returns:
            ResourceConfig 实例
        """
        config_dir = config_dir or DEFAULT_CONFIG_DIR

        # Initialize with defaults
        unlimited_resources = DEFAULT_UNLIMITED_RESOURCES.copy()
        budgets = DEFAULT_BUDGETS.copy()
        emergency_thresholds = DEFAULT_EMERGENCY_THRESHOLDS.copy()
        recovery = DEFAULT_RECOVERY.copy()

        # Load resources.yaml
        resources_file = config_dir / "resources.yaml"
        if resources_file.exists():
            try:
                with open(resources_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}

                # Read unlimited_resources
                if "unlimited_resources" in data:
                    unlimited_resources = set(data["unlimited_resources"])

                # Read budgets
                if "budgets" in data:
                    budgets.update(data["budgets"])

                # Read emergency_thresholds
                if "emergency_thresholds" in data:
                    emergency_thresholds.update(data["emergency_thresholds"])

                # Read recovery
                if "recovery" in data:
                    recovery.update(data["recovery"])

                logger.info(f"Loaded resource configuration from {resources_file}")
                logger.info(f"  Unlimited resources: {unlimited_resources}")

            except Exception as e:
                logger.error(f"Error loading {resources_file}: {e}, using defaults")
        else:
            logger.warning(f"{resources_file} not found, using default configuration")
            logger.info(f"  Default unlimited resources: {unlimited_resources}")

        return cls(
            unlimited_resources=unlimited_resources,
            budgets=budgets,
            emergency_thresholds=emergency_thresholds,
            recovery=recovery,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "unlimited_resources": list(self.unlimited_resources),
            "budgets": self.budgets.copy(),
            "emergency_thresholds": self.emergency_thresholds.copy(),
            "recovery": self.recovery.copy(),
        }


# Global configuration cache
_global_config: Optional[ResourceConfig] = None


def get_resource_config(config_dir: Optional[Path] = None, reload: bool = False) -> ResourceConfig:
    """Get global resource configuration.

    Args:
        config_dir: Configuration directory path
        reload: Force reload from YAML files

    Returns:
        ResourceConfig instance
    """
    global _global_config

    if _global_config is None or reload:
        _global_config = ResourceConfig.from_yaml(config_dir)

    return _global_config


def reset_global_config():
    """Reset global configuration (mainly for testing)."""
    global _global_config
    _global_config = None


if __name__ == "__main__":
    # Test loading configuration
    print("Testing ResourceConfig loading...")

    try:
        config = ResourceConfig.from_yaml()
        print("\nLoaded configuration:")
        print(f"  Unlimited resources: {config.unlimited_resources}")
        print(f"  Budgets: {config.budgets}")
        print(f"  Emergency thresholds: {config.emergency_thresholds}")
        print(f"  Recovery: {config.recovery}")
        print("\n✓ Configuration loaded successfully")

        # Test individual methods
        print(f"\n  cpu_tokens is unlimited: {config.is_unlimited('cpu_tokens')}")
        print(f"  io_ops is unlimited: {config.is_unlimited('io_ops')}")
    except Exception as e:
        print(f"\n✗ Error loading configuration: {e}")
