"""Organ Manager - 器官管理器

管理所有内部器官和肢体，提供统一的调用接口。

命名说明：
- 器官 (organs/) = 自身进化产生的内部能力
- 肢体 (limbs/) = 外部工具吞噬后挂载的
"""
from typing import Dict, Any, List, Optional, Tuple
from .base_organ import BaseOrgan, CapabilityResult

# 尝试从 .limbs 导入，如果不可用则使用向后兼容的 MountedOrgan
try:
    from .limbs import Limb
    MountedOrgan = Limb
except ImportError:
    from .base_organ import MountedOrgan

# 从 axiology.drives 导入驱动力相关（新架构）
from axiology.drives import DriveSignal, CuriosityDrive, CompetenceDrive, HomeostasisDrive, AttachmentDrive, SafetyDrive


class OrganManager:
    """器官管理器

    负责管理所有器官和肢体，提供统一的接口：
    1. 获取驱动力信号（给 LLM）
    2. 执行能力（路由到具体肢体或技能）
    3. 管理肢体的生命周期
    """

    def __init__(self):
        """初始化器官管理器"""
        # 内置驱动力（新架构：从 axiology.drives 导入，5维价值系统）
        self._builtin_organs = {
            "curiosity": CuriosityDrive(),
            "competence": CompetenceDrive(),
            "homeostasis": HomeostasisDrive(),
            "attachment": AttachmentDrive(),
            "safety": SafetyDrive(),
        }

        # 肢体（提供驱动力 + 具体能力）
        self._limbs: Dict[str, MountedOrgan] = {}

    # ==================== 驱动力信号 ====================

    def get_all_drive_signals(self, state: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, DriveSignal]:
        """获取所有器官的驱动力信号

        Args:
            state: 当前状态
            context: 当前上下文

        Returns:
            器官名称 -> 驱动力信号
        """
        signals = {}

        # 内部器官的信号
        for name, organ in self._builtin_organs.items():
            if organ.enabled:
                signals[name] = organ.generate_drive_signal(state, context)

        # 肢体不生成驱动力信号（它们只是工具，不产生"想要"）
        # 肢体由内部器官根据需要来调用

        return signals

    def get_dominant_drive(self, state: Dict[str, Any], context: Dict[str, Any]) -> Optional[DriveSignal]:
        """获取最强的驱动力信号

        Args:
            state: 当前状态
            context: 当前上下文

        Returns:
            最强的驱动力信号
        """
        signals = self.get_all_drive_signals(state, context)
        if not signals:
            return None

        # 按优先级排序
        sorted_signals = sorted(
            signals.items(),
            key=lambda x: x[1].priority,
            reverse=True
        )
        return sorted_signals[0][1]

    def format_drives_for_llm(self, state: Dict[str, Any], context: Dict[str, Any]) -> str:
        """格式化为给 LLM 的提示文本

        Args:
            state: 当前状态
            context: 当前上下文

        Returns:
            格式化的驱动力描述
        """
        signals = self.get_all_drive_signals(state, context)

        # 按强度排序
        sorted_signals = sorted(
            signals.items(),
            key=lambda x: x[1].intensity,
            reverse=True
        )

        lines = ["## 当前驱动力状态", ""]

        for name, signal in sorted_signals:
            lines.append(f"- {signal.to_prompt()}")

        # 找出最强的驱动力
        if sorted_signals:
            dominant = sorted_signals[0][1]
            if dominant.intensity > 0.5:
                lines.append("")
                lines.append(f"**当前最强烈的驱动力：{dominant.name}**")

        return "\n".join(lines)

    # ==================== 能力执行 ====================

    def has_capability(self, capability_name: str) -> bool:
        """检查是否有某个能力

        Args:
            capability_name: 能力名称

        Returns:
            是否有此能力
        """
        # 检查肢体
        for limb in self._limbs.values():
            if limb.is_mounted() and limb.has_capability(capability_name):
                return True
        return False

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
            执行结果
        """
        # 先找肢体
        for limb in self._limbs.values():
            if limb.is_mounted() and limb.has_capability(capability_name):
                return limb.execute_capability(capability_name, **kwargs)

        return CapabilityResult(
            success=False,
            message=f"没有找到能力: {capability_name}",
            error=f"Capability not found: {capability_name}"
        )

    def list_all_capabilities(self) -> List[str]:
        """列出所有可用能力

        Returns:
            能力名称列表
        """
        capabilities = []
        for limb in self._limbs.values():
            if limb.is_mounted():
                capabilities.extend(limb.get_capabilities())
        return capabilities

    # ==================== 肢体管理 ====================

    def mount_limb(self, limb: MountedOrgan) -> Tuple[bool, str]:
        """挂载一个肢体

        Args:
            limb: 要挂载的肢体

        Returns:
            (是否成功, 消息)
        """
        if limb.name in self._limbs:
            return False, f"肢体 {limb.name} 已存在"

        success, message = limb.mount()
        if success:
            self._limbs[limb.name] = limb
        return success, message

    def unmount_limb(self, limb_name: str) -> Tuple[bool, str]:
        """卸载一个肢体

        Args:
            limb_name: 肢体名称

        Returns:
            (是否成功, 消息)
        """
        if limb_name not in self._limbs:
            return False, f"肢体 {limb_name} 不存在"

        limb = self._limbs[limb_name]
        success, message = limb.unmount()
        if success:
            del self._limbs[limb_name]
        return success, message

    def get_mounted_limbs(self) -> List[str]:
        """获取已挂载的肢体列表

        Returns:
            肢体名称列表
        """
        return [
            name for name, limb in self._limbs.items()
            if limb.is_mounted()
        ]

    # ==================== 向后兼容 ====================

    def mount_organ(self, organ: MountedOrgan) -> Tuple[bool, str]:
        """挂载一个器官 (向后兼容，实际挂载的是肢体)

        Args:
            organ: 要挂载的器官（实际是肢体）

        Returns:
            (是否成功, 消息)
        """
        return self.mount_limb(organ)

    def unmount_organ(self, organ_name: str) -> Tuple[bool, str]:
        """卸载一个器官 (向后兼容)

        Args:
            organ_name: 器官名称

        Returns:
            (是否成功, 消息)
        """
        return self.unmount_limb(organ_name)

    def get_mounted_organs(self) -> List[str]:
        """获取已挂载的器官列表 (向后兼容)

        Returns:
            器官名称列表
        """
        return self.get_mounted_limbs()

    def get_organ_info(self, organ_name: str) -> Optional[Dict[str, Any]]:
        """获取器官信息

        Args:
            organ_name: 器官名称

        Returns:
            器官信息
        """
        # 内部器官
        if organ_name in self._builtin_organs:
            organ = self._builtin_organs[organ_name]
            signal = organ.get_last_signal()
            return {
                "name": organ.name,
                "type": "builtin",
                "value_dimension": organ.value_dimension,
                "enabled": organ.enabled,
                "last_signal": signal.to_prompt() if signal else None,
            }

        # 肢体
        if organ_name in self._limbs:
            limb = self._limbs[organ_name]
            signal = limb.get_last_signal()
            return {
                "name": limb.name,
                "type": "limb",
                "value_dimension": limb.value_dimension,
                "enabled": limb.enabled,
                "is_mounted": limb.is_mounted(),
                "container_image": limb.container_image,
                "capabilities": limb.get_capabilities(),
                "last_signal": signal.to_prompt() if signal else None,
            }

        return None

    # ==================== 内置器官访问 ====================

    def get_builtin_organ(self, name: str) -> Optional[BaseOrgan]:
        """获取内置器官

        Args:
            name: 器官名称

        Returns:
            器官实例
        """
        return self._builtin_organs.get(name)

    @property
    def curiosity(self) -> CuriosityDrive:
        """获取好奇心驱动力"""
        return self._builtin_organs["curiosity"]

    @property
    def competence(self) -> CompetenceDrive:
        """获取胜任力驱动力"""
        return self._builtin_organs["competence"]

    @property
    def homeostasis(self) -> HomeostasisDrive:
        """获取稳态驱动力"""
        return self._builtin_organs["homeostasis"]

    @property
    def attachment(self) -> AttachmentDrive:
        """获取依恋驱动力"""
        return self._builtin_organs["attachment"]

    @property
    def safety(self) -> SafetyDrive:
        """获取安全驱动力"""
        return self._builtin_organs["safety"]

    def record_interaction(self, positive: bool = True):
        """记录交互（委托给依恋器官）"""
        self.attachment.record_interaction(positive)

    def record_exploration(self, topic: str, novelty: float):
        """记录探索（委托给好奇心器官）"""
        if hasattr(self.curiosity, '_explored_topics'):
            self.curiosity._explored_topics.add(topic)

    def record_achievement(self, skill: str):
        """记录成就（委托给胜任力器官）"""
        self.competence.record_achievement(skill)
