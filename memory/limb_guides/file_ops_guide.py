"""File operations skill."""
from typing import Dict, Any
import os
from pathlib import Path
from .base import BaseSkill, SkillResult, SkillCost


class FileSkill(BaseSkill):
    """文件操作技能

    读取和写入文件。
    """

    def __init__(self):
        super().__init__(
            name="file_ops",
            description="文件操作工具。支持读取文件内容、写入内容到文件。"
        )

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "操作类型：read（读取）或 write（写入）",
                    "enum": ["read", "write"]
                },
                "filepath": {
                    "type": "string",
                    "description": "文件路径（相对或绝对路径）"
                },
                "content": {
                    "type": "string",
                    "description": "要写入的内容（仅 write 操作需要）"
                },
            },
            "required": ["action", "filepath"]
        }

    def estimate_cost(self, **kwargs) -> SkillCost:
        action = kwargs.get("action", "read")
        if action == "write":
            content_length = len(kwargs.get("content", ""))
            return SkillCost(
                cpu_tokens=500 + content_length // 100,
                io_ops=1,
                time_seconds=0.5,
            )
        else:
            return SkillCost(
                cpu_tokens=200,
                io_ops=1,
                time_seconds=0.3,
            )

    def can_execute(self, **kwargs) -> tuple[bool, str | None]:
        action = kwargs.get("action")
        filepath = kwargs.get("filepath")

        if not action:
            return False, "缺少 action 参数"
        if action not in ["read", "write"]:
            return False, f"不支持的 action: {action}"
        if not filepath:
            return False, "缺少 filepath 参数"
        if action == "write" and not kwargs.get("content"):
            return False, "write 操作需要 content 参数"

        # 检查文件大小（读取时）
        if action == "read":
            try:
                abs_path = self._resolve_path(filepath)
                if os.path.exists(abs_path):
                    size = os.path.getsize(abs_path)
                    if size > 10000000:  # 10MB
                        return False, f"文件过大（{size} 字节，最大 10MB）"
            except:
                pass

        return True, None

    def execute(self, **kwargs) -> SkillResult:
        action = kwargs["action"]
        filepath = kwargs["filepath"]

        try:
            from tools.tool_executor import LLMToolExecutor
            executor = LLMToolExecutor(safe_mode=False)

            if action == "read":
                result = executor._read_file(filepath)
                # 判断是否成功
                if not result.startswith("错误:"):
                    return SkillResult(
                        success=True,
                        message=f"已读取文件：{filepath}",
                        data={"filepath": filepath, "content": result},
                        cost=self.estimate_cost(action=action),
                    )
                else:
                    return SkillResult(
                        success=False,
                        message="读取失败",
                        error=result,
                        cost=SkillCost(cpu_tokens=100),
                    )

            else:  # write
                content = kwargs["content"]
                result = executor._write_file(filepath, content)
                if result.startswith("成功写入"):
                    return SkillResult(
                        success=True,
                        message=result,
                        data={"filepath": filepath, "size": len(content)},
                        cost=self.estimate_cost(action=action, content=content),
                    )
                else:
                    return SkillResult(
                        success=False,
                        message="写入失败",
                        error=result,
                        cost=SkillCost(cpu_tokens=200),
                    )

        except Exception as e:
            return SkillResult(
                success=False,
                message=f"{action} 操作异常",
                error=str(e),
                cost=SkillCost(cpu_tokens=100),
            )

    def _resolve_path(self, path: str) -> str:
        """解析路径"""
        if not os.path.isabs(path):
            return os.path.abspath(path)
        return path
