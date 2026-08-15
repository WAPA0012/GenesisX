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


class DockerLimb(BaseOrgan):
    """Docker 肢体基类 (P5-13 澄清: 原 class Limb 与 unified_organ.py 的 Limb 同名混淆)

    重命名为 DockerLimb 以区分：
    - DockerLimb (本类): 运行在 Docker 容器中的外部工具
    - Limb (unified_organ.py): LLM 动态生成的代码模块

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

        P5-14: Docker 集成未实现。原代码"模拟挂载成功 + execute 恒失败"语义不一致，
        会让未来调试者困惑（挂载成功了为什么执行失败？）。现统一返回未实现。

        Returns:
            (是否成功, 消息)
        """
        if self._is_mounted:
            return True, "肢体已挂载"

        # TODO: 实现 Docker 容器启动（P5-14 placeholder）
        # container_id = start_container(self.container_image)
        # self._container_id = container_id
        # self._is_mounted = True
        return False, f"Docker 集成未实现（P5-14 placeholder），肢体 {self.name} 无法挂载"

    def unmount(self) -> Tuple[bool, str]:
        """卸载肢体（停止 Docker 容器）

        P5-14: 同 mount，Docker 集成未实现。

        Returns:
            (是否成功, 消息)
        """
        if not self._is_mounted:
            return True, "肢体未挂载"

        # TODO: 实现 Docker 容器停止（P5-14 placeholder）
        # stop_container(self._container_id)
        # self._container_id = None
        # self._is_mounted = False
        self._is_mounted = False  # 状态清理（即便 Docker 未实现，也要保持状态一致）
        return False, f"Docker 集成未实现（P5-14 placeholder），肢体 {self.name} 容器未真停止"

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
Limb = DockerLimb  # P5-13: 外部调用方仍可用 limbs.Limb
MountedOrgan = DockerLimb


__all__ = [
    "DockerLimb",
    "Limb",  # 向后兼容别名
    "CapabilityResult",
    "MountedOrgan",  # 向后兼容
]
