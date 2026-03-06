"""Insight Quality Assessment Module.

Implements paper Section 3.5.2 (7): Meaning dimension insight quality.

Q^insight has three components:
1. Compression: Can multiple experiences be compressed into one rule?
2. Transferability: Can it improve future task success/reduce cost?
3. Novelty: Is it significantly different from existing schemas?
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class Insight:
    """Represents an insight/schema formed from experience."""
    content: str
    source_episodes: List[int]  # Episode tick numbers
    created_at: int  # Tick when insight was formed
    quality: float = 0.0  # Q^insight ∈ [0,1]
    compression_score: float = 0.0
    transferability_score: float = 0.0
    novelty_score: float = 0.0


class InsightQualityAssessor:
    """Assesses quality of insights for Meaning dimension.

    Paper formula: u^meaning_t = Q^insight_t · 1(insight formed at t)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize assessor.

        Args:
            config: Configuration dict
        """
        self.config = config or {}

        # Weights for quality components
        self.w_compression = self.config.get("weight_compression", 0.4)
        self.w_transferability = self.config.get("weight_transferability", 0.3)
        self.w_novelty = self.config.get("weight_novelty", 0.3)

    def assess_insight(
        self,
        insight: Insight,
        existing_schemas: List[Insight],
        episode_count: int,
    ) -> float:
        """Assess quality of an insight.

        Args:
            insight: Insight to assess
            existing_schemas: Existing schema memory
            episode_count: Total number of episodes

        Returns:
            Quality score Q^insight ∈ [0,1]
        """
        # Component 1: Compression
        compression = self._assess_compression(insight, episode_count)
        insight.compression_score = compression

        # Component 2: Transferability
        transferability = self._assess_transferability(insight)
        insight.transferability_score = transferability

        # Component 3: Novelty
        novelty = self._assess_novelty(insight, existing_schemas)
        insight.novelty_score = novelty

        # Weighted combination
        quality = (
            self.w_compression * compression +
            self.w_transferability * transferability +
            self.w_novelty * novelty
        )

        insight.quality = quality
        return quality

    def _assess_compression(self, insight: Insight, episode_count: int) -> float:
        """Assess compression quality.

        Paper: 是否能把多条经验压缩为一条可复用规则

        Args:
            insight: Insight to assess
            episode_count: Total number of episodes

        Returns:
            Compression score [0,1]
        """
        # Number of source episodes compressed
        num_episodes = len(insight.source_episodes)

        if num_episodes <= 1:
            return 0.0

        # Compression ratio: more episodes compressed = higher score
        # Normalized by total episode count
        compression_ratio = min(1.0, num_episodes / max(10, episode_count * 0.1))

        # Additional bonus for content length efficiency
        # Shorter insights that compress more episodes are better
        content_length = len(insight.content)
        if content_length > 0:
            efficiency = min(1.0, num_episodes / (content_length / 100.0))
        else:
            efficiency = 0.0

        return 0.7 * compression_ratio + 0.3 * efficiency

    def _assess_transferability(self, insight: Insight) -> float:
        """Assess transferability quality.

        Paper: 是否能提升后续任务成功率/减少成本

        Args:
            insight: Insight to assess

        Returns:
            Transferability score [0,1]
        """
        # Heuristic: Check if insight contains actionable patterns
        content = insight.content.lower()

        transferable_indicators = [
            "when",      # Conditional patterns
            "if",        # Decision rules
            "then",      # Consequents
            "always",    # Universal rules
            "never",     # Prohibitions
            "should",    # Recommendations
            "pattern",   # Explicit patterns
            "strategy",  # Strategic insights
            "rule",      # Explicit rules
        ]

        matches = sum(1 for indicator in transferable_indicators if indicator in content)
        score = min(1.0, matches / len(transferable_indicators))

        return score

    def _assess_novelty(
        self,
        insight: Insight,
        existing_schemas: List[Insight]
    ) -> float:
        """Assess novelty quality using semantic embeddings.

        Paper Section 3.10.4: Use sentence embeddings instead of word overlap.
        C_nov = 1 - max_{s∈Schema} cos(emb(insight), emb(s))

        Args:
            insight: Insight to assess
            existing_schemas: Existing schemas

        Returns:
            Novelty score [0,1]
        """
        if not existing_schemas:
            return 1.0  # First insight is maximally novel

        try:
            # Try to use semantic embeddings if available
            from tools.embeddings import get_embedding, cosine_similarity

            # Get embedding for new insight
            new_embedding = get_embedding(insight.content)

            max_similarity = 0.0
            for existing in existing_schemas:
                # Get embedding for existing schema
                existing_embedding = get_embedding(existing.content)

                # Compute cosine similarity
                similarity = cosine_similarity(new_embedding, existing_embedding)
                max_similarity = max(max_similarity, similarity)

            # Novelty is inverse of max similarity
            novelty = 1.0 - max_similarity
            return max(0.0, min(1.0, novelty))

        except ImportError:
            # Fallback to word overlap if embeddings not available
            new_words = set(insight.content.lower().split())

            max_similarity = 0.0
            for existing in existing_schemas:
                existing_words = set(existing.content.lower().split())

                if not new_words or not existing_words:
                    continue

                # Jaccard similarity
                intersection = len(new_words & existing_words)
                union = len(new_words | existing_words)

                similarity = intersection / union if union > 0 else 0.0
                max_similarity = max(max_similarity, similarity)

            # Novelty is inverse of max similarity
            novelty = 1.0 - max_similarity
            return novelty
