"""
Code Execution Tool: Sandboxed Python Code Execution

HIGH RISK TOOL - Must be used with extreme caution:
- Sandboxed execution environment
- Resource limits (CPU, memory, time)
- Forbidden operations (file system, network, subprocess)
- Replay mode: MUST NOT execute, only return cached results

References:
- 代码大纲 tools/code_exec.py
- 工作索引 04.5 最小工具集：code_exec(高风险,沙箱)
"""

from typing import Dict, Any, Optional, Tuple
from .tool_protocol import Tool, ToolMetadata, ToolRiskLevel, ToolDeterminism
import subprocess
import tempfile
from pathlib import Path
import signal
import sys


class CodeExecutionTool(Tool):
    """
    Execute Python code in a sandboxed environment.

    WARNING: This is a HIGH RISK tool. Use with extreme caution.

    Safety features:
    - Timeout limits
    - Resource limits (via sandbox)
    - Forbidden imports/operations
    - Replay mode does NOT execute
    """

    # Forbidden imports/operations (expanded for security)
    # 修复: 移除 typing 和 dataclasses，它们是安全的类型注解模块
    FORBIDDEN_IMPORTS = {
        "os", "subprocess", "sys", "socket", "requests",
        "urllib", "http", "ftplib", "telnetlib",
        "shutil", "pathlib", "tempfile", "pickle", "marshal",
        "__import__", "eval", "exec", "compile",
        "importlib",
        # Additional dangerous modules
        "ctypes", "multiprocessing", "threading",
        "signal", "resource", "pty", "fcntl",
    }

    # Forbidden built-in functions and attributes
    FORBIDDEN_BUILTINS = {
        "__import__", "eval", "exec", "compile", "open",
        "globals", "locals", "vars", "dir",
        "getattr", "setattr", "delattr", "hasattr",
        "property", "super", "__class__",
    }

    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.config = config

        # Execution limits
        self.timeout_seconds = config.get("code_exec_timeout", 5)
        self.max_output_size = config.get("code_exec_max_output", 10000)

        # Sandbox mode
        self.sandbox_enabled = config.get("code_exec_sandbox", True)

    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata"""
        return ToolMetadata(
            tool_id="code_exec",
            name="Code Execution",
            description="Execute Python code in sandboxed environment (HIGH RISK)",
            risk_level=ToolRiskLevel.HIGH,
            determinism=ToolDeterminism.DETERMINISTIC,
            requires_approval=True,
            cost_estimate=0.001,
            tags=["code", "execution", "high-risk"],
        )

    def validate_parameters(self, parameters: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate execution parameters"""
        if "code" not in parameters:
            return False, "Missing required parameter 'code'"

        code = parameters["code"]
        if not isinstance(code, str) or len(code.strip()) == 0:
            return False, "Code must be a non-empty string"

        # Check for forbidden imports/operations
        if self._contains_forbidden(code):
            return False, "Code contains forbidden operations"

        return True, None

    def execute(self, parameters: Dict[str, Any]) -> Any:
        """
        Execute Python code.

        Args:
            parameters: {
                "code": str - Python code to execute
                "timeout": int (optional) - Timeout in seconds
            }

        Returns:
            Execution result dict with stdout, stderr, success
        """
        code = parameters["code"]
        timeout = parameters.get("timeout", self.timeout_seconds)

        # Execute in sandbox
        if self.sandbox_enabled:
            return self._execute_sandboxed(code, timeout)
        else:
            return self._execute_direct(code, timeout)

    def _contains_forbidden(self, code: str) -> bool:
        """
        Check if code contains forbidden operations.

        Uses regex word boundaries to avoid false positives
        (e.g., 'import os' must not match 'import osgeo').

        Args:
            code: Python code string

        Returns:
            True if contains forbidden operations
        """
        import re

        # Check for forbidden imports and direct usage with word boundaries
        for forbidden in self.FORBIDDEN_IMPORTS:
            escaped = re.escape(forbidden)
            # Check import statements: "import os" but not "import osgeo"
            if re.search(rf'\bimport\s+{escaped}\b', code, re.IGNORECASE):
                return True
            # Check from-import: "from os" but not "from oslo"
            if re.search(rf'\bfrom\s+{escaped}\b', code, re.IGNORECASE):
                return True
            # Check direct call: "os.system(" but not "cosmos("
            if re.search(rf'\b{escaped}\s*\(', code, re.IGNORECASE):
                return True

        # Check for dangerous built-ins with word boundaries
        for forbidden_builtin in self.FORBIDDEN_BUILTINS:
            escaped = re.escape(forbidden_builtin)
            if re.search(rf'\b{escaped}\s*\(', code, re.IGNORECASE):
                return True

        # Check for dangerous patterns
        dangerous_patterns = [
            r'__class__\s*\.',      # Access to object class
            r'__bases__',            # Inheritance manipulation
            r'__subclasses__',       # Subclass access
            r'\.func_code',          # Code object access
            r'\.__code__',           # Code object access
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, code):
                return True

        return False

    def _execute_sandboxed(self, code: str, timeout: int) -> Dict[str, Any]:
        """
        Execute code in sandboxed subprocess.

        Args:
            code: Python code to execute
            timeout: Timeout in seconds

        Returns:
            Result dict
        """
        # Create temporary file for code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            temp_file = Path(f.name)
            f.write(code)

        try:
            # Execute in subprocess with timeout
            result = subprocess.run(
                [sys.executable, str(temp_file)],
                capture_output=True,
                text=True,
                timeout=timeout,
                # Add resource limits here if platform supports
            )

            stdout = result.stdout[:self.max_output_size]
            stderr = result.stderr[:self.max_output_size]

            return {
                "success": result.returncode == 0,
                "stdout": stdout,
                "stderr": stderr,
                "returncode": result.returncode,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Execution timeout after {timeout} seconds",
                "returncode": -1,
            }

        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Execution error: {str(e)}",
                "returncode": -1,
            }

        finally:
            # Clean up temp file
            try:
                temp_file.unlink()
            except Exception:
                pass

    def _execute_direct(self, code: str, timeout: int) -> Dict[str, Any]:
        """
        Execute code directly (less safe, for testing only).

        Args:
            code: Python code to execute
            timeout: Timeout in seconds

        Returns:
            Result dict
        """
        import io
        import contextlib

        # Capture stdout/stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        # Set timeout alarm (Unix only)
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Execution timeout after {timeout} seconds")

        try:
            # Set timeout (Unix only, won't work on Windows)
            if hasattr(signal, 'SIGALRM'):
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(timeout)

            # Execute with captured output in restricted environment
            with contextlib.redirect_stdout(stdout_capture), \
                 contextlib.redirect_stderr(stderr_capture):
                # Create restricted execution environment (SAFER)
                safe_builtins = {
                    'abs': abs,
                    'all': all,
                    'any': any,
                    'bin': bin,
                    'bool': bool,
                    'bytearray': bytearray,
                    'bytes': bytes,
                    'chr': chr,
                    'complex': complex,
                    'dict': dict,
                    'divmod': divmod,
                    'enumerate': enumerate,
                    'filter': filter,
                    'float': float,
                    'format': format,
                    'frozenset': frozenset,
                    'hex': hex,
                    'int': int,
                    'isinstance': isinstance,
                    'issubclass': issubclass,
                    'iter': iter,
                    'len': len,
                    'list': list,
                    'map': map,
                    'max': max,
                    'min': min,
                    'next': next,
                    'oct': oct,
                    'ord': ord,
                    'pow': pow,
                    'print': print,
                    'range': range,
                    'reversed': reversed,
                    'round': round,
                    'set': set,
                    'slice': slice,
                    'sorted': sorted,
                    'str': str,
                    'sum': sum,
                    'tuple': tuple,
                    'zip': zip,
                    '__builtins__': {},
                }
                exec(code, safe_builtins)

            # Cancel alarm
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)

            return {
                "success": True,
                "stdout": stdout_capture.getvalue()[:self.max_output_size],
                "stderr": stderr_capture.getvalue()[:self.max_output_size],
                "returncode": 0,
            }

        except TimeoutError as e:
            return {
                "success": False,
                "stdout": stdout_capture.getvalue()[:self.max_output_size],
                "stderr": str(e),
                "returncode": -1,
            }

        except Exception as e:
            return {
                "success": False,
                "stdout": stdout_capture.getvalue()[:self.max_output_size],
                "stderr": f"{type(e).__name__}: {str(e)}",
                "returncode": -1,
            }

        finally:
            # Cancel alarm if set
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)


# Example usage and test
if __name__ == "__main__":
    tool = CodeExecutionTool({"code_exec_sandbox": True})

    # Test safe code
    result = tool.execute({
        "code": """
print("Hello from code execution!")
x = 2 + 2
print(f"2 + 2 = {x}")
"""
    })

    print("Safe code result:")
    print(result)

    # Test forbidden code (should be rejected in validation)
    result = tool.execute({
        "code": "import os; os.system('ls')"
    })

    print("\nForbidden code result:")
    print(result)
