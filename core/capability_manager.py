"""Capability Manager - 能力管理器

统一调度成长系统和插件系统，为 LifeLoop 提供简单的能力查询接口。

架构：
    LifeLoop
        ↓
    CapabilityManager.get_capability("图像处理")
        ↓
        ├── 1. 查插件系统（现成的）
        ├── 2. 查已生成肢体（之前长出来的）
        └── 3. 成长系统（LLM 新生成）

职责分离：
| 系统 | 职责 | 触发条件 |
|------|------|----------|
| CapabilityManager | 统一调度 | "我需要这个能力" |
| 插件系统 | 快速装备 | 有现成的 |
| 成长系统 | 自主生成 | 没有现成的 |
| 技能记忆 | 使用知识 | 知道怎么用 |

使用方式：
    manager = CapabilityManager(growth_manager, plugin_manager)
    capability = manager.get_capability("http_get")
    if capability:
        result = capability.execute(...)
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from common.logger import get_logger

logger = get_logger(__name__)


class CapabilitySource(Enum):
    """能力来源"""
    PLUGIN = "plugin"           # 预制插件
    LIMB = "limb"               # 已生成的肢体
    GENERATING = "generating"   # 正在生成中
    UNKNOWN = "unknown"         # 未知

    # 向后兼容
    GROWN = "limb"              # 已废弃，请使用 LIMB


@dataclass
class Capability:
    """能力实例"""
    name: str
    source: CapabilitySource
    capabilities: List[str]
    instance: Any = None
    execute_func: Callable = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def execute(self, method: str = None, **kwargs) -> Dict[str, Any]:
        """执行能力

        Args:
            method: 方法名（可选）
            **kwargs: 参数

        Returns:
            执行结果
        """
        try:
            if self.execute_func:
                # 有指定的执行函数
                return self.execute_func(**kwargs)

            if self.instance is None:
                return {"success": False, "error": "No instance available"}

            if method:
                # 调用指定方法
                if not hasattr(self.instance, method):
                    return {"success": False, "error": f"Method '{method}' not found"}
                func = getattr(self.instance, method)
                result = func(**kwargs)
                return {"success": True, "result": result}
            else:
                # 直接调用实例
                if callable(self.instance):
                    result = self.instance(**kwargs)
                    return {"success": True, "result": result}
                else:
                    return {"success": False, "error": "Instance is not callable and no method specified"}

        except Exception as e:
            return {"success": False, "error": str(e)}


class CapabilityManager:
    """能力管理器

    统一调度插件系统和成长系统，提供简单的能力查询和执行接口。

    查询优先级：
    1. 插件系统 - 现成的、稳定的
    2. 已生成肢体 - 之前通过成长生成的
    3. 成长系统 - LLM 动态生成新的

    使用方式：
        # 初始化
        manager = CapabilityManager(growth_manager, plugin_manager)

        # 查询能力
        cap = manager.get_capability("http_get")

        # 执行能力
        if cap:
            result = cap.execute("get", endpoint="/users")

        # 检查是否有能力
        if manager.has_capability("图像处理"):
            ...
    """

    def __init__(
        self,
        growth_manager=None,
        plugin_manager=None,
        organ_manager=None,
        config: Dict[str, Any] = None
    ):
        """刟能力管理器

        Args:
            growth_manager: 成长管理器
            plugin_manager: 插件管理器
            organ_manager: 器官管理器
            config: 配置
        """
        self.growth_manager = growth_manager
        self.plugin_manager = plugin_manager
        self.organ_manager = organ_manager
        self.config = config or {}

        # 已获取的能力缓存
        self._capability_cache: Dict[str, Capability] = {}

        # 能力映射（能力名 -> 来源）
        self._capability_map: Dict[str, CapabilitySource] = {}

        # 统计
        self._stats = {
            "plugin_hits": 0,
            "limb_hits": 0,
            "growth_requests": 0,
            "misses": 0,
        }

        # 初始化能力映射
        self._build_capability_map()

        logger.info("CapabilityManager initialized")

    def _build_capability_map(self):
        """构建能力映射"""
        # 内置能力（系统始终拥有）
        builtin_capabilities = [
            "llm_access",      # LLM 访问能力
            "memory_access",   # 记忆访问能力
            "tool_use",        # 工具使用能力
        ]
        for cap in builtin_capabilities:
            self._capability_map[cap] = CapabilitySource.PLUGIN  # 标记为内置

        # 从插件系统获取能力
        if self.plugin_manager:
            for plugin_info in self.plugin_manager.list_plugins():
                for cap in plugin_info.capabilities:
                    self._capability_map[cap] = CapabilitySource.PLUGIN

        # 从器官管理器获取能力
        if self.organ_manager:
            try:
                capabilities = self.organ_manager.list_all_capabilities()
                for cap in capabilities:
                    if cap not in self._capability_map:
                        self._capability_map[cap] = CapabilitySource.UNKNOWN
            except Exception as e:
                logger.warning(f"Failed to get capabilities from organ_manager: {e}")

        logger.info(f"Built capability map with {len(self._capability_map)} capabilities")

    def get_capability(self, capability_name: str) -> Optional[Capability]:
        """获取能力

        按优先级查找：插件 -> 已生成 -> 触发成长

        Args:
            capability_name: 能力名称

        Returns:
            Capability 实例，如果不存在返回 None
        """
        # 1. 检查缓存
        if capability_name in self._capability_cache:
            return self._capability_cache[capability_name]

        # 2. 从插件系统查找
        if self.plugin_manager:
            plugin = self.plugin_manager.get_plugin_for_capability(capability_name)
            if plugin:
                self._stats["plugin_hits"] += 1
                # 使用闭包捕获 plugin
                def make_execute_func(p):
                    def execute_func(**kw):
                        return p.execute(**kw)
                    return execute_func

                cap = Capability(
                    name=plugin.info.name,
                    source=CapabilitySource.PLUGIN,
                    capabilities=plugin.info.capabilities,
                    instance=plugin._instance if hasattr(plugin, '_instance') else None,
                    execute_func=make_execute_func(plugin),
                    metadata={"plugin_info": plugin.info.to_dict()}
                )
                self._capability_cache[capability_name] = cap
                logger.debug(f"Found capability '{capability_name}' in plugin: {plugin.info.name}")
                return cap

        # 3. 从已生成肢体查找
        if self.growth_manager:
            for limb_name, limb in self.growth_manager.limb_generator._generated_limbs.items():
                if capability_name in limb.capabilities:
                    self._stats["limb_hits"] += 1
                    cap = Capability(
                        name=limb_name,
                        source=CapabilitySource.LIMB,
                        capabilities=limb.capabilities,
                        metadata={"limb": limb}
                    )
                    self._capability_cache[capability_name] = cap
                    logger.debug(f"Found capability '{capability_name}' in limb: {limb_name}")
                    return cap

        # 4. 触发成长（异步，返回 None）
        if self.growth_manager and self.growth_manager._growth_enabled:
            self._stats["growth_requests"] += 1
            logger.info(f"Capability '{capability_name}' not found, triggering growth")

            # 这里不直接触发成长，而是记录需求
            # 实际成长应该在合适的时机由 LifeLoop 触发
            # 返回一个标记正在生成的能力
            return Capability(
                name=capability_name,
                source=CapabilitySource.GENERATING,
                capabilities=[capability_name],
                metadata={"status": "needs_growth"}
            )

        self._stats["misses"] += 1
        return None

    def has_capability(self, capability_name: str) -> bool:
        """检查是否有某能力

        Args:
            capability_name: 能力名称

        Returns:
            是否存在
        """
        # 检查映射
        if capability_name in self._capability_map:
            return True

        # 检查缓存
        if capability_name in self._capability_cache:
            return True

        # 尝试获取
        cap = self.get_capability(capability_name)
        return cap is not None and cap.source != CapabilitySource.GENERATING

    def list_capabilities(self) -> List[str]:
        """列出所有可用能力

        Returns:
            能力名称列表
        """
        capabilities = set()

        # 从插件获取
        if self.plugin_manager:
            for plugin_info in self.plugin_manager.list_plugins():
                capabilities.update(plugin_info.capabilities)

        # 从已生成肢体获取
        if self.growth_manager:
            for limb in self.growth_manager.limb_generator._generated_limbs.values():
                capabilities.update(limb.capabilities)

        # 从器官管理器获取
        if self.organ_manager:
            try:
                capabilities.update(self.organ_manager.list_all_capabilities())
            except Exception:
                pass

        return list(capabilities)

    def request_growth(self, capability_name: str, context: Dict[str, Any] = None) -> bool:
        """请求成长新能力

        Args:
            capability_name: 需要的能力名称
            context: 上下文

        Returns:
            是否成功触发成长
        """
        if not self.growth_manager:
            logger.warning("Growth manager not available")
            return False

        if not self.growth_manager._growth_enabled:
            logger.warning("Growth is disabled")
            return False

        # 创建需求
        from .growth import LimbRequirement, GenerationType

        requirement = LimbRequirement(
            name=capability_name,
            description=f"自动生成能力: {capability_name}",
            capabilities=[capability_name],
            generation_type=GenerationType.INTERNAL,
        )

        # 触发成长
        success, limb = self.growth_manager.generate_limb(requirement)

        if success and limb:
            # 更新缓存
            self._capability_cache[capability_name] = Capability(
                name=limb.name,
                source=CapabilitySource.LIMB,
                capabilities=limb.capabilities,
                metadata={"limb": limb}
            )
            # 更新映射
            for cap in limb.capabilities:
                self._capability_map[cap] = CapabilitySource.LIMB
            return True

        return False

    def register_capability(self, capability: Capability):
        """注册能力

        Args:
            capability: 能力实例
        """
        self._capability_cache[capability.name] = capability
        for cap in capability.capabilities:
            self._capability_map[cap] = capability.source
        logger.info(f"Registered capability: {capability.name}")

    def get_active_capabilities(self, current_tick: int = None) -> List[str]:
        """获取当前活跃的能力列表

        Args:
            current_tick: 当前 tick（用于过滤，暂时未使用）

        Returns:
            活跃能力名称列表
        """
        # 返回所有已注册的能力
        return list(self._capability_map.keys())

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息
        """
        return {
            **self._stats,
            "total_capabilities": len(self._capability_map),
            "cached_capabilities": len(self._capability_cache),
        }

    def clear_cache(self):
        """清空缓存"""
        self._capability_cache.clear()
        logger.info("Capability cache cleared")


def create_capability_manager(
    growth_manager=None,
    plugin_manager=None,
    organ_manager=None,
    config: Dict[str, Any] = None
) -> CapabilityManager:
    """创建能力管理器

    Args:
        growth_manager: 成长管理器
        plugin_manager: 插件管理器
        organ_manager: 器官管理器
        config: 配置

    Returns:
        CapabilityManager 实例
    """
    return CapabilityManager(growth_manager, plugin_manager, organ_manager, config)
