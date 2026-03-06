"""PDF generation skill."""
from typing import Dict, Any
import os
from pathlib import Path
from .base import BaseSkill, SkillResult, SkillCost


class PDFSkill(BaseSkill):
    """PDF 生成技能

    将文本内容生成 PDF 文件。
    """

    def __init__(self):
        super().__init__(
            name="generate_pdf",
            description="将文本内容生成 PDF 文件。支持中文字体，自动处理分页和格式。"
        )

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "PDF 文件保存路径（相对或绝对路径）"
                },
                "content": {
                    "type": "string",
                    "description": "PDF 内容（支持 Markdown 风格，会用空行分段）"
                },
                "title": {
                    "type": "string",
                    "description": "PDF 文档标题（显示在第一行）"
                },
            },
            "required": ["filepath", "content"]
        }

    def estimate_cost(self, **kwargs) -> SkillCost:
        content_length = len(kwargs.get("content", ""))
        return SkillCost(
            cpu_tokens=1000 + content_length // 10,
            io_ops=1,
            time_seconds=1.0 + content_length / 10000,
        )

    def can_execute(self, **kwargs) -> tuple[bool, str | None]:
        filepath = kwargs.get("filepath")
        if not filepath:
            return False, "缺少 filepath 参数"

        content = kwargs.get("content")
        if not content:
            return False, "缺少 content 参数"

        if len(content) > 100000:
            return False, "内容过长（最大 100000 字符）"

        return True, None

    def execute(self, **kwargs) -> SkillResult:
        filepath = kwargs["filepath"]
        content = kwargs["content"]
        title = kwargs.get("title", "Document")

        try:
            # 使用 tool_executor 中的 PDF 生成函数
            from tools.tool_executor import LLMToolExecutor
            executor = LLMToolExecutor(safe_mode=False)
            result = executor._create_pdf_helper(filepath, content, title)

            if result.startswith("✅"):
                # 获取文件大小
                abs_path = self._resolve_path(filepath)
                size = os.path.getsize(abs_path) if os.path.exists(abs_path) else 0

                return SkillResult(
                    success=True,
                    message=result,
                    data={"filepath": abs_path, "size": size},
                    cost=self.estimate_cost(content=content),
                )
            else:
                return SkillResult(
                    success=False,
                    message="PDF 生成失败",
                    error=result,
                    cost=SkillCost(cpu_tokens=100),
                )

        except Exception as e:
            return SkillResult(
                success=False,
                message="PDF 生成异常",
                error=str(e),
                cost=SkillCost(cpu_tokens=100),
            )

    def _resolve_path(self, path: str) -> str:
        """解析路径"""
        if not os.path.isabs(path):
            return os.path.abspath(path)
        return path
