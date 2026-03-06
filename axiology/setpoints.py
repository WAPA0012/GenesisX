"""
Setpoints: Value Dimension Setpoint Management

Manages setpoint values (ω) for each value dimension:
- Initial setpoint values
- Drift limits (how much setpoints can change per day)
- Setpoint learning from experience
- Dynamic setpoint adaptation

References:
- 论文 3.5 Axiology Engine
- 代码大纲 axiology/setpoints.py
- 代码大纲 axiology/dynamic_setpoints.py
"""

from typing import Dict, Any, Optional, TYPE_CHECKING, Tuple
from pathlib import Path
from common.logger import get_logger

logger = get_logger(__name__)

# 延迟导入避免循环依赖
if TYPE_CHECKING:
    from .dynamic_setpoints import DynamicSetpointSystem

try:
    import yaml
except ImportError:
    yaml = None


class Setpoints:
    """
    Manages setpoint values for all value dimensions.

    Setpoints represent the "ideal" or "target" value for each dimension.
    They can slowly drift based on experience and learning.
    """

    # Default setpoint values for 5 dimensions (v14)
    # 与 state.py / value_learning.py / value_setpoints.yaml 保持一致
    DEFAULT_SETPOINTS = {
        "homeostasis": 0.70,   # Energy/resource target
        "attachment": 0.70,    # Bond/relationship target
        "curiosity": 0.60,     # Exploration drive target
        "competence": 0.75,    # Skill/capability target
        "safety": 0.80,        # Security/risk-avoidance target
    }

    # Maximum drift per day (in absolute value)
    DEFAULT_DRIFT_LIMITS = {
        "homeostasis": 0.05,   # Homeostasis is relatively stable
        "attachment": 0.10,    # Attachment can vary more
        "curiosity": 0.15,     # Curiosity is most variable
        "competence": 0.08,    # Competence expectations can drift
        "safety": 0.05,        # Safety preferences are stable
    }

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Current setpoints
        self.setpoints = self.DEFAULT_SETPOINTS.copy()

        # Drift limits
        self.drift_limits = self.DEFAULT_DRIFT_LIMITS.copy()

        # Drift accumulation (tracks daily drift)
        self.drift_today = {dim: 0.0 for dim in self.setpoints.keys()}

        # Dynamic learning system (可选)
        self._dynamic_system = None
        self.enable_dynamic_learning = config.get("enable_dynamic_learning", False)

        # Load custom setpoints from config if provided
        if "setpoints" in config:
            self.setpoints.update(config["setpoints"])

        if "drift_limits" in config:
            self.drift_limits.update(config["drift_limits"])

    @classmethod
    def from_yaml(cls, yaml_path: Path):
        """
        Load setpoints from YAML file.

        Args:
            yaml_path: Path to setpoints YAML file

        Returns:
            Setpoints instance
        """
        if yaml is None:
            logger.warning("PyYAML not installed, using default setpoints")
            return cls({})

        if not yaml_path.exists():
            return cls({})

        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return cls(config)
        except (IOError, yaml.YAMLError) as e:
            logger.warning(f"Failed to load setpoints from {yaml_path}: {e}")
            return cls({})

    def get_setpoint(self, dimension: str) -> float:
        """
        Get current setpoint for a dimension.

        Args:
            dimension: Value dimension name

        Returns:
            Setpoint value [0, 1]
        """
        return self.setpoints.get(dimension, 0.5)

    def get_all_setpoints(self) -> Dict[str, float]:
        """Get all current setpoints"""
        return self.setpoints.copy()

    def update_setpoint(
        self,
        dimension: str,
        delta: float,
        force: bool = False
    ) -> bool:
        """
        Update setpoint by delta amount.

        Args:
            dimension: Value dimension name
            delta: Amount to change setpoint (can be negative)
            force: If True, ignore drift limits

        Returns:
            True if update successful
        """
        if dimension not in self.setpoints:
            return False

        # Check drift limit (unless forced)
        if not force:
            current_drift = self.drift_today.get(dimension, 0.0)
            max_drift = self.drift_limits.get(dimension, 0.1)

            # Check if adding this delta would exceed daily limit
            # Track cumulative absolute drift, not absolute of net change
            new_drift = abs(current_drift) + abs(delta)
            if new_drift > max_drift:
                # Clamp delta to stay within limit
                remaining = max_drift - abs(current_drift)
                if delta > 0:
                    delta = min(delta, remaining)
                else:
                    delta = max(delta, -remaining)

        # Apply update with bounds [0, 1]
        new_value = self.setpoints[dimension] + delta
        new_value = max(0.0, min(1.0, new_value))

        self.setpoints[dimension] = new_value

        # Track cumulative absolute drift (not net drift)
        if not force:
            self.drift_today[dimension] = self.drift_today.get(dimension, 0.0) + abs(delta)

        return True

    def reset_daily_drift(self):
        """
        Reset daily drift accumulation.

        Call this at the end of each day (or simulation period).
        """
        self.drift_today = {dim: 0.0 for dim in self.setpoints.keys()}

    def learn_from_experience(
        self,
        dimension: str,
        observed_value: float,
        learning_rate: float = 0.01
    ):
        """
        Slowly adjust setpoint based on experienced values.

        This implements implicit preference learning: if the agent
        consistently experiences higher/lower values in a dimension,
        the setpoint gradually drifts to match.

        Args:
            dimension: Value dimension name
            observed_value: Observed value in [0, 1]
            learning_rate: How fast to adapt (default 0.01 = very slow)
        """
        if dimension not in self.setpoints:
            return

        current_setpoint = self.setpoints[dimension]

        # Calculate drift towards observed value
        delta = (observed_value - current_setpoint) * learning_rate

        # Update with drift limit enforcement
        self.update_setpoint(dimension, delta, force=False)

    def save_to_yaml(self, yaml_path: Path):
        """
        Save current setpoints to YAML file.

        Args:
            yaml_path: Path to save YAML
        """
        data = {
            "setpoints": self.setpoints,
            "drift_limits": self.drift_limits,
        }

        try:
            yaml_path.parent.mkdir(parents=True, exist_ok=True)
            with open(yaml_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False)
        except (IOError, yaml.YAMLError) as e:
            logger.error(f"Failed to save setpoints to {yaml_path}: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about setpoints"""
        base_stats = {
            "setpoints": self.setpoints.copy(),
            "drift_limits": self.drift_limits.copy(),
            "drift_today": self.drift_today.copy(),
            "avg_setpoint": sum(self.setpoints.values()) / len(self.setpoints),
            "min_setpoint": min(self.setpoints.values()),
            "max_setpoint": max(self.setpoints.values()),
            "dynamic_learning_enabled": self.enable_dynamic_learning,
        }

        # 如果启用了动态学习，添加其统计
        if self._dynamic_system is not None:
            base_stats["dynamic_learning"] = self._dynamic_system.get_stats()

        return base_stats

    # =============================================================================
    # 动态设定点学习集成
    # =============================================================================

    def enable_dynamic(
        self,
        mode: str = "hybrid",
        learning_rate: float = 0.01,
        config: Optional[Dict[str, Any]] = None
    ):
        """启用动态设定点学习.

        Args:
            mode: 学习模式 ("experience_driven", "rpe_driven", "hybrid")
            learning_rate: 基础学习率
            config: 额外配置
        """
        from .dynamic_setpoints import create_dynamic_setpoint_system, SetpointLearningConfig

        if config is None:
            config = {}

        config["adjustment_mode"] = mode
        config["base_learning_rate"] = learning_rate

        learning_config = SetpointLearningConfig(**config)
        self._dynamic_system = DynamicSetpointSystem(learning_config)

        # 同步当前设定点
        self._dynamic_system.setpoints = self.setpoints.copy()

        self.enable_dynamic_learning = True
        logger.info(f"Dynamic setpoint learning enabled: mode={mode}, lr={learning_rate}")

    def disable_dynamic(self):
        """禁用动态设定点学习."""
        self.enable_dynamic_learning = False
        self._dynamic_system = None
        logger.info("Dynamic setpoint learning disabled")

    def observe(
        self,
        tick: int,
        features: Dict[str, float],
        rpes: Dict[str, float]
    ):
        """观察当前状态（动态学习）.

        Args:
            tick: 当前时间步
            features: 各维度特征值
            rpes: 各维度RPE
        """
        if self._dynamic_system is not None and self.enable_dynamic_learning:
            self._dynamic_system.observe(tick, features, rpes)

    def update_dynamic(self, tick: int, force: bool = False) -> Dict[str, Tuple[float, float]]:
        """更新动态设定点.

        Args:
            tick: 当前时间步
            force: 是否强制更新

        Returns:
            各维度 (旧设定点, 新设定点) 元组
        """
        if self._dynamic_system is None or not self.enable_dynamic_learning:
            return {}

        # 计算调整
        adjustments = self._dynamic_system.compute_adjustments(tick)

        # 应用调整
        results = self._dynamic_system.apply_adjustments(tick, adjustments, force)

        # 同步到主设定点
        for dim, (old_val, new_val) in results.items():
            delta = new_val - old_val
            self.update_setpoint(dim, delta, force=force)

        return results

    def get_dynamic_system(self):
        """获取动态设定点系统实例."""
        return self._dynamic_system

    def export_dynamic_state(self) -> Optional[Dict[str, Any]]:
        """导出动态学习状态."""
        if self._dynamic_system is not None:
            return self._dynamic_system.export_state()
        return None

    def import_dynamic_state(self, state: Dict[str, Any]):
        """导入动态学习状态."""
        if self._dynamic_system is not None:
            self._dynamic_system.import_state(state)
