"""Exception hierarchy and handling for Genesis X.

Implements paper Section 3.13 requirement for comprehensive exception handling
with degradation strategies.

异常处理层次结构 (Paper Section 3.13):
1. CriticalError: 系统威胁性错误
2. HighError: 严重但可恢复的错误
3. MediumError: 需要降级的错误
4. LowError: 轻微问题
"""
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass
from enum import Enum
import time
import functools


class GenesisXException(Exception):
    """Base exception for all Genesis X errors."""

    def __init__(
        self,
        message: str,
        severity: "ErrorSeverity" = None,
        recoverable: bool = True,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.severity = severity or ErrorSeverity.LOW
        self.recoverable = recoverable
        self.details = details or {}


class ErrorSeverity(Enum):
    """Error severity levels."""
    CRITICAL = "critical"   # 系统威胁，需要caretaker模式
    HIGH = "high"           # 严重但可恢复
    MEDIUM = "medium"       # 需要降级
    LOW = "low"             # 轻微问题


class CriticalError(GenesisXException):
    """Critical errors that threaten system stability.

    Examples:
    - Memory overflow
    - State corruption
    - Complete tool failure
    """

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            severity=ErrorSeverity.CRITICAL,
            recoverable=False,
            details=details,
        )


class HighError(GenesisXException):
    """High severity errors that are recoverable.

    Examples:
    - LLM API failure
    - Major tool failure
    - Network timeout
    """

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            recoverable=True,
            details=details,
        )


class MediumError(GenesisXException):
    """Medium severity errors requiring degradation.

    Examples:
    - Single tool failure
    - Minor network issue
    - Partial API failure
    """

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            details=details,
        )


class LowError(GenesisXException):
    """Low severity errors for minor issues.

    Examples:
    - Non-critical validation failure
    - Minor data inconsistency
    - Log write failure
    """

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            severity=ErrorSeverity.LOW,
            recoverable=True,
            details=details,
        )


class ToolExecutionError(HighError):
    """Error during tool execution.

    论文Section 3.13: ToolExecutionError需要重试和降级策略
    """

    def __init__(
        self,
        message: str,
        tool_id: str,
        attempt: int = 0,
        max_attempts: int = 3,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details=details or {})
        self.tool_id = tool_id
        self.attempt = attempt
        self.max_attempts = max_attempts


class MemoryOverflowError(CriticalError):
    """Memory system overflow.

    论文Section 3.13: 触发紧急记忆压缩
    """

    def __init__(
        self,
        message: str,
        memory_type: str,
        current_size: int,
        capacity: int,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message,
            details=details or {
                "memory_type": memory_type,
                "current_size": current_size,
                "capacity": capacity,
            }
        )
        self.memory_type = memory_type
        self.current_size = current_size
        self.capacity = capacity


class ParameterError(GenesisXException):
    """Value parameter drift or out-of-range error.

    论文Section 3.13: 参数越界，重置到默认值

    Note: Renamed from ValueError to avoid conflict with Python built-in.
    """

    def __init__(
        self,
        message: str,
        parameter_name: str,
        actual_value: Any,
        expected_range: tuple,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            recoverable=True,
            details=details or {
                "parameter": parameter_name,
                "actual": actual_value,
                "expected_range": expected_range,
            }
        )
        self.parameter_name = parameter_name
        self.actual_value = actual_value
        self.expected_range = expected_range


@dataclass
class DegradationTier:
    """Degradation tier for system operation.

    论文Section 3.13: 降级策略
    """
    name: str
    description: str
    max_tool_risk: float
    simplified_prompts: bool
    timeout_multiplier: float
    enable_local_fallback: bool


# Degradation tiers (论文Section 3.13)
DEGRADATION_TIERS = {
    "full": DegradationTier(
        name="full",
        description="Full capability",
        max_tool_risk=1.0,
        simplified_prompts=False,
        timeout_multiplier=1.0,
        enable_local_fallback=False,
    ),
    "reduced": DegradationTier(
        name="reduced",
        description="Reduced complexity",
        max_tool_risk=0.7,
        simplified_prompts=True,
        timeout_multiplier=1.5,
        enable_local_fallback=False,
    ),
    "local_fallback": DegradationTier(
        name="local_fallback",
        description="Local model fallback",
        max_tool_risk=0.5,
        simplified_prompts=True,
        timeout_multiplier=2.0,
        enable_local_fallback=True,
    ),
    "safe_mode": DegradationTier(
        name="safe_mode",
        description="Safe mode only",
        max_tool_risk=0.0,
        simplified_prompts=True,
        timeout_multiplier=3.0,
        enable_local_fallback=True,
    ),
}


class CircuitBreaker:
    """Circuit breaker for preventing repeated failures.

    论文Section 3.13: Circuit breaker pattern for repeated failures
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_attempts: int = 1,
    ):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Failures before opening
            recovery_timeout: Seconds to wait before half-open
            half_open_attempts: Attempts in half-open state
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_attempts = half_open_attempts

        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._state = "closed"  # closed, open, half_open
        self._half_open_count = 0

    def call(self, func: Callable) -> Callable:
        """Decorator to wrap function with circuit breaker."""

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not self.allow_request():
                raise HighError(
                    f"Circuit breaker is {self._state}",
                    details={"state": self._state, "failures": self._failure_count}
                )

            try:
                result = func(*args, **kwargs)
                self.on_success()
                return result
            except Exception as e:
                self.on_failure()
                raise

        return wrapper

    def allow_request(self) -> bool:
        """Check if request should be allowed."""
        if self._state == "closed":
            return True
        elif self._state == "open":
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = "half_open"
                self._half_open_count = 0
                return True
            return False
        elif self._state == "half_open":
            return self._half_open_count < self.half_open_attempts
        return False

    def on_success(self):
        """Handle successful call."""
        self._failure_count = 0
        if self._state == "half_open":
            self._half_open_count += 1
            if self._half_open_count >= self.half_open_attempts:
                self._state = "closed"

    def on_failure(self):
        """Handle failed call."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self.failure_threshold:
            self._state = "open"

    def reset(self):
        """Reset circuit breaker."""
        self._failure_count = 0
        self._last_failure_time = None
        self._state = "closed"
        self._half_open_count = 0

    def get_state(self) -> Dict[str, Any]:
        """Get current state."""
        return {
            "state": self._state,
            "failure_count": self._failure_count,
            "last_failure_time": self._last_failure_time,
        }


class RetryWithBackoff:
    """Retry logic with exponential backoff.

    论文Section 3.13: Retry mechanism with exponential backoff
    """

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
    ):
        """Initialize retry handler.

        Args:
            max_attempts: Maximum retry attempts
            base_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Exponential backoff base
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

    def call(self, func: Callable) -> Callable:
        """Decorator to wrap function with retry logic."""

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(self.max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if attempt < self.max_attempts - 1:
                        delay = min(
                            self.base_delay * (self.exponential_base ** attempt),
                            self.max_delay
                        )
                        time.sleep(delay)

            raise HighError(
                f"Retry failed after {self.max_attempts} attempts",
                details={"original_error": str(last_exception)}
            )

        return wrapper


class ErrorHandler:
    """Central error handler with degradation strategies.

    论文Section 3.13: Comprehensive error handling
    """

    def __init__(self):
        """Initialize error handler."""
        self._consecutive_errors: Dict[str, int] = {}
        self._error_thresholds = {
            ErrorSeverity.CRITICAL: 1,
            ErrorSeverity.HIGH: 3,
            ErrorSeverity.MEDIUM: 5,
            ErrorSeverity.LOW: 10,
        }
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._current_tier = "full"

    def handle(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Handle an error with appropriate strategy.

        论文Section 3.13:
        - ToolExecutionError: 重试和降级
        - MemoryOverflow: 紧急压缩
        - ValueError: 重置参数
        - Other: Caretaker模式

        Args:
            error: The exception to handle
            context: Additional context

        Returns:
            Handler response with action taken
        """
        context = context or {}

        if isinstance(error, ToolExecutionError):
            return self._handle_tool_error(error, context)
        elif isinstance(error, MemoryOverflowError):
            return self._handle_memory_overflow(error, context)
        elif isinstance(error, ParameterError):
            return self._handle_parameter_error(error, context)
        elif isinstance(error, CriticalError):
            return self._handle_critical_error(error, context)
        # 修复：添加对内置 ValueError 的处理
        elif isinstance(error, ValueError):
            return self._handle_value_error(error, context)
        else:
            return self._handle_generic_error(error, context)

    def _handle_tool_error(
        self,
        error: ToolExecutionError,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle tool execution error."""
        tool_id = error.tool_id

        # Track consecutive errors
        self._consecutive_errors[tool_id] = self._consecutive_errors.get(tool_id, 0) + 1
        consecutive = self._consecutive_errors[tool_id]

        # Check if threshold exceeded
        threshold = self._error_thresholds.get(ErrorSeverity.HIGH, 3)
        if consecutive >= threshold:
            # Disable tool temporarily
            return {
                "action": "disable_tool",
                "tool_id": tool_id,
                "reason": f"Too many consecutive failures ({consecutive})",
                "fallback": "safe_mode",
            }

        # Retry with backoff
        if error.attempt < error.max_attempts:
            return {
                "action": "retry",
                "tool_id": tool_id,
                "attempt": error.attempt + 1,
                "delay": 2.0 ** error.attempt,
            }

        # Fallback to degraded mode
        return {
            "action": "degrade",
            "tool_id": tool_id,
            "tier": self._get_next_tier(),
        }

    def _handle_memory_overflow(
        self,
        error: MemoryOverflowError,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle memory overflow."""
        return {
            "action": "emergency_consolidation",
            "memory_type": error.memory_type,
            "current_size": error.current_size,
            "capacity": error.capacity,
            "target_reduction": 0.2,  # Reduce by 20%
        }

    def _handle_parameter_error(
        self,
        error: ParameterError,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle parameter error."""
        return {
            "action": "reset_parameter",
            "parameter": error.parameter_name,
            "actual_value": error.actual_value,
            "expected_range": error.expected_range,
        }

    def _handle_value_error(
        self,
        error: ValueError,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle built-in ValueError (not ParameterError)."""
        return {
            "action": "log_and_continue",
            "error": str(error),
            "type": "ValueError",
        }

    def _handle_critical_error(
        self,
        error: CriticalError,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle critical error."""
        return {
            "action": "enter_caretaker_mode",
            "reason": error.message,
            "details": error.details,
            "allowed_actions": ["CHAT", "QUERY"],  # Only safe actions
        }

    def _handle_generic_error(
        self,
        error: Exception,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle generic error."""
        return {
            "action": "log_and_continue",
            "error": str(error),
            "type": type(error).__name__,
        }

    def _get_next_tier(self) -> str:
        """Get next degradation tier."""
        tiers = ["full", "reduced", "local_fallback", "safe_mode"]
        current_idx = tiers.index(self._current_tier)
        if current_idx < len(tiers) - 1:
            self._current_tier = tiers[current_idx + 1]
        return self._current_tier

    def reset_tier(self):
        """Reset degradation tier to full."""
        self._current_tier = "full"

    def get_circuit_breaker(self, key: str) -> CircuitBreaker:
        """Get or create circuit breaker for key."""
        if key not in self._circuit_breakers:
            self._circuit_breakers[key] = CircuitBreaker()
        return self._circuit_breakers[key]

    def reset_errors(self, tool_id: Optional[str] = None):
        """Reset error tracking."""
        if tool_id:
            self._consecutive_errors.pop(tool_id, None)
        else:
            self._consecutive_errors.clear()
            self.reset_tier()


# Global error handler instance
_global_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get global error handler instance."""
    global _global_handler
    if _global_handler is None:
        _global_handler = ErrorHandler()
    return _global_handler
