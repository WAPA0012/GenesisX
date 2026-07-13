"""
Genesis X 交互式对话测试脚本

模拟用户与数字生命的对话，展示系统的动态响应
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from chat_interactive import GenesisXChat


@pytest.fixture
def mock_chat():
    """创建mock的GenesisXChat实例，跳过初始化副作用"""
    with patch.object(GenesisXChat, '__init__', lambda self, *a, **kw: None):
        chat = GenesisXChat.__new__(GenesisXChat)
        # 手动初始化必要的属性
        from core.state import GlobalState
        chat.state = GlobalState()
        chat.display = MagicMock()
        chat.life_loop = MagicMock()
        chat.life_loop.state = chat.state
        chat.messages = []
        chat.tool_executor = MagicMock()
        chat._running = True
        chat._last_interaction = 0
        chat._autonomous_interval = 120
        chat._autonomous_enabled = False
        yield chat


def test_conversation(mock_chat):
    """测试 GlobalState.update_body 的物理参数动态（被动 tick）。

    P8-4 后 energy/fatigue 独立：update_body 累积 fatigue（活动疲劳）和 boredom，
    衰减 stress，但不动 energy（energy 只在 EXPLORE/LEARN 动作时消耗，
    SLEEP/昼夜节律恢复）。这是设计意图：数字生命永远有动力做事（价值缺口驱动），
    update_body 不应被动扣减 energy。
    """

    chat = mock_chat

    # 验证状态可访问
    assert chat.state is not None
    assert chat.state.tick == 0
    assert 0.0 <= chat.state.energy <= 1.0
    assert 0.0 <= chat.state.mood <= 1.0

    initial_energy = chat.state.energy
    initial_fatigue = chat.state.fatigue

    # 模拟多次body更新（被动 tick，无认知重活）
    for i in range(5):
        chat.state.update_body(dt=1.0)

    # energy 不受 update_body 影响（无被动衰减——设计意图）
    assert chat.state.energy == initial_energy
    # fatigue 随活动累积（activity_fatigue 同步到 fatigue）
    assert chat.state.fatigue > initial_fatigue
    # boredom 随时间增加
    assert chat.state.boredom > 0.0
    # stress 自然衰减
    assert chat.state.stress <= 0.15  # 初始 0.15，5 tick 后衰减


def test_goal_switching(mock_chat):
    """测试目标切换"""

    chat = mock_chat

    initial_goal = chat.state.current_goal

    # 模拟疲劳累积
    for i in range(5):
        chat.state.update_body(dt=10)
        chat.state.fatigue = min(1.0, chat.state.fatigue + 0.15)

    # 触发目标重新编译
    from common.models import ValueDimension
    from cognition.goal_compiler import GoalCompiler

    gaps = chat.state.gaps
    gaps[ValueDimension.HOMEOSTASIS] = 0.5  # 创建大的homeostasis缺口

    # 使用goal_compiler编译新目标
    goal_compiler = GoalCompiler()
    new_goal = goal_compiler.compile(gaps, chat.state.weights, chat.state.to_dict())

    # 验证目标已编译
    assert new_goal is not None
    assert new_goal.goal_type is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
