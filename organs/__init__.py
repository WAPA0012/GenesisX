"""Organ system - 器官系统

GenesisX 的器官系统负责提供所有执行能力。

三种器官类型：
- 内脏 (BuiltinOrgan) = 内置器官，代码写死的（如 MindOrgan）
- 肢体 (Limb)         = LLM 动态生成的（对应 limb_generator 的 GeneratedLimb）
- 插件 (Plugin)       = 预制安装的（对应 plugin_manager 的 Plugin）

新架构 (v2.0):
- 所有能力提供者都是"器官"
- 来源不同：内脏/肢体/插件
- 接口统一：propose_actions + execute_capability

使用方式:
    from organs import UnifiedOrganManager, BuiltinOrgan, Limb, Plugin

    manager = UnifiedOrganManager()
    manager.add_builtin_organ(MindOrgan())    # 添加内脏
    manager.add_limb(limb_organ)              # 添加肢体
    manager.add_plugin(plugin_organ)          # 添加插件

    capabilities = manager.list_all_capabilities()
    result = manager.execute_capability("http_request", url="...")
"""
import warnings
from typing import Optional
from enum import Enum

# 新架构 - 统一器官系统
from .unified_organ import (
    UnifiedOrgan,
    UnifiedOrganManager,
    BuiltinOrgan,
    Limb,
    Plugin,
    OrganSource,
    OrganType,
    OrganInfo,
    # 向后兼容别名
    GrownOrgan,
    PluggedOrgan,
)

# 旧架构 - 向后兼容
from .base_organ import BaseOrgan
from common.models import CapabilityResult

# 尝试从 .limbs 导入 Limb，如果不可用则向后兼容
try:
    from .limbs import Limb as MountedOrgan
except ImportError:
    from .base_organ import MountedOrgan

# 从 axiology.drives 导入驱动力相关类（向后兼容）
from axiology.drives import DriveSignal

# DriveIntensity 枚举（用于驱动力强度描述）
class DriveIntensity(Enum):
    """驱动力强度等级"""
    NONE = 0.0
    WEAK = 0.25
    MODERATE = 0.5
    STRONG = 0.75
    URGENT = 1.0


# 从新位置导入驱动力（向后兼容）
from axiology.drives import (
    CuriosityDrive as _CuriosityDrive,
    CompetenceDrive as _CompetenceDrive,
    HomeostasisDrive as _HomeostasisDrive,
    AttachmentDrive as _AttachmentDrive,
    SafetyDrive as _SafetyDrive,
)

# 创建向后兼容的别名类（已废弃）
class CuriosityOrgan(_CuriosityDrive):
    """好奇心器官（已废弃，请使用 axiology.drives.CuriosityDrive）"""
    def __init__(self):
        warnings.warn(
            "CuriosityOrgan 已废弃，请使用 axiology.drives.CuriosityDrive",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__()


class CompetenceOrgan(_CompetenceDrive):
    """胜任力器官（已废弃，请使用 axiology.drives.CompetenceDrive）"""
    def __init__(self):
        warnings.warn(
            "CompetenceOrgan 已废弃，请使用 axiology.drives.CompetenceDrive",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__()


class HomeostasisOrgan(_HomeostasisDrive):
    """稳态器官（已废弃，请使用 axiology.drives.HomeostasisDrive）"""
    def __init__(self):
        warnings.warn(
            "HomeostasisOrgan 已废弃，请使用 axiology.drives.HomeostasisDrive",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__()


class AttachmentOrgan(_AttachmentDrive):
    """依恋器官（已废弃，请使用 axiology.drives.AttachmentDrive）"""
    def __init__(self):
        warnings.warn(
            "AttachmentOrgan 已废弃，请使用 axiology.drives.AttachmentDrive",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__()


# 内部器官（从 internal/ 导入）
try:
    from .internal.mind_organ import MindOrgan
    from .internal.caretaker_organ import CaretakerOrgan
    from .internal.scout_organ import ScoutOrgan
    from .internal.builder_organ import BuilderOrgan
    from .internal.archivist_organ import ArchivistOrgan
    from .internal.immune_organ import ImmuneOrgan
    _internal_organs_available = True
except ImportError:
    _internal_organs_available = False

# 其他组件
try:
    from .organ_selector import OrganSelector
    from .organ_interface import OrganInterface
except ImportError:
    pass


__all__ = [
    # 新架构 - 统一器官系统
    "UnifiedOrgan",
    "UnifiedOrganManager",
    "BuiltinOrgan",
    "Limb",
    "Plugin",
    "OrganSource",
    "OrganType",
    "OrganInfo",
    # 向后兼容
    "GrownOrgan",
    "PluggedOrgan",
    # 旧架构 - 向后兼容
    "BaseOrgan",
    "MountedOrgan",
    "DriveSignal",
    "DriveIntensity",
    "CapabilityResult",
    # 向后兼容的驱动力器官（已废弃）
    "CuriosityOrgan",
    "CompetenceOrgan",
    "HomeostasisOrgan",
    "AttachmentOrgan",
    # 器官管理
    "OrganManager",  # 旧管理器
    "get_global_organ_manager",
    "get_unified_organ_manager",  # 新管理器
]

# 添加内部器官到 __all__（如果可用）
if _internal_organs_available:
    __all__.extend([
        "MindOrgan",
        "CaretakerOrgan",
        "ScoutOrgan",
        "BuilderOrgan",
        "ArchivistOrgan",
        "ImmuneOrgan",
    ])

# 添加其他组件
try:
    __all__.extend(["OrganSelector", "OrganInterface"])
except NameError:
    pass


# ==================== 全局单例 ====================

# 旧管理器（向后兼容）
try:
    from .organ_manager import OrganManager
    _global_organ_manager: Optional["OrganManager"] = None

    def get_global_organ_manager() -> "OrganManager":
        """获取全局器官管理器单例（旧版，向后兼容）"""
        global _global_organ_manager
        if _global_organ_manager is None:
            _global_organ_manager = OrganManager()
        return _global_organ_manager
except ImportError:
    pass

# 新管理器
_global_unified_manager: Optional[UnifiedOrganManager] = None


def get_unified_organ_manager() -> UnifiedOrganManager:
    """获取统一器官管理器单例（新版）"""
    global _global_unified_manager
    if _global_unified_manager is None:
        _global_unified_manager = UnifiedOrganManager()
    return _global_unified_manager
