"""Capability Gap Detector - 能力缺口检测器

连接探索和进化之间的关键环节：
1. 从探索行为中识别"想要做但做不到"的事情
2. 分析当前能力边界
3. 生成进化需求

这是"好奇心 → 探索 → 发现缺口 → 进化"循环的核心。
"""
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import re

from common.logger import get_logger

logger = get_logger(__name__)


class GapType(Enum):
    """缺口类型"""
    TOOL_MISSING = "tool_missing"          # 缺少特定工具
    KNOWLEDGE_MISSING = "knowledge_missing" # 缺少知识
    SKILL_MISSING = "skill_missing"         # 缺少技能
    CAPABILITY_LIMITED = "capability_limited" # 能力受限


@dataclass
class CapabilityGap:
    """能力缺口

    描述"想要做但做不到"的事情
    """
    gap_type: GapType
    description: str                  # 缺口描述
    missing_capability: str           # 缺失的能力
    priority: float                   # 优先级 [0,1]
    context: Dict[str, Any] = field(default_factory=dict)
    suggested_solution: Optional[str] = None  # 建议的解决方案


@dataclass
class ExplorationDiscovery:
    """探索发现

    探索过程中发现的新信息
    """
    topic: str                         # 探索的主题
    discovered_needs: List[str]        # 发现的需求
    missing_tools: List[str]           # 缺少的工具
    interesting_capabilities: List[str] # 发现的有用能力
    novelty: float                     # 新颖度


class CapabilityGapDetector:
    """能力缺口检测器

    分析行为和结果，识别能力缺口，驱动进化。

    工作流程：
    1. 监控探索行为
    2. 分析"尝试但失败"的情况
    3. 识别"需要但缺少"的能力
    4. 生成进化需求
    """

    # 兴趣领域与所需能力的映射
    DOMAIN_CAPABILITIES = {
        "图像处理": ["image_edit", "image_crop", "image_filter", "photoshop", "gimp"],
        "视频处理": ["video_edit", "video_convert", "ffmpeg", "video_crop"],
        "数据分析": ["pandas", "excel", "csv", "data_analysis", "statistics"],
        "网页操作": ["browser", "selenium", "scrapy", "web_automation"],
        "API调用": ["http", "api", "requests", "rest", "graphql"],
        "文档处理": ["pdf", "word", "docx", "text_processing"],
        "音频处理": ["audio_edit", "ffmpeg", "speech_to_text"],
        "代码执行": ["code_execution", "sandbox", "docker"],
        "机器学习": ["sklearn", "tensorflow", "pytorch", "ml"],
        "数据库": ["sql", "database", "query", "mongodb"],
    }

    # 探索主题到领域的映射
    TOPIC_TO_DOMAIN = {
        # 科学探索
        "science": "数据分析",
        "mathematics": "数据分析",
        "psychology": "数据分析",

        # 技术探索
        "technology": "API调用",
        "emerging_concepts": "API调用",

        # 创意探索
        "art": "图像处理",
        "creative": "图像处理",

        # 社会探索
        "sociology": "数据分析",
        "economics": "数据分析",
    }

    def __init__(self, config: Dict[str, Any] = None):
        """初始化能力缺口检测器

        Args:
            config: 配置
        """
        self.config = config or {}

        # 检测历史
        self._detection_history: List[Dict[str, Any]] = []

        # 已知的能力集合（从器官管理器获取）
        self._known_capabilities: Set[str] = set()

        # 探索发现缓存
        self._exploration_discoveries: List[ExplorationDiscovery] = []

        # 阈值
        self._gap_priority_threshold = 0.5
        self._novelty_threshold = 0.3

    def update_known_capabilities(self, capabilities: Set[str]):
        """更新已知能力集合

        Args:
            capabilities: 当前拥有的能力集合
        """
        self._known_capabilities = capabilities

    def detect_from_exploration(
        self,
        exploration_action: Dict[str, Any],
        exploration_result: Dict[str, Any],
        state: Dict[str, Any]
    ) -> List[CapabilityGap]:
        """从探索行为中检测能力缺口

        Args:
            exploration_action: 探索行动
            exploration_result: 探索结果
            state: 当前状态

        Returns:
            检测到的能力缺口列表
        """
        gaps = []

        # 提取探索主题
        topic = exploration_action.get("params", {}).get("topic", "")
        depth = exploration_action.get("params", {}).get("depth", "medium")

        # 分析探索结果
        success = exploration_result.get("success", True)
        novelty = exploration_result.get("novelty", 0.5)
        learned = exploration_result.get("learned", "")

        # 1. 如果探索失败，可能是因为缺少能力
        if not success:
            error_msg = exploration_result.get("error", "")
            gap = self._analyze_failure(topic, error_msg, state)
            if gap:
                gaps.append(gap)

        # 2. 如果探索成功但新颖度低，可能需要更深入的探索工具
        elif novelty < self._novelty_threshold:
            # 低新颖度可能意味着当前能力不足以深入
            domain = self._map_topic_to_domain(topic)
            if domain:
                required_caps = self.DOMAIN_CAPABILITIES.get(domain, [])
                missing_caps = [c for c in required_caps if c not in self._known_capabilities]

                if missing_caps:
                    gaps.append(CapabilityGap(
                        gap_type=GapType.CAPABILITY_LIMITED,
                        description=f"深入探索 {domain} 需要更多工具",
                        missing_capability=domain,
                        priority=0.6,
                        context={"missing_tools": missing_caps}
                    ))

        # 3. 从探索结果中提取潜在需求
        potential_needs = self._extract_needs_from_result(learned, topic)
        for need in potential_needs:
            if need not in self._known_capabilities:
                gaps.append(CapabilityGap(
                    gap_type=GapType.TOOL_MISSING,
                    description=f"探索发现需要: {need}",
                    missing_capability=need,
                    priority=0.5,
                    suggested_solution=self._suggest_solution_for_need(need)
                ))

        # 记录探索发现
        discovery = ExplorationDiscovery(
            topic=topic,
            discovered_needs=[g.missing_capability for g in gaps],
            missing_tools=[g.missing_capability for g in gaps if g.gap_type == GapType.TOOL_MISSING],
            interesting_capabilities=list(self._known_capabilities),
            novelty=novelty
        )
        self._exploration_discoveries.append(discovery)

        return gaps

    def detect_from_drive_signals(
        self,
        drive_signals: Dict[str, Any],
        state: Dict[str, Any]
    ) -> List[CapabilityGap]:
        """从驱动力信号中检测能力缺口

        当强烈的好奇心指向某个领域，但缺少相应能力时，
        生成能力缺口。

        Args:
            drive_signals: 驱动力信号
            state: 当前状态

        Returns:
            检测到的能力缺口列表
        """
        gaps = []

        # 检查好奇心驱动力
        curiosity = drive_signals.get("curiosity")
        if curiosity and curiosity.intensity > 0.7:
            # 强烈的好奇心
            boredom = state.get("boredom", 0.0)

            # 如果同时无聊且好奇，说明"想探索但没什么可探索的"
            # 这可能需要新的能力来开辟新的探索领域
            if boredom > 0.5:
                # 分析最近探索的主题
                recent_topics = [d.topic for d in self._exploration_discoveries[-5:]]

                # 如果最近探索的主题很少，说明需要新的探索工具
                if len(set(recent_topics)) < 3:
                    # 建议获取新的探索能力
                    suggested_domains = self._suggest_new_domains(self._known_capabilities)

                    for domain in suggested_domains:
                        gaps.append(CapabilityGap(
                            gap_type=GapType.TOOL_MISSING,
                            description=f"开辟新探索领域: {domain}",
                            missing_capability=domain,
                            priority=0.7,
                            suggested_solution=f"获取 {domain} 相关工具"
                        ))

        # 检查胜任力驱动力
        competence = drive_signals.get("competence")
        if competence and competence.intensity > 0.7:
            # 强烈的胜任需求，可能需要新的能力来掌握
            context = competence.context or {}
            target_domain = context.get("target_domain")

            if target_domain and target_domain not in self._known_capabilities:
                gaps.append(CapabilityGap(
                    gap_type=GapType.SKILL_MISSING,
                    description=f"想要掌握: {target_domain}",
                    missing_capability=target_domain,
                    priority=0.8,
                    suggested_solution=f"学习/获取 {target_domain} 能力"
                ))

        return gaps

    def _analyze_failure(
        self,
        topic: str,
        error_msg: str,
        state: Dict[str, Any]
    ) -> Optional[CapabilityGap]:
        """分析失败原因，识别能力缺口

        Args:
            topic: 探索主题
            error_msg: 错误消息
            state: 当前状态

        Returns:
            能力缺口，如果能识别
        """
        # 分析错误消息
        error_lower = error_msg.lower()

        # 常见错误模式
        if "no tool" in error_lower or "tool not found" in error_lower:
            # 缺少工具
            return CapabilityGap(
                gap_type=GapType.TOOL_MISSING,
                description=f"探索 {topic} 失败: 缺少必要工具",
                missing_capability=topic,
                priority=0.7
            )

        if "permission" in error_lower or "access" in error_lower:
            # 权限问题
            return CapabilityGap(
                gap_type=GapType.CAPABILITY_LIMITED,
                description=f"探索 {topic} 失败: 权限不足",
                missing_capability=f"{topic}_access",
                priority=0.5
            )

        if "unknown" in error_lower or "not found" in error_lower:
            # 可能需要搜索/发现能力
            return CapabilityGap(
                gap_type=GapType.KNOWLEDGE_MISSING,
                description=f"探索 {topic} 失败: 知识不足",
                missing_capability=f"{topic}_knowledge",
                priority=0.6
            )

        return None

    def _map_topic_to_domain(self, topic: str) -> Optional[str]:
        """将探索主题映射到领域

        Args:
            topic: 探索主题

        Returns:
            领域名称
        """
        topic_lower = topic.lower()

        # 直接匹配
        for domain, keywords in self.DOMAIN_CAPABILITIES.items():
            if any(kw in topic_lower for kw in keywords):
                return domain

        # 使用预定义映射
        for key, domain in self.TOPIC_TO_DOMAIN.items():
            if key in topic_lower:
                return domain

        return None

    def _extract_needs_from_result(self, result_text: str, topic: str) -> List[str]:
        """从探索结果中提取潜在需求

        Args:
            result_text: 探索结果文本
            topic: 探索主题

        Returns:
            潜在需求列表
        """
        needs = []

        # 常见需求模式
        patterns = [
            r"需要?(.{1,10})工具",
            r"缺少?(.{1,10})能力",
            r"如果?有?(.{1,10})就好了",
            r"应该?有?(.{1,10})功能",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, result_text)
            needs.extend(matches)

        # 去重并过滤
        unique_needs = list(set(needs))
        return [n for n in unique_needs if len(n) > 1]

    def _suggest_solution_for_need(self, need: str) -> Optional[str]:
        """为需求建议解决方案

        Args:
            need: 需求描述

        Returns:
            解决方案建议
        """
        # 映射到进化系统的软件仓库
        need_lower = need.lower()

        suggestions = {
            "图像": "吞噬图像处理软件 (GIMP/Photoshop)",
            "视频": "吞噬视频处理软件 (FFmpeg)",
            "数据": "生成或吞噬数据处理工具",
            "网页": "吞噬浏览器工具",
            "api": "生成API调用肢体",
        }

        for keyword, suggestion in suggestions.items():
            if keyword in need_lower:
                return suggestion

        return "尝试自主生成或外部吞噬"

    def _suggest_new_domains(self, known_capabilities: Set[str]) -> List[str]:
        """建议新的探索领域

        基于当前已知能力，建议尚未探索的领域。

        Args:
            known_capabilities: 已知能力集合

        Returns:
            建议的领域列表
        """
        all_domains = set(self.DOMAIN_CAPABILITIES.keys())

        # 找出没有对应能力的领域
        missing_domains = []
        for domain in all_domains:
            caps = self.DOMAIN_CAPABILITIES[domain]
            # 如果没有任何相关能力，说明这个领域是新的
            if not any(cap in known_capabilities for cap in caps):
                missing_domains.append(domain)

        # 返回优先级最高的几个
        priority_order = ["数据分析", "图像处理", "视频处理", "网页操作", "API调用"]
        ordered = [d for d in priority_order if d in missing_domains]

        return ordered[:3]

    def rank_gaps(self, gaps: List[CapabilityGap]) -> List[CapabilityGap]:
        """对能力缺口排序

        Args:
            gaps: 能力缺口列表

        Returns:
            排序后的缺口列表
        """
        # 综合考虑优先级、类型、新颖度
        def score_gap(gap: CapabilityGap) -> float:
            score = gap.priority

            # 工具缺失的权重更高
            if gap.gap_type == GapType.TOOL_MISSING:
                score *= 1.2

            return score

        return sorted(gaps, key=score_gap, reverse=True)

    def gaps_to_evolution_needs(self, gaps: List[CapabilityGap]) -> List[str]:
        """将能力缺口转换为进化需求

        Args:
            gaps: 能力缺口列表

        Returns:
            进化需求描述列表
        """
        needs = []

        for gap in gaps:
            if gap.gap_type == GapType.TOOL_MISSING:
                needs.append(f"获取 {gap.missing_capability} 工具")
            elif gap.gap_type == GapType.CAPABILITY_LIMITED:
                needs.append(f"增强 {gap.missing_capability} 能力")
            elif gap.gap_type == GapType.SKILL_MISSING:
                needs.append(f"学习 {gap.missing_capability} 技能")
            elif gap.gap_type == GapType.KNOWLEDGE_MISSING:
                needs.append(f"获取 {gap.missing_capability} 知识")

        return needs

    def get_exploration_summary(self) -> Dict[str, Any]:
        """获取探索活动摘要

        Returns:
            摘要信息
        """
        if not self._exploration_discoveries:
            return {
                "total_explorations": 0,
                "domains_explored": [],
                "most_frequent_gaps": []
            }

        all_topics = [d.topic for d in self._exploration_discoveries]
        all_missing = []

        for d in self._exploration_discoveries:
            all_missing.extend(d.missing_tools)

        # 统计最常出现的缺口
        from collections import Counter
        gap_counter = Counter(all_missing)

        return {
            "total_explorations": len(self._exploration_discoveries),
            "domains_explored": list(set(all_topics)),
            "most_frequent_gaps": gap_counter.most_common(5),
            "recent_novelty": [d.novelty for d in self._exploration_discoveries[-5:]],
        }


def create_capability_gap_detector(config: Dict[str, Any] = None) -> CapabilityGapDetector:
    """创建能力缺口检测器

    Args:
        config: 配置

    Returns:
        CapabilityGapDetector 实例
    """
    return CapabilityGapDetector(config)
