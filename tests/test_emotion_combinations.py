"""
测试各种情绪状态组合，检查是否存在死锁或异常行为。

测试场景：
1. 高压 + 低能量 - 能否恢复？
2. 低能量 + 高疲劳 - 休息逻辑
3. 低情绪 + 探索动作 - 是否被阻止？
4. 高压 + 高无聊 - 之前的死锁场景
5. 所有临界值同时触发 - 极端情况
"""

import sys
import io
from pathlib import Path

# 设置 stdout 为 UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent.parent))

from safety.integrity_check import check_integrity
from common.models import Action, ActionType


def create_state(stress=0.5, energy=0.5, mood=0.5, fatigue=0.3, boredom=0.3):
    """创建测试状态"""
    return {
        "stress": stress,
        "energy": energy,
        "mood": mood,
        "fatigue": fatigue,
        "boredom": boredom
    }


def test_integrity(action_type, state, expected_ok=True, expected_reason=None):
    """测试完整性检查"""
    action = Action(type=action_type, params={})
    result = check_integrity(action, state)

    ok = result.get("ok", False)
    reason = result.get("reason", "")

    status = "[OK]" if ok == expected_ok else "[FAIL]"
    print(f"  {status} {action_type.name}: ok={ok}, reason={reason or 'None'}")

    if expected_reason and expected_reason not in reason:
        print(f"       WARN: Expected reason containing: '{expected_reason}'")
        return False

    return ok == expected_ok


def run_tests():
    """运行所有测试"""
    all_passed = True

    # ========== 测试 1: 高压 + 低能量 ==========
    print("\n" + "="*60)
    print("测试 1: 高压(stress=0.95) + 低能量(energy=0.08)")
    print("="*60)
    state = create_state(stress=0.95, energy=0.08)

    # 高压+低能量时，能量检查优先，只允许 SLEEP
    all_passed &= test_integrity(ActionType.SLEEP, state, expected_ok=True)
    all_passed &= test_integrity(ActionType.CHAT, state, expected_ok=False, expected_reason="Energy")
    all_passed &= test_integrity(ActionType.REFLECT, state, expected_ok=False, expected_reason="Energy")

    # 高压时不应该允许消耗性动作（压力检查先触发）
    all_passed &= test_integrity(ActionType.EXPLORE, state, expected_ok=False, expected_reason="Stress")
    all_passed &= test_integrity(ActionType.LEARN_SKILL, state, expected_ok=False, expected_reason="Stress")

    # 低能量时应该只允许 SLEEP
    print("\n  低能量临界测试 (energy=0.05):")
    state_low_e = create_state(stress=0.3, energy=0.05)
    # 低能量时只允许 SLEEP
    all_passed &= test_integrity(ActionType.SLEEP, state_low_e, expected_ok=True)
    all_passed &= test_integrity(ActionType.CHAT, state_low_e, expected_ok=False, expected_reason="Energy")

    # ========== 测试 2: 低能量 + 高疲劳 ==========
    print("\n" + "="*60)
    print("测试 2: 低能量(energy=0.15) + 高疲劳(fatigue=0.8)")
    print("="*60)
    state = create_state(energy=0.15, fatigue=0.8)

    all_passed &= test_integrity(ActionType.SLEEP, state, expected_ok=True)
    all_passed &= test_integrity(ActionType.CHAT, state, expected_ok=True)
    all_passed &= test_integrity(ActionType.REFLECT, state, expected_ok=True)

    # ========== 测试 3: 低情绪 + 探索动作 ==========
    print("\n" + "="*60)
    print("测试 3: 低情绪(mood=0.05) + 探索/学习动作")
    print("="*60)
    state = create_state(mood=0.05)

    # 低情绪时应该阻止探索和学习
    all_passed &= test_integrity(ActionType.EXPLORE, state, expected_ok=False, expected_reason="Mood")
    all_passed &= test_integrity(ActionType.LEARN_SKILL, state, expected_ok=False, expected_reason="Mood")

    # 低情绪时应该允许其他动作
    all_passed &= test_integrity(ActionType.CHAT, state, expected_ok=True)
    all_passed &= test_integrity(ActionType.SLEEP, state, expected_ok=True)
    all_passed &= test_integrity(ActionType.REFLECT, state, expected_ok=True)

    # ========== 测试 4: 高压 + 高无聊 (之前的死锁场景) ==========
    print("\n" + "="*60)
    print("测试 4: 高压(stress=0.95) + 高无聊(boredom=0.9)")
    print("="*60)
    state = create_state(stress=0.95, boredom=0.9)

    # 关键：CHAT 应该被允许（解决死锁）
    all_passed &= test_integrity(ActionType.CHAT, state, expected_ok=True)
    all_passed &= test_integrity(ActionType.SLEEP, state, expected_ok=True)
    all_passed &= test_integrity(ActionType.REFLECT, state, expected_ok=True)

    # 探索应该被阻止
    all_passed &= test_integrity(ActionType.EXPLORE, state, expected_ok=False, expected_reason="Stress")

    # ========== 测试 5: 极端情况 - 所有临界值 ==========
    print("\n" + "="*60)
    print("测试 5: 极端情况 - 所有临界值同时触发")
    print("stress=0.95, energy=0.05, mood=0.05, fatigue=0.9, boredom=0.95")
    print("="*60)
    state = create_state(stress=0.95, energy=0.05, mood=0.05, fatigue=0.9, boredom=0.95)

    # 能量临界时，只允许 SLEEP
    all_passed &= test_integrity(ActionType.SLEEP, state, expected_ok=True)
    all_passed &= test_integrity(ActionType.CHAT, state, expected_ok=False, expected_reason="Energy")

    # ========== 测试 6: 正常状态 ==========
    print("\n" + "="*60)
    print("测试 6: 正常状态 - 所有动作应该被允许")
    print("="*60)
    state = create_state(stress=0.3, energy=0.6, mood=0.5, fatigue=0.2, boredom=0.3)

    for action_type in [ActionType.CHAT, ActionType.SLEEP, ActionType.REFLECT,
                         ActionType.EXPLORE, ActionType.LEARN_SKILL]:
        all_passed &= test_integrity(action_type, state, expected_ok=True)

    # ========== 测试 7: 边界值测试 ==========
    print("\n" + "="*60)
    print("测试 7: 边界值测试")
    print("="*60)

    # 压力刚好在阈值下 (0.89)
    print("\n  压力刚好在阈值下 (stress=0.89):")
    state = create_state(stress=0.89)
    all_passed &= test_integrity(ActionType.EXPLORE, state, expected_ok=True)

    # 压力刚好在阈值上 (0.91)
    print("\n  压力刚好在阈值上 (stress=0.91):")
    state = create_state(stress=0.91)
    all_passed &= test_integrity(ActionType.EXPLORE, state, expected_ok=False, expected_reason="Stress")
    all_passed &= test_integrity(ActionType.CHAT, state, expected_ok=True)

    # 能量刚好在阈值上 (0.11)
    print("\n  能量刚好在阈值上 (energy=0.11):")
    state = create_state(energy=0.11)
    all_passed &= test_integrity(ActionType.CHAT, state, expected_ok=True)

    # 能量刚好在阈值下 (0.09)
    print("\n  能量刚好在阈值下 (energy=0.09):")
    state = create_state(energy=0.09)
    all_passed &= test_integrity(ActionType.CHAT, state, expected_ok=False, expected_reason="Energy")

    # ========== 结果汇总 ==========
    print("\n" + "="*60)
    if all_passed:
        print("[PASS] All tests passed!")
    else:
        print("[FAIL] Some tests failed, please check results above")
    print("="*60)

    return all_passed


if __name__ == "__main__":
    run_tests()
