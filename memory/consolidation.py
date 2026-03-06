"""Dream-Reflect-Insight consolidation mechanism.

Implements Section 3.10.4 of the paper:
1. Sample high-salience episodes
2. Compress patterns into schemas/skills
3. Evaluate quality (with semantic embedding novelty)
4. Accept or reject (with evidence verification - P1-8)
5. Prune low-value episodic memories

论文Section 3.10.4要求: "新颖性评估应使用语义嵌入（sentence embeddings）
而非词汇重叠（Jaccard similarity）"
"""
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from common.models import EpisodeRecord
from .episodic import EpisodicMemory
from .schema import SchemaMemory, SchemaEntry
from .skill import SkillMemory, SkillEntry
from .salience import compute_salience

# 修复：添加导入错误处理，如果语义模块不可用则使用回退
try:
    from .semantic_novelty import SemanticNoveltyCalculator
    SEMANTIC_AVAILABLE = True
except ImportError:
    SemanticNoveltyCalculator = None
    SEMANTIC_AVAILABLE = False


@dataclass
class EvidenceConfig:
    """配置证据要求 (P1-8).

    论文 Section 3.10.4:
    "在高风险或高影响规则写入时，推荐要求至少一条 tool_call 或用户确认作为强证据"

    Attributes:
        min_tool_calls: 高影响洞察所需的最小工具调用数量
        min_user_confirmations: 高影响洞察所需的最小用户确认数量
        high_quality_threshold: 高质量洞察的阈值 (Q^insight >= 此值需要证据)
        high_impact_tags: 高影响标签集合
        require_evidence_for_high_quality: 是否对高质量洞察强制要求证据
    """
    min_tool_calls: int = 1
    min_user_confirmations: int = 0
    high_quality_threshold: float = 0.8
    # v15修复: 使用5维核心价值系统
    # integrity → safety, contract → attachment
    high_impact_tags: Set[str] = field(default_factory=lambda: {"safety", "attachment"})
    require_evidence_for_high_quality: bool = True

    @classmethod
    def from_global_config(cls, global_config: Dict[str, Any]) -> 'EvidenceConfig':
        """从全局配置创建 EvidenceConfig (P2-10: 配置化参数)."""
        config = cls()

        if 'evidence' in global_config:
            evidence_cfg = global_config['evidence']

            for key, value in evidence_cfg.items():
                if hasattr(config, key):
                    if key == 'high_impact_tags' and isinstance(value, list):
                        setattr(config, key, set(value))
                    else:
                        setattr(config, key, value)

        return config


class InsightQualityEvaluator:
    """Evaluate insight quality using paper-specified metrics.

    论文Section 3.10.4: 顿悟质量 (Q^insight) 包含三类项:
    1. 压缩性: 是否能把多条经验压缩为一条可复用规则
    2. 可迁移性: 是否能提升后续任务成功率/减少成本
    3. 新颖性: 是否显著不同于已有 schema (使用语义嵌入)
    """

    def __init__(
        self,
        semantic_calculator: Optional[SemanticNoveltyCalculator] = None,
        weights: Optional[Dict[str, float]] = None,
    ):
        """Initialize quality evaluator.

        Args:
            semantic_calculator: For computing semantic novelty
            weights: Weights for each quality dimension
        """
        # 修复：处理SemanticNoveltyCalculator可能不可用的情况
        if SEMANTIC_AVAILABLE:
            self.semantic_calculator = semantic_calculator or SemanticNoveltyCalculator()
        else:
            self.semantic_calculator = None

        # 修复 M14: 统一 insight 质量权重与 insight_quality.py 一致
        self.weights = weights or {
            "compressibility": 0.4,
            "transferability": 0.3,
            "novelty": 0.3,
        }

    def evaluate(
        self,
        insight_claim: str,
        supporting_episodes: List[EpisodeRecord],
        existing_schemas: Optional[List[SchemaEntry]] = None,
    ) -> float:
        """Evaluate insight quality Q^insight.

        论文公式 Section 3.10.4:
        Q^insight = w_comp * Compressibility + w_trans * Transferability + w_nov * Novelty

        Args:
            insight_claim: The insight text to evaluate
            supporting_episodes: Episodes supporting this insight
            existing_schemas: Existing schemas for novelty comparison

        Returns:
            Quality score Q^insight in [0, 1]
        """
        # 1. Compressibility: More supporting episodes = higher compressibility
        compressibility = self._compute_compressibility(supporting_episodes)

        # 2. Transferability: Average reward of supporting episodes
        transferability = self._compute_transferability(supporting_episodes)

        # 3. Novelty: Semantic distance from existing schemas
        novelty = self._compute_semantic_novelty(
            insight_claim,
            existing_schemas or [],
        )

        # Weighted sum
        quality = (
            self.weights["compressibility"] * compressibility +
            self.weights["transferability"] * transferability +
            self.weights["novelty"] * novelty
        )

        return quality

    def _compute_compressibility(self, episodes: List[EpisodeRecord]) -> float:
        """Compute compressibility: how many episodes are compressed into one insight.

        More episodes = better compression (capped at some reasonable max).
        """
        if not episodes:
            return 0.0

        # Use log scaling: compressibility increases with episode count
        # but has diminishing returns
        import math
        return min(1.0, math.log(len(episodes) + 1) / math.log(10))

    def _compute_transferability(self, episodes: List[EpisodeRecord]) -> float:
        """Compute transferability: average reward/success of supporting episodes."""
        if not episodes:
            return 0.0

        avg_reward = sum(ep.reward for ep in episodes) / len(episodes)
        return max(0.0, min(1.0, avg_reward))

    def _compute_semantic_novelty(
        self,
        insight_claim: str,
        existing_schemas: List[SchemaEntry],
    ) -> float:
        """Compute semantic novelty using embeddings.

        论文Section 3.10.4公式:
        C_nov = 1 - max_{s in Schema} cos(emb(insight), emb(s))
        """
        if not existing_schemas:
            return 1.0  # Completely novel if nothing to compare

        # 修复：处理semantic_calculator不可用的情况
        if self.semantic_calculator is None:
            # 回退到简单的字符串比较
            existing_texts = [s.claim for s in existing_schemas]
            # 简单的词汇重叠度作为回退
            claim_words = set(insight_claim.lower().split())
            max_overlap = 0.0
            for existing in existing_texts:
                existing_words = set(existing.lower().split())
                if claim_words or existing_words:
                    overlap = len(claim_words & existing_words) / max(len(claim_words | existing_words), 1)
                    max_overlap = max(max_overlap, overlap)
            return 1.0 - max_overlap

        # Get existing schema texts
        existing_texts = [s.claim for s in existing_schemas]

        # Use semantic novelty calculator
        novelty, _ = self.semantic_calculator.compute_novelty(
            insight_claim,
            existing_texts,
            threshold=0.0,  # Don't filter, return actual score
        )

        return novelty


class DreamConsolidator:
    """Dream-Reflect-Insight consolidation system.

    运行说明 (论文 Section 3.10.4):
    - Compress episodic memories into schemas
    - Extract skills from successful action sequences
    - Prune low-value episodes
    - Evaluate insight quality using semantic embedding novelty
    - P1-8: Verify evidence requirements for high-impact insights
    - 防死循环机制: Cooldown/Attempt/Quality降级
    """

    def __init__(
        self,
        episodic: EpisodicMemory,
        schema: SchemaMemory,
        skill: SkillMemory,
        quality_threshold: float = 0.65,  # Q_min from Appendix A.7
        evidence_config: Optional[EvidenceConfig] = None,
        # 防死循环参数 (论文 Section 3.10.4)
        cooldown_ticks: int = 30,       # T_cooldown: 巩固冷却期
        max_attempts: int = 3,          # N_max: 最大尝试次数
        quality_decay_rate: float = 0.1, # 连续失败时的质量阈值降级率
    ):
        """Initialize consolidator.

        Args:
            episodic: Episodic memory instance
            schema: Schema memory instance
            skill: Skill memory instance
            quality_threshold: Minimum Q^insight to accept (论文默认0.65)
            evidence_config: Evidence requirement configuration (P1-8)
            cooldown_ticks: 巩固冷却期 (论文默认30 ticks)
            max_attempts: 最大尝试次数 (论文默认3次)
            quality_decay_rate: 质量阈值降级率
        """
        self.episodic = episodic
        self.schema = schema
        self.skill = skill
        self.quality_threshold = quality_threshold
        self.initial_quality_threshold = quality_threshold  # 记录初始阈值

        # Quality evaluator with semantic novelty
        self.quality_evaluator = InsightQualityEvaluator()

        # P1-8: 证据要求配置
        self.evidence_config = evidence_config or EvidenceConfig()

        # 防死循环状态
        self.cooldown_ticks = cooldown_ticks
        self.max_attempts = max_attempts
        self.quality_decay_rate = quality_decay_rate

        # 当前状态
        self.current_cooldown = 0
        self.current_attempts = 0
        self.consecutive_failures = 0

    def should_consolidate(self, current_tick: int) -> Tuple[bool, str]:
        """检查是否应该执行巩固.

        防死循环机制 (论文 Section 3.10.4):
        1. Cooldown: 两次巩固之间至少间隔 T_cooldown ticks
        2. Attempt限制: 累计尝试次数不超过 N_max
        3. Quality降级: 连续失败时降低质量阈值

        Args:
            current_tick: 当前tick

        Returns:
            (是否应该巩固, 原因说明)
        """
        # 检查Cooldown
        if self.current_cooldown > 0:
            self.current_cooldown -= 1
            return False, f"Cooldown active ({self.current_cooldown} ticks remaining)"

        # 检查Attempt限制
        if self.current_attempts >= self.max_attempts:
            return False, f"Max attempts reached ({self.max_attempts})"

        # 检查是否需要降级质量阈值
        if self.consecutive_failures >= 2:
            # 降级质量阈值
            decay_amount = self.quality_decay_rate * self.consecutive_failures
            self.quality_threshold = max(
                0.3,  # 最低0.3
                self.initial_quality_threshold - decay_amount
            )
            return True, f"Quality threshold lowered to {self.quality_threshold:.2f} due to {self.consecutive_failures} consecutive failures"

        return True, "Ready to consolidate"

    def record_success(self):
        """记录巩固成功."""
        self.current_attempts = 0
        self.consecutive_failures = 0
        self.current_cooldown = self.cooldown_ticks
        # 恢复初始质量阈值
        self.quality_threshold = self.initial_quality_threshold

    def record_failure(self):
        """记录巩固失败."""
        self.current_attempts += 1
        self.consecutive_failures += 1
        self.current_cooldown = self.cooldown_ticks

    def get_consolidation_state(self) -> Dict[str, Any]:
        """获取巩固系统状态."""
        return {
            "current_cooldown": self.current_cooldown,
            "current_attempts": self.current_attempts,
            "max_attempts": self.max_attempts,
            "consecutive_failures": self.consecutive_failures,
            "quality_threshold": self.quality_threshold,
            "initial_quality_threshold": self.initial_quality_threshold,
        }

    def _check_evidence_requirement(
        self,
        insight_claim: str,
        quality: float,
        episodes: List[EpisodeRecord],
        tags: List[str],
    ) -> Tuple[bool, str]:
        """P1-8: 检查高影响洞察是否满足证据要求.

        论文 Section 3.10.4:
        "在高风险或高影响规则写入时，推荐要求至少一条 tool_call 或用户确认作为强证据"

        Args:
            insight_claim: 洞察文本
            quality: 洞察质量 Q^insight
            episodes: 支持该洞察的episodes
            tags: 洞察标签

        Returns:
            (满足证据要求, 原因说明)
        """
        cfg = self.evidence_config

        # 检查是否需要证据
        needs_evidence = (
            quality >= cfg.high_quality_threshold and cfg.require_evidence_for_high_quality
        ) or any(tag in cfg.high_impact_tags for tag in tags)

        if not needs_evidence:
            return True, "Low/medium quality or low impact - no evidence required"

        # 检查工具调用证据
        tool_call_count = 0
        for ep in episodes:
            if hasattr(ep, 'action') and ep.action:
                # 检查是否有工具调用（除了CHAT/SLEEP等内部动作）
                if ep.action.type and ep.action.type not in ["CHAT", "SLEEP", "REFLECT"]:
                    tool_call_count += 1

        has_tool_evidence = tool_call_count >= cfg.min_tool_calls

        # 检查用户确认证据
        # 检查多种可能的用户反馈字段
        user_confirmation_count = 0
        for ep in episodes:
            # 检查1: user_confirmed字段（布尔值）
            if hasattr(ep, 'user_confirmed') and ep.user_confirmed:
                user_confirmation_count += 1
                continue

            # 检查2: user_rating字段（评分，通常>=3/5表示满意）
            if hasattr(ep, 'user_rating') and ep.user_rating is not None:
                # 假设评分是1-5分，3分以上表示确认
                if ep.user_rating >= 3.0:
                    user_confirmation_count += 1
                    continue

            # 检查3: feedback字段中的积极反馈
            if hasattr(ep, 'feedback') and ep.feedback:
                feedback_lower = str(ep.feedback).lower()
                positive_keywords = ['good', 'correct', 'yes', 'approve', 'confirm', 'ok', '正确', '好', '是']
                if any(keyword in feedback_lower for keyword in positive_keywords):
                    user_confirmation_count += 1
                    continue

            # 检查4: 从outcome中推断用户满意度（成功的action可能表示用户认可）
            if hasattr(ep, 'outcome') and ep.outcome and ep.outcome.ok:
                # 如果action是USE_TOOL且成功，可能表示用户满意
                if hasattr(ep, 'action') and ep.action and ep.action.type == "USE_TOOL":
                    user_confirmation_count += 1

        has_user_evidence = user_confirmation_count >= cfg.min_user_confirmations

        # 判断是否满足证据要求
        # 至少需要一种证据类型满足要求，且当该类型的最小要求大于0时必须有实际证据
        has_evidence = False
        evidence_details = []

        # 检查工具调用证据
        if cfg.min_tool_calls > 0:
            if tool_call_count >= cfg.min_tool_calls:
                has_evidence = True
                evidence_details.append(f"{tool_call_count} tool calls")
            else:
                return False, (
                    f"Insufficient evidence: need {cfg.min_tool_calls} tool calls (got {tool_call_count})"
                )
        else:
            # 工具调用不要求时，如果有工具调用也算作加分
            if tool_call_count > 0:
                evidence_details.append(f"{tool_call_count} tool calls")

        # 检查用户确认证据
        if cfg.min_user_confirmations > 0:
            if user_confirmation_count >= cfg.min_user_confirmations:
                has_evidence = True
                evidence_details.append(f"{user_confirmation_count} user confirmations")
            else:
                return False, (
                    f"Insufficient evidence: need {cfg.min_user_confirmations} user confirmations (got {user_confirmation_count})"
                )
        else:
            # 用户确认不要求时，如果有用户确认也算作加分
            if user_confirmation_count > 0:
                evidence_details.append(f"{user_confirmation_count} user confirmations")

        # 如果两种类型的最低要求都是0，但没有任何证据，仍然应该拒绝
        if not has_evidence and not evidence_details:
            return False, "Insufficient evidence: no tool calls or user confirmations provided"

        # 有至少一种证据满足要求（或两种都有加分）
        if has_evidence:
            reason = f"Evidence verified: {', '.join(evidence_details)}"
            return True, reason
        else:
            # 有加分证据但不满足最低要求，根据是否配置了最低要求来决定
            if cfg.min_tool_calls == 0 and cfg.min_user_confirmations == 0:
                # 两种都不要求，允许通过
                reason = f"Evidence not required (got: {', '.join(evidence_details)})"
                return True, reason
            else:
                # 有一种类型要求大于0但未满足
                return False, f"Insufficient evidence: {', '.join(evidence_details)}"

    def consolidate(
        self,
        current_tick: int,
        budget_tokens: int = 2000,
        salience_threshold: float = 0.6,
    ) -> Dict[str, Any]:
        """Run one consolidation cycle.

        防死循环机制 (论文 Section 3.10.4):
        1. 检查是否应该执行巩固 (should_consolidate)
        2. 如果成功，重置计数器
        3. 如果失败，增加失败计数并触发cooldown

        Args:
            current_tick: Current tick
            budget_tokens: Token budget for this cycle
            salience_threshold: Minimum salience for sampling

        Returns:
            Stats dict with counts of created schemas/skills
        """
        # 检查是否应该执行巩固
        should_run, reason = self.should_consolidate(current_tick)

        if not should_run:
            return {
                "executed": False,
                "reason": reason,
                "consolidation_state": self.get_consolidation_state(),
            }

        stats = {
            "sampled_episodes": 0,
            "schemas_created": 0,
            "skills_created": 0,
            "episodes_pruned": 0,
            "executed": True,
        }

        try:
            # Step 1: Sample high-salience episodes
            candidates = self._sample_episodes(salience_threshold, limit=20)
            stats["sampled_episodes"] = len(candidates)

            if not candidates:
                self.record_failure()
                stats["success"] = False
                stats["reason"] = "No high-salience episodes found"
                stats["consolidation_state"] = self.get_consolidation_state()
                return stats

            # Step 2: Compress into schemas
            new_schemas = self._extract_schemas(candidates, current_tick)
            for schema in new_schemas:
                self.schema.add(schema)
            stats["schemas_created"] = len(new_schemas)

            # Step 3: Extract skills from successful sequences
            new_skills = self._extract_skills(candidates, current_tick)
            for skill in new_skills:
                self.skill.add(skill)
            stats["skills_created"] = len(new_skills)

            # Step 4: Prune low-value episodes (optional, budget-dependent)
            if budget_tokens > 1000:
                pruned = self._prune_episodes(current_tick)
                stats["episodes_pruned"] = pruned

            # 检查是否创建了任何有用的内容
            total_created = stats["schemas_created"] + stats["skills_created"]
            if total_created > 0:
                self.record_success()
                stats["success"] = True
                stats["reason"] = f"Successfully created {total_created} items"
            else:
                self.record_failure()
                stats["success"] = False
                stats["reason"] = "No schemas or skills created"

        except Exception as e:
            self.record_failure()
            stats["success"] = False
            stats["reason"] = f"Error: {str(e)}"
            stats["error"] = str(e)

        stats["consolidation_state"] = self.get_consolidation_state()
        return stats

    def _sample_episodes(self, threshold: float, limit: int) -> List[EpisodeRecord]:
        """Sample high-salience episodes for consolidation.

        Args:
            threshold: Salience threshold
            limit: Maximum episodes to sample

        Returns:
            List of sampled episodes
        """
        all_episodes = self.episodic.get_all()

        # Compute salience for each
        scored = []
        for ep in all_episodes:
            salience = compute_salience(ep)
            if salience >= threshold:
                scored.append((salience, ep))

        # Sort by salience descending
        scored.sort(key=lambda x: x[0], reverse=True)

        # Sample top episodes
        return [ep for _, ep in scored[:limit]]

    def _extract_schemas(
        self,
        episodes: List[EpisodeRecord],
        current_tick: int,
    ) -> List[SchemaEntry]:
        """Extract schema patterns from episodes.

        Enhanced version: uses quality evaluation with semantic novelty.
        P1-8: 添加证据要求验证.

        Args:
            episodes: Episodes to analyze
            current_tick: Current tick

        Returns:
            List of new schemas that pass quality threshold and evidence requirements
        """
        schemas = []

        # Get existing schemas for novelty comparison
        existing_schemas = list(self.schema.get_all())

        # Group by goal
        by_goal: Dict[str, List[EpisodeRecord]] = {}
        for ep in episodes:
            if ep.current_goal:
                if ep.current_goal not in by_goal:
                    by_goal[ep.current_goal] = []
                by_goal[ep.current_goal].append(ep)

        # Create schema for each goal with multiple occurrences
        for goal, goal_episodes in by_goal.items():
            if len(goal_episodes) < 2:
                continue

            # Calculate average reward
            avg_reward = sum(ep.reward for ep in goal_episodes) / len(goal_episodes)

            # Only consider positive experiences
            if avg_reward > 0.3:
                # Generate insight claim
                insight_claim = f"Goal '{goal}' typically yields reward ~{avg_reward:.2f}"

                # Evaluate quality using semantic novelty
                quality = self.quality_evaluator.evaluate(
                    insight_claim=insight_claim,
                    supporting_episodes=goal_episodes,
                    existing_schemas=existing_schemas,
                )

                # Only accept schemas above quality threshold (论文Section 3.10.4)
                if quality >= self.quality_threshold:
                    # P1-8: 检查证据要求
                    tags = ["goal", goal, "strategy", f"quality_{quality:.2f}"]
                    has_evidence, evidence_reason = self._check_evidence_requirement(
                        insight_claim=insight_claim,
                        quality=quality,
                        episodes=goal_episodes,
                        tags=tags,
                    )

                    # 只通过满足证据要求的schema
                    if has_evidence:
                        schema = SchemaEntry(
                            claim=insight_claim,
                            scope="goal_strategy",
                            confidence=min(0.9, len(goal_episodes) / 10.0),
                            evidence_refs=[ep.tick for ep in goal_episodes],
                            supporting_count=len(goal_episodes),
                            conflicting_count=0,
                            created_tick=current_tick,
                            last_updated_tick=current_tick,
                            risk_level=0.1,
                            tags=tags + [f"verified:{evidence_reason}"],
                        )
                        schemas.append(schema)
                    else:
                        # 记录未通过证据验证的schema（用于调试）
                        # TODO: 可以添加到日志中
                        pass

        return schemas

    def _extract_skills(
        self,
        episodes: List[EpisodeRecord],
        current_tick: int,
    ) -> List[SkillEntry]:
        """Extract skills from successful action sequences.

        Simplified version: identifies repeated successful actions.

        Args:
            episodes: Episodes to analyze
            current_tick: Current tick

        Returns:
            List of new skills
        """
        skills = []

        # Group by action type
        by_action: Dict[str, List[EpisodeRecord]] = {}
        for ep in episodes:
            if ep.action and ep.reward > 0.5:  # Only successful actions
                action_type = ep.action.type
                if action_type not in by_action:
                    by_action[action_type] = []
                by_action[action_type].append(ep)

        # Create skill for frequently successful actions
        for action_type, action_episodes in by_action.items():
            if len(action_episodes) < 3:
                continue

            avg_reward = sum(ep.reward for ep in action_episodes) / len(action_episodes)

            if avg_reward > 0.6:
                # Get representative action
                representative_ep = action_episodes[0]
                if not representative_ep.action:
                    continue

                skill = SkillEntry(
                    name=f"skill_{action_type.lower()}",
                    description=f"Execute {action_type} action",
                    action_sequence=[representative_ep.action],
                    success_criteria="reward > 0.5",
                    estimated_cost=representative_ep.cost,
                    risk_level=representative_ep.action.risk_level,
                    capabilities=representative_ep.action.capability_req,
                    invocation_count=len(action_episodes),
                    success_count=len(action_episodes),
                    failure_count=0,
                    average_reward=avg_reward,
                    created_tick=current_tick,
                    evidence_refs=[ep.tick for ep in action_episodes],
                    tags=["action", action_type.lower()],
                )
                skills.append(skill)

        return skills

    def _prune_episodes(self, current_tick: int, keep_recent: int = 100) -> int:
        """Prune low-value episodic memories.

        论文 Section 3.10.4: 删除低显著性情节以保持记忆系统效率

        Args:
            current_tick: Current tick
            keep_recent: Number of recent episodes to always keep

        Returns:
            Number of episodes pruned
        """
        try:
            # Use episodic memory's prune_disk_by_salience method
            # Calculate keep_recent_ratio from keep_recent count
            total_episodes = len(self.episodic._cache)
            if total_episodes == 0:
                return 0

            keep_recent_ratio = min(1.0, keep_recent / max(1, total_episodes))

            # Prune with salience threshold of 0.3 (moderate significance)
            result = self.episodic.prune_disk_by_salience(
                salience_threshold=0.3,
                keep_recent_ratio=keep_recent_ratio,
                backup=True
            )

            pruned_count = result.get('pruned', 0)

            # Clear and reload cache to sync with disk
            if pruned_count > 0 and self.episodic.episodes_path:
                self.episodic._cache.clear()
                self.episodic._by_tick.clear()  # 修复: 使用正确的属性名
                self.episodic._sorted_ticks.clear()
                self.episodic._load_from_disk()

            return pruned_count

        except Exception as e:
            # Log error but don't crash - pruning is not critical
            import logging
            logging.getLogger(__name__).warning(f"Episode pruning failed: {e}")
            return 0
