"""Archivist Organ - memory management and hygiene.

支持两种模式：
1. LLM 模式：使用 LLM 进行真正的记忆管理决策
2. 规则模式：使用预设规则进行决策（LLM 不可用时的 fallback）
"""
from typing import List, Dict, Any, Set, Optional, TYPE_CHECKING
from ..base_organ import BaseOrgan
from common.models import Action
from collections import defaultdict

if TYPE_CHECKING:
    from ..organ_llm_session import OrganLLMSession


class ArchivistOrgan(BaseOrgan):
    """Archivist organ for memory management.

    Sophisticated memory management system that handles:
    - Memory consolidation and integration
    - Pruning and cleanup of redundant memories
    - Indexing and categorization for retrieval
    - Pattern recognition across memories
    - Priority-based retention strategies
    - Memory compression and summarization
    - Recall optimization and access patterns
    """

    # Memory thresholds
    EPISODIC_CONSOLIDATION_THRESHOLD = 50
    SEMANTIC_UPDATE_THRESHOLD = 30
    PRUNING_THRESHOLD = 100
    CRITICAL_MEMORY_OVERLOAD = 200

    # Memory importance levels
    IMPORTANCE_CRITICAL = 1.0
    IMPORTANCE_HIGH = 0.8
    IMPORTANCE_MEDIUM = 0.5
    IMPORTANCE_LOW = 0.3
    IMPORTANCE_TRIVIAL = 0.1

    # Consolidation strategies
    CONSOLIDATION_STRATEGIES = [
        "temporal",        # Group by time proximity
        "thematic",       # Group by topic/theme
        "causal",         # Group by cause-effect relationships
        "associative",    # Group by associations
        "hierarchical",   # Organize in hierarchies
        "pattern_based",  # Group by patterns
    ]

    # Retention policies
    RETENTION_RECENT = 10      # Keep last N memories always
    RETENTION_IMPORTANT = 50   # Keep important memories longer
    RETENTION_PATTERN = 20     # Keep pattern-forming memories

    def __init__(self, llm_session: Optional["OrganLLMSession"] = None):
        """Initialize archivist organ.

        Args:
            llm_session: LLM 会话（可选，用于真正的记忆管理思考）
        """
        super().__init__("archivist")

        # LLM 会话
        self._llm_session = llm_session

        # 最后的思考（用于选择性记忆）
        self._last_thought: Optional[str] = None

        # Memory tracking
        self.memory_count = 0
        self.episodic_count = 0
        self.semantic_count = 0
        self.memory_categories = defaultdict(int)  # category -> count

        # Consolidation tracking
        self.last_consolidation_tick = 0
        self.consolidation_history = []  # Track consolidation events
        self.consolidated_memory_groups = []  # Groups of related memories

        # Pruning tracking
        self.last_pruning_tick = 0
        self.pruned_count = 0
        self.retention_scores = {}  # memory_id -> retention_score

        # Access patterns
        self.memory_access_frequency = defaultdict(int)  # memory_id -> access_count
        self.recent_accesses = []  # Track recent memory accesses
        self.access_patterns = []  # Detected patterns in access

        # Memory importance
        self.memory_importance = {}  # memory_id -> importance_score
        self.critical_memories = set()  # IDs of critical memories

        # Indexing and categorization
        self.memory_index = {}  # topic -> [memory_ids]
        self.memory_tags = defaultdict(set)  # memory_id -> set of tags
        self.tag_usage = defaultdict(int)  # tag -> usage_count

        # Strategy effectiveness
        self.current_consolidation_strategy = "temporal"
        self.strategy_effectiveness = {s: 0.5 for s in self.CONSOLIDATION_STRATEGIES}

        # Quality metrics
        self.retrieval_success_rate = 0.5
        self.consolidation_quality_scores = []

    def set_llm_session(self, session: "OrganLLMSession"):
        """设置 LLM 会话"""
        self._llm_session = session

    def propose_actions(
        self,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[Action]:
        """提议动作 - 如果有 LLM 会话则使用 LLM 思考"""
        if self._llm_session:
            return self._propose_actions_with_llm(state, context)
        else:
            return self._propose_actions_impl(state, context)

    def _propose_actions_with_llm(
        self,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[Action]:
        """使用 LLM 进行记忆管理思考"""
        actions = []

        # 构建思考提示
        prompt = self._build_thinking_prompt(state, context)

        # 调用 LLM 思考
        thought = self._llm_session.think(prompt)

        if thought:
            # 保存最后的思考（用于选择性记忆）
            self._last_thought = thought

            # 解析 LLM 的思考结果为 Action
            actions = self._parse_llm_thought_to_actions(thought, state, context)

        # 如果 LLM 没有返回有效的动作，fallback 到规则模式
        if not actions:
            actions = self._propose_actions_impl(state, context)

        return actions

    def get_last_thought(self) -> Optional[str]:
        """获取最后的思考内容（用于选择性记忆）"""
        return self._last_thought

    def clear_last_thought(self):
        """清除最后的思考"""
        self._last_thought = None

    def _build_thinking_prompt(self, state: Dict[str, Any], context: Dict[str, Any]) -> str:
        """构建记忆管理思考提示"""
        energy = state.get("energy", 0.5)
        cognitive_load = state.get("cognitive_load", 0.0)
        tick = state.get("tick", 0)

        # 获取记忆统计
        stats = self.get_memory_statistics()

        prompt = f"""请基于我的当前状态，独立思考并提出你认为值得记录或整理的内容。

【我的当前状态】
- 精力: {energy:.1%}
- 认知负荷: {cognitive_load:.1%}
- 当前tick: {tick}

【记忆状态】
- 总记忆数: {stats['total_memories']}
- 情景记忆: {stats['episodic_count']}
- 语义记忆: {stats['semantic_count']}
- 关键记忆: {stats['critical_memories']}
- 已整理: {stats['consolidations_performed']} 次
- 当前策略: {stats['current_consolidation_strategy']}

【记忆类别】
{stats['memory_categories'] if stats['memory_categories'] else '暂无分类'}

请回答以下问题：
1. 我最近有什么重要的经历或发现值得记录？
2. 有哪些记忆之间的联系值得整理？
3. 我应该关注哪些知识或模式？

请直接告诉我你的思考，不要使用列表格式。"""
        return prompt

    def _parse_llm_thought_to_actions(
        self,
        thought: str,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[Action]:
        """将 LLM 的思考解析为 Action"""
        actions = []
        thought_lower = thought.lower()

        # 根据 LLM 的思考内容推断记忆管理意图
        if any(kw in thought_lower for kw in ["整理", "归纳", "分类", "索引", "组织"]):
            actions.append(Action(
                type="REFLECT",
                params={
                    "purpose": "memory_consolidation",
                    "depth": 2,
                    "strategy": self.current_consolidation_strategy,
                    "source": "llm_thinking",
                    "thought": thought[:200],
                },
                risk_level=0.0,
                capability_req=["llm_access"],
            ))

        if any(kw in thought_lower for kw in ["模式", "规律", "联系", "关联", "发现"]):
            actions.append(Action(
                type="REFLECT",
                params={
                    "purpose": "pattern_recognition",
                    "depth": 2,
                    "scope": "cross_memory_analysis",
                    "source": "llm_thinking",
                    "thought": thought[:200],
                },
                risk_level=0.0,
                capability_req=["llm_access"],
            ))

        if any(kw in thought_lower for kw in ["清理", "删除", "修剪", "优化", "压缩"]):
            actions.append(Action(
                type="REFLECT",
                params={
                    "purpose": "memory_pruning",
                    "depth": 1,
                    "criteria": "low_importance",
                    "source": "llm_thinking",
                    "thought": thought[:200],
                },
                risk_level=0.1,
                capability_req=[],
            ))

        # 如果没有匹配到任何意图，创建一个通用的反思动作
        if not actions:
            actions.append(Action(
                type="REFLECT",
                params={
                    "purpose": "memory_reflection",
                    "depth": 1,
                    "source": "llm_thinking",
                    "thought": thought[:200],
                },
                risk_level=0.0,
                capability_req=[],
            ))

        return actions

    def _propose_actions_impl(
        self,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[Action]:
        """Propose memory management actions with sophisticated strategies.

        Args:
            state: Current state
            context: Current context

        Returns:
            List of archival actions
        """
        actions = []

        # Extract relevant state
        episodic_count = state.get("episodic_count", 0)
        semantic_count = state.get("semantic_count", 0)
        tick = state.get("tick", 0)
        energy = state.get("energy", 0.5)
        cognitive_load = state.get("cognitive_load", 0.0)

        # Update archivist state
        self._update_archivist_state(episodic_count, semantic_count, tick)

        # === STRATEGY 1: CRITICAL MEMORY OVERLOAD ===
        # Emergency consolidation when memory is dangerously high
        if episodic_count > self.CRITICAL_MEMORY_OVERLOAD:
            emergency_actions = self._emergency_consolidation(state, context)
            actions.extend(emergency_actions)
            return actions  # Emergency: skip other strategies

        # === STRATEGY 2: PERIODIC CONSOLIDATION ===
        # Regular memory consolidation to prevent buildup
        if self._should_consolidate(episodic_count, tick):
            consolidation_actions = self._consolidate_memories(state, context)
            actions.extend(consolidation_actions)

        # === STRATEGY 3: MEMORY PRUNING ===
        # Remove low-value or redundant memories
        if self._should_prune(episodic_count, tick):
            pruning_actions = self._prune_memories(state, context)
            actions.extend(pruning_actions)

        # === STRATEGY 4: SEMANTIC INTEGRATION ===
        # Integrate episodic memories into semantic knowledge
        if self._should_integrate_semantic(episodic_count, semantic_count):
            integration_actions = self._integrate_semantic(state, context)
            actions.extend(integration_actions)

        # === STRATEGY 5: MEMORY INDEXING ===
        # Create and update memory indices for better retrieval
        if self._should_index(tick):
            indexing_actions = self._index_memories(state, context)
            actions.extend(indexing_actions)

        # === STRATEGY 6: PATTERN RECOGNITION ===
        # Identify patterns across memories
        if self._should_recognize_patterns(episodic_count):
            pattern_actions = self._recognize_patterns(state, context)
            actions.extend(pattern_actions)

        # === STRATEGY 7: MEMORY COMPRESSION ===
        # Compress related memories into summaries
        if self._should_compress(episodic_count):
            compression_actions = self._compress_memories(state, context)
            actions.extend(compression_actions)

        # === STRATEGY 8: ADAPTIVE STRATEGY ===
        # Adjust consolidation strategy based on effectiveness
        if len(self.consolidation_history) > 10:
            adaptive_actions = self._adapt_consolidation_strategy(state, context)
            actions.extend(adaptive_actions)

        return actions

    def _update_archivist_state(
        self, episodic_count: int, semantic_count: int, tick: int
    ):
        """Update internal archivist state.

        Args:
            episodic_count: Current episodic memory count
            semantic_count: Current semantic memory count
            tick: Current tick
        """
        self.episodic_count = episodic_count
        self.semantic_count = semantic_count
        self.memory_count = episodic_count + semantic_count

        # Update retention scores based on access patterns
        self._update_retention_scores()

    def _update_retention_scores(self):
        """Update retention scores for memories based on multiple factors."""
        for memory_id in list(self.retention_scores.keys()):
            # Base retention score
            base_score = self.retention_scores.get(memory_id, 0.5)

            # Boost for frequently accessed memories
            access_freq = self.memory_access_frequency.get(memory_id, 0)
            access_boost = min(access_freq / 10, 0.3)

            # Boost for important memories
            importance = self.memory_importance.get(memory_id, self.IMPORTANCE_MEDIUM)
            importance_boost = importance * 0.4

            # Calculate final retention score
            retention_score = min(base_score + access_boost + importance_boost, 1.0)
            self.retention_scores[memory_id] = retention_score

    # === MEMORY MANAGEMENT STRATEGY METHODS ===

    def _emergency_consolidation(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Emergency consolidation when memory overload is critical."""
        actions = []

        actions.append(Action(
            type="REFLECT",
            params={
                "purpose": "emergency_memory_consolidation",
                "depth": 3,
                "urgency": "critical",
                "target": "reduce_episodic_count",
                "aggressive": True
            },
            risk_level=0.1,
            capability_req=["llm_access"],
        ))

        return actions

    def _should_consolidate(self, episodic_count: int, tick: int) -> bool:
        """Determine if memory consolidation is needed."""
        # Check threshold
        threshold_met = episodic_count >= self.EPISODIC_CONSOLIDATION_THRESHOLD

        # Check time since last consolidation
        ticks_since_last = tick - self.last_consolidation_tick
        time_for_consolidation = ticks_since_last > 100

        # Periodic consolidation at specific intervals
        periodic = episodic_count % 20 == 0 and episodic_count > 0

        return threshold_met or (time_for_consolidation and episodic_count > 20) or periodic

    def _consolidate_memories(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Consolidate episodic memories using current strategy."""
        actions = []

        # Choose consolidation strategy
        strategy = self.current_consolidation_strategy

        actions.append(Action(
            type="REFLECT",
            params={
                "purpose": "consolidate_memories",
                "depth": 2,
                "strategy": strategy,
                "focus": ["patterns", "themes", "connections"],
                "episodic_count": self.episodic_count
            },
            risk_level=0.0,
            capability_req=["llm_access"],
        ))

        # Record consolidation
        self.last_consolidation_tick = state.get("tick", 0)
        self.consolidation_history.append({
            "tick": state.get("tick", 0),
            "strategy": strategy,
            "count_before": self.episodic_count
        })

        return actions

    def _should_prune(self, episodic_count: int, tick: int) -> bool:
        """Determine if memory pruning is needed."""
        # Prune when memory count is high
        threshold_met = episodic_count >= self.PRUNING_THRESHOLD

        # Periodic pruning
        ticks_since_last = tick - self.last_pruning_tick
        time_for_pruning = ticks_since_last > 200

        return threshold_met or time_for_pruning

    def _prune_memories(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Prune low-value memories to free space."""
        actions = []

        # Identify candidates for pruning (low retention score)
        prune_candidates = [
            mem_id for mem_id, score in self.retention_scores.items()
            if score < self.IMPORTANCE_LOW and mem_id not in self.critical_memories
        ]

        if len(prune_candidates) > 5:
            actions.append(Action(
                type="REFLECT",
                params={
                    "purpose": "memory_pruning",
                    "depth": 1,
                    "candidates": len(prune_candidates),
                    "criteria": "low_importance_and_low_access",
                    "preserve_critical": True
                },
                risk_level=0.1,
                capability_req=[],
            ))

            self.last_pruning_tick = state.get("tick", 0)
            self.pruned_count += len(prune_candidates[:20])  # Prune up to 20

        return actions

    def _should_integrate_semantic(
        self, episodic_count: int, semantic_count: int
    ) -> bool:
        """Determine if semantic integration is needed."""
        # Integrate when episodic memories can form semantic knowledge
        return episodic_count > self.SEMANTIC_UPDATE_THRESHOLD and episodic_count > semantic_count * 2

    def _integrate_semantic(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Integrate episodic memories into semantic knowledge."""
        actions = []

        actions.append(Action(
            type="REFLECT",
            params={
                "purpose": "semantic_integration",
                "depth": 3,
                "source": "episodic_memories",
                "target": "semantic_knowledge",
                "focus": ["generalizations", "principles", "concepts"]
            },
            risk_level=0.0,
            capability_req=["llm_access"],
        ))

        return actions

    def _should_index(self, tick: int) -> bool:
        """Determine if memory indexing is needed."""
        # Index periodically to maintain retrieval efficiency
        return tick % 150 == 0 and self.memory_count > 30

    def _index_memories(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Create and update memory indices."""
        actions = []

        actions.append(Action(
            type="REFLECT",
            params={
                "purpose": "memory_indexing",
                "depth": 2,
                "focus": ["categorization", "tagging", "topic_extraction"],
                "update_indices": True
            },
            risk_level=0.0,
            capability_req=["llm_access"],
        ))

        return actions

    def _should_recognize_patterns(self, episodic_count: int) -> bool:
        """Determine if pattern recognition is needed."""
        return episodic_count >= 40 and episodic_count % 30 == 0

    def _recognize_patterns(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Recognize patterns across memories."""
        actions = []

        actions.append(Action(
            type="REFLECT",
            params={
                "purpose": "pattern_recognition",
                "depth": 2,
                "scope": "cross_memory_analysis",
                "focus": ["recurring_themes", "causal_chains", "associations"],
                "memory_count": self.episodic_count
            },
            risk_level=0.0,
            capability_req=["llm_access"],
        ))

        return actions

    def _should_compress(self, episodic_count: int) -> bool:
        """Determine if memory compression is needed."""
        # Compress when we have many related memories
        return len(self.consolidated_memory_groups) > 10

    def _compress_memories(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Compress related memories into summaries."""
        actions = []

        actions.append(Action(
            type="REFLECT",
            params={
                "purpose": "memory_compression",
                "depth": 2,
                "technique": "summarization",
                "preserve": ["key_facts", "important_details"],
                "groups": len(self.consolidated_memory_groups)
            },
            risk_level=0.1,
            capability_req=["llm_access"],
        ))

        return actions

    def _adapt_consolidation_strategy(
        self, state: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Action]:
        """Adapt consolidation strategy based on effectiveness."""
        actions = []

        # Find best performing strategy
        best_strategy = max(
            self.strategy_effectiveness,
            key=self.strategy_effectiveness.get
        )

        # Switch if current strategy isn't effective
        if (best_strategy != self.current_consolidation_strategy and
            self.strategy_effectiveness[self.current_consolidation_strategy] < 0.4):
            self.current_consolidation_strategy = best_strategy

            actions.append(Action(
                type="REFLECT",
                params={
                    "purpose": "consolidation_strategy_adaptation",
                    "depth": 1,
                    "new_strategy": best_strategy,
                    "reason": "effectiveness_optimization"
                },
                risk_level=0.0,
                capability_req=[],
            ))

        return actions

    # === HELPER METHODS ===

    def add_memory(
        self, memory_id: str, category: str,
        importance: float = 0.5, tags: Optional[Set[str]] = None
    ):
        """Add a memory for tracking.

        Args:
            memory_id: Memory identifier
            category: Memory category
            importance: Importance score (0-1)
            tags: Optional set of tags
        """
        self.memory_count += 1
        self.memory_categories[category] += 1
        self.memory_importance[memory_id] = importance
        self.retention_scores[memory_id] = importance

        if importance >= self.IMPORTANCE_CRITICAL:
            self.critical_memories.add(memory_id)

        if tags:
            self.memory_tags[memory_id] = tags
            for tag in tags:
                self.tag_usage[tag] += 1

    def access_memory(self, memory_id: str):
        """Record memory access for pattern tracking.

        Args:
            memory_id: Memory identifier
        """
        self.memory_access_frequency[memory_id] += 1
        self.recent_accesses.append(memory_id)

        # Keep recent accesses manageable
        if len(self.recent_accesses) > 50:
            self.recent_accesses.pop(0)

    def categorize_memory(self, memory_id: str, topics: List[str]):
        """Categorize memory by topics for indexing.

        Args:
            memory_id: Memory identifier
            topics: List of topics
        """
        for topic in topics:
            if topic not in self.memory_index:
                self.memory_index[topic] = []
            self.memory_index[topic].append(memory_id)

    def get_related_memories(self, topic: str) -> List[str]:
        """Get memories related to a topic.

        Args:
            topic: Topic to search for

        Returns:
            List of related memory IDs
        """
        return self.memory_index.get(topic, [])

    def mark_consolidation_quality(self, quality_score: float):
        """Record quality of a consolidation operation.

        Args:
            quality_score: Quality score (0-1)
        """
        self.consolidation_quality_scores.append(quality_score)

        # Update strategy effectiveness
        strategy = self.current_consolidation_strategy
        if quality_score > 0.7:
            self.strategy_effectiveness[strategy] = min(
                1.0, self.strategy_effectiveness[strategy] + 0.05
            )
        elif quality_score < 0.3:
            self.strategy_effectiveness[strategy] = max(
                0.0, self.strategy_effectiveness[strategy] - 0.05
            )

        # Keep history manageable
        if len(self.consolidation_quality_scores) > 50:
            self.consolidation_quality_scores.pop(0)

    def get_memory_statistics(self) -> Dict[str, Any]:
        """Get memory statistics for monitoring.

        Returns:
            Dict with memory statistics
        """
        avg_consolidation_quality = 0.0
        if self.consolidation_quality_scores:
            avg_consolidation_quality = sum(self.consolidation_quality_scores) / len(
                self.consolidation_quality_scores
            )

        return {
            "total_memories": self.memory_count,
            "episodic_count": self.episodic_count,
            "semantic_count": self.semantic_count,
            "critical_memories": len(self.critical_memories),
            "pruned_count": self.pruned_count,
            "consolidations_performed": len(self.consolidation_history),
            "current_consolidation_strategy": self.current_consolidation_strategy,
            "avg_consolidation_quality": avg_consolidation_quality,
            "memory_categories": dict(self.memory_categories),
            "top_tags": sorted(
                self.tag_usage.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10],
            "index_size": len(self.memory_index),
            "retrieval_success_rate": self.retrieval_success_rate,
        }

    def get_archivist_status(self) -> Dict[str, Any]:
        """Get current archivist status for monitoring.

        Returns:
            Dict with archivist state information
        """
        return {
            "memory_count": self.memory_count,
            "episodic_count": self.episodic_count,
            "semantic_count": self.semantic_count,
            "consolidation_strategy": self.current_consolidation_strategy,
            "strategy_effectiveness": self.strategy_effectiveness.copy(),
            "last_consolidation_tick": self.last_consolidation_tick,
            "last_pruning_tick": self.last_pruning_tick,
            "pruned_count": self.pruned_count,
            "critical_memories_count": len(self.critical_memories),
        }
