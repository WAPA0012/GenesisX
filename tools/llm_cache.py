"""LLM Response Cache - LLM响应缓存

通过缓存相似查询的响应来减少 API 调用次数和延迟。

缓存策略:
1. 精确匹配缓存 - 对于完全相同的消息直接返回缓存响应
2. 语义相似缓存 - 对于语义相似的消息（可选）
3. TTL过期 - 缓存条目有时间限制
4. LRU淘汰 - 最近最少使用的条目被淘汰
"""

import hashlib
import time
import threading
from typing import Dict, Any, Optional, List, Tuple
from collections import OrderedDict
from dataclasses import dataclass, field
import json


@dataclass
class CacheEntry:
    """缓存条目"""
    response: str
    created_at: float
    last_accessed: float
    hit_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class LLMCache:
    """LLM 响应缓存

    使用 LRU (Least Recently Used) 策略管理缓存。

    Example:
        cache = LLMCache(max_size=100, ttl_seconds=3600)

        # 生成缓存键
        key = cache.generate_key(messages, system_prompt)

        # 尝试获取缓存
        cached = cache.get(key)
        if cached:
            return cached

        # 调用 LLM 并缓存结果
        response = llm.chat(messages, system_prompt)
        cache.set(key, response)
    """

    def __init__(
        self,
        max_size: int = 100,
        ttl_seconds: float = 3600,  # 1小时
        enabled: bool = True
    ):
        """初始化缓存

        Args:
            max_size: 最大缓存条目数
            ttl_seconds: 缓存有效期（秒）
            enabled: 是否启用缓存
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.enabled = enabled
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()

        # 统计信息
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "total_requests": 0
        }

    def generate_key(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """生成缓存键

        基于消息内容和关键参数生成唯一的缓存键。

        Args:
            messages: 消息列表
            system_prompt: 系统提示词
            **kwargs: 其他影响响应的参数（如 temperature, tools）

        Returns:
            缓存键字符串
        """
        # 提取影响响应的关键参数
        key_data = {
            "messages": messages,
            "system_prompt": system_prompt,
        }

        # 只包含影响响应一致性的参数
        # 注意：temperature 影响随机性，所以不包含在键中
        if "tools" in kwargs:
            # 工具定义简化，只使用函数名
            tools = kwargs.get("tools", [])
            if tools:
                key_data["tools"] = [
                    t.get("function", {}).get("name", "")
                    for t in tools
                ]

        # 生成哈希键
        key_str = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(key_str.encode('utf-8')).hexdigest()[:16]

    def get(self, key: str) -> Optional[str]:
        """获取缓存的响应

        Args:
            key: 缓存键

        Returns:
            缓存的响应，如果不存在或已过期返回 None
        """
        if not self.enabled:
            return None

        with self._lock:
            self.stats["total_requests"] += 1

            if key not in self._cache:
                self.stats["misses"] += 1
                return None

            entry = self._cache[key]

            # 检查 TTL
            if time.time() - entry.created_at > self.ttl_seconds:
                del self._cache[key]
                self.stats["misses"] += 1
                self.stats["evictions"] += 1
                return None

            # 更新访问信息
            entry.last_accessed = time.time()
            entry.hit_count += 1

            # 移动到末尾（LRU）
            self._cache.move_to_end(key)

            self.stats["hits"] += 1
            return entry.response

    def set(
        self,
        key: str,
        response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """设置缓存

        Args:
            key: 缓存键
            response: 响应内容
            metadata: 可选的元数据
        """
        if not self.enabled:
            return

        with self._lock:
            now = time.time()

            # 如果键已存在，更新
            if key in self._cache:
                entry = self._cache[key]
                entry.response = response
                entry.created_at = now
                entry.last_accessed = now
                entry.metadata = metadata or {}
                self._cache.move_to_end(key)
                return

            # 检查容量，必要时淘汰
            while len(self._cache) >= self.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self.stats["evictions"] += 1

            # 添加新条目
            self._cache[key] = CacheEntry(
                response=response,
                created_at=now,
                last_accessed=now,
                hit_count=0,
                metadata=metadata or {}
            )

    def invalidate(self, key: str) -> bool:
        """使指定缓存失效

        Args:
            key: 缓存键

        Returns:
            是否成功删除
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> int:
        """清空所有缓存

        Returns:
            清除的条目数
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息

        Returns:
            统计信息字典
        """
        with self._lock:
            total = self.stats["total_requests"]
            hits = self.stats["hits"]
            hit_rate = hits / total if total > 0 else 0.0

            return {
                "enabled": self.enabled,
                "size": len(self._cache),
                "max_size": self.max_size,
                "ttl_seconds": self.ttl_seconds,
                "hits": hits,
                "misses": self.stats["misses"],
                "evictions": self.stats["evictions"],
                "total_requests": total,
                "hit_rate": hit_rate
            }

    def prune_expired(self) -> int:
        """清理过期条目

        Returns:
            清理的条目数
        """
        with self._lock:
            now = time.time()
            expired_keys = [
                k for k, v in self._cache.items()
                if now - v.created_at > self.ttl_seconds
            ]
            for key in expired_keys:
                del self._cache[key]
                self.stats["evictions"] += 1
            return len(expired_keys)


# ============================================================================
# 全局缓存实例
# ============================================================================

_global_cache: Optional[LLMCache] = None
_cache_lock = threading.Lock()


def get_llm_cache() -> LLMCache:
    """获取全局 LLM 缓存实例"""
    global _global_cache
    with _cache_lock:
        if _global_cache is None:
            _global_cache = LLMCache(
                max_size=100,
                ttl_seconds=1800,  # 30分钟
                enabled=True
            )
        return _global_cache


def clear_llm_cache() -> int:
    """清空全局缓存

    Returns:
        清除的条目数
    """
    cache = get_llm_cache()
    return cache.clear()
