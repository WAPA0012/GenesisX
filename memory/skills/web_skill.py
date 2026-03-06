"""Web search and fetch skill."""
from typing import Dict, Any
from .base import BaseSkill, SkillResult, SkillCost


class WebSkill(BaseSkill):
    """网络搜索和获取技能

    执行网络搜索或获取网页内容。
    """

    def __init__(self):
        super().__init__(
            name="web_search",
            description="搜索网络信息。输入查询内容，返回相关的搜索结果摘要。"
        )

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询内容"
                },
                "depth": {
                    "type": "string",
                    "description": "搜索深度：shallow（快速）或 deep（详细）",
                    "enum": ["shallow", "deep"]
                },
            },
            "required": ["query"]
        }

    def estimate_cost(self, **kwargs) -> SkillCost:
        depth = kwargs.get("depth", "shallow")
        base_cost = 5000 if depth == "deep" else 2000
        return SkillCost(
            cpu_tokens=base_cost,
            net_bytes=50000,
            time_seconds=3.0 if depth == "deep" else 1.0,
        )

    def can_execute(self, **kwargs) -> tuple[bool, str | None]:
        query = kwargs.get("query")
        if not query:
            return False, "缺少 query 参数"
        if len(query) > 500:
            return False, "查询过长（最大 500 字符）"
        return True, None

    def execute(self, **kwargs) -> SkillResult:
        query = kwargs["query"]
        depth = kwargs.get("depth", "shallow")

        try:
            # 使用 tool_executor 中的网络搜索功能
            from tools.tool_executor import LLMToolExecutor
            executor = LLMToolExecutor(safe_mode=False)
            result = executor._web_search(query)

            # 简单判断是否成功
            if not result.startswith("搜索失败") and not result.startswith("搜索暂时不可用"):
                return SkillResult(
                    success=True,
                    message=f"搜索完成：{query}",
                    data={"query": query, "results": result},
                    cost=self.estimate_cost(query=query, depth=depth),
                )
            else:
                return SkillResult(
                    success=False,
                    message="搜索失败",
                    error=result,
                    cost=SkillCost(cpu_tokens=500),
                )

        except Exception as e:
            return SkillResult(
                success=False,
                message="搜索异常",
                error=str(e),
                cost=SkillCost(cpu_tokens=500),
            )
