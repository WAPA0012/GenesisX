"""
安全代码执行器 - 使用AST分析防止代码注入

提供基于抽象语法树(AST)的代码执行安全检查，而不是简单的字符串匹配。
"""

import ast
import io
import sys
import signal
import threading
import multiprocessing
from typing import Dict, Any, Set, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from contextlib import redirect_stdout


class SecurityViolation(Exception):
    """代码安全检查违规异常"""
    def __init__(self, message: str, node_type: str = "", line: int = 0):
        super().__init__(message)
        self.node_type = node_type
        self.line = line


class ExecutionTimeout(Exception):
    """代码执行超时异常"""
    pass


class RiskLevel(Enum):
    """代码风险等级"""
    SAFE = "safe"           # 完全安全
    LOW = "low"            # 低风险，可能需要监控
    MEDIUM = "medium"      # 中等风险，需要警告
    HIGH = "high"          # 高风险，不建议执行
    CRITICAL = "critical"  # 危险，禁止执行


@dataclass
class SecurityPolicy:
    """安全策略配置"""
    # 允许的AST节点类型
    allowed_nodes: Set[str] = None

    # 禁止的函数调用
    forbidden_calls: Set[str] = None

    # 禁止的模块导入
    forbidden_imports: Set[str] = None

    # 允许的内置函数
    allowed_builtins: Set[str] = None

    # 最大代码长度
    max_code_length: int = 5000

    # 最大执行时间（秒）
    max_execution_time: float = 5.0

    # 最大内存使用（MB）
    max_memory_mb: int = 100

    def __post_init__(self):
        if self.allowed_nodes is None:
            self.allowed_nodes = {
                # 表达式
                "Expression", "Expr", "Constant", "Num", "Str", "Bytes",
                "Name", "Load", "Store",
                # 运算
                "BinOp", "UnaryOp", "Add", "Sub", "Mult", "Div", "Mod",
                "Pow", "FloorDiv", "UAdd", "USub",
                "Compare", "Eq", "NotEq", "Lt", "LtE", "Gt", "GtE",
                "BoolOp", "And", "Or", "Not",
                # 容器
                "List", "Tuple", "Set", "Dict", "ListComp", "SetComp",
                "DictComp", "GeneratorExp",
                # 索引和切片
                "Index", "Slice", "ExtSlice",
                # 赋值
                "Assign", "AugAssign", "AnnAssign",
                # 控制流
                "If", "For", "While", "Break", "Continue",
                "Return",
                # 其他
                "Pass", "Module",
            }

        if self.forbidden_calls is None:
            self.forbidden_calls = {
                "exec", "eval", "compile", "__import__",
                "open", "file", "input",
                "globals", "locals", "vars", "dir",
                "getattr", "setattr", "delattr", "hasattr",
                "property", "super",
            }

        if self.forbidden_imports is None:
            self.forbidden_imports = {
                "os", "sys", "subprocess", "multiprocessing",
                "threading", "socket", "http", "urllib",
                "pickle", "marshal", "shelve", "ctypes",
                "importlib", "__import__",
            }

        if self.allowed_builtins is None:
            self.allowed_builtins = {
                "print", "len", "str", "int", "float", "bool",
                "list", "tuple", "set", "dict",
                "range", "enumerate", "zip", "reversed", "sorted",
                "sum", "max", "min", "abs", "round", "divmod", "pow",
                "any", "all",
                "hex", "bin", "oct", "chr", "ord",
                "type", "isinstance", "issubclass",
                "hash", "id",
                "map", "filter", "reduce",
            }


class ASTSecurityChecker(ast.NodeVisitor):
    """AST安全检查器

    通过分析抽象语法树来检测潜在的危险操作。
    """

    def __init__(self, policy: SecurityPolicy = None):
        self.policy = policy or SecurityPolicy()
        self.violations: List[SecurityViolation] = []
        self.risk_level = RiskLevel.SAFE

    def check(self, code: str) -> tuple[bool, List[SecurityViolation], RiskLevel]:
        """检查代码安全性

        Args:
            code: 要检查的Python代码

        Returns:
            (是否安全, 违规列表, 风险等级)
        """
        self.violations = []
        self.risk_level = RiskLevel.SAFE

        try:
            tree = ast.parse(code)
            self.visit(tree)
        except SyntaxError as e:
            self.violations.append(SecurityViolation(
                f"语法错误: {e.msg}",
                "SyntaxError",
                e.lineno or 0
            ))
            self.risk_level = RiskLevel.CRITICAL

        is_safe = (
            self.risk_level in {RiskLevel.SAFE, RiskLevel.LOW} and
            len(self.violations) == 0
        )

        return is_safe, self.violations, self.risk_level

    def _add_violation(self, msg: str, node: ast.AST, level: RiskLevel = RiskLevel.HIGH):
        """添加违规记录"""
        self.violations.append(SecurityViolation(
            msg,
            node.__class__.__name__,
            getattr(node, "lineno", 0)
        ))
        # 升级风险等级
        level_order = [RiskLevel.SAFE, RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        current_idx = level_order.index(self.risk_level)
        new_idx = level_order.index(level)
        if new_idx > current_idx:
            self.risk_level = level

    def visit_Import(self, node: ast.Import):
        """检查import语句"""
        for alias in node.names:
            module_name = alias.name
            if module_name in self.policy.forbidden_imports:
                self._add_violation(
                    f"禁止导入模块: {module_name}",
                    node,
                    RiskLevel.CRITICAL
                )
            elif module_name.split('.')[0] in self.policy.forbidden_imports:
                self._add_violation(
                    f"禁止导入模块: {module_name}",
                    node,
                    RiskLevel.CRITICAL
                )
            else:
                self._add_violation(
                    f"导入外部模块: {module_name}",
                    node,
                    RiskLevel.MEDIUM
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """检查from ... import语句"""
        if node.module:
            if node.module in self.policy.forbidden_imports:
                self._add_violation(
                    f"禁止从模块导入: {node.module}",
                    node,
                    RiskLevel.CRITICAL
                )
            else:
                self._add_violation(
                    f"从外部模块导入: {node.module}",
                    node,
                    RiskLevel.MEDIUM
                )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        """检查函数调用"""
        # 检查调用的函数名
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in self.policy.forbidden_calls:
                self._add_violation(
                    f"禁止调用函数: {func_name}",
                    node,
                    RiskLevel.CRITICAL
                )

        # 检查属性访问调用 (如 os.system)
        elif isinstance(node.func, ast.Attribute):
            attr_chain = self._get_attribute_chain(node.func)
            if any(forbidden in attr_chain for forbidden in self.policy.forbidden_calls):
                self._add_violation(
                    f"禁止调用: {attr_chain}",
                    node,
                    RiskLevel.CRITICAL
                )

        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        """检查属性访问"""
        attr_chain = self._get_attribute_chain(node)

        # 检查危险的属性访问
        dangerous_attrs = {
            "__class__", "__base__", "__bases__", "__subclasses__",
            "__mro__", "__dict__", "__code__", "__globals__",
            "__closure__", "__defaults__", "__kwdefaults__",
        }

        for attr in dangerous_attrs:
            if attr in attr_chain:
                self._add_violation(
                    f"危险属性访问: {attr_chain}",
                    node,
                    RiskLevel.HIGH
                )
                break

        self.generic_visit(node)

    def visit_Starred(self, node: ast.Starred):
        """检查星号表达式 (可能用于参数注入)"""
        self._add_violation(
            "使用星号表达式",
            node,
            RiskLevel.MEDIUM
        )
        self.generic_visit(node)

    def _get_attribute_chain(self, node: ast.Attribute) -> str:
        """获取属性访问链"""
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))


class SafeCodeExecutor:
    """安全代码执行器

    提供受限的Python代码执行环境。
    """

    def __init__(self, policy: SecurityPolicy = None):
        self.policy = policy or SecurityPolicy()
        self.checker = ASTSecurityChecker(self.policy)
        self._execution_result = None
        self._execution_exception = None

    def execute(
        self,
        code: str,
        globals_dict: Optional[Dict[str, Any]] = None,
        locals_dict: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None
    ) -> tuple[bool, str, Any]:
        """安全执行代码

        Args:
            code: 要执行的Python代码
            globals_dict: 全局命名空间
            locals_dict: 局部命名空间
            timeout: 超时时间（秒）

        Returns:
            (是否成功, 输出/错误消息, 返回值)
        """
        timeout = timeout or self.policy.max_execution_time

        # 1. 检查代码长度
        if len(code) > self.policy.max_code_length:
            return False, f"代码过长（最大 {self.policy.max_code_length} 字符）", None

        # 2. AST安全检查
        is_safe, violations, risk_level = self.checker.check(code)
        if not is_safe:
            error_msgs = [f"第{v.line}行: {str(v)}" for v in violations]
            return False, f"安全检查失败:\n" + "\n".join(error_msgs), None

        # 3. 准备执行环境
        exec_globals = self._create_safe_globals(globals_dict)
        exec_locals = locals_dict or {}

        # 4. 使用超时执行
        try:
            result = self._execute_with_timeout(
                code, exec_globals, exec_locals, timeout
            )
            return True, result, exec_locals.get("_result")
        except ExecutionTimeout:
            return False, f"代码执行超时（{timeout}秒）", None
        except MemoryError:
            return False, "内存使用超限", None
        except Exception as e:
            return False, f"执行错误: {str(e)}", None

    def _create_safe_globals(self, custom_globals: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """创建安全的全局命名空间"""
        safe_globals = {
            "__builtins__": {},
            # 数学常量
            "math": __import__("math"),
            # 类型工具
            "type": type,
            "isinstance": isinstance,
        }

        # 添加允许的内置函数
        for name in self.policy.allowed_builtins:
            if hasattr(__builtins__, name):
                safe_globals[name] = getattr(__builtins__, name)

        # 合并用户提供的全局变量
        if custom_globals:
            # 只允许安全类型的值
            for key, value in custom_globals.items():
                if self._is_safe_value(value):
                    safe_globals[key] = value

        return safe_globals

    def _is_safe_value(self, value: Any) -> bool:
        """检查值是否安全（不包含危险引用）"""
        if value is None:
            return True

        value_type = type(value)

        # 基本类型
        if value_type in (int, float, str, bool, bytes):
            return True

        # 容器类型（递归检查）
        if value_type in (list, tuple):
            try:
                return all(self._is_safe_item(item) for item in value)
            except:
                return False

        if value_type is dict:
            try:
                return all(
                    self._is_safe_item(k) and self._is_safe_item(v)
                    for k, v in value.items()
                )
            except:
                return False

        if value_type is set:
            try:
                return all(self._is_safe_item(item) for item in value)
            except:
                return False

        # 模块、函数、类等 - 不安全
        return False

    def _is_safe_item(self, item: Any) -> bool:
        """检查容器中的单项是否安全"""
        # 防止通过容器注入危险对象
        if hasattr(item, "__globals__"):
            return False
        if hasattr(item, "__code__"):
            return False
        return self._is_safe_value(item)

    def _execute_with_timeout(
        self,
        code: str,
        globals_dict: Dict[str, Any],
        locals_dict: Dict[str, Any],
        timeout: float
    ) -> str:
        """带超时的执行"""
        output_buffer = io.StringIO()

        def target():
            try:
                with redirect_stdout(output_buffer):
                    exec(code, globals_dict, locals_dict)
            except Exception as e:
                self._execution_exception = e

        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            # 线程仍在运行，超时
            return output_buffer.getvalue() + "\n[执行超时]"

        if self._execution_exception:
            raise self._execution_exception

        return output_buffer.getvalue()


def execute_code_safely(
    code: str,
    policy: Optional[SecurityPolicy] = None,
    timeout: float = 5.0
) -> tuple[bool, str, Any]:
    """便捷函数：安全执行代码

    Args:
        code: Python代码
        policy: 安全策略
        timeout: 超时时间

    Returns:
        (是否成功, 输出/错误, 返回值)
    """
    executor = SafeCodeExecutor(policy)
    return executor.execute(code, timeout=timeout)


# =============================================================================
# 预定义的安全策略
# =============================================================================

STRICT_POLICY = SecurityPolicy(
    max_code_length=3000,
    max_execution_time=3.0,
    max_memory_mb=50,
)

MODERATE_POLICY = SecurityPolicy(
    max_code_length=5000,
    max_execution_time=5.0,
    max_memory_mb=100,
)

PERMISSIVE_POLICY = SecurityPolicy(
    max_code_length=10000,
    max_execution_time=10.0,
    max_memory_mb=200,
    # 允许更多内置函数
    allowed_builtins={
        "print", "len", "str", "int", "float", "bool",
        "list", "tuple", "set", "dict",
        "range", "enumerate", "zip", "reversed", "sorted",
        "sum", "max", "min", "abs", "round", "divmod", "pow",
        "any", "all",
        "hex", "bin", "oct", "chr", "ord",
        "type", "isinstance", "issubclass",
        "hash", "id",
        "map", "filter",
        "help", "dir",  # PERMISSIVE 模式允许这些
    }
)


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    "SecurityViolation",
    "ExecutionTimeout",
    "RiskLevel",
    "SecurityPolicy",
    "ASTSecurityChecker",
    "SafeCodeExecutor",
    "execute_code_safely",
    "STRICT_POLICY",
    "MODERATE_POLICY",
    "PERMISSIVE_POLICY",
]
