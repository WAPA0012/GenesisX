# -*- coding: utf-8 -*-
"""测试工具解析器"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.tool_system_v2 import SmartToolParser

# 测试用例
test_cases = [
    "C:\\Users\\Administrator\\Desktop\\论文.txt，能帮我看一下这个论文吗",
    "读取 /home/user/file.py",
    "分析 C:\\path\\to\\code.py",
    "帮我看看 main.py",
    "C:\\data\\file.txt 能否分析",
]

print("工具解析器测试\n" + "="*60)

for test in test_cases:
    print(f"\n输入: {test}")
    calls = SmartToolParser.parse_tool_calls(test)

    if calls:
        for call in calls:
            print(f"  → 工具: {call.tool_name}")
            print(f"     描述: {call.description}")
            print(f"     参数: {call.parameters}")
    else:
        print("  → 未检测到工具调用")

print("\n" + "="*60)
