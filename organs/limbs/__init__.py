"""Limbs - 肢体系统

肢体是从外部软件"吞噬"而来的外部能力，运行在 Docker 容器中。

命名说明：
- 器官 (organs/) = 自身进化产生的内部能力，完全可控
- 肢体 (limbs/) = 外部工具吞噬后挂载的，像"假肢"或"外骨骼"

生物学比喻：
- 器官 = 自己身体里长的（心、肝、肺）
- 肢体 = 可以外接的工具（假肢、外骨骼、工具手）

特点：
- 来自外部软件（PS、Excel、浏览器等）
- 按需挂载，不常驻内存
- 可以内化为真正的内部器官

与器官的区别：
- 肢体 = 外部软件的容器化运行
- 器官 = 自主进化的能力或已完全内化的能力

修复：使用 common.models.CapabilityResult 统一定义，避免重复。
"""
from typing import List, Dict, Any, Optional, Tuple
from common.models import Action, CapabilityResult
from organs.base_organ import BaseOrgan


class Limb(BaseOrgan):
    """肢体基类

    肢体是"被吞噬的外部工具"，运行在 Docker 容器中，
    提供具体的执行能力（如 PS肢体、Excel肢体）。

    特点：
    - 运行在独立容器中
    - 可以长期挂载
    - 有具体执行能力
    - 继承自 BaseOrgan 以保持接口兼容
    """

    def __init__(
        self,
        name: str,
        container_image: str,
        capabilities: List[str],
        value_dimension: str = None,
        description: str = ""
    ):
        """初始化肢体

        Args:
            name: 肢体名称
            container_image: Docker 镜像名称
            capabilities: 此肢体提供的能力列表
            value_dimension: 对应的价值维度
            description: 肢体描述
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
        """挂载肢体（启动 Docker 容器）

        Returns:
            (是否成功, 消息)
        """
        if self._is_mounted:
            return True, "肢体已挂载"

        try:
            # TODO: 实现 Docker 容器启动
            # container_id = start_container(self.container_image)
            # self._container_id = container_id
            # self._is_mounted = True
            self._is_mounted = True  # 模拟
            return True, f"肢体 {self.name} 挂载成功（模拟）"
        except Exception as e:
            return False, f"挂载失败: {str(e)}"

    def unmount(self) -> Tuple[bool, str]:
        """卸载肢体（停止 Docker 容器）

        Returns:
            (是否成功, 消息)
        """
        if not self._is_mounted:
            return True, "肢体未挂载"

        try:
            # TODO: 实现 Docker 容器停止
            # stop_container(self._container_id)
            # self._container_id = None
            # self._is_mounted = False
            self._is_mounted = False  # 模拟
            return True, f"肢体 {self.name} 卸载成功（模拟）"
        except Exception as e:
            return False, f"卸载失败: {str(e)}"

    def is_mounted(self) -> bool:
        """检查肢体是否已挂载"""
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
            message=f"肢体 {self.name} 不支持能力 {capability_name}",
            error=f"Capability not supported: {capability_name}"
        )


# 向后兼容：保留旧名称
MountedOrgan = Limb


__all__ = [
    "Limb",
    "CapabilityResult",
    "MountedOrgan",  # 向后兼容
]
