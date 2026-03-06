"""Data analysis skill."""
from typing import Dict, Any, List
import json
import re
from .base import BaseSkill, SkillResult, SkillCost


class AnalysisSkill(BaseSkill):
    """数据分析技能

    对文本数据进行分析：统计、提取、总结等。
    """

    def __init__(self):
        super().__init__(
            name="analyze_data",
            description="数据分析工具。支持文本统计、关键词提取、简单聚合计算等。"
        )

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "分析类型",
                    "enum": [
                        "count_words",      # 统计字数
                        "count_lines",      # 统计行数
                        "extract_numbers",  # 提取数字
                        "extract_urls",     # 提取 URL
                        "extract_emails",   # 提取邮箱
                        "sum",              # 求和
                        "average",          # 平均值
                        "max",              # 最大值
                        "min",              # 最小值
                        "frequency",        # 词频统计
                        "summary",          # 简单总结
                    ]
                },
                "data": {
                    "type": "string",
                    "description": "要分析的数据（文本或 JSON 数组）"
                },
            },
            "required": ["operation", "data"]
        }

    def estimate_cost(self, **kwargs) -> SkillCost:
        data_length = len(kwargs.get("data", ""))
        return SkillCost(
            cpu_tokens=500 + data_length // 100,
            time_seconds=0.5,
        )

    def can_execute(self, **kwargs) -> tuple[bool, str | None]:
        operation = kwargs.get("operation")
        data = kwargs.get("data")

        if not operation:
            return False, "缺少 operation 参数"
        if not data:
            return False, "缺少 data 参数"

        valid_ops = [
            "count_words", "count_lines", "extract_numbers", "extract_urls",
            "extract_emails", "sum", "average", "max", "min", "frequency", "summary"
        ]
        if operation not in valid_ops:
            return False, f"不支持的 operation: {operation}"

        if len(data) > 1000000:
            return False, "数据过大（最大 1000000 字符）"

        return True, None

    def execute(self, **kwargs) -> SkillResult:
        operation = kwargs["operation"]
        data = kwargs["data"]

        try:
            if operation == "count_words":
                result = self._count_words(data)
            elif operation == "count_lines":
                result = self._count_lines(data)
            elif operation == "extract_numbers":
                result = self._extract_numbers(data)
            elif operation == "extract_urls":
                result = self._extract_urls(data)
            elif operation == "extract_emails":
                result = self._extract_emails(data)
            elif operation == "sum":
                result = self._sum(data)
            elif operation == "average":
                result = self._average(data)
            elif operation == "max":
                result = self._max(data)
            elif operation == "min":
                result = self._min(data)
            elif operation == "frequency":
                result = self._frequency(data)
            elif operation == "summary":
                result = self._summary(data)
            else:
                result = {"error": f"未知操作: {operation}"}

            return SkillResult(
                success=True,
                message=f"分析完成：{operation}",
                data=result,
                cost=self.estimate_cost(operation=operation, data=data),
            )

        except Exception as e:
            return SkillResult(
                success=False,
                message=f"分析失败：{operation}",
                error=str(e),
                cost=SkillCost(cpu_tokens=200),
            )

    def _count_words(self, text: str) -> Dict[str, Any]:
        words = text.split()
        return {"count": len(words), "chars": len(text)}

    def _count_lines(self, text: str) -> Dict[str, Any]:
        lines = text.split("\n")
        non_empty = [l for l in lines if l.strip()]
        return {"total_lines": len(lines), "non_empty_lines": len(non_empty)}

    def _extract_numbers(self, text: str) -> Dict[str, Any]:
        # 提取所有数字（整数和小数）
        numbers = re.findall(r"-?\d+\.?\d*", text)
        numbers = [float(n) for n in numbers if n]
        return {"numbers": numbers[:100], "count": len(numbers)}  # 最多返回100个

    def _extract_urls(self, text: str) -> Dict[str, Any]:
        # 简单的 URL 提取
        url_pattern = r"https?://[^\s]+"
        urls = re.findall(url_pattern, text)
        return {"urls": urls[:50], "count": len(urls)}

    def _extract_emails(self, text: str) -> Dict[str, Any]:
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        emails = re.findall(email_pattern, text)
        return {"emails": emails[:50], "count": len(emails)}

    def _sum(self, data: str) -> Dict[str, Any]:
        # 尝试解析为数字列表
        numbers = self._parse_numbers(data)
        return {"sum": sum(numbers), "count": len(numbers)}

    def _average(self, data: str) -> Dict[str, Any]:
        numbers = self._parse_numbers(data)
        if numbers:
            return {"average": sum(numbers) / len(numbers), "count": len(numbers)}
        return {"error": "没有找到数字"}

    def _max(self, data: str) -> Dict[str, Any]:
        numbers = self._parse_numbers(data)
        if numbers:
            return {"max": max(numbers)}
        return {"error": "没有找到数字"}

    def _min(self, data: str) -> Dict[str, Any]:
        numbers = self._parse_numbers(data)
        if numbers:
            return {"min": min(numbers)}
        return {"error": "没有找到数字"}

    def _frequency(self, text: str) -> Dict[str, Any]:
        words = text.lower().split()
        freq = {}
        for word in words:
            word = word.strip(".,!?;:\"'()[]{}")
            if len(word) > 1:  # 忽略单字符
                freq[word] = freq.get(word, 0) + 1

        # 排序并取前20
        sorted_freq = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:20]
        return {"top_words": dict(sorted_freq)}

    def _summary(self, data: str) -> Dict[str, Any]:
        return {
            "length": len(data),
            "words": len(data.split()),
            "lines": len(data.split("\n")),
            "has_numbers": bool(re.search(r"\d", data)),
            "has_urls": bool(re.search(r"https?://", data)),
        }

    def _parse_numbers(self, data: str) -> List[float]:
        # 先尝试 JSON 解析
        try:
            parsed = json.loads(data)
            if isinstance(parsed, list):
                return [float(x) for x in parsed if self._is_number(x)]
        except:
            pass

        # 否则从文本提取数字
        numbers = re.findall(r"-?\d+\.?\d*", data)
        return [float(n) for n in numbers if n]

    def _is_number(self, x) -> bool:
        try:
            float(x)
            return True
        except:
            return False
