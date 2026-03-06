"""Tests for Insight Quality Assessment."""
import pytest
import numpy as np
from cognition.insight_quality import InsightQualityAssessor, Insight


class TestInsightQuality:
    """Test insight quality assessment."""

    def test_assess_basic(self):
        """Test basic insight assessment."""
        assessor = InsightQualityAssessor()

        insight = Insight(
            content="When user asks about X, always check Y first",
            source_episodes=[1, 2, 3, 4, 5],
            created_at=100,
        )

        quality = assessor.assess_insight(insight, [], 100)

        assert 0.0 <= quality <= 1.0
        assert insight.quality == quality

    def test_compression_score(self):
        """Test compression scoring."""
        assessor = InsightQualityAssessor()

        # More episodes = higher compression
        insight_many = Insight(
            content="Pattern found",
            source_episodes=list(range(20)),
            created_at=100,
        )

        insight_few = Insight(
            content="Pattern found",
            source_episodes=[1, 2],
            created_at=100,
        )

        assessor.assess_insight(insight_many, [], 100)
        assessor.assess_insight(insight_few, [], 100)

        assert insight_many.compression_score > insight_few.compression_score

    def test_novelty_score(self):
        """Test novelty scoring with controlled embeddings."""
        import unittest.mock as mock

        assessor = InsightQualityAssessor()

        existing = Insight(
            content="Always check input before processing",
            source_episodes=[1],
            created_at=50,
        )

        # Similar insight
        similar = Insight(
            content="Always check input before output",
            source_episodes=[2],
            created_at=100,
        )

        # Different insight
        different = Insight(
            content="The sky is blue and clouds are white",
            source_episodes=[3],
            created_at=100,
        )

        # Create controlled mock embeddings
        # Similar vectors: high cosine similarity
        embedding_existing = np.array([1.0, 0.0, 0.0, 0.0])
        embedding_similar = np.array([0.9, 0.1, 0.0, 0.0])
        # Different vector: low cosine similarity
        embedding_different = np.array([0.1, 0.1, 0.7, 0.7])

        def mock_get_embedding(text):
            if "processing" in text:
                return embedding_existing
            elif "output" in text:
                return embedding_similar
            else:
                return embedding_different

        def mock_cosine_sim(emb1, emb2):
            e1 = emb1 / (np.linalg.norm(emb1) + 1e-10)
            e2 = emb2 / (np.linalg.norm(emb2) + 1e-10)
            return float(np.dot(e1, e2))

        # Patch at the source module level
        with mock.patch('tools.embeddings.get_embedding', side_effect=mock_get_embedding):
            with mock.patch('tools.embeddings.cosine_similarity', side_effect=mock_cosine_sim):
                assessor.assess_insight(similar, [existing], 100)
                assessor.assess_insight(different, [existing], 100)

        # Verify: different insight should have higher novelty
        assert different.novelty_score > similar.novelty_score
        # Similar insight should have low novelty due to high similarity
        assert similar.novelty_score < 0.5
        # Different insight should have high novelty
        assert different.novelty_score > 0.5

    def test_first_insight_max_novelty(self):
        """Test that first insight has max novelty."""
        assessor = InsightQualityAssessor()

        insight = Insight(
            content="First insight ever",
            source_episodes=[1],
            created_at=1,
        )

        assessor.assess_insight(insight, [], 10)

        assert insight.novelty_score == 1.0
