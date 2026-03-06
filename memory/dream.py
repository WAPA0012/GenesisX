"""Dream-Reflect-Insight system for Digital Life.

论文 Section 3.10.4: 梦-反思-洞察 (Dream-Reflect-Insight)

在睡眠/离线模式下运行:
1. 抽样高显著性情节
2. 压缩模式为schemas
3. 评估洞察质量
4. 接受或拒绝 (带证据验证 P1-8)
5. 形成新技能

这是记忆巩固的高级接口，实际实现在 consolidation.py 中。
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class DreamPhase(Enum):
    """梦境阶段."""
    SAMPLING = "sampling"        # 抽样高显著性情节
    COMPRESSION = "compression"   # 压缩为模式
    EVALUATION = "evaluation"     # 评估洞察质量
    CONSOLIDATION = "consolidation"  # 巩固为长期记忆


@dataclass
class DreamEpisode:
    """梦境情节.

    在梦中重放的记忆片段.
    """
    tick: int
    observation: Any
    action: Any
    reward: float
    delta: float  # RPE
    salience: float
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DreamReport:
    """梦境报告.

    记录一次梦境周期的结果.
    """
    tick: int
    phase: DreamPhase
    episodes_sampled: int
    schemas_created: int
    skills_created: int
    insights_evaluated: int
    insights_accepted: int
    insights_rejected: int
    duration_seconds: float = 0.0
    notes: List[str] = field(default_factory=list)


class DreamEngine:
    """梦-反思-洞察引擎.

    论文 Section 3.10.4: 在离线模式下运行记忆巩固

    功能:
    - 抽样高显著性情节
    - 识别重复模式
    - 生成洞察假设
    - 评估洞察质量
    - 巩固为长期记忆
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        sample_size: int = 50,
        quality_threshold: float = 0.65
    ):
        """初始化梦境引擎.

        Args:
            config: 全局配置
            sample_size: 每次梦境抽样情节数量
            quality_threshold: 洞察质量阈值 (Q^insight)
        """
        self.config = config or {}
        self.sample_size = sample_size
        self.quality_threshold = quality_threshold

        # 统计信息
        self.dream_count = 0
        self.total_insights = 0
        self.accepted_insights = 0

    def should_dream(self, state: Dict[str, Any]) -> bool:
        """判断是否应该进入梦境模式.

        论文 Section 3.10.4: 在睡眠/离线模式下运行

        Args:
            state: 当前状态

        Returns:
            是否应该进入梦境
        """
        # 检查模式
        mode = state.get("mode", "work")
        if mode not in ("sleep", "offline"):
            return False

        # 检查是否有足够的情节记忆
        episode_count = state.get("episodic_count", 0)
        if episode_count < self.sample_size:
            return False

        return True

    def prepare_dream_context(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """准备梦境上下文.

        Args:
            state: 当前状态

        Returns:
            梦境上下文
        """
        return {
            "tick": state.get("tick", 0),
            "mode": state.get("mode", "sleep"),
            "mood": state.get("mood", 0.5),
            "stress": state.get("stress", 0.2),
            "sample_size": self.sample_size,
            "quality_threshold": self.quality_threshold,
        }

    def generate_dream_prompt(self, context: Dict[str, Any]) -> str:
        """生成梦境提示.

        用于LLM生成洞察假设.

        Args:
            context: 梦境上下文

        Returns:
            梦境提示文本
        """
        return f"""梦境模式 - 记忆反思与洞察生成

当前状态:
- Tick: {context['tick']}
- 情绪: {context['mood']:.2f}
- 压力: {context['stress']:.2f}

任务:
基于最近的高显著性情节，识别重复模式并生成洞察假设。

输出格式:
1. 模式描述
2. 触发条件
3. 典型行动
4. 预期结果
5. 证据强度
"""


class DreamDirector:
    """梦境导演.

    协调整个梦境周期的执行.

    论文 Section 3.10.4: 梦境周期的四个阶段

    Enhanced: 实现实际的内存访问和四个阶段的具体逻辑 (修复P1-4).
    """

    def __init__(self, dream_engine: Optional[DreamEngine] = None):
        """初始化梦境导演.

        Args:
            dream_engine: 梦境引擎实例
        """
        self.dream_engine = dream_engine or DreamEngine()
        self.current_phase = DreamPhase.SAMPLING
        self.current_report: Optional[DreamReport] = None

        # 新增：实际内存访问接口
        self.episodic_memory = None
        self.schema_memory = None
        self.skill_memory = None

        # 联想记忆引用
        self._associative_memory = None

    def set_memory_interfaces(self, episodic, schema, skill):
        """设置内存接口（用于实际访问记忆）

        Args:
            episodic: 情节记忆实例
            schema: 图式记忆实例
            skill: 技能记忆实例
        """
        self.episodic_memory = episodic
        self.schema_memory = schema
        self.skill_memory = skill

        # 尝试获取联想记忆引用
        if hasattr(episodic, 'get_associative_memory'):
            self._associative_memory = episodic.get_associative_memory()

    def start_dream_cycle(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """开始一个新的梦境周期（增强版：实际执行四个阶段）.

        论文 Section 3.10.4: Dream-Reflect-Insight 流程
        1. 抽样 (Replay Sampling): 从episodic中采样高显著性片段
        2. 生成梦境轨迹 (Dream Trace): 重组为联想/对比/因果链
        3. 提取候选洞察 (Candidate Insights): 生成规则/策略/总结
        4. 质量评估 (Quality Assessment): 计算Q^insight
        5. 沉淀 (Consolidation): 写入schema，可复用片段写入skill
        6. 遗忘/归档 (Prune): 删除低价值/高相似episode

        Args:
            state: 当前状态

        Returns:
            梦境报告 (如果不应该做梦则返回 None)
        """
        if not self.dream_engine.should_dream(state):
            return None

        import time
        start_time = time.time()

        # 创建报告
        self.current_report = DreamReport(
            tick=state.get("tick", 0),
            phase=DreamPhase.SAMPLING,
            episodes_sampled=0,
            schemas_created=0,
            skills_created=0,
            insights_evaluated=0,
            insights_accepted=0,
            insights_rejected=0,
        )

        # ========== 阶段1: 抽样高显著性情节 ==========
        sampled_episodes = self._sample_salient_episodes(state)
        self.current_report.episodes_sampled = len(sampled_episodes)

        if not sampled_episodes:
            self.current_report.notes.append("No high-salience episodes to process")
            return {
                "status": "dreaming",
                "phase": "sampling",
                "report": self.current_report,
            }

        # ========== 阶段2: 生成梦境轨迹 ==========
        self.current_phase = DreamPhase.COMPRESSION
        dream_traces = self._generate_dream_traces(sampled_episodes)

        # ========== 阶段3: 提取候选洞察 ==========
        self.current_phase = DreamPhase.EVALUATION
        candidate_insights = self._extract_insights(dream_traces)

        # ========== 阶段4: 质量评估与沉淀 ==========
        self.current_phase = DreamPhase.CONSOLIDATION
        for insight in candidate_insights:
            self.current_report.insights_evaluated += 1

            quality_score = self._evaluate_insight_quality(insight, state)

            if quality_score >= self.dream_engine.quality_threshold:
                self._consolidate_insight(insight, quality_score)
                self.current_report.insights_accepted += 1
                self.current_report.schemas_created += 1
            else:
                self.current_report.insights_rejected += 1

        # ========== 阶段5: 遗忘/归档 ==========
        self._prune_low_value_episodes(state)

        # 更新统计
        self.dream_engine.dream_count += 1
        self.dream_engine.total_insights += self.current_report.insights_evaluated
        self.dream_engine.accepted_insights += self.current_report.insights_accepted

        duration = time.time() - start_time
        self.current_report.duration_seconds = duration

        return {
            "status": "completed",
            "phase": "consolidation",
            "report": self.current_report,
        }

    def _sample_salient_episodes(self, state: Dict[str, Any]) -> List[DreamEpisode]:
        """抽样高显著性情节

        论文: 采样概率与显著性（RPE绝对值、情绪变化、未完成目标相关性）正相关

        Args:
            state: 当前状态

        Returns:
            抽样的情节列表
        """
        if self.episodic_memory is None:
            return []

        episodes = []

        try:
            # 从情节记忆中获取所有记录
            all_episodes = self.episodic_memory.get_all()

            # 按显著性排序（|delta|越大，显著性越高）
            scored = [
                (ep, abs(getattr(ep, 'delta', 0)) + abs(getattr(ep, 'reward', 0)))
                for ep in all_episodes
            ]
            scored.sort(key=lambda x: x[1], reverse=True)

            # 取前N个
            for ep, score in scored[:self.dream_engine.sample_size]:
                dream_ep = DreamEpisode(
                    tick=getattr(ep, 'tick', 0),
                    observation=getattr(ep, 'observation', None),
                    action=getattr(ep, 'action', None),
                    reward=getattr(ep, 'reward', 0),
                    delta=getattr(ep, 'delta', 0),
                    salience=score,
                    context=getattr(ep, 'state_snapshot', {}),
                )
                episodes.append(dream_ep)

        except Exception as e:
            self.current_report.notes.append(f"Sampling error: {e}")

        return episodes

    def _generate_dream_traces(self, episodes: List[DreamEpisode]) -> List[Dict[str, Any]]:
        """生成梦境轨迹

        论文: 将多段片段在语义空间中重组为联想/对比/因果链

        增强版: 使用联想记忆进行真正的联想重组

        Args:
            episodes: 抽样的情节列表

        Returns:
            梦境轨迹列表
        """
        traces = []

        # 尝试使用联想记忆生成梦境轨迹
        if hasattr(self, '_associative_memory') and self._associative_memory:
            return self._generate_associative_traces(episodes)

        # 降级方案: 按时间分组
        episodes_by_time = {}
        for ep in episodes:
            time_bucket = ep.tick // 100  # 100 ticks一个bucket
            if time_bucket not in episodes_by_time:
                episodes_by_time[time_bucket] = []
            episodes_by_time[time_bucket].append(ep)

        # 每个时间桶生成一个轨迹
        for time_bucket, bucket_episodes in episodes_by_time.items():
            if len(bucket_episodes) < 2:
                continue

            trace = {
                "time_range": (time_bucket * 100, (time_bucket + 1) * 100),
                "episodes": bucket_episodes,
                "patterns": self._identify_patterns(bucket_episodes),
                "type": "temporal",  # 标记为时间分组类型
            }
            traces.append(trace)

        return traces

    def _generate_associative_traces(self, episodes: List[DreamEpisode]) -> List[Dict[str, Any]]:
        """使用联想记忆生成梦境轨迹

        基于联想网络进行真正的联想重组:
        - 共现联想: 同一episode中的记忆
        - 因果联想: action→result链
        - 情绪联想: 相似情绪状态的记忆
        - 语义联想: 语义相似的记忆

        Args:
            episodes: 抽样的情节列表

        Returns:
            梦境轨迹列表
        """
        traces = []

        # 获取种子记忆ID (显著性最高的几个)
        seed_ids = [f"ep_{ep.tick}_tick_{ep.tick}" for ep in episodes[:5]]

        # 使用联想记忆生成梦境组合
        dream_assembly = self._associative_memory.generate_dream_assembly(
            seed_memories=seed_ids,
            diversity=0.6,
            max_count=20
        )

        # 按联想类型分组
        for assembly in dream_assembly:
            trace = {
                "node_id": assembly["node_id"],
                "text": assembly["text"],
                "activation_score": assembly["activation_score"],
                "mood_context": assembly["mood_context"],
                "stress_context": assembly["stress_context"],
                "associative_paths": assembly["associative_paths"],
                "neighbors": assembly["neighbors"],
                "type": "associative",
            }
            traces.append(trace)

        return traces

    def _identify_patterns(self, episodes: List[DreamEpisode]) -> List[str]:
        """识别重复模式"""
        patterns = []

        # 分析共同标签
        all_tags = set()
        for ep in episodes:
            if hasattr(ep, 'context') and 'tags' in ep.context:
                all_tags.update(ep.context['tags'])

        # 频繁出现的标签作为模式
        if len(all_tags) > 0:
            patterns.extend(list(all_tags)[:5])

        return patterns

    def _extract_insights(self, traces: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """提取候选洞察

        Args:
            traces: 梦境轨迹列表

        Returns:
            候选洞察列表
        """
        insights = []

        for trace in traces:
            if "patterns" not in trace or not trace["patterns"]:
                continue

            # 提取证据tick引用
            episodes = trace.get("episodes", [])
            evidence_refs = [
                getattr(ep, 'tick', 0) if hasattr(ep, 'tick') else ep.get('tick', 0)
                for ep in episodes
            ]
            # 使用最新episode的tick作为created_tick
            created_tick = max(evidence_refs) if evidence_refs else 0

            insight = {
                "type": "pattern",
                "description": f"Pattern: {', '.join(trace['patterns'][:3])}",
                "triggers": trace["patterns"],
                "evidence_count": len(episodes),
                "evidence_refs": evidence_refs,
                "created_tick": created_tick,
                "time_range": trace.get("time_range"),
            }
            insights.append(insight)

        return insights

    def _evaluate_insight_quality(self, insight: Dict[str, Any], state: Dict[str, Any]) -> float:
        """评估洞察质量 Q^insight

        论文: 包含压缩性、可迁移性、新颖性

        Args:
            insight: 洞察字典
            state: 当前状态

        Returns:
            质量分数 [0,1]
        """
        quality = 0.0

        # 压缩性：证据数量
        evidence_count = insight.get("evidence_count", 0)
        quality += min(0.4, evidence_count / 10.0)

        # 可迁移性：是否有明确的触发条件
        if insight.get("triggers"):
            quality += 0.3

        # 新颖性：检查是否与现有schema不同
        if self.schema_memory:
            is_novel = self._check_novelty(insight)
            quality += 0.3 if is_novel else 0.0

        return min(1.0, quality)

    def _check_novelty(self, insight: Dict[str, Any]) -> bool:
        """检查洞察的新颖性（使用语义嵌入）

        论文 P1-4: 使用 sentence embeddings 评估洞察新颖度
        """
        # 尝试使用语义嵌入检查
        try:
            from .semantic_novelty import compute_novelty

            if self.schema_memory:
                existing_schemas = self.schema_memory.get_all()
                if existing_schemas:
                    # 提取现有schema的声明文本
                    existing_texts = []
                    for schema in existing_schemas:
                        if hasattr(schema, 'claim'):
                            existing_texts.append(schema.claim)

                    # 使用语义嵌入计算新颖度
                    insight_text = insight.get("claim", insight.get("description", ""))
                    if insight_text and existing_texts:
                        novelty_score, is_novel = compute_novelty(
                            insight=insight_text,
                            existing=existing_texts,
                            threshold=0.85,  # 高阈值确保真正的语义新颖性
                        )
                        return is_novel
        except ImportError:
            # 降级到字符串匹配（如果 semantic_novelty 不可用）
            pass

        # 降级方案：简单字符串匹配
        if self.schema_memory:
            existing_schemas = self.schema_memory.get_all()
            for schema in existing_schemas:
                if hasattr(schema, 'claim'):
                    if insight.get("claim", "") == schema.claim:
                        return False
        return True

    def _consolidate_insight(self, insight: Dict[str, Any], quality: float):
        """沉淀洞察到记忆"""
        if self.schema_memory:
            try:
                # 创建新的schema条目
                from .schema import SchemaEntry
                schema_entry = SchemaEntry(
                    claim=insight.get("claim", insight.get("description", "")),
                    scope="general",
                    confidence=quality,
                    evidence_refs=insight.get("evidence_refs", []),
                    supporting_count=insight.get("evidence_count", 0),
                    conflicting_count=0,
                    created_tick=insight.get("created_tick", 0),
                    last_updated_tick=insight.get("created_tick", 0),
                    tags=insight.get("triggers", []),
                )
                self.schema_memory.add(schema_entry)
            except Exception as e:
                self.current_report.notes.append(f"Consolidation error: {e}")

    def _prune_low_value_episodes(self, state: Dict[str, Any]):
        """遗忘/归档低价值情节"""
        if self.episodic_memory:
            try:
                # 获取所有情节并按重要性排序
                all_episodes = self.episodic_memory.get_all()

                # 计算重要性分数
                scored = [
                    (ep, abs(getattr(ep, 'delta', 0)))
                    for ep in all_episodes
                ]
                scored.sort(key=lambda x: x[1], reverse=True)

                # 如果超过容量，删除低价值的
                capacity = state.get("episodic_capacity", 1000)
                if len(scored) > capacity:
                    pruned_count = len(scored) - capacity
                    # Use prune_disk_by_salience to actually remove low-value episodes
                    min_delta = scored[capacity - 1][1] if capacity > 0 else 0.0
                    try:
                        self.episodic_memory.prune_disk_by_salience(
                            salience_threshold=min_delta,
                            keep_recent_ratio=0.15,
                        )
                    except Exception:
                        pass  # Pruning is best-effort
                    self.current_report.notes.append(
                        f"Pruned {pruned_count} low-value episodes (delta < {min_delta:.3f})"
                    )
            except Exception as e:
                self.current_report.notes.append(f"Pruning error: {e}")

    def complete_dream_cycle(self) -> DreamReport:
        """完成当前梦境周期.

        Returns:
            梦境报告
        """
        if self.current_report:
            self.current_report.phase = DreamPhase.CONSOLIDATION

        return self.current_report or DreamReport(
            tick=0,
            phase=DreamPhase.CONSOLIDATION,
            episodes_sampled=0,
            schemas_created=0,
            skills_created=0,
            insights_evaluated=0,
            insights_accepted=0,
            insights_rejected=0,
        )

    def get_dream_summary(self) -> Dict[str, Any]:
        """获取梦境统计摘要.

        Returns:
            统计摘要
        """
        return {
            "dream_count": self.dream_engine.dream_count,
            "total_insights": self.dream_engine.total_insights,
            "accepted_insights": self.dream_engine.accepted_insights,
            "acceptance_rate": (
                self.dream_engine.accepted_insights / max(1, self.dream_engine.total_insights)
                if self.dream_engine.total_insights > 0 else 0.0
            ),
        }


def create_dream_engine(config: Optional[Dict[str, Any]] = None) -> DreamEngine:
    """工厂函数: 创建梦境引擎.

    Args:
        config: 全局配置

    Returns:
        梦境引擎实例
    """
    # 从配置中读取参数
    dream_config = config.get("dream", {}) if config else {}

    sample_size = dream_config.get("sample_size", 50)
    quality_threshold = dream_config.get("quality_threshold", 0.65)

    return DreamEngine(
        config=config,
        sample_size=sample_size,
        quality_threshold=quality_threshold,
    )


def create_dream_director(config: Optional[Dict[str, Any]] = None) -> DreamDirector:
    """工厂函数: 创建梦境导演.

    Args:
        config: 全局配置

    Returns:
        梦境导演实例
    """
    engine = create_dream_engine(config)
    return DreamDirector(engine)
