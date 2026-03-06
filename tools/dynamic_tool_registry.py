"""动态工具注册表 - 支持运行时发现和加载工具.

类似 OpenClaw 的 ClawHub 和 Claude 的 Tool Search，
允许动态注册、发现和管理工具。
"""

import os
import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from common.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ToolDefinition:
    """工具定义."""
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable
    category: str = "general"
    risk_level: float = 0.0
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class DynamicToolRegistry:
    """动态工具注册表.

    特性：
    - 运行时注册和注销工具
    - 从目录自动发现工具
    - 工具分类和搜索
    - 风险评估
    - 热重载
    """

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._categories: Dict[str, List[str]] = {}
        self._hooks = {
            "before_execute": [],
            "after_execute": [],
            "on_error": []
        }

    def register(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable,
        category: str = "general",
        risk_level: float = 0.0,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """注册一个新工具.

        Args:
            name: 工具名称（唯一标识符）
            description: 工具描述（给 LLM 看）
            parameters: 参数 schema (OpenAI Function Calling 格式)
            handler: 执行函数
            category: 分类标签
            risk_level: 风险等级 (0-1)
            metadata: 额外元数据

        Returns:
            是否注册成功
        """
        if name in self._tools:
            logger.warning(f"工具 {name} 已存在，将被覆盖")

        tool = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler,
            category=category,
            risk_level=risk_level,
            enabled=True,
            metadata=metadata or {}
        )

        self._tools[name] = tool

        # 更新分类索引
        if category not in self._categories:
            self._categories[category] = []
        if name not in self._categories[category]:
            self._categories[category].append(name)

        logger.info(f"已注册工具: {name} (分类: {category}, 风险: {risk_level})")
        return True

    def unregister(self, name: str) -> bool:
        """注销工具."""
        if name not in self._tools:
            return False

        tool = self._tools[name]
        category = tool.category

        del self._tools[name]

        # 从分类中移除
        if category in self._categories and name in self._categories[category]:
            self._categories[category].remove(name)

        logger.info(f"已注销工具: {name}")
        return True

    def get(self, name: str) -> Optional[ToolDefinition]:
        """获取工具定义."""
        return self._tools.get(name)

    def list_tools(
        self,
        category: Optional[str] = None,
        enabled_only: bool = True,
        max_risk: Optional[float] = None
    ) -> List[ToolDefinition]:
        """列出工具.

        Args:
            category: 过滤分类
            enabled_only: 只显示已启用的工具
            max_risk: 最大风险等级

        Returns:
            工具列表
        """
        tools = list(self._tools.values())

        if category:
            tools = [t for t in tools if t.category == category]

        if enabled_only:
            tools = [t for t in tools if t.enabled]

        if max_risk is not None:
            tools = [t for t in tools if t.risk_level <= max_risk]

        return tools

    def search(self, query: str) -> List[ToolDefinition]:
        """搜索工具（按名称和描述）."""
        query = query.lower()
        return [
            t for t in self._tools.values()
            if t.enabled and (query in t.name.lower() or query in t.description.lower())
        ]

    def execute(self, name: str, parameters: Dict[str, Any]) -> Any:
        """执行工具.

        Args:
            name: 工具名称
            parameters: 参数

        Returns:
            执行结果
        """
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"工具不存在: {name}")

        if not tool.enabled:
            raise ValueError(f"工具已禁用: {name}")

        # 执行前置钩子
        for hook in self._hooks["before_execute"]:
            hook(tool, parameters)

        try:
            result = tool.handler(**parameters)

            # 执行后置钩子
            for hook in self._hooks["after_execute"]:
                hook(tool, parameters, result)

            return result

        except Exception as e:
            # 执行错误钩子
            for hook in self._hooks["on_error"]:
                hook(tool, parameters, e)
            raise

    def to_llm_format(self) -> List[Dict[str, Any]]:
        """转换为 LLM Function Calling 格式.

        Returns:
            OpenAI 兼容的工具定义列表
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters
                }
            }
            for t in self._tools.values()
            if t.enabled
        ]

    def add_hook(self, event: str, callback: Callable):
        """添加事件钩子.

        支持的事件:
        - before_execute: 工具执行前
        - after_execute: 工具执行后
        - on_error: 工具执行出错
        """
        if event in self._hooks:
            self._hooks[event].append(callback)

    def discover_from_directory(self, directory: Path):
        """从目录自动发现并注册工具.

        扫描目录中的 Python 文件，查找带有 @tool 装饰器的函数。

        Args:
            directory: 要扫描的目录
        """
        if not directory.exists():
            logger.warning(f"工具目录不存在: {directory}")
            return

        for py_file in directory.rglob("*.py"):
            if py_file.name.startswith("_"):
                continue

            try:
                self._load_tools_from_file(py_file)
            except Exception as e:
                logger.warning(f"加载工具文件失败 {py_file}: {e}")

    def _load_tools_from_file(self, file_path: Path):
        """从 Python 文件加载工具."""
        # 动态导入模块
        module_path = str(file_path.parent)
        module_name = file_path.stem

        import sys
        if module_path not in sys.path:
            sys.path.insert(0, module_path)

        try:
            module = importlib.import_module(module_name)

            # 查找带有 _tool_def 属性的函数
            for name, obj in inspect.getmembers(module, inspect.is_function):
                if hasattr(obj, "_tool_def"):
                    tool_def = obj._tool_def
                    self.register(
                        name=tool_def.get("name", name),
                        description=tool_def.get("description", ""),
                        parameters=tool_def.get("parameters", {}),
                        handler=obj,
                        category=tool_def.get("category", "general"),
                        risk_level=tool_def.get("risk_level", 0.0),
                        metadata=tool_def.get("metadata", {})
                    )

        finally:
            # 清理 sys.path
            if module_path in sys.path:
                sys.path.remove(module_path)

    def enable(self, name: str) -> bool:
        """启用工具."""
        if name in self._tools:
            self._tools[name].enabled = True
            return True
        return False

    def disable(self, name: str) -> bool:
        """禁用工具."""
        if name in self._tools:
            self._tools[name].enabled = False
            return True
        return False

    @property
    def categories(self) -> List[str]:
        """获取所有分类."""
        return list(self._categories.keys())

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息."""
        return {
            "total_tools": len(self._tools),
            "enabled_tools": sum(1 for t in self._tools.values() if t.enabled),
            "categories": len(self._categories),
            "tools_by_category": {
                cat: len(tools) for cat, tools in self._categories.items()
            }
        }


def tool(name: str = None, description: str = "", parameters: Dict = None,
         category: str = "general", risk_level: float = 0.0, **metadata):
    """工具装饰器 - 用于标记和注册工具.

    使用示例:
    ```python
    @tool(
        name="search_files",
        description="在指定目录中搜索文件",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "pattern": {"type": "string"}
            },
            "required": ["path"]
        },
        category="file_system",
        risk_level=0.1
    )
    def search_files(path: str, pattern: str = "*"):
        ...
    ```
    """
    def decorator(func):
        func._tool_def = {
            "name": name or func.__name__,
            "description": description,
            "parameters": parameters or {},
            "category": category,
            "risk_level": risk_level,
            "metadata": metadata
        }
        return func

    return decorator


# ==================== 技能系统集成 ====================

def register_skills(registry: 'DynamicToolRegistry', skill_registry=None):
    """将技能注册到工具注册表

    Args:
        registry: DynamicToolRegistry 实例
        skill_registry: SkillRegistry 实例（如果为 None 则使用全局注册表）
    """
    from memory.skills import SkillRegistry as SR
    from memory.skills.base import SkillCost

    if skill_registry is None:
        from memory.skills.skill_registry import get_global_registry
        skill_registry = get_global_registry()

    # 初始化技能（如果还没有初始化）
    if not skill_registry.get_names():
        _initialize_default_skills(skill_registry)

    # 为每个技能创建工具包装器
    for skill in skill_registry.list_all():
        _wrap_skill_as_tool(registry, skill, skill_registry)

    logger.info(f"已注册 {len(skill_registry.list_all())} 个技能到工具注册表")


def _initialize_default_skills(skill_registry):
    """初始化默认技能"""
    from memory.skills.pdf_skill import PDFSkill
    from memory.skills.web_skill import WebSkill
    from memory.skills.file_skill import FileSkill
    from memory.skills.analysis_skill import AnalysisSkill

    skill_registry.register(PDFSkill())
    skill_registry.register(WebSkill())
    skill_registry.register(FileSkill())
    skill_registry.register(AnalysisSkill())


def _wrap_skill_as_tool(tool_registry, skill, skill_registry):
    """将技能包装为工具

    Args:
        tool_registry: DynamicToolRegistry 实例
        skill: BaseSkill 实例
        skill_registry: SkillRegistry 实例
    """
    def skill_wrapper(**kwargs):
        # 调用技能
        result = skill_registry.execute(skill.name, **kwargs)

        # 返回格式适配 LLM
        if result.success:
            return {
                "success": True,
                "message": result.message,
                "data": result.data
            }
        else:
            return {
                "success": False,
                "error": result.error or result.message
            }

    # 注册为工具
    tool_registry.register(
        name=skill.name,
        description=skill.description,
        parameters=skill.get_parameters_schema(),
        handler=skill_wrapper,
        category="skill",
        risk_level=0.1,  # 技能风险较低
        metadata={"type": "skill", "skill_name": skill.name}
    )


# 全局工具注册表实例
_global_registry: Optional[DynamicToolRegistry] = None


def get_global_registry() -> DynamicToolRegistry:
    """获取全局工具注册表."""
    global _global_registry
    if _global_registry is None:
        _global_registry = DynamicToolRegistry()
        # 注册默认工具
        _register_default_tools(_global_registry)
    return _global_registry


def _register_default_tools(registry: DynamicToolRegistry):
    """注册默认工具集."""
    from tools.tool_executor import LLMToolExecutor

    # 创建工具执行器实例
    executor = LLMToolExecutor(safe_mode=False)

    # 文件系统工具
    registry.register(
        name="list_directory",
        description="列出指定目录下的所有文件和子目录。支持别名如 ~/Desktop",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "目录路径，支持相对路径和别名（~/Desktop, ~/Documents）"
                }
            },
            "required": ["path"]
        },
        handler=executor._list_directory,
        category="file_system",
        risk_level=0.1
    )

    registry.register(
        name="read_file",
        description="读取文件内容。支持文本文件、代码文件等",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径"
                }
            },
            "required": ["path"]
        },
        handler=executor._read_file,
        category="file_system",
        risk_level=0.1
    )

    registry.register(
        name="write_file",
        description="写入文件内容。如果文件不存在会创建，存在则覆盖",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
                "content": {"type": "string", "description": "文件内容"}
            },
            "required": ["path", "content"]
        },
        handler=executor._write_file,
        category="file_system",
        risk_level=0.5  # 写操作风险较高
    )

    registry.register(
        name="web_search",
        description="网络搜索，获取最新信息",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索查询"}
            },
            "required": ["query"]
        },
        handler=executor._web_search,
        category="network",
        risk_level=0.2
    )

    registry.register(
        name="execute_code",
        description="执行 Python 代码。可用于数据处理、计算等",
        parameters={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python 代码"}
            },
            "required": ["code"]
        },
        handler=executor._execute_code,
        category="code",
        risk_level=0.8  # 代码执行风险高
    )

    logger.info(f"已注册 {len(registry._tools)} 个默认工具")
