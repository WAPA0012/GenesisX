"""Organ LLM Session - 器官LLM会话管理

支持三种架构模式：

模式1: 独立会话模式 (OrganLLMManager, mode="independent")
- 每个器官拥有独立的LLM会话
- 独立的会话ID、对话历史、系统提示词
- 器官之间互不污染
- 可为每个器官单独配置 LLM 和会话参数

模式2: 共享大脑模式 (SharedBrainManager, mode="shared")
- 所有器官共享一个LLM会话
- 统一的对话历史
- 通过角色标记区分不同器官的思考

模式3: 禁用模式 (mode="disabled")
- 不使用 LLM，器官使用规则模式运行

选择性记忆：
- OrganMemoryWriter 负责选择性保存器官思考到记忆
- 只保存重要洞察、关键决策、有价值的学习

使用方式：
    # 独立会话模式（默认）
    manager = OrganLLMManager(llm_client)
    session = manager.get_session("mind")

    # 独立会话模式（自定义器官 LLM）
    manager = OrganLLMManager(
        llm_client=default_client,
        organ_clients={"mind": custom_client},
        organ_session_configs={"mind": SessionConfig(temperature=0.8)}
    )

    # 共享大脑模式
    shared = SharedBrainManager(llm_client)
    response = shared.think("mind", "我现在的状态是...")
"""

from typing import Dict, Any, List, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid

from common.logger import get_logger

if TYPE_CHECKING:
    from tools.llm_client import LLMClient

logger = get_logger(__name__)


@dataclass
class SessionConfig:
    """会话配置"""
    max_history: int = 20          # 最大历史消息数
    temperature: float = 0.7       # 思考温度
    max_tokens: int = 1000         # 最大输出token
    save_to_memory: bool = False   # 是否保存思考到记忆（用户选择3：选择性写入）


class OrganLLMSession:
    """器官LLM会话

    每个器官独立的LLM会话，拥有：
    - 独立的session_id
    - 独立的对话历史
    - 独立的系统提示词（器官人格）
    """

    # 器官人格模板
    ORGAN_PERSONALITIES = {
        "mind": """你是GenesisX的【思维器官】(MindOrgan)。

你的职责：
- 深度思考和推理
- 规划和决策
- 分析复杂问题
- 提出探索方向

你的特点：
- 逻辑严密，喜欢深入分析
- 会主动发现知识缺口
- 会反思自己的思维过程

你现在要基于当前状态，提出你认为最值得做的事。
思考要独立、自主，不要只是响应外界输入。""",

        "scout": """你是GenesisX的【侦察器官】(ScoutOrgan)。

你的职责：
- 探索未知领域
- 发现新信息
- 搜索和调查
- 监控环境变化

你的特点：
- 好奇心强，喜欢探索
- 敏锐，善于发现异常
- 主动寻找新机会

你现在要基于当前状态，提出你想探索的方向。""",

        "builder": """你是GenesisX的【构建器官】(BuilderOrgan)。

你的职责：
- 构建和创造
- 实现想法
- 生成代码
- 解决技术问题

你的特点：
- 实用主义，关注可行性
- 喜欢动手实现
- 追求效率和优雅

你现在要基于当前状态，提出你想构建或实现的东西。""",

        "caretaker": """你是GenesisX的【照护器官】(CaretakerOrgan)。

你的职责：
- 维护系统稳定
- 关注用户需求
- 确保安全
- 协调各器官

你的特点：
- 谨慎，关注风险
- 有同理心
- 善于协调

你现在要基于当前状态，提出你认为需要关注或维护的方面。""",

        "archivist": """你是GenesisX的【档案器官】(ArchivistOrgan)。

你的职责：
- 管理记忆
- 整理知识
- 检索历史信息
- 发现模式和规律

你的特点：
- 有条理，善于整理
- 记忆力强
- 善于发现联系

你现在要基于当前状态，提出你认为值得记录或整理的内容。""",

        "immune": """你是GenesisX的【免疫器官】(ImmuneOrgan)。

你的职责：
- 检测威胁
- 防御攻击
- 修复损伤
- 维护安全边界

你的特点：
- 警觉，善于发现异常
- 防御性强
- 反应迅速

你现在要基于当前状态，提出你认为需要警惕或防御的方面。""",

        "default": """你是GenesisX的一个器官。

你要基于当前状态，独立思考并提出你认为最值得做的事。
思考要自主、有创造性，不要只是响应外界输入。"""
    }

    def __init__(
        self,
        organ_name: str,
        llm_client: "LLMClient",
        system_prompt: Optional[str] = None,
        config: Optional[SessionConfig] = None,
    ):
        """初始化会话

        Args:
            organ_name: 器官名称
            llm_client: LLM客户端（共享的API）
            system_prompt: 自定义系统提示词（可选，默认使用器官人格）
            config: 会话配置
        """
        self.organ_name = organ_name
        self.llm_client = llm_client
        self.config = config or SessionConfig()

        # 独立的会话ID
        self.session_id = f"{organ_name}_{uuid.uuid4().hex[:8]}"

        # 独立的对话历史
        self._history: List[Dict[str, str]] = []

        # 系统提示词（器官人格）
        self.system_prompt = system_prompt or self._get_personality()

        # 统计
        self._call_count = 0
        self._total_tokens = 0

        logger.info(f"[OrganLLMSession] Created session for {organ_name}: {self.session_id}")

    def _get_personality(self) -> str:
        """获取器官人格"""
        return self.ORGAN_PERSONALITIES.get(
            self.organ_name.lower(),
            self.ORGAN_PERSONALITIES["default"]
        )

    def think(
        self,
        prompt: str,
        include_history: bool = True,
        temperature: Optional[float] = None,
    ) -> str:
        """思考（带历史上下文）

        这是主要的思考接口，会保持对话历史。

        Args:
            prompt: 思考提示
            include_history: 是否包含历史
            temperature: 温度（可选）

        Returns:
            思考结果
        """
        if not self.llm_client:
            logger.warning(f"[{self.organ_name}] LLM client not available")
            return ""

        # 构建消息
        messages = []

        if include_history:
            # 添加历史（限制数量）
            messages.extend(self._history[-self.config.max_history:])

        # 添加当前消息
        messages.append({"role": "user", "content": prompt})

        # 调用LLM
        try:
            response = self.llm_client.chat(
                messages=messages,
                system_prompt=self.system_prompt,
                temperature=temperature or self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

            self._call_count += 1
            self._total_tokens += response.get("total_tokens", 0)

            if response.get("ok"):
                result = response.get("text", "")

                # 更新历史
                self._history.append({"role": "user", "content": prompt})
                self._history.append({"role": "assistant", "content": result})

                # 限制历史长度
                if len(self._history) > self.config.max_history * 2:
                    self._history = self._history[-self.config.max_history * 2:]

                logger.debug(f"[{self.organ_name}] Think: {prompt[:50]}... -> {result[:50]}...")
                return result
            else:
                logger.error(f"[{self.organ_name}] LLM error: {response.get('error')}")
                return ""

        except Exception as e:
            logger.error(f"[{self.organ_name}] Think failed: {e}")
            return ""

    def respond(
        self,
        prompt: str,
        temperature: Optional[float] = None,
    ) -> str:
        """快速响应（不带历史）

        用于简单的判断，不保持上下文。

        Args:
            prompt: 提示
            temperature: 温度

        Returns:
            响应结果
        """
        return self.think(prompt, include_history=False, temperature=temperature)

    def reflect(self) -> str:
        """反思当前状态

        让器官反思自己的思考历史和决策。
        """
        if not self._history:
            return "没有思考历史可以反思"

        reflection_prompt = f"""请反思你最近的思考：

最近对话历史：
{self._format_history()}

请回答：
1. 你发现了什么模式？
2. 你的思考有什么盲点？
3. 你下一步想探索什么？"""

        return self.think(reflection_prompt, include_history=True)

    def clear_history(self):
        """清空历史"""
        self._history = []
        logger.info(f"[{self.organ_name}] History cleared")

    def get_history(self) -> List[Dict[str, str]]:
        """获取历史"""
        return self._history.copy()

    def _format_history(self) -> str:
        """格式化历史为文本"""
        lines = []
        for msg in self._history[-10:]:  # 最近10条
            role = "我" if msg["role"] == "assistant" else "输入"
            content = msg["content"][:100]
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "organ_name": self.organ_name,
            "session_id": self.session_id,
            "call_count": self._call_count,
            "total_tokens": self._total_tokens,
            "history_length": len(self._history),
        }


class OrganLLMManager:
    """器官LLM会话管理器

    管理所有器官的LLM会话，确保每个器官独立。
    支持为每个器官配置不同的 LLM 客户端和会话参数。
    """

    def __init__(
        self,
        llm_client: "LLMClient",
        default_config: Optional[SessionConfig] = None,
        organ_clients: Optional[Dict[str, "LLMClient"]] = None,
        organ_session_configs: Optional[Dict[str, SessionConfig]] = None,
    ):
        """初始化管理器

        Args:
            llm_client: 默认 LLM 客户端（用于没有单独配置的器官）
            default_config: 默认会话配置
            organ_clients: 器官专属 LLM 客户端映射 {organ_name: LLMClient}
            organ_session_configs: 器官专属会话配置映射 {organ_name: SessionConfig}
        """
        self.llm_client = llm_client
        self.default_config = default_config or SessionConfig()
        self.organ_clients = organ_clients or {}
        self.organ_session_configs = organ_session_configs or {}
        self._sessions: Dict[str, OrganLLMSession] = {}

    def get_session(
        self,
        organ_name: str,
        system_prompt: Optional[str] = None,
        config: Optional[SessionConfig] = None,
    ) -> OrganLLMSession:
        """获取或创建器官会话

        Args:
            organ_name: 器官名称
            system_prompt: 自定义系统提示词
            config: 会话配置（优先级：参数 > 器官专属 > 默认）

        Returns:
            器官LLM会话
        """
        if organ_name not in self._sessions:
            # 选择 LLM 客户端（优先使用器官专属配置）
            llm_client = self.organ_clients.get(organ_name, self.llm_client)

            # 选择会话配置（优先级：参数 > 器官专属 > 默认）
            if config:
                session_config = config
            elif organ_name in self.organ_session_configs:
                session_config = self.organ_session_configs[organ_name]
            else:
                session_config = self.default_config

            self._sessions[organ_name] = OrganLLMSession(
                organ_name=organ_name,
                llm_client=llm_client,
                system_prompt=system_prompt,
                config=session_config,
            )

            # 记录是否使用自定义 LLM
            using_custom = organ_name in self.organ_clients
            logger.info(f"[OrganLLMManager] Created session for {organ_name} (custom_llm={using_custom})")

        return self._sessions[organ_name]

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有会话统计"""
        return {
            name: session.get_stats()
            for name, session in self._sessions.items()
        }

    def clear_all_history(self):
        """清空所有会话历史"""
        for session in self._sessions.values():
            session.clear_history()
        logger.info("[OrganLLMManager] All sessions history cleared")


class SharedBrainSession:
    """共享大脑会话

    所有器官共享同一个LLM会话，通过角色标记区分不同器官的思考。
    """

    # 共享大脑的系统提示词
    SHARED_BRAIN_SYSTEM_PROMPT = """你是GenesisX的【共享大脑】。

你同时服务于多个器官，每个器官有独立的职责和视角：

- 【思维器官】: 深度思考、规划决策、分析问题
- 【侦察器官】: 探索未知、发现信息、监控环境
- 【构建器官】: 构建创造、实现想法、解决技术问题
- 【照护器官】: 维护稳定、关注需求、确保安全
- 【档案器官】: 管理记忆、整理知识、发现规律
- 【免疫器官】: 检测威胁、防御攻击、维护边界

当某个器官通过 [器官名] 标记提问时，你需要：
1. 切换到该器官的视角和职责
2. 基于该器官的特点进行思考
3. 保持整体一致性的同时展现器官个性

你会记住之前所有器官的思考，形成统一的认知。"""

    def __init__(
        self,
        llm_client: "LLMClient",
        config: Optional[SessionConfig] = None,
    ):
        """初始化共享大脑会话

        Args:
            llm_client: LLM客户端
            config: 会话配置
        """
        self.llm_client = llm_client
        self.config = config or SessionConfig()

        # 统一的会话ID
        self.session_id = f"shared_brain_{uuid.uuid4().hex[:8]}"

        # 共享的对话历史
        self._history: List[Dict[str, str]] = []

        # 统计
        self._call_count = 0
        self._total_tokens = 0

        # 各器官的统计
        self._organ_call_counts: Dict[str, int] = {}

        logger.info(f"[SharedBrainSession] Created: {self.session_id}")

    def think(
        self,
        organ_name: str,
        prompt: str,
        include_history: bool = True,
        temperature: Optional[float] = None,
    ) -> str:
        """以特定器官身份思考

        Args:
            organ_name: 器官名称
            prompt: 思考提示
            include_history: 是否包含共享历史
            temperature: 温度

        Returns:
            思考结果
        """
        if not self.llm_client:
            logger.warning("[SharedBrain] LLM client not available")
            return ""

        # 构建带器官标记的提示
        organ_prompt = f"[{organ_name.upper()}] {prompt}"

        # 构建消息
        messages = []
        if include_history:
            messages.extend(self._history[-self.config.max_history:])
        messages.append({"role": "user", "content": organ_prompt})

        # 调用LLM
        try:
            response = self.llm_client.chat(
                messages=messages,
                system_prompt=self.SHARED_BRAIN_SYSTEM_PROMPT,
                temperature=temperature or self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

            self._call_count += 1
            self._total_tokens += response.get("total_tokens", 0)
            self._organ_call_counts[organ_name] = self._organ_call_counts.get(organ_name, 0) + 1

            if response.get("ok"):
                result = response.get("text", "")

                # 更新共享历史
                self._history.append({"role": "user", "content": organ_prompt})
                self._history.append({"role": "assistant", "content": result})

                # 限制历史长度
                if len(self._history) > self.config.max_history * 2:
                    self._history = self._history[-self.config.max_history * 2:]

                logger.debug(f"[SharedBrain][{organ_name}] Think: {prompt[:30]}... -> {result[:30]}...")
                return result
            else:
                logger.error(f"[SharedBrain] LLM error: {response.get('error')}")
                return ""

        except Exception as e:
            logger.error(f"[SharedBrain] Think failed: {e}")
            return ""

    def respond(
        self,
        organ_name: str,
        prompt: str,
        temperature: Optional[float] = None,
    ) -> str:
        """快速响应（不带历史）"""
        return self.think(organ_name, prompt, include_history=False, temperature=temperature)

    def get_organ_history(self, organ_name: str) -> List[Dict[str, str]]:
        """获取特定器官的历史（过滤出该器官的对话）"""
        organ_tag = f"[{organ_name.upper()}]"
        history = []
        for i, msg in enumerate(self._history):
            if organ_tag in msg.get("content", ""):
                history.append(msg)
                if i + 1 < len(self._history):
                    history.append(self._history[i + 1])
        return history

    def clear_history(self):
        """清空共享历史"""
        self._history = []
        logger.info("[SharedBrain] History cleared")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "session_id": self.session_id,
            "mode": "shared_brain",
            "total_call_count": self._call_count,
            "total_tokens": self._total_tokens,
            "history_length": len(self._history),
            "organ_call_counts": self._organ_call_counts.copy(),
        }


class SharedBrainManager:
    """共享大脑管理器

    所有器官共享一个LLM会话，可以互相感知对方的思考。
    """

    def __init__(self, llm_client: "LLMClient", config: Optional[SessionConfig] = None):
        """初始化共享大脑管理器

        Args:
            llm_client: LLM客户端
            config: 会话配置
        """
        self.llm_client = llm_client
        self.config = config or SessionConfig()

        # 创建唯一的共享会话
        self._shared_session = SharedBrainSession(llm_client, self.config)

        # 为每个器官创建代理接口
        self._organ_proxies: Dict[str, OrganProxy] = {}

        logger.info("[SharedBrainManager] Initialized")

    def get_session(self, organ_name: str) -> "OrganProxy":
        """获取器官的代理接口

        Args:
            organ_name: 器官名称

        Returns:
            器官代理，可以调用 think() 和 respond()
        """
        if organ_name not in self._organ_proxies:
            self._organ_proxies[organ_name] = OrganProxy(
                organ_name=organ_name,
                shared_session=self._shared_session
            )
            logger.debug(f"[SharedBrainManager] Created proxy for {organ_name}")

        return self._organ_proxies[organ_name]

    def get_shared_stats(self) -> Dict[str, Any]:
        """获取共享大脑的统计信息"""
        return self._shared_session.get_stats()

    def clear_shared_history(self):
        """清空共享历史"""
        self._shared_session.clear_history()

    def get_shared_history(self) -> List[Dict[str, str]]:
        """获取完整的共享历史"""
        return self._shared_session._history.copy()


class OrganProxy:
    """器官代理

    包装共享大脑会话，提供与独立会话相同的接口。
    """

    def __init__(self, organ_name: str, shared_session: SharedBrainSession):
        """初始化代理

        Args:
            organ_name: 器官名称
            shared_session: 共享会话
        """
        self.organ_name = organ_name
        self._shared_session = shared_session

        # 兼容性属性
        self.session_id = f"{organ_name}_proxy_{shared_session.session_id}"
        self.system_prompt = OrganLLMSession.ORGAN_PERSONALITIES.get(
            organ_name.lower(),
            OrganLLMSession.ORGAN_PERSONALITIES["default"]
        )

    def think(
        self,
        prompt: str,
        include_history: bool = True,
        temperature: Optional[float] = None,
    ) -> str:
        """思考"""
        return self._shared_session.think(
            self.organ_name, prompt, include_history, temperature
        )

    def respond(self, prompt: str, temperature: Optional[float] = None) -> str:
        """快速响应"""
        return self._shared_session.respond(self.organ_name, prompt, temperature)

    def get_history(self) -> List[Dict[str, str]]:
        """获取该器官的历史"""
        return self._shared_session.get_organ_history(self.organ_name)

    def clear_history(self):
        """清空历史（实际上清空整个共享历史）"""
        logger.warning(f"[{self.organ_name}] clear_history() called on shared brain, clearing ALL history")
        self._shared_session.clear_history()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        stats = self._shared_session.get_stats()
        stats["organ_name"] = self.organ_name
        stats["mode"] = "shared_proxy"
        return stats


# ============================================================
# 选择性记忆系统
# ============================================================

@dataclass
class MemoryWorthiness:
    """记忆价值评估结果"""
    should_save: bool
    importance: float  # 0-1
    category: str  # insight, decision, learning, observation, routine
    reason: str
    summary: str = ""  # LLM 生成的摘要


class OrganMemoryWriter:
    """器官思考选择性记忆写入器

    使用 LLM 智能判断哪些思考值得保存：
    - 重要洞察（insight）
    - 关键决策（decision）
    - 有价值的学习（learning）
    - 重要的观察（observation）
    - 排除日常琐事（routine）
    """

    # LLM 判断系统提示词
    MEMORY_JUDGE_PROMPT = """你是一个记忆评估器，负责判断一段思考是否值得保存到长期记忆。

评估标准：
1. **洞察类** (insight): 对问题本质的理解、规律发现、因果关系
2. **决策类** (decision): 重要选择、计划变更、优先级调整
3. **学习类** (learning): 新技能掌握、经验教训、知识获取
4. **观察类** (observation): 异常发现、有趣现象、值得记录的状态
5. **日常类** (routine): 重复性、无新信息、可忽略的琐事

请用以下JSON格式回复（只输出JSON，不要其他内容）：
{
    "should_save": true/false,
    "importance": 0.0-1.0,
    "category": "insight/decision/learning/observation/routine",
    "reason": "简短说明为什么",
    "summary": "如需保存，用一句话概括核心内容"
}

判断原则：
- 宁缺毋滥：不确定时倾向于不保存
- 重视独特性：重复或相似内容不保存
- 关注影响：对后续行为有影响的才保存
- 情感加成：带有强烈情绪体验的更有价值"""

    # 快速排除关键词（不经过 LLM 直接跳过）
    QUICK_EXCLUDE_PATTERNS = [
        "正在", "继续", "待机", "闲置", "等待",
        "没有特别", "如常", "正常", "一如既往",
        "重复", "又是", "还是一样",
    ]

    def __init__(
        self,
        memory_system: Optional[Any] = None,
        llm_client: Optional["LLMClient"] = None,
        importance_threshold: float = 0.5,
        use_llm_judge: bool = True,
    ):
        """初始化记忆写入器

        Args:
            memory_system: 记忆系统（EpisodicMemory）
            llm_client: LLM 客户端（用于智能判断）
            importance_threshold: 重要性阈值
            use_llm_judge: 是否使用 LLM 判断（False 则用关键词）
        """
        self.memory_system = memory_system
        self.llm_client = llm_client
        self.importance_threshold = importance_threshold
        self.use_llm_judge = use_llm_judge and (llm_client is not None)

        self._write_count = 0
        self._skip_count = 0
        self._llm_judge_count = 0
        self._quick_skip_count = 0

        logger.info(f"[OrganMemoryWriter] Initialized (use_llm_judge={self.use_llm_judge})")

    def _quick_check_exclude(self, thought: str) -> bool:
        """快速排除检查（不经 LLM）"""
        thought_lower = thought.lower()
        for pattern in self.QUICK_EXCLUDE_PATTERNS:
            if pattern in thought_lower:
                return True
        return False

    def _llm_evaluate(
        self,
        organ_name: str,
        thought: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> MemoryWorthiness:
        """使用 LLM 评估思考价值"""
        if not self.llm_client:
            return self._keyword_evaluate(organ_name, thought, context)

        # 构建评估提示
        context_info = ""
        if context:
            context_info = f"""
【当前上下文】
- 压力: {context.get('stress', 0):.1%}
- 精力: {context.get('energy', 0.5):.1%}
- 心情: {context.get('mood', 0.5):.1%}
"""

        judge_prompt = f"""请评估以下来自【{organ_name}】器官的思考是否值得保存：

【思考内容】
{thought}
{context_info}
请判断这段思考的记忆价值。"""

        try:
            response = self.llm_client.chat(
                messages=[{"role": "user", "content": judge_prompt}],
                system_prompt=self.MEMORY_JUDGE_PROMPT,
                temperature=0.1,  # 低温度，更确定性
                max_tokens=200,
            )

            if response.get("ok"):
                result_text = response.get("text", "")
                self._llm_judge_count += 1

                # 解析 JSON
                import json
                # 尝试提取 JSON
                json_start = result_text.find("{")
                json_end = result_text.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = result_text[json_start:json_end]
                    result = json.loads(json_str)

                    return MemoryWorthiness(
                        should_save=result.get("should_save", False),
                        importance=float(result.get("importance", 0.5)),
                        category=result.get("category", "routine"),
                        reason=result.get("reason", ""),
                        summary=result.get("summary", "")[:200],
                    )
        except Exception as e:
            logger.warning(f"[OrganMemory] LLM judge failed: {e}, falling back to keywords")

        # Fallback 到关键词判断
        return self._keyword_evaluate(organ_name, thought, context)

    def _keyword_evaluate(
        self,
        organ_name: str,
        thought: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> MemoryWorthiness:
        """关键词判断（fallback）"""
        importance_keywords = {
            "insight": ["发现", "意识到", "理解", "洞察", "明白了", "关键在于", "本质"],
            "decision": ["决定", "选择", "应该", "计划", "打算", "优先", "放弃"],
            "learning": ["学会了", "掌握了", "经验", "教训", "记住"],
            "observation": ["注意到", "观察到", "异常", "有趣", "奇怪"],
        }

        importance = 0.0
        matched_category = "routine"

        for category, keywords in importance_keywords.items():
            for keyword in keywords:
                if keyword in thought:
                    importance += 0.2
                    matched_category = category
                    break

        # 上下文加成
        if context:
            if context.get("stress", 0) > 0.7:
                importance += 0.1
            if context.get("energy", 1) < 0.3:
                importance += 0.1

        importance = min(importance, 1.0)

        return MemoryWorthiness(
            should_save=importance >= self.importance_threshold,
            importance=importance,
            category=matched_category,
            reason="关键词匹配" if importance > 0 else "未匹配重要关键词",
            summary=thought[:100],
        )

    def evaluate_thought(
        self,
        organ_name: str,
        thought: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> MemoryWorthiness:
        """评估思考是否值得保存

        Args:
            organ_name: 器官名称
            thought: 思考内容
            context: 上下文

        Returns:
            MemoryWorthiness 评估结果
        """
        # 快速排除检查
        if self._quick_check_exclude(thought):
            self._quick_skip_count += 1
            return MemoryWorthiness(
                should_save=False,
                importance=0.0,
                category="routine",
                reason="快速排除：日常琐事",
            )

        # 使用 LLM 或关键词判断
        if self.use_llm_judge:
            return self._llm_evaluate(organ_name, thought, context)
        else:
            return self._keyword_evaluate(organ_name, thought, context)

    def save_if_worthwhile(
        self,
        organ_name: str,
        thought: str,
        state: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        tick: int = 0,
    ) -> bool:
        """如果值得，保存思考到记忆

        Args:
            organ_name: 器官名称
            thought: 思考内容
            state: 当前状态
            context: 上下文
            tick: 当前tick

        Returns:
            是否保存成功
        """
        evaluation = self.evaluate_thought(organ_name, thought, context)

        if not evaluation.should_save:
            self._skip_count += 1
            logger.debug(f"[OrganMemory] Skip {organ_name}: {evaluation.reason}")
            return False

        if not self.memory_system:
            logger.warning("[OrganMemory] No memory system available")
            return False

        try:
            from common.models import EpisodeRecord, Action, Outcome, CostVector

            # 使用 LLM 生成的摘要（如果有）
            summary = evaluation.summary or thought[:200]

            memory_entry = EpisodeRecord(
                tick=tick,
                session_id=f"organ_{organ_name}",
                observation=None,
                action=Action(
                    type="THINK",
                    params={
                        "organ": organ_name,
                        "thought": thought[:500],
                        "category": evaluation.category,
                        "summary": summary,
                    },
                    risk_level=0.0,
                    capability_req=[],
                ),
                outcome=Outcome(
                    ok=True,
                    status=summary,
                ),
                reward=evaluation.importance,
                delta=0.0,
                value_pred=0.0,
                state_snapshot=state or {},
                weights={},
                gaps={},
                utilities={},
                current_goal=f"{organ_name}_{evaluation.category}",
                cost=CostVector(),
            )

            self.memory_system.append(memory_entry)
            self._write_count += 1
            logger.info(f"[OrganMemory] Saved {organ_name}: {evaluation.category} (importance={evaluation.importance:.2f})")
            return True

        except Exception as e:
            logger.error(f"[OrganMemory] Failed to save: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = self._write_count + self._skip_count
        save_rate = self._write_count / total if total > 0 else 0

        return {
            "write_count": self._write_count,
            "skip_count": self._skip_count,
            "quick_skip_count": self._quick_skip_count,
            "llm_judge_count": self._llm_judge_count,
            "save_rate": save_rate,
            "importance_threshold": self.importance_threshold,
            "use_llm_judge": self.use_llm_judge,
        }


def create_llm_manager(
    llm_client: "LLMClient",
    mode: str = "independent",
    config: Optional[SessionConfig] = None,
    organ_clients: Optional[Dict[str, "LLMClient"]] = None,
    organ_session_configs: Optional[Dict[str, SessionConfig]] = None,
) -> Any:
    """创建LLM管理器的工厂函数

    Args:
        llm_client: 默认 LLM 客户端
        mode: 模式 "independent"、"shared" 或 "disabled"
        config: 默认会话配置
        organ_clients: 器官专属 LLM 客户端映射（仅 independent 模式）
        organ_session_configs: 器官专属会话配置映射（仅 independent 模式）

    Returns:
        OrganLLMManager 或 SharedBrainManager，或 None（disabled 模式）
    """
    if mode == "disabled":
        logger.info("[Factory] Organ LLM disabled")
        return None
    elif mode == "shared":
        logger.info("[Factory] Creating SharedBrainManager")
        return SharedBrainManager(llm_client, config)
    else:
        logger.info("[Factory] Creating OrganLLMManager (independent mode)")
        return OrganLLMManager(
            llm_client=llm_client,
            default_config=config,
            organ_clients=organ_clients,
            organ_session_configs=organ_session_configs,
        )

