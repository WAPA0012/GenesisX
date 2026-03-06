# -*- coding: utf-8 -*-
"""
改进的工具系统 - 更接近 Claude Code 的能力

添加：
1. 智能意图检测
2. 代码/论文分析工具
3. 自动格式推断
4. 可回放性支持（输入输出hash记录）
"""

import os
import re
import hashlib
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field


@dataclass
class ToolCall:
    """工具调用请求"""
    tool_name: str
    description: str
    parameters: Dict[str, Any]
    category: str  # "read", "write", "execute", "network", "analyze"
    call_id: str = field(default="")
    timestamp: float = field(default_factory=time.time)


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    result: Any
    error: Optional[str] = None
    # 新增：可回放性支持字段
    call_id: str = ""
    input_hash: str = ""
    output_hash: str = ""
    execution_time: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class ToolCallRecord:
    """完整的工具调用记录，用于严格回放（Strict Replay）"""
    call_id: str
    tool_name: str
    parameters: Dict[str, Any]
    input_hash: str
    output: Any
    output_hash: str
    success: bool
    error: Optional[str]
    execution_time: float
    timestamp: float
    model_version: Optional[str] = None  # 对于LLM工具


class ToolCallLogger:
    """工具调用审计日志记录器"""

    def __init__(self, log_path: Optional[Path] = None):
        """初始化日志记录器

        Args:
            log_path: 日志文件路径，默认为 artifacts/run_*/tool_calls.jsonl
        """
        self.log_path = log_path or Path("artifacts/tool_calls.jsonl")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._records: List[ToolCallRecord] = []

    def compute_hash(self, data: Any) -> str:
        """计算数据的SHA256 hash（前16字符）

        Args:
            data: 要hash的数据

        Returns:
            Hash字符串（前16字符）
        """
        if isinstance(data, (dict, list)):
            content = json.dumps(data, sort_keys=True)
        else:
            content = str(data)
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    def log_call(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        output: Any,
        success: bool,
        error: Optional[str] = None,
        execution_time: float = 0.0,
        model_version: Optional[str] = None,
    ) -> ToolCallRecord:
        """记录工具调用

        Args:
            tool_name: 工具名称
            parameters: 输入参数
            output: 输出结果
            success: 是否成功
            error: 错误信息
            execution_time: 执行时间（秒）
            model_version: 模型版本（用于LLM调用）

        Returns:
            ToolCallRecord 记录对象
        """
        import uuid
        call_id = str(uuid.uuid4())[:16]

        record = ToolCallRecord(
            call_id=call_id,
            tool_name=tool_name,
            parameters=parameters,
            input_hash=self.compute_hash(parameters),
            output=output,
            output_hash=self.compute_hash(output) if success else "",
            success=success,
            error=error,
            execution_time=execution_time,
            timestamp=time.time(),
            model_version=model_version,
        )

        self._records.append(record)
        self._write_record(record)

        return record

    def _write_record(self, record: ToolCallRecord):
        """写入记录到文件

        Args:
            record: 工具调用记录
        """
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                # 将Pydantic模型或dataclass转换为字典
                record_dict = {
                    "call_id": record.call_id,
                    "tool_name": record.tool_name,
                    "parameters": record.parameters,
                    "input_hash": record.input_hash,
                    "output": record.output,
                    "output_hash": record.output_hash,
                    "success": record.success,
                    "error": record.error,
                    "execution_time": record.execution_time,
                    "timestamp": record.timestamp,
                    "model_version": record.model_version,
                }
                f.write(json.dumps(record_dict, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[ToolCallLogger] Failed to write record: {e}")

    def get_replay_output(self, tool_name: str, parameters: Dict[str, Any]) -> Optional[Any]:
        """获取历史输出用于回放

        Args:
            tool_name: 工具名称
            parameters: 输入参数

        Returns:
            历史输出（如果存在），否则返回None
        """
        input_hash = self.compute_hash(parameters)

        for record in reversed(self._records):
            if record.tool_name == tool_name and record.input_hash == input_hash:
                return record.output

        return None


class SmartToolParser:
    """智能工具解析器 - 从自然语言中提取工具调用意图"""

    @staticmethod
    def parse_tool_calls(text: str, available_tools: List[str] = None) -> List[ToolCall]:
        """智能解析 LLM 输出中的工具调用

        支持多种方式：
        1. 显式格式：[TOOL:read_file] {"path": "xxx"}
        2. JSON 代码块
        3. 自然语言意图推断（新）
        """
        import json

        tool_calls = []

        # ========== 格式1: 显式工具调用 ==========
        # [TOOL:tool_name] {"param": value}
        pattern1 = r'\[TOOL:(\w+)\]\s*(\{[^}]*\})'
        matches = re.findall(pattern1, text, re.DOTALL)

        for tool_name, params_str in matches:
            try:
                params = json.loads(params_str)
                tool_calls.append(ToolCall(
                    tool_name=tool_name,
                    description=f"调用 {tool_name}",
                    parameters=params,
                    category="unknown"
                ))
            except Exception:
                pass

        # ========== 格式2: JSON 代码块 ==========
        pattern2 = r'```(?:json)?\s*(\{[^}]*"tool"[^}]*\})\s*```'
        matches = re.findall(pattern2, text, re.DOTALL)

        for json_str in matches:
            try:
                data = json.loads(json_str)
                if "tool" in data:
                    tool_calls.append(ToolCall(
                        tool_name=data["tool"],
                        description=data.get("description", ""),
                        parameters=data.get("parameters", {}),
                        category=data.get("category", "unknown")
                    ))
            except Exception:
                pass

        # ========== 格式3: 自然语言意图推断（核心改进）==========

        # 3.1 文件读取意图 - 改进的正则表达式
        # 模式：
        #   - "读取xxx.txt"
        #   - "C:\path\to\file.txt，帮我看看"
        #   - "能帮我看一下这个论文吗" + 上一轮提到文件路径

        # 首先检测 Windows/Unix 路径格式（直接提供文件路径）
        path_pattern = r'(?:(?:[A-Za-z]:[\\/]|[~/.])[^\s"\'<>：：，、。；\n\r]+?\.[a-zA-Z0-9]+|(?:[A-Za-z]:[\\/])[^\s"\'<>：：，、。；\n\r]+)'
        paths = re.findall(path_pattern, text)

        for file_path in paths:
            file_path = file_path.strip('\'":，、。；\n\r')
            if len(file_path) > 5:  # 最小路径长度检查
                # 判断用户意图：如果提到"看、分析、读取、检查"等关键词
                intent_keywords = ['看', '分析', '读取', '检查', '审阅', '查看', '打开', '阅读', '帮我', '帮忙', '能否', '可以']
                has_intent = any(kw in text for kw in intent_keywords)

                if has_intent:
                    tool_calls.append(ToolCall(
                        tool_name="read_file",
                        description=f"读取文件: {file_path}",
                        parameters={"path": file_path},
                        category="read"
                    ))

        # 如果没有直接路径，检测 "读取/查看 + 文件名" 模式
        if not paths:
            read_patterns = [
                r'(?:读取|查看|打开|阅读|检查|分析|审阅|看看)(?:一下)?(?:文件)?[："\'\s，、]+([^\s"\'<>：：，、。；\n\r]+?)(?:[："\'\s，、。；]|$)',
                r'(?:read|open|view|check|analyze|review)[："\'\s]+([^\s"\'<>]+?)(?:[："\'\s]|$)',
            ]

            for pattern in read_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for file_path in matches:
                    file_path = file_path.strip('\'":，、。；')
                    if len(file_path) > 3:
                        tool_calls.append(ToolCall(
                            tool_name="read_file",
                            description=f"读取文件: {file_path}",
                            parameters={"path": file_path},
                            category="read"
                        ))

        # 3.2 文件写入意图
        # 模式：写入/创建/保存 + 文件路径
        write_pattern = r'(?:写入|创建|保存|生成)(?:文件)?[："\'\s]+([^\s"\'<>]+?)(?:[："\'\s]|$)'
        matches = re.findall(write_pattern, text, re.IGNORECASE)

        for file_path in matches:
            file_path = file_path.strip('\'":，、。；')
            if len(file_path) > 3:
                tool_calls.append(ToolCall(
                    tool_name="write_file",
                    description=f"写入文件: {file_path}",
                    parameters={"path": file_path, "content": ""},  # 内容需要后续填充
                    category="write"
                ))

        # 3.3 搜索意图
        # 模式：搜索/查找/找 + 关键词
        search_pattern = r'(?:搜索|查找|找)(?:文件)?[："\'\s]+([^\s"\'<>]+?)(?:[："\'\s]|$)'
        matches = re.findall(search_pattern, text, re.IGNORECASE)

        for search_term in matches:
            search_term = search_term.strip('\'":，、。；')
            if len(search_term) > 1:
                tool_calls.append(ToolCall(
                    tool_name="search_files",
                    description=f"搜索文件内容: {search_term}",
                    parameters={"directory": ".", "search_text": search_term},
                    category="read"
                ))

        # 3.4 列出文件意图
        if re.search(r'(?:列出|显示|查看).*(?:文件|目录|所有|有什么)', text, re.IGNORECASE):
            tool_calls.append(ToolCall(
                tool_name="list_files",
                description="列出文件",
                parameters={"directory": ".", "pattern": "*"},
                category="read"
            ))

        # 3.5 分析论文/代码意图（新增）
        if re.search(r'(?:论文|代码|文章).*?(?:有问题|怎么样|如何|分析)', text, re.IGNORECASE):
            # 尝试从上下文中提取文件路径
            path_pattern = r'[：:]\s*([A-Za-z]:\\\\[^：:\n]+|[A-Za-z]:/[^：:\n]+|[^：:\s\\\\/]+\.[a-z]{2,4})'
            paths = re.findall(path_pattern, text)

            for path in paths:
                path = path.strip()
                if len(path) > 5:
                    tool_calls.append(ToolCall(
                        tool_name="analyze_file",
                        description=f"分析文件: {path}",
                        parameters={"path": path, "file_type": "auto"},
                        category="analyze"
                    ))

        return tool_calls


class EnhancedToolExecutor:
    """增强的工具执行器（带可回放性支持）"""

    def __init__(self, log_path: Optional[Path] = None, replay_mode: bool = False):
        """初始化工具执行器

        Args:
            log_path: 工具调用日志路径
            replay_mode: 是否启用回放模式（Strict Replay）
        """
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.parser = SmartToolParser()
        self.logger = ToolCallLogger(log_path)
        self.replay_mode = replay_mode
        self._register_tools()

    def set_replay_mode(self, enabled: bool):
        """设置回放模式"""
        self.replay_mode = enabled

    def _register_tools(self):
        """注册所有工具"""

        # 基础工具
        self.tools["read_file"] = {
            "func": self._read_file,
            "category": "read",
            "description": "读取文件内容",
            "dangerous": False
        }

        self.tools["write_file"] = {
            "func": self._write_file,
            "category": "write",
            "description": "创建或覆写文件",
            "dangerous": True
        }

        self.tools["list_files"] = {
            "func": self._list_files,
            "category": "read",
            "description": "列出目录中的文件",
            "dangerous": False
        }

        self.tools["search_files"] = {
            "func": self._search_files,
            "category": "read",
            "description": "搜索包含特定内容的文件",
            "dangerous": False
        }

        # 新增：分析工具
        self.tools["analyze_file"] = {
            "func": self._analyze_file,
            "category": "analyze",
            "description": "分析论文或代码文件",
            "dangerous": False
        }

    def parse_and_execute(self, text: str) -> List[ToolResult]:
        """解析文本中的工具调用意图并执行"""
        tool_calls = self.parser.parse_tool_calls(text, list(self.tools.keys()))

        results = []
        for call in tool_calls:
            # 设置正确的分类
            if call.category == "unknown":
                tool_info = self.tools.get(call.tool_name, {})
                call.category = tool_info.get("category", "unknown")
                if not call.description or call.description == f"调用 {call.tool_name}":
                    call.description = tool_info.get("description", "")

            # 执行
            result = self._execute_with_permission(call)
            results.append(result)

        return results

    def _execute_with_permission(self, tool_call: ToolCall) -> ToolResult:
        """执行工具（带权限请求和hash记录）"""
        tool = self.tools.get(tool_call.tool_name)

        if not tool:
            result = ToolResult(
                success=False,
                result=None,
                error=f"未知工具: {tool_call.tool_name}"
            )
            return result

        # 显示工具调用信息
        print(f"\n[工具调用] {tool_call.tool_name}")
        print(f"  描述: {tool_call.description}")
        print(f"  参数: {tool_call.parameters}")

        # Strict Replay模式：检查是否有历史记录
        if self.replay_mode:
            replay_output = self.logger.get_replay_output(
                tool_call.tool_name,
                tool_call.parameters
            )
            if replay_output is not None:
                print(f"  [Replay] 使用历史输出")
                return ToolResult(
                    success=True,
                    result=replay_output,
                    call_id=tool_call.call_id,
                )

        # 请求许可（简化版，实际应该有用户交互）
        # 这里直接执行，因为用户已经表达了意图
        start_time = time.time()
        success = False
        result = None
        error = None

        try:
            func = tool["func"]
            result = func(**tool_call.parameters)
            success = True
        except Exception as e:
            error = str(e)

        execution_time = time.time() - start_time

        # 记录工具调用（可回放性）
        self.logger.log_call(
            tool_name=tool_call.tool_name,
            parameters=tool_call.parameters,
            output=result,
            success=success,
            error=error,
            execution_time=execution_time,
        )

        return ToolResult(
            success=success,
            result=result,
            error=error,
            call_id=tool_call.call_id,
            input_hash=self.logger.compute_hash(tool_call.parameters),
            output_hash=self.logger.compute_hash(result) if success else "",
            execution_time=execution_time,
        )

    # 工具实现
    def _read_file(self, path: str, limit: int = None) -> str:
        """读取文件"""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {path}")

        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            if limit:
                lines = []
                for i, line in enumerate(f):
                    if i >= limit:
                        break
                    lines.append(line.rstrip('\n'))
                return '\n'.join(lines)
            else:
                return f.read()

    def _write_file(self, path: str, content: str) -> str:
        """写入文件"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

        return f"已写入: {path} ({len(content)} 字符)"

    def _list_files(self, directory: str = ".", pattern: str = "*") -> List[str]:
        """列出文件"""
        path = Path(directory)
        if not path.exists():
            raise FileNotFoundError(f"目录不存在: {path}")

        files = list(path.glob(pattern))
        return [str(f) for f in files[:50]]  # 限制返回数量

    def _search_files(self, directory: str = ".", search_text: str = "") -> List[str]:
        """搜索文件内容"""
        path = Path(directory)
        matches = []

        for file_path in path.rglob("*"):
            if file_path.is_file():
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if search_text.lower() in content.lower():
                            matches.append(str(file_path))
                            if len(matches) >= 20:  # 限制结果数量
                                break
                except Exception:
                    pass

        return matches

    def _analyze_file(self, path: str, file_type: str = "auto") -> str:
        """分析文件内容（论文或代码）"""
        content = self._read_file(path)

        # 简单分析
        lines = content.split('\n')
        total_lines = len(lines)
        total_chars = len(content)

        # 检测文件类型
        if path.endswith('.txt') or path.endswith('.md'):
            file_type = "文本"
        elif path.endswith('.py'):
            file_type = "Python代码"
        elif path.endswith('.js'):
            file_type = "JavaScript代码"
        else:
            file_type = "未知类型"

        analysis = f"""文件分析报告:
- 文件路径: {path}
- 文件类型: {file_type}
- 总行数: {total_lines}
- 总字符数: {total_chars}

内容概要:
"""

        # 提取标题/章节（针对论文）
        if file_type == "文本":
            titles = [line for line in lines if re.match(r'^#{1,3}\s+', line)]
            if titles:
                analysis += "章节标题:\n"
                for title in titles[:10]:
                    analysis += f"  {title}\n"

        # 提取函数/类（针对代码）
        elif file_type == "Python代码":
            functions = [line for line in lines if line.strip().startswith('def ')]
            classes = [line for line in lines if line.strip().startswith('class ')]
            analysis += f"  函数数量: {len(functions)}\n"
            analysis += f"  类数量: {len(classes)}\n"
            if functions:
                analysis += "  函数列表:\n"
                for func in functions[:10]:
                    analysis += f"    {func.strip()}\n"

        return analysis


# 测试
if __name__ == "__main__":
    executor = EnhancedToolExecutor()

    test_texts = [
        "帮我看一下 C:\\Users\\test.txt 这个文件",
        "读取论文 xxx.txt",
        "搜索包含 Genesis X 的文件",
        "分析代码 main.py",
    ]

    for text in test_texts:
        print(f"\n输入: {text}")
        results = executor.parse_and_execute(text)
        for result in results:
            if result.success:
                print(f"结果: {result.result[:100]}...")
            else:
                print(f"错误: {result.error}")
