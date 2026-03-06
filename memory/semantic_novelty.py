"""Semantic embedding-based novelty calculation.

Implements paper Section 3.10.4 requirement for semantic embedding
novelty evaluation instead of lexical overlap (Jaccard similarity).

论文公式:
C_nov = 1 - max_{s in Schema} cos(emb(insight), emb(s))

支持四种模式:
1. SENTENCE_TRANSFORMERS - 本地sentence-transformers模型 (推荐，无外部依赖)
2. API调用模式 - 配置API地址和密钥，通过/model参数选择模型
3. 本地大模型模式 - 直接调用已配置好的本地模型服务
4. TF-IDF回退 - 简单回退，无外部依赖

默认使用TF-IDF回退。安装sentence-transformers后可自动启用语义嵌入。
"""
from typing import List, Dict, Any, Optional, Tuple, Union
from pathlib import Path
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
from threading import Lock
import httpx
import os

from .utils import cosine_similarity as _cosine_similarity_shared

# Import logger for proper logging
try:
    from common.logger import get_logger
    logger = get_logger(__name__)
except Exception:
    # Fallback if logger not available
    import logging
    logger = logging.getLogger(__name__)


class EmbeddingBackend(str, Enum):
    """嵌入后端类型."""
    # 本地模型 - sentence-transformers (推荐，论文符合)
    SENTENCE_TRANSFORMERS = "sentence_transformers"  # 本地sentence-transformers

    # API模式 - 通过API调用获取嵌入
    OPENAI = "openai"           # OpenAI兼容API
    DASHSCOPE = "dashscope"     # 阿里云通义千问API
    QIANWEN = "qianwen"         # 千问API
    CUSTOM_API = "custom_api"   # 自定义API端点

    # 本地模式 - 直接调用本地模型服务
    LOCAL_LLM = "local_llm"     # 本地大模型服务 (如vLLM, Ollama等)
    LOCAL_EMBEDDING = "local_embedding"  # 本地嵌入服务

    # 回退模式 - 不依赖外部服务
    TFIDF = "tfidf"             # 简单的TF-IDF回退（无外部依赖）


@dataclass
class EmbeddingAPIConfig:
    """API调用模式配置.

    通过API调用获取嵌入向量，支持OpenAI兼容的API端点。
    """
    # API端点配置
    api_key: str = ""                    # API密钥
    api_base: str = "https://api.openai.com/v1"  # API基础URL
    model: str = "text-embedding-3-small"  # 模型名称（通过API的/model参数选择）

    # 请求配置
    timeout: int = 30                     # 请求超时时间（秒）
    max_retries: int = 3                  # 最大重试次数
    embedding_dim: int = 1536             # 嵌入向量维度（根据模型配置）

    # 高级配置
    headers: Dict[str, str] = field(default_factory=dict)  # 自定义HTTP头


@dataclass
class SentenceTransformerConfig:
    """sentence-transformers配置.

    使用本地sentence-transformers库生成语义嵌入，完全符合论文Section 3.10.4要求。
    无需外部API调用，模型下载后可离线使用。

    推荐模型:
    - sentence-transformers/all-MiniLM-L6-v2: 快速，384维，~80MB
    - sentence-transformers/all-mpnet-base-v2: 高质量，768维，~400MB
    - sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2: 多语言支持
    """
    # 模型配置
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"  # 模型名称
    device: str = "cpu"  # 运行设备: "cpu" 或 "cuda"

    # 缓存配置
    cache_folder: Optional[Path] = None  # 模型缓存目录

    # 性能配置
    batch_size: int = 32  # 批处理大小
    show_progress: bool = False  # 是否显示下载进度


@dataclass
class LocalLLMConfig:
    """本地大模型配置.

    直接调用已配置好的本地模型服务（如vLLM、Ollama等）。
    """
    # 本地服务端点
    base_url: str = "http://localhost:11434"  # 本地服务地址（如Ollama默认端口）
    model: str = "nomic-embed-text"                 # 本地模型名称

    # 请求配置
    timeout: int = 60                              # 本地模型可能需要更长超时
    embedding_dim: int = 768                       # 嵌入向量维度（根据模型配置）

    # Ollama特定配置
    ollama_host: Optional[str] = None              # Ollama服务地址（兼容性）


@dataclass
class EmbeddingConfig:
    """嵌入模型配置总入口.

    支持四种模式选择其一：
    1. st_config: sentence-transformers配置（推荐，论文符合）
    2. api_config: API调用模式配置
    3. local_config: 本地大模型模式配置
    如果都不配置，使用TF-IDF回退模式。
    """
    # 后端类型选择
    backend: EmbeddingBackend = EmbeddingBackend.TFIDF

    # sentence-transformers配置（backend为SENTENCE_TRANSFORMERS时使用）
    st_config: Optional[SentenceTransformerConfig] = None

    # API配置（backend为API类型时使用）
    api_config: Optional[EmbeddingAPIConfig] = None

    # 本地模型配置（backend为LOCAL类型时使用）
    local_config: Optional[LocalLLMConfig] = None

    # 缓存配置
    cache_embeddings: bool = True                # 是否缓存嵌入向量
    cache_dir: Optional[Path] = None              # 持久化缓存目录
    max_cache_size: int = 10000                   # 最大缓存数量

    @classmethod
    def from_env(cls) -> 'EmbeddingConfig':
        """从环境变量创建配置.

        支持的环境变量:
        - EMBEDDING_BACKEND: 后端类型 (sentence_transformers/api/local/tfidf)
        - OPENAI_API_KEY: OpenAI API密钥
        - OPENAI_API_BASE: OpenAI API基础URL
        - EMBEDDING_MODEL: 模型名称
        - LOCAL_LLM_URL: 本地模型服务URL
        """
        backend_str = os.environ.get("EMBEDDING_BACKEND", "tfidf")
        try:
            backend = EmbeddingBackend(backend_str)
        except ValueError:
            logger.warning(f"Unknown backend: {backend_str}, using tfidf fallback")
            backend = EmbeddingBackend.TFIDF

        config = cls(backend=backend)

        # sentence-transformers配置
        if backend == EmbeddingBackend.SENTENCE_TRANSFORMERS:
            model_name = os.environ.get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
            device = os.environ.get("EMBEDDING_DEVICE", "cpu")

            config.st_config = SentenceTransformerConfig(
                model_name=model_name,
                device=device
            )

        # API配置
        elif backend in [EmbeddingBackend.OPENAI, EmbeddingBackend.DASHSCOPE,
                       EmbeddingBackend.QIANWEN, EmbeddingBackend.CUSTOM_API]:
            api_key = os.environ.get("OPENAI_API_KEY", "")
            api_base = os.environ.get("OPENAI_API_BASE",
                                         "https://api.openai.com/v1")
            model = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")

            config.api_config = EmbeddingAPIConfig(
                api_key=api_key,
                api_base=api_base,
                model=model
            )

        # 本地模型配置
        elif backend in [EmbeddingBackend.LOCAL_LLM, EmbeddingBackend.LOCAL_EMBEDDING]:
            local_url = os.environ.get("LOCAL_LLM_URL", "http://localhost:11434")
            model = os.environ.get("EMBEDDING_MODEL", "nomic-embed-text")

            config.local_config = LocalLLMConfig(
                base_url=local_url,
                model=model
            )

        return config

    @classmethod
    def for_openai(cls, api_key: str, model: str = "text-embedding-3-small",
                   api_base: str = "https://api.openai.com/v1") -> 'EmbeddingConfig':
        """创建OpenAI API配置."""
        config = cls(backend=EmbeddingBackend.OPENAI)
        config.api_config = EmbeddingAPIConfig(
            api_key=api_key,
            api_base=api_base,
            model=model
        )
        return config

    @classmethod
    def for_local(cls, base_url: str, model: str = "nomic-embed-text") -> 'EmbeddingConfig':
        """创建本地模型配置."""
        config = cls(backend=EmbeddingBackend.LOCAL_LLM)
        config.local_config = LocalLLMConfig(
            base_url=base_url,
            model=model
        )
        return config

    @classmethod
    def for_tfidf(cls) -> 'EmbeddingConfig':
        """创建TF-IDF回退配置（无外部依赖）."""
        return cls(backend=EmbeddingBackend.TFIDF)

    @classmethod
    def for_sentence_transformers(
        cls,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        device: str = "cpu"
    ) -> 'EmbeddingConfig':
        """创建sentence-transformers配置（推荐，论文符合）.

        Args:
            model_name: 模型名称，默认为all-MiniLM-L6-v2（快速，384维）
            device: 运行设备，"cpu" 或 "cuda"

        Returns:
            EmbeddingConfig实例
        """
        config = cls(backend=EmbeddingBackend.SENTENCE_TRANSFORMERS)
        config.st_config = SentenceTransformerConfig(
            model_name=model_name,
            device=device
        )
        return config

    def auto_detect_backend(cls) -> 'EmbeddingConfig':
        """自动检测最佳后端.

        优先级:
        1. sentence-transformers (如果已安装)
        2. TF-IDF回退

        Returns:
            自动检测的配置
        """
        # 尝试导入sentence-transformers
        try:
            import sentence_transformers
            logger.info("sentence-transformers detected, using for semantic embeddings")
            return cls.for_sentence_transformers()
        except ImportError:
            logger.info("sentence-transformers not available, using TF-IDF fallback")
            return cls.for_tfidf()


class SemanticNoveltyCalculator:
    """Calculate novelty using semantic embeddings.

    论文Section 3.10.4要求:
    "新颖性评估应使用语义嵌入（sentence embeddings）而非词汇重叠"

    支持四种模式:
    1. sentence-transformers - 本地语义嵌入（推荐，论文符合）
    2. API模式 - 调用OpenAI兼容API获取嵌入
    3. 本地模型模式 - 调用本地LLM服务
    4. TF-IDF模式 - 简单回退，无外部依赖

    Examples:
        # 使用sentence-transformers（推荐）
        config = EmbeddingConfig.for_sentence_transformers()
        calc = SemanticNoveltyCalculator(config)

        # 使用OpenAI API
        config = EmbeddingConfig.for_openai(api_key="sk-xxx")
        calc = SemanticNoveltyCalculator(config)

        # 使用本地Ollama
        config = EmbeddingConfig.for_local("http://localhost:11434")
        calc = SemanticNoveltyCalculator(config)

        # 使用TF-IDF回退
        config = EmbeddingConfig.for_tfidf()
        calc = SemanticNoveltyCalculator(config)
    """

    def __init__(
        self,
        config: Optional[EmbeddingConfig] = None,
        cache_dir: Optional[Path] = None,
    ):
        """Initialize novelty calculator.

        Args:
            config: 嵌入配置，如果为None则从环境变量加载
            cache_dir: 持久化缓存目录
        """
        self.config = config or EmbeddingConfig.from_env()
        self._cache: Dict[str, np.ndarray] = {} if self.config.cache_embeddings else None
        self._cache_lock = Lock()

        # 持久化缓存
        self._cache_dir = cache_dir or self.config.cache_dir
        self._disk_cache_index: Dict[str, str] = {}
        if self._cache_dir:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            self._load_disk_cache_index()

        # sentence-transformers模型（延迟加载）
        self._st_model = None

        # HTTP客户端（API模式使用）
        self._http_client: Optional[httpx.Client] = None
        if self.config.backend in EmbeddingBackend.__members__.values():
            if self.config.backend.value.endswith("api") or "API" in self.config.backend.value:
                self._http_client = httpx.Client(timeout=30)

    def _get_embedding_dim(self) -> int:
        """获取当前配置的嵌入维度."""
        if self.config.backend == EmbeddingBackend.TFIDF:
            return 384  # TF-IDF默认维度
        elif self.config.backend == EmbeddingBackend.SENTENCE_TRANSFORMERS:
            # sentence-transformers维度由模型决定
            if self._st_model is not None:
                return self._st_model.get_sentence_embedding_dimension()
            # all-MiniLM-L6-v2 默认384维
            return 384
        elif self.config.api_config:
            return self.config.api_config.embedding_dim
        elif self.config.local_config:
            return self.config.local_config.embedding_dim
        return 384

    def _get_st_model(self):
        """获取sentence-transformers模型（延迟加载）."""
        if self._st_model is not None:
            return self._st_model

        if self.config.backend != EmbeddingBackend.SENTENCE_TRANSFORMERS:
            return None

        try:
            from sentence_transformers import SentenceTransformer
            st_config = self.config.st_config

            logger.info(f"Loading sentence-transformers model: {st_config.model_name}")
            self._st_model = SentenceTransformer(
                st_config.model_name,
                device=st_config.device,
                cache_folder=str(st_config.cache_folder) if st_config.cache_folder else None
            )
            logger.info(f"Model loaded, embedding dimension: {self._st_model.get_sentence_embedding_dimension()}")
            return self._st_model

        except ImportError:
            logger.warning("sentence-transformers not installed, falling back to TF-IDF")
            logger.info("Install with: pip install sentence-transformers")
            return None
        except Exception as e:
            logger.warning(f"Failed to load sentence-transformers model: {e}")
            return None

    def _compute_embedding_sentence_transformers(self, text: str) -> np.ndarray:
        """使用sentence-transformers计算嵌入向量.

        Args:
            text: 输入文本

        Returns:
            嵌入向量
        """
        model = self._get_st_model()
        if model is None:
            # 回退到TF-IDF
            return self._compute_embedding_tfidf(text)

        st_config = self.config.st_config

        # 生成嵌入
        embedding = model.encode(
            text,
            convert_to_numpy=True,
            show_progress_bar=st_config.show_progress
        )

        return embedding

    def _compute_embedding_api(self, text: str) -> np.ndarray:
        """通过API计算嵌入向量.

        Args:
            text: 输入文本

        Returns:
            嵌入向量
        """
        if not self.config.api_config:
            raise ValueError("API config not set")

        api_cfg = self.config.api_config
        headers = {
            "Authorization": f"Bearer {api_cfg.api_key}",
            "Content-Type": "application/json"
        }
        headers.update(api_cfg.headers)

        # 调用嵌入API
        # 标准OpenAI格式: POST /v1/embeddings
        url = f"{api_cfg.api_base.rstrip('/')}/embeddings"

        payload = {
            "model": api_cfg.model,
            "input": text
        }

        if self._http_client is None:
            self._http_client = httpx.Client(timeout=api_cfg.timeout)

        response = self._http_client.post(url, json=payload, headers=headers)
        response.raise_for_status()

        result = response.json()
        # OpenAI格式: {"data": [{"embedding": [...]}, ...]}
        embedding = result["data"][0]["embedding"]

        return np.array(embedding)

    def _compute_embedding_local(self, text: str) -> np.ndarray:
        """通过本地模型服务计算嵌入向量.

        Args:
            text: 输入文本

        Returns:
            嵌入向量
        """
        if not self.config.local_config:
            raise ValueError("Local LLM config not set")

        local_cfg = self.config.local_config

        # 调用本地嵌入服务
        # Ollama兼容格式: POST /api/embed
        url = f"{local_cfg.base_url.rstrip('/')}/api/embed"

        payload = {
            "model": local_cfg.model,
            "input": text
        }

        if self._http_client is None:
            self._http_client = httpx.Client(timeout=local_cfg.timeout)

        response = self._http_client.post(url, json=payload)
        response.raise_for_status()

        result = response.json()
        # Ollama格式: {"embedding": [...]}
        embedding = result.get("embedding", result.get("embeddings", [])[0])

        return np.array(embedding)

    def _compute_embedding_tfidf(self, text: str, dim: int = 384) -> np.ndarray:
        """TF-IDF回退嵌入（无外部依赖）.

        Args:
            text: 输入文本
            dim: 嵌入维度

        Returns:
            嵌入向量
        """
        # 标准化文本
        text = text.lower().strip()

        # 基于字符三元组的简单嵌入
        embedding = np.zeros(dim)
        if text:
            for i, char in enumerate(text):
                # 字符哈希
                idx = (ord(char) * (i + 1) * 17) % dim
                embedding[idx] += 1.0

        # 归一化
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding

    def compute_embedding(self, text: str) -> np.ndarray:
        """计算文本的嵌入向量.

        Args:
            text: 输入文本

        Returns:
            嵌入向量
        """
        # 检查内存缓存
        cache_key = hashlib.md5(text.encode()).hexdigest()
        if self._cache is not None and cache_key in self._cache:
            return self._cache[cache_key].copy()

        # 计算嵌入
        if self.config.backend == EmbeddingBackend.SENTENCE_TRANSFORMERS:
            embedding = self._compute_embedding_sentence_transformers(text)
        elif self.config.backend == EmbeddingBackend.TFIDF:
            embedding = self._compute_embedding_tfidf(text, self._get_embedding_dim())
        elif self.config.backend.value.endswith("api") or self.config.backend in (
            EmbeddingBackend.OPENAI, EmbeddingBackend.DASHSCOPE,
            EmbeddingBackend.QIANWEN, EmbeddingBackend.CUSTOM_API,
        ):
            # API模式
            embedding = self._compute_embedding_api(text)
        elif "local" in self.config.backend.value:
            # 本地模型模式
            embedding = self._compute_embedding_local(text)
        else:
            # 回退到TF-IDF
            embedding = self._compute_embedding_tfidf(text, self._get_embedding_dim())

        # 缓存 (修复 M27: 强制缓存大小限制，防止无限增长)
        if self._cache is not None:
            if len(self._cache) >= self.config.max_cache_size:
                # 淘汰最旧的条目 (FIFO, dict保序自Python 3.7)
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
            self._cache[cache_key] = embedding.copy()

        return embedding

    def cosine_similarity(
        self,
        emb1: np.ndarray,
        emb2: np.ndarray,
    ) -> float:
        """计算余弦相似度.

        Args:
            emb1: 嵌入向量1
            emb2: 嵌入向量2

        Returns:
            相似度 [0, 1]
        """
        return _cosine_similarity_shared(emb1, emb2)

    def compute_novelty(
        self,
        insight_text: str,
        existing_texts: List[str],
        threshold: float = 0.85,
    ) -> Tuple[float, bool]:
        """计算洞察的新颖度.

        论文公式 (Section 3.10.4):
            C_nov = 1 - max_{s in Schema} cos(emb(insight), emb(s))

        Args:
            insight_text: 新洞察文本
            existing_texts: 现有文本列表
            threshold: 新颖度阈值

        Returns:
            (novelty_score, is_novel) 元组
        """
        if not existing_texts:
            return 1.0, True

        # 计算洞察嵌入
        insight_emb = self.compute_embedding(insight_text)

        # 找到最大相似度
        max_similarity = 0.0
        for existing_text in existing_texts:
            existing_emb = self.compute_embedding(existing_text)
            sim = self.cosine_similarity(insight_emb, existing_emb)
            max_similarity = max(max_similarity, sim)

        # 新颖度 = 1 - 最大相似度
        novelty = 1.0 - max_similarity
        is_novel = novelty >= threshold

        return novelty, is_novel

    def compute_novelty_batch(
        self,
        insight_texts: List[str],
        existing_texts: List[str],
        threshold: float = 0.85,
    ) -> List[Tuple[float, bool]]:
        """批量计算新颖度.

        Args:
            insight_texts: 新洞察文本列表
            existing_texts: 现有文本列表
            threshold: 新颖度阈值

        Returns:
            [(novelty, is_novel), ...] 列表
        """
        results = []

        # 预计算现有文本的嵌入
        existing_embeddings = []
        for text in existing_texts:
            try:
                existing_embeddings.append(self.compute_embedding(text))
            except Exception as e:
                logger.warning(f"Failed to compute embedding for existing text: {e}")
                existing_embeddings.append(None)

        # 计算每个洞察的新颖度
        for insight_text in insight_texts:
            if not existing_texts or all(emb is None for emb in existing_embeddings):
                results.append((1.0, True))
                continue

            try:
                insight_emb = self.compute_embedding(insight_text)

                # 找最大相似度
                max_similarity = 0.0
                for existing_emb in existing_embeddings:
                    if existing_emb is not None:
                        sim = self.cosine_similarity(insight_emb, existing_emb)
                        max_similarity = max(max_similarity, sim)

                novelty = 1.0 - max_similarity
                is_novel = novelty >= threshold
                results.append((novelty, is_novel))

            except Exception as e:
                logger.warning(f"Failed to compute novelty for insight: {e}")
                results.append((0.5, False))  # 保守估计

        return results

    def _load_disk_cache_index(self) -> None:
        """加载磁盘缓存索引."""
        if self._cache_dir is None:
            return

        index_path = self._cache_dir / "cache_index.json"
        if index_path.exists():
            try:
                with open(index_path, 'r', encoding='utf-8') as f:
                    self._disk_cache_index = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load disk cache index: {e}")
                self._disk_cache_index = {}

    def _save_to_disk_cache(self, text: str, embedding: np.ndarray) -> None:
        """保存到磁盘缓存."""
        if self._cache_dir is None:
            return

        cache_key = hashlib.md5(text.encode()).hexdigest()
        cache_path = self._cache_dir / f"{cache_key}.npy"

        try:
            np.save(cache_path, embedding)
            self._disk_cache_index[cache_key] = str(cache_path)

            # 保存索引
            index_path = self._cache_dir / "cache_index.json"
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(self._disk_cache_index, f)
        except Exception as e:
            logger.warning(f"Failed to save to disk cache: {e}")

    def _load_from_disk_cache(self, text: str) -> Optional[np.ndarray]:
        """从磁盘缓存加载."""
        if self._cache_dir is None:
            return None

        cache_key = hashlib.md5(text.encode()).hexdigest()
        if cache_key not in self._disk_cache_index:
            return None

        cache_path = self._disk_cache_index[cache_key]
        if not Path(cache_path).exists():
            return None

        try:
            return np.load(cache_path)
        except Exception as e:
            logger.warning(f"Failed to load from disk cache: {e}")
            return None

    def clear_cache(self) -> None:
        """清空所有缓存."""
        if self._cache is not None:
            self._cache.clear()
        self._disk_cache_index.clear()

    def close(self) -> None:
        """关闭资源."""
        if self._http_client is not None:
            self._http_client.close()
            self._http_client = None


# 便利函数
def get_default_calculator() -> SemanticNoveltyCalculator:
    """获取默认的新颖度计算器（从环境变量配置）."""
    return SemanticNoveltyCalculator()


def compute_novelty(
    insight: str,
    existing: List[str],
    threshold: float = 0.85,
    config: Optional[EmbeddingConfig] = None,
) -> Tuple[float, bool]:
    """便利函数：计算新颖度.

    Args:
        insight: 新洞察文本
        existing: 现有文本列表
        threshold: 新颖度阈值
        config: 可选配置

    Returns:
        (novelty_score, is_novel) 元组
    """
    calc = SemanticNoveltyCalculator(config)
    return calc.compute_novelty(insight, existing, threshold)


# 兼容旧代码的别名
SemanticNoveltyModel = EmbeddingConfig  # 向后兼容
LocalLLMConfig_old = LocalLLMConfig  # 向后兼容
