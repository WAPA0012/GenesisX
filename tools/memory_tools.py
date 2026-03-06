"""记忆工具 - AI可主动调用的记忆检索功能

通过 Function Calling 让 AI 自己决定何时检索记忆。
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass


# ============================================================================
# 记忆工具定义（供 Function Calling 使用）
# ============================================================================

MEMORY_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_memory",
            "description": "搜索历史记忆和对话记录。当你需要回忆之前的对话内容、用户提到过的信息、或者需要上下文来回答问题时使用此工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词或问题，例如：用户喜欢的电影、上次讨论的话题、用户的偏好等"
                    },
                    "search_type": {
                        "type": "string",
                        "enum": ["recent", "keyword", "semantic"],
                        "description": "搜索类型：recent=最近对话，keyword=关键词匹配，semantic=语义理解（最智能但较慢）"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回结果数量，默认5条",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_conversations",
            "description": "获取最近的对话记录，快速了解最近的交流内容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "description": "获取最近几条对话，默认5条",
                        "default": 5
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_to_memory",
            "description": "将重要信息保存到长期记忆中。当用户告诉你重要的事情（如喜好、个人信息、约定等）时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "要保存的内容"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "标签，便于后续检索，例如：['用户偏好', '电影', '喜好']"
                    },
                    "importance": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "重要性级别",
                        "default": "medium"
                    }
                },
                "required": ["content"]
            }
        }
    }
]


# ============================================================================
# 工具执行器
# ============================================================================

@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    result: Any
    error: Optional[str] = None


class MemoryToolExecutor:
    """记忆工具执行器

    处理 AI 调用的记忆相关工具。
    """

    def __init__(self, life_loop):
        """
        Args:
            life_loop: LifeLoop 实例，用于访问记忆系统
        """
        self.life_loop = life_loop

    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """执行工具调用

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            ToolResult 执行结果
        """
        try:
            if tool_name == "search_memory":
                return self._search_memory(
                    query=arguments.get("query", ""),
                    search_type=arguments.get("search_type", "keyword"),
                    limit=arguments.get("limit", 5)
                )
            elif tool_name == "get_recent_conversations":
                return self._get_recent_conversations(
                    count=arguments.get("count", 5)
                )
            elif tool_name == "save_to_memory":
                return self._save_to_memory(
                    content=arguments.get("content", ""),
                    tags=arguments.get("tags", []),
                    importance=arguments.get("importance", "medium")
                )
            else:
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"Unknown tool: {tool_name}"
                )
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=str(e)
            )

    def _search_memory(self, query: str, search_type: str, limit: int) -> ToolResult:
        """搜索记忆

        Args:
            query: 搜索查询
            search_type: 搜索类型
            limit: 结果数量限制

        Returns:
            ToolResult
        """
        if not self.life_loop:
            return ToolResult(success=False, result=None, error="记忆系统未初始化")

        try:
            # 提取搜索关键词
            keywords = query.split()[:5]

            # 根据搜索类型设置权重
            if search_type == "recent":
                recency_weight = 0.6
                salience_weight = 0.2
                keyword_weight = 0.2
                semantic_weight = 0.0
            elif search_type == "semantic":
                recency_weight = 0.2
                salience_weight = 0.2
                keyword_weight = 0.2
                semantic_weight = 0.4
            else:  # keyword
                recency_weight = 0.3
                salience_weight = 0.3
                keyword_weight = 0.4
                semantic_weight = 0.0

            # 执行检索
            episodes = self.life_loop.retrieval.retrieve_episodes(
                query_tags=keywords,
                query_text=query if semantic_weight > 0 else None,
                current_tick=self.life_loop.state.tick,
                limit=limit,
                recency_weight=recency_weight,
                salience_weight=salience_weight,
                keyword_weight=keyword_weight,
                semantic_weight=semantic_weight,
            )

            # 格式化结果
            results = []
            for ep in episodes:
                if hasattr(ep, 'action') and ep.action:
                    results.append({
                        "tick": ep.tick,
                        "action_type": ep.action.type.value if ep.action else None,
                        "content": ep.action.params if ep.action and ep.action.params else None,
                        "reward": ep.reward if hasattr(ep, 'reward') else None,
                    })

            return ToolResult(
                success=True,
                result={
                    "query": query,
                    "found": len(results),
                    "results": results
                }
            )

        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_recent_conversations(self, count: int) -> ToolResult:
        """获取最近对话

        Args:
            count: 数量

        Returns:
            ToolResult
        """
        if not self.life_loop:
            return ToolResult(success=False, result=None, error="记忆系统未初始化")

        try:
            episodes = self.life_loop.episodic.query_recent(count)

            results = []
            for ep in episodes:
                if hasattr(ep, 'action') and ep.action:
                    results.append({
                        "tick": ep.tick,
                        "action_type": ep.action.type.value if ep.action else None,
                        "content": ep.action.params if ep.action and ep.action.params else None,
                    })

            return ToolResult(
                success=True,
                result={
                    "count": len(results),
                    "conversations": results
                }
            )

        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _save_to_memory(self, content: str, tags: List[str], importance: str) -> ToolResult:
        """保存到记忆

        Args:
            content: 内容
            tags: 标签
            importance: 重要性

        Returns:
            ToolResult
        """
        if not self.life_loop:
            return ToolResult(success=False, result=None, error="记忆系统未初始化")

        try:
            # 保存到 schema memory
            from memory import SchemaEntry
            from datetime import datetime, timezone

            entry = SchemaEntry(
                content=content,
                tags=tags + [f"importance:{importance}"],
                confidence=0.9 if importance == "high" else 0.7,
                created_at=datetime.now(timezone.utc),
                evidence_count=1,
            )

            self.life_loop.schema.add(entry)

            return ToolResult(
                success=True,
                result={
                    "saved": True,
                    "content": content,
                    "tags": tags,
                    "importance": importance
                }
            )

        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))


# ============================================================================
# 辅助函数
# ============================================================================

def get_memory_tools_definition() -> List[Dict]:
    """获取记忆工具定义（供 Function Calling 使用）

    Returns:
        工具定义列表
    """
    return MEMORY_TOOLS


def format_tool_result_for_llm(tool_name: str, result: ToolResult) -> str:
    """格式化工具结果给 LLM

    Args:
        tool_name: 工具名称
        result: 执行结果

    Returns:
        格式化的字符串
    """
    if not result.success:
        return f"[{tool_name}] 执行失败: {result.error}"

    if tool_name == "search_memory":
        data = result.result
        if data["found"] == 0:
            return f"[搜索记忆] 没有找到关于 \"{data['query']}\" 的相关记忆。"
        else:
            lines = [f"[搜索记忆] 找到 {data['found']} 条相关记忆:"]
            for i, r in enumerate(data["results"], 1):
                content = r.get("content", {})
                if isinstance(content, dict):
                    msg = content.get("message", content.get("response", str(content)))
                else:
                    msg = str(content)
                lines.append(f"  {i}. Tick {r['tick']}: {msg[:100]}...")
            return "\n".join(lines)

    elif tool_name == "get_recent_conversations":
        data = result.result
        if data["count"] == 0:
            return "[最近对话] 暂无对话记录。"
        else:
            lines = [f"[最近对话] 获取到 {data['count']} 条记录:"]
            for i, r in enumerate(data["conversations"], 1):
                content = r.get("content", {})
                if isinstance(content, dict):
                    msg = content.get("message", content.get("response", str(content)))
                else:
                    msg = str(content)
                lines.append(f"  {i}. {msg[:100]}...")
            return "\n".join(lines)

    elif tool_name == "save_to_memory":
        data = result.result
        return f"[保存记忆] 已保存: \"{data['content'][:50]}...\" (重要性: {data['importance']})"

    return f"[{tool_name}] {result.result}"
