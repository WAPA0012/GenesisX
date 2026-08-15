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
    # 阶段1.1 调整（2026-07）：原 0.20 是 ETA_IDLE(0.03) 的 6.7 倍，导致只要 novelty > 0.15
    # boredom 就不升反降（被 ETA_NOV·novelty 压制）。降到 0.05：novelty 高时仍能减少无聊，
    # 但不会完全压制 ETA_IDLE 的累积。配合 LOW_NOVELTY_THRESHOLD=0.5，待机状态 novelty~0.43
    # 时 boredom 能缓慢累积（+0.004/tick），约 50 tick 累积到 0.2 触发探索。
    ETA_NOV: float = 0.05

    # η_B^soc: 社交参与减少无聊的量
    ETA_SOC: float = 0.05

    # 低新颖度阈值
    # 阶段1.1 调整（2026-07）：原 0.2 太严格——novelty 要低于 0.2 才触发无聊累积，
    # 但正常待机状态 novelty 多在 0.3-0.5（没新东西但也不算"完全无新意"），
    # 导致系统永远不无聊、永远不探索。提到 0.5：novelty 低于中等就开始无聊，
    # 符合"没新输入就该找事做"的直觉。ETA_IDLE=0.03 很小，不会无聊暴涨。
    LOW_NOVELTY_THRESHOLD: float = 0.5

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

    注：资源压力覆盖（论文 Section 3.6.4 effective_boredom）原由 resource_pressure.py
    的 is_emergency_state 实现，但 life_loop 调用时 compute/memory 恒为默认 1.0（P4-50），
    从不触发。该模块已删除，资源紧急判断统一由 state.py:get_effective_boredom 负责
    （基于真实 psutil 采样的 resource_pressure）。compute/memory/apply_resource_override
    参数保留仅为向后兼容，不再有任何效果。

    Args:
        boredom: Current boredom [0,1]
        dt: Time step
        novelty: Current novelty level [0,1] (from retrieval similarity)
        socially_engaged: Whether the agent is socially engaged (last action was CHAT with user response)
        config: Optional configuration (uses default if not provided)
        compute: (已废弃，保留兼容) Compute resource level
        memory: (已废弃，保留兼容) Memory resource level
        apply_resource_override: (已废弃，保留兼容) 无效果

    Returns:
        Updated boredom in [0,1]
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

    return max(0.0, min(1.0, new_boredom))


def compute_effective_boredom(
    boredom: float,
    compute: float = 1.0,
    memory: float = 1.0,
) -> float:
    """计算有效无聊度（向后兼容存根）.

    原实现依赖 resource_pressure.is_emergency_state（论文 Section 3.6.4），但该模块
    已删除（生产路径 life_loop 不传 compute/memory，此函数从不被运行时调用）。
    资源紧急时的有效无聊度判断统一由 state.py:get_effective_boredom 基于
    真实 psutil 采样的 resource_pressure 实现。

    此存根保留仅为向后兼容（test_fixes 引用），直接返回 clip 后的 boredom。

    Args:
        boredom: 当前原始无聊度 [0,1]
        compute: (已废弃)
        memory: (已废弃)

    Returns:
        clip 后的 boredom [0,1]
    """
    return max(0.0, min(1.0, boredom))
