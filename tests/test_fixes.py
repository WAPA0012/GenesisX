"""测试核心修复: 有效 Boredom, 中间变量

验证论文 v14 定义的核心公式实现。

注：test_resource_pressure 已删除（resource_pressure.py 模块在 P4-61 修复中移除，
其 RP 公式与 state.py 生产版语义相反且零运行时引用）。
"""


def test_intermediate_variables():
    """测试大五人格中间变量.

    论文 Section 3.4.1:
    ET_t = 0.4*O + 0.3*E + 0.3*(1-C)
    CT_t = 0.5*C + 0.3*N + 0.2*A
    ES_t = 0.6*N + 0.2*O + 0.2*(1-C)
    """
    print("\n" + "=" * 60)
    print("测试大五人格中间变量 (ET_t, CT_t, ES_t)")
    print("=" * 60)

    from axiology.personality import (
        BigFiveTraits,
        compute_intermediate_variables,
    )

    # 测试用例
    test_cases = [
        # (O, C, E, A, N, expected_ET, expected_CT, expected_ES, desc)
        (0.8, 0.4, 0.7, 0.6, 0.3, 0.71, 0.41, 0.46, "High exploration"),
        (0.3, 0.8, 0.4, 0.7, 0.5, 0.38, 0.73, 0.52, "High conservation"),
        (0.5, 0.5, 0.5, 0.5, 0.5, 0.50, 0.50, 0.50, "Balanced"),
    ]

    all_passed = True
    for O, C, E, A, N, exp_et, exp_ct, exp_es, desc in test_cases:
        traits = BigFiveTraits(
            openness=O,
            conscientiousness=C,
            extraversion=E,
            agreeableness=A,
            neuroticism=N
        )
        intermediate = compute_intermediate_variables(traits)

        et = intermediate.exploration_tendency
        ct = intermediate.conservation_tendency
        es = intermediate.emotional_sensitivity

        # 验证 ET_t
        if abs(et - exp_et) > 0.01:
            print(f"  ❌ {desc}: ET_t expected {exp_et:.2f}, got {et:.2f}")
            all_passed = False
        else:
            print(f"  ✅ {desc}: ET_t = {et:.2f}")

        # 验证 CT_t
        if abs(ct - exp_ct) > 0.01:
            print(f"    ❌ CT_t expected {exp_ct:.2f}, got {ct:.2f}")
            all_passed = False
        else:
            print(f"    ✅ CT_t = {ct:.2f}")

        # 验证 ES_t
        if abs(es - exp_es) > 0.01:
            print(f"    ❌ ES_t expected {exp_es:.2f}, got {es:.2f}")
            all_passed = False
        else:
            print(f"    ✅ ES_t = {es:.2f}")

        # 验证范围 [0, 1]
        if not (0 <= et <= 1 and 0 <= ct <= 1 and 0 <= es <= 1):
            print(f"    ❌ Intermediate variables must be in [0,1]")
            all_passed = False

    if all_passed:
        print("\n✅ 中间变量测试全部通过!")
    else:
        print("\n❌ 中间变量测试有失败")
    return all_passed


def test_global_state():
    """测试 GlobalState 的新功能.

    - resource_pressure 字段
    - get_effective_boredom() 方法
    - is_emergency_state() 方法
    - update_body() 自动更新 RP_t
    """
    print("\n" + "=" * 60)
    print("测试 GlobalState 新功能")
    print("=" * 60)

    from core.state import GlobalState

    state = GlobalState()

    # 初始状态
    print(f"  Initial: compute={state.compute:.2f}, memory={state.memory:.2f}")
    print(f"  RP_t = {state.resource_pressure:.3f}")
    print(f"  Effective boredom = {state.get_effective_boredom():.2f}")
    print(f"  Emergency = {state.is_emergency_state()}")

    # 验证初始 RP_t 计算
    # RP_t = max(0, 1 - (0.6*0.8 + 0.4*0.85)) = max(0, 1 - 0.82) = 0.18
    expected_rp = max(0, 1 - (0.6 * 0.8 + 0.4 * 0.85))
    if abs(state.resource_pressure - expected_rp) > 0.01:
        print(f"  ❌ Initial RP_t expected {expected_rp:.2f}, got {state.resource_pressure:.2f}")
        return False

    # 验证有效无聊度
    if state.get_effective_boredom() != state.boredom:
        print(f"  ❌ Effective boredom should equal boredom when not emergency")
        return False

    # 模拟资源下降
    state.compute = 0.2
    state.memory = 0.3
    state.update_body(1.0)

    print(f"\n  After resource drop:")
    print(f"  compute={state.compute:.2f}, memory={state.memory:.2f}")
    print(f"  RP_t = {state.resource_pressure:.3f}")
    print(f"  Effective boredom = {state.get_effective_boredom():.2f}")
    print(f"  Emergency = {state.is_emergency_state()}")

    # 验证紧急状态
    if not state.is_emergency_state():
        print(f"  ❌ Should be emergency with low resources")
        return False

    if state.get_effective_boredom() != 0.0:
        print(f"  ❌ Effective boredom should be 0 in emergency")
        return False

    print("\n✅ GlobalState 测试通过!")
    return True


def test_boredom_integration():
    """测试 boredom 模块的 η-coefficient 更新（P4-61 修复后）.

    resource_pressure.py 已删除，资源紧急判断由 state.py 负责。
    此测试只验证 boredom 的 η-coefficient 公式本身。
    """
    print("\n" + "=" * 60)
    print("测试 Boredom η-coefficient 更新")
    print("=" * 60)

    from metabolism.boredom import update_boredom, compute_effective_boredom

    # 低新颖度时无聊应增长（η_idle 项）
    boredom = 0.5
    new_boredom = update_boredom(boredom, dt=1.0, novelty=0.1, socially_engaged=False)
    print(f"  Low novelty: boredom {boredom:.2f} -> {new_boredom:.2f}")
    if new_boredom <= boredom:
        print(f"  ❌ Boredom should increase with low novelty")
        return False

    # 高新颖度时无聊应减少（η_nov 项）
    boredom = 0.5
    new_boredom = update_boredom(boredom, dt=1.0, novelty=0.9, socially_engaged=False)
    print(f"  High novelty: boredom {boredom:.2f} -> {new_boredom:.2f}")
    if new_boredom >= boredom:
        print(f"  ❌ Boredom should decrease with high novelty")
        return False

    # 社交参与时无聊应减少（η_soc 项）
    boredom = 0.5
    new_boredom = update_boredom(boredom, dt=1.0, novelty=0.1, socially_engaged=True)
    print(f"  Social: boredom {boredom:.2f} -> {new_boredom:.2f}")

    # compute_effective_boredom 现在是向后兼容存根，直接返回 clip 后的 boredom
    eff_boredom = compute_effective_boredom(0.7)
    if eff_boredom != 0.7:
        print(f"  ❌ Effective boredom should be 0.7, got {eff_boredom}")
        return False

    print("\n✅ Boredom 集成测试通过!")
    return True


if __name__ == "__main__":
    results = []

    results.append(("RP_t 资源压力指数", test_resource_pressure()))
    results.append(("中间变量 (ET_t, CT_t, ES_t)", test_intermediate_variables()))
    results.append(("GlobalState 新功能", test_global_state()))
    results.append(("Boredom 集成", test_boredom_integration()))

    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {status}: {name}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 所有测试通过! 代码与论文 v14 定义一致。")
    else:
        print("\n⚠️ 部分测试失败，需要修复。")
