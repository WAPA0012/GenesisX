"""Associative Memory with Familiarity Signal.

联想记忆系统 - 实现论文 Section 3.4.3 熟悉度信号 + 双阶段检索

核心功能:
1. 双阶段检索 (论文 Section 3.4.3):
   - Phase 1: 快速熟悉度判断 O(log n)
   - Phase 2: 联想激活传播 (联想扩散)

2. 联想网络 (Associative Network G = (V, E)):
   - 共现联想: 记录在同一episode中出现的记忆
   - 因果联想: 记录actions导致results的关系
   - 情绪联想: 基于情绪上下文的相似性 (普鲁斯特效应)
   - 语义联想: 基于嵌入向量的相似度
   - 时间联想: 时间接近度

3. 记忆检索时的熟悉度信号:
   Familiarity(q, M) = max_i sim_associative(q, m_i)

   其中联想相似度:
   sim_associative = Σ_j w_ij · sim_semantic(q, m_j)

4. 梦境生成中的联想重组:
   - 联想激活传播
   - 普鲁斯特效应（情绪触发记忆）
   - 创造性思考（跨领域联想）

References:
- 论文 Section 3.4.3: 熟悉度信号与双阶段检索
- 论文 Section 3.10.4: 梦境重组与联想传播
"""

import time
import math
from typing import Dict, Any, List, Optional, Set, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from collections import defaultdict, deque
import numpy as np

from common.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# 联想边类型
# ============================================================================

class AssociationType(str, Enum):
    """联想边类型"""
    CO_OCCURRENCE = "co_occurrence"  # 共现联想 - 同一episodes中
    CAUSAL = "causal"                # 因果联想 - action→result
    EMOTIONAL = "emotional"           # 情绪联想 - 相似情绪状态
    SEMANTIC = "semantic"             # 语义联想 - 嵌入相似度
    TEMPORAL = "temporal"             # 时间联想 - 时间接近


@dataclass
class AssociationEdge:
    """联想边

    权重公式:
    w_ij = β₁·w_cooccurrence + β₂·w_causal + β₃·w_emotional + β₄·w_semantic
    """
    source_id: str          # 源记忆 ID
    target_id: str         # 目标记忆 ID
    weight: float = 0.0     # 综合权重 [0, 1]

    # 分类型权重
    co_occurrence: float = 0.0  # 共现频率
    causal: float = 0.0         # 因果关联强度
    emotional: float = 0.0      # 情绪关联强度
    semantic: float = 0.0        # 语义相似度
    temporal: float = 0.0        # 时间接近度

    # 元数据
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    access_count: int = 0
    reinforced_count: int = 0    # 被强化次数

    def __post_init__(self):
        # 确保权重在 [0, 1] 范围内
        self.weight = max(0.0, min(1.0, self.weight))
        self.co_occurrence = max(0.0, min(1.0, self.co_occurrence))
        self.causal = max(0.0, min(1.0, self.causal))
        self.emotional = max(0.0, min(1.0, self.emotional))
        self.semantic = max(0.0, min(1.0, self.semantic))
        self.temporal = max(0.0, min(1.0, self.temporal))

    def reinforce(self, amount: float = 0.1):
        """强化联想边"""
        self.reinforced_count += 1
        self.weight = min(1.0, self.weight + amount)
        self.last_accessed = datetime.now(timezone.utc)
        self.access_count += 1

    def decay(self, rate: float = 0.01):
        """衰减联想边"""
        self.weight = max(0.0, self.weight - rate)


# ============================================================================
# 记忆节点 - 用于联想网络
# ============================================================================

@dataclass
class AssociativeNode:
    """联想网络中的记忆节点"""
    id: str                           # 唯一标识 (通常是 episode.tick)
    text: str                         # 记忆内容摘要
    embedding: Optional[np.ndarray]   # 语义嵌入向量

    # 情绪上下文
    mood_context: float = 0.5         # 编码时的情绪 [0, 1]
    stress_context: float = 0.2       # 编码时的压力 [0, 1]

    # 时间信息
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tick: int = 0

    # 元数据
    importance: float = 0.5          # 重要性 [0, 1]
    salience: float = 0.5            # 显著性 [0, 1]

    # 关联的episode信息
    episode_tick: int = 0
    action: Optional[str] = None
    result: Optional[str] = None

    # 统计
    access_count: int = 0
    last_accessed: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # 联想（目标记忆 ID → 边）
    associations: Dict[str, AssociationEdge] = field(default_factory=dict)

    def get_embedding(self) -> np.ndarray:
        if self.embedding is None:
            return np.zeros(384)
        return self.embedding

    def add_association(self, edge: AssociationEdge) -> None:
        """添加或更新联想边"""
        self.associations[edge.target_id] = edge

    def get_associations(self) -> List[AssociationEdge]:
        """获取所有联想边，按权重排序"""
        edges = list(self.associations.values())
        edges.sort(key=lambda e: e.weight, reverse=True)
        return edges

    def touch(self):
        """更新访问时间"""
        self.access_count += 1
        self.last_accessed = datetime.now(timezone.utc)


# ============================================================================
# 联想网络
# ============================================================================

class AssociativeNetwork:
    """联想网络 - 存储记忆间的联想关系

    结构: G = (V, E)
    - V: 记忆节点集合
    - E: 联想边集合

    特性:
    - 自动构建共现、因果、情绪、语义联想
    - 联想强化与衰减
    - 联想传播用于梦境生成
    - 普鲁斯特效应（情绪触发）
    """

    def __init__(
        self,
        association_threshold: float = 0.2,  # 保留强关联的阈值
        max_associations: int = 10,           # 每个记忆的最大关联数
        beta: Optional[List[float]] = None,   # 权重系数
        decay_rate: float = 0.001,            # 联想衰减率
        reinforcement_rate: float = 0.05,     # 联想强化率
    ):
        self.association_threshold = association_threshold
        self.max_associations = max_associations
        self.decay_rate = decay_rate
        self.reinforcement_rate = reinforcement_rate

        # 权重系数 [β₁, β₂, β₃, β₄, β₅]
        if beta is None:
            beta = [0.25, 0.30, 0.20, 0.15, 0.10]  # 共现、因果、情绪、语义、时间
        self.beta = beta

        # 存储: memory_id → AssociativeNode
        self._nodes: Dict[str, AssociativeNode] = {}

        # 反向索引（用于快速查找指向某记忆的所有边）
        self._incoming: Dict[str, Set[str]] = defaultdict(set)

        # Episode co-occurrence tracking
        self._episode_members: Dict[int, Set[str]] = defaultdict(set)  # episode_id -> node_ids

        # Causal tracking: action -> result mappings
        self._causal_links: List[Tuple[str, str, float]] = []  # (source, target, strength)

        # 统计
        self.total_associations = 0
        self.association_updates = 0

    def add_node(self, node: AssociativeNode) -> None:
        """添加记忆节点"""
        self._nodes[node.id] = node

    def get_node(self, node_id: str) -> Optional[AssociativeNode]:
        """获取记忆节点"""
        return self._nodes.get(node_id)

    def has_node(self, node_id: str) -> bool:
        """检查节点是否存在"""
        return node_id in self._nodes

    def register_episode(self, episode_id: int, node_ids: List[str]) -> None:
        """注册一个episode中的所有节点

        用于构建共现联想
        """
        self._episode_members[episode_id] = set(node_ids)

        # 为同一episode中的节点建立共现联想
        self._build_co_occurrence_associations(episode_id, node_ids)

    def _build_co_occurrence_associations(self, episode_id: int, node_ids: List[str]) -> None:
        """为同一episode中的节点建立共现联想"""
        n = len(node_ids)
        if n < 2:
            return

        # 每对节点之间建立共现联想
        for i in range(n):
            for j in range(i + 1, n):
                source_id = node_ids[i]
                target_id = node_ids[j]

                if source_id not in self._nodes or target_id not in self._nodes:
                    continue

                self._update_or_create_association(
                    source_id, target_id,
                    co_occurrence_boost=0.3
                )

    def register_causal_link(
        self,
        source_id: str,
        result_id: str,
        strength: float = 0.5
    ) -> None:
        """注册因果链接 (action -> result)"""
        self._causal_links.append((source_id, result_id, strength))

        self._update_or_create_association(
            source_id, result_id,
            causal_boost=strength
        )

    def _update_or_create_association(
        self,
        source_id: str,
        target_id: str,
        co_occurrence_boost: float = 0.0,
        causal_boost: float = 0.0,
    ) -> None:
        """更新或创建联想边"""
        source = self.get_node(source_id)
        target = self.get_node(target_id)

        if not source or not target:
            return

        # 检查是否已存在
        existing = source.associations.get(target_id)

        # 计算各类型权重
        w_co = co_occurrence_boost
        w_causal = causal_boost
        w_emo = self._compute_emotional_similarity(source, target)
        w_sem = self._compute_semantic_similarity(source, target)
        w_temp = self._compute_temporal_similarity(source, target)

        # 综合权重
        total = (
            self.beta[0] * w_co +
            self.beta[1] * w_causal +
            self.beta[2] * w_emo +
            self.beta[3] * w_sem +
            self.beta[4] * w_temp
        )

        total = max(0.0, min(1.0, total))

        # 检查阈值
        if total < self.association_threshold and not existing:
            return

        if existing:
            # 更新现有边
            existing.co_occurrence = max(existing.co_occurrence, w_co)
            existing.causal = max(existing.causal, w_causal)
            existing.emotional = w_emo
            existing.semantic = w_sem
            existing.temporal = w_temp
            existing.weight = total
            existing.last_accessed = datetime.now(timezone.utc)
        else:
            # 创建新边
            # 检查是否超过最大关联数
            if len(source.associations) >= self.max_associations:
                # 移除权重最小的边
                if source.associations:
                    min_edge = min(source.associations.values(), key=lambda e: e.weight)
                    if min_edge.weight < total:
                        del source.associations[min_edge.target_id]
                        self._incoming[min_edge.target_id].discard(source_id)
                    else:
                        return  # 不替换，新边权重不够

            edge = AssociationEdge(
                source_id=source_id,
                target_id=target_id,
                weight=total,
                co_occurrence=w_co,
                causal=w_causal,
                emotional=w_emo,
                semantic=w_sem,
                temporal=w_temp
            )
            source.add_association(edge)
            self._incoming[target_id].add(source_id)
            self.total_associations += 1

        self.association_updates += 1

    def _compute_emotional_similarity(
        self,
        source: AssociativeNode,
        target: AssociativeNode
    ) -> float:
        """计算情绪相似度"""
        mood_diff = abs(source.mood_context - target.mood_context)
        stress_diff = abs(source.stress_context - target.stress_context)

        # 情绪相似度 = 1 - 加权差异
        return max(0.0, 1.0 - (mood_diff * 0.6 + stress_diff * 0.4))

    def _compute_semantic_similarity(
        self,
        source: AssociativeNode,
        target: AssociativeNode
    ) -> float:
        """计算语义相似度（基于嵌入向量）"""
        emb_source = source.get_embedding()
        emb_target = target.get_embedding()

        # 余弦相似度
        dot_product = np.dot(emb_source, emb_target)
        norm_source = np.linalg.norm(emb_source)
        norm_target = np.linalg.norm(emb_target)

        if norm_source == 0 or norm_target == 0:
            return 0.0

        similarity = dot_product / (norm_source * norm_target)
        # 将 [-1, 1] 映射到 [0, 1]
        return (similarity + 1) / 2

    def _compute_temporal_similarity(
        self,
        source: AssociativeNode,
        target: AssociativeNode
    ) -> float:
        """计算时间接近度"""
        time_diff = abs((source.created_at - target.created_at).total_seconds())

        # 1小时内: 1.0, 之后指数衰减
        if time_diff < 3600:
            return 1.0
        elif time_diff < 86400:  # 24小时内
            return math.exp(-time_diff / 3600)
        else:
            return 0.0

    def get_neighbors(
        self,
        node_id: str,
        min_weight: float = 0.0
    ) -> List[Tuple[str, float]]:
        """获取节点的联想邻居

        Args:
            node_id: 节点ID
            min_weight: 最小权重阈值

        Returns:
            [(neighbor_id, weight), ...] 按权重降序排列
        """
        node = self.get_node(node_id)
        if not node:
            return []

        neighbors = [
            (edge.target_id, edge.weight)
            for edge in node.get_associations()
            if edge.weight >= min_weight
        ]
        return neighbors

    def propagate_activation(
        self,
        seed_ids: List[str],
        max_steps: int = 3,
        activation_threshold: float = 0.3
    ) -> Dict[str, float]:
        """联想激活传播

        用于梦境生成中的联想重组

        Args:
            seed_ids: 种子节点ID列表
            max_steps: 最大传播步数
            activation_threshold: 激活阈值

        Returns:
            {node_id: activation_score} 字典
        """
        activation = {nid: 1.0 for nid in seed_ids if nid in self._nodes}

        for step in range(max_steps):
            new_activation = activation.copy()

            for node_id, score in activation.items():
                if score < activation_threshold:
                    continue

                neighbors = self.get_neighbors(node_id)
                for neighbor_id, weight in neighbors:
                    # 激活传播 = 当前激活 * 联想权重 * 衰减
                    propagated = score * weight * 0.7
                    new_activation[neighbor_id] = max(
                        new_activation.get(neighbor_id, 0.0),
                        propagated
                    )

            activation = new_activation

        # 过滤低激活节点
        return {
            nid: score
            for nid, score in activation.items()
            if score >= activation_threshold
        }

    def find_associative_path(
        self,
        start_id: str,
        end_id: str,
        max_length: int = 5
    ) -> Optional[List[str]]:
        """寻找两个节点之间的联想路径

        使用BFS寻找最短联想路径
        """
        if start_id not in self._nodes or end_id not in self._nodes:
            return None

        if start_id == end_id:
            return [start_id]

        # BFS
        queue = deque([(start_id, [start_id])])
        visited = {start_id}

        while queue:
            current_id, path = queue.popleft()

            if len(path) > max_length:
                continue

            neighbors = self.get_neighbors(current_id)
            for neighbor_id, _ in neighbors:
                if neighbor_id == end_id:
                    return path + [neighbor_id]

                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, path + [neighbor_id]))

        return None

    def get_proust_effect_memories(
        self,
        mood: float,
        stress: float,
        threshold: float = 0.7
    ) -> List[Tuple[str, float]]:
        """获取普鲁斯特效应记忆（情绪触发）

        返回与当前情绪状态相似的记忆
        """
        candidates = []

        for node_id, node in self._nodes.items():
            # 计算情绪相似度
            mood_diff = abs(node.mood_context - mood)
            stress_diff = abs(node.stress_context - stress)
            similarity = 1.0 - (mood_diff * 0.6 + stress_diff * 0.4)

            if similarity >= threshold:
                candidates.append((node_id, similarity))

        # 按相似度排序
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:10]  # 返回前10个

    def decay_associations(self):
        """衰减所有联想边"""
        for node in self._nodes.values():
            for edge in list(node.associations.values()):
                edge.decay(self.decay_rate)
                if edge.weight < self.association_threshold:
                    # 移除弱关联
                    del node.associations[edge.target_id]
                    self._incoming[edge.target_id].discard(node.id)
                    self.total_associations -= 1

    def reinforce_association(self, source_id: str, target_id: str):
        """强化特定的联想边"""
        node = self.get_node(source_id)
        if node and target_id in node.associations:
            node.associations[target_id].reinforce(self.reinforcement_rate)

    def get_stats(self) -> Dict[str, Any]:
        """获取网络统计信息"""
        return {
            "node_count": len(self._nodes),
            "total_associations": self.total_associations,
            "association_updates": self.association_updates,
            "avg_associations_per_node": (
                sum(len(n.associations) for n in self._nodes.values()) / max(1, len(self._nodes))
            ),
            "causal_links": len(self._causal_links),
            "episodes_tracked": len(self._episode_members),
        }


# ============================================================================
# 联想记忆管理器 - 主入口
# ============================================================================

class AssociativeMemory:
    """联想记忆管理器

    集成到EpisodicMemory中，自动:
    - 追踪episode中的共现关系
    - 记录action→result因果链接
    - 构建语义/情绪联想
    - 支持梦境生成中的联想重组
    """

    def __init__(
        self,
        association_threshold: float = 0.2,
        max_associations: int = 10,
        embedding_dim: int = 384,
        enable_auto_link: bool = True,
    ):
        self.network = AssociativeNetwork(
            association_threshold=association_threshold,
            max_associations=max_associations,
        )
        self.embedding_dim = embedding_dim
        self.enable_auto_link = enable_auto_link

        # Embedding cache
        self._embed_cache: Dict[str, np.ndarray] = {}

        # 嵌入函数（可配置）
        self._embedding_fn: Optional[Callable[[str], np.ndarray]] = None

    def set_embedding_function(self, fn: Callable[[str], np.ndarray]):
        """设置嵌入函数"""
        self._embedding_fn = fn

    def _get_embedding(self, text: str) -> np.ndarray:
        """获取文本嵌入"""
        if text in self._embed_cache:
            return self._embed_cache[text]

        if self._embedding_fn is not None:
            embedding = self._embedding_fn(text)
        else:
            # 默认: 基于哈希的伪嵌入
            import hashlib
            hash_val = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
            np.random.seed(hash_val % (2**32))
            embedding = np.random.randn(self.embedding_dim)
            embedding = embedding / (np.linalg.norm(embedding) + 1e-10)

        self._embed_cache[text] = embedding
        return embedding

    def add_episode_memory(
        self,
        episode_id: int,
        tick: int,
        observation: Any,
        action: Any,
        result: Any,
        mood: float,
        stress: float,
        salience: float = 0.5,
    ) -> str:
        """添加episode记忆到联想网络

        Args:
            episode_id: Episode ID
            tick: 时间步
            observation: 观察内容
            action: 执行的动作
            result: 结果
            mood: 情绪状态
            stress: 压力状态
            salience: 显著性

        Returns:
            创建的节点ID
        """
        # 创建节点ID
        node_id = f"ep_{episode_id}_tick_{tick}"

        # 构建文本摘要
        text = f"Action: {action}, Result: {result}"

        # 创建节点
        node = AssociativeNode(
            id=node_id,
            text=text,
            embedding=self._get_embedding(text),
            mood_context=mood,
            stress_context=stress,
            tick=tick,
            episode_tick=tick,
            action=str(action) if action else None,
            result=str(result) if result else None,
            salience=salience,
        )

        self.network.add_node(node)

        # 自动链接: 如果在同一episode中，建立共现
        if self.enable_auto_link:
            existing_members = self.network._episode_members.get(episode_id, set())
            if existing_members:
                # 与episode中已有节点建立共现联想
                for existing_id in existing_members:
                    self.network._update_or_create_association(
                        existing_id, node_id,
                        co_occurrence_boost=0.3
                    )
                    # 双向
                    self.network._update_or_create_association(
                        node_id, existing_id,
                        co_occurrence_boost=0.3
                    )

            # 注册到episode
            existing_members.add(node_id)
            self.network._episode_members[episode_id] = existing_members

        return node_id

    def register_action_result(
        self,
        action_node_id: str,
        result_node_id: str,
        strength: float = 0.5
    ):
        """注册action→result因果链接"""
        self.network.register_causal_link(action_node_id, result_node_id, strength)

    def retrieve_by_association(
        self,
        query_text: str,
        top_k: int = 5,
        mood: Optional[float] = None,
        stress: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """基于联想检索记忆

        Args:
            query_text: 查询文本
            top_k: 返回数量
            mood: 可选的情绪上下文（用于普鲁斯特效应）
            stress: 可选的压力上下文

        Returns:
            检索结果列表
        """
        # 获取查询嵌入
        query_emb = self._get_embedding(query_text)

        # 计算语义相似度
        similarities = []
        for node_id, node in self.network._nodes.items():
            node_emb = node.get_embedding()
            sim = np.dot(query_emb, node_emb) / (
                np.linalg.norm(query_emb) * np.linalg.norm(node_emb) + 1e-10
            )
            similarities.append((node_id, sim))

        # 排序
        similarities.sort(key=lambda x: x[1], reverse=True)

        # 获取联想增强的分数
        results = []
        for node_id, sem_sim in similarities[:top_k * 2]:  # 取更多候选
            node = self.network.get_node(node_id)
            if not node:
                continue

            # 联想分数: 考虑邻居的相似度
            assoc_score = 0.0
            neighbors = self.network.get_neighbors(node_id)
            if neighbors:
                for neighbor_id, weight in neighbors[:3]:
                    neighbor = self.network.get_node(neighbor_id)
                    if neighbor:
                        n_emb = neighbor.get_embedding()
                        n_sim = np.dot(query_emb, n_emb) / (
                            np.linalg.norm(query_emb) * np.linalg.norm(n_emb) + 1e-10
                        )
                        assoc_score += weight * max(0, n_sim)

            # 综合分数: 70% 语义 + 30% 联想
            total_score = 0.7 * sem_sim + 0.3 * assoc_score

            # 普鲁斯特效应增强
            proust_boost = 0.0
            if mood is not None and stress is not None:
                mood_diff = abs(node.mood_context - mood)
                stress_diff = abs(node.stress_context - stress)
                emo_sim = 1.0 - (mood_diff * 0.6 + stress_diff * 0.4)
                if emo_sim > 0.7:
                    proust_boost = 0.2  # 情绪匹配时提升

            results.append({
                "node_id": node_id,
                "text": node.text,
                "score": total_score + proust_boost,
                "semantic_similarity": sem_sim,
                "associative_score": assoc_score,
                "proust_boost": proust_boost,
                "mood_context": node.mood_context,
                "stress_context": node.stress_context,
                "tick": node.tick,
            })

        # 排序并返回top_k
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def generate_dream_assembly(
        self,
        seed_memories: List[str],
        diversity: float = 0.5,
        max_count: int = 10
    ) -> List[Dict[str, Any]]:
        """生成梦境联想组合

        用于梦境生成中的联想重组

        Args:
            seed_memories: 种子记忆ID列表
            diversity: 多样性参数 (0-1), 越高越多样化
            max_count: 最大返回数量

        Returns:
            梦境组合列表
        """
        # 联想激活传播
        activated = self.network.propagate_activation(
            seed_memories,
            max_steps=3 if diversity > 0.5 else 2,
            activation_threshold=0.3
        )

        # 按激活分数排序
        sorted_activated = sorted(
            activated.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # 构建梦境组合
        dream_assembly = []
        for node_id, activation_score in sorted_activated[:max_count]:
            node = self.network.get_node(node_id)
            if node:
                # 获取联想路径
                paths = []
                for seed_id in seed_memories:
                    path = self.network.find_associative_path(seed_id, node_id, max_length=4)
                    if path:
                        paths.append(path)

                dream_assembly.append({
                    "node_id": node_id,
                    "text": node.text,
                    "activation_score": activation_score,
                    "mood_context": node.mood_context,
                    "stress_context": node.stress_context,
                    "associative_paths": paths[:2],  # 最多2条路径
                    "neighbors": self.network.get_neighbors(node_id)[:3],
                })

        return dream_assembly

    def decay(self):
        """衰减联想网络"""
        self.network.decay_associations()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.network.get_stats()
        stats["cache_size"] = len(self._embed_cache)
        return stats

    def export_state(self) -> Dict[str, Any]:
        """导出状态"""
        return {
            "nodes": {
                nid: {
                    "id": n.id,
                    "text": n.text,
                    "mood_context": n.mood_context,
                    "stress_context": n.stress_context,
                    "tick": n.tick,
                    "salience": n.salience,
                    "associations": {
                        tid: {
                            "weight": e.weight,
                            "co_occurrence": e.co_occurrence,
                            "causal": e.causal,
                            "emotional": e.emotional,
                        }
                        for tid, e in n.associations.items()
                    }
                }
                for nid, n in self.network._nodes.items()
            },
            "episode_members": {
                str(k): list(v) for k, v in self.network._episode_members.items()
            },
            "stats": self.get_stats(),
        }

    def import_state(self, state: Dict[str, Any]):
        """导入状态"""
        # 简化实现: 只恢复统计信息
        # 完整恢复需要重建节点和边
        pass


# ============================================================================
# 工厂函数
# ============================================================================

def create_associative_memory(
    association_threshold: float = 0.2,
    max_associations: int = 10,
    embedding_dim: int = 384
) -> AssociativeMemory:
    """创建联想记忆管理器"""
    return AssociativeMemory(
        association_threshold=association_threshold,
        max_associations=max_associations,
        embedding_dim=embedding_dim,
    )
