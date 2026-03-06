"""Base Organ - 器官基类

器官系统负责提供"我能做什么"的执行能力。

注意：驱动力信号生成已迁移到 axiology.drives 模块。
    - 驱动力（"我想要什么"）→ axiology.drives
    - 器官（"我能做什么"）→ organs

命名说明：
- 器官 (organs/) = 自身进化产生的内部能力，完全可控
- 肢体 (limbs/) = 外部工具吞噬后挂载的，像"假肢"或"外骨骼"

修复：使用 common.models.CapabilityResult 统一定义，避免重复。
"""
from typing import List, Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod
from common.models import Action, CapabilityResult


class BaseOrgan(ABC):
    """器官基类

    所有器官必须继承此类。器官的核心功能：
    1. propose_actions() - 提议动作（主要接口，旧架构）
    2. execute_capability() - 执行具体能力（肢体实现）

    注意：驱动力信号生成由 axiology.drives 负责，不是器官的职责。
    """

    def __init__(self, name: str, value_dimension: str = None):
        """初始化器官

        Args:
            name: 器官名称
            value_dimension: 对应的价值维度 (curiosity/competence/homeostasis/attachment/safety)
                             用于器官与驱动力的关联
        """
        self.name = name
        self.value_dimension = value_dimension
        self.enabled = True

    # ==================== 能力执行（可选，肢体实现）====================

    def has_capability(self, capability_name: str) -> bool:
        """检查是否有某个能力

        默认返回 False，内部器官通常没有具体执行能力。
        肢体可以重写此方法。

        Args:
            capability_name: 能力名称

        Returns:
            是否有此能力
        """
        return False

    def execute_capability(
        self,
        capability_name: str,
        **kwargs
    ) -> CapabilityResult:
        """执行具体能力

        默认返回错误，肢体可以重写此方法来提供实际功能。

        Args:
            capability_name: 能力名称
            **kwargs: 能力参数

        Returns:
            CapabilityResult: 执行结果
        """
        return CapabilityResult(
            success=False,
            message=f"器官 {self.name} 不支持能力 {capability_name}",
            error=f"Capability not supported: {capability_name}"
        )

    def get_capabilities(self) -> List[str]:
        """获取此器官提供的所有能力列表

        Returns:
            能力名称列表
        """
        return []

    # ==================== 动作提议（旧架构接口）====================

    def propose_actions(
        self,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[Action]:
        """提议动作（旧架构接口）

        旧架构器官通过此方法提议动作。
        新架构中，驱动力信号由 axiology.drives 生成。

        Args:
            state: 当前状态
            context: 当前上下文

        Returns:
            动作列表
        """
        # 默认实现：返回空列表
        # 旧架构器官会重写此方法
        return []

    def set_enabled(self, enabled: bool):
        """启用或禁用器官"""
        self.enabled = enabled


# 向后兼容：从 organs.limbs 模块导入 Limb 作为 MountedOrgan
try:
    from .limbs import Limb as MountedOrgan
except ImportError:
    # 如果 limbs 模块不可用，创建一个简单的占位符
    class MountedOrgan(BaseOrgan):
        """挂载器官基类 (已废弃，请使用 limbs.Limb)

        此类保留用于向后兼容。
        新代码应使用 limbs.Limb 代替。

        命名说明：
        - 器官 (organs/) = 自身进化产生的内部能力
        - 肢体 (limbs/) = 外部工具吞噬后挂载的
        """

        def __init__(
            self,
            name: str,
            container_image: str,
            capabilities: List[str],
            value_dimension: str = None,
            description: str = ""
        ):
            """初始化挂载器官 (向后兼容)

            Args:
                name: 器官名称
                container_image: Docker 镜像名称
                capabilities: 此器官提供的能力列表
                value_dimension: 对应的价值维度
                description: 描述
            """
            super().__init__(name, value_dimension)
            self.container_image = container_image
            self._capabilities = capabilities
            self._container_id = None
            self._is_mounted = False
            self.description = description

        def has_capability(self, capability_name: str) -> bool:
            return capability_name in self._capabilities

        def get_capabilities(self) -> List[str]:
            return self._capabilities.copy()

        def mount(self) -> Tuple[bool, str]:
            """挂载器官（启动 Docker 容器）

            Returns:
                (是否成功, 消息)
            """
            if self._is_mounted:
                return True, "器官已挂载"
            self._is_mounted = True
            return True, f"器官 {self.name} 挂载成功（模拟）"

        def unmount(self) -> Tuple[bool, str]:
            """卸载器官（停止 Docker 容器）

            Returns:
                (是否成功, 消息)
            """
            if not self._is_mounted:
                return True, "器官未挂载"
            self._is_mounted = False
            return True, f"器官 {self.name} 卸载成功（模拟）"

        def is_mounted(self) -> bool:
            """检查器官是否已挂载"""
            return self._is_mounted

        def execute_capability(
            self,
            capability_name: str,
            **kwargs
        ) -> CapabilityResult:
            """执行能力（默认实现，子类可以重写）

            Args:
                capability_name: 能力名称
                **kwargs: 能力参数

            Returns:
                CapabilityResult: 执行结果
            """
            if capability_name in self._capabilities:
                return CapabilityResult(
                    success=False,
                    message=f"能力 {capability_name} 已定义但未实现（占位符）",
                    error=f"Not implemented: {capability_name}"
                )
            return CapabilityResult(
                success=False,
                message=f"器官 {self.name} 不支持能力 {capability_name}",
                error=f"Capability not supported: {capability_name}"
            )
