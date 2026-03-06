"""统一器官系统 - Unified Organ System

将三种能力来源统一为一套系统：
- 内脏 (BuiltinOrgan) = 内置器官，代码写死的（如 MindOrgan）
- 肢体 (Limb)         = LLM 动态生成的（对应 limb_generator 的 GeneratedLimb）
- 插件 (Plugin)       = 预制安装的（对应 plugin_manager 的 Plugin）

设计原则：
1. 器官 = 所有能力的统一抽象
2. 来源不同：内脏/肢体/插件
3. 接口统一：都有相同的 propose_actions 和 execute_capability

器官来源 (OrganSource):
- BUILTIN  = 内脏 - 代码写死的，如 MindOrgan
- LIMB     = 肢体 - LLM 动态生成的，对应 GeneratedLimb
- PLUGIN   = 插件 - 预制安装的，对应 Plugin

使用方式：
    manager = UnifiedOrganManager()

    # 添加内脏
    manager.add_builtin_organ(MindOrgan())

    # 添加肢体（由成长系统/limb_generator 生成）
    manager.add_limb(limb_organ)

    # 添加插件（由插件系统加载）
    manager.add_plugin(plugin_organ)

    # 统一调用
    capabilities = manager.list_all_capabilities()
    result = manager.execute_capability("http_request", url="...")
"""

from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
from datetime import datetime, timezone
import hashlib

from common.logger import get_logger
from common.models import Action, CapabilityResult

logger = get_logger(__name__)


class OrganSource(Enum):
    """器官来源"""
    BUILTIN = "builtin"    # 内脏 - 代码写死的
    LIMB = "limb"          # 肢体 - LLM生成的
    PLUGIN = "plugin"      # 插件 - 预制安装的

    # 向后兼容
    GROWN = "limb"         # 已废弃，请使用 LIMB
    PLUGGED = "plugin"     # 已废弃，请使用 PLUGIN


class OrganType(Enum):
    """器官类型"""
    INTERNAL = "internal"   # 内部器官（纯 Python）
    EXTERNAL = "external"   # 外部器官（需要 API/容器）
    HYBRID = "hybrid"       # 混合器官


@dataclass
class OrganInfo:
    """器官信息"""
    name: str
    description: str
    source: OrganSource
    organ_type: OrganType
    capabilities: List[str]
    version: str = "1.0"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # 元数据
    author: str = "GenesisX"
    dependencies: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)

    # 成长器官特有
    generation_prompt: str = ""  # LLM 生成时的提示词
    parent_organ: str = ""       # 父器官（如果有）

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "source": self.source.value,
            "organ_type": self.organ_type.value,
            "capabilities": self.capabilities,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "author": self.author,
            "dependencies": self.dependencies,
        }


class UnifiedOrgan(ABC):
    """统一器官基类

    所有器官（内置/成长/外挂）都继承此类。
    """

    def __init__(
        self,
        name: str,
        source: OrganSource,
        organ_type: OrganType = OrganType.INTERNAL,
        capabilities: List[str] = None,
        description: str = "",
        value_dimension: str = None,
    ):
        self.name = name
        self.source = source
        self.organ_type = organ_type
        self._capabilities = capabilities or []
        self.description = description
        self.value_dimension = value_dimension
        self.enabled = True
        self._mounted = False

    # ==================== 核心接口 ====================

    @abstractmethod
    def propose_actions(
        self,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[Action]:
        """提议动作

        Args:
            state: 当前状态
            context: 当前上下文

        Returns:
            动作列表
        """
        pass

    def execute_capability(
        self,
        capability_name: str,
        **kwargs
    ) -> CapabilityResult:
        """执行能力

        Args:
            capability_name: 能力名称
            **kwargs: 能力参数

        Returns:
            CapabilityResult: 执行结果
        """
        if capability_name not in self._capabilities:
            return CapabilityResult(
                success=False,
                message=f"器官 {self.name} 不支持能力 {capability_name}",
                error=f"Capability not supported: {capability_name}"
            )

        # 默认实现：子类应该重写
        return CapabilityResult(
            success=False,
            message=f"能力 {capability_name} 未实现",
            error="Not implemented"
        )

    # ==================== 能力查询 ====================

    def has_capability(self, capability_name: str) -> bool:
        """检查是否有某个能力"""
        return capability_name in self._capabilities

    def get_capabilities(self) -> List[str]:
        """获取能力列表"""
        return self._capabilities.copy()

    def add_capability(self, capability: str):
        """添加能力"""
        if capability not in self._capabilities:
            self._capabilities.append(capability)

    # ==================== 生命周期 ====================

    def mount(self) -> Tuple[bool, str]:
        """挂载器官（启动容器/初始化）"""
        if self._mounted:
            return True, "器官已挂载"
        self._mounted = True
        return True, f"器官 {self.name} 挂载成功"

    def unmount(self) -> Tuple[bool, str]:
        """卸载器官"""
        if not self._mounted:
            return True, "器官未挂载"
        self._mounted = False
        return True, f"器官 {self.name} 卸载成功"

    def is_mounted(self) -> bool:
        """检查是否已挂载"""
        return self._mounted

    def set_enabled(self, enabled: bool):
        """启用/禁用器官"""
        self.enabled = enabled

    def get_info(self) -> OrganInfo:
        """获取器官信息"""
        return OrganInfo(
            name=self.name,
            description=self.description,
            source=self.source,
            organ_type=self.organ_type,
            capabilities=self._capabilities,
        )


# ============================================================================
# 具体器官类型（内脏、肢体、插件）
# ============================================================================

class BuiltinOrgan(UnifiedOrgan):
    """内脏 - 内置器官基类

    代码写死的器官，如 MindOrgan, CaretakerOrgan 等。
    这些是 GenesisX 出生就有的"内脏"，不需要学习。
    """

    def __init__(
        self,
        name: str,
        capabilities: List[str] = None,
        description: str = "",
        value_dimension: str = None,
    ):
        super().__init__(
            name=name,
            source=OrganSource.BUILTIN,
            organ_type=OrganType.INTERNAL,
            capabilities=capabilities,
            description=description,
            value_dimension=value_dimension,
        )


class Limb(UnifiedOrgan):
    """肢体

    LLM 动态生成的代码模块，对应 limb_generator 生成的 GeneratedLimb。
    当 GenesisX 发现需要新能力时，可以通过成长系统生成新肢体。

    流程：LimbGenerator → GeneratedLimb → Limb → UnifiedOrganManager
    """

    def __init__(
        self,
        name: str,
        code: str,
        capabilities: List[str],
        description: str = "",
        generation_prompt: str = "",
        organ_type: OrganType = OrganType.INTERNAL,
        config: Dict[str, Any] = None,
    ):
        super().__init__(
            name=name,
            source=OrganSource.LIMB,
            organ_type=organ_type,
            capabilities=capabilities,
            description=description,
        )
        self.code = code
        self.generation_prompt = generation_prompt
        self.config = config or {}
        self._instance = None
        self._hash = hashlib.md5(code.encode()).hexdigest()[:16]

    def _create_instance(self):
        """从代码创建实例"""
        if self._instance is not None:
            return self._instance

        try:
            namespace = {"__name__": f"limb_{self.name}"}
            exec(self.code, namespace)

            # 查找类
            for name, obj in namespace.items():
                if isinstance(obj, type) and name != "object":
                    self._instance = obj()
                    return self._instance
        except Exception as e:
            logger.error(f"创建肢体实例失败: {e}")
        return None

    def execute_capability(self, capability_name: str, **kwargs) -> CapabilityResult:
        """执行能力"""
        if not self.has_capability(capability_name):
            return CapabilityResult(
                success=False,
                error=f"Capability not supported: {capability_name}"
            )

        instance = self._create_instance()
        if instance is None:
            return CapabilityResult(
                success=False,
                error="Failed to create limb instance"
            )

        try:
            if hasattr(instance, capability_name):
                method = getattr(instance, capability_name)
                result = method(**kwargs)
                return CapabilityResult(
                    success=True,
                    data=result if isinstance(result, dict) else {"result": result}
                )
            return CapabilityResult(
                success=False,
                error=f"Method {capability_name} not found"
            )
        except Exception as e:
            return CapabilityResult(
                success=False,
                error=str(e)
            )

    def propose_actions(self, state: Dict[str, Any], context: Dict[str, Any]) -> List[Action]:
        """肢体默认不提议动作"""
        return []


# 向后兼容别名
GrownOrgan = Limb


class Plugin(UnifiedOrgan):
    """插件

    预制安装的代码模块，对应 plugin_manager 加载的 PluginInfo。
    这些是别人写好的代码，直接加载使用。

    流程：PluginManager → PluginInfo → Plugin → UnifiedOrganManager
    """

    def __init__(
        self,
        name: str,
        code: str,
        capabilities: List[str],
        description: str = "",
        author: str = "unknown",
        version: str = "1.0",
        dependencies: List[str] = None,
        config_schema: Dict[str, Any] = None,
    ):
        super().__init__(
            name=name,
            source=OrganSource.PLUGIN,
            organ_type=OrganType.HYBRID,
            capabilities=capabilities,
            description=description,
        )
        self.code = code
        self.author = author
        self.version = version
        self.dependencies = dependencies or []
        self.config_schema = config_schema or {}
        self._instance = None

    def _create_instance(self):
        """从代码创建实例"""
        if self._instance is not None:
            return self._instance

        try:
            namespace = {"__name__": f"plugin_{self.name}"}
            exec(self.code, namespace)

            for name, obj in namespace.items():
                if isinstance(obj, type) and name != "object":
                    self._instance = obj()
                    return self._instance
        except Exception as e:
            logger.error(f"创建插件实例失败: {e}")
        return None

    def execute_capability(self, capability_name: str, **kwargs) -> CapabilityResult:
        """执行能力"""
        if not self.has_capability(capability_name):
            return CapabilityResult(
                success=False,
                error=f"Capability not supported: {capability_name}"
            )

        instance = self._create_instance()
        if instance is None:
            return CapabilityResult(
                success=False,
                error="Failed to create plugin instance"
            )

        try:
            if hasattr(instance, capability_name):
                method = getattr(instance, capability_name)
                result = method(**kwargs)
                return CapabilityResult(
                    success=True,
                    data=result if isinstance(result, dict) else {"result": result}
                )
            return CapabilityResult(
                success=False,
                error=f"Method {capability_name} not found"
            )
        except Exception as e:
            return CapabilityResult(
                success=False,
                error=str(e)
            )

    def propose_actions(self, state: Dict[str, Any], context: Dict[str, Any]) -> List[Action]:
        """插件默认不提议动作"""
        return []


# 向后兼容别名
PluggedOrgan = Plugin


# ============================================================================
# 统一器官管理器
# ============================================================================

class UnifiedOrganManager:
    """统一器官管理器

    管理所有来源的器官：
    - 内脏 (BUILTIN)  - 内置器官，代码写死的（如 MindOrgan）
    - 肢体 (LIMB)     - LLM 生成的（对应 GeneratedLimb）
    - 插件 (PLUGIN)   - 预制安装的（对应 Plugin）
    """

    def __init__(self):
        self._organs: Dict[str, UnifiedOrgan] = {}
        self._capability_index: Dict[str, str] = {}  # capability -> organ_name

    # ==================== 添加器官 ====================

    def add_builtin_organ(self, organ: UnifiedOrgan) -> bool:
        """添加内脏（内置器官）"""
        if organ.name in self._organs:
            logger.warning(f"器官 {organ.name} 已存在")
            return False
        organ.source = OrganSource.BUILTIN
        self._register_organ(organ)
        logger.info(f"添加内脏: {organ.name}")
        return True

    def add_limb(self, organ: Limb) -> bool:
        """添加肢体（LLM生成的器官）"""
        if organ.name in self._organs:
            logger.warning(f"器官 {organ.name} 已存在")
            return False
        self._register_organ(organ)
        logger.info(f"添加肢体: {organ.name}")
        return True

    def add_plugin(self, organ: Plugin) -> bool:
        """添加插件（预制安装的器官）"""
        if organ.name in self._organs:
            logger.warning(f"器官 {organ.name} 已存在")
            return False
        self._register_organ(organ)
        logger.info(f"添加插件: {organ.name}")
        return True

    # 向后兼容别名
    add_grown_organ = add_limb
    add_plugged_organ = add_plugin

    def _register_organ(self, organ: UnifiedOrgan):
        """注册器官"""
        self._organs[organ.name] = organ
        for cap in organ.get_capabilities():
            self._capability_index[cap] = organ.name

    # ==================== 移除器官 ====================

    def remove_organ(self, name: str) -> bool:
        """移除器官"""
        if name not in self._organs:
            return False

        organ = self._organs[name]

        # 移除能力索引
        for cap in organ.get_capabilities():
            if self._capability_index.get(cap) == name:
                del self._capability_index[cap]

        # 卸载并移除
        organ.unmount()
        del self._organs[name]
        logger.info(f"移除器官: {name}")
        return True

    # ==================== 查询 ====================

    def get_organ(self, name: str) -> Optional[UnifiedOrgan]:
        """获取器官"""
        return self._organs.get(name)

    def list_organs(self, source: OrganSource = None) -> List[UnifiedOrgan]:
        """列出器官"""
        if source is None:
            return list(self._organs.values())
        return [o for o in self._organs.values() if o.source == source]

    def list_all_capabilities(self) -> List[str]:
        """列出所有能力"""
        return list(self._capability_index.keys())

    def has_capability(self, capability: str) -> bool:
        """检查是否有某个能力"""
        return capability in self._capability_index

    def get_organ_by_capability(self, capability: str) -> Optional[UnifiedOrgan]:
        """通过能力获取器官"""
        organ_name = self._capability_index.get(capability)
        if organ_name:
            return self._organs.get(organ_name)
        return None

    # ==================== 执行 ====================

    def execute_capability(self, capability: str, **kwargs) -> CapabilityResult:
        """执行能力"""
        organ = self.get_organ_by_capability(capability)
        if organ is None:
            return CapabilityResult(
                success=False,
                error=f"No organ provides capability: {capability}"
            )
        return organ.execute_capability(capability, **kwargs)

    def propose_all_actions(
        self,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[Tuple[str, Action]]:
        """收集所有器官的动作提议

        Returns:
            List of (organ_name, action)
        """
        actions = []
        for name, organ in self._organs.items():
            if organ.enabled:
                for action in organ.propose_actions(state, context):
                    actions.append((name, action))
        return actions

    # ==================== 统计 ====================

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        builtin = len([o for o in self._organs.values() if o.source == OrganSource.BUILTIN])
        limb = len([o for o in self._organs.values() if o.source == OrganSource.LIMB])
        plugin = len([o for o in self._organs.values() if o.source == OrganSource.PLUGIN])

        return {
            "total_organs": len(self._organs),
            "builtin_organs": builtin,
            "limb_organs": limb,
            "plugin_organs": plugin,
            "total_capabilities": len(self._capability_index),
        }
