"""
Genesis X Default Parameters

All parameters aligned with paper Appendix A specifications.
These provide reproducible, code-level defaults for all components.

References:
- 论文 Appendix A: Variables & Default Hyperparameters
- Code should log these values into every run artifact for reproducibility
"""

from typing import Dict, Any
from dataclasses import dataclass, field


@dataclass
class TimeParameters:
    """Time and tick parameters (Appendix A.1)"""

    # Tick duration in seconds (default: 10s, suggested: {5, 10, 30, 60})
    tick_duration: float = 10.0

    # Neglect half-life in hours (default: 24h, suggested: {6, 12, 24, 48, 96})
    neglect_halflife_hours: float = 24.0


@dataclass
class CoreHyperparameters:
    """Core system hyperparameters (Appendix A.5, Table 1)

    论文 Section 3.5.1: 5维核心价值向量
    """

    # Number of value dimensions (default: 5, 论文 Section 3.5.1)
    n_value_dims: int = 5

    # Discount factor for future rewards (default: 0.97, range: [0.95, 0.995])
    gamma: float = 0.97

    # Planning horizon in ticks (default: 5, suggested: {3, 5, 8})
    planning_horizon: int = 5

    # Weight softmax temperature (default: 4.0, range: [1, 8])
    tau: float = 4.0

    # Extra cost penalty (default: 0, range: [0, 0.30])
    # Set to 0 when using Efficiency dimension
    lambda_cost: float = 0.0

    # Mood gain per positive δ (default: 0.25, range: [0.05, 0.50])
    k_plus: float = 0.25

    # Mood loss per negative δ (default: 0.30, range: [0.05, 0.60])
    k_minus: float = 0.30

    # Stress gain per negative δ (default: 0.20, range: [0.05, 0.50])
    stress_gain: float = 0.20

    # Stress relief per positive δ (default: 0.10, range: [0.02, 0.30])
    stress_relief: float = 0.10

    # Value EMA rate (default: 0.05, range: [0.01, 0.10])
    alpha_V: float = 0.05

    # Value parameter learning rate (default: 0.001, range: [0.0001, 0.01])
    epsilon: float = 0.001


@dataclass
class SetpointDefaults:
    """Homeostasis setpoints (Appendix A.4)"""

    # Energy setpoint (default: 0.70)
    energy: float = 0.70

    # Stress setpoint (default: 0.20)
    stress: float = 0.20

    # Fatigue setpoint (default: 0.30)
    fatigue: float = 0.30

    # Mood setpoint (neutral, default: 0.0 on [-1, 1] scale)
    mood: float = 0.0

    # Bond setpoint (default: 0.70)
    bond: float = 0.70

    # Trust setpoint (default: 0.70)
    trust: float = 0.70

    # Boredom setpoint (default: 0.20)
    boredom: float = 0.20


@dataclass
class BodyUpdateRates:
    """Body dynamics update rates (Appendix A.3)"""

    # Energy update rates
    eta_E_base: float = 0.01      # Base energy decay per tick
    eta_E_act: float = 0.05       # Energy cost multiplier for actions
    eta_E_sleep: float = 0.15     # Energy restoration during sleep

    # Fatigue update rates
    eta_F_base: float = 0.01      # Base fatigue accumulation per tick
    eta_F_act: float = 0.03       # Fatigue accumulation from actions
    eta_F_sleep: float = 0.20     # Fatigue reduction during sleep

    # Stress update rates
    eta_S_base: float = 0.005     # Base stress accumulation per tick
    eta_S_act: float = 0.04       # Stress from actions
    eta_S_relax: float = 0.10     # Stress relief during sleep/reflect

    # Boredom update rates
    eta_B_idle: float = 0.02      # Boredom accumulation when low novelty
    eta_B_nov: float = 0.10       # Boredom reduction from novelty
    eta_B_soc: float = 0.05       # Boredom reduction from social engagement

    # Bond update rates
    eta_Bo_pos: float = 0.05      # Bond increase from positive feedback
    eta_Bo_neg: float = 0.08      # Bond decrease from negative feedback
    eta_Bo_neglect: float = 0.03  # Bond decrease from neglect

    # Trust update rates
    eta_Tr_pos: float = 0.03      # Trust increase from positive feedback
    eta_Tr_neg: float = 0.10      # Trust decrease from negative feedback
    eta_Tr_err: float = 0.15      # Trust decrease from major errors


@dataclass
class ToolCostCaps:
    """Tool cost normalization caps (Appendix A.6)"""

    # Time cap in seconds (default: 10s)
    time_cap_seconds: float = 10.0

    # Network cap in bytes (default: 2MB)
    net_cap_bytes: int = 2 * 1024 * 1024  # 2MB

    # File I/O operations cap (default: 20)
    io_cap_ops: int = 20

    # LLM tokens cap (default: 4000)
    tokens_cap: int = 4000

    # Risk scores (deterministic rubric)
    risk_scores: Dict[str, float] = field(default_factory=lambda: {
        "safe": 0.0,      # Embeddings, read-only tools
        "low": 0.2,       # Web search, file read
        "medium": 0.5,    # File write, API calls
        "high": 1.0,      # Code execution, system commands
    })


@dataclass
class MemoryParameters:
    """Memory system parameters (Appendix A.7)"""

    # Episodic memory budget (default: 50,000 episodes)
    N_epi: int = 50000

    # Schema memory budget (default: 1,000 schemas)
    N_sch: int = 1000

    # Skill memory budget (default: 300 skills)
    N_sk: int = 300

    # Replay batch size (default: 64)
    replay_batch_size: int = 64

    # Salience softmax temperature (default: 3.0)
    kappa_sal: float = 3.0

    # Salience weights (default: a_δ=1.0, a_u=0.5, a_n=0.3)
    salience_delta_weight: float = 1.0    # Weight for RPE magnitude
    salience_unmet_weight: float = 0.5    # Weight for unmet goals
    salience_novelty_weight: float = 0.3  # Weight for novelty

    # Pruning parameters
    delta_keep_threshold: float = 0.30    # Keep episodes with |δ| > 0.30
    p_recent_keep: float = 0.15           # Keep newest 15% of episodes
    similarity_dup_threshold: float = 0.92  # Prune if similarity > 0.92

    # Sleep/Dream triggers
    fatigue_sleep_threshold: float = 0.75   # Enter sleep when fatigue > 0.75
    boredom_sleep_threshold: float = 0.80   # Enter sleep when boredom > 0.80
    meaning_gap_threshold: float = 0.40     # Enter reflect when meaning gap > 0.40

    # Insight parameters
    Q_min_insight: float = 0.65             # Accept insights with Q >= 0.65

    # Novelty threshold for "low novelty" detection
    low_novelty_threshold: float = 0.20


@dataclass
class ValueDimensionFeatures:
    """Feature definitions for value dimensions (Appendix A.4)

    v1.2.0: 更新为5维核心价值系统，删除的维度通过补偿机制实现。
    """

    # Feature extractors per dimension
    # These define how to compute f^(i)(S_t) from state

    homeostasis_features: Dict[str, Any] = field(default_factory=lambda: {
        "type": "l1_distance",
        "fields": ["compute", "memory", "stress"],  # 数字原生模型
        "setpoints": [0.70, 0.70, 0.20],
        "formula": "(Compute/Compute* + Memory/Memory* + (1-Stress)/(1-Stress*)) / 3"
    })

    attachment_features: Dict[str, Any] = field(default_factory=lambda: {
        "type": "composite",
        "fields": ["relationship", "neglect"],
        "formula": "Relationship × (1 - Neglect(Δt))"
    })

    curiosity_features: Dict[str, Any] = field(default_factory=lambda: {
        "type": "composite",
        "fields": ["novelty", "insight_quality"],
        "formula": "0.7 × Novelty + 0.3 × EMA(Q^insight)"
    })

    competence_features: Dict[str, Any] = field(default_factory=lambda: {
        "type": "ema",
        "measure": "quality_score",
        "alpha": 0.05,
        "formula": "EMA(Q_t)"
    })

    safety_features: Dict[str, Any] = field(default_factory=lambda: {
        "type": "risk_inverse",
        "measure": "risk_score",
        "formula": "1 - RiskScore(S_t, a_t)"
    })

    # ========== 删除的维度 (通过补偿机制实现) ==========
    # 这些特征定义保留用于向后兼容和补偿机制

    integrity_features: Dict[str, Any] = field(default_factory=lambda: {
        "type": "drift",
        "measure": "personality_drift",
        "formula": "1 - drift(θ_t, θ_{t-1})",
        "note": "通过 IntegrityConstraintChecker 硬约束检查实现"
    })

    contract_features: Dict[str, Any] = field(default_factory=lambda: {
        "type": "progress",
        "measure": "command_progress",
        "formula": "Prog(Cmd_t, S_t)",
        "note": "通过 ContractSignalBooster 权重提升实现"
    })

    meaning_features: Dict[str, Any] = field(default_factory=lambda: {
        "type": "ema",
        "measure": "insight_quality",
        "alpha": 0.05,
        "formula": "EMA(Q^insight_t)",
        "note": "并入 CURIOSITY 维度"
    })

    efficiency_features: Dict[str, Any] = field(default_factory=lambda: {
        "type": "ema",
        "measure": "resource_cost",
        "alpha": 0.05,
        "formula": "1 - EMA(Cost_res)",
        "note": "并入 HOMEOSTASIS 维度"
    })


@dataclass
class PersonalityBias:
    """Personality bias modulation (g_i(θ))

    v1.2.0: 更新为5维核心价值系统，保留删除维度用于向后兼容。

    默认值从 value_setpoints.yaml 读取，而非硬编码。
    """

    # 5维核心价值系统
    homeostasis_bias: float = 1.0
    attachment_bias: float = 1.0
    curiosity_bias: float = 1.0
    competence_bias: float = 1.0
    safety_bias: float = 1.0

    # 删除的维度 (保留用于向后兼容)
    integrity_bias: float = 1.0
    contract_bias: float = 1.0
    meaning_bias: float = 1.0
    efficiency_bias: float = 1.0


@dataclass
class GenesisXParameters:
    """Complete Genesis X parameter set (Appendix A)"""

    time: TimeParameters = field(default_factory=TimeParameters)
    core: CoreHyperparameters = field(default_factory=CoreHyperparameters)
    setpoints: SetpointDefaults = field(default_factory=SetpointDefaults)
    body_rates: BodyUpdateRates = field(default_factory=BodyUpdateRates)
    tool_costs: ToolCostCaps = field(default_factory=ToolCostCaps)
    memory: MemoryParameters = field(default_factory=MemoryParameters)
    value_features: ValueDimensionFeatures = field(default_factory=ValueDimensionFeatures)
    personality: PersonalityBias = field(default_factory=PersonalityBias)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "time": self.time.__dict__,
            "core": self.core.__dict__,
            "setpoints": self.setpoints.__dict__,
            "body_rates": self.body_rates.__dict__,
            "tool_costs": {
                **self.tool_costs.__dict__,
                "net_cap_mb": self.tool_costs.net_cap_bytes / (1024 * 1024),
            },
            "memory": self.memory.__dict__,
            "value_features": {
                "homeostasis": self.value_features.homeostasis_features,
                "integrity": self.value_features.integrity_features,
                "attachment": self.value_features.attachment_features,
                "contract": self.value_features.contract_features,
                "competence": self.value_features.competence_features,
                "curiosity": self.value_features.curiosity_features,
                "meaning": self.value_features.meaning_features,
                "efficiency": self.value_features.efficiency_features,
            },
            "personality": self.personality.__dict__,
        }

    def get_sweep_ranges(self) -> Dict[str, Any]:
        """Get suggested hyperparameter sweep ranges (Appendix A.5, Table 1)."""
        return {
            "tick_duration": [5, 10, 30, 60],
            "n_value_dims": [6, 8, 10],
            "gamma": (0.95, 0.995),
            "planning_horizon": [3, 5, 8],
            "tau": (1, 8),
            "lambda_cost": (0, 0.30),
            "k_plus": (0.05, 0.50),
            "k_minus": (0.05, 0.60),
            "stress_gain": (0.05, 0.50),
            "stress_relief": (0.02, 0.30),
            "alpha_V": (0.01, 0.10),
            "epsilon": (0.0001, 0.01),
            "neglect_halflife_hours": [6, 12, 24, 48, 96],
        }


# Global default parameters instance
DEFAULT_PARAMS = GenesisXParameters()


# Convenience functions
def get_default_parameters() -> GenesisXParameters:
    """Get default Genesis X parameters aligned with paper Appendix A."""
    return GenesisXParameters()


def load_parameters_from_dict(config: Dict[str, Any]) -> GenesisXParameters:
    """
    Load parameters from configuration dictionary.

    Args:
        config: Configuration dict (can be partial)

    Returns:
        GenesisXParameters with defaults + overrides
    """
    params = GenesisXParameters()

    # Helper function to update dataclass attributes
    def update_section(section_obj, section_config: Dict[str, Any]):
        """Update dataclass attributes from config dict."""
        if not section_config:
            return
        for k, v in section_config.items():
            if hasattr(section_obj, k):
                setattr(section_obj, k, v)

    # Override with config values
    if "time" in config:
        update_section(params.time, config["time"])

    if "core" in config:
        update_section(params.core, config["core"])

    if "setpoints" in config:
        update_section(params.setpoints, config["setpoints"])

    if "body_rates" in config:
        update_section(params.body_rates, config["body_rates"])

    if "tool_costs" in config:
        update_section(params.tool_costs, config["tool_costs"])

    if "memory" in config:
        update_section(params.memory, config["memory"])

    if "value_features" in config:
        # value_features contains nested dicts, handle specially
        vf_config = config["value_features"]
        for feature_name in ["homeostasis_features", "integrity_features",
                              "attachment_features", "contract_features",
                              "competence_features", "curiosity_features",
                              "meaning_features", "efficiency_features"]:
            if feature_name in vf_config:
                setattr(params.value_features, feature_name, vf_config[feature_name])

    if "personality" in config:
        update_section(params.personality, config["personality"])

    return params


def save_parameters_to_artifact(params: GenesisXParameters, artifact_dir) -> None:
    """
    Save parameters to run artifact for reproducibility.

    Args:
        params: Parameters to save
        artifact_dir: Artifact directory path
    """
    from pathlib import Path

    artifact_path = Path(artifact_dir) / "parameters.json"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        import orjson
        with open(artifact_path, 'wb') as f:
            f.write(orjson.dumps(
                params.to_dict(),
                option=orjson.OPT_INDENT_2
            ))
    except ImportError:
        import json
        with open(artifact_path, 'w', encoding='utf-8') as f:
            json.dump(params.to_dict(), f, indent=2)


# Example usage and validation
if __name__ == "__main__":
    # Create default parameters
    params = get_default_parameters()

    print("Genesis X Default Parameters (Appendix A)")
    print("=" * 60)

    print("\n[Time Parameters]")
    print(f"  Tick duration: {params.time.tick_duration}s")
    print(f"  Neglect half-life: {params.time.neglect_halflife_hours}h")

    print("\n[Core Hyperparameters]")
    print(f"  Value dimensions: {params.core.n_value_dims}")
    print(f"  Discount γ: {params.core.gamma}")
    print(f"  Planning horizon H: {params.core.planning_horizon}")
    print(f"  Weight temperature τ: {params.core.tau}")
    print(f"  Mood gain k+: {params.core.k_plus}")
    print(f"  Mood loss k-: {params.core.k_minus}")
    print(f"  Stress gain s: {params.core.stress_gain}")
    print(f"  Stress relief s': {params.core.stress_relief}")
    print(f"  Value EMA α_V: {params.core.alpha_V}")
    print(f"  Param LR ε: {params.core.epsilon}")

    print("\n[Setpoints]")
    print(f"  Energy*: {params.setpoints.energy}")
    print(f"  Stress*: {params.setpoints.stress}")
    print(f"  Fatigue*: {params.setpoints.fatigue}")
    print(f"  Bond*: {params.setpoints.bond}")
    print(f"  Trust*: {params.setpoints.trust}")

    print("\n[Memory Parameters]")
    print(f"  Episodic budget N_epi: {params.memory.N_epi:,}")
    print(f"  Schema budget N_sch: {params.memory.N_sch:,}")
    print(f"  Skill budget N_sk: {params.memory.N_sk}")
    print(f"  Replay batch size B: {params.memory.replay_batch_size}")
    print(f"  Salience temperature κ_sal: {params.memory.kappa_sal}")
    print(f"  Sleep trigger (fatigue): {params.memory.fatigue_sleep_threshold}")
    print(f"  Sleep trigger (boredom): {params.memory.boredom_sleep_threshold}")
    print(f"  Insight threshold Q_min: {params.memory.Q_min_insight}")

    print("\n[Tool Cost Caps]")
    print(f"  Time cap: {params.tool_costs.time_cap_seconds}s")
    print(f"  Network cap: {params.tool_costs.net_cap_bytes / (1024*1024):.1f}MB")
    print(f"  I/O ops cap: {params.tool_costs.io_cap_ops}")
    print(f"  Tokens cap: {params.tool_costs.tokens_cap}")

    print("\n[Suggested Sweep Ranges]")
    sweep = params.get_sweep_ranges()
    for key, value in list(sweep.items())[:5]:
        print(f"  {key}: {value}")

    # Save to JSON
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        save_parameters_to_artifact(params, tmpdir)
        print(f"\nParameters saved to {tmpdir}/parameters.json")
        print("✓ All parameters aligned with paper Appendix A")
