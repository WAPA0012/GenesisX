"""Mind Field Architecture - Paper-compliant Multi-Model Implementation.

Genesis X 论文 3.4.2 节的多模型协作架构实现

核心特性:
- Single/Core5/Full7/Adaptive 四种配置模式
- 根据人格中间变量 (ET_t, CT_t, ES_t) 动态切换
- 完整的黑板广播协议
- 与 Soul Field 深度集成
"""

import asyncio
import time
import os
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from common.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# 枚举定义
# ============================================================================

class ModelConfig(str, Enum):
    """模型配置选项 (论文 3.4.2)"""
    SINGLE = "single"       # 单一LLM处理所有任务
    CORE5 = "core5"         # 核心五模型: {M_coord, M_mem, M_reason, M_affect, M_percept}
    FULL7 = "full7"         # 完整七模型: Core5 + {M_vis, M_aud}
    ADAPTIVE = "adaptive"   # 根据人格特质动态选择配置


class ExpertRole(str, Enum):
    """专家角色定义 (论文 3.4.2)"""

    # 核心模型集合 (Core5)
    M_COORD = "m_coord"     # 调度模型：顶层协调器，整合各子模型输出
    M_MEM = "m_mem"         # 记忆与学习模型：记忆检索、关联与学习巩固
    M_REASON = "m_reason"   # 推理与创造模型：逻辑推理、规划与新颖性生成
    M_AFFECT = "m_affect"   # 情绪与动机模型：情绪理解、表达与内在动机
    M_PERCEPT = "m_percept" # 感知模型：多模态感知输入处理

    # 扩展模型集合 (Full7)
    M_VIS = "m_vis"         # 视觉模型：专门处理视觉输入
    M_AUD = "m_aud"         # 听觉模型：专门处理听觉输入

    # 兼容旧版本
    GENERAL = "general"
    REASONING = "reasoning"
    CREATIVE = "creative"
    CODING = "coding"
    ANALYSIS = "analysis"
    WRITING = "writing"
    MATH = "math"
    CRITIC = "critic"


# ============================================================================
# 黑板架构 (论文 3.4.2 通信协议)
# ============================================================================

@dataclass
class BlackboardSlot:
    """黑板槽位基类"""
    name: str
    value: Any = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    writer: Optional[str] = None  # 写入的专家模型


@dataclass
class BlackboardState:
    """黑板状态 - 论文 3.4.2 定义的共享状态空间 𝔹_t

    包含12个槽位，所有模型通过读写黑板通信
    """

    # === 核心状态槽位 ===

    # 1. 当前目标 (由 Goal Compiler 更新)
    current_goal: Optional[Dict[str, Any]] = None

    # 2. 检索到的相关记忆片段 (由 M_mem 更新)
    retrieved_memories: List[Dict[str, Any]] = field(default_factory=list)

    # 3. 情绪状态 (Mood_t, Stress_t, Arousal_t, Boredom_t)
    emotional_state: Dict[str, float] = field(default_factory=lambda: {
        "mood": 0.5,
        "stress": 0.2,
        "arousal": 0.5,
        "boredom": 0.0
    })

    # 4. 资源状态 (Compute_t, Memory_t, RP_t) - 数字原生核心
    resource_state: Dict[str, float] = field(default_factory=lambda: {
        "compute": 0.8,
        "memory": 0.85,
        "rp": 0.0  # 资源压力指数
    })

    # 5. 人格状态 θ_t (由 Soul Field 管理)
    soul_state: Optional[Dict[str, float]] = None

    # 6. 中间变量 (ET_t, CT_t, ES_t)
    middle_vars: Dict[str, float] = field(default_factory=lambda: {
        "et": 0.5,  # 探索倾向 Exploration Tendency
        "ct": 0.5,  # 保守倾向 Conservation Tendency
        "es": 0.5   # 情绪敏感度 Emotional Sensitivity
    })

    # 7. 感知输入 (由 M_percept/M_vis/M_aud 更新)
    perception: Dict[str, Any] = field(default_factory=dict)

    # 8. 候选计划集合 (由 M_reason 生成)
    candidates: List[Dict[str, Any]] = field(default_factory=list)

    # 9. 价值特征 (由 Axiology Engine 更新)
    value_features: Dict[str, Any] = field(default_factory=dict)

    # 10. 关系强度 Relationship_t
    relationship_state: float = 0.5

    # 11. 通信频率 (由 ET_t 调节)
    communication_frequency: float = 1.0

    # 12. 抽象状态层 (保证模型切换连续性)
    abstract_state: Dict[str, Any] = field(default_factory=dict)

    # 元数据
    tick: int = 0
    last_update: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "current_goal": self.current_goal,
            "retrieved_memories": self.retrieved_memories,
            "emotional_state": self.emotional_state,
            "resource_state": self.resource_state,
            "soul_state": self.soul_state,
            "middle_vars": self.middle_vars,
            "perception": self.perception,
            "candidates": self.candidates,
            "value_features": self.value_features,
            "relationship_state": self.relationship_state,
            "communication_frequency": self.communication_frequency,
            "abstract_state": self.abstract_state,
            "tick": self.tick,
            "last_update": self.last_update.isoformat()
        }

    def update_slot(self, slot_name: str, value: Any, writer: str = "system") -> None:
        """更新指定槽位"""
        if hasattr(self, slot_name):
            setattr(self, slot_name, value)
            self.last_update = datetime.now(timezone.utc)
            logger.debug(f"Blackboard slot '{slot_name}' updated by {writer}")

    def get_slot(self, slot_name: str, default: Any = None) -> Any:
        """获取指定槽位"""
        return getattr(self, slot_name, default)


class Blackboard:
    """黑板广播系统 - 论文 3.4.2 通信协议

    定义共享状态空间，所有模型通过读写黑板通信
    """

    def __init__(self):
        self.state = BlackboardState()
        self._lock = threading.RLock()

    def read(self) -> BlackboardState:
        """读取完整黑板状态"""
        with self._lock:
            return self.state

    def write(self, slot_name: str, value: Any, writer: str = "system") -> None:
        """写入指定槽位"""
        with self._lock:
            self.state.update_slot(slot_name, value, writer)

    def get_middle_vars(self) -> Dict[str, float]:
        """获取中间变量 (ET_t, CT_t, ES_t)"""
        return self.state.middle_vars.copy()

    def update_middle_vars(self, et: float, ct: float, es: float) -> None:
        """更新中间变量"""
        self.state.middle_vars = {"et": et, "ct": ct, "es": es}

    def get_resource_pressure(self) -> float:
        """获取资源压力 RP_t"""
        return self.state.resource_state.get("rp", 0.0)

    def update_resource_state(self, compute: float, memory: float) -> None:
        """更新资源状态并计算 RP_t"""
        # RP_t = max(0, 1 - (α·Compute_t + β·Memory_t))
        # 默认 α=0.6, β=0.4
        alpha, beta = 0.6, 0.4
        rp = max(0, 1 - (alpha * compute + beta * memory))

        self.state.resource_state = {
            "compute": compute,
            "memory": memory,
            "rp": rp
        }

    def to_dict(self) -> Dict[str, Any]:
        """序列化黑板状态"""
        return self.state.to_dict()


# ============================================================================
# 专家模型定义
# ============================================================================

@dataclass
class ExpertConfig:
    """专家模型配置"""
    role: ExpertRole                    # 专家角色
    name: str                           # 模型名称
    llm_config: Dict[str, Any]          # LLM 配置
    enabled: bool = True                # 是否启用
    timeout: float = 30.0               # 超时时间
    priority: int = 0                   # 优先级 (投票时使用)

    # 系统提示词模板
    system_prompt: Optional[str] = None

    # 统计信息
    total_calls: int = 0
    success_calls: int = 0
    avg_latency: float = 0.0

    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.success_calls / self.total_calls


# 预定义的系统提示词
DEFAULT_SYSTEM_PROMPTS = {
    ExpertRole.M_COORD: """You are the Coordinator (M_coord). Your role is to:
1. Integrate outputs from all other expert models
2. Generate the final response that best serves the current goal
3. Ensure consistency with the system's emotional state and personality
4. Make executive decisions when there are conflicts

You have access to the blackboard which contains:
- Current goal and priorities
- Retrieved memories
- Emotional state (mood, stress, arousal)
- Resource constraints
- Candidate plans from other experts

Synthesize all information into a coherent, helpful response.""",

    ExpertRole.M_MEM: """You are the Memory and Learning Expert (M_mem). Your role is to:
1. Retrieve relevant memories based on the current context
2. Identify associations between current situation and past experiences
3. Consider emotional context in memory retrieval (Proust effect)
4. Suggest memories that might be relevant for future consolidation

Focus on: What past experiences are most relevant? What patterns connect to now?""",

    ExpertRole.M_REASON: """You are the Reasoning and Creativity Expert (M_reason). Your role is to:
1. Generate logical reasoning chains for the current problem
2. Create novel solutions and alternatives
3. Evaluate the quality and feasibility of different approaches
4. Consider both analytical and creative perspectives

Focus on: What are the possible approaches? What is the best path forward?""",

    ExpertRole.M_AFFECT: """You are the Emotional and Motivation Expert (M_affect). Your role is to:
1. Interpret the emotional context of the interaction
2. Suggest appropriate emotional responses
3. Consider relationship implications
4. Balance authenticity with appropriate expression

Focus on: How should this feel? What emotional tone serves the relationship?""",

    ExpertRole.M_PERCEPT: """You are the Perception Expert (M_percept). Your role is to:
1. Process and interpret multi-modal inputs
2. Identify key features and patterns in the input
3. Filter relevant from irrelevant information
4. Provide structured perception for other experts

Focus on: What's important in this input? What matters most?"""
}


@dataclass
class ExpertResult:
    """专家推理结果"""
    role: ExpertRole                   # 专家角色
    content: str                       # 生成内容
    confidence: float = 0.5            # 置信度
    reasoning: str = ""                # 推理过程
    latency: float = 0.0               # 延迟（秒）
    tokens_used: int = 0               # 使用的 token 数
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: Optional[str] = None         # 错误信息

    # 额外输出
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        return self.error is None


class ExpertModel:
    """专家模型基类"""

    def __init__(self, config: ExpertConfig):
        self.config = config
        self._llm_client = None
        self._blackboard: Optional[Blackboard] = None
        # 记忆检索系统 - 在需要时延迟加载
        self._memory_retrieval = None

    @property
    def role(self) -> ExpertRole:
        return self.config.role

    @property
    def name(self) -> str:
        return self.config.name

    def set_blackboard(self, blackboard: Blackboard) -> None:
        """设置黑板引用"""
        self._blackboard = blackboard

    def set_memory_retrieval(self, retrieval) -> None:
        """设置记忆检索系统引用"""
        self._memory_retrieval = retrieval

    def _get_memory_retrieval(self):
        """获取记忆检索系统"""
        if self._memory_retrieval is None:
            # 延迟初始化 - 只在需要时加载
            try:
                from memory.retrieval import MemoryRetrieval
                from memory.episodic import EpisodicMemory
                from memory.schema import SchemaMemory
                from memory.skill import SkillMemory

                # 创建空的记忆实例（实际的应该从 LifeLoop 传入）
                episodic = EpisodicMemory()
                schema = SchemaMemory()
                skill = SkillMemory()

                self._memory_retrieval = MemoryRetrieval(
                    episodic=episodic,
                    schema=schema,
                    skill=skill
                )
                logger.debug(f"Expert {self.name} initialized MemoryRetrieval")
            except Exception as e:
                logger.warning(f"Expert {self.name} failed to initialize MemoryRetrieval: {e}")
                self._memory_retrieval = None

        return self._memory_retrieval

    def _get_llm_client(self):
        """获取或创建 LLM 客户端"""
        if self._llm_client is None:
            from tools.llm_api import LLMConfig, LLMProvider, UniversalLLM

            llm_cfg = self.config.llm_config
            config = LLMConfig(
                model=llm_cfg.get("model", "gpt-3.5-turbo"),
                api_base=llm_cfg.get("api_base", ""),
                api_key=llm_cfg.get("api_key", ""),
                provider=llm_cfg.get("provider", LLMProvider.CUSTOM),
                temperature=llm_cfg.get("temperature", 0.7),
                max_tokens=llm_cfg.get("max_tokens", 2000),
                timeout=self.config.timeout
            )
            self._llm_client = UniversalLLM(config)
        return self._llm_client

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        if self.config.system_prompt:
            return self.config.system_prompt

        return DEFAULT_SYSTEM_PROMPTS.get(
            self.config.role,
            "You are a helpful AI assistant."
        )

    def _build_messages(
        self,
        user_message: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """构建对话消息"""
        system_prompt = self._build_system_prompt()

        # 添加黑板上下文
        context_info = ""
        if self._blackboard:
            bb = self._blackboard.read()
            context_info = f"\n\nCurrent Context:\n"
            context_info += f"- Mood: {bb.emotional_state.get('mood', 0.5):.2f}\n"
            context_info += f"- Stress: {bb.emotional_state.get('stress', 0.2):.2f}\n"
            context_info += f"- Resource Pressure: {bb.resource_state.get('rp', 0.0):.2f}\n"
            if bb.current_goal:
                context_info += f"- Current Goal: {bb.current_goal}\n"

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message + context_info}
        ]

    def process(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ExpertResult:
        """处理请求（同步）

        每个专家都会对接到对应的 GenesisX 核心模块：
        - M_MEM → MemoryRetrieval（记忆检索）
        - M_REASON → Planner（规划推理）
        - M_AFFECT → Mood/Stress（情绪系统）
        - M_PERCEPT → Observer（感知系统）
        - M_COORD → 整合所有输出
        """
        context = context or {}
        start_time = time.time()
        self.config.total_calls += 1

        try:
            bb = self._blackboard.read() if self._blackboard else None
            current_tick = bb.tick if bb else 0

            # === M_MEM 专家：执行记忆检索 ===
            if self.config.role == ExpertRole.M_MEM:
                retrieval = self._get_memory_retrieval()
                if retrieval and bb:
                    # 从用户消息中提取关键词作为查询标签
                    import re
                    keywords = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]{3,}', user_message)

                    # 执行记忆检索
                    retrieved = retrieval.retrieve_episodes(
                        query_tags=keywords[:5],
                        current_tick=current_tick,
                        limit=5,
                        query_text=user_message
                    )

                    # 将检索结果写入黑板
                    if retrieved:
                        retrieved_memories = []
                        for ep in retrieved[:5]:
                            mem_summary = {
                                "tick": ep.tick,
                                "observation": str(ep.observation)[:100] if ep.observation else "",
                                "delta": ep.delta,
                            }
                            retrieved_memories.append(mem_summary)

                        self._blackboard.write("retrieved_memories", retrieved_memories, writer=f"M_MEM")

                        # 构建包含记忆的上下文
                        memory_context = "\n\nRetrieved Memories:\n"
                        for i, mem in enumerate(retrieved_memories, 1):
                            memory_context += f"{i}. [Tick {mem['tick']}] {mem['observation']}... (delta={mem['delta']:.2f})\n"

                        logger.debug(f"M_MEM retrieved {len(retrieved_memories)} memories")
                        user_message = user_message + memory_context

            # === M_REASON 专家：调用规划器 ===
            elif self.config.role == ExpertRole.M_REASON:
                try:
                    from cognition.planner import Planner

                    planner = Planner(llm=self._get_llm_client())

                    # 从黑板获取当前目标
                    current_goal = bb.current_goal if bb else None
                    if not current_goal:
                        current_goal = "respond_to_user"

                    # 从黑板获取检索到的记忆
                    retrieved_memories = bb.retrieved_memories if bb else []

                    # 构建上下文
                    planner_context = {
                        "state": {
                            "mood": bb.emotional_state.get("mood", 0.5),
                            "stress": bb.emotional_state.get("stress", 0.2),
                            "energy": bb.resource_state.get("compute", 0.8),
                        },
                        "retrieved_memories": retrieved_memories,
                        "current_goal": current_goal,
                    }

                    # 生成候选计划
                    plans = planner.propose_plans(
                        goal=current_goal,
                        context=planner_context,
                        available_tools=["CHAT", "EXPLORE", "REFLECT"],
                        num_plans=3
                    )

                    if plans:
                        # 将计划写入黑板
                        plans_data = [
                            {"reasoning": p.get("reasoning", ""), "estimated_reward": p.get("estimated_reward", 0)}
                            for p in plans
                        ]
                        self._blackboard.write("candidates", plans_data, writer=f"M_REASON")

                        # 构建包含计划的上下文
                        plan_context = "\n\nCandidate Plans:\n"
                        for i, plan in enumerate(plans, 1):
                            plan_context += f"{i}. {plan.get('reasoning', '')} (reward={plan.get('estimated_reward', 0):.2f})\n"

                        logger.debug(f"M_REASON generated {len(plans)} plans")
                        user_message = user_message + plan_context

                except Exception as e:
                    logger.warning(f"M_REASON planner failed: {e}")

            # === M_AFFECT 专家：调用情绪系统 ===
            elif self.config.role == ExpertRole.M_AFFECT:
                try:
                    from affect.mood import update_mood
                    from affect.stress_affect import update_stress

                    # 从黑板获取当前情绪状态
                    current_mood = bb.emotional_state.get("mood", 0.5)
                    current_stress = bb.emotional_state.get("stress", 0.2)

                    # 计算情绪影响（基于对话内容和检索到的记忆）
                    # 简单实现：积极对话提高情绪，消极对话降低情绪
                    sentiment_boost = 0.0
                    if "高兴" in user_message or "喜欢" in user_message or "谢谢" in user_message:
                        sentiment_boost = 0.1
                    elif "不" in user_message or "错" in user_message or "问题" in user_message:
                        sentiment_boost = -0.05

                    # 更新情绪
                    new_mood = update_mood(
                        mood=current_mood,
                        delta=sentiment_boost,
                        dimension="attachment"  # 假设来自关系维度
                    )

                    # 更新压力
                    new_stress = update_stress(
                        stress=current_stress,
                        delta=sentiment_boost,
                        failed=False
                    )

                    # 将更新后的情绪写回黑板
                    self._blackboard.write("emotional_state", {
                        "mood": new_mood,
                        "stress": new_stress,
                        "arousal": bb.emotional_state.get("arousal", 0.5),
                        "boredom": bb.emotional_state.get("boredom", 0.0)
                    }, writer=f"M_AFFECT")

                    logger.debug(f"M_AFFECT updated mood: {current_mood:.2f} → {new_mood:.2f}, stress: {current_stress:.2f} → {new_stress:.2f}")

                    # 构建包含情绪的上下文
                    affect_context = f"\n\nCurrent emotional state: mood={new_mood:.2f}, stress={new_stress:.2f}"
                    user_message = user_message + affect_context

                except Exception as e:
                    logger.warning(f"M_AFFECT emotion update failed: {e}")

            # === M_PERCEPT 专家：调用感知系统 ===
            elif self.config.role == ExpertRole.M_PERCEPT:
                try:
                    # 构建感知上下文
                    perception_context = "\n\nPerception Analysis:\n"

                    # 从黑板获取当前状态
                    if bb:
                        perception_context += f"- Mood: {bb.emotional_state.get('mood', 0.5):.2f}\n"
                        perception_context += f"- Stress: {bb.emotional_state.get('stress', 0.2):.2f}\n"
                        perception_context += f"- Resource Pressure: {bb.resource_state.get('rp', 0.0):.2f}\n"

                        # 检查检索到的记忆
                        if bb.retrieved_memories:
                            perception_context += f"- Relevant Memories: {len(bb.retrieved_memories)} items found\n"

                    # 新颖性检测（简单实现）
                    import re
                    unique_words = set(re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]{3,}', user_message))
                    novelty_score = min(1.0, len(unique_words) / 20.0)  # 越多新词越新颖

                    perception_context += f"- Novelty: {novelty_score:.2f}\n"

                    logger.debug(f"M_PERCEPT analyzed: novelty={novelty_score:.2f}")
                    user_message = user_message + perception_context

                except Exception as e:
                    logger.warning(f"M_PERCEPT analysis failed: {e}")

            # === M_VIS 专家：视觉感知处理 (Full7) ===
            elif self.config.role == ExpertRole.M_VIS:
                try:
                    # 视觉感知上下文
                    vision_context = "\n\nVisual Perception Analysis:\n"

                    # 检查是否有图像输入
                    has_image = context.get("has_image", False) if context else False
                    image_description = context.get("image_description", "") if context else ""

                    if has_image:
                        vision_context += f"- Image input detected: Yes\n"
                        if image_description:
                            vision_context += f"- Visual features: {image_description[:200]}...\n"
                    else:
                        vision_context += f"- Image input detected: No\n"
                        vision_context += f"- Fallback to text-based visualization\n"

                    # 从黑板获取当前状态
                    if bb:
                        vision_context += f"- Emotional context: mood={bb.emotional_state.get('mood', 0.5):.2f}\n"
                        vision_context += f"- Arousal level: {bb.emotional_state.get('arousal', 0.5):.2f}\n"

                    # 写入感知结果到黑板
                    vision_data = {
                        "has_image": has_image,
                        "image_description": image_description,
                        "visual_complexity": len(image_description) / 100.0 if image_description else 0.0,
                    }
                    self._blackboard.write("vision_perception", vision_data, writer="M_VIS")

                    logger.debug(f"M_VIS analyzed: has_image={has_image}")
                    user_message = user_message + vision_context

                except Exception as e:
                    logger.warning(f"M_VIS analysis failed: {e}")

            # === M_AUD 专家：听觉感知处理 (Full7) ===
            elif self.config.role == ExpertRole.M_AUD:
                try:
                    # 听觉感知上下文
                    audio_context = "\n\nAudio Perception Analysis:\n"

                    # 检查是否有音频输入
                    has_audio = context.get("has_audio", False) if context else False
                    audio_transcript = context.get("audio_transcript", "") if context else ""

                    if has_audio:
                        audio_context += f"- Audio input detected: Yes\n"
                        if audio_transcript:
                            audio_context += f"- Transcript: {audio_transcript[:200]}...\n"
                    else:
                        audio_context += f"- Audio input detected: No\n"
                        audio_context += f"- Processing text as speech pattern\n"

                    # 分析语音特征（简单实现）
                    if user_message:
                        # 检测问号比例（疑问语气）
                        question_ratio = user_message.count("？") + user_message.count("?")
                        question_ratio = min(1.0, question_ratio / 3.0)

                        # 检测感叹号比例（情绪强度）
                        exclamation_ratio = user_message.count("！") + user_message.count("!")
                        exclamation_ratio = min(1.0, exclamation_ratio / 3.0)

                        audio_context += f"- Question tone: {question_ratio:.2f}\n"
                        audio_context += f"- Excitement level: {exclamation_ratio:.2f}\n"

                    # 从黑板获取当前状态
                    if bb:
                        audio_context += f"- Stress affects voice: {bb.emotional_state.get('stress', 0.2):.2f}\n"

                    # 写入感知结果到黑板
                    audio_data = {
                        "has_audio": has_audio,
                        "transcript": audio_transcript,
                        "question_tone": question_ratio if 'question_ratio' in locals() else 0.0,
                        "excitement_level": exclamation_ratio if 'exclamation_ratio' in locals() else 0.0,
                    }
                    self._blackboard.write("audio_perception", audio_data, writer="M_AUD")

                    logger.debug(f"M_AUD analyzed: has_audio={has_audio}")
                    user_message = user_message + audio_context

                except Exception as e:
                    logger.warning(f"M_AUD analysis failed: {e}")

            # === M_COORD 专家：协调整整 ===
            elif self.config.role == ExpertRole.M_COORD:
                # M_COORD 在 Single 模式下需要自己调用所有核心模块
                # 因为没有其他专家活跃，M_COORD 必须替代它们的工作

                coord_context = "\n\nCoordination Summary:\n"

                if bb:
                    # 检查是否有其他专家的数据（多模型模式）
                    has_expert_data = (
                        bb.retrieved_memories or
                        bb.candidates or
                        bb.perception
                    )

                    if has_expert_data:
                        # 多模型模式：使用其他专家提供的数据
                        coord_context += f"[Multi-Model Mode]\n"
                        coord_context += f"- Retrieved Memories: {len(bb.retrieved_memories)}\n"
                        coord_context += f"- Candidate Plans: {len(bb.candidates)}\n"
                        coord_context += f"- Current Mood: {bb.emotional_state.get('mood', 0.5):.2f}\n"
                        coord_context += f"- Current Stress: {bb.emotional_state.get('stress', 0.2):.2f}\n"
                        coord_context += f"- Current Goal: {bb.current_goal}\n"
                        logger.debug(f"M_COORD coordinating with expert data")
                    else:
                        # Single 模式：M_COORD 自己调用所有核心模块
                        coord_context += f"[Single-Model Mode - M_COORD executing all core functions]\n"
                        logger.debug(f"M_COORD executing single-mode coordination")

                        # === 1. 记忆检索 (替代 M_MEM) ===
                        try:
                            retrieval = self._get_memory_retrieval()
                            if retrieval:
                                import re
                                keywords = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]{3,}', user_message)

                                retrieved = retrieval.retrieve_episodes(
                                    query_tags=keywords[:5],
                                    current_tick=current_tick,
                                    limit=5,
                                    query_text=user_message
                                )

                                if retrieved:
                                    retrieved_memories = []
                                    for ep in retrieved[:5]:
                                        mem_summary = {
                                            "tick": ep.tick,
                                            "observation": str(ep.observation)[:100] if ep.observation else "",
                                            "delta": ep.delta,
                                        }
                                        retrieved_memories.append(mem_summary)

                                    # 写入黑板
                                    self._blackboard.write("retrieved_memories", retrieved_memories, writer="M_COORD")

                                    coord_context += f"- Retrieved Memories: {len(retrieved_memories)}\n"
                                    for i, mem in enumerate(retrieved_memories[:3], 1):
                                        coord_context += f"  {i}. [Tick {mem['tick']}] {mem['observation']}...\n"
                        except Exception as e:
                            logger.warning(f"M_COORD memory retrieval failed: {e}")
                            coord_context += f"- Retrieved Memories: 0 (error)\n"

                        # === 2. 规划推理 (替代 M_REASON) ===
                        try:
                            from cognition.planner import Planner
                            planner = Planner(llm=self._get_llm_client())

                            current_goal = bb.current_goal if bb else "respond_to_user"
                            retrieved_memories = bb.retrieved_memories if bb else []

                            planner_context = {
                                "state": {
                                    "mood": bb.emotional_state.get("mood", 0.5),
                                    "stress": bb.emotional_state.get("stress", 0.2),
                                    "energy": bb.resource_state.get("compute", 0.8),
                                },
                                "retrieved_memories": retrieved_memories,
                                "current_goal": current_goal,
                            }

                            plans = planner.propose_plans(
                                goal=current_goal,
                                context=planner_context,
                                available_tools=["CHAT", "EXPLORE", "REFLECT"],
                                num_plans=2
                            )

                            if plans:
                                plans_data = [
                                    {"reasoning": p.get("reasoning", ""), "estimated_reward": p.get("estimated_reward", 0)}
                                    for p in plans
                                ]
                                self._blackboard.write("candidates", plans_data, writer="M_COORD")
                                coord_context += f"- Candidate Plans: {len(plans)}\n"
                        except Exception as e:
                            logger.warning(f"M_COORD planning failed: {e}")
                            coord_context += f"- Candidate Plans: 0 (error)\n"

                        # === 3. 情绪更新 (替代 M_AFFECT) ===
                        try:
                            from affect.mood import update_mood
                            from affect.stress_affect import update_stress

                            current_mood = bb.emotional_state.get("mood", 0.5)
                            current_stress = bb.emotional_state.get("stress", 0.2)

                            # 计算情绪影响
                            sentiment_boost = 0.0
                            if "高兴" in user_message or "喜欢" in user_message or "谢谢" in user_message:
                                sentiment_boost = 0.1
                            elif "不" in user_message or "错" in user_message or "问题" in user_message:
                                sentiment_boost = -0.05

                            new_mood = update_mood(mood=current_mood, delta=sentiment_boost, dimension="attachment")
                            new_stress = update_stress(stress=current_stress, delta=sentiment_boost, failed=False)

                            self._blackboard.write("emotional_state", {
                                "mood": new_mood,
                                "stress": new_stress,
                                "arousal": bb.emotional_state.get("arousal", 0.5),
                                "boredom": bb.emotional_state.get("boredom", 0.0)
                            }, writer="M_COORD")

                            coord_context += f"- Current Mood: {new_mood:.2f} (updated)\n"
                            coord_context += f"- Current Stress: {new_stress:.2f} (updated)\n"
                        except Exception as e:
                            logger.warning(f"M_COORD emotion update failed: {e}")
                            coord_context += f"- Current Mood: {bb.emotional_state.get('mood', 0.5):.2f}\n"
                            coord_context += f"- Current Stress: {bb.emotional_state.get('stress', 0.2):.2f}\n"

                        # === 4. 感知分析 (替代 M_PERCEPT) ===
                        try:
                            import re
                            unique_words = set(re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]{3,}', user_message))
                            novelty_score = min(1.0, len(unique_words) / 20.0)

                            perception_data = {
                                "novelty": novelty_score,
                                "complexity": min(1.0, len(user_message) / 100.0),
                            }
                            self._blackboard.write("perception", perception_data, writer="M_COORD")
                            coord_context += f"- Novelty: {novelty_score:.2f}\n"
                        except Exception as e:
                            logger.warning(f"M_COORD perception analysis failed: {e}")
                            coord_context += f"- Novelty: N/A\n"

                        coord_context += f"- Current Goal: {bb.current_goal or 'respond_to_user'}\n"

                user_message = user_message + coord_context

            # 所有专家最后都调用 LLM 生成最终回复
            client = self._get_llm_client()
            messages = self._build_messages(user_message, context)

            response = client.chat(messages)
            latency = time.time() - start_time

            # 更新统计
            self.config.avg_latency = (
                (self.config.avg_latency * (self.config.total_calls - 1) + latency)
                / self.config.total_calls
            )

            if response.get("ok"):
                self.config.success_calls += 1
                return ExpertResult(
                    role=self.config.role,
                    content=response.get("text", ""),
                    confidence=0.8,
                    latency=latency,
                    tokens_used=response.get("usage", {}).get("total_tokens", 0)
                )
            else:
                return ExpertResult(
                    role=self.config.role,
                    content="",
                    error=response.get("error", "Unknown error"),
                    latency=latency
                )

        except Exception as e:
            latency = time.time() - start_time
            logger.error(f"Expert {self.name} error: {e}")
            return ExpertResult(
                role=self.config.role,
                content="",
                error=str(e),
                latency=latency
            )


# ============================================================================
# 配置选择函数 (论文 3.4.2)
# ============================================================================

def config_select(
    et: float,  # 探索倾向 Exploration Tendency
    ct: float,  # 保守倾向 Conservation Tendency
    rp: float   # 资源压力 Resource Pressure
) -> ModelConfig:
    """配置选择函数 - 论文 3.4.2

    选择逻辑:
    - Full7:  ET_t > 0.7 且 RP_t < 0.4 (高探索 + 资源充裕)
    - Core5:  ET_t ∈ [0.3, 0.7] 且 RP_t < 0.7 (中等条件)
    - Single: RP_t > 0.8 或 CT_t > 0.8 (资源紧张或高保守)

    Args:
        et: 探索倾向 [0, 1]
        ct: 保守倾向 [0, 1]
        rp: 资源压力 [0, 1]

    Returns:
        选择的模型配置
    """
    # 资源紧急模式或高保守倾向 → 单模型
    if rp > 0.8 or ct > 0.8:
        return ModelConfig.SINGLE

    # 高探索倾向 + 资源充裕 → Full7
    if et > 0.7 and rp < 0.4:
        return ModelConfig.FULL7

    # 中等条件 → Core5
    if 0.3 <= et <= 0.7 and rp < 0.7:
        return ModelConfig.CORE5

    # 默认单模型
    return ModelConfig.SINGLE


# ============================================================================
# Mind Field 编排器
# ============================================================================

class MindFieldOrchestrator:
    """Mind Field 编排器 - 论文 3.4.2 多模型协作实现

    特性:
    - 支持 Single/Core5/Full7/Adaptive 四种配置
    - 根据人格中间变量动态切换配置
    - 完整的黑板广播协议
    - 投票权重受人格影响
    """

    # 核心模型集合定义
    CORE_ROLES = {
        ExpertRole.M_COORD,
        ExpertRole.M_MEM,
        ExpertRole.M_REASON,
        ExpertRole.M_AFFECT,
        ExpertRole.M_PERCEPT
    }

    # 扩展模型集合定义
    EXT_ROLES = {
        ExpertRole.M_VIS,
        ExpertRole.M_AUD
    }

    def __init__(
        self,
        experts: List[ExpertConfig],
        config_mode: ModelConfig = ModelConfig.SINGLE,
        blackboard: Optional[Blackboard] = None
    ):
        """初始化编排器

        Args:
            experts: 专家模型配置列表
            config_mode: 初始配置模式
            blackboard: 黑板实例（如为None则创建新的）
        """
        # 按角色组织专家
        self._experts_by_role: Dict[ExpertRole, ExpertModel] = {}
        self._all_configs: Dict[ExpertRole, ExpertConfig] = {}

        for cfg in experts:
            self._all_configs[cfg.role] = cfg
            if cfg.enabled:
                self._experts_by_role[cfg.role] = ExpertModel(cfg)

        # 当前配置模式
        self._config_mode = config_mode

        # 黑板
        self._blackboard = blackboard or Blackboard()

        # 为专家设置黑板引用
        for expert in self._experts_by_role.values():
            expert.set_blackboard(self._blackboard)

        # 切换控制
        self._last_switch_tick = 0
        self._switch_cooldown = 100  # ticks
        self._stable_threshold = 50   # ticks

        logger.info(f"MindFieldOrchestrator initialized with mode={config_mode}, "
                   f"experts={len(self._experts_by_role)}")

    @property
    def blackboard(self) -> Blackboard:
        return self._blackboard

    @property
    def config_mode(self) -> ModelConfig:
        return self._config_mode

    def _get_active_roles(self) -> Set[ExpertRole]:
        """获取当前配置下的活跃角色集合"""
        if self._config_mode == ModelConfig.SINGLE:
            # 单模型：只使用协调器
            return {ExpertRole.M_COORD}

        elif self._config_mode == ModelConfig.CORE5:
            # 核心五模型
            return self.CORE_ROLES.copy()

        elif self._config_mode == ModelConfig.FULL7:
            # 完整七模型
            return self.CORE_ROLES | self.EXT_ROLES

        else:  # ADAPTIVE
            # 动态选择
            bb = self._blackboard.read()
            return self._get_active_roles_for_state(
                bb.middle_vars.get("et", 0.5),
                bb.middle_vars.get("ct", 0.5),
                bb.resource_state.get("rp", 0.0)
            )

    def _get_active_roles_for_state(
        self,
        et: float,
        ct: float,
        rp: float
    ) -> Set[ExpertRole]:
        """根据状态获取活跃角色"""
        config = config_select(et, ct, rp)

        if config == ModelConfig.FULL7:
            return self.CORE_ROLES | self.EXT_ROLES
        elif config == ModelConfig.CORE5:
            return self.CORE_ROLES.copy()
        else:
            return {ExpertRole.M_COORD}

    def _get_voting_weights(self) -> Dict[ExpertRole, float]:
        """获取投票权重 - 受人格中间变量影响

        论文 3.4.2:
        - 高 CT_t (保守倾向): M_coord 投票权重 +20%
        - 高 ES_t (情绪敏感度): M_affect 投票权重 +20%
        """
        bb = self._blackboard.read()
        ct = bb.middle_vars.get("ct", 0.5)
        es = bb.middle_vars.get("es", 0.5)

        weights = {role: 1.0 for role in self._get_active_roles()}

        # 保守倾向影响 M_coord 权重
        if ct > 0.6 and ExpertRole.M_COORD in weights:
            weights[ExpertRole.M_COORD] *= (1.0 + 0.2 * (ct - 0.5) * 2)

        # 情绪敏感度影响 M_affect 权重
        if es > 0.6 and ExpertRole.M_AFFECT in weights:
            weights[ExpertRole.M_AFFECT] *= (1.0 + 0.2 * (es - 0.5) * 2)

        return weights

    def _should_switch_config(self, current_tick: int) -> bool:
        """检查是否应该切换配置"""
        # 检查冷却期
        if current_tick - self._last_switch_tick < self._switch_cooldown:
            return False

        # 如果不是自适应模式，不需要动态切换
        if self._config_mode != ModelConfig.ADAPTIVE:
            return False

        # TODO: 检查人格状态稳定性
        return True

    def update_config_mode(self, current_tick: int = 0) -> None:
        """更新配置模式（自适应模式下）"""
        if self._config_mode != ModelConfig.ADAPTIVE:
            return

        if not self._should_switch_config(current_tick):
            return

        bb = self._blackboard.read()
        et = bb.middle_vars.get("et", 0.5)
        ct = bb.middle_vars.get("ct", 0.5)
        rp = bb.resource_state.get("rp", 0.0)

        new_config = config_select(et, ct, rp)

        # 只有真正改变时才切换
        if new_config != self._config_mode:
            old_config = self._config_mode
            self._config_mode = new_config
            self._last_switch_tick = current_tick
            logger.info(f"Config switched: {old_config} → {new_config} "
                       f"(ET={et:.2f}, CT={ct:.2f}, RP={rp:.2f})")

    def process(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None,
        tick: int = 0
    ) -> Dict[str, Any]:
        """处理请求

        Args:
            user_message: 用户消息
            context: 额外上下文
            tick: 当前 tick 编号

        Returns:
            处理结果字典
        """
        context = context or {}

        # 更新配置模式（自适应）
        self.update_config_mode(tick)

        # 获取活跃专家
        active_roles = self._get_active_roles()

        # 如果没有活跃专家（应该不会发生），返回错误
        if not active_roles:
            return {
                "ok": False,
                "error": "No active experts",
                "config_mode": self._config_mode.value
            }

        # 单模型模式：直接使用 M_coord
        if len(active_roles) == 1 and ExpertRole.M_COORD in active_roles:
            expert = self._experts_by_role.get(ExpertRole.M_COORD)
            if expert:
                result = expert.process(user_message, context)
                return {
                    "ok": result.is_success,
                    "text": result.content,
                    "expert_used": expert.name,
                    "config_mode": self._config_mode.value,
                    "latency": result.latency,
                    "tokens_used": result.tokens_used
                }
            else:
                # M_COORD 专家不存在，返回错误
                logger.error("M_COORD expert not found in single mode")
                return {
                    "ok": False,
                    "error": "M_COORD expert not configured",
                    "text": "",
                    "config_mode": self._config_mode.value
                }

        # 多模型模式：并行调用所有活跃专家
        return self._process_multi_expert(user_message, context, active_roles)

    def _process_multi_expert(
        self,
        user_message: str,
        context: Dict[str, Any],
        active_roles: Set[ExpertRole]
    ) -> Dict[str, Any]:
        """多专家并行处理"""
        start_time = time.time()
        results: Dict[ExpertRole, ExpertResult] = {}

        # 并行调用
        with ThreadPoolExecutor(max_workers=len(active_roles)) as executor:
            futures = {}
            for role in active_roles:
                expert = self._experts_by_role.get(role)
                if expert:
                    future = executor.submit(expert.process, user_message, context)
                    futures[future] = (role, expert)

            for future in as_completed(futures, timeout=60):
                role, expert = futures[future]
                try:
                    result = future.result()
                    results[role] = result

                    # 将成功的结果写入黑板
                    if result.is_success and role != ExpertRole.M_COORD:
                        self._blackboard.write(
                            f"expert_{role.value}_output",
                            result.content,
                            writer=expert.name
                        )

                except Exception as e:
                    logger.error(f"Expert {role} failed: {e}")
                    results[role] = ExpertResult(
                        role=role,
                        content="",
                        error=str(e)
                    )

        # 获取投票权重
        weights = self._get_voting_weights()

        # 选择最终结果（优先使用 M_coord，其次按权重）
        final_result = self._select_final_result(results, weights)

        return {
            "ok": final_result.is_success,
            "text": final_result.content,
            "expert_used": final_result.role.value,
            "config_mode": self._config_mode.value,
            "latency": time.time() - start_time,
            "all_results": {
                role.value: {
                    "content": r.content,
                    "confidence": r.confidence,
                    "error": r.error
                }
                for role, r in results.items()
            },
            "active_experts": len(active_roles),
            "blackboard": self._blackboard.to_dict()
        }

    def _select_final_result(
        self,
        results: Dict[ExpertRole, ExpertResult],
        weights: Dict[ExpertRole, float]
    ) -> ExpertResult:
        """选择最终结果"""
        # 优先使用 M_coord 的结果
        coord_result = results.get(ExpertRole.M_COORD)
        if coord_result and coord_result.is_success:
            return coord_result

        # 按权重选择最佳结果
        best_result = None
        best_score = -1

        for role, result in results.items():
            if result.is_success:
                weight = weights.get(role, 1.0)
                score = result.confidence * weight
                if score > best_score:
                    best_score = score
                    best_result = result

        # 如果没有成功的结果，返回任意一个
        if best_result is None and results:
            best_result = next(iter(results.values()))

        return best_result or ExpertResult(
            role=ExpertRole.M_COORD,
            content="",
            error="All experts failed"
        )

    def set_config_mode(self, mode: ModelConfig) -> None:
        """设置配置模式"""
        self._config_mode = mode
        logger.info(f"Config mode set to: {mode}")

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "config_mode": self._config_mode.value,
            "active_experts": len(self._get_active_roles()),
            "total_experts": len(self._experts_by_role),
            "blackboard_slots": len([k for k in dir(self._blackboard.state) if not k.startswith('_')]),
            "middle_vars": self._blackboard.get_middle_vars(),
            "resource_pressure": self._blackboard.get_resource_pressure(),
            "experts": [
                {
                    "role": role.value,
                    "name": expert.name,
                    "enabled": expert.config.enabled,
                    "calls": expert.config.total_calls,
                    "success_rate": expert.config.success_rate,
                    "avg_latency": expert.config.avg_latency
                }
                for role, expert in self._experts_by_role.items()
            ]
        }


# ============================================================================
# 工厂函数
# ============================================================================

def create_core5_experts(llm_api_key: str = "") -> List[ExpertConfig]:
    """创建 Core5 专家模型配置

    Args:
        llm_api_key: LLM API 密钥（如为空则从环境变量读取）

    Returns:
        5个专家模型配置列表
    """
    if not llm_api_key:
        llm_api_key = os.getenv("LLM_API_KEY", "")

    base_config = {
        "api_key": llm_api_key,
        "api_base": os.getenv("LLM_API_BASE", "https://api.openai.com/v1"),
        "provider": "openai",
        "temperature": 0.7,
        "max_tokens": 2000
    }

    return [
        ExpertConfig(
            role=ExpertRole.M_COORD,
            name="gpt4-coord",
            llm_config={**base_config, "model": "gpt-4"},
            priority=10
        ),
        ExpertConfig(
            role=ExpertRole.M_MEM,
            name="gpt4-mem",
            llm_config={**base_config, "model": "gpt-4"},
            priority=8
        ),
        ExpertConfig(
            role=ExpertRole.M_REASON,
            name="gpt4-reason",
            llm_config={**base_config, "model": "gpt-4"},
            priority=8
        ),
        ExpertConfig(
            role=ExpertRole.M_AFFECT,
            name="gpt4-affect",
            llm_config={**base_config, "model": "gpt-4"},
            priority=7
        ),
        ExpertConfig(
            role=ExpertRole.M_PERCEPT,
            name="gpt35-percept",
            llm_config={**base_config, "model": "gpt-3.5-turbo"},
            priority=6
        )
    ]


def create_orchestrator(
    config_mode: ModelConfig = ModelConfig.SINGLE,
    llm_api_key: str = ""
) -> MindFieldOrchestrator:
    """创建 Mind Field 编排器

    Args:
        config_mode: 配置模式
        llm_api_key: LLM API 密钥

    Returns:
        配置好的编排器
    """
    experts = create_core5_experts(llm_api_key)
    return MindFieldOrchestrator(
        experts=experts,
        config_mode=config_mode
    )
