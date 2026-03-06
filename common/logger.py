"""
Structured logging system for Genesis X.

Provides JSON-formatted logging with multiple handlers, correlation IDs,
performance tracking, and integration points for external logging services.
"""

import logging
import logging.handlers
import json
import sys
import traceback
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List, Tuple
from pathlib import Path
import contextvars
import os


# Context variable for correlation ID tracking
correlation_id_var = contextvars.ContextVar('correlation_id', default=None)


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def __init__(self, include_trace: bool = True):
        super().__init__()
        self.include_trace = include_trace
        self.hostname = os.environ.get('HOSTNAME', 'unknown')

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.now(timezone.utc).isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread_id': record.thread,
            'thread_name': record.threadName,
            'process_id': record.process,
            'hostname': self.hostname,
        }

        # Add correlation ID if present
        correlation_id = correlation_id_var.get()
        if correlation_id:
            log_data['correlation_id'] = correlation_id

        # Add extra fields from record
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)

        # Add exception information
        if record.exc_info and self.include_trace:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }

        # Add performance metrics if present
        if hasattr(record, 'duration_ms'):
            log_data['duration_ms'] = record.duration_ms

        if hasattr(record, 'memory_mb'):
            log_data['memory_mb'] = record.memory_mb

        return json.dumps(log_data, default=str)


class ConsoleFormatter(logging.Formatter):
    """Human-readable formatter for console output."""

    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'
    }

    def __init__(self, use_colors: bool = True):
        super().__init__()
        self.use_colors = use_colors and sys.stdout.isatty()

    def format(self, record: logging.LogRecord) -> str:
        """Format log record for console."""
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        level = record.levelname

        if self.use_colors:
            color = self.COLORS.get(level, '')
            reset = self.COLORS['RESET']
            level_colored = f"{color}{level:<8}{reset}"
        else:
            level_colored = f"{level:<8}"

        message = record.getMessage()
        location = f"{record.name}:{record.funcName}:{record.lineno}"

        # Add correlation ID if present
        correlation_id = correlation_id_var.get()
        if correlation_id:
            location = f"[{correlation_id}] {location}"

        log_line = f"{timestamp} {level_colored} {location} - {message}"

        # Add exception traceback if present
        if record.exc_info:
            log_line += "\n" + "".join(traceback.format_exception(*record.exc_info))

        return log_line


class ContextAdapter(logging.LoggerAdapter):
    """Logger adapter that adds contextual information to log records."""

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """Add extra fields to log record."""
        extra = kwargs.get('extra', {})

        # Add correlation ID from context
        correlation_id = correlation_id_var.get()
        if correlation_id:
            extra['correlation_id'] = correlation_id

        kwargs['extra'] = extra
        return msg, kwargs


class PerformanceLogger:
    """Context manager for performance logging."""

    def __init__(self, logger: logging.Logger, operation: str, **kwargs):
        self.logger = logger
        self.operation = operation
        self.extra_fields = kwargs
        self.start_time = None

    def __enter__(self):
        """Start timing."""
        self.start_time = time.perf_counter()
        self.logger.debug(f"Starting: {self.operation}", extra={'extra_fields': self.extra_fields})
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Log completion with duration."""
        duration_ms = (time.perf_counter() - self.start_time) * 1000

        extra = self.extra_fields.copy()
        extra['duration_ms'] = duration_ms
        extra['operation'] = self.operation

        if exc_type:
            self.logger.error(
                f"Failed: {self.operation} ({duration_ms:.2f}ms)",
                exc_info=(exc_type, exc_val, exc_tb),
                extra={'extra_fields': extra}
            )
        else:
            level = logging.WARNING if duration_ms > 1000 else logging.INFO
            self.logger.log(
                level,
                f"Completed: {self.operation} ({duration_ms:.2f}ms)",
                extra={'extra_fields': extra}
            )


class ErrorAggregator:
    """Aggregates similar errors to prevent log flooding."""

    def __init__(self, window_seconds: int = 60, max_count: int = 10):
        self.window_seconds = window_seconds
        self.max_count = max_count
        self.errors = {}
        self.lock = threading.Lock()

    def should_log(self, error_key: str) -> Tuple[bool, int]:
        """Check if error should be logged."""
        with self.lock:
            now = time.time()

            # Clean old entries
            self.errors = {
                k: (t, c) for k, (t, c) in self.errors.items()
                if now - t < self.window_seconds
            }

            if error_key in self.errors:
                first_time, count = self.errors[error_key]
                count += 1
                self.errors[error_key] = (first_time, count)

                if count <= self.max_count:
                    return True, count
                elif count == self.max_count + 1:
                    return True, count  # Log "suppressing" message
                else:
                    return False, count
            else:
                self.errors[error_key] = (now, 1)
                return True, 1


class GenesisLogger:
    """Central logging manager for Genesis X."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize logging system."""
        if hasattr(self, '_initialized'):
            return

        self._initialized = True
        self.loggers = {}
        self.error_aggregator = ErrorAggregator()
        self.log_dir = Path('logs')
        self.log_dir.mkdir(exist_ok=True)

        # Configure root logger
        self._setup_root_logger()

    def _setup_root_logger(self):
        """Setup root logger with handlers."""
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)
        root.handlers.clear()

        # Console handler with color formatting
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(ConsoleFormatter(use_colors=True))
        root.addHandler(console_handler)

        # JSON file handler with rotation
        json_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / 'genesis.json',
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=10,
            encoding='utf-8'
        )
        json_handler.setLevel(logging.DEBUG)
        json_handler.setFormatter(StructuredFormatter(include_trace=True))
        root.addHandler(json_handler)

        # Error file handler with rotation
        error_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / 'errors.json',
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=10,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(StructuredFormatter(include_trace=True))
        root.addHandler(error_handler)

    def get_logger(self, name: str, level: Optional[int] = None) -> logging.Logger:
        """Get or create a logger with the specified name."""
        if name not in self.loggers:
            logger = logging.getLogger(name)
            if level:
                logger.setLevel(level)
            self.loggers[name] = logger
        return self.loggers[name]

    def set_level(self, name: str, level: int):
        """Set log level for a specific logger."""
        logger = self.get_logger(name)
        logger.setLevel(level)

    def set_correlation_id(self, correlation_id: str):
        """Set correlation ID for current context."""
        correlation_id_var.set(correlation_id)

    def clear_correlation_id(self):
        """Clear correlation ID from current context."""
        correlation_id_var.set(None)

    def log_performance(self, logger: logging.Logger, operation: str, **kwargs) -> PerformanceLogger:
        """Create performance logging context."""
        return PerformanceLogger(logger, operation, **kwargs)


# Global logger instance
_logger_manager = GenesisLogger()


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (typically __name__)
        level: Optional log level override

    Returns:
        Configured logger instance
    """
    return _logger_manager.get_logger(name, level)


def set_correlation_id(correlation_id: str):
    """Set correlation ID for request tracking."""
    _logger_manager.set_correlation_id(correlation_id)


def clear_correlation_id():
    """Clear correlation ID."""
    _logger_manager.clear_correlation_id()


def log_performance(logger: logging.Logger, operation: str, **kwargs):
    """
    Context manager for performance logging.

    Example:
        with log_performance(logger, "database_query", table="users"):
            # ... perform operation ...
            pass
    """
    return _logger_manager.log_performance(logger, operation, **kwargs)


def configure_module_levels(levels: Dict[str, int]):
    """
    Configure log levels for multiple modules.

    Args:
        levels: Dict mapping module names to log levels

    Example:
        configure_module_levels({
            'genesis.core': logging.DEBUG,
            'genesis.api': logging.INFO,
            'genesis.llm': logging.WARNING
        })
    """
    for name, level in levels.items():
        _logger_manager.set_level(name, level)
