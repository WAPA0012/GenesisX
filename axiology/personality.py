"""
Personality: Soul Field (θ) Parameters

Defines the personality DNA that influences:
- Big Five personality traits (O, C, E, A, N)
- Intermediate variables (ET_t, CT_t, ES_t)
- Value dimension biases (g_i(θ))
- Temperature parameter (τ) for weight dynamics
- Exploration tendencies
- Learning rates
- Style preferences

References:
- 论文 Section 3.4.1: Soul Field 人格系统的形式化
- 大五人格模型: θ_t = ⟨O_t, C_t, E_t, A_t, N_t⟩
"""

from typing import Dict, Any, Optional
from pathlib import Path
import yaml
from dataclasses import dataclass, field


@dataclass
class BigFiveTraits:
    """大五人格特质 (Big Five Personality Traits).

    论文 Section 3.4.1:
    θ_t = ⟨O_t, C_t, E_t, A_t, N_t⟩

    Attributes:
        openness (O_t): 开放性 ∈ [0,1]，影响新奇偏好与探索倾向
        conscientiousness (C_t): 尽责性 ∈ [0,1]，影响计划性与自律
        extraversion (E_t): 外向性 ∈ [0,1]，影响社交倾向与表达欲
        agreeableness (A_t): 宜人性 ∈ [0,1]，影响合作倾向与冲突回避
        neuroticism (N_t): 神经质 ∈ [0,1]，影响压力敏感度与情绪波动
    """

    openness: float = 0.7
    conscientiousness: float = 0.6
    extraversion: float = 0.5
    agreeableness: float = 0.7
    neuroticism: float = 0.3

    def __post_init__(self):
        """验证参数范围."""
        for name, value in [
            ("openness", self.openness),
            ("conscientiousness", self.conscientiousness),
            ("extraversion", self.extraversion),
            ("agreeableness", self.agreeableness),
            ("neuroticism", self.neuroticism),
        ]:
            if not (0 <= value <= 1):
                raise ValueError(f"{name} must be in [0, 1], got {value}")

    def to_dict(self) -> Dict[str, float]:
        """转换为字典."""
        return {
            "openness": self.openness,
            "conscientiousness": self.conscientiousness,
            "extraversion": self.extraversion,
            "agreeableness": self.agreeableness,
            "neuroticism": self.neuroticism,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> 'BigFiveTraits':
        """从字典创建."""
        return cls(
            openness=data.get("openness", 0.7),
            conscientiousness=data.get("conscientiousness", 0.6),
            extraversion=data.get("extraversion", 0.5),
            agreeableness=data.get("agreeableness", 0.7),
            neuroticism=data.get("neuroticism", 0.3),
        )


@dataclass
class IntermediateVariables:
    """人格系统的中间变量.

    论文 Section 3.4.1 中间变量层:
    通过3个中间变量聚合大五人格的影响，避免参数空间爆炸。

    Attributes:
        exploration_tendency (ET_t): 探索倾向
        conservation_tendency (CT_t): 保守倾向
        emotional_sensitivity (ES_t): 情绪敏感度
    """

    exploration_tendency: float = 0.0
    conservation_tendency: float = 0.0
    emotional_sensitivity: float = 0.0

    def __post_init__(self):
        """验证参数范围."""
        for name, value in [
            ("exploration_tendency", self.exploration_tendency),
            ("conservation_tendency", self.conservation_tendency),
            ("emotional_sensitivity", self.emotional_sensitivity),
        ]:
            if not (0 <= value <= 1):
                raise ValueError(f"{name} must be in [0, 1], got {value}")

    def to_dict(self) -> Dict[str, float]:
        """转换为字典."""
        return {
            "exploration_tendency": self.exploration_tendency,
            "conservation_tendency": self.conservation_tendency,
            "emotional_sensitivity": self.emotional_sensitivity,
        }


def compute_intermediate_variables(traits: BigFiveTraits) -> IntermediateVariables:
    """从大五人格计算中间变量.

    论文 Section 3.4.1 公式:

    1. 探索倾向 (ET_t):
       ET_t = 0.4·O_t + 0.3·E_t + 0.3·(1 - C_t)
       解释: 高开放性、高外向性、低尽责性共同驱动探索行为。

    2. 保守倾向 (CT_t):
       CT_t = 0.5·C_t + 0.3·N_t + 0.2·A_t
       解释: 高尽责性、高神经质、高宜人性共同驱动保守/风险回避行为。

    3. 情绪敏感度 (ES_t):
       ES_t = 0.6·N_t + 0.2·O_t + 0.2·(1 - C_t)
       解释: 高神经质、高开放性、低尽责性共同驱动情绪敏感性。

    Args:
        traits: 大五人格特质

    Returns:
        中间变量 (ET_t, CT_t, ES_t)
    """
    # 探索倾向: ET_t = 0.4*O + 0.3*E + 0.3*(1-C)
    et = (
        0.4 * traits.openness
        + 0.3 * traits.extraversion
        + 0.3 * (1.0 - traits.conscientiousness)
    )

    # 保守倾向: CT_t = 0.5*C + 0.3*N + 0.2*A
    ct = (
        0.5 * traits.conscientiousness
        + 0.3 * traits.neuroticism
        + 0.2 * traits.agreeableness
    )

    # 情绪敏感度: ES_t = 0.6*N + 0.2*O + 0.2*(1-C)
    es = (
        0.6 * traits.neuroticism
        + 0.2 * traits.openness
        + 0.2 * (1.0 - traits.conscientiousness)
    )

    return IntermediateVariables(
        exploration_tendency=max(0.0, min(1.0, et)),
        conservation_tendency=max(0.0, min(1.0, ct)),
        emotional_sensitivity=max(0.0, min(1.0, es)),
    )


@dataclass
class InteractionStyle:
    """交互风格参数 (φ_t).

    论文 Section 3.4.1:
    φ_t = ⟨initiative, expressiveness, humor, formality⟩

    Attributes:
        initiative: 主动性 ∈ [0,1]，发起行为的倾向
        expressiveness: 表达性 ∈ [0,1]，语言风格的变化范围
        humor: 幽默感 ∈ [0,1]，轻松氛围的生成倾向
        formality: 正式度 ∈ [0,1]，语言正式程度
    """

    initiative: float = 0.5
    expressiveness: float = 0.6
    humor: float = 0.3
    formality: float = 0.5

    def to_dict(self) -> Dict[str, float]:
        """转换为字典."""
        return {
            "initiative": self.initiative,
            "expressiveness": self.expressiveness,
            "humor": self.humor,
            "formality": self.formality,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> 'InteractionStyle':
        """从字典创建."""
        return cls(
            initiative=data.get("initiative", 0.5),
            expressiveness=data.get("expressiveness", 0.6),
            humor=data.get("humor", 0.3),
            formality=data.get("formality", 0.5),
        )


class Personality:
    """
    Personality parameters (θ) - the "Soul Field" DNA.

    论文 Section 3.4.1: Soul Field 人格系统的形式化

    These are slow-changing parameters that define individual character:
    - Big Five traits: O, C, E, A, N
    - Intermediate variables: ET_t, CT_t, ES_t
    - Interaction style: initiative, expressiveness, humor, formality
    - Value biases: how much each dimension is naturally emphasized
    - Temperature: how sharply to focus on high-gap dimensions
    """

    # Default personality parameters (修复 v15: 5维核心价值向量)
    DEFAULT_PARAMS = {
        # Value dimension biases (multiplicative factor on gaps)
        # 论文 Section 3.5.1: 5维核心价值向量
        # 论文 Section 3.6.2: g_i(θ) 人格偏置系数
        "biases": {
            "homeostasis": 1.0,   # 资源稳态
            "attachment": 1.0,    # 社交连接
            "curiosity": 1.0,     # 好奇探索
            "competence": 1.0,    # 胜任目标
            "safety": 1.0,        # 风险回避
        },

        # Temperature for softmax (paper Appendix A.5: τ = 4.0)
        "temperature": 4.0,

        # Exploration parameters
        "exploration_rate": 0.1,           # Base exploration probability
        "exploration_decay": 0.995,        # Decay per step
        "min_exploration": 0.01,           # Minimum exploration

        # Learning rates
        "value_learning_rate": 0.01,       # How fast V(s) adapts
        "setpoint_learning_rate": 0.001,   # How fast setpoints drift
        "skill_learning_rate": 0.1,        # How fast skills improve

        # Affect parameters
        "mood_positive_lr": 0.1,           # Mood update from positive RPE
        "mood_negative_lr": 0.15,          # Mood update from negative RPE (asymmetric)
        "stress_increase_lr": 0.2,         # Stress increase from failure
        "stress_decrease_lr": 0.05,        # Stress recovery (slow)

        # Decision parameters
        "planning_depth": 3,               # How many steps ahead to plan
        "risk_aversion": 0.5,              # Risk penalty weight [0, 1]
        "impatience": 0.9,                 # Discount factor γ
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

        # Initialize with defaults
        self.params = self._deep_copy_dict(self.DEFAULT_PARAMS)

        # Override with config
        if "personality" in self.config:
            self._update_nested(self.params, self.config["personality"])

        # 初始化大五人格 (从 config 或使用默认值)
        traits_data = self.config.get("big_five", {})
        if isinstance(traits_data, dict):
            self.big_five = BigFiveTraits.from_dict(traits_data)
        else:
            self.big_five = BigFiveTraits()

        # 计算中间变量 ET_t, CT_t, ES_t
        self.intermediate = compute_intermediate_variables(self.big_five)

        # 初始化交互风格
        style_data = self.config.get("interaction_style", {})
        if isinstance(style_data, dict):
            self.style = InteractionStyle.from_dict(style_data)
        else:
            self.style = InteractionStyle()

        # Validate parameters
        self._validate()

    @classmethod
    def from_yaml(cls, yaml_path: Path):
        """
        Load personality from YAML file.

        Args:
            yaml_path: Path to personality YAML file

        Returns:
            Personality instance
        """
        if not yaml_path.exists():
            return cls({})

        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return cls(config)
        except (IOError, yaml.YAMLError) as e:
            import logging
            logging.warning(f"Failed to load personality from {yaml_path}: {e}")
            return cls({})

    def get_bias(self, dimension: str) -> float:
        """
        Get bias for a value dimension.

        Args:
            dimension: Value dimension name

        Returns:
            Bias multiplier (typically around 1.0)
        """
        return self.params["biases"].get(dimension, 1.0)

    def get_all_biases(self) -> Dict[str, float]:
        """Get all dimension biases"""
        return self.params["biases"].copy()

    def get_temperature(self) -> float:
        """Get temperature parameter for weight dynamics"""
        return self.params["temperature"]

    def get_exploration_rate(self) -> float:
        """Get current exploration rate"""
        return self.params["exploration_rate"]

    def decay_exploration(self):
        """Decay exploration rate over time"""
        current = self.params["exploration_rate"]
        decay = self.params["exploration_decay"]
        min_explore = self.params["min_exploration"]

        self.params["exploration_rate"] = max(min_explore, current * decay)

    def get_learning_rate(self, rate_type: str) -> float:
        """
        Get learning rate for specific type.

        Args:
            rate_type: One of "value", "setpoint", "skill"

        Returns:
            Learning rate
        """
        key = f"{rate_type}_learning_rate"
        return self.params.get(key, 0.01)

    def get_affect_params(self) -> Dict[str, float]:
        """Get affect-related parameters"""
        return {
            "mood_positive_lr": self.params["mood_positive_lr"],
            "mood_negative_lr": self.params["mood_negative_lr"],
            "stress_increase_lr": self.params["stress_increase_lr"],
            "stress_decrease_lr": self.params["stress_decrease_lr"],
        }

    def get_decision_params(self) -> Dict[str, Any]:
        """Get decision-making parameters"""
        return {
            "planning_depth": self.params["planning_depth"],
            "risk_aversion": self.params["risk_aversion"],
            "discount_factor": self.params["impatience"],
        }

    def get_style_params(self) -> Dict[str, float]:
        """Get communication style parameters"""
        return self.style.to_dict()

    # ========== 论文 Section 3.4.1: 大五人格与中间变量 ==========

    def get_big_five(self) -> BigFiveTraits:
        """获取大五人格特质.

        Returns:
            BigFiveTraits 实例
        """
        return self.big_five

    def get_intermediate_variables(self) -> IntermediateVariables:
        """获取中间变量 (ET_t, CT_t, ES_t).

        论文 Section 3.4.1:
        - ET_t (Exploration Tendency): 探索倾向
        - CT_t (Conservation Tendency): 保守倾向
        - ES_t (Emotional Sensitivity): 情绪敏感度

        Returns:
            IntermediateVariables 实例
        """
        return self.intermediate

    def get_exploration_tendency(self) -> float:
        """获取探索倾向 ET_t.

        ET_t = 0.4·O_t + 0.3·E_t + 0.3·(1 - C_t)

        Returns:
            探索倾向 ∈ [0, 1]
        """
        return self.intermediate.exploration_tendency

    def get_conservation_tendency(self) -> float:
        """获取保守倾向 CT_t.

        CT_t = 0.5·C_t + 0.3·N_t + 0.2·A_t

        Returns:
            保守倾向 ∈ [0, 1]
        """
        return self.intermediate.conservation_tendency

    def get_emotional_sensitivity(self) -> float:
        """获取情绪敏感度 ES_t.

        ES_t = 0.6·N_t + 0.2·O_t + 0.2·(1 - C_t)

        Returns:
            情绪敏感度 ∈ [0, 1]
        """
        return self.intermediate.emotional_sensitivity

    # ========== 论文 Section 3.6.2: 人格对价值权重的调制 ==========

    def modulate_value_weights(self, base_weights: Dict[str, float]) -> Dict[str, float]:
        """根据人格特质调制价值权重.

        论文 Section 3.6.2:
        g_i(θ) = g_base · (1 + λ_i · (CT_t - 0.5))

        其中:
        - g_base: 基准敏感度 (默认 1.0)
        - λ_i: 人格影响强度 (论文默认 0.3)
        - CT_t: 保守倾向 (从中间变量计算)

        各维度的人格调制方向 (论文 Section 3.5.1):
        - HOMEOSTASIS: 与尽责性 正相关
        - ATTACHMENT: 与宜人性 正相关
        - CURIOSITY: 与开放性 正相关
        - COMPETENCE: 与尽责性 正相关
        - SAFETY: 与神经质 正相关

        Args:
            base_weights: 基础价值权重 {dim: weight}

        Returns:
            调制后的价值权重 {dim: modulated_weight}
        """
        ct = self.intermediate.conservation_tendency
        lambda_i = 0.3  # 论文默认人格影响强度
        g_base = 1.0    # 基准敏感度

        # 各维度的特质关联系数
        # 基于大五人格与价值维度的相关性
        trait_associations = {
            "homeostasis": self.big_five.conscientiousness,    # 尽责 → 注重稳态
            "attachment": self.big_five.agreeableness,         # 宜人 → 注重关系
            "curiosity": self.big_five.openness,               # 开放 → 注重好奇
            "competence": self.big_five.conscientiousness,     # 尽责 → 注重胜任
            "safety": self.big_five.neuroticism,               # 神经质 → 注重安全
        }

        modulated = {}
        for dim, weight in base_weights.items():
            if dim not in trait_associations:
                modulated[dim] = weight
                continue

            # 计算人格偏置 g_i(θ)
            # 使用保守倾向作为全局调制因子
            g_i = g_base * (1 + lambda_i * (ct - 0.5))

            # 使用特质关联作为局部调制因子
            trait_factor = trait_associations[dim]

            # 组合调制
            modulated[dim] = weight * g_i * (0.8 + 0.4 * trait_factor)

        # 归一化
        total = sum(modulated.values())
        if total > 0:
            modulated = {k: v / total for k, v in modulated.items()}

        return modulated

    def modulate_value_gaps(self, base_gaps: Dict[str, float]) -> Dict[str, float]:
        """根据人格特质调制价值缺口.

        论文 Section 3.6.2:
        d^(i)_t = d^(i)_t · g_i(θ)

        Args:
            base_gaps: 基础价值缺口 {dim: gap}

        Returns:
            调制后的价值缺口 {dim: modulated_gap}
        """
        ct = self.intermediate.conservation_tendency
        lambda_i = 0.3
        g_base = 1.0

        modulated = {}
        for dim, gap in base_gaps.items():
            g_i = g_base * (1 + lambda_i * (ct - 0.5))
            modulated[dim] = gap * g_i

        return modulated

    def update_big_five(self, **traits: float):
        """更新大五人格特质并重新计算中间变量.

        Args:
            **traits: 要更新的特质 (openness, conscientiousness, etc.)
        """
        for key, value in traits.items():
            if hasattr(self.big_five, key):
                setattr(self.big_five, key, value)
        # 重新计算中间变量
        self.intermediate = compute_intermediate_variables(self.big_five)

    # ========== 向后兼容方法 ==========

    def get_style_params_legacy(self) -> Dict[str, float]:
        """Get communication style parameters (向后兼容)"""
        return self.style.to_dict()

    def update_param(self, key: str, value: Any):
        """
        Update a personality parameter.

        Args:
            key: Parameter key (can be nested like "biases.curiosity")
            value: New value
        """
        keys = key.split(".")

        # Navigate to parent dict
        current = self.params
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        # Set value
        current[keys[-1]] = value

        # Revalidate
        self._validate()

    def save_to_yaml(self, yaml_path: Path):
        """
        Save personality to YAML file.

        Args:
            yaml_path: Path to save YAML
        """
        try:
            yaml_path.parent.mkdir(parents=True, exist_ok=True)
            with open(yaml_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.params, f, default_flow_style=False)
        except (IOError, yaml.YAMLError) as e:
            import logging
            logging.error(f"Failed to save personality to {yaml_path}: {e}")

    def _validate(self):
        """Validate parameter ranges"""
        # Temperature must be positive
        if self.params["temperature"] <= 0:
            raise ValueError("Temperature must be positive")

        # Rates must be in [0, 1]
        for key in ["exploration_rate", "min_exploration", "risk_aversion",
                    "verbosity", "formality", "humor"]:
            if key in self.params:
                val = self.params[key]
                if not (0 <= val <= 1):
                    raise ValueError(f"{key} must be in [0, 1], got {val}")

        # Discount factor must be in (0, 1]
        if not (0 < self.params["impatience"] <= 1):
            raise ValueError("Impatience (discount factor) must be in (0, 1]")

    @staticmethod
    def _deep_copy_dict(d: Dict) -> Dict:
        """Deep copy a dictionary"""
        import copy
        return copy.deepcopy(d)

    @staticmethod
    def _update_nested(target: Dict, source: Dict):
        """Update target dict with source, recursively"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                Personality._update_nested(target[key], value)
            else:
                target[key] = value

    def get_all_params(self) -> Dict[str, Any]:
        """Get all personality parameters"""
        result = self._deep_copy_dict(self.params)
        # 添加大五人格和中间变量
        result["big_five"] = self.big_five.to_dict()
        result["intermediate_variables"] = self.intermediate.to_dict()
        result["interaction_style"] = self.style.to_dict()
        return result

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典用于序列化."""
        return {
            "params": self.params,
            "big_five": self.big_five.to_dict(),
            "intermediate_variables": self.intermediate.to_dict(),
            "interaction_style": self.style.to_dict(),
        }

    def __repr__(self) -> str:
        et = self.intermediate.exploration_tendency
        ct = self.intermediate.conservation_tendency
        return (f"Personality(ET={et:.2f}, CT={ct:.2f}, "
                f"O={self.big_five.openness:.2f}, C={self.big_five.conscientiousness:.2f})")
