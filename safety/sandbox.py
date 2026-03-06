"""
Sandbox Manager: Execution Environment Isolation

Provides:
- Filesystem sandboxing
- Resource limits
- Network restrictions

References:
- 代码大纲架构 safety/sandbox.py
"""

from typing import Dict, Any, Optional, List
from pathlib import Path


class SandboxConfig:
    """Sandbox configuration"""

    def __init__(
        self,
        allowed_dirs: Optional[List[str]] = None,
        forbidden_patterns: Optional[List[str]] = None,
        max_memory_mb: int = 512,
        max_cpu_percent: int = 50,
        network_allowed: bool = False,
    ):
        self.allowed_dirs = allowed_dirs or []
        self.forbidden_patterns = forbidden_patterns or []
        self.max_memory_mb = max_memory_mb
        self.max_cpu_percent = max_cpu_percent
        self.network_allowed = network_allowed


class SandboxViolation(Exception):
    """Sandbox violation exception"""

    def __init__(self, message: str, violation_type: str):
        super().__init__(message)
        self.violation_type = violation_type


class Sandbox:
    """
    Execution environment sandbox.

    Enforces:
    - File system access restrictions
    - Resource usage limits
    - Network access control
    """

    def __init__(self, config: SandboxConfig):
        self.config = config

        # Resolve allowed directories
        self.allowed_dirs = [
            Path(d).resolve() for d in config.allowed_dirs
        ]

        # Compile forbidden patterns
        self.forbidden_patterns = config.forbidden_patterns

    def check_path_access(self, path: str, operation: str = "read") -> bool:
        """
        Check if path access is allowed.

        Args:
            path: File path
            operation: "read" or "write"

        Returns:
            True if allowed

        Raises:
            SandboxViolation: If access denied
        """
        # 修复 TOCTOU 问题: 使用原子性检查
        # 在 resolve() 后验证最终路径仍在允许目录内
        original_path = Path(path)

        # 首先检查原始路径是否为符号链接
        if original_path.is_symlink():
            raise SandboxViolation(
                f"Symbolic links are not allowed: '{path}'",
                violation_type="symlink_blocked"
            )

        # Resolve path (follows all symlinks)
        try:
            path_obj = original_path.resolve(strict=False)
        except (OSError, RuntimeError) as e:
            raise SandboxViolation(
                f"Invalid path '{path}': {e}",
                violation_type="invalid_path"
            )

        # 修复 TOCTOU: 再次检查解析后的路径是否为符号链接
        # （检查中间组件是否为符号链接）
        if path_obj.is_symlink():
            raise SandboxViolation(
                f"Resolved path is a symbolic link: '{path_obj}'",
                violation_type="symlink_blocked"
            )

        # 验证路径的所有组件都不在允许目录之外
        self._verify_path_components(path_obj)

        # Check if within allowed directories
        if self.allowed_dirs:
            allowed = False
            for allowed_dir in self.allowed_dirs:
                try:
                    # Check if path is relative to allowed directory
                    relative = path_obj.relative_to(allowed_dir)
                    # Check for '..' components that could escape
                    if '..' in relative.parts:
                        continue
                    allowed = True
                    break
                except ValueError:
                    continue

            if not allowed:
                raise SandboxViolation(
                    f"Path '{path}' not in allowed directories",
                    violation_type="path_access"
                )

        # Check forbidden patterns
        for pattern in self.forbidden_patterns:
            if path_obj.match(pattern):
                raise SandboxViolation(
                    f"Path '{path}' matches forbidden pattern '{pattern}'",
                    violation_type="forbidden_pattern"
                )

        return True

    def _verify_path_components(self, path_obj: Path) -> None:
        """Verify all path components are within allowed directories.

        修复 TOCTOU 问题: 检查路径的所有组件。

        Args:
            path_obj: Resolved path object

        Raises:
            SandboxViolation: If any component escapes allowed directories
        """
        if not self.allowed_dirs:
            return

        # 检查最终路径是否在允许目录内
        allowed = False
        for allowed_dir in self.allowed_dirs:
            try:
                relative = path_obj.relative_to(allowed_dir)
                # 检查 '..' 组件
                if '..' not in relative.parts:
                    allowed = True
                    break
            except ValueError:
                continue

        if not allowed:
            raise SandboxViolation(
                f"Path '{path_obj}' not in allowed directories",
                violation_type="path_access"
            )

        # 检查路径中间组件是否为符号链接（防止 symlink 攻击）
        current = path_obj
        while current != current.parent:
            parent = current.parent
            if parent.is_symlink():
                raise SandboxViolation(
                    f"Path component '{parent}' is a symbolic link",
                    violation_type="symlink_blocked"
                )
            current = parent

        # 修复跨平台路径检查：使用 pathlib 规范化
        self._check_system_paths(path_obj)

    def _check_system_paths(self, path_obj: Path) -> None:
        """Check if path is in system-critical directories.

        修复跨平台路径检查问题。

        Args:
            path_obj: Path to check

        Raises:
            SandboxViolation: If path is system-critical
        """
        import os
        import platform

        # 根据平台定义关键路径
        if platform.system() == "Windows":
            critical_paths = [
                Path(os.environ.get("SystemRoot", "C:\\Windows")),
                Path("C:\\Windows\\System32"),
                Path("C:\\Program Files"),
                Path("C:\\Program Files (x86)"),
            ]
        else:
            critical_paths = [
                Path("/etc"),
                Path("/sys"),
                Path("/proc"),
                Path("/dev"),
                Path("/bin"),
                Path("/sbin"),
                Path("/usr/bin"),
                Path("/usr/sbin"),
            ]

        # 规范化路径进行比较
        path_resolved = path_obj.resolve()
        for critical in critical_paths:
            try:
                if critical.exists():
                    critical_resolved = critical.resolve()
                    # 检查是否是同一目录或子目录
                    if (path_resolved == critical_resolved or
                        str(path_resolved).startswith(str(critical_resolved))):
                        raise SandboxViolation(
                            f"Path '{path_obj}' is in system-critical directory '{critical}'",
                            violation_type="system_path"
                        )
            except (OSError, ValueError):
                continue

    def check_path_access_for_write(self, path: str) -> bool:
        """Check if write access is allowed for path.

        修复：单独的写权限检查方法。

        Args:
            path: File path to check

        Returns:
            True if write allowed

        Raises:
            SandboxViolation: If write denied
        """
        path_obj = Path(path).resolve(strict=False)
        self._check_system_paths(path_obj)
        return True

    def check_network_access(self, host: str, port: int) -> bool:
        """
        Check if network access is allowed.

        Args:
            host: Target host
            port: Target port

        Returns:
            True if allowed

        Raises:
            SandboxViolation: If access denied
        """
        if not self.config.network_allowed:
            raise SandboxViolation(
                f"Network access to {host}:{port} not allowed",
                violation_type="network_access"
            )

        return True

    def check_resource_usage(
        self,
        memory_mb: float,
        cpu_percent: float
    ) -> bool:
        """
        Check if resource usage is within limits.

        Args:
            memory_mb: Memory usage in MB
            cpu_percent: CPU usage percentage

        Returns:
            True if within limits

        Raises:
            SandboxViolation: If limits exceeded
        """
        if memory_mb > self.config.max_memory_mb:
            raise SandboxViolation(
                f"Memory usage ({memory_mb}MB) exceeds limit ({self.config.max_memory_mb}MB)",
                violation_type="memory_limit"
            )

        if cpu_percent > self.config.max_cpu_percent:
            raise SandboxViolation(
                f"CPU usage ({cpu_percent}%) exceeds limit ({self.config.max_cpu_percent}%)",
                violation_type="cpu_limit"
            )

        return True

    def get_safe_temp_dir(self) -> Path:
        """
        Get safe temporary directory within sandbox.

        Returns:
            Path to temp directory
        """
        if self.allowed_dirs:
            # Use first allowed directory
            temp_dir = self.allowed_dirs[0] / "temp"
        else:
            # Use system temp
            import tempfile
            temp_dir = Path(tempfile.gettempdir()) / "genesis_sandbox"

        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir

    def cleanup_temp(self):
        """Clean up temporary files"""
        temp_dir = self.get_safe_temp_dir()

        if temp_dir.exists():
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


class SandboxManager:
    """
    Manages multiple sandbox contexts.

    Allows different sandbox configurations for different operations.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Default sandbox
        self.default_sandbox = Sandbox(
            SandboxConfig(
                allowed_dirs=config.get("allowed_dirs", []),
                forbidden_patterns=config.get("forbidden_patterns", []),
                max_memory_mb=config.get("max_memory_mb", 512),
                max_cpu_percent=config.get("max_cpu_percent", 50),
                network_allowed=config.get("network_allowed", False),
            )
        )

        # Named sandbox contexts
        self.sandboxes: Dict[str, Sandbox] = {
            "default": self.default_sandbox,
        }

    def get_sandbox(self, name: str = "default") -> Sandbox:
        """
        Get sandbox by name.

        Args:
            name: Sandbox name

        Returns:
            Sandbox instance
        """
        return self.sandboxes.get(name, self.default_sandbox)

    MAX_SANDBOXES = 100

    def create_sandbox(
        self,
        name: str,
        config: SandboxConfig
    ):
        """
        Create a new sandbox context.

        Args:
            name: Sandbox name
            config: Sandbox configuration

        Raises:
            RuntimeError: If maximum sandbox count exceeded
        """
        if len(self.sandboxes) >= self.MAX_SANDBOXES and name not in self.sandboxes:
            raise RuntimeError(
                f"Maximum sandbox count ({self.MAX_SANDBOXES}) exceeded. "
                f"Clean up unused sandboxes first."
            )
        self.sandboxes[name] = Sandbox(config)

    def cleanup_all(self):
        """Clean up all sandbox temporary files"""
        for sandbox in self.sandboxes.values():
            sandbox.cleanup_temp()
