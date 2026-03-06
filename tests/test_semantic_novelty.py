"""
Tests for Semantic Novelty Calculator

Tests the paper Section 3.10.4 requirement for semantic embedding
novelty evaluation instead of lexical overlap (Jaccard similarity).

Paper formula:
C_nov = 1 - max_{s in Schema} cos(emb(insight), emb(s))

This module tests:
- EmbeddingConfig configuration
- Embedding computation with caching
- Novelty calculation using cosine similarity
- TF-IDF fallback
- Batch processing
- Convenience functions
"""

import pytest
import numpy as np
from typing import List
from unittest.mock import Mock, patch, MagicMock
from memory.semantic_novelty import (
    SemanticNoveltyCalculator,
    EmbeddingConfig,
    EmbeddingBackend,
    compute_novelty,
    get_default_calculator,
)

# Backward-compatible alias
EmbeddingModel = EmbeddingConfig


class TestEmbeddingModel:
    """Test EmbeddingConfig configuration."""

    def test_default_config(self):
        """Test default model configuration."""
        config = EmbeddingModel()
        assert config.backend == EmbeddingBackend.TFIDF
        assert config.cache_embeddings is True

    def test_custom_backend(self):
        """Test custom backend configuration."""
        config = EmbeddingModel(backend=EmbeddingBackend.OPENAI)
        assert config.backend == EmbeddingBackend.OPENAI


class TestSemanticNoveltyCalculator:
    """Test SemanticNoveltyCalculator core functionality."""

    def test_initialization(self):
        """Test calculator initialization with defaults (TF-IDF)."""
        calc = SemanticNoveltyCalculator()
        assert calc.config is not None
        assert calc.config.backend == EmbeddingBackend.TFIDF

    def test_initialization_with_custom_config(self):
        """Test initialization with custom config."""
        config = EmbeddingConfig(cache_embeddings=False)
        calc = SemanticNoveltyCalculator(config=config)
        assert calc._cache is None

    def test_initialization_with_cache(self):
        """Test initialization with caching enabled."""
        config = EmbeddingConfig(cache_embeddings=True)
        calc = SemanticNoveltyCalculator(config=config)
        assert calc._cache is not None
        assert isinstance(calc._cache, dict)

    def test_tfidf_embedding(self):
        """Test TF-IDF embedding generation."""
        config = EmbeddingConfig(cache_embeddings=False)
        calc = SemanticNoveltyCalculator(config=config)

        text1 = "hello world"
        text2 = "hello world"

        emb1 = calc.compute_embedding(text1)
        emb2 = calc.compute_embedding(text2)

        # Same text should produce same embedding
        np.testing.assert_array_almost_equal(emb1, emb2)

        # Embedding should have expected dimension
        assert len(emb1) == 384


class TestCosineSimilarity:
    """Test cosine similarity computation."""

    def test_cosine_similarity_identical(self):
        """Test cosine similarity of identical vectors."""
        calc = SemanticNoveltyCalculator()

        vec = np.array([1.0, 0.0, 0.0])
        similarity = calc.cosine_similarity(vec, vec)

        assert similarity == pytest.approx(1.0)

    def test_cosine_similarity_orthogonal(self):
        """Test cosine similarity of orthogonal vectors."""
        calc = SemanticNoveltyCalculator()

        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([0.0, 1.0, 0.0])

        similarity = calc.cosine_similarity(vec1, vec2)

        assert similarity == pytest.approx(0.0)

    def test_cosine_similarity_opposite(self):
        """Test cosine similarity of opposite vectors."""
        calc = SemanticNoveltyCalculator()

        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([-1.0, 0.0, 0.0])

        similarity = calc.cosine_similarity(vec1, vec2)

        assert similarity == pytest.approx(-1.0)

    def test_cosine_similarity_zero_vector(self):
        """Test cosine similarity with zero vector."""
        calc = SemanticNoveltyCalculator()

        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([0.0, 0.0, 0.0])

        similarity = calc.cosine_similarity(vec1, vec2)

        assert similarity == 0.0


class TestNoveltyComputation:
    """Test novelty computation following paper formula."""

    def test_novelty_with_empty_existing(self):
        """Test novelty when no existing texts exist."""
        config = EmbeddingConfig(cache_embeddings=False)
        calc = SemanticNoveltyCalculator(config=config)

        insight = "A completely new insight"
        existing = []

        novelty, is_novel = calc.compute_novelty(insight, existing)

        # Should be completely novel
        assert novelty == pytest.approx(1.0)
        assert is_novel is True

    def test_novelty_with_identical_text(self):
        """Test novelty with identical existing text."""
        config = EmbeddingConfig(cache_embeddings=False)
        calc = SemanticNoveltyCalculator(config=config)

        insight = "This is a test insight"
        existing = ["This is a test insight"]

        novelty, is_novel = calc.compute_novelty(insight, existing, threshold=0.85)

        # Should have very low novelty (high similarity)
        assert novelty < 0.5
        assert is_novel is False

    def test_novelty_with_different_text(self):
        """Test novelty with completely different text."""
        config = EmbeddingConfig(cache_embeddings=False)
        calc = SemanticNoveltyCalculator(config=config)

        insight = "Quantum computing uses qubits"
        existing = ["The sky is blue", "Cats are furry animals"]

        novelty, is_novel = calc.compute_novelty(insight, existing, threshold=0.5)

        # Should have high novelty (different topics)
        assert novelty > 0.5

    def test_novelty_threshold(self):
        """Test novelty threshold logic."""
        config = EmbeddingConfig(cache_embeddings=False)
        calc = SemanticNoveltyCalculator(config=config)

        insight = "Different content here"
        existing = ["Something completely different"]

        # Test with different thresholds
        novelty_high, is_novel_high = calc.compute_novelty(insight, existing, threshold=0.9)
        novelty_low, is_novel_low = calc.compute_novelty(insight, existing, threshold=0.1)

        # Same novelty score
        assert novelty_high == novelty_low

        # With low threshold, more likely to be novel
        assert is_novel_low is True

    def test_novelty_returns_tuple(self):
        """Test that compute_novelty returns proper tuple."""
        config = EmbeddingConfig(cache_embeddings=False)
        calc = SemanticNoveltyCalculator(config=config)

        result = calc.compute_novelty("test", [])

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], float)  # novelty score
        assert isinstance(result[1], bool)    # is_novel flag


class TestBatchNoveltyComputation:
    """Test batch novelty computation."""

    def test_batch_novelty_empty_insights(self):
        """Test batch computation with empty insights."""
        config = EmbeddingConfig(cache_embeddings=False)
        calc = SemanticNoveltyCalculator(config=config)

        results = calc.compute_novelty_batch([], ["existing text"])

        assert results == []

    def test_batch_novelty_multiple_insights(self):
        """Test batch computation with multiple insights."""
        config = EmbeddingConfig(cache_embeddings=False)
        calc = SemanticNoveltyCalculator(config=config)

        insights = ["Insight one", "Insight two", "Insight three"]
        existing = ["Existing content"]

        results = calc.compute_novelty_batch(insights, existing, threshold=0.5)

        assert len(results) == 3

        for novelty, is_novel in results:
            assert 0.0 <= novelty <= 1.0
            assert isinstance(is_novel, bool)

    def test_batch_novelty_with_empty_existing(self):
        """Test batch computation with no existing texts."""
        config = EmbeddingConfig(cache_embeddings=False)
        calc = SemanticNoveltyCalculator(config=config)

        insights = ["Insight one", "Insight two"]
        results = calc.compute_novelty_batch(insights, [])

        # All should be completely novel
        for novelty, is_novel in results:
            assert novelty == pytest.approx(1.0)
            assert is_novel is True


class TestCaching:
    """Test embedding caching functionality."""

    def test_cache_enabled(self):
        """Test that cache is used when enabled."""
        config = EmbeddingConfig(cache_embeddings=True)
        calc = SemanticNoveltyCalculator(config=config)

        text = "test text for caching"

        # First call - compute and cache
        emb1 = calc.compute_embedding(text)
        assert calc._cache is not None
        assert len(calc._cache) > 0

        # Second call - should use cache
        emb2 = calc.compute_embedding(text)

        np.testing.assert_array_equal(emb1, emb2)

    def test_cache_disabled(self):
        """Test that cache is not used when disabled."""
        config = EmbeddingConfig(cache_embeddings=False)
        calc = SemanticNoveltyCalculator(config=config)

        text = "test text without caching"

        emb1 = calc.compute_embedding(text)
        assert calc._cache is None

        emb2 = calc.compute_embedding(text)

        # Should still work, just no caching
        np.testing.assert_array_equal(emb1, emb2)

    def test_clear_cache(self):
        """Test cache clearing."""
        config = EmbeddingConfig(cache_embeddings=True)
        calc = SemanticNoveltyCalculator(config=config)

        # Add some embeddings to cache
        calc.compute_embedding("text 1")
        calc.compute_embedding("text 2")

        assert len(calc._cache) > 0

        # Clear cache
        calc.clear_cache()

        assert len(calc._cache) == 0


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_get_default_calculator(self):
        """Test default calculator factory."""
        calc = get_default_calculator()

        assert isinstance(calc, SemanticNoveltyCalculator)
        assert calc.config.backend == EmbeddingBackend.TFIDF

    def test_compute_novelty_function(self):
        """Test convenience compute_novelty function."""
        insight = "new insight"
        existing = ["existing insight"]

        novelty, is_novel = compute_novelty(insight, existing)

        assert 0.0 <= novelty <= 1.0
        assert isinstance(is_novel, bool)


class TestPaperFormulaCompliance:
    """Test compliance with paper Section 3.10.4 formula."""

    def test_novelty_formula_structure(self):
        """Test that novelty follows formula: C_nov = 1 - max(cos(emb(insight), emb(s)))"""
        config = EmbeddingConfig(cache_embeddings=False)
        calc = SemanticNoveltyCalculator(config=config)

        insight = "test insight"
        existing = ["similar text", "different text"]

        # Compute novelty using the method
        novelty, _ = calc.compute_novelty(insight, existing)

        # Manually compute using formula
        insight_emb = calc.compute_embedding(insight)
        max_sim = 0.0
        for text in existing:
            existing_emb = calc.compute_embedding(text)
            sim = calc.cosine_similarity(insight_emb, existing_emb)
            max_sim = max(max_sim, sim)

        expected_novelty = 1.0 - max_sim

        assert novelty == pytest.approx(expected_novelty, rel=1e-10)

    def test_novelty_range(self):
        """Test that novelty is always in [0, 1] range."""
        config = EmbeddingConfig(cache_embeddings=False)
        calc = SemanticNoveltyCalculator(config=config)

        insights = ["text one", "text two", "text three"]
        existing = ["existing one", "existing two"]

        for insight in insights:
            novelty, _ = calc.compute_novelty(insight, existing)
            assert 0.0 <= novelty <= 1.0
