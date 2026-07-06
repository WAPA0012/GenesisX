"""Base Organ - 器官基类

器官系统负责提供"我能做什么"的执行能力。

注意：驱动力信号生成已迁移到 axiology.drives 模块。
    - 驱动力（"我想要什么"）→ axiology.drives
    - 器官（"我能做什么"）→ organs

命名说明：
- 器官 (organs/) = 自身进化产生的内部能力，完全可控
- 肢体 (limbs/) = 外部工具吞噬后挂载的，像"假肢"或"外骨骼"

修复：使用 common.models.CapabilityResult 统一定义，避免重复。

P0-1/P5-15 修复（2026-07）：新增 LLM 思考的"结构化动作决策"模板方法。
    6 个内置器官的 _propose_actions_with_llm 原本各自重复"关键词解析 LLM 叙事"
    的脆弱逻辑（中文关键词失配 → fallback 到规则模式 → 产出 REFLECT/THINK
    → 系统陷入反思死循环、mood 锁死归零）。现抽到基类统一为：
      结构化解析（【动作:XXX】标记）→ 关键词 fallback → 规则模式兜底
    让 LLM 真正决定动作类型，关键词匹配降级为二级兜底。
"""
import os
import re
from typing import List, Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod
from common.models import Action, CapabilityResult
from common.logger import get_logger

logger = get_logger(__name__)

# 环境变量灰度开关（沿用 ORGAN_PARALLEL_MODE/LLM_MODE 同款约定，无前缀大写）
# "1"（默认）= 启用结构化动作决策；"0" = 回退到原关键词逻辑（保命开关）
# 注意：用函数惰性读取而非模块级常量，避免 import 顺序早于 .env 加载导致读到空值。
def _structured_actions_enabled() -> bool:
    return os.environ.get("STRUCTURED_ORGAN_ACTIONS", "1") == "1"

# 结构化动作标记的正则。【动作:EXPLORE】 / 【主题:量子计算】
# 容错：允许全角/半角冒号、忽略首尾空白、动作类型大小写不敏感。
_ACTION_RE = re.compile(r"【\s*动作\s*[:：]\s*([A-Z_]+)\s*】", re.IGNORECASE)
_TOPIC_RE = re.compile(r"【\s*主题\s*[:：]\s*(.+?)\s*】")
# 思考正文：取第一个【动作】标记之前的自然语言部分（避免污染记忆评估）
_THOUGHT_BODY_RE = re.compile(r"^(.*?)【\s*动作", re.DOTALL)


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

    # ==================== LLM 思考模板方法（P0-1/P5-15 修复）====================

    def _propose_actions_with_llm_template(
        self,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[Action]:
        """LLM 思考的模板方法（6 内置器官共用）。

        统一三步：构建提示 → 调 LLM → 解析动作。
        解析优先级：
          1. 结构化标记（【动作:XXX】）—— LLM 真正决策
          2. 关键词 fallback（_keyword_fallback_actions）—— 子类提供
          3. 规则模式（_propose_actions_impl）—— 子类提供
        env STRUCTURED_ORGAN_ACTIONS=0 时跳过第 1 步，直接走关键词（保命回退）。

        子类需提供：
          - _build_thinking_prompt(state, context) -> str
          - _llm_session（None 时直接走规则模式）
          - _keyword_fallback_actions(thought, state, context) -> List[Action]（可选）
          - _propose_actions_impl(state, context) -> List[Action]
        """
        # 无 LLM 会话时直接走规则模式（保持原 propose_actions 分发语义）
        llm_session = getattr(self, "_llm_session", None)
        if llm_session is None:
            return self._propose_actions_impl(state, context)

        # 步骤 1：构建提示并调 LLM
        prompt = self._build_thinking_prompt(state, context)
        # P0-1 残留修复：格式要求前置（推理模型对开头指令更敏感）
        prompt = self._format_structured_output_prompt_prefix() + prompt
        try:
            thought = llm_session.think(prompt)
        except Exception as e:
            logger.warning(f"器官 {self.name} LLM think 异常，降级规则模式: {e}")
            return self._propose_actions_impl(state, context)

        if not thought:
            # LLM 返回空串（无 client / 失败）→ 规则模式（与原逻辑一致）
            return self._propose_actions_impl(state, context)

        # 保存思考用于选择性记忆（取【动作】标记前的自然语言正文）
        body = self._extract_thought_body(thought)
        if hasattr(self, "_last_thought"):
            self._last_thought = body or thought

        # 步骤 2：解析动作（结构化优先 → 关键词 fallback）
        actions: List[Action] = []
        if _structured_actions_enabled():
            structured = self._parse_structured_action(thought, state, context)
            if structured:
                actions.extend(structured)
                logger.debug(f"器官 {self.name} 结构化解析得到 {len(actions)} 动作")

        if not actions:
            # 结构化未命中或被关闭 → 关键词 fallback
            kw_actions = self._keyword_fallback_actions(thought, state, context)
            if kw_actions:
                actions.extend(kw_actions)
                if _structured_actions_enabled():
                    logger.debug(f"器官 {self.name} 关键词 fallback 得到 {len(actions)} 动作")

        # 步骤 2.5：关键词 fallback 只产出被动动作（REFLECT/THINK）且有显著缺口时，
        # 追加价值驱动动作。避免 LLM 叙事习惯（总命中"思考/分析"→REFLECT）劫持行为，
        # 让真实的价值需求有候选进入 PHASE 8 评估。
        if actions and _structured_actions_enabled():
            passive_types = {"REFLECT", "THINK"}
            only_passive = all(a.type.value in passive_types for a in actions)
            if only_passive:
                value_actions = self._value_driven_fallback(state, context)
                if value_actions:
                    actions.extend(value_actions)
                    logger.debug(f"器官 {self.name} 追加价值驱动动作（关键词仅产被动动作）")

        # 步骤 3：结构化和关键词都没命中 → 价值驱动兜底
        if not actions:
            actions = self._value_driven_fallback(state, context)

        # 步骤 4：价值驱动也无动作 → 各器官的规则模式
        if not actions:
            actions = self._propose_actions_impl(state, context)

        return actions

    def _value_driven_fallback(
        self,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[Action]:
        """价值驱动兜底（P0-1 残留修复）：结构化+关键词都失败时，按价值缺口选动作。

        推理模型（step-3.7-flash）常忽略【动作:XXX】格式要求，退回关键词 fallback。
        若关键词也偏向 REFLECT/THINK（高频词命中），系统会陷入反思死循环。
        此方法在退入规则模式前，根据当前最大的价值缺口维度选一个主动动作，
        让价值系统真正驱动行为，而非被 LLM 的叙事习惯劫持。

        映射（按器官的 value_dimension 与缺口的语义对应）：
          - curiosity 缺口大 → EXPLORE（满足好奇）
          - attachment 缺口大 → CHAT（社交联结）
          - homeostasis 缺口大 → SLEEP（恢复）
          - competence 缺口大 → EXPLORE（学习提升）
          - safety 缺口大 → REFLECT（警惕）
        缺口阈值 0.3；无显著缺口则返回空（交给规则模式）。
        """
        gaps = context.get("value_gaps") or state.get("gaps") or {}
        if not gaps:
            return []

        # 找最大缺口维度
        max_dim = max(gaps, key=gaps.get) if gaps else None
        max_gap = gaps.get(max_dim, 0) if max_dim else 0
        if max_gap < 0.3:
            return []  # 无显著缺口，交给规则模式

        # 维度 → 动作映射
        dim_action = {
            "curiosity": ("EXPLORE", 0.2, ["llm_access"]),
            "attachment": ("CHAT", 0.0, []),
            "homeostasis": ("SLEEP", 0.0, []),
            "competence": ("EXPLORE", 0.2, ["llm_access"]),
            "safety": ("REFLECT", 0.1, []),
        }
        mapping = dim_action.get(max_dim)
        if not mapping:
            return []

        action_type_str, risk, caps = mapping
        from common.models import ActionType
        try:
            action_type = ActionType(action_type_str)
        except ValueError:
            return []

        logger.debug(
            f"器官 {self.name} 价值驱动兜底: 缺口维度={max_dim}({max_gap:.2f}) → {action_type_str}"
        )
        return [Action(
            type=action_type,
            params={
                "source": "value_driven_fallback",
                "gap_dimension": max_dim,
                "gap_value": round(max_gap, 3),
            },
            risk_level=risk,
            capability_req=caps,
        )]

    def _format_structured_output_prompt_prefix(self) -> str:
        """返回前置到 prompt 开头的强制格式提醒（适配推理模型）。

        推理模型（step-3.7-flash）会先内部推理再输出 content，对 prompt 末尾的
        格式要求容易忽略。把核心要求前置到开头，让模型在开始推理前就知道
        最终必须输出【动作:XXX】标记。
        """
        return (
            "【重要】请在回答的最后用【动作:类型】【主题:内容】格式给出行动决策"
            "（如【动作:EXPLORE】【主题:xxx】）。可选动作: EXPLORE/REFLECT/CHAT/GROW/LEARN_SKILL/THINK。"
            "不要默认选 REFLECT/THINK。下面是思考素材：\n\n"
        )

    def _format_structured_output_prompt_suffix(self) -> str:
        """返回追加到 _build_thinking_prompt 末尾的结构化输出格式说明。

        让 LLM 在自由思考后用固定标记给出动作决策，避免中文叙事被关键词误解析。
        """
        return (
            "\n\n=== 行动决策（必须填写）===\n"
            "在你完成上面的思考后，请用以下格式给出你**当前最想做的**一个行动决策。\n"
            "每项一行，必须包含【动作】和【主题】：\n\n"
            "【动作:EXPLORE】\n"
            "【主题:你具体想探索/反思/构建的对象，一句话描述】\n\n"
            "可选动作类型（只能选一个）：\n"
            "  EXPLORE    - 探索新事物、学习、满足好奇（当你感到无聊或好奇时优先选这个）\n"
            "  REFLECT    - 反思、回顾、整理思绪（仅在你真的需要停下来想清楚时选）\n"
            "  CHAT       - 与用户对话、主动表达（当你想交流或回应时选）\n"
            "  GROW       - 构建、创造、实现某个东西\n"
            "  LEARN_SKILL - 刻意练习一项技能\n"
            "  THINK      - 纯粹思考（仅当其他都不合适时选）\n\n"
            "**重要：不要默认选 REFLECT 或 THINK。**"
            "请基于上面的【价值缺口】和【内在驱动】选择——\n"
            "如果有明显的好奇缺口（curiosity）或无聊感，倾向 EXPLORE；\n"
            "如果有依恋缺口（attachment）或想交流，倾向 CHAT；\n"
            "只有在你真的卡住需要整理思路时才选 REFLECT。\n"
        )

    def _parse_structured_action(
        self,
        thought: str,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[Action]:
        """从 LLM 思考中解析【动作:XXX】【主题:YYY】标记。

        提取失败（无标记/动作类型不合法）返回空列表，由调用方走关键词 fallback。
        """
        actions: List[Action] = []

        # mind 器官特殊：有用户消息时优先 CHAT（透明透传，不被结构化覆盖）
        if hasattr(self, "_should_respond_to_user") and self._should_respond_to_user(state, context):
            # 交给子类的 _keyword_fallback_actions 处理 CHAT 路径
            return []

        m_action = _ACTION_RE.search(thought)
        if not m_action:
            return []

        action_type_str = m_action.group(1).upper()
        # 合法性校验：必须能映射到 ActionType 枚举
        from common.models import ActionType
        try:
            action_type = ActionType(action_type_str)
        except ValueError:
            logger.debug(f"器官 {self.name} 结构化动作类型不合法: {action_type_str}")
            return []

        topic = ""
        m_topic = _TOPIC_RE.search(thought)
        if m_topic:
            topic = m_topic.group(1).strip()

        # 委托子类构建具体 Action（每器官的 params/risk/capability 不同）
        action = self._build_action_from_structured(action_type, topic, thought, state, context)
        if action:
            actions.append(action)
        return actions

    def _build_action_from_structured(
        self,
        action_type,
        topic: str,
        thought: str,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Optional[Action]:
        """根据结构化解析结果构建 Action（子类可覆盖，默认通用实现）。

        默认实现：按 action_type 给出合理的 params/risk/capability。
        子类可覆盖以加入器官专属字段（如 scout 的 explored_topics）。
        """
        from common.models import ActionType
        body = self._extract_thought_body(thought) or thought[:200]

        if action_type == ActionType.EXPLORE:
            return Action(
                type="EXPLORE",
                params={
                    "topic": topic or "llm_guided_exploration",
                    "depth": "medium",
                    "source": "llm_structured",
                    "thought": body[:200],
                },
                risk_level=0.2,
                capability_req=["llm_access"],
            )
        elif action_type == ActionType.REFLECT:
            return Action(
                type="REFLECT",
                params={
                    "purpose": topic or "self_initiated",
                    "depth": 2,
                    "source": "llm_structured",
                    "thought": body[:200],
                },
                risk_level=0.1,
                capability_req=[],
            )
        elif action_type == ActionType.CHAT:
            # 主动 CHAT（无用户消息时）—— message 留空由下游 action_executor 用 LLM 生成
            return Action(
                type="CHAT",
                params={
                    "message": "",
                    "topic": topic,
                    "source": "llm_structured",
                    "thought": body[:200],
                },
                risk_level=0.0,
                capability_req=[],
            )
        elif action_type == ActionType.GROW:
            return Action(
                type="GROW",
                params={
                    "task": topic or thought[:100],
                    "source": "llm_structured",
                },
                risk_level=0.3,
                capability_req=["llm_access"],
            )
        elif action_type == ActionType.LEARN_SKILL:
            return Action(
                type="LEARN_SKILL",
                params={
                    "skill": topic or "general",
                    "source": "llm_structured",
                },
                risk_level=0.2,
                capability_req=["llm_access"],
            )
        elif action_type == ActionType.THINK:
            return Action(
                type="THINK",
                params={
                    "thought": body,
                    "source": "llm_structured",
                },
                risk_level=0.0,
                capability_req=[],
            )
        return None

    def _keyword_fallback_actions(
        self,
        thought: str,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[Action]:
        """关键词 fallback（子类应覆盖为原 _parse_llm_thought_to_actions 的逻辑）。

        默认返回空，由 _propose_actions_impl 兜底。
        """
        return []

    @staticmethod
    def _extract_thought_body(thought: str) -> str:
        """提取【动作】标记前的自然语言正文（用于记忆评估，避免污染）。

        若无标记，返回原 thought 截断到 500 字符。
        """
        if not thought:
            return ""
        m = _THOUGHT_BODY_RE.search(thought)
        if m:
            body = m.group(1).strip()
            return body[:500] if body else ""
        return thought[:500]

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
