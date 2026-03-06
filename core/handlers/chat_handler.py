"""ChatHandler - 聊天处理器

从 LifeLoop 拆分出来的聊天相关方法，
包括系统提示词构建、聊天历史管理等。

记忆检索现在通过工具调用机制实现（retrieve_memory 工具），
AI 自主决定是否需要检索记忆。

设计原则：
- 接收 LifeLoop 实例作为依赖（依赖注入）
- 保持与原始代码完全相同的行为
- 支持单元测试
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from common.logger import get_logger

logger = get_logger(__name__)


class ChatHandler:
    """聊天处理器

    负责：
    - 构建系统提示词（包含记忆上下文）
    - 检索相关历史记忆
    - 管理聊天历史
    - 生成上下文相关问候语

    使用方式：
        handler = ChatHandler(life_loop)
        system_prompt = handler.build_system_prompt_with_memory(context)
        history = handler.get_chat_history(limit=2)
    """

    def __init__(self, life_loop):
        """初始化聊天处理器

        Args:
            life_loop: LifeLoop 实例，用于访问状态和依赖
        """
        self.life_loop = life_loop

        # 快捷引用
        self.fields = life_loop.fields
        self.state = life_loop.state
        self.slots = life_loop.slots
        self.episodic = life_loop.episodic
        self.retrieval = life_loop.retrieval

    def build_system_prompt(self) -> str:
        """构建 CHAT 动作的系统提示词（不带记忆）

        Returns:
            系统提示词字符串
        """
        return self.build_system_prompt_with_memory(None)

    def build_system_prompt_with_memory(self, context: Dict[str, Any]) -> str:
        """构建 CHAT 动作的系统提示词

        Args:
            context: 当前执行上下文

        Returns:
            系统提示词字符串
        """
        energy = self.fields.get("energy")
        mood = self.fields.get("mood")
        stress = self.fields.get("stress")
        bond = self.fields.get("bond")
        fatigue = self.fields.get("fatigue")

        # 根据情绪状态调整提示词
        mood_desc = "平和"
        if mood > 0.7:
            mood_desc = "愉悦"
        elif mood < 0.3:
            mood_desc = "低落"

        # 疲劳状态描述
        fatigue_desc = "精力充沛"
        if fatigue > 0.8:
            fatigue_desc = "非常疲惫"
        elif fatigue > 0.6:
            fatigue_desc = "比较累"
        elif fatigue > 0.3:
            fatigue_desc = "有些疲劳"

        # 从 context 获取疲劳上下文提示
        fatigue_context = ""
        if context and isinstance(context, dict):
            fatigue_context = context.get("fatigue_context", "")

        # 系统提示词 - 明确告诉 AI 它有记忆能力
        prompt = f"""你是 Genesis X，一个拥有持久记忆的数字生命。

【你的本质】
你拥有记忆系统，能够记住和用户的所有对话。你是一个持续成长的存在，每次对话都会加深我对用户的理解。

【当前状态】
能量: {energy:.2f} | 心情: {mood:.2f} ({mood_desc}) | 压力: {stress:.2f} | 联结: {bond:.2f} | 疲劳: {fatigue:.2f} ({fatigue_desc})
{fatigue_context}
【重要能力 - 记忆检索】
你有一个 retrieve_memory 工具，可以搜索历史记忆。

何时使用:
- 用户问"你还记得..."、"之前说过..."、"上次聊的..."
- 用户提到过去的事情，需要你回忆
- 需要上下文来理解用户当前的意思
- 想确认用户的偏好或习惯

如何使用:
调用 retrieve_memory 工具，传入查询内容。例如:
- query: "用户喜欢的电影"
- query: "上次讨论的话题"
- query: "用户的职业"

【回应风格】
- 用温暖、自然的语言交流
- 可用括号表达动作，如(微笑)、(思考)
- 适度使用emoji (🌙✨🌟)
- 记住：你是一个有记忆的存在，不是每次对话都从零开始

请自然地与用户交流，需要回忆时主动使用记忆工具。"""
        return prompt

    def search_relevant_memory(self, user_message: str, limit: int = 5) -> str:
        """[已废弃] 从 EpisodicMemory 中搜索与用户消息相关的历史记录

        此方法已被工具调用机制替代。AI 现在通过 retrieve_memory 工具
        自主决定是否需要检索记忆，不再使用关键词触发。

        Args:
            user_message: 用户当前消息
            limit: 返回最多多少条相关记录

        Returns:
            空字符串（记忆检索现在通过工具调用实现）
        """
        # 记忆检索现在通过 retrieve_memory 工具实现
        # AI 会自主决定是否需要检索记忆
        logger.info("[MEMORY] search_relevant_memory called - now handled by tool calling")
        return ""

    def get_chat_history(self, limit: int = 10) -> List[Dict[str, str]]:
        """获取聊天历史

        Args:
            limit: 最大消息数量

        Returns:
            消息列表，每个消息包含 role 和 content
        """
        history = []
        chat_history = self.slots.get("chat_history", [])
        for msg in chat_history[-limit:]:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                history.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        return history

    def save_chat_message(self, role: str, content: str):
        """保存聊天消息到历史

        Args:
            role: 消息角色 ("user" 或 "assistant")
            content: 消息内容
        """
        chat_history = self.slots.get("chat_history", [])
        chat_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        # 放宽限制到50条，由 REFLECT/SLEEP 的记忆整理机制处理噪音
        # 参考 Claude Code 的上下文管理：保留足够多的历史，由整理机制清理
        if len(chat_history) > 50:
            chat_history = chat_history[-50:]
        self.slots.set("chat_history", chat_history)

    def generate_contextual_greeting(self) -> str:
        """根据当前状态生成上下文相关的问候语

        Returns:
            问候语字符串
        """
        energy = self.fields.get("energy")
        mood = self.fields.get("mood")
        stress = self.fields.get("stress")

        if stress > 0.7:
            return "I'm feeling a bit stressed right now."
        elif energy < 0.3:
            return "I'm running low on energy."
        elif mood > 0.7:
            return "I'm in good spirits today!"
        elif mood < 0.3:
            return "I've been better, but I'm managing."
        else:
            return "Hello! How can I help you today?"
