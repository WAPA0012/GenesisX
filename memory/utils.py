"""Utility functions for memory subsystem.

Common helper functions shared across memory modules.
"""
from typing import Any, Union, List
import math

# Optional numpy import for optimized vector operations
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    np = None
    HAS_NUMPY = False


def get_episode_attr(episode: Union[dict, Any], key: str, default: Any = None) -> Any:
    """Get attribute from episode (dict or Pydantic model).

    Args:
        episode: Episode record (dict or Pydantic model)
        key: Attribute key to retrieve
        default: Default value if key not found

    Returns:
        Attribute value or default
    """
    if isinstance(episode, dict):
        return episode.get(key, default)
    return getattr(episode, key, default)


def cosine_similarity(vec1: Union[List[float], Any], vec2: Union[List[float], Any]) -> float:
    """Compute cosine similarity between two vectors.

    Supports both Python lists and numpy arrays.

    Args:
        vec1: First vector (list or numpy array)
        vec2: Second vector (list or numpy array)

    Returns:
        Cosine similarity in [-1, 1]
    """
    # Use numpy if available and inputs are numpy arrays
    if HAS_NUMPY and (isinstance(vec1, np.ndarray) or isinstance(vec2, np.ndarray)):
        v1 = np.asarray(vec1)
        v2 = np.asarray(vec2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(v1, v2) / (norm1 * norm2))

    # Pure Python fallback for lists
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)
