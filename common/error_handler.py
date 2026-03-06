"""
Global error handling system for Genesis X.

Provides error categorization, reporting, retry mechanisms,
and circuit breaker pattern for graceful degradation.
"""

import sys
import traceback
import time
import threading
from typing import Optional, Callable, Any, Dict, List, Type
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import logging


class ErrorCategory(Enum):
    """Error categories for classification."""
    TRANSIENT = "transient"          # Temporary errors, retry likely to succeed
    PERMANENT = "permanent"          # Permanent errors, retry won't help
    CONFIGURATION = "configuration"  # Configuration/setup errors
    VALIDATION = "validation"        # Input validation errors
    RESOURCE = "resource"            # Resource exhaustion (memory, disk, etc.)
    NETWORK = "network"              # Network connectivity errors
    API = "api"                      # External API errors
    DATABASE = "database"            # Database errors
    TIMEOUT = "timeout"              # Operation timeout
    UNKNOWN = "unknown"              # Uncategorized errors


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """Context information for an error."""
    error: Exception
    category: ErrorCategory
    severity: ErrorSeverity
    component: str
    operation: str
    timestamp: datetime
    traceback_str: str
    metadata: Dict[str, Any]
    retry_count: int = 0


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.

    Prevents cascading failures by stopping requests to failing services.
    """

    class State(Enum):
        CLOSED = "closed"      # Normal operation
        OPEN = "open"          # Failing, reject requests
        HALF_OPEN = "half_open"  # Testing if service recovered

    def __init__(self,
                 failure_threshold: int = 5,
                 recovery_timeout: float = 60.0,
                 success_threshold: int = 2):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying again
            success_threshold: Successes needed to close circuit from half-open
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.state = self.State.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.lock = threading.Lock()

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker.

        Raises:
            CircuitBreakerOpenError: If circuit is open
        """
        with self.lock:
            if self.state == self.State.OPEN:
                if self._should_attempt_reset():
                    self.state = self.State.HALF_OPEN
                    self.success_count = 0
                else:
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker is open. Last failure: {self.last_failure_time}"
                    )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try reset."""
        if self.last_failure_time is None:
            return True
        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.recovery_timeout

    def _on_success(self):
        """Handle successful call."""
        with self.lock:
            self.failure_count = 0

            if self.state == self.State.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    self.state = self.State.CLOSED
                    self.success_count = 0

    def _on_failure(self):
        """Handle failed call."""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.state == self.State.HALF_OPEN:
                self.state = self.State.OPEN
            elif self.failure_count >= self.failure_threshold:
                self.state = self.State.OPEN

    def reset(self):
        """Manually reset circuit breaker."""
        with self.lock:
            self.state = self.State.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.last_failure_time = None


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


class RetryPolicy:
    """Configuration for retry behavior."""

    def __init__(self,
                 max_attempts: int = 3,
                 initial_delay: float = 1.0,
                 max_delay: float = 60.0,
                 exponential_base: float = 2.0,
                 jitter: bool = True):
        """
        Initialize retry policy.

        Args:
            max_attempts: Maximum number of retry attempts
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay between retries
            exponential_base: Base for exponential backoff
            jitter: Add random jitter to delays
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number."""
        delay = min(
            self.initial_delay * (self.exponential_base ** attempt),
            self.max_delay
        )

        if self.jitter:
            import random
            delay *= (0.5 + random.random())

        return delay


class ErrorHandler:
    """Global error handler for Genesis X."""

    def __init__(self):
        """Initialize error handler."""
        self.logger = logging.getLogger(__name__)
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.error_callbacks: List[Callable[[ErrorContext], None]] = []
        self.categorizers: List[Callable[[Exception], Optional[ErrorCategory]]] = []

        # Register default categorizers
        self._register_default_categorizers()

    def _register_default_categorizers(self):
        """Register default error categorizers."""
        def categorize_common_errors(error: Exception) -> Optional[ErrorCategory]:
            error_type = type(error).__name__
            error_msg = str(error).lower()

            # Transient errors
            if any(x in error_msg for x in ['timeout', 'timed out', 'connection reset']):
                return ErrorCategory.TRANSIENT

            # Network errors
            if any(x in error_msg for x in ['connection', 'network', 'socket', 'dns']):
                return ErrorCategory.NETWORK

            # API errors
            if any(x in error_type.lower() for x in ['api', 'http', 'request']):
                return ErrorCategory.API

            # Resource errors
            if any(x in error_msg for x in ['memory', 'disk', 'quota', 'limit exceeded']):
                return ErrorCategory.RESOURCE

            # Validation errors
            if any(x in error_type.lower() for x in ['validation', 'value', 'type']):
                return ErrorCategory.VALIDATION

            return None

        self.categorizers.append(categorize_common_errors)

    def categorize_error(self, error: Exception) -> ErrorCategory:
        """Categorize an error."""
        for categorizer in self.categorizers:
            category = categorizer(error)
            if category:
                return category
        return ErrorCategory.UNKNOWN

    def handle_error(self,
                    error: Exception,
                    component: str,
                    operation: str,
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                    metadata: Optional[Dict[str, Any]] = None,
                    retry_count: int = 0) -> ErrorContext:
        """
        Handle an error with full context.

        Args:
            error: The exception
            component: Component where error occurred
            operation: Operation being performed
            severity: Error severity
            metadata: Additional context
            retry_count: Current retry attempt

        Returns:
            ErrorContext object
        """
        category = self.categorize_error(error)

        context = ErrorContext(
            error=error,
            category=category,
            severity=severity,
            component=component,
            operation=operation,
            timestamp=datetime.now(timezone.utc),
            traceback_str=traceback.format_exc(),
            metadata=metadata or {},
            retry_count=retry_count
        )

        # Log the error
        self._log_error(context)

        # Notify callbacks
        for callback in self.error_callbacks:
            try:
                callback(context)
            except Exception as e:
                self.logger.error(f"Error in error callback: {e}")

        return context

    def _log_error(self, context: ErrorContext):
        """Log error with appropriate level."""
        log_data = {
            'error_type': type(context.error).__name__,
            'error_message': str(context.error),
            'category': context.category.value,
            'severity': context.severity.value,
            'component': context.component,
            'operation': context.operation,
            'retry_count': context.retry_count,
            **context.metadata
        }

        if context.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(f"Critical error in {context.component}", extra={'extra_fields': log_data})
        elif context.severity == ErrorSeverity.HIGH:
            self.logger.error(f"Error in {context.component}", extra={'extra_fields': log_data})
        elif context.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(f"Error in {context.component}", extra={'extra_fields': log_data})
        else:
            self.logger.info(f"Minor error in {context.component}", extra={'extra_fields': log_data})

    def retry_with_backoff(self,
                          func: Callable,
                          *args,
                          policy: Optional[RetryPolicy] = None,
                          component: str = "unknown",
                          operation: str = "unknown",
                          **kwargs) -> Any:
        """
        Execute function with retry logic and exponential backoff.

        Args:
            func: Function to execute
            policy: Retry policy (uses default if None)
            component: Component name for error tracking
            operation: Operation name for error tracking
            *args, **kwargs: Arguments to pass to function

        Returns:
            Function result

        Raises:
            Last exception if all retries fail
        """
        policy = policy or RetryPolicy()
        last_error = None

        for attempt in range(policy.max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e

                # Handle the error
                context = self.handle_error(
                    e,
                    component=component,
                    operation=operation,
                    retry_count=attempt,
                    metadata={'max_attempts': policy.max_attempts}
                )

                # Don't retry permanent errors
                if context.category == ErrorCategory.PERMANENT:
                    raise

                # If not last attempt, wait and retry
                if attempt < policy.max_attempts - 1:
                    delay = policy.get_delay(attempt)
                    self.logger.info(
                        f"Retrying {operation} after {delay:.2f}s (attempt {attempt + 1}/{policy.max_attempts})"
                    )
                    time.sleep(delay)

        # All retries failed
        raise last_error

    def get_circuit_breaker(self, name: str, **kwargs) -> CircuitBreaker:
        """Get or create a circuit breaker."""
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker(**kwargs)
        return self.circuit_breakers[name]

    def register_callback(self, callback: Callable[[ErrorContext], None]):
        """Register error callback (e.g., for Sentry)."""
        self.error_callbacks.append(callback)

    def register_categorizer(self, categorizer: Callable[[Exception], Optional[ErrorCategory]]):
        """Register custom error categorizer."""
        self.categorizers.append(categorizer)


# Global error handler instance
_error_handler = ErrorHandler()


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance."""
    return _error_handler


def handle_error(error: Exception, component: str, operation: str, **kwargs) -> ErrorContext:
    """Convenience function to handle an error."""
    return _error_handler.handle_error(error, component, operation, **kwargs)


def retry_with_backoff(func: Callable, *args, **kwargs) -> Any:
    """Convenience function to retry with backoff."""
    return _error_handler.retry_with_backoff(func, *args, **kwargs)
