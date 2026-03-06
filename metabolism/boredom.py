"""Boredom accumulation - 论文 Appendix A.3 η-coefficient formula.

论文公式:
Boredom_{t+1} = clip_{[0,1]}(Boredom_t + η_B^idle * 1[low novelty] - η_B^nov * Novelty_t - η_B^soc * 1[socially engaged])

其中:
- "low novelty" 指 Novelty_t < 0.2
- "socially engaged" 指上一个动作是 CHAT 且用户有回应

有效无聊度 (论文 Section 3.6.4):
effective_boredom_t = Boredom_t · 1[RP_t < θ_emergency]

当资源紧急时 (RP_t >= θ_emergency)，Boredom 被禁用。
"""
from typing import Optional, Dict, Any


class BoredomConfig:
    """Boredom metabolism configuration (论文 Appendix A.3).

    η-coefficients for boredom dynamics.
    """

    # η_B^idle: 低新颖度时的无聊增长率
    ETA_IDLE: float = 0.03

    # η_B^nov: 新颖度减少无聊的系数
    ETA_NOV: float = 0.20

    # η_B^soc: 社交参与减少无聊的量
    ETA_SOC: float = 0.05

    # 低新颖度阈值
    LOW_NOVELTY_THRESHOLD: float = 0.2

    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> 'BoredomConfig':
        """从配置字典创建BoredomConfig."""
        cfg = cls()
        if 'boredom' in config:
            boredom_cfg = config['boredom']
            if 'eta_idle' in boredom_cfg:
                cfg.ETA_IDLE = boredom_cfg['eta_idle']
            if 'eta_nov' in boredom_cfg:
                cfg.ETA_NOV = boredom_cfg['eta_nov']
            if 'eta_soc' in boredom_cfg:
                cfg.ETA_SOC = boredom_cfg['eta_soc']
            if 'low_novelty_threshold' in boredom_cfg:
                cfg.LOW_NOVELTY_THRESHOLD = boredom_cfg['low_novelty_threshold']
        return cfg


# 默认配置实例
_default_config: BoredomConfig = BoredomConfig()


def configure_boredom(config: BoredomConfig):
    """配置无聊代谢参数."""
    global _default_config
    _default_config = config


def update_boredom(
    boredom: float,
    dt: float,
    novelty: float = 0.0,
    socially_engaged: bool = False,
    config: Optional[BoredomConfig] = None,
    compute: float = 1.0,
    memory: float = 1.0,
    apply_resource_override: bool = True,
) -> float:
    """Update boredom level using 论文 Appendix A.3 η-coefficient formula.

    Boredom_{t+1} = clip_{[0,1]}(Boredom_t + η_B^idle * 1[low novelty] - η_B^nov * Novelty_t - η_B^soc * 1[social])

    有效无聊度 (论文 Section 3.6.4):
    effective_boredom_t = Boredom_t · 1[RP_t < θ_emergency]

    Args:
        boredom: Current boredom [0,1]
        dt: Time step
        novelty: Current novelty level [0,1] (from retrieval similarity)
        socially_engaged: Whether the agent is socially engaged (last action was CHAT with user response)
        config: Optional configuration (uses default if not provided)
        compute: Compute resource level [0,1] (for resource pressure check)
        memory: Memory resource level [0,1] (for resource pressure check)
        apply_resource_override: Whether to apply resource pressure override (default: True)

    Returns:
        Updated boredom in [0,1] (effective boredom if resource override enabled)
    """
    cfg = config or _default_config

    # 判断是否低新颖度
    is_low_novelty = 1.0 if novelty < cfg.LOW_NOVELTY_THRESHOLD else 0.0

    # 判断是否社交参与
    is_social = 1.0 if socially_engaged else 0.0

    # 论文公式 (所有η项均乘以dt，保持时间步一致性)
    new_boredom = (
        boredom
        + cfg.ETA_IDLE * is_low_novelty * dt
        - cfg.ETA_NOV * novelty * dt
        - cfg.ETA_SOC * is_social * dt
    )

    new_boredom = max(0.0, min(1.0, new_boredom))

    # 应用资源压力覆盖 (论文 Section 3.6.4)
    if apply_resource_override:
        try:
            from .resource_pressure import is_emergency_state

            if is_emergency_state(compute, memory):
                # 紧急状态：返回 0，禁用无聊机制
                return 0.0
        except ImportError:
            # 如果 resource_pressure 模块不可用，跳过
            pass

    return new_boredom


def compute_effective_boredom(
    boredom: float,
    compute: float,
    memory: float,
) -> float:
    """计算有效无聊度.

    论文公式 (Section 3.6.4):
    effective_boredom_t = Boredom_t · 1[RP_t < θ_emergency]

    Args:
        boredom: 当前原始无聊度 [0,1]
        compute: 计算资源水平 [0,1]
        memory: 内存资源水平 [0,1]

    Returns:
        有效无聊度 [0,1] (资源紧急时返回 0)
    """
    try:
        from .resource_pressure import is_emergency_state

        if is_emergency_state(compute, memory):
            return 0.0
    except ImportError:
        pass

    return max(0.0, min(1.0, boredom))
