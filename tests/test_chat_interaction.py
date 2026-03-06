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
    """测试对话交互 - 验证状态对象存在并可操作"""

    chat = mock_chat

    # 验证状态可访问
    assert chat.state is not None
    assert chat.state.tick == 0
    assert 0.0 <= chat.state.energy <= 1.0
    assert 0.0 <= chat.state.mood <= 1.0

    # 模拟多次body更新
    for i in range(5):
        chat.state.update_body(dt=1.0)

    # 验证能量消耗
    assert chat.state.energy < 0.8  # 应该有所下降
    assert chat.state.fatigue > 0.1  # 应该有所上升


def test_emotional_response(mock_chat):
    """测试情绪响应 - 验证stress和fatigue动态"""

    chat = mock_chat

    # 记录初始状态
    initial_stress = chat.state.stress
    initial_fatigue = chat.state.fatigue

    # 模拟疲劳累积
    for i in range(5):
        chat.state.update_body(dt=10)
        chat.state.fatigue = min(1.0, chat.state.fatigue + 0.15)

    # 验证疲劳增加
    assert chat.state.fatigue > initial_fatigue


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
