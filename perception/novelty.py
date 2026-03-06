"""
Novelty Detector: Deterministic Novelty Score Calculation

Calculates novelty based on:
- Embedding distance from recent experiences
- Frequency of similar inputs
- Semantic dissimilarity

References:
- 代码大纲架构 perception/novelty.py
- 论文 Curiosity drive and novelty detection
"""

from typing import Dict, Any, List, Optional
import numpy as np
from collections import deque
import time

from memory.utils import cosine_similarity as _cosine_similarity_shared
from common.hashing import hash_any


class NoveltyDetector:
    """
    Deterministic novelty score calculator.

    Uses:
    - Content hashing for exact match detection
    - Embedding distance for semantic novelty (if available)
    - Recency weighting
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # History buffer
        self.history_size = config.get("history_size", 100)
        self.recent_inputs: deque = deque(maxlen=self.history_size)

        # Novelty thresholds
        self.high_novelty_threshold = config.get("high_novelty_threshold", 0.7)
        self.low_novelty_threshold = config.get("low_novelty_threshold", 0.3)

        # Recency decay factor
        self.recency_decay = config.get("recency_decay", 0.95)

    def calculate_novelty(
        self,
        input_data: Any,
        embedding: Optional[np.ndarray] = None
    ) -> float:
        """
        Calculate novelty score for input.

        Args:
            input_data: Input data
            embedding: Optional embedding vector

        Returns:
            Novelty score [0, 1]
        """
        # Calculate content hash
        content_hash = hash_any(input_data, truncate=16)

        # Check for exact matches
        if self._has_exact_match(content_hash):
            return 0.0

        # If no embedding, use frequency-based novelty
        if embedding is None:
            return self._frequency_based_novelty(content_hash)

        # Use embedding-based novelty
        return self._embedding_based_novelty(embedding)

    def _has_exact_match(self, content_hash: str) -> bool:
        """Check if content hash exists in recent history"""
        for entry in self.recent_inputs:
            if entry.get("hash") == content_hash:
                return True
        return False

    def _frequency_based_novelty(self, content_hash: str) -> float:
        """
        Calculate novelty based on frequency of similar inputs.

        Args:
            content_hash: Content hash

        Returns:
            Novelty score [0, 1]
        """
        if not self.recent_inputs:
            return 1.0

        # Count similar inputs with recency weighting
        similarity_score = 0.0
        total_weight = 0.0

        for i, entry in enumerate(self.recent_inputs):
            # Recency weight (more recent = higher weight)
            recency_weight = self.recency_decay ** (len(self.recent_inputs) - i - 1)

            # Simple similarity: exact match = 1.0, else 0.0
            similarity = 1.0 if entry.get("hash") == content_hash else 0.0

            similarity_score += similarity * recency_weight
            total_weight += recency_weight

        avg_similarity = similarity_score / total_weight if total_weight > 0 else 0.0

        # Novelty is inverse of similarity
        novelty = 1.0 - avg_similarity

        return max(0.0, min(1.0, novelty))

    def _embedding_based_novelty(self, embedding: np.ndarray) -> float:
        """
        Calculate novelty based on embedding distance.

        Args:
            embedding: Input embedding vector

        Returns:
            Novelty score [0, 1]
        """
        if not self.recent_inputs:
            return 1.0

        # Calculate distances to recent embeddings
        distances = []
        weights = []

        for i, entry in enumerate(self.recent_inputs):
            if "embedding" not in entry:
                continue

            # Cosine distance
            other_embedding = entry["embedding"]
            distance = self._cosine_distance(embedding, other_embedding)

            # Recency weight
            recency_weight = self.recency_decay ** (len(self.recent_inputs) - i - 1)

            distances.append(distance)
            weights.append(recency_weight)

        if not distances:
            return 1.0

        # Weighted average distance
        avg_distance = np.average(distances, weights=weights)

        # Map distance to novelty score
        # Distance 0 (identical) -> novelty 0
        # Distance 1 (orthogonal) -> novelty 1
        # Distance 2 (opposite) -> novelty 1 (clamp)
        # 余弦距离范围是[0, 2]，需要归一化到[0, 1]
        novelty = min(1.0, avg_distance)  # distance >= 1 都视为完全新颖

        return max(0.0, novelty)

    @staticmethod
    def _cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine distance between two vectors"""
        # Distance = 1 - similarity
        return 1.0 - _cosine_similarity_shared(a, b)

    def update_history(
        self,
        input_data: Any,
        embedding: Optional[np.ndarray] = None
    ):
        """
        Add input to history.

        Args:
            input_data: Input data
            embedding: Optional embedding vector
        """
        content_hash = hash_any(input_data, truncate=16)

        entry = {
            "hash": content_hash,
            "timestamp": time.time(),
        }

        if embedding is not None:
            entry["embedding"] = embedding

        self.recent_inputs.append(entry)

    def is_novel(self, input_data: Any, embedding: Optional[np.ndarray] = None) -> bool:
        """
        Check if input is novel (above threshold).

        Args:
            input_data: Input data
            embedding: Optional embedding vector

        Returns:
            True if novel
        """
        novelty = self.calculate_novelty(input_data, embedding)
        return novelty >= self.high_novelty_threshold

    def get_novelty_category(self, novelty_score: float) -> str:
        """
        Categorize novelty score.

        Args:
            novelty_score: Novelty score [0, 1]

        Returns:
            Category: "high", "medium", "low"
        """
        if novelty_score >= self.high_novelty_threshold:
            return "high"
        elif novelty_score >= self.low_novelty_threshold:
            return "medium"
        else:
            return "low"

    def reset(self):
        """Clear history"""
        self.recent_inputs.clear()
