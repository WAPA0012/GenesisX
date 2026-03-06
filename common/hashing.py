"""
Hashing Utilities for Genesis X.

Provides content hashing and sensitive data redaction.
"""

import hashlib
import json
from typing import Any, Dict, Union


def hash_content(content: str, algorithm: str = 'sha256') -> str:
    """Hash content string using specified algorithm.

    Args:
        content: Content to hash
        algorithm: Hash algorithm (default sha256)

    Returns:
        Hex digest string
    """
    h = hashlib.new(algorithm)
    h.update(content.encode('utf-8'))
    return h.hexdigest()


def hash_dict(data: Dict[str, Any], algorithm: str = 'sha256') -> str:
    """Hash a dictionary by serializing it to a sorted JSON string.

    Args:
        data: Dictionary to hash
        algorithm: Hash algorithm (default sha256)

    Returns:
        Hex digest string
    """
    serialized = json.dumps(data, sort_keys=True, default=str)
    return hash_content(serialized, algorithm)


def hash_any(data: Any, algorithm: str = 'sha256', truncate: int = 0) -> str:
    """Hash any Python object by serializing it.

    Args:
        data: Any Python object to hash
        algorithm: Hash algorithm (default sha256)
        truncate: If > 0, truncate hex digest to this many characters

    Returns:
        Hex digest string (optionally truncated)
    """
    if isinstance(data, str):
        result = hash_content(data, algorithm)
    elif isinstance(data, dict):
        result = hash_dict(data, algorithm)
    else:
        # For other types, serialize to JSON string
        serialized = json.dumps(data, sort_keys=True, default=str)
        result = hash_content(serialized, algorithm)

    if truncate > 0:
        return result[:truncate]
    return result


def redact_sensitive(data: dict, sensitive_keys: set = None) -> dict:
    """Redact sensitive fields from a dictionary.

    Args:
        data: Dictionary to redact
        sensitive_keys: Set of keys to redact (default: common secret keys)

    Returns:
        New dict with sensitive values replaced by [REDACTED]
    """
    if sensitive_keys is None:
        sensitive_keys = {
            'api_key', 'api_secret', 'password', 'token',
            'secret', 'credentials', 'auth_token',
            'access_token', 'refresh_token',
        }

    result = {}
    for key, value in data.items():
        if key.lower() in sensitive_keys:
            result[key] = '[REDACTED]'
        elif isinstance(value, dict):
            result[key] = redact_sensitive(value, sensitive_keys)
        else:
            result[key] = value
    return result
