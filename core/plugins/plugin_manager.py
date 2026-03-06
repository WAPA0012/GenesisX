"""Plugin Manager - 插件管理器

负责管理和加载预制能力插件。

与自主成长系统的区别：
- 插件系统：加载现成的、预制的能力模块
- 成长系统：通过 LLM 动态生成新能力

新架构 (v2.0):
- 插件自动转换为器官系统的 Plugin
- 注册到 UnifiedOrganManager
- 统一的能力调用接口

使用场景：
1. 快速装备已知能力（如 HTTP API 调用、数据处理）
2. 作为 LLM 不可用时的 fallback
3. 提供经过验证的、稳定的实现
"""

import json
from typing import Dict, Any, List, Optional, Type, Callable
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timezone
from enum import Enum

from common.logger import get_logger

# 器官指南管理器
from memory.organ_guide_manager import get_organ_guide_manager

logger = get_logger(__name__)


class PluginType(Enum):
    """插件类型"""
    INTERNAL = "internal"      # 内部插件（纯 Python）
    EXTERNAL = "external"      # 外部插件（需要 API key 等）
    HYBRID = "hybrid"          # 混合插件


@dataclass
class PluginInfo:
    """插件信息"""
    name: str
    description: str
    plugin_type: PluginType
    capabilities: List[str]
    version: str = "1.0"
    author: str = "GenesisX"
    dependencies: List[str] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "plugin_type": self.plugin_type.value,
            "capabilities": self.capabilities,
            "version": self.version,
            "author": self.author,
            "dependencies": self.dependencies,
            "config_schema": self.config_schema,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class Plugin:
    """插件实例"""
    info: PluginInfo
    code: str
    config: Dict[str, Any] = field(default_factory=dict)
    _instance: Any = field(default=None, repr=False)

    def execute(self, method: str, **kwargs) -> Dict[str, Any]:
        """执行插件方法

        Args:
            method: 方法名
            **kwargs: 方法参数

        Returns:
            执行结果
        """
        if self._instance is None:
            self._instance = self._create_instance()

        if self._instance is None:
            return {"success": False, "error": "Failed to create plugin instance"}

        if not hasattr(self._instance, method):
            return {"success": False, "error": f"Method '{method}' not found"}

        try:
            func = getattr(self._instance, method)
            result = func(**kwargs)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _create_instance(self) -> Optional[Any]:
        """创建插件实例"""
        try:
            # 创建命名空间
            namespace = {}

            # 执行代码
            exec(self.code, namespace)

            # 查找主类
            class_name = self._get_main_class_name()
            if class_name and class_name in namespace:
                cls = namespace[class_name]
                return cls(**self.config)

            return None

        except Exception as e:
            logger.error(f"Failed to create plugin instance: {e}")
            return None

    def _get_main_class_name(self) -> Optional[str]:
        """获取主类名"""
        # 转换插件名到类名
        parts = self.info.name.replace('-', '_').split('_')
        return ''.join(word.capitalize() for word in parts)

    def get_capabilities(self) -> List[str]:
        """获取插件能力"""
        return self.info.capabilities


class PluginManager:
    """插件管理器

    负责：
    1. 加载和管理预制插件
    2. 提供插件查询接口
    3. 处理插件配置

    新架构 (v2.0):
    - 插件自动转换为器官系统的 Plugin
    - 注册到 UnifiedOrganManager

    使用方式：
        manager = PluginManager()
        manager.load_plugin("http_api")
        plugin = manager.get_plugin("http_api")
        result = plugin.execute("call_api", method="GET", endpoint="/users")
    """

    def __init__(
        self,
        plugins_dir: Path = None,
        config: Dict[str, Any] = None,
        unified_organ_manager=None,  # 新增：统一器官管理器
    ):
        """初始化插件管理器

        Args:
            plugins_dir: 插件目录
            config: 配置
            unified_organ_manager: 统一器官管理器（新版，可选）
        """
        self.config = config or {}
        self.unified_organ_manager = unified_organ_manager

        # 插件目录
        if plugins_dir is None:
            self.plugins_dir = Path(__file__).parent / "templates"
        else:
            self.plugins_dir = Path(plugins_dir)

        self.plugins_dir.mkdir(parents=True, exist_ok=True)

        # 已加载的插件
        self._plugins: Dict[str, Plugin] = {}

        # 插件配置
        self._plugin_configs: Dict[str, Dict[str, Any]] = {}

        # 加载内置插件
        self._load_builtin_plugins()

        logger.info(f"PluginManager initialized, loaded {len(self._plugins)} plugins")

    def _load_builtin_plugins(self):
        """加载内置插件"""
        # 内置插件定义
        builtin_plugins = {
            "http_api": self._create_http_api_plugin(),
            "data_processor": self._create_data_processor_plugin(),
        }

        for name, plugin in builtin_plugins.items():
            self._plugins[name] = plugin
            # 新架构：自动注册为器官系统的 Plugin
            self._register_as_organ(plugin)
            logger.debug(f"Loaded builtin plugin: {name}")

    def _register_as_organ(self, plugin: Plugin) -> bool:
        """将插件注册到统一器官管理器

        Args:
            plugin: 插件实例

        Returns:
            是否成功注册
        """
        if not self.unified_organ_manager:
            return False

        try:
            from organs import Plugin as OrganPlugin

            organ_plugin = OrganPlugin(
                name=plugin.info.name,
                code=plugin.code,
                capabilities=plugin.info.capabilities,
                description=plugin.info.description,
                author=plugin.info.author,
                version=plugin.info.version,
                dependencies=plugin.info.dependencies,
                config_schema=plugin.info.config_schema,
            )

            success = self.unified_organ_manager.add_plugin(organ_plugin)
            if success:
                logger.info(f"已将插件注册到器官管理器: {plugin.info.name}")

                # 注册器官使用指南（存入记忆系统）
                guide_manager = get_organ_guide_manager()
                guide_manager.register_organ_guide(
                    name=plugin.info.name,
                    organ_type="plugin",
                    description=plugin.info.description,
                    capabilities=plugin.info.capabilities,
                    parameters=plugin.info.config_schema,
                )
                logger.info(f"已为插件生成使用指南: {plugin.info.name}")

            return success

        except Exception as e:
            logger.error(f"注册插件到器官管理器失败: {e}")
            return False

    # 向后兼容别名
    _register_as_plugged_organ = _register_as_organ

    def _create_http_api_plugin(self) -> Plugin:
        """创建 HTTP API 插件"""
        code = '''"""HTTP API 插件 - 调用外部 HTTP API"""

import requests
from typing import Dict, Any, Optional

class HttpApi:
    """HTTP API 调用插件"""

    def __init__(self, base_url: str = "", api_key: str = "", timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()

        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})

    def get(self, endpoint: str, params: Dict = None, **kwargs) -> Dict[str, Any]:
        """GET 请求"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        response = self.session.get(url, params=params, timeout=self.timeout, **kwargs)
        response.raise_for_status()
        return response.json()

    def post(self, endpoint: str, data: Dict = None, json: Dict = None, **kwargs) -> Dict[str, Any]:
        """POST 请求"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        response = self.session.post(url, data=data, json=json, timeout=self.timeout, **kwargs)
        response.raise_for_status()
        return response.json()

    def put(self, endpoint: str, data: Dict = None, **kwargs) -> Dict[str, Any]:
        """PUT 请求"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        response = self.session.put(url, data=data, timeout=self.timeout, **kwargs)
        response.raise_for_status()
        return response.json()

    def delete(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """DELETE 请求"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        response = self.session.delete(url, timeout=self.timeout, **kwargs)
        response.raise_for_status()
        return response.json()

    def set_header(self, key: str, value: str):
        """设置请求头"""
        self.session.headers[key] = value

    def set_base_url(self, base_url: str):
        """设置基础 URL"""
        self.base_url = base_url.rstrip('/')
'''

        return Plugin(
            info=PluginInfo(
                name="http_api",
                description="HTTP API 调用插件",
                plugin_type=PluginType.EXTERNAL,
                capabilities=["http_get", "http_post", "http_put", "http_delete"],
                dependencies=["requests"],
                config_schema={
                    "base_url": {"type": "string", "default": ""},
                    "api_key": {"type": "string", "default": ""},
                    "timeout": {"type": "integer", "default": 30},
                }
            ),
            code=code,
        )

    def _create_data_processor_plugin(self) -> Plugin:
        """创建数据处理插件"""
        code = '''"""数据处理插件 - CSV/Excel 数据处理"""

from typing import Dict, Any, List, Optional
import io

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

class DataProcessor:
    """数据处理插件"""

    def __init__(self):
        self.capabilities = ["read_csv", "read_json", "process_data", "to_excel", "filter_data"]

    def read_csv(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """读取 CSV 文件"""
        if not HAS_PANDAS:
            return {"success": False, "error": "pandas not installed"}

        df = pd.read_csv(file_path, **kwargs)
        return {
            "success": True,
            "data": df.to_dict("records"),
            "rows": len(df),
            "columns": list(df.columns)
        }

    def read_json(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """读取 JSON 文件"""
        if not HAS_PANDAS:
            return {"success": False, "error": "pandas not installed"}

        df = pd.read_json(file_path, **kwargs)
        return {
            "success": True,
            "data": df.to_dict("records"),
            "rows": len(df),
            "columns": list(df.columns)
        }

    def process_data(self, data: List[Dict], operations: List[Dict]) -> Dict[str, Any]:
        """处理数据（过滤、聚合等）"""
        if not HAS_PANDAS:
            return {"success": False, "error": "pandas not installed"}

        df = pd.DataFrame(data)

        for op in operations:
            op_type = op.get("type")

            if op_type == "filter":
                df = df.query(op["query"])
            elif op_type == "aggregate":
                df = df.groupby(op["by"]).agg(op["func"]).reset_index()
            elif op_type == "sort":
                df = df.sort_values(by=op["by"], ascending=op.get("ascending", True))
            elif op_type == "select":
                df = df[op["columns"]]

        return {
            "success": True,
            "data": df.to_dict("records"),
            "rows": len(df)
        }

    def to_excel(self, data: List[Dict], output_path: str) -> Dict[str, Any]:
        """导出到 Excel"""
        if not HAS_PANDAS:
            return {"success": False, "error": "pandas not installed"}

        df = pd.DataFrame(data)
        df.to_excel(output_path, index=False)
        return {
            "success": True,
            "output_path": output_path
        }

    def filter_data(self, data: List[Dict], condition: str) -> Dict[str, Any]:
        """过滤数据"""
        if not HAS_PANDAS:
            return {"success": False, "error": "pandas not installed"}

        df = pd.DataFrame(data)
        filtered = df.query(condition)
        return {
            "success": True,
            "data": filtered.to_dict("records"),
            "rows": len(filtered)
        }

    def get_capabilities(self) -> List[str]:
        return self.capabilities
'''

        return Plugin(
            info=PluginInfo(
                name="data_processor",
                description="数据处理插件 - CSV/Excel 处理",
                plugin_type=PluginType.INTERNAL,
                capabilities=["read_csv", "read_json", "process_data", "to_excel", "filter_data"],
                dependencies=["pandas"],
                config_schema={}
            ),
            code=code,
        )

    def load_plugin(self, name: str, config: Dict[str, Any] = None) -> bool:
        """加载插件

        Args:
            name: 插件名
            config: 插件配置

        Returns:
            是否成功
        """
        # 已经加载过
        if name in self._plugins:
            if config:
                self._plugins[name].config.update(config)
            return True

        # 从文件加载
        plugin_dir = self.plugins_dir / name
        if not plugin_dir.exists():
            logger.warning(f"Plugin not found: {name}")
            return False

        try:
            # 读取代码
            code_file = plugin_dir / "__init__.py"
            if not code_file.exists():
                logger.error(f"Plugin code not found: {code_file}")
                return False

            with open(code_file, 'r', encoding='utf-8') as f:
                code = f.read()

            # 读取元数据
            meta_file = plugin_dir / "metadata.json"
            if meta_file.exists():
                with open(meta_file, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
            else:
                meta = {}

            # 创建插件
            plugin = Plugin(
                info=PluginInfo(
                    name=meta.get("name", name),
                    description=meta.get("description", ""),
                    plugin_type=PluginType(meta.get("plugin_type", "internal")),
                    capabilities=meta.get("capabilities", []),
                    dependencies=meta.get("dependencies", []),
                ),
                code=code,
                config=config or {},
            )

            self._plugins[name] = plugin
            # 新架构：自动注册到器官管理器
            self._register_as_organ(plugin)
            logger.info(f"Loaded plugin: {name}")
            return True

        except Exception as e:
            logger.error(f"Failed to load plugin {name}: {e}")
            return False

    def get_plugin(self, name: str) -> Optional[Plugin]:
        """获取插件

        Args:
            name: 插件名

        Returns:
            插件实例
        """
        return self._plugins.get(name)

    def list_plugins(self) -> List[PluginInfo]:
        """列出所有插件

        Returns:
            插件信息列表
        """
        return [p.info for p in self._plugins.values()]

    def get_plugin_for_capability(self, capability: str) -> Optional[Plugin]:
        """根据能力获取插件

        Args:
            capability: 能力名称

        Returns:
            插件实例
        """
        for plugin in self._plugins.values():
            if capability in plugin.info.capabilities:
                return plugin
        return None

    def get_similar_plugin_for_learning(self, requirement) -> Optional[Plugin]:
        """获取相似插件作为学习参考

        成长系统可以参考插件来学习如何生成代码。
        这是"插件作为过渡"设计的一部分。

        Args:
            requirement: 肢体需求（LimbRequirement）

        Returns:
            相似的插件，如果没有返回 None
        """
        # 1. 精确匹配：插件能力完全包含需求能力
        for plugin in self._plugins.values():
            if set(requirement.capabilities).issubset(set(plugin.info.capabilities)):
                logger.info(f"Found exact match plugin for learning: {plugin.info.name}")
                return plugin

        # 2. 部分匹配：有重叠的能力
        best_match = None
        best_overlap = 0

        for plugin in self._plugins.values():
            overlap = len(set(requirement.capabilities) & set(plugin.info.capabilities))
            if overlap > best_overlap:
                best_overlap = overlap
                best_match = plugin

        # 3. 类型匹配：根据插件类型和需求类型
        if best_match is None:
            # 根据需求描述关键词匹配
            desc_lower = requirement.description.lower()

            for plugin in self._plugins.values():
                plugin_keywords = {
                    "http_api": ["http", "api", "request", "get", "post", "url", "网络", "接口"],
                    "data_processor": ["csv", "excel", "data", "process", "数据", "表格", "处理"],
                }

                keywords = plugin_keywords.get(plugin.info.name, [])
                if any(kw in desc_lower for kw in keywords):
                    best_match = plugin
                    break

        if best_match:
            logger.info(f"Found similar plugin for learning: {best_match.info.name} (overlap: {best_overlap})")

        return best_match

    def has_plugin(self, name: str) -> bool:
        """检查插件是否存在

        Args:
            name: 插件名

        Returns:
            是否存在
        """
        return name in self._plugins

    def unload_plugin(self, name: str) -> bool:
        """卸载插件

        Args:
            name: 插件名

        Returns:
            是否成功
        """
        if name in self._plugins:
            # 新架构：从统一器官管理器中移除
            if self.unified_organ_manager:
                self.unified_organ_manager.remove_organ(name)

            # 移除器官使用指南
            guide_manager = get_organ_guide_manager()
            guide_manager.remove_organ_guide(name)

            del self._plugins[name]
            logger.info(f"Unloaded plugin: {name}")
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息
        """
        return {
            "total_plugins": len(self._plugins),
            "plugins": [name for name in self._plugins.keys()],
            "builtin_count": 2,  # http_api, data_processor
        }


def create_plugin_manager(
    plugins_dir: Path = None,
    config: Dict[str, Any] = None,
    unified_organ_manager=None
) -> PluginManager:
    """创建插件管理器

    Args:
        plugins_dir: 插件目录
        config: 配置
        unified_organ_manager: 统一器官管理器（新版，可选）

    Returns:
        PluginManager 实例
    """
    return PluginManager(plugins_dir, config, unified_organ_manager)
