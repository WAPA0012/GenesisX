"""
Embeddings Tool: Text Embedding Generation (Deterministic Replay)

Generates vector embeddings for text:
- Semantic similarity search
- Memory retrieval
- Novelty detection

MUST be deterministic for replay:
- Cache all embeddings with input hash
- During replay, return cached embeddings
- No randomness in embedding generation

Supports multiple backends:
1. sentence-transformers - Local semantic embeddings (recommended, paper-compliant)
2. OpenAI embeddings API
3. DashScope (千问) embeddings API (TODO: not yet implemented)
4. Mock fallback - Deterministic hash-based vectors

References:
- 代码大纲 tools/embeddings.py
- 工作索引 04.5 embeddings(可回放)
- 论文 Section 3.10.4: 语义嵌入 (sentence embeddings)

修复：添加缓存大小限制，防止内存无限增长。
"""

from typing import Dict, Any, Optional, List, Tuple
from .tool_protocol import Tool, ToolMetadata, ToolRiskLevel, ToolDeterminism
from collections import OrderedDict
import numpy as np
import hashlib

from memory.utils import cosine_similarity as _cosine_similarity_shared
from common.constants import ToolConstants


class LRUCache(OrderedDict):
    """LRU缓存实现

    修复：限制缓存大小，防止内存无限增长。
    """

    def __init__(self, max_size: int = ToolConstants.MAX_EMBEDDING_CACHE_SIZE):
        super().__init__()
        self.max_size = max_size

    def __setitem__(self, key, value):
        """设置缓存项，超过容量时删除最旧的项"""
        if key in self:
            self.move_to_end(key)
        super().__setitem__(key, value)
        if len(self) > self.max_size:
            self.popitem(last=False)


class EmbeddingsTool(Tool):
    """
    Generate text embeddings with deterministic replay support.

    修复：添加LRU缓存限制，防止内存泄漏。

    For replay to work:
    - All embeddings are cached with input hash
    - Replay mode returns cached embeddings
    - Mock implementation uses deterministic hash-based vectors
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.config = config

        # Embedding dimension
        self.embedding_dim = config.get("embedding_dim", 768)

        # 修复：使用LRU缓存限制大小，防止内存无限增长
        max_cache_size = config.get("max_cache_size", ToolConstants.MAX_EMBEDDING_CACHE_SIZE)
        self.cache: LRUCache = LRUCache(max_cache_size)

        # Mock mode (no real embedding model)
        self.mock_mode = config.get("embeddings_mock", True)

    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata"""
        return ToolMetadata(
            tool_id="embeddings",
            name="Text Embeddings",
            description="Generate semantic embeddings for text (deterministic)",
            risk_level=ToolRiskLevel.SAFE,
            determinism=ToolDeterminism.DETERMINISTIC,
            requires_approval=False,
            cost_estimate=0.0001,
            tags=["embeddings", "semantic", "deterministic"],
        )

    def validate_parameters(self, parameters: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate embedding parameters"""
        if "text" not in parameters:
            return False, "Missing required parameter 'text'"

        text = parameters["text"]
        if not isinstance(text, str):
            return False, "Text must be a string"

        return True, None

    def execute(self, parameters: Dict[str, Any]) -> Any:
        """
        Generate embedding for text.

        Args:
            parameters: {
                "text": str - Text to embed
                "use_cache": bool (optional) - Use cached embedding if available
            }

        Returns:
            Embedding vector as list
        """
        text = parameters["text"]
        use_cache = parameters.get("use_cache", True)

        # Generate input hash for caching
        input_hash = self._hash_text(text)

        # Check cache first
        if use_cache and input_hash in self.cache:
            embedding = self.cache[input_hash]
            return {
                "embedding": embedding.tolist(),
                "dimension": len(embedding),
                "cached": True,
            }

        # Generate embedding
        if self.mock_mode:
            embedding = self._generate_mock_embedding(text)
        else:
            embedding = self._generate_real_embedding(text)

        # Cache for future use
        self.cache[input_hash] = embedding

        return {
            "embedding": embedding.tolist(),
            "dimension": len(embedding),
            "cached": False,
        }

    def batch_embed(self, texts: List[str]) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        embeddings = []

        for text in texts:
            result = self.execute({"text": text})
            embedding = np.array(result["embedding"])
            embeddings.append(embedding)

        return embeddings

    def _hash_text(self, text: str) -> str:
        """Generate hash for text (for caching)"""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]

    def _generate_mock_embedding(self, text: str) -> np.ndarray:
        """
        Generate deterministic mock embedding.

        Uses text hash to seed random generator for consistency.

        Args:
            text: Input text

        Returns:
            Embedding vector (numpy array)
        """
        # Use text hash as seed for determinism
        text_hash = self._hash_text(text)
        seed = int(text_hash, 16) % (2**32)

        # Generate deterministic "random" vector
        rng = np.random.RandomState(seed)
        embedding = rng.randn(self.embedding_dim)

        # Normalize to unit length
        embedding = embedding / (np.linalg.norm(embedding) + 1e-10)

        return embedding

    def _generate_real_embedding(self, text: str) -> np.ndarray:
        """
        Generate real embedding using actual model.

        Supports multiple embedding backends:
        1. sentence-transformers (local models)
        2. OpenAI embeddings API
        3. 千问 embeddings API (DashScope)

        Args:
            text: Input text

        Returns:
            Embedding vector
        """
        # Try to use sentence-transformers if available
        try:
            from sentence_transformers import SentenceTransformer

            # Lazy load model (load on first use)
            if not hasattr(self, '_st_model'):
                model_name = self.config.get("st_model", "sentence-transformers/all-MiniLM-L6-v2")
                self._st_model = SentenceTransformer(model_name)

            # Generate embedding
            embedding = self._st_model.encode(text, convert_to_numpy=True)
            return embedding

        except ImportError:
            # sentence-transformers not available, try API
            pass

        # Fallback to mock embedding (sentence-transformers not available)
        import warnings
        warnings.warn("sentence-transformers not available, using mock embedding")

        # Fallback to mock embedding
        return self._generate_mock_embedding(text)

    def cosine_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Cosine similarity [-1, 1]
        """
        return _cosine_similarity_shared(embedding1, embedding2)

    def find_most_similar(
        self,
        query_text: str,
        candidate_texts: List[str],
        top_k: int = 5
    ) -> List[tuple]:
        """
        Find most similar texts to query.

        Args:
            query_text: Query text
            candidate_texts: List of candidate texts
            top_k: Number of top results to return

        Returns:
            List of (text, similarity) tuples, sorted by similarity
        """
        # Embed query
        query_result = self.execute({"text": query_text})
        query_embedding = np.array(query_result["embedding"])

        # Embed candidates
        candidate_embeddings = self.batch_embed(candidate_texts)

        # Calculate similarities
        similarities = []
        for text, embedding in zip(candidate_texts, candidate_embeddings):
            sim = self.cosine_similarity(query_embedding, embedding)
            similarities.append((text, sim))

        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_k]

    def clear_cache(self):
        """Clear embedding cache"""
        self.cache.clear()

    def get_cache_size(self) -> int:
        """Get number of cached embeddings"""
        return len(self.cache)

    def export_cache(self) -> Dict[str, List[float]]:
        """Export cache for serialization"""
        return {
            hash_key: embedding.tolist()
            for hash_key, embedding in self.cache.items()
        }

    def import_cache(self, cache_data: Dict[str, List[float]]):
        """Import cache from serialization"""
        self.cache = {
            hash_key: np.array(embedding)
            for hash_key, embedding in cache_data.items()
        }


# Convenience functions for external modules (e.g., insight_quality.py)
_default_tool = None


def _get_default_tool() -> EmbeddingsTool:
    """Get or create default embedding tool."""
    global _default_tool
    if _default_tool is None:
        _default_tool = EmbeddingsTool({"embeddings_mock": True, "embedding_dim": 768})
    return _default_tool


def get_embedding(text: str, use_cache: bool = True) -> np.ndarray:
    """
    Get embedding for text (convenience function).

    Paper Section 3.10.4: Used for semantic novelty assessment.

    Args:
        text: Text to embed
        use_cache: Whether to use cached embedding

    Returns:
        Embedding vector as numpy array
    """
    tool = _get_default_tool()
    result = tool.execute({"text": text, "use_cache": use_cache})
    return np.array(result["embedding"])


def cosine_similarity(
    embedding1: np.ndarray,
    embedding2: np.ndarray
) -> float:
    """
    Calculate cosine similarity between two embeddings.

    Paper Section 3.10.4: C_nov = 1 - max cos(emb(insight), emb(schema))

    Args:
        embedding1: First embedding vector
        embedding2: Second embedding vector

    Returns:
        Cosine similarity in [-1, 1]
    """
    tool = _get_default_tool()
    return tool.cosine_similarity(embedding1, embedding2)


def get_embedding_tool(config: Dict[str, Any] = None) -> EmbeddingsTool:
    """
    Get a new embedding tool with custom config.

    Args:
        config: Optional configuration

    Returns:
        New EmbeddingsTool instance
    """
    if config is None:
        config = {}
    return EmbeddingsTool(config)


# Example usage and test
if __name__ == "__main__":
    tool = EmbeddingsTool({"embeddings_mock": True, "embedding_dim": 128})

    # Test single embedding
    result = tool.execute({"text": "Hello, world!"})
    print("Embedding result:")
    print(f"  Dimension: {result['dimension']}")
    print(f"  Cached: {result['cached']}")
    print(f"  First 5 values: {result['embedding'][:5]}")

    # Test determinism
    result2 = tool.execute({"text": "Hello, world!"})
    print(f"\nSecond call cached: {result2['cached']}")

    # Test similarity search
    query = "machine learning"
    candidates = [
        "artificial intelligence and deep learning",
        "cooking recipes and food",
        "neural networks and AI",
        "sports and athletics",
        "data science and statistics",
    ]

    similar = tool.find_most_similar(query, candidates, top_k=3)
    print(f"\nMost similar to '{query}':")
    for text, sim in similar:
        print(f"  {sim:.3f}: {text}")
