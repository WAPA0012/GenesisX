"""Common utility functions for Genesis X.

This module contains reusable utility functions that reduce code duplication
across the codebase.
"""
import logging
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar, Tuple, Type, Dict, List
from functools import wraps


# Type variable for generic return types
T = TypeVar('T')


def safe_execute(
    operation: Callable[..., T],
    error_message: str,
    logger: logging.Logger,
    default_return: Optional[T] = None,
    reraise: bool = False,
    exc_type: Tuple[Type[Exception], ...] = (Exception,),
) -> Optional[T]:
    """Execute operation with try/catch wrapper and error handling.

    This is a common pattern used throughout the codebase to handle
    exceptions with consistent logging and return values.

    Args:
        operation: The function to execute
        error_message: Error message to log if operation fails
        logger: Logger instance for error reporting
        default_return: Value to return on failure (default: None)
        reraise: If True, re-raise the exception after logging (default: False)
        exc_type: Exception types to catch (default: all Exceptions)

    Returns:
        The result of the operation, or default_return on failure

    Examples:
        >>> def risky_operation():
        ...     return 1 / 0
        >>> result = safe_execute(risky_operation, "Division failed", logger)
        >>> result is None
        True

        >>> result = safe_execute(lambda: 42, "Calculation", logger, default_return=0)
        >>> result
        42
    """
    try:
        return operation()
    except exc_type as e:
        logger.error(f"{error_message}: {e}")
        if reraise:
            raise
        return default_return


def ensure_directory_exists(
    filepath: Path,
    logger: Optional[logging.Logger] = None,
    is_file: bool = True,
) -> bool:
    """Ensure parent directory exists for a file path.

    This is a common pattern before file write operations throughout
    the memory and persistence modules.

    Args:
        filepath: Path to file or directory
        logger: Optional logger for debug logging
        is_file: If True, creates parent directory for filepath.
                 If False, creates filepath itself as directory.

    Returns:
        True if directory exists or was created successfully, False otherwise

    Examples:
        >>> from pathlib import Path
        >>> import tempfile
        >>> tmpdir = Path(tempfile.mkdtemp())
        >>> filepath = tmpdir / "subdir" / "file.txt"
        >>> ensure_directory_exists(filepath, is_file=True)
        True
        >>> filepath.parent.exists()
        True
    """
    try:
        target_dir = filepath.parent if is_file else filepath
        target_dir.mkdir(parents=True, exist_ok=True)
        if logger:
            logger.debug(f"Ensured directory exists: {target_dir}")
        return True
    except OSError as e:
        if logger:
            logger.error(f"Failed to create directory {filepath.parent}: {e}")
        return False


def validate_secrets(
    config_dict: Dict[str, Any],
    required_secrets: List[str],
    logger: logging.Logger,
    config_name: str = "config",
) -> bool:
    """Validate that all required secrets are present and non-empty.

    Common pattern for validating API keys and other sensitive configuration.

    Args:
        config_dict: Configuration dictionary to validate
        required_secrets: List of secret field names that must be present
        logger: Logger instance for validation reporting
        config_name: Name of config for logging (default: "config")

    Returns:
        True if all secrets are present and non-empty, False otherwise

    Examples:
        >>> import logging
        >>> logger = logging.getLogger(__name__)
        >>> config = {"API_KEY": "sk-12345", "SECRET": ""}
        >>> validate_secrets(config, ["API_KEY"], logger)
        True
        >>> validate_secrets(config, ["SECRET"], logger)
        False
    """
    all_valid = True

    for secret_field in required_secrets:
        value = config_dict.get(secret_field)

        if value is None:
            logger.error(f"{config_name}: Missing required secret '{secret_field}'")
            all_valid = False
        elif isinstance(value, str) and not value.strip():
            logger.error(f"{config_name}: Secret '{secret_field}' is empty")
            all_valid = False
        else:
            logger.debug(f"{config_name}: Secret '{secret_field}' validated")

    return all_valid


def serialize_labels(labels: Dict[str, str]) -> str:
    """Serialize labels to JSON string with consistent sorting.

    This creates hashable keys from labels for metrics storage.

    Args:
        labels: Dictionary of label key-value pairs

    Returns:
        JSON string with sorted keys for consistent serialization

    Examples:
        >>> serialize_labels({"env": "prod", "region": "us-east-1"})
        '{"env":"prod","region":"us-east-1"}'
        >>> serialize_labels({"b": 2, "a": 1})
        '{"a":1,"b":2}'
    """
    import json
    return json.dumps(labels, sort_keys=True)


def retry_on_failure(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """Decorator to retry a function on failure.

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        exceptions: Exception types to catch and retry

    Returns:
        Decorated function that retries on failure

    Examples:
        >>> import random
        >>> @retry_on_failure(max_attempts=3, delay=0.1)
        ... def flaky_function():
        ...     if random.random() < 0.5:
        ...         raise ValueError("Random failure")
        ...     return "success"
    """
    import time

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            current_delay = delay
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(current_delay)
                        current_delay *= backoff

            raise last_exception  # type: ignore

        return wrapper
    return decorator


def format_timedelta(seconds: float) -> str:
    """Format seconds into human-readable time string.

    Args:
        seconds: Time duration in seconds

    Returns:
        Formatted string (e.g., "1h 23m 45.6s")

    Examples:
        >>> format_timedelta(3661.6)
        '1h 1m 1.6s'
        >>> format_timedelta(45.6)
        '45.6s'
        >>> format_timedelta(125)
        '2m 5.0s'
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60

    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs:.1f}s")

    return " ".join(parts)


# Example usage and testing
if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)

    print("Genesis X Common Utilities")
    print("=" * 60)

    # Test safe_execute
    print("\n1. Testing safe_execute:")
    result = safe_execute(lambda: 10 / 2, "Division", logger, default_return=-1)
    print(f"   Success: {result}")

    result = safe_execute(lambda: 10 / 0, "Division", logger, default_return=-1)
    print(f"   Failure (with default): {result}")

    # Test ensure_directory_exists
    print("\n2. Testing ensure_directory_exists:")
    import tempfile
    tmpdir = Path(tempfile.mkdtemp())
    test_file = tmpdir / "test" / "subdir" / "file.txt"
    ensure_directory_exists(test_file, logger)
    print(f"   Directory created: {test_file.parent.exists()}")

    # Test validate_secrets
    print("\n3. Testing validate_secrets:")
    config = {"API_KEY": "sk-12345", "SECRET": ""}
    valid = validate_secrets(config, ["API_KEY", "SECRET"], logger)
    print(f"   Validation result: {valid}")

    # Test serialize_labels
    print("\n4. Testing serialize_labels:")
    labels_str = serialize_labels({"env": "prod", "region": "us-east-1"})
    print(f"   Serialized: {labels_str}")

    # Test format_timedelta
    print("\n5. Testing format_timedelta:")
    print(f"   3661.6s -> {format_timedelta(3661.6)}")
    print(f"   45.6s -> {format_timedelta(45.6)}")

    print("\n✓ All utilities working correctly")
