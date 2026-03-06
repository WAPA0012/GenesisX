"""
File Operations Tool: Safe File Read/Write with Sandbox

Implements:
- File read/write with path validation
- Sandbox constraints
- File type filtering

References:
- 代码大纲架构 tools/file_ops.py
"""

from typing import Dict, Any, Optional, Tuple
from pathlib import Path
from .tool_protocol import Tool, ToolMetadata, ToolRiskLevel, ToolDeterminism
import os


class FileOpsTool(Tool):
    """
    File operations tool with sandbox constraints.

    Supports read/write within allowed directories.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.config = config

        # Allowed directories
        self.allowed_dirs = config.get("allowed_dirs", [])
        self.allowed_dirs = [Path(d).resolve() for d in self.allowed_dirs]

        # Forbidden paths
        self.forbidden_patterns = config.get("forbidden_patterns", [
            "*.exe", "*.dll", "*.so", "*.dylib",
            "/etc/passwd", "/etc/shadow",
        ])

        # Max file size for read (bytes)
        self.max_read_size = config.get("max_read_size_bytes", 10 * 1024 * 1024)  # 10 MB

    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata"""
        return ToolMetadata(
            tool_id="file_ops",
            name="File Operations",
            description="Read and write files within sandbox",
            risk_level=ToolRiskLevel.MEDIUM,
            determinism=ToolDeterminism.DETERMINISTIC,
            requires_approval=True,
            cost_estimate=0.0001,
            tags=["file", "io", "storage"],
        )

    def validate_parameters(self, parameters: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate file operation parameters"""
        if "operation" not in parameters:
            return False, "Missing required parameter 'operation'"

        operation = parameters["operation"]
        if operation not in ["read", "write", "list"]:
            return False, f"Invalid operation '{operation}'. Must be 'read', 'write', or 'list'"

        if "path" not in parameters:
            return False, "Missing required parameter 'path'"

        return True, None

    def execute(self, parameters: Dict[str, Any]) -> Any:
        """
        Execute file operation.

        Args:
            parameters: {
                "operation": "read" | "write" | "list",
                "path": str,
                "content": str (for write),
            }

        Returns:
            File content (for read) or success status
        """
        operation = parameters["operation"]
        path = Path(parameters["path"]).resolve()

        # Security check
        if not self._is_path_allowed(path):
            raise PermissionError(f"Path not allowed: {path}")

        if operation == "read":
            return self._read_file(path)
        elif operation == "write":
            content = parameters.get("content", "")
            return self._write_file(path, content)
        elif operation == "list":
            return self._list_directory(path)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def _is_path_allowed(self, path: Path) -> bool:
        """
        Check if path is within allowed directories.

        修复：添加symlink检查以防止路径遍历攻击。

        Args:
            path: File path

        Returns:
            True if allowed
        """
        # 修复：解析路径并检查symlink
        try:
            # Resolve to handle symlinks and relative paths
            resolved_path = path.resolve()
        except (OSError, RuntimeError):
            return False

        # Check if within allowed directories
        if self.allowed_dirs:
            allowed = False
            for allowed_dir in self.allowed_dirs:
                try:
                    # Normalize allowed directory
                    resolved_allowed = Path(allowed_dir).resolve()
                    # Check if resolved path is within allowed directory
                    resolved_path.relative_to(resolved_allowed)
                    allowed = True
                    break
                except ValueError:
                    continue

            if not allowed:
                return False

        # Check forbidden patterns
        for pattern in self.forbidden_patterns:
            if resolved_path.match(pattern):
                return False

        return True

    def _read_file(self, path: Path) -> str:
        """
        Read file content.

        Args:
            path: File path

        Returns:
            File content as string
        """
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        if not path.is_file():
            raise ValueError(f"Not a file: {path}")

        # Check file size
        file_size = path.stat().st_size
        if file_size > self.max_read_size:
            raise ValueError(f"File too large: {file_size} bytes (max: {self.max_read_size})")

        # Read file
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except UnicodeDecodeError:
            # Try binary mode
            with open(path, 'rb') as f:
                content = f.read()
            return f"<binary file, {len(content)} bytes>"

    def _write_file(self, path: Path, content: str) -> Dict[str, Any]:
        """
        Write content to file.

        Args:
            path: File path
            content: Content to write

        Returns:
            Success status dict
        """
        # Create parent directory if needed
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

        return {
            "success": True,
            "path": str(path),
            "bytes_written": len(content.encode('utf-8')),
        }

    def _list_directory(self, path: Path) -> list:
        """
        List directory contents.

        Args:
            path: Directory path

        Returns:
            List of file/directory names
        """
        if not path.exists():
            raise FileNotFoundError(f"Directory not found: {path}")

        if not path.is_dir():
            raise ValueError(f"Not a directory: {path}")

        entries = []
        for entry in path.iterdir():
            entries.append({
                "name": entry.name,
                "path": str(entry),
                "is_file": entry.is_file(),
                "is_dir": entry.is_dir(),
                "size": entry.stat().st_size if entry.is_file() else 0,
            })

        return entries
