"""Plugin Templates - 插件模板目录

这个目录用于存放自定义插件。

插件目录结构：
    templates/
    └── my_plugin/
        ├── __init__.py      # 插件代码
        └── metadata.json    # 插件元数据

metadata.json 格式：
{
    "name": "my_plugin",
    "description": "插件描述",
    "plugin_type": "internal",  # internal, external, hybrid
    "capabilities": ["cap1", "cap2"],
    "dependencies": ["requests"],
    "version": "1.0",
    "author": "作者名"
}

使用方式：
    manager = PluginManager()
    manager.load_plugin("my_plugin")
    plugin = manager.get_plugin("my_plugin")
    result = plugin.execute("method_name", **params)
"""

# 内置插件在 plugin_manager.py 中定义
# 这个目录用于存放用户自定义插件
