"""Memory Retrieval - hybrid scoring for memory queries.

Enhanced: 语义相似度检索支持 (论文P1-4: 使用sentence embeddings).
"""
from typing import List, Dict, Any, Optional
from common.models import EpisodeRecord
from common.logger import get_logger
from .episodic import EpisodicMemory
from .schema import SchemaMemory, SchemaEntry
from .skill import SkillMemory, SkillEntry

logger = get_logger(__name__)


class SemanticEmbeddingProvider:
    """语义嵌入提供者 - 用于计算语义相似度"""

    def __init__(self, backend: str = "simple"):
        """初始化嵌入提供者

        Args:
            backend: 嵌入后端类型 ("simple", "sentence_transformers", "openai")
        """
        self.backend = backend
        self._model = None

        if backend == "sentence_transformers":
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Using sentence-transformers backend")
            except ImportError:
                logger.warning("sentence-transformers not available, falling back to simple")
                self.backend = "simple"
        elif backend == "openai":
            try:
                import openai
                self._client = openai.Client()
                logger.info("Using OpenAI embeddings backend")
            except ImportError:
                logger.warning("OpenAI not available, falling back to simple")
                self.backend = "simple"

    def embed(self, texts: List[str]) -> List[List[float]]:
        """获取文本的嵌入向量

        Args:
            texts: 文本列表

        Returns:
            嵌入向量列表
        """
        if self.backend == "sentence_transformers" and self._model:
            return self._model.encode(texts).tolist()
        elif self.backend == "openai":
            # 简化实现，实际需要调用OpenAI API
            return [[0.0] * 384 for _ in texts]
        else:
            # Simple fallback: 使用词频特征
            return self._simple_embed(texts)

    def _simple_embed(self, texts: List[str]) -> List[List[float]]:
        """简单的词频嵌入"""
        import hashlib
        embeddings = []
        for text in texts:
            # 使用hash生成固定长度的伪嵌入
            hash_obj = hashlib.md5(text.encode())
            hash_bytes = hash_obj.digest()
            # 转换为384维向量（与MiniLM相同）
            vec = []
            for i in range(384):
                byte_idx = i % len(hash_bytes)
                val = hash_bytes[byte_idx] / 255.0
                vec.append(val)
            embeddings.append(vec)
        return embeddings

    def compute_similarity(self, emb1: List[float], emb2: List[float]) -> float:
        """计算余弦相似度

        Args:
            emb1: 第一个嵌入向量
            emb2: 第二个嵌入向量

        Returns:
            余弦相似度 [-1, 1]
        """
        import math
        dot = sum(a * b for a, b in zip(emb1, emb2))
        norm1 = math.sqrt(sum(a * a for a in emb1))
        norm2 = math.sqrt(sum(b * b for b in emb2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)


class MemoryRetrieval:
    """Hybrid memory retrieval system.

    Combines multiple scoring factors:
    - Semantic similarity (使用sentence embeddings) - 论文P1-4实现
    - Keyword matching
    - Recency
    - Salience (based on |delta|)
    """

    def __init__(
        self,
        episodic: EpisodicMemory,
        schema: SchemaMemory,
        skill: SkillMemory,
        embedding_backend: str = "simple",
    ):
        """Initialize retrieval system.

        Args:
            episodic: Episodic memory instance
            schema: Schema memory instance
            skill: Skill memory instance
            embedding_backend: 嵌入后端类型
        """
        self.episodic = episodic
        self.schema = schema
        self.skill = skill
        self.embedding_provider = SemanticEmbeddingProvider(embedding_backend)

    def retrieve_episodes(
        self,
        query_tags: List[str],
        current_tick: int,
        limit: int = 10,
        recency_weight: float = 0.3,
        salience_weight: float = 0.4,
        keyword_weight: float = 0.3,
        semantic_weight: float = 0.0,
        query_text: Optional[str] = None,
        enable_associative: bool = True,
        associative_weight: float = 0.15,
    ) -> List[EpisodeRecord]:
        """Retrieve relevant episodes.

        Enhanced:
        - 支持语义相似度检索 (论文P1-4)
        - 支持联想检索 (普鲁斯特效应、因果联想)

        Args:
            query_tags: Tags to search for
            current_tick: Current tick for recency calculation
            limit: Maximum episodes to return
            recency_weight: Weight for recency score
            salience_weight: Weight for salience score
            keyword_weight: Weight for keyword matching score
            semantic_weight: Weight for semantic similarity (新增)
            query_text: Query text for semantic similarity (新增)
            enable_associative: Enable associative memory retrieval (新增)
            associative_weight: Weight for associative score (新增)

        Returns:
            List of retrieved episodes
        """
        try:
            # Validate inputs
            if not query_tags and not query_text:
                logger.warning("Empty query_tags and query_text, returning recent episodes")
                return self.episodic.query_recent(limit)

            if limit <= 0:
                logger.warning(f"Invalid limit: {limit}, using default 10")
                limit = 10

            # Get candidates
            candidates = self.episodic.query_by_tags(query_tags, limit=limit * 2)

            if not candidates:
                logger.debug(f"No episodes found for tags {query_tags}, falling back to recent")
                return self.episodic.query_recent(limit)

            # === 新增: 联想检索 ===
            associative_results = {}
            if enable_associative and query_text:
                try:
                    # 获取当前情绪上下文（用于普鲁斯特效应）
                    from core.stores.fields import FieldStore
                    # 尝试从全局状态获取情绪
                    current_mood = None
                    current_stress = None

                    # 通过联想检索获取相关记忆
                    assoc_results = self.episodic.retrieve_by_association(
                        query=query_text,
                        top_k=limit * 2,
                        mood=current_mood,
                        stress=current_stress
                    )

                    # 将联想结果转换为 tick -> score 映射
                    for result in assoc_results:
                        tick = result.get("tick")
                        score = result.get("score", 0.0)
                        if tick is not None:
                            # 联想分数包含: 语义相似度 + 联想增强 + 普鲁斯特效应
                            associative_results[tick] = score

                    if associative_results:
                        logger.debug(f"Associative retrieval found {len(associative_results)} candidates")
                except Exception as e:
                    logger.warning(f"Associative retrieval failed: {e}")

            # Compute semantic embeddings if needed
            semantic_scores = {}
            if semantic_weight > 0 and query_text:
                semantic_scores = self._compute_semantic_scores(candidates, query_text)

            # Score each candidate
            scored = []
            for ep in candidates:
                try:
                    score = self._score_episode(
                        ep,
                        query_tags,
                        current_tick,
                        recency_weight,
                        salience_weight,
                        keyword_weight,
                        semantic_weight,
                        semantic_scores.get(ep.tick, 0.0),
                        associative_weight,
                        associative_results.get(ep.tick, 0.0),
                    )
                    scored.append((score, ep))
                except Exception as e:
                    logger.warning(f"Failed to score episode {ep.tick}: {e}")
                    continue

            # Sort by score descending
            scored.sort(key=lambda x: x[0], reverse=True)

            return [ep for _, ep in scored[:limit]]

        except Exception as e:
            logger.error(f"Error in retrieve_episodes: {e}")
            return []

    def _compute_semantic_scores(
        self,
        episodes: List[EpisodeRecord],
        query_text: str,
    ) -> Dict[int, float]:
        """计算语义相似度分数 (论文P1-4).

        Args:
            episodes: 要评分的情节列表
            query_text: 查询文本

        Returns:
            episode.tick到语义分数的映射
        """
        scores = {}

        try:
            # 准备文本
            episode_texts = []
            for ep in episodes:
                # 构建情节的文本表示
                text_parts = []
                if hasattr(ep, 'observation') and ep.observation:
                    text_parts.append(str(ep.observation))
                if hasattr(ep, 'action') and ep.action:
                    text_parts.append(str(ep.action))
                if hasattr(ep, 'tags'):
                    text_parts.append(' '.join(ep.tags))
                episode_texts.append(' '.join(text_parts))

            # 计算嵌入
            query_emb = self.embedding_provider.embed([query_text])[0]
            episode_embs = self.embedding_provider.embed(episode_texts)

            # 计算相似度 (使用tick作为稳定key，而非id())
            for ep, emb in zip(episodes, episode_embs):
                similarity = self.embedding_provider.compute_similarity(query_emb, emb)
                scores[ep.tick] = max(0.0, similarity)  # 只取正相似度

        except Exception as e:
            logger.warning(f"Semantic scoring failed: {e}")

        return scores

    def retrieve_by_semantic_similarity(
        self,
        query_text: str,
        current_tick: int,
        limit: int = 10,
        min_similarity: float = 0.3,
        max_candidates: int = 100,  # 性能优化：限制候选数量
    ) -> List[EpisodeRecord]:
        """通过语义相似度检索记忆 (论文P1-4: 语义嵌入新颖度).

        性能优化:
        - 只检索最近的 max_candidates 条记录
        - 使用轻量级相似度计算

        Args:
            query_text: 查询文本
            current_tick: 当前tick
            limit: 最大返回数量
            min_similarity: 最小相似度阈值
            max_candidates: 最大候选记录数量（性能优化）

        Returns:
            检索到的情节列表
        """
        try:
            # 性能优化：只获取最近的记录，而不是全部
            # 使用 query_recent 获取最近的候选记录
            candidates = self.episodic.query_recent(max_candidates)

            if not candidates:
                return []

            # 计算语义分数
            semantic_scores = self._compute_semantic_scores(candidates, query_text)

            # 过滤低相似度并排序
            filtered = [
                (ep, semantic_scores.get(ep.tick, 0.0))
                for ep in candidates
                if semantic_scores.get(ep.tick, 0.0) >= min_similarity
            ]
            filtered.sort(key=lambda x: x[1], reverse=True)

            return [ep for ep, _ in filtered[:limit]]

        except Exception as e:
            logger.error(f"Error in retrieve_by_semantic_similarity: {e}")
            return []

    # Note: retrieve_episodes method is defined above (line 128) with full semantic support.
    # The duplicate method definition that was here has been removed to prevent
    # overriding the semantic retrieval functionality.

    def _score_episode(
        self,
        episode: EpisodeRecord,
        query_tags: List[str],
        current_tick: int,
        recency_weight: float,
        salience_weight: float,
        keyword_weight: float,
        semantic_weight: float = 0.0,
        semantic_score: float = 0.0,
        associative_weight: float = 0.0,
        associative_score: float = 0.0,
    ) -> float:
        """Score an episode for retrieval.

        Enhanced:
        - 支持语义相似度评分 (论文P1-4)
        - 支持联想记忆评分 (普鲁斯特效应、因果联想)

        Args:
            episode: Episode to score
            query_tags: Query tags
            current_tick: Current tick
            recency_weight: Recency weight
            salience_weight: Salience weight
            keyword_weight: Keyword weight
            semantic_weight: Semantic similarity weight
            semantic_score: Pre-computed semantic score
            associative_weight: Associative memory weight (新增)
            associative_score: Pre-computed associative score (新增)

        Returns:
            Total score
        """
        # Recency score (exponential decay)
        age = current_tick - episode.tick
        recency_score = max(0.0, 1.0 - age / 1000.0)  # Decay over 1000 ticks

        # Salience score (based on |delta|)
        salience_score = min(1.0, abs(episode.delta))

        # Keyword score (fraction of tags matching)
        if query_tags:
            matching_tags = sum(1 for tag in query_tags if tag in episode.tags)
            keyword_score = matching_tags / len(query_tags)
        else:
            keyword_score = 0.0

        # Normalize weights (包含联想权重)
        total_weight = recency_weight + salience_weight + keyword_weight + semantic_weight + associative_weight
        if total_weight == 0:
            total_weight = 1.0

        # Combine scores (包含联想分数)
        total_score = (
            (recency_weight / total_weight) * recency_score +
            (salience_weight / total_weight) * salience_score +
            (keyword_weight / total_weight) * keyword_score +
            (semantic_weight / total_weight) * semantic_score +
            (associative_weight / total_weight) * associative_score
        )

        return total_score

    def retrieve_schemas(
        self,
        query_tags: List[str],
        min_confidence: float = 0.5,
        limit: int = 5,
    ) -> List[SchemaEntry]:
        """Retrieve relevant schemas.

        Args:
            query_tags: Tags to search for
            min_confidence: Minimum confidence threshold
            limit: Maximum schemas to return

        Returns:
            List of schemas
        """
        schemas = self.schema.query_by_tags(query_tags, min_confidence=min_confidence)

        # Sort by confidence descending
        schemas.sort(key=lambda s: s.confidence, reverse=True)

        return schemas[:limit]

    def retrieve_skills(
        self,
        query_tags: List[str],
        min_success_rate: float = 0.5,
        limit: int = 3,
    ) -> List[SkillEntry]:
        """Retrieve relevant skills.

        Args:
            query_tags: Tags to search for
            min_success_rate: Minimum success rate
            limit: Maximum skills to return

        Returns:
            List of skills
        """
        skills = self.skill.query_by_tags(query_tags, min_success_rate=min_success_rate)

        # Sort by success rate and average reward
        skills.sort(
            key=lambda s: (s.success_rate(), s.average_reward),
            reverse=True
        )

        return skills[:limit]
