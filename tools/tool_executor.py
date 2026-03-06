"""Tool executor for function calling.

执行 LLM 返回的工具调用。
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from .tool_definitions import get_tool_definition

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class LLMToolExecutor:
    """LLM 工具执行器 - 执行 LLM 返回的工具调用

    重命名说明: 原 ToolExecutor 重命名为 LLMToolExecutor 以避免与
    tool_protocol.py 中的 ToolExecutor 类冲突。
    tool_protocol.ToolExecutor 是抽象的工具包装器，用于风险管理。
    LLMToolExecutor 是具体的执行器，用于处理 LLM 函数调用。
    """

    def __init__(self, safe_mode: bool = False):
        """初始化工具执行器

        Args:
            safe_mode: 安全模式，限制某些危险操作 (默认False = OpenCLAW模式)
        """
        self.safe_mode = safe_mode

        # 被禁用的工具（安全模式下）
        self.disabled_tools = set()
        if safe_mode:
            self.disabled_tools = {"write_file", "execute_code", "web_search"}

        # 缓存常用路径
        self._path_aliases = self._init_path_aliases()

    def _init_path_aliases(self) -> dict:
        """初始化路径别名，方便 LLM 使用"""
        import os
        aliases = {}
        home = os.path.expanduser("~")
        aliases["~"] = home
        aliases["home"] = home
        aliases["用户目录"] = home

        # 桌面路径（处理中文桌面）
        desktop = os.path.join(home, "Desktop")
        if not os.path.exists(desktop):
            # 可能是中文桌面
            desktop = os.path.join(home, "桌面")
        aliases["desktop"] = desktop
        aliases["桌面"] = desktop
        aliases["Desktop"] = desktop

        # 文档目录
        documents = os.path.join(home, "Documents")
        if not os.path.exists(documents):
            documents = os.path.join(home, "文档")
        aliases["documents"] = documents
        aliases["文档"] = documents
        aliases["Documents"] = documents

        return aliases

    def _try_import(self, module_name: str):
        """安全地尝试导入模块"""
        try:
            return __import__(module_name)
        except ImportError:
            return None

    def _create_pdf_helper(self, filepath: str, text_content: str, title: str = "Document") -> str:
        """创建 PDF 文件的辅助函数

        Args:
            filepath: PDF 文件保存路径
            text_content: PDF 内容（支持 Markdown 风格）
            title: PDF 文档标题

        Returns:
            操作结果消息
        """
        try:
            from reportlab.lib.pagesizes import A4, letter
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.lib.enums import TA_LEFT, TA_CENTER
            import os
            import sys

            # 确保目录存在
            os.makedirs(os.path.dirname(os.path.abspath(filepath)) or ".", exist_ok=True)

            # 创建 PDF
            doc = SimpleDocTemplate(
                filepath,
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18
            )

            # 尝试注册中文字体
            chinese_font_registered = False
            try:
                # Windows 系统自带中文字体
                if sys.platform == "win32":
                    font_paths = [
                        "C:/Windows/Fonts/msyh.ttc",  # 微软雅黑
                        "C:/Windows/Fonts/simsun.ttc",  # 宋体
                        "C:/Windows/Fonts/simhei.ttf",  # 黑体
                    ]
                    for font_path in font_paths:
                        if os.path.exists(font_path):
                            try:
                                pdfmetrics.registerFont(TTFont('Chinese', font_path))
                                chinese_font_registered = True
                                break
                            except:
                                continue
            except:
                pass

            # 样式
            styles = getSampleStyleSheet()

            if chinese_font_registered:
                # 使用中文字体
                title_style = ParagraphStyle(
                    'CustomTitle',
                    parent=styles['Heading1'],
                    fontSize=18,
                    textColor='#0066cc',
                    spaceAfter=30,
                    fontName='Chinese',
                    alignment=TA_CENTER,
                )
                body_style = ParagraphStyle(
                    'CustomBody',
                    parent=styles['BodyText'],
                    fontSize=11,
                    leading=16,
                    fontName='Chinese',
                    alignment=TA_LEFT,
                )
            else:
                # 回退到默认字体（中文可能显示为方块）
                title_style = ParagraphStyle(
                    'CustomTitle',
                    parent=styles['Heading1'],
                    fontSize=18,
                    textColor='#0066cc',
                    spaceAfter=30,
                    alignment=TA_CENTER,
                )
                body_style = styles['BodyText']
                body_style.fontSize = 11
                body_style.leading = 16

            # 构建内容
            story = []
            story.append(Paragraph(title, title_style))
            story.append(Spacer(1, 12))

            # 处理文本内容（简单分段）
            paragraphs = text_content.split('\n\n')
            for para in paragraphs:
                if para.strip():
                    # 转义特殊字符
                    para = para.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    # 如果没有中文字体，提示用户
                    if not chinese_font_registered and any('\u4e00' <= c <= '\u9fff' for c in para):
                        para = para + " [Note: Chinese font not available, text may not display correctly]"
                    story.append(Paragraph(para, body_style))
                    story.append(Spacer(1, 6))

            # 构建 PDF
            doc.build(story)

            # 检查文件是否真的生成
            if os.path.exists(filepath):
                size = os.path.getsize(filepath)
                return f"✅ PDF 已成功生成: {filepath} (大小: {size} 字节)"
            else:
                return f"❌ PDF 生成失败: 文件未创建"

        except ImportError:
            return "❌ 错误: reportlab 库未安装，请运行: pip install reportlab"
        except Exception as e:
            return f"❌ 生成 PDF 失败: {str(e)}"

    def _resolve_path(self, path: str) -> str:
        """解析路径，支持别名和相对路径

        Args:
            path: 用户输入的路径

        Returns:
            解析后的完整路径
        """
        import os

        # 如果路径为空，返回当前目录
        if not path or path.strip() == ".":
            return os.getcwd()

        original_path = path

        # 检查是否是路径别名
        for alias, resolved in self._path_aliases.items():
            if path == alias or path == f"{alias}/" or path == f"{alias}\\" or path.startswith(f"{alias}/") or path.startswith(f"{alias}\\"):
                path = path.replace(alias, resolved, 1)
                break

        # 如果是相对路径，基于当前目录解析
        if not os.path.isabs(path):
            path = os.path.abspath(path)

        return path

    def execute(self, tool_id: str, params: Dict[str, Any]) -> Any:
        """执行工具（统一入口，供 LifeLoop 调用）

        Args:
            tool_id: 工具标识符（如 "read_file", "list_directory"）
            params: 工具参数

        Returns:
            执行结果
        """
        # 工具 ID 映射到函数名
        tool_mapping = {
            "file_read": "read_file",
            "file_write": "write_file",
            "read_file": "read_file",
            "write_file": "write_file",
            "list_directory": "list_directory",
            "list": "list_directory",
            "web_search": "web_search",
            "search": "web_search",
            "execute_code": "execute_code",
            "code_exec": "execute_code",
        }

        function_name = tool_mapping.get(tool_id, tool_id)

        try:
            result = self._execute(function_name, params)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def execute_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个工具调用

        Args:
            tool_call: 工具调用信息，包含 id、function 等字段

        Returns:
            执行结果，包含 content 字段
        """
        # OpenAI 格式
        if "function" in tool_call:
            function_name = tool_call["function"]["name"]
            arguments_str = tool_call["function"]["arguments"]
        # Anthropic 格式
        elif "name" in tool_call:
            function_name = tool_call["name"]
            input_data = tool_call.get("input", {})
            arguments_str = json.dumps(input_data)
        else:
            return {
                "content": f"无法识别的工具调用格式: {tool_call}",
                "error": True
            }

        # 检查是否被禁用
        if function_name in self.disabled_tools:
            return {
                "content": f"工具 {function_name} 在安全模式下被禁用",
                "error": True
            }

        # 解析参数
        try:
            arguments = json.loads(arguments_str) if isinstance(arguments_str, str) else arguments_str
        except json.JSONDecodeError:
            return {
                "content": f"无法解析工具参数: {arguments_str}",
                "error": True
            }

        # 执行工具
        try:
            result = self._execute(function_name, arguments)
            return {"content": result, "error": False}
        except Exception as e:
            return {
                "content": f"执行工具 {function_name} 时出错: {str(e)}",
                "error": True
            }

    def _execute(self, function_name: str, arguments: Dict[str, Any]) -> str:
        """执行具体的工具

        Args:
            function_name: 工具名称
            arguments: 工具参数

        Returns:
            执行结果字符串
        """
        # 内置工具
        if function_name == "read_file":
            return self._read_file(arguments.get("path", ""))

        elif function_name == "write_file":
            return self._write_file(arguments.get("path", ""), arguments.get("content", ""))

        elif function_name == "list_directory":
            return self._list_directory(arguments.get("path", ""))

        elif function_name == "web_search":
            return self._web_search(arguments.get("query", ""))

        elif function_name == "execute_code":
            return self._execute_code(arguments.get("code", ""))

        else:
            return f"未知工具: {function_name}"

    def _read_file(self, path: str) -> str:
        """读取文件"""
        # 解析路径别名
        path = self._resolve_path(path)

        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            # 限制返回大小
            if len(content) > 50000:
                content = content[:50000] + "\n\n...（文件太长，已截断）"
            return f"文件内容:\n\n{content}"
        except FileNotFoundError:
            return f"错误: 找不到文件 {path}"
        except PermissionError:
            return f"错误: 没有权限读取文件 {path}"
        except Exception as e:
            return f"错误: {str(e)}（路径: {path}）"

    def _write_file(self, path: str, content: str) -> str:
        """写入文件"""
        # 解析路径别名
        path = self._resolve_path(path)

        try:
            # 确保目录存在
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"成功写入文件: {path}"
        except Exception as e:
            return f"错误: {str(e)}（路径: {path}）"

    def _list_directory(self, path: str) -> str:
        """列出目录内容"""
        # 解析路径别名
        path = self._resolve_path(path)

        try:
            if not os.path.exists(path):
                return f"错误: 路径不存在 {path}。\n提示: Windows桌面路径通常是 C:\\Users\\你的用户名\\Desktop"
            if not os.path.isdir(path):
                return f"错误: {path} 不是目录"

            items = os.listdir(path)
            # 分离文件和文件夹
            dirs = []
            files = []
            for item in items:
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    dirs.append(f"[目录] {item}")
                else:
                    files.append(item)

            result = []
            if dirs:
                result.append("目录:")
                result.extend(dirs)
            if files:
                result.append("\n文件:")
                result.extend(files[:20])  # 最多显示20个文件
                if len(files) > 20:
                    result.append(f"...（还有 {len(files) - 20} 个文件）")

            return "\n".join(result) if result else "（空目录）"
        except PermissionError:
            return f"错误: 没有权限访问 {path}"
        except Exception as e:
            return f"错误: {str(e)}（路径: {path}）"

    def _web_search(self, query: str) -> str:
        """网络搜索（使用通义千问的联网能力）"""
        try:
            from .llm_client import LLMClient

            # 创建专门的搜索客户端
            client = LLMClient()

            # 构建搜索消息
            search_messages = [
                {"role": "system", "content": "你是一个搜索助手。请根据用户的搜索查询，使用联网搜索功能获取最新信息，并简洁地总结搜索结果。请只返回搜索结果的核心信息，不要添加额外评论。"},
                {"role": "user", "content": f"搜索：{query}"}
            ]

            # 使用 chat 方法进行联网搜索
            result = client.chat(
                messages=search_messages,
                temperature=0.3  # 降低温度以获得更准确的搜索结果
            )

            if result.get("ok") and result.get("text"):
                return result["text"]
            else:
                error = result.get("error", "未知错误")
                return f"搜索失败: {error}"

        except Exception as e:
            # 如果联网搜索失败，回退到提示信息
            return f"搜索暂时不可用: {str(e)}"

    def _execute_code(self, code: str) -> str:
        """执行 Python 代码

        FULL_ACCESS 模式（完全访问模式）:
        - 允许完全 Python 访问
        - 可以导入模块、读写文件、联网
        - 支持 self-modification (自我修改代码)

        安全措施（仅保留基本的超时保护）:
        1. 超时保护 (防止无限循环)

        注意：此模式仅供高级用户使用，请在 Web 界面中谨慎选择。
        """
        if self.safe_mode:
            # 安全模式下的受限执行
            return self._execute_code_sandboxed(code)

        # FULL_ACCESS 模式 - 完全访问
        try:
            # 提供完整的 Python 环境
            exec_globals = {
                "__builtins__": __builtins__,
                # 添加常用模块
                "os": __import__("os"),
                "sys": __import__("sys"),
                "json": __import__("json"),
                "pathlib": __import__("pathlib"),
                "datetime": __import__("datetime"),
                "math": __import__("math"),
                "random": __import__("random"),
                # Genesis X 自身模块
                "genesis_self": self,  # 允许访问自己
            }

            # 添加 PDF 生成辅助函数
            exec_globals["create_pdf"] = self._create_pdf_helper

            # 捕获输出
            import io
            import sys
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()

            try:
                exec(code, exec_globals)
                output = sys.stdout.getvalue()
            finally:
                sys.stdout = old_stdout

            return output if output.strip() else "(代码执行成功，无输出)"

        except TimeoutError:
            return "错误: 代码执行超时"
        except Exception as e:
            return f"错误: {str(e)}"

    def _execute_code_sandboxed(self, code: str) -> str:
        """安全模式下的受限代码执行"""
        # 安全检查：代码长度限制
        MAX_CODE_LENGTH = 5000
        if len(code) > MAX_CODE_LENGTH:
            return f"错误: 代码过长（最大 {MAX_CODE_LENGTH} 字符）"

        # 安全检查：禁止危险关键字
        dangerous_patterns = [
            "import", "exec", "eval", "compile", "open", "file",
            "__import__", "globals", "locals", "vars", "dir",
            "getattr", "setattr", "delattr", "hasattr",
            "os.", "sys.", "subprocess", "multiprocessing",
            "threading", "socket", "http", "urllib",
            "__class__", "__base__", "__subclasses__", "__mro__",
            "pickle", "marshal", "shelve", "type(",
        ]
        code_lower = code.lower()
        for pattern in dangerous_patterns:
            if pattern.lower() in code_lower:
                return f"错误: 代码包含禁止的关键字 '{pattern}'"

        try:
            # 创建更安全的执行环境
            safe_globals = {
                "__builtins__": {},  # 完全移除 builtins
                # 只提供安全的函数
                "print": print,
                "len": len,
                "str": str,
                "int": int,
                "float": float,
                "list": list,
                "dict": dict,
                "tuple": tuple,
                "set": set,
                "range": range,
                "sum": sum,
                "max": max,
                "min": min,
                "abs": abs,
                "round": round,
                "enumerate": enumerate,
                "zip": zip,
                "sorted": sorted,
                "any": any,
                "all": all,
                "bool": bool,
                # 数学常量和函数
                "pow": pow,
                "divmod": divmod,
                # 类型转换
                "hex": hex,
                "bin": bin,
                "oct": oct,
                "chr": chr,
                "ord": ord,
            }
            # 创建空的安全局部命名空间
            safe_locals = {}

            # 捕获输出
            import io
            import sys
            import signal

            def timeout_handler(signum, frame):
                raise TimeoutError("代码执行超时")

            old_stdout = sys.stdout
            sys.stdout = io.StringIO()

            # 设置超时（如果支持）
            old_handler = None
            try:
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(5)  # 5秒超时
            except (AttributeError, ValueError):
                # Windows 不支持 SIGALRM
                pass

            try:
                # 使用 exec 而不是 eval，并传递安全的命名空间
                exec(code, safe_globals, safe_locals)
                output = sys.stdout.getvalue()

                # 恢复 stdout
                sys.stdout = old_stdout

                # 取消超时
                try:
                    signal.alarm(0)
                    if old_handler:
                        signal.signal(signal.SIGALRM, old_handler)
                except (AttributeError, ValueError):
                    pass

                # 尝试获取结果（如果有表达式返回值）
                result = None
                if safe_locals:
                    # 检查是否有变量定义
                    result_vars = {k: v for k, v in safe_locals.items()
                                  if not k.startswith('__')}
                    if result_vars:
                        result_str = ", ".join(f"{k}={repr(v)}" for k, v in result_vars.items())
                        if output:
                            return f"输出:\n{output}\n\n变量: {result_str}"
                        else:
                            return f"变量: {result_str}"

                if output:
                    return f"输出:\n{output}"
                else:
                    return "代码执行成功（无输出）"

            except TimeoutError:
                sys.stdout = old_stdout
                return "错误: 代码执行超时（最大5秒）"
            except Exception as e:
                output = sys.stdout.getvalue()
                sys.stdout = old_stdout
                # 取消超时
                try:
                    signal.alarm(0)
                    if old_handler:
                        signal.signal(signal.SIGALRM, old_handler)
                except (AttributeError, ValueError):
                    pass
                if output:
                    return f"输出:\n{output}\n\n错误: {str(e)}"
                return f"错误: {str(e)}"
        except Exception as e:
            return f"执行代码时出错: {str(e)}"


def create_llm_tool_executor(safe_mode: bool = True) -> 'LLMToolExecutor':
    """创建 LLM 工具执行器"""
    return LLMToolExecutor(safe_mode=safe_mode)


# 保留旧名称作为别名以保持向后兼容
ToolExecutor = LLMToolExecutor
