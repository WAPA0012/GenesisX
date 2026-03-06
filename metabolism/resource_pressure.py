"""Resource Pressure Index - RP_t

论文定义:
RP_t = max(0, 1 - (α·Compute_t + β·Memory_t))

资源压力指数用于:
1. 在低资源时触发优先级覆盖 (Ω_t)
2. 调制 Boredom 有效性 (effective_boredom_t = Boredom_t · 1[RP_t < θ_emergency])
3. 影响 Arousal 计算

参考文献:
- 论文 Section 3.2: 数字原生模型
- 论文 Section 3.6.4: 优先级覆盖机制
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ResourcePressureConfig:
    """资源压力指数配置.

    Attributes:
        alpha_compute: 计算资源权重 α
        beta_memory: 内存资源权重 β
        emergency_threshold: 紧急阈值 θ_emergency，当 RP_t < 此值时进入紧急状态
    """

    # 论文公式: RP_t = max(0, 1 - (α·Compute_t + β·Memory_t))
    # α + β = 1 确保资源充足时 RP_t = 0
    alpha_compute: float = 0.6   # 计算资源权重
    beta_memory: float = 0.4     # 内存资源权重

    # θ_emergency: 紧急阈值
    # 当 RP_t > emergency_threshold 时，系统处于资源紧急状态
    # 此时 Boredom 机制被禁用，资源优先用于核心功能
    emergency_threshold: float = 0.35

    def __post_init__(self):
        """验证参数."""
        # α + β 应该接近 1 (允许小误差)
        total = self.alpha_compute + self.beta_memory
        if abs(total - 1.0) > 0.01:
            raise ValueError(
                f"alpha_compute + beta_memory should equal 1.0, got {total}"
            )

        if not (0 <= self.emergency_threshold <= 1):
            raise ValueError(
                f"emergency_threshold should be in [0, 1], got {self.emergency_threshold}"
            )


# 默认配置实例
_default_config: ResourcePressureConfig = ResourcePressureConfig()


def configure_resource_pressure(config: ResourcePressureConfig):
    """配置资源压力参数."""
    global _default_config
    _default_config = config


def compute_resource_pressure(
    compute: float,
    memory: float,
    config: Optional[ResourcePressureConfig] = None
) -> float:
    """计算资源压力指数 RP_t.

    论文公式:
    RP_t = max(0, 1 - (α·Compute_t + β·Memory_t))

    当 Compute_t 和 Memory_t 都充足（接近 1）时，RP_t 接近 0。
    当资源不足时，RP_t 增加，最大为 1。

    Args:
        compute: 计算资源水平 Compute_t ∈ [0, 1]
        memory: 内存资源水平 Memory_t ∈ [0, 1]
        config: 可选配置

    Returns:
        资源压力指数 RP_t ∈ [0, 1]
    """
    cfg = config or _default_config

    # 归一化输入
    compute = max(0.0, min(1.0, compute))
    memory = max(0.0, min(1.0, memory))

    # 论文公式
    weighted_resources = cfg.alpha_compute * compute + cfg.beta_memory * memory
    rp = max(0.0, 1.0 - weighted_resources)

    return rp


def is_emergency_state(
    compute: float,
    memory: float,
    config: Optional[ResourcePressureConfig] = None
) -> bool:
    """判断是否处于资源紧急状态.

    当 RP_t > θ_emergency 时，系统进入紧急状态:
    - Boredom 机制被禁用 (effective_boredom = 0)
    - HOMEOSTASIS 价值维度获得最高优先级
    - 非核心动作被抑制

    Args:
        compute: 计算资源水平
        memory: 内存资源水平
        config: 可选配置

    Returns:
        是否处于紧急状态
    """
    rp = compute_resource_pressure(compute, memory, config)
    cfg = config or _default_config
    return rp > cfg.emergency_threshold


def compute_effective_boredom(
    boredom: float,
    compute: float,
    memory: float,
    config: Optional[ResourcePressureConfig] = None
) -> float:
    """计算有效无聊度.

    论文公式:
    effective_boredom_t = Boredom_t · 1[RP_t < θ_emergency]

    当资源紧急时 (RP_t >= θ_emergency)，Boredom 被禁用，返回 0。
    这确保在资源不足时，系统不会因为"无聊"而消耗资源去探索，
    而是专注于维持核心生存功能。

    Args:
        boredom: 当前无聊度 Boredom_t ∈ [0, 1]
        compute: 计算资源水平
        memory: 内存资源水平
        config: 可选配置

    Returns:
        有效无聊度 ∈ [0, 1]
    """
    if is_emergency_state(compute, memory, config):
        # 紧急状态：禁用无聊机制
        return 0.0
    # 正常状态：使用原始无聊度
    return max(0.0, min(1.0, boredom))


def get_resource_pressure_report(
    compute: float,
    memory: float,
    config: Optional[ResourcePressureConfig] = None
) -> Dict[str, Any]:
    """获取完整的资源压力报告.

    Args:
        compute: 计算资源水平
        memory: 内存资源水平
        config: 可选配置

    Returns:
        包含 RP_t、紧急状态、建议等的字典
    """
    cfg = config or _default_config
    rp = compute_resource_pressure(compute, memory, cfg)
    emergency = is_emergency_state(compute, memory, cfg)

    # 资源状态分类
    if rp < 0.15:
        status = "excellent"  # 资源充足
    elif rp < 0.35:
        status = "normal"  # 正常
    elif rp < 0.60:
        status = "stressed"  # 压力较大
    else:
        status = "critical"  # 严重不足

    # 建议
    if emergency:
        suggestion = "EMERGENCY: Conserve resources, disable non-essential functions"
    elif rp > 0.5:
        suggestion = "WARNING: High resource pressure, reduce activity"
    elif rp > 0.3:
        suggestion = "Moderate pressure, monitor resource usage"
    else:
        suggestion = "Resources adequate, normal operation"

    return {
        "resource_pressure": rp,
        "emergency": emergency,
        "status": status,
        "suggestion": suggestion,
        "compute_level": compute,
        "memory_level": memory,
        "emergency_threshold": cfg.emergency_threshold,
    }


# 便捷函数
def rp_from_state(state: Dict[str, float], config: Optional[ResourcePressureConfig] = None) -> float:
    """从状态字典计算 RP_t.

    便捷函数，用于从包含 compute/memory 的状态字典计算资源压力.

    Args:
        state: 状态字典，需包含 'compute' 和 'memory' 键
        config: 可选配置

    Returns:
        资源压力指数 RP_t
    """
    return compute_resource_pressure(
        state.get("compute", 0.5),
        state.get("memory", 0.5),
        config
    )


if __name__ == "__main__":
    # 测试资源压力计算
    print("Resource Pressure Index Tests")
    print("=" * 60)

    test_cases = [
        (1.0, 1.0, "Full resources"),
        (0.8, 0.85, "Normal (default initial)"),
        (0.5, 0.6, "Medium stress"),
        (0.3, 0.4, "High stress"),
        (0.1, 0.2, "Critical"),
    ]

    for compute, memory, desc in test_cases:
        rp = compute_resource_pressure(compute, memory)
        emergency = is_emergency_state(compute, memory)
        report = get_resource_pressure_report(compute, memory)

        print(f"\n[{desc}]")
        print(f"  Compute={compute:.2f}, Memory={memory:.2f}")
        print(f"  RP_t = {rp:.3f}")
        print(f"  Emergency: {emergency}")
        print(f"  Status: {report['status']}")
        print(f"  Suggestion: {report['suggestion']}")

    # 测试有效无聊度
    print("\n\nEffective Boredom Tests")
    print("=" * 60)

    boredom = 0.7
    for compute, memory, desc in test_cases:
        eff_boredom = compute_effective_boredom(boredom, compute, memory)
        print(f"[{desc}] Boredom={boredom:.2f} -> Effective={eff_boredom:.2f}")
