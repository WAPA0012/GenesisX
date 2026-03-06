"""Example: Using Compensation Mechanisms with 5-Dimensional Value System (方案 B)

This example demonstrates how to use the compensation mechanisms to ensure
no functionality is lost when using the 5-dimensional value system.

运行方式:
    python -m axiology.examples.compensation_example

或者:
    from axiology.compensation import CompensationManager
    # 使用下面的示例代码
"""

from typing import Dict, Any
from axiology.compensation import (
    CompensationManager,
    IntegrityConstraintChecker,
    ContractSignalBooster,
    EfficiencyMonitor,
    MeaningTracker,
    ConstraintViolation,
)


def example_integrity_constraint():
    """示例1: 人格完整性约束检查."""
    print("=" * 60)
    print("示例1: 人格完整性约束检查 (INTEGRITY 硬约束)")
    print("=" * 60)

    checker = IntegrityConstraintChecker(drift_threshold=0.20)

    # 正常状态
    normal_state = {
        "personality_drift": 0.05,
        "recent_errors": 0,
        "resource_pressure": 0.3,
    }
    result = checker.check_integrity(normal_state)
    print(f"\n正常状态: {result.to_dict()}")

    # 警告状态
    warning_state = {
        "personality_drift": 0.25,
        "recent_errors": 2,
        "resource_pressure": 0.5,
    }
    result = checker.check_integrity(warning_state)
    print(f"\n警告状态: {result.to_dict()}")

    # 严重状态
    critical_state = {
        "personality_drift": 0.35,
        "recent_errors": 6,
        "resource_pressure": 0.9,
    }
    result = checker.check_integrity(critical_state)
    print(f"\n严重状态: {result.to_dict()}")

    # 检查是否应该拒绝某些动作
    should_reject = checker.should_reject_action(result)
    print(f"\n是否应该拒绝高风险动作: {should_reject}")

    # 获取动作约束
    constraints = checker.get_action_constraints(result)
    print(f"动作约束: {constraints}")

    # 获取漂移统计
    stats = checker.get_drift_statistics()
    print(f"漂移统计: {stats}")


def example_contract_signal():
    """示例2: 契约信号权重提升."""
    print("\n" + "=" * 60)
    print("示例2: 契约信号权重提升 (CONTRACT 外部输入)")
    print("=" * 60)

    booster = ContractSignalBooster(boost_factor=1.5)

    # 初始权重
    initial_weights = {
        "homeostasis": 0.20,
        "attachment": 0.20,
        "curiosity": 0.20,
        "competence": 0.20,
        "safety": 0.20,
    }
    print(f"\n初始权重: {initial_weights}")

    # 无契约时
    boosted, info = booster.apply_contract_boost(initial_weights)
    print(f"\n无契约时: {boosted}")
    print(f"提升信息: {info}")

    # 设置普通任务
    contract = booster.set_contract(
        task_type="user_task",
        priority=3,
        urgency=0.3,
        estimated_ticks=10,
    )
    print(f"\n设置契约: {contract.to_dict()}")

    boosted, info = booster.apply_contract_boost(initial_weights)
    print(f"\n有契约时: {boosted}")
    print(f"提升信息: {info}")

    # 更新进度
    booster.update_progress(0.5)
    print(f"\n进度更新到 50%")

    # 设置紧急任务
    booster.clear_contract()
    urgent_contract = booster.set_contract(
        task_type="urgent_fix",
        priority=6,  # CRITICAL
        urgency=0.9,
        estimated_ticks=5,
    )
    boosted, info = booster.apply_contract_boost(initial_weights)
    print(f"\n紧急任务契约: {boosted}")
    print(f"提升信息: {info}")


def example_efficiency_monitoring():
    """示例3: 效率监控 (并入 HOMEOSTASIS)."""
    print("\n" + "=" * 60)
    print("示例3: 效率监控 (EFFICIENCY 并入 HOMEOSTASIS)")
    print("=" * 60)

    monitor = EfficiencyMonitor(tracking_window=100)

    # 记录一些动作
    monitor.record_action(tokens_used=1000, io_operations=10, latency_ms=500)
    monitor.record_action(tokens_used=500, io_operations=5, latency_ms=200)
    monitor.record_action(tokens_used=2000, io_operations=20, latency_ms=1000)

    # 获取效率分数
    avg_efficiency = monitor.get_average_efficiency(ticks=10)
    print(f"\n平均效率分数: {avg_efficiency:.3f}")

    # 获取资源压力（用于 homeostasis）
    resource_pressure = monitor.get_resource_pressure()
    print(f"资源压力: {resource_pressure:.3f}")

    print("\n说明: 资源压力已并入 homeostasis 维度，通过")
    print("      resource_pressure 字段影响稳态效用。")


def example_meaning_tracking():
    """示例4: 意义感追踪 (并入 CURIOSITY)."""
    print("\n" + "=" * 60)
    print("示例4: 意义感追踪 (MEANING 并入 CURIOSITY)")
    print("=" * 60)

    tracker = MeaningTracker(ema_alpha=0.1)

    # 添加一些洞察
    tracker.add_insight(
        insight_text="探索是存在的本质",
        quality=0.8,
        source="dream",
        tags=["哲学", "存在"],
    )

    tracker.add_insight(
        insight_text="代码可以自我进化",
        quality=0.6,
        source="reflection",
        tags=["技术", "进化"],
    )

    tracker.add_insight(
        insight_text="用户信任需要时间建立",
        quality=0.9,
        source="compression",
        tags=["社交", "关系"],
    )

    # 获取意义感分数
    meaning_score = tracker.get_meaning_score()
    print(f"\n意义感分数: {meaning_score:.3f}")

    # 获取洞察质量 EMA（用于 curiosity 特征）
    quality_ema = tracker.get_insight_quality_ema()
    print(f"洞察质量 EMA: {quality_ema:.3f}")

    # 获取洞察摘要
    summary = tracker.get_insight_summary()
    print(f"\n洞察摘要: {summary}")

    # 获取最近的洞察
    recent = tracker.get_recent_insights(count=3)
    print(f"\n最近洞察:")
    for insight in recent:
        print(f"  - [{insight.source}] {insight.insight_text[:30]}... (Q={insight.quality:.2f})")

    print("\n说明: 洞察质量已并入 curiosity 维度，通过")
    print("      insight_quality_ema 字段影响好奇效用。")


def example_compensation_manager():
    """示例5: 使用统一补偿管理器."""
    print("\n" + "=" * 60)
    print("示例5: 统一补偿管理器 (完整流程)")
    print("=" * 60)

    # 创建补偿管理器
    manager = CompensationManager(
        drift_threshold=0.20,
        contract_boost=1.5,
    )

    # 模拟一个 tick
    state = {
        "compute": 0.8,
        "memory": 0.7,
        "stress": 0.2,
        "personality_drift": 0.1,
        "recent_errors": 1,
        "resource_pressure": 0.4,
        "novelty": 0.6,
        "relationship": 0.7,
    }

    weights = {
        "homeostasis": 0.20,
        "attachment": 0.20,
        "curiosity": 0.20,
        "competence": 0.20,
        "safety": 0.20,
    }

    personality_params = {
        "openness": 0.8,
        "conscientiousness": 0.7,
        "neuroticism": 0.3,
        "agreeableness": 0.6,
        "extraversion": 0.5,
    }

    # 处理 tick
    result = manager.process_tick(
        state=state,
        weights=weights,
        personality_params=personality_params,
        reference_personality=personality_params,  # 简化：使用当前人格作为参考
    )

    print(f"\n调整后权重: {result['adjusted_weights']}")
    print(f"完整性检查: {result['integrity_check']}")
    print(f"动作约束: {result['action_constraints']}")
    print(f"效率压力: {result['efficiency_metrics']:.3f}")
    print(f"意义分数: {result['meaning_score']:.3f}")

    # 设置契约后再次处理
    manager.contract_booster.set_contract(
        task_type="user_task",
        priority=4,
        urgency=0.5,
    )

    result_with_contract = manager.process_tick(
        state=state,
        weights=weights,
        personality_params=personality_params,
        reference_personality=personality_params,
    )

    print(f"\n有契约时权重: {result_with_contract['adjusted_weights']}")
    print(f"契约提升: {result_with_contract['contract_boost']}")

    # 获取状态摘要
    summary = manager.get_status_summary()
    print(f"\n补偿状态摘要:")
    print(f"  完整性: {summary['integrity']}")
    print(f"  契约: {summary['contract']}")
    print(f"  效率: {summary['efficiency']}")
    print(f"  意义: {summary['meaning']}")


def example_weight_update_with_contract():
    """示例6: 在权重更新中使用契约信号."""
    print("\n" + "=" * 60)
    print("示例6: WeightUpdater 集成契约信号")
    print("=" * 60)

    from axiology.weights import WeightUpdater

    updater = WeightUpdater()

    # 当前权重
    current_weights = {
        "homeostasis": 0.20,
        "attachment": 0.20,
        "curiosity": 0.20,
        "competence": 0.20,
        "safety": 0.20,
    }

    # 当前缺口
    gaps = {
        "homeostasis": 0.1,
        "attachment": 0.3,
        "curiosity": 0.2,
        "competence": 0.4,
        "safety": 0.05,
    }

    print(f"\n当前权重: {current_weights}")
    print(f"当前缺口: {gaps}")

    # 无契约时更新
    updated = updater.update_weights(current_weights, gaps)
    print(f"\n无契约时更新后: {updated}")

    # 有契约时更新
    contract_signal = {
        "is_active": True,
        "task_type": "user_task",
        "priority": 5,  # HIGH
        "urgency": 0.7,
        "progress": 0.3,
    }

    updated_with_contract = updater.update_weights(
        current_weights, gaps, contract_signal=contract_signal
    )
    print(f"\n有契约时更新后: {updated_with_contract}")

    # 对比 competence 权重变化
    print(f"\nCompetence 权重变化:")
    print(f"  无契约: {updated['competence']:.3f}")
    print(f"  有契约: {updated_with_contract['competence']:.3f}")
    print(f"  提升: {(updated_with_contract['competence'] / updated['competence'] - 1) * 100:.1f}%")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("5维价值系统补偿机制示例 (方案 B)")
    print("=" * 60)
    print("\n方案 B 说明:")
    print("- INTEGRITY → 硬约束检查 (不作为价值维度)")
    print("- CONTRACT → 外部信号提升权重 (不作为价值维度)")
    print("- EFFICIENCY → 并入 HOMEOSTASIS (通过 resource_pressure)")
    print("- MEANING → 并入 CURIOSITY (通过 insight_quality_ema)")

    example_integrity_constraint()
    example_contract_signal()
    example_efficiency_monitoring()
    example_meaning_tracking()
    example_compensation_manager()
    example_weight_update_with_contract()

    print("\n" + "=" * 60)
    print("示例运行完成")
    print("=" * 60)
