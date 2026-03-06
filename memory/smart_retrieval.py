"""智能检索决策模块

让AI决定是否需要执行语义检索，而不是每次都执行或完全禁用。

决策逻辑：
1. 简单问候/闲聊 → 不需要检索
2. 需要回忆对话 → 需要检索
3. 涉及用户个人信息/偏好 → 需要检索
4. 复杂问题/需要上下文 → 需要检索
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class RetrievalNeed(Enum):
    """检索需求级别"""
    NONE = "none"           # 不需要检索
    BASIC = "basic"         # 基础检索（最近记忆）
    SEMANTIC = "semantic"   # 语义检索（深度搜索）


@dataclass
class RetrievalDecision:
    """检索决策结果"""
    need: RetrievalNeed
    reason: str
    suggested_limit: int
    use_semantic: bool = False
    query_keywords: List[str] = None


# 不需要检索的模式（简单问候、确认等）
SIMPLE_PATTERNS = [
    r'^(你好|嗨|hi|hello|hey)[\s!！.。]*$',  # 简单问候
    r'^(谢谢|感谢|thanks|thank you)[\s!！.。]*$',  # 感谢
    r'^(好的|ok|嗯|哦|行)[\s!！.。]*$',  # 确认
    r'^(再见|拜拜|bye|goodbye)[\s!！.。]*$',  # 告别
    r'^(是|否|对|不对|是的|不是)[\s!！.。]*$',  # 简单回答
    r'^[👍👎😊😢😂❤️]+$',  # 纯表情
]

# 需要语义检索的关键词
SEMANTIC_KEYWORDS = [
    # 回忆类
    '上次', '之前', '以前', '记得', '回忆', '说过', '聊过', '讨论过',
    '记得吗', '忘了', '想起来',
    # 个人信息
    '我喜欢', '我讨厌', '我的', '我是', '我叫', '住在', '工作',
    '偏好', '爱好', '习惯',
    # 上下文依赖
    '那个', '这个', '它', '他', '她', '刚才', '之后', '然后',
    # 复杂问题
    '为什么', '怎么', '如何', '什么原因', '解释', '分析',
    '比较', '区别', '不同', '相同',
    # 延续对话
    '继续', '接着', '还有', '另外', '补充',
]

# 只需要基础检索的关键词
BASIC_KEYWORDS = [
    '今天', '现在', '当前', '最近', '刚刚',
    '怎么样', '如何', '什么',
]


def analyze_retrieval_need(message: str, context: Dict[str, Any] = None) -> RetrievalDecision:
    """分析消息是否需要检索

    Args:
        message: 用户消息
        context: 可选的上下文信息

    Returns:
        RetrievalDecision 决策结果
    """
    message_lower = message.lower().strip()

    # 1. 检查简单模式（不需要检索）
    for pattern in SIMPLE_PATTERNS:
        if re.match(pattern, message_lower, re.IGNORECASE):
            return RetrievalDecision(
                need=RetrievalNeed.NONE,
                reason="simple_greeting",
                suggested_limit=0
            )

    # 2. 检查消息长度（太短通常不需要深度检索）
    if len(message) < 5:
        return RetrievalDecision(
            need=RetrievalNeed.BASIC,
            reason="short_message",
            suggested_limit=3
        )

    # 3. 检查语义检索关键词
    semantic_matches = []
    for keyword in SEMANTIC_KEYWORDS:
        if keyword in message:
            semantic_matches.append(keyword)

    if semantic_matches:
        return RetrievalDecision(
            need=RetrievalNeed.SEMANTIC,
            reason=f"semantic_keywords: {semantic_matches[:3]}",
            suggested_limit=10,
            use_semantic=True,
            query_keywords=semantic_matches
        )

    # 4. 检查基础检索关键词
    basic_matches = []
    for keyword in BASIC_KEYWORDS:
        if keyword in message:
            basic_matches.append(keyword)

    if basic_matches:
        return RetrievalDecision(
            need=RetrievalNeed.BASIC,
            reason=f"basic_keywords: {basic_matches[:3]}",
            suggested_limit=5,
            use_semantic=False,
            query_keywords=basic_matches
        )

    # 5. 默认：根据消息复杂度决定
    # 计算消息复杂度（词数、问号数量等）
    word_count = len(message.split())
    question_marks = message.count('?') + message.count('？')

    if word_count > 20 or question_marks > 1:
        # 复杂消息，需要语义检索
        return RetrievalDecision(
            need=RetrievalNeed.SEMANTIC,
            reason="complex_message",
            suggested_limit=8,
            use_semantic=True
        )
    elif word_count > 10 or question_marks > 0:
        # 中等复杂度，基础检索
        return RetrievalDecision(
            need=RetrievalNeed.BASIC,
            reason="moderate_message",
            suggested_limit=5,
            use_semantic=False
        )
    else:
        # 简单消息，最少检索
        return RetrievalDecision(
            need=RetrievalNeed.BASIC,
            reason="simple_message",
            suggested_limit=3,
            use_semantic=False
        )


def get_retrieval_config(decision: RetrievalDecision) -> Dict[str, Any]:
    """根据决策获取检索配置

    Args:
        decision: 检索决策

    Returns:
        检索配置字典
    """
    if decision.need == RetrievalNeed.NONE:
        return {
            "limit": 0,
            "use_semantic": False,
            "semantic_weight": 0.0,
            "recency_weight": 0.0,
            "salience_weight": 0.0,
        }

    config = {
        "limit": decision.suggested_limit,
        "use_semantic": decision.use_semantic,
        "recency_weight": 0.4,
        "salience_weight": 0.4,
        "keyword_weight": 0.2,
        "semantic_weight": 0.0,
    }

    if decision.use_semantic:
        config["semantic_weight"] = 0.3
        config["recency_weight"] = 0.3
        config["salience_weight"] = 0.2
        config["keyword_weight"] = 0.2

    return config


# ============================================================================
# AI驱动的检索决策（可选，需要LLM）
# ============================================================================

async def ai_decide_retrieval(
    message: str,
    llm_client,
    conversation_history: List[Dict] = None
) -> RetrievalDecision:
    """使用AI决定是否需要检索

    这是一个更智能但更慢的决策方式，适合对响应质量要求高的场景。

    Args:
        message: 用户消息
        llm_client: LLM客户端
        conversation_history: 对话历史

    Returns:
        RetrievalDecision 决策结果
    """
    # 快速检查简单模式
    for pattern in SIMPLE_PATTERNS:
        if re.match(pattern, message.lower().strip(), re.IGNORECASE):
            return RetrievalDecision(
                need=RetrievalNeed.NONE,
                reason="simple_pattern",
                suggested_limit=0
            )

    # 构建决策提示
    prompt = f"""分析用户消息，判断是否需要从记忆中检索相关信息。

用户消息: "{message}"

请回答以下问题（只回答是或否）：
1. 是否需要回忆之前的对话内容？
2. 是否涉及用户的个人信息或偏好？
3. 是否需要上下文才能正确理解？

如果有任一答案是"是"，则需要检索。

请用以下格式回答：
NEED_RETRIEVAL: 是/否
RETRIEVAL_TYPE: none/basic/semantic
REASON: 简短原因"""

    try:
        result = llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.1  # 低温度确保一致性
        )

        if result.get("ok"):
            response = result.get("text", "").lower()

            if "need_retrieval: 否" in response or "need_retrieval: no" in response:
                return RetrievalDecision(
                    need=RetrievalNeed.NONE,
                    reason="ai_decided_none",
                    suggested_limit=0
                )

            if "semantic" in response:
                return RetrievalDecision(
                    need=RetrievalNeed.SEMANTIC,
                    reason="ai_decided_semantic",
                    suggested_limit=10,
                    use_semantic=True
                )

            return RetrievalDecision(
                need=RetrievalNeed.BASIC,
                reason="ai_decided_basic",
                suggested_limit=5
            )
    except Exception as e:
        # AI决策失败，降级到规则决策
        return analyze_retrieval_need(message)

    return analyze_retrieval_need(message)
