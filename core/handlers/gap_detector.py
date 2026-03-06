"""GapDetectorMixin - 能力缺口检测混入

从 LifeLoop 拆分出来的能力缺口检测方法。
负责从多个来源检测能力缺口：用户请求、驱动力信号、探索历史。

设计原则：
- 使用混入模式（Mixin），可以被 LifeLoop 继承
- 保持与原始代码完全相同的行为
- 支持单元测试
"""

from typing import Dict, Any, List, Optional

from common.models import ActionType
from common.logger import get_logger

logger = get_logger(__name__)


class GapDetectorMixin:
    """能力缺口检测混入

    提供：
    - _identify_evolution_need: 识别进化需求
    - _identify_user_request_gaps: 从用户请求识别缺口
    - _identify_drive_signal_gaps: 从驱动力信号识别缺口
    - _identify_exploration_gaps: 从探索历史识别缺口
    - _check_action_capability: 检查执行行为所需能力

    使用方式：
        class LifeLoop(GapDetectorMixin):
            ...
    """

    def _identify_evolution_need(self, context: Dict[str, Any]) -> Optional[str]:
        """识别进化需求

        从多个来源识别能力缺口：
        1. 用户请求的显式需求
        2. 探索行为发现的能力缺口
        3. 驱动力信号（好奇心/胜任力）暗示的需求

        Args:
            context: 当前上下文

        Returns:
            需求描述，如果没有则返回 None
        """
        # 检查 gap_detector 是否可用
        if not hasattr(self, 'gap_detector') or not self.gap_detector:
            return None

        all_gaps = []

        # 1. 从用户请求中分析需求
        user_gaps = self._identify_user_request_gaps(context)
        all_gaps.extend(user_gaps)

        # 2. 从驱动力信号中分析需求
        drive_gaps = self._identify_drive_signal_gaps(context)
        all_gaps.extend(drive_gaps)

        # 3. 从探索历史中分析需求
        exploration_gaps = self._identify_exploration_gaps(context)
        all_gaps.extend(exploration_gaps)

        # 4. 更新能力缺口检测器的已知能力
        if hasattr(self, 'organ_manager') and self.organ_manager:
            known_capabilities = self.organ_manager.list_all_capabilities()
            self.gap_detector.update_known_capabilities(set(known_capabilities))

        # 5. 使用检测器分析缺口并排序
        if all_gaps:
            ranked_gaps = self.gap_detector.rank_gaps(all_gaps)
            if ranked_gaps:
                # 返回优先级最高的缺口作为进化需求
                top_gap = ranked_gaps[0]
                logger.info(f"检测到能力缺口: {top_gap.description} (优先级: {top_gap.priority:.2f})")
                return top_gap.missing_capability

        return None

    def _identify_user_request_gaps(self, context: Dict[str, Any]) -> List:
        """从用户请求中识别能力缺口

        Args:
            context: 当前上下文

        Returns:
            能力缺口列表
        """
        from core.capability_gap_detector import CapabilityGap, GapType

        gaps = []
        observations = context.get("observations", [])

        for obs in observations:
            if hasattr(obs, 'type') and obs.type == "user_chat":
                if hasattr(obs, 'payload'):
                    msg = obs.payload.get("message", "")
                    msg_lower = msg.lower()

                    # 分析用户请求中的关键词
                    if any(kw in msg_lower for kw in ["图片", "图像", "裁剪", "滤镜", "ps"]):
                        gaps.append(CapabilityGap(
                            gap_type=GapType.TOOL_MISSING,
                            description="用户请求图像处理能力",
                            missing_capability="图像处理",
                            priority=0.9  # 用户请求优先级高
                        ))
                    elif any(kw in msg_lower for kw in ["表格", "excel", "数据透视", "图表"]):
                        gaps.append(CapabilityGap(
                            gap_type=GapType.TOOL_MISSING,
                            description="用户请求数据处理能力",
                            missing_capability="数据处理",
                            priority=0.9
                        ))
                    elif any(kw in msg_lower for kw in ["浏览器", "爬虫", "网页自动化"]):
                        gaps.append(CapabilityGap(
                            gap_type=GapType.TOOL_MISSING,
                            description="用户请求网页操作能力",
                            missing_capability="网页操作",
                            priority=0.9
                        ))
                    elif any(kw in msg_lower for kw in ["视频", "剪辑", "转码"]):
                        gaps.append(CapabilityGap(
                            gap_type=GapType.TOOL_MISSING,
                            description="用户请求视频处理能力",
                            missing_capability="视频处理",
                            priority=0.9
                        ))

        return gaps

    def _identify_drive_signal_gaps(self, context: Dict[str, Any]) -> List:
        """从驱动力信号中识别能力缺口

        当强烈的好奇心/胜任力指向某个领域，但缺少相应能力时，
        生成能力缺口。

        Args:
            context: 当前上下文

        Returns:
            能力缺口列表
        """
        gaps = []

        # 检查 gap_detector 是否可用
        if not hasattr(self, 'gap_detector') or not self.gap_detector:
            return gaps

        # 使用能力缺口检测器分析驱动力信号
        drive_signals = context.get("drive_signals", {})
        drive_state = {
            "boredom": self.fields.get("boredom"),
            "energy": self.fields.get("energy"),
            "stress": self.fields.get("stress"),
            "curiosity": self.fields.get("curiosity"),
        }

        detected_gaps = self.gap_detector.detect_from_drive_signals(
            drive_signals, drive_state
        )
        gaps.extend(detected_gaps)

        return gaps

    def _identify_exploration_gaps(self, context: Dict[str, Any]) -> List:
        """从探索历史中识别能力缺口

        分析最近的探索行为，找出"尝试但失败"或"需要但缺少"的能力。

        Args:
            context: 当前上下文

        Returns:
            能力缺口列表
        """
        from core.capability_gap_detector import CapabilityGap, GapType

        gaps = []

        # 检查 gap_detector 是否可用
        if not hasattr(self, 'gap_detector') or not self.gap_detector:
            return gaps

        # 从最近的 actions 中找到 EXPLORE 类型的行为
        recent_actions = context.get("recent_actions", [])

        for action in recent_actions[-10:]:  # 只看最近10个
            if hasattr(action, 'type') and action.type == "EXPLORE":
                # 检查这个探索是否产生了能力缺口
                exploration_topic = action.params.get("topic", "")

                # 如果探索主题涉及某个领域，但系统缺少该领域的能力
                domain = self.gap_detector._map_topic_to_domain(exploration_topic)
                if domain and hasattr(self, 'organ_manager'):
                    known_capabilities = set(self.organ_manager.list_all_capabilities())
                    required_caps = self.gap_detector.DOMAIN_CAPABILITIES.get(domain, [])

                    # 检查是否缺少关键能力
                    has_any = any(cap.lower() in str(known_capabilities).lower() for cap in required_caps)

                    if not has_any:
                        gaps.append(CapabilityGap(
                            gap_type=GapType.TOOL_MISSING,
                            description=f"探索 {exploration_topic} 发现缺少 {domain} 能力",
                            missing_capability=domain,
                            priority=0.6
                        ))

        return gaps

    def _check_action_capability(self, action, context: Dict[str, Any]) -> Optional[Any]:
        """检查执行行为所需的能力

        这是能力缺口检测的正确定位：在行为执行前检查，
        而不是作为自主行为的驱动源。

        Args:
            action: 待执行的行为
            context: 当前上下文

        Returns:
            如果缺少能力，返回 CapabilityGap；否则返回 None
        """
        from core.capability_gap_detector import CapabilityGap, GapType

        # 获取当前已知能力
        known_capabilities = set()
        if hasattr(self, 'organ_manager') and self.organ_manager:
            try:
                known_capabilities = set(self.organ_manager.list_all_capabilities())
            except Exception:
                pass

        # 根据 action 类型检查所需能力
        required_capability = None

        if action.type == ActionType.USE_TOOL:
            # 工具使用需要对应工具能力
            tool_name = action.params.get("tool", "")
            if tool_name:
                # 检查是否有这个工具
                tool_caps = ["tool_" + tool_name.lower(), tool_name.lower()]
                has_tool = any(cap in known_capabilities for cap in tool_caps)
                if not has_tool:
                    required_capability = tool_name

        elif action.type == ActionType.EXPLORE:
            # 探索行为可能需要特定领域能力
            topic = action.params.get("topic", "")
            if topic and hasattr(self, 'gap_detector') and self.gap_detector:
                domain = self.gap_detector._map_topic_to_domain(topic)
                if domain:
                    domain_caps = self.gap_detector.DOMAIN_CAPABILITIES.get(domain, [])
                    has_domain_cap = any(
                        cap.lower() in str(known_capabilities).lower()
                        for cap in domain_caps
                    )
                    if not has_domain_cap and domain_caps:
                        required_capability = domain

        # 如果检测到能力缺口，返回 CapabilityGap
        if required_capability:
            return CapabilityGap(
                gap_type=GapType.TOOL_MISSING,
                description=f"执行 {action.type.value} 需要能力: {required_capability}",
                missing_capability=required_capability,
                priority=0.7,
                context={
                    "action_type": action.type.value,
                    "action_params": action.params,
                }
            )

        return None
