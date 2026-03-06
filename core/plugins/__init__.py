"""Plugins System - 插件系统

预制能力插件，与自主成长系统互补：

| 系统 | 作用 | 类比 |
|------|------|------|
| 成长系统 | LLM 动态生成新能力 | 长出牛角 |
| 插件系统 | 加载预制能力模块 | 戴上带牛角的头盔 |
| 技能记忆 | 记录如何使用能力 | 学会怎么用牛角 |

插件 vs 成长 vs 技能：
- 插件 = 预制模块（现成的 PDF 处理库）
- 成长 = 自主生成（LLM 写一个图像处理脚本）
- 技能 = 使用知识（知道怎么调用某个函数）

使用方式：
    from core.plugins import PluginManager

    manager = PluginManager()
    manager.load_plugin("http_api")
    plugin = manager.get_plugin("http_api")
    result = plugin.execute(**params)
"""

from .plugin_manager import (
    PluginManager,
    Plugin,
    PluginInfo,
    create_plugin_manager,
)

__all__ = [
    "PluginManager",
    "Plugin",
    "PluginInfo",
    "create_plugin_manager",
]
