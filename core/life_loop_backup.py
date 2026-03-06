"""Life Loop - Genesis X production-ready version.

Full integration with:
- core/stores/ (fields/slots/signals/ledger)
- persistence/ (replay engine)
- differentiate (dynamic organ expression)
- Complete tool execution pipeline
- Full safety and budget control
- Affect modulation (情感调制)
- 5维驱动力系统 (5 drive dimensions)
- Evolution engine (进化引擎, 默认关闭)
- Capability gap detection (能力缺口检测)
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime, timezone
import time
import json

# Core imports
from .state import GlobalState
from .tick import TickContext
from .invariants import check_invariants
from .differentiate import select_organs, get_organ_priority

# Store imports
from .stores import FieldStore, SlotStore, SignalBus, MetabolicLedger

# Model imports
from common.models import EpisodeRecord, Action, Observation, CostVector, ValueDimension, ActionType, Outcome
from common.jsonl import JSONLWriter
from common.logger import get_logger

# System modules
from axiology import extract_all_features, compute_gaps, compute_weights, compute_utilities, compute_reward
from affect import ValueFunction, compute_rpe, update_mood
from affect.rpe import RPEComputer, compute_per_dimension_rpe, compute_weighted_rpe
from affect.mood import update_mood_per_dimension
from affect.modulation import AffectModulation  # 情感调制
from memory import EpisodicMemory, SchemaMemory, SkillMemory, MemoryRetrieval, DreamConsolidator
from cognition import GoalCompiler, Planner, PlanEvaluator, Verifier
from metabolism import update_boredom
from affect.stress_affect import update_stress
from metabolism.circadian import CircadianRhythm
from organs import MindOrgan, CaretakerOrgan, ScoutOrgan, BuilderOrgan, ArchivistOrgan, ImmuneOrgan
from tools.tool_registry import ToolRegistry
from tools.capability import CapabilityManager
from safety import check_integrity, assess_risk, check_budget
from perception import observe_environment, build_context
from axiology.weights import WeightUpdater
from axiology.value_learning import ValueLearner, FeedbackSignal, FeedbackType

# 暂时禁用新模块（需要调试）
# from axiology.drives.homeostasis import HomeostasisDrive
# from axiology.drives.attachment import AttachmentDrive
# from axiology.drives.competence import CompetenceDrive
# from axiology.drives.curiosity import CuriosityDrive
# from axiology.drives.safety import SafetyDrive

# 进化系统（自我复制迭代）- 默认禁用（缺少接口实现）
# from .evolution import EvolutionEngine, EVOLUTION_ENABLED

# 成长系统（获取新能力）- 已启用
from .growth import GrowthManager, create_growth_manager

# 能力缺口检测（连接探索和成长）- 已启用
from .capability_gap_detector import CapabilityGapDetector, create_capability_gap_detector

# 新架构：器官系统（整合驱动力）
from organs import OrganManager

logger = get_logger(__name__)


class LifeLoop:
    """Genesis X 核心生命循环 - 完整版

    Features:
    - Complete state management with stores
    - Replay support
    - Dynamic organ differentiation
    - Full safety and budget control
    - Production monitoring
    """

    def __init__(self, config: Dict[str, Any], run_dir: Path, replay_mode: str = None):
        """Initialize GA life loop.

        Args:
            config: Configuration dict
            run_dir: Directory for run artifacts
            replay_mode: Optional replay mode (strict/semantic/fork)
        """
        self.config = config
        self.run_dir = run_dir
        self.replay_mode = replay_mode
        # 使用固定的持久化 session_id，而不是每次重启都创建新的
        # 这样 GenesisX 就是一个长期持续的数字生命，记忆不会因重启而丢失
        self.session_id = config.get("session_id", "genesisx_persistent")

        # Current phase tracking (for Web UI display)
        self._current_phase = "init"

        # Create run directory
        self.run_dir.mkdir(parents=True, exist_ok=True)

        # Initialize state with stores
        self.state = GlobalState()
        self.fields = FieldStore()
        self.slots = SlotStore()
        self.signals = SignalBus()
        self.ledger = MetabolicLedger(
            budgets=config.get("runtime", {}).get("budgets", {})
        )

        self._init_state_from_config()

        # Initialize memories
        episodes_path = self.run_dir / "episodes.jsonl"
        self.episodic = EpisodicMemory(episodes_path)
        self.schema = SchemaMemory()
        self.skill = SkillMemory()
        self.retrieval = MemoryRetrieval(self.episodic, self.schema, self.skill)
        self.consolidator = DreamConsolidator(self.episodic, self.schema, self.skill)

        # 修复: 从历史记录恢复 tick 计数，避免 tick 冲突
        self._restore_tick_from_history()

        # 修复: 从历史记录恢复聊天历史
        self._restore_chat_history()

        # Initialize cognition
        self.goal_compiler = GoalCompiler()
        self.planner = Planner()
        self.evaluator = PlanEvaluator()
        self.verifier = Verifier()

        # Initialize all organs
        self.organs = {
            "caretaker": CaretakerOrgan(),
            "immune": ImmuneOrgan(),
            "mind": MindOrgan(),
            "scout": ScoutOrgan(),
            "builder": BuilderOrgan(),
            "archivist": ArchivistOrgan(),
        }

        # Initialize tools
        self.tool_registry = ToolRegistry()
        # 新增: 动态工具注册表
        from tools.dynamic_tool_registry import get_global_registry, register_skills
        self.dynamic_tool_registry = get_global_registry()

        # 自动发现和注册工具（扫描 tools 目录）
        try:
            tools_dir = Path(__file__).parent.parent / "tools"
            if tools_dir.exists():
                self.dynamic_tool_registry.discover_from_directory(tools_dir)
                stats = self.dynamic_tool_registry.get_stats()
                logger.info(f"动态工具注册表: {stats}")
        except Exception as e:
            logger.warning(f"自动发现工具失败: {e}")

        # 新增: 注册技能系统
        try:
            register_skills(self.dynamic_tool_registry)
            logger.info("技能系统已注册到工具注册表")
        except Exception as e:
            logger.warning(f"注册技能系统失败: {e}")

        self.capability_manager = CapabilityManager()

        # 新增: 器官管理器（新架构 - 整合驱动力系统）
        self.organ_manager = OrganManager()

        # ===== 进化系统（自我复制迭代）- 禁用（缺少接口实现）=====
        self.evolution_system = None
        self.evolution_enabled = False

        # ===== 成长系统（获取新能力）- 已启用 =====
        growth_config = config.get("growth", {})
        self.growth_manager = create_growth_manager(
            organ_manager=self.organ_manager,
            llm_client=None,  # 将在后面设置
            config=growth_config
        )
        self.growth_enabled = growth_config.get("enabled", True)
        if self.growth_enabled:
            logger.info("GrowthManager 已启用 - 可以生成肢体、获取新能力")

        # ===== 能力缺口检测器（连接探索和成长）- 已启用 =====
        gap_detector_config = config.get("capability_gap_detector", {})
        self.gap_detector = create_capability_gap_detector(gap_detector_config)
        self.gap_detection_enabled = gap_detector_config.get("enabled", True)
        if self.gap_detection_enabled:
            # 更新已知能力集合
            try:
                known_caps = set(self.organ_manager.list_all_capabilities())
                self.gap_detector.update_known_capabilities(known_caps)
                logger.info(f"CapabilityGapDetector 已启用 - 已加载 {len(known_caps)} 个已知能力")
            except Exception as e:
                logger.warning(f"Failed to update known capabilities: {e}")
                self.gap_detector.update_known_capabilities(set())

        # Initialize affect
        self.value_function = ValueFunction()
        # 论文3.7.2: 维度级RPE计算器
        self.rpe_computer = RPEComputer()

        # 论文 Section 3.6.4: 权重更新器（含软优先级覆盖）
        self.weight_updater = WeightUpdater(config)
        # 恢复持久化的覆盖状态
        if self.state.override_active:
            override_state = {
                "override_active": self.state.override_active,
                "timestamp": self.state.override_trigger_time
            }
            self.weight_updater.set_override_state(override_state)

        # 论文 Section 3.12: 价值学习器
        self.value_learner = ValueLearner()
        # 恢复持久化的价值参数
        if 'value_parameters' in config:
            self.value_learner.set_parameters(config['value_parameters'])

        # 昼夜节律系统 - 集成代谢周期和优化学习窗口
        circadian_config = config.get("circadian", {})
        self.circadian = CircadianRhythm(circadian_config)

        # ===== 启用情感调制模块 =====
        # 根据心情和压力动态调整行为参数（探索率、计划深度、风险容忍度等）
        modulation_config = config.get("affect_modulation", {})
        self.affect_modulator = AffectModulation(modulation_config)
        logger.info("AffectModulation 已启用 - 将根据情绪状态动态调整行为参数")

        # ===== 模块启用状态 =====
        # 已启用：
        # - 5维驱动力模块 (通过 OrganManager)
        # - AffectModulation (情感调制)
        # - GrowthManager (成长系统)
        # - CapabilityGapDetector (能力缺口检测)
        # 禁用：
        # - EvolutionEngine (进化系统) - 缺少接口实现
        self.drives_enabled = True  # 已通过 OrganManager 启用驱动力系统
        # growth_enabled, gap_detection_enabled 已在上面设置
        # evolution_enabled 已在上面设置

        # User input support (for interactive mode)
        self.get_user_input = None  # Callback function to get user input

        # Caretaker mode tracking (initialized to avoid AttributeError)
        self._caretaker_mode_tick = None

        # Initialize loggers
        # 注意: EpisodicMemory 已经写 episodes.jsonl，这里使用单独的状态日志文件
        # 避免两个 writer 同时写同一个文件导致数据重复或损坏
        self.episode_writer = JSONLWriter(self.run_dir / "states.jsonl")
        self.episode_writer.open()
        self.tool_writer = JSONLWriter(self.run_dir / "tool_calls.jsonl")
        self.tool_writer.open()

        logger.info(f"Initialized session: {self.session_id}")
        logger.info(f"Run directory: {self.run_dir}")
        logger.info(f"Replay mode: {self.replay_mode or 'None (live)'}")

    def _restore_tick_from_history(self):
        """从历史记录恢复 tick 计数，避免重新初始化时 tick 冲突。

        如果 episodes.jsonl 中有记录，将 tick 设置为最后一个记录的 tick + 1。
        这样可以确保新写入的 episode 不会覆盖旧的记录。
        """
        if self.episodic.count() > 0:
            all_episodes = self.episodic.get_all()
            if all_episodes:
                max_tick = max(ep.tick for ep in all_episodes)
                self.state.tick = max_tick + 1
                logger.info(f"Restored tick from history: {self.state.tick} (previous max: {max_tick})")

    def _restore_chat_history(self):
        """从 episodes.jsonl 恢复聊天历史到 SlotStore.

        解析最近的 CHAT 动作，提取用户消息和助手响应，
        恢复到 chat_history slot 中，这样重启后对话上下文不会丢失。
        """
        try:
            if self.episodic.count() > 0:
                all_episodes = self.episodic.get_all()
                if not all_episodes:
                    return

                # 按时间排序，取最近的对话
                all_episodes.sort(key=lambda ep: ep.tick)

                chat_history = []
                for ep in all_episodes:
                    # 检查是否是 CHAT 类型的 action (注意: ActionType.CHAT = "CHAT" 大写)
                    if ep.action and hasattr(ep.action, 'type') and ep.action.type.value == "CHAT":
                        # 从 action.params 中提取用户消息
                        user_msg = None
                        if ep.action.params:
                            user_msg = ep.action.params.get("message") or ep.action.params.get("user_message")

                        if user_msg:
                            chat_history.append({"role": "user", "content": user_msg})

                        # 从 outcome 中提取助手响应
                        # 响应可能在 outcome.status 或 outcome.response 中
                        assistant_msg = None
                        if ep.outcome:
                            if isinstance(ep.outcome, dict):
                                assistant_msg = ep.outcome.get("response") or ep.outcome.get("status")
                            elif hasattr(ep.outcome, 'response'):
                                assistant_msg = ep.outcome.response
                            elif hasattr(ep.outcome, 'status'):
                                assistant_msg = ep.outcome.status

                        if assistant_msg:
                            chat_history.append({"role": "assistant", "content": assistant_msg})

                # 只保留最近 2 条（避免文学风格污染）
                # 历史记录中的冗长响应会训练LLM继续文学风格，减少历史上下文
                if chat_history:
                    chat_history = chat_history[-2:]
                    self.slots.set("chat_history", chat_history)
                    logger.info(f"Restored {len(chat_history)} chat messages from history")
        except Exception as e:
            logger.warning(f"Failed to restore chat history: {e}")

    def _init_state_from_config(self):
        """Initialize state from config."""
        genome = self.config.get("genome", {})
        initial = genome.get("initial_state", {})

        # Load into field store
        self.fields.set("energy", initial.get("energy", 0.8))
        self.fields.set("mood", initial.get("mood", 0.5))
        self.fields.set("stress", initial.get("stress", 0.2))
        self.fields.set("fatigue", initial.get("fatigue", 0.1))
        self.fields.set("bond", initial.get("bond", 0.0))
        self.fields.set("trust", initial.get("trust", 0.5))
        self.fields.set("boredom", initial.get("boredom", 0.0))
        self.fields.set("curiosity", initial.get("curiosity", 0.5))  # 缺失字段

        # 修复: 使用统一的同步方法更新 GlobalState
        self._sync_state_to_global()

        # Load setpoints
        value_config = self.config.get("value_setpoints", {})
        dims = value_config.get("value_dimensions", {})
        for dim_name, dim_config in dims.items():
            try:
                dim = ValueDimension(dim_name)
                self.state.setpoints[dim] = dim_config.get("setpoint", 0.5)
            except ValueError:
                continue

    def run_session(self, max_ticks: int = None):
        """Run a complete session.

        论文 Section 3.13: 增强的异常处理与降级策略

        Args:
            max_ticks: Maximum ticks to run
        """
        if max_ticks is None:
            max_ticks = self.config.get("runtime", {}).get("max_ticks", 100)

        logger.info(f"Starting session for {max_ticks} ticks...")
        logger.debug("=" * 70)

        # 论文 Section 3.13: 异常计数器
        consecutive_errors = 0
        max_consecutive_errors = 3
        disabled_tools = set()

        ticks_executed = 0
        for t in range(max_ticks):
            try:
                episode = self.tick(t)
                self.episode_writer.write(episode.model_dump())
                consecutive_errors = 0  # 重置错误计数器
                ticks_executed = t + 1

                # Print progress
                if t % 10 == 0:
                    self._print_progress(t, episode)

            except KeyboardInterrupt:
                logger.info("Interrupted by user")
                ticks_executed = t + 1
                break

            # 论文 Section 3.13: ToolExecutionError处理
            except Exception as e:
                error_type = type(e).__name__
                error_msg = str(e)
                ticks_executed = t + 1

                consecutive_errors += 1
                logger.error(f"Error at tick {t}: {error_type}: {error_msg}")

                # 根据错误类型进行不同处理
                if "tool" in error_msg.lower() or "Tool" in error_type:
                    # 工具执行错误
                    if consecutive_errors >= max_consecutive_errors:
                        logger.warning("Too many tool errors, disabling risky tools")
                        # 进入管家模式，只响应基本查询
                        self._enter_caretaker_mode()
                        consecutive_errors = 0

                elif "memory" in error_msg.lower() or "Memory" in error_type:
                    # 记忆溢出 - 论文 Section 3.13
                    logger.warning("Memory overflow, triggering emergency consolidation")
                    try:
                        self.consolidator.consolidate(
                            current_tick=t,
                            budget_tokens=5000,
                            salience_threshold=0.4  # 更低阈值，更激进地清理
                        )
                        logger.info("Emergency consolidation completed")
                    except Exception as e2:
                        logger.error(f"Emergency consolidation failed: {e2}")

                elif "value" in error_msg.lower() or "parameter" in error_msg.lower():
                    # 参数越界 - 论文 Section 3.13
                    logger.warning("Parameter drift detected, resetting to safe defaults")
                    self._reset_to_safe_defaults()

                else:
                    # 通用异常处理
                    import traceback as tb
                    logger.error(f"Unexpected error: {tb.format_exc()}")

                    if consecutive_errors >= max_consecutive_errors:
                        logger.warning("Too many errors, entering safe mode")
                        self._enter_caretaker_mode()
                        consecutive_errors = 0

        self._print_summary(ticks_executed)
        self.episode_writer.close()
        self.tool_writer.close()

    def tick(self, t: int) -> EpisodeRecord:
        """Execute one complete tick with full GA integration.

        Args:
            t: Tick number

        Returns:
            EpisodeRecord
        """
        dt = self.config.get("runtime", {}).get("tick_dt", 1.0)
        ctx = TickContext(t=t, dt=dt)
        self.state.tick = t

        # === PHASE 0: Check caretaker mode exit ===
        self._check_exit_caretaker_mode()
        self._current_phase = "caretaker_check"

        # === PHASE 1: Body Update ===
        ctx.advance_phase("body_update")
        self._current_phase = "body_update"
        self._update_body(dt)

        # === PHASE 2: Observe ===
        ctx.advance_phase("observe")
        self._current_phase = "observe"
        field_snapshot = self.fields.snapshot()

        # Get user input if available (for interactive mode)
        user_input = None
        if self.get_user_input is not None:
            user_input = self.get_user_input()

        observations = observe_environment(t, self.state.mode, field_snapshot, user_input)
        for obs in observations:
            ctx.add_observation(obs)

        # === PHASE 3: Retrieve (修复 H2: 集成 MemoryRetrieval) ===
        ctx.advance_phase("retrieve")
        self._current_phase = "retrieve"
        recent_episodes = self.episodic.query_recent(10)

        # 使用 MemoryRetrieval 进行混合检索 (语义 + 近因 + 显著性 + 关键词)
        # 根据观察生成检索标签
        retrieval_tags = []
        query_text = None
        for obs in observations:
            if obs.payload:
                # 从观察中提取关键词作为检索标签
                if "user_input" in obs.payload and obs.payload["user_input"]:
                    query_text = obs.payload["user_input"]
                    retrieval_tags.extend(obs.payload["user_input"].split()[:5])
                if "type" in obs.payload:
                    retrieval_tags.append(obs.payload["type"])
            retrieval_tags.append(obs.type)

        # 检索相关的情节记忆
        retrieved_episodes = []
        if retrieval_tags or query_text:
            retrieved_episodes = self.retrieval.retrieve_episodes(
                query_tags=retrieval_tags,
                current_tick=t,
                limit=10,
                recency_weight=0.3,
                salience_weight=0.4,
                keyword_weight=0.2,
                semantic_weight=0.1 if query_text else 0.0,
                query_text=query_text,
            )

        # 检索相关的 Schema 和 Skill
        retrieved_schemas = self.retrieval.retrieve_schemas(
            query_tags=retrieval_tags, min_confidence=0.5, limit=5
        ) if retrieval_tags else []
        retrieved_skills = self.retrieval.retrieve_skills(
            query_tags=retrieval_tags, min_success_rate=0.5, limit=3
        ) if retrieval_tags else []

        # 合并检索结果
        retrieved = {
            "episodes": retrieved_episodes,
            "schemas": retrieved_schemas,
            "skills": retrieved_skills,
        }

        # === PHASE 4: Build Context ===
        context = build_context(field_snapshot, recent_episodes, retrieved)
        # 添加 observations 到 context，供器官使用
        context["observations"] = ctx.obs_batch

        # === 新增: PHASE 4.5: 驱动力系统 ===
        # 构建驱动力状态，提供给 LLM 理解当前"想要什么"
        drive_state = {
            "gaps": {dim.value: g for dim, g in self.state.gaps.items()},
            "weights": {dim.value: w for dim, w in self.state.weights.items()},
            "mood": self.fields.get("mood"),
            "energy": self.fields.get("energy"),
            "stress": self.fields.get("stress"),
            "fatigue": self.fields.get("fatigue"),
            "boredom": self.fields.get("boredom"),
            "bond": self.fields.get("bond"),
            "trust": self.fields.get("trust"),
        }
        drive_signals = self.organ_manager.get_all_drive_signals(drive_state, context)
        context["drive_signals"] = drive_signals
        context["drives_prompt"] = self.organ_manager.format_drives_for_llm(drive_state, context)

        # === 新增: PHASE 4.6: 进化系统检查 ===
        # 检查是否需要触发自我进化（吞噬新软件）
        # NOTE: EvolutionEngine 尚未实现完整接口，暂时跳过
        try:
            if hasattr(self.evolution_system, 'check_evolution_trigger') and self.evolution_system.check_evolution_trigger(drive_state, context):
                evolution_need = self._identify_evolution_need(context)
                if evolution_need:
                    evolution_success, evolution_msg = self.evolution_system.evolve(
                        evolution_need, drive_state, context
                    )
                    if evolution_success:
                        logger.info(f"进化成功: {evolution_msg}")
                        # 记录进化事件
                        context["evolution_event"] = {
                            "success": True,
                            "message": evolution_msg,
                            "need": evolution_need,
                        }
                    else:
                        logger.warning(f"进化失败: {evolution_msg}")
                        context["evolution_event"] = {
                            "success": False,
                            "message": evolution_msg,
                            "need": evolution_need,
                        }
        except AttributeError as e:
            # EvolutionEngine 接口未完全实现，跳过进化检查
            pass

        # === PHASE 4.7: 成长系统维护 ===
        # 更新已知能力（供后续行为检查使用）
        # 注意：能力缺口检测已移至行为执行前检查 (PHASE 9e)
        if self.gap_detector and self.gap_detection_enabled:
            try:
                known_caps = set(self.organ_manager.list_all_capabilities())
                self.gap_detector.update_known_capabilities(known_caps)
            except Exception as e:
                logger.debug(f"Failed to update known capabilities: {e}")

        # === PHASE 5: Axiology ===
        ctx.advance_phase("axiology")
        self._current_phase = "axiology"
        features = extract_all_features(field_snapshot, context)
        gaps = compute_gaps(features, self.state.setpoints)
        biases = {dim: 1.0 for dim in ValueDimension}

        # 论文 Section 3.6.4: 使用 WeightUpdater 实现软优先级覆盖
        # 修复：直接使用枚举键，避免不必要的字符串转换
        # WeightUpdater.update_weights现在支持枚举键输入并返回字符串键
        updated_weights = self.weight_updater.update_weights(
            current_weights=self.state.weights,
            gaps=gaps,
            biases=biases
        )

        # 转换回枚举键用于后续计算
        weights = {}
        for dim in ValueDimension:
            weights[dim] = updated_weights.get(dim.value, 1.0 / len(ValueDimension))

        utilities = compute_utilities(features, self.state.setpoints)

        self.state.weights = weights
        self.state.gaps = gaps

        # === PHASE 6: Goal Compile (含冲突协调) ===
        ctx.advance_phase("goal_compile")
        self._current_phase = "goal_compile"
        # 论文 Section 3.8.3: 使用多目标协调机制
        multi_goals = self.goal_compiler.compile_multi_goal(
            gaps=gaps,
            weights=weights,
            state=field_snapshot,
            owner="self",
            max_goals=3  # 最多并行3个兼容目标
        )
        # 主目标（最高优先级）
        goal = multi_goals[0] if multi_goals else self.goal_compiler._create_idle_goal()
        self.slots.set("current_goal", goal)
        self.slots.set("active_goals", multi_goals)  # 存储所有活跃目标
        # Convert goal to string for JSON serialization
        context["goal"] = goal.description if hasattr(goal, "description") else str(goal)
        # Keep active_goals as-is for now (used internally, not serialized to LLM)
        context["active_goals"] = multi_goals
        ctx.metadata["num_active_goals"] = len(multi_goals)

        # === PHASE 7: Organ Differentiation & Proposals ===
        ctx.advance_phase("organ_proposals")
        self._current_phase = "organ_proposals"

        # 修复 M10: 检查是否需要推进发育阶段
        from core.differentiate import Differentiator
        diff = Differentiator(self.config.get("genome", {}))
        new_stage = diff.advance_stage(self.state.stage, t)
        if new_stage is not None:
            old_stage = self.state.stage
            self.state.stage = new_stage.value if hasattr(new_stage, 'value') else str(new_stage)
            logger.info(f"Stage advanced: {old_stage} → {self.state.stage} at tick {t}")

        # 传递 stage/mode/signals 给器官分化系统
        genome_with_state = self.config.get("genome", {}).copy()
        genome_with_state["stage"] = self.state.stage
        genome_with_state["mode"] = self.state.mode
        context["signals"] = self.signals.get_all()
        expressed_organs = select_organs(
            genome_with_state,
            field_snapshot,
            context
        )

        # 论文 Section 3.9: 器官选择应该基于价值权重
        # 定义器官与价值维度的映射关系
        # 修复 v14: 使用5维核心价值向量 (论文 Section 3.5.1)
        organ_value_mapping = {
            "caretaker": "homeostasis",   # 管家 → 稳态
            "immune": "safety",           # 免疫 → 安全
            "mind": "competence",         # 思维 → 胜任
            "scout": "curiosity",         # 侦察 → 好奇
            "builder": "competence",      # 建造 → 胜任
            "archivist": "curiosity",     # 档案馆 → 好奇
        }

        # 根据价值权重计算器官优先级
        def organ_priority_by_value(organ_name: str) -> float:
            """计算器官基于价值权重的优先级"""
            # 获取基础优先级（用于平局）
            base_priority = get_organ_priority(organ_name)

            # 获取对应的价值权重
            value_dim = organ_value_mapping.get(organ_name, "competence")
            try:
                dim_enum = ValueDimension(value_dim)
                weight = weights.get(dim_enum, 0.5)
            except ValueError:
                # Invalid dimension name, use default weight
                weight = 0.5

            # 组合：价值权重占70%，基础优先级（反转）占30%
            # 基础优先级越小越高，所以用 10 - priority
            return weight * 0.7 + (10 - base_priority) * 0.03

        proposed_actions = []
        # 按价值驱动优先级排序器官
        sorted_organs = sorted(
            expressed_organs,
            key=organ_priority_by_value,
            reverse=True
        )
        for organ_name in sorted_organs:
            organ = self.organs.get(organ_name)
            if organ and organ.enabled:
                actions = organ.propose_actions(field_snapshot, context)
                proposed_actions.extend(actions)

        # === PHASE 8: Plan Evaluation (含单外部动作强制, 修复 H4) ===
        ctx.advance_phase("plan_evaluate")
        self._current_phase = "plan_evaluate"
        # 论文红线: 每tick至多一个外部动作 (USE_TOOL, CHAT with external)
        # 过滤proposed_actions，确保最多保留一个外部动作
        EXTERNAL_ACTIONS = {ActionType.USE_TOOL, ActionType.CHAT}
        external_actions = [a for a in proposed_actions if a.type in EXTERNAL_ACTIONS]
        internal_actions = [a for a in proposed_actions if a.type not in EXTERNAL_ACTIONS]
        # 只保留第一个外部动作（如果有），与所有内部动作合并
        if len(external_actions) > 1:
            logger.debug(f"H4 enforcement: {len(external_actions)} external actions proposed, keeping only first")
            proposed_actions = internal_actions + [external_actions[0]]

        if proposed_actions:
            # 优先选择 CHAT 动作（用户交互）
            chat_actions = [a for a in proposed_actions if a.type == ActionType.CHAT]
            if chat_actions:
                selected_action = chat_actions[0]
            else:
                # 构建计划列表并评估
                plans = [
                    {"actions": [a], "estimated_reward": 0.5, "estimated_cost": 100.0}
                    for a in proposed_actions
                ]
                budget_utilization = self.ledger.normalize_all()
                # normalize_all() returns utilization (spent/total), so remaining = 1 - utilization
                cpu_remaining_fraction = 1.0 - budget_utilization.get("cpu_tokens", 0.0)
                scored = self.evaluator.evaluate_plans(
                    plans,
                    {dim.value: w for dim, w in weights.items()},
                    cpu_remaining_fraction * 100000
                )
                # 论文 Section 3.9.3: 选择得分最高的计划
                if scored and len(scored) > 0:
                    # scored 是 [(score, plan), ...] 按分数降序排列
                    best_score, best_plan = scored[0]
                    selected_action = best_plan["actions"][0]
                    ctx.metadata["plan_score"] = best_score
                else:
                    selected_action = proposed_actions[0]
        else:
            # 修复: 当没有器官提出动作时，根据当前状态选择合适的默认动作
            # 而不是简单地使用 CHAT 动作
            if self.state.energy < 0.3 or self.state.fatigue > 0.7:
                # 低能量或高疲劳时选择休息
                selected_action = Action(type=ActionType.SLEEP, params={"duration": 5, "reason": "auto_rest"})
            elif self.state.stress > 0.7:
                # 高压力时选择反思
                selected_action = Action(type=ActionType.REFLECT, params={"purpose": "stress_relief", "depth": 1})
            elif self.state.boredom > 0.6:
                # 高无聊时选择探索
                selected_action = Action(type=ActionType.EXPLORE, params={"topic": "auto_stimulation"})
            else:
                # 默认待机状态
                selected_action = Action(type=ActionType.CHAT, params={"message": "Idle - maintaining status"})

        # === PHASE 9: Safety Check (论文 Section 3.13: 完整安全管道) ===
        ctx.advance_phase("safety_check")
        self._current_phase = "safety_check"

        # 9a. 完整性检查
        integrity_ok = check_integrity(selected_action, field_snapshot)
        if not integrity_ok.get("ok", False):
            logger.warning(f"Action blocked by integrity: {integrity_ok.get('reason')}")
            selected_action = Action(type=ActionType.SLEEP, params={"duration": 1})

        # 9b. Verifier 检查 (能力、模式、能量、压力)
        else:
            # 获取当前活跃能力
            active_caps = self.capability_manager.get_active_capabilities(self.state.tick)

            # 构建状态字典用于 Verifier
            verifier_state = {
                "mode": self.state.mode,
                "energy": self.fields.get("energy"),
                "stress": self.fields.get("stress"),
                "mood": self.fields.get("mood"),
            }

            verifier_result = self.verifier.verify_action(
                selected_action,
                verifier_state,
                active_caps
            )

            if not verifier_result.get("ok", True):
                logger.warning(f"Action blocked by verifier: {verifier_result.get('error')}")
                # 根据 verifier 的建议选择替代动作
                if "energy" in verifier_result.get("error", ""):
                    selected_action = Action(type=ActionType.SLEEP, params={"duration": 1, "reason": "low_energy"})
                elif "stress" in verifier_result.get("error", ""):
                    selected_action = Action(type=ActionType.REFLECT, params={"purpose": "stress_relief"})
                else:
                    selected_action = Action(type=ActionType.REFLECT, params={"purpose": "verification_failed"})

        # 9c. 风险评估 (修复 H8: assess_risk 从未调用)
        # 修复 v14: assess_risk 返回 float，需要判断阈值
        if selected_action.type in (ActionType.USE_TOOL, ActionType.EXPLORE):
            risk_score = assess_risk(selected_action, field_snapshot)
            if risk_score > 0.8:  # 高风险阈值
                logger.warning(f"Action blocked by risk: risk_score={risk_score:.2f}")
                selected_action = Action(type=ActionType.REFLECT, params={"purpose": "risk_avoidance"})

        # 9d. 预算检查 (修复 H8: check_budget 从未调用)
        if selected_action.type not in (ActionType.SLEEP, ActionType.REFLECT):
            budget_remaining = {
                name: res.remaining()
                for name, res in self.ledger.resources.items()
            }
            budget_ok = check_budget(selected_action, field_snapshot, budget_remaining)
            if not budget_ok.get("ok", True):
                logger.warning(f"Action blocked by budget: {budget_ok.get('reason')}")
                selected_action = Action(type=ActionType.SLEEP, params={"duration": 1, "reason": "budget_exhausted"})

        # 9e. 能力缺口检查（执行前检查是否拥有所需能力）
        # 这是能力缺口检测的正确定位：作为执行检查，而不是驱动源
        if self.gap_detection_enabled and self.gap_detector and self.growth_enabled:
            capability_gap = self._check_action_capability(selected_action, context)
            if capability_gap:
                logger.info(f"检测到能力缺口: {capability_gap.description}")
                # 触发成长（异步，不影响当前 tick）
                if self.growth_manager:
                    try:
                        from .growth import LimbRequirement, GenerationType
                        requirement = LimbRequirement(
                            name=capability_gap.missing_capability,
                            description=capability_gap.description,
                            capabilities=[capability_gap.missing_capability],
                            generation_type=GenerationType.INTERNAL,
                        )
                        # 记录成长需求，但不阻塞当前行为
                        context["pending_growth_requirement"] = requirement
                        logger.info(f"已记录成长需求: {requirement.name}")
                    except Exception as e:
                        logger.warning(f"创建成长需求失败: {e}")

        # === PHASE 10: Execute ===
        ctx.advance_phase("execute")
        self._current_phase = "execute"

        try:
            outcome = self._execute_action(selected_action, context)
        except Exception as e:
            logger.error(f"[tick] _execute_action raised exception: {e}")
            import traceback
            logger.error(f"[tick] Traceback: {traceback.format_exc()}")
            # 提供默认的 outcome 以防止后续代码崩溃
            outcome = {
                "success": False,
                "ok": False,
                "cost": CostVector(cpu_tokens=50),
                "response": f"执行动作时出错: {str(e)}",
                "error": str(e)
            }

        # 论文红线: 从 MetabolicLedger 扣除实际成本 (修复 H3)
        action_cost = outcome.get("cost", CostVector())
        if action_cost.cpu_tokens > 0:
            self.ledger.spend("cpu_tokens", action_cost.cpu_tokens)
        if action_cost.io_ops > 0:
            self.ledger.spend("io_ops", action_cost.io_ops)
        if action_cost.net_bytes > 0:
            self.ledger.spend("net_bytes", action_cost.net_bytes)
        if action_cost.money > 0:
            self.ledger.spend("money", action_cost.money)
        if action_cost.risk_score > 0:
            self.ledger.spend("risk_score", action_cost.risk_score)

        # 修复 M42: 同步 ledger 资源计数器到 GlobalState (之前这些字段从不更新)
        ledger_snap = self.ledger.snapshot()
        self.state.tokens_used = int(ledger_snap.get("cpu_tokens", {}).get("spent", 0))
        self.state.io_ops = int(ledger_snap.get("io_ops", {}).get("spent", 0))
        self.state.net_bytes = int(ledger_snap.get("net_bytes", {}).get("spent", 0))
        self.state.money_spent = ledger_snap.get("money", {}).get("spent", 0.0)

        # === PHASE 11: Reward & Affect ===
        ctx.advance_phase("reward_affect")
        self._current_phase = "reward_affect"

        # 基础 reward（基于 utilities 和 weights）
        reward = compute_reward(utilities, weights, outcome.get("cost", CostVector()))

        # 修复: 成功的 CHAT 动作应该产生正向奖励
        # 直接添加 reward bonus 而不是调整 utilities
        if outcome.get("success") and outcome.get("ok"):
            # CHAT 成功：添加足够大的正向奖励来抵消负效用
            # 即使 utilities 是负的，这个 bonus 也能让整体 reward 变正
            reward += 0.2  # 固定的正向奖励，足够大以产生正 RPE

        value_current = self.value_function.get()
        # 论文 Appendix A.5: V(S_t) ← (1-α_V)V(S_t) + α_V(r_t + γV(S_{t+1}))
        # 修复 H20: update() 现在使用 TD target = r_t + γV(S_{t+1})
        self.value_function.update(reward, value_next=value_current)  # bootstrap
        value_next = self.value_function.get()
        delta = compute_rpe(reward, value_current, value_next)

        # 论文3.7.2: 计算维度级RPE
        # 修复: 成功的 CHAT 动作应该产生正向的 attachment/competence RPE
        utilities_str = {dim.value: u for dim, u in utilities.items()}
        rpe_result = self.rpe_computer.compute(
            utilities=utilities_str,
            weights={dim.value: w for dim, w in weights.items()},
        )
        delta_per_dim = rpe_result["per_dimension"]

        # === 关键修复: 成功的 CHAT 动作强制产生正向情绪 ===
        # 直接修正 delta_per_dim，而不是 utilities
        if outcome.get("success") and outcome.get("ok"):
            # 覆盖 attachment 和 competence 的 RPE 为正值
            # 这会让 mood 上升，stress 下降
            delta_per_dim["attachment"] = abs(delta_per_dim.get("attachment", 0.0)) + 0.05
            delta_per_dim["competence"] = abs(delta_per_dim.get("competence", 0.0)) + 0.03

        # Update fields via store - 使用维度级RPE更新情绪
        new_mood = update_mood_per_dimension(self.fields.get("mood"), delta_per_dim)
        self.fields.set("mood", new_mood)
        self.state.mood = new_mood  # 同步到 GlobalState

        # 更新 Stress：使用 affect/stress_affect.update_stress
        # 该函数已包含 RPE 影响、失败惩罚、自然衰减等所有逻辑
        failed = not outcome.get("success", True)
        current_stress = self.fields.get("stress")
        new_stress = update_stress(current_stress, delta, failed)
        self.fields.set("stress", new_stress)
        self.state.stress = new_stress  # 同步到 GlobalState

        # === AffectModulation: 根据情绪状态调整行为参数 ===
        if self.affect_modulator:
            modulated_params = self.affect_modulator.get_modulated_params(
                mood=new_mood,
                stress=new_stress
            )
            # 将调制后的参数存入 context 供后续使用
            context["modulated_params"] = modulated_params
            # 检查是否应该触发反思
            meaning_gap = gaps.get(ValueDimension.CURIOSITY, 0.0) if gaps else 0.0
            boredom = self.fields.get("boredom", 0.0)
            if self.affect_modulator.should_trigger_reflection(new_stress, meaning_gap, boredom):
                context["trigger_reflection"] = True
                logger.debug(f"AffectModulation: 触发反思 (stress={new_stress:.2f}, boredom={boredom:.2f})")

        # === 处理待定的成长需求 ===
        # 如果在行为执行前检测到能力缺口，这里触发成长
        pending_growth = context.get("pending_growth_requirement")
        if pending_growth and self.growth_manager and self.growth_enabled:
            try:
                success, limb = self.growth_manager.generate_limb(pending_growth)
                if success:
                    logger.info(f"成长成功: {limb.name}")
                    context["growth_event"] = {
                        "type": "limb_generated",
                        "description": f"生成了新肢体: {limb.name}",
                        "capabilities": limb.capabilities,
                    }
                # 清除待定需求
                del context["pending_growth_requirement"]
            except Exception as e:
                logger.warning(f"Growth generation failed: {e}")

        # Decay signals
        self.signals.tick(dt)

        # === PHASE 12: Memory Write ===
        ctx.advance_phase("memory_write")
        self._current_phase = "memory_write"
        # Convert outcome dict to Outcome object if needed
        from common.models import Outcome
        outcome_obj = None
        if outcome.get("ok", outcome.get("success", True)):
            outcome_obj = Outcome(
                ok=outcome.get("ok", outcome.get("success", True)),
                status=outcome.get("response", ""),  # Use status field to store LLM response
                tool_output_ref=outcome.get("tool_output_ref"),
                cost_vector=outcome.get("cost", CostVector()),
                evidence_refs=outcome.get("evidence_refs", []),
                major_error=not outcome.get("ok", outcome.get("success", True)),
                error_message=outcome.get("error_message"),
            )

        episode = EpisodeRecord(
            tick=t,
            session_id=self.session_id,
            observation=observations[0] if len(observations) > 0 else None,
            action=selected_action,
            outcome=outcome_obj,
            reward=reward,
            delta=delta,
            delta_per_dim=delta_per_dim,  # 论文3.10.2: 记录维度级RPE
            value_pred=value_current,
            state_snapshot=self.fields.snapshot(),
            weights={dim.value: w for dim, w in weights.items()},
            gaps={dim.value: g for dim, g in gaps.items()},
            utilities={dim.value: u for dim, u in utilities.items()},
            current_goal=goal.description if hasattr(goal, 'description') else str(goal),
            cost=outcome.get("cost", CostVector()),
        )

        # 修复: 确保日志记录 episode 保存情况
        logger.debug(f"Tick {t}: Saving episode to {self.episodic.episodes_path}")
        try:
            self.episodic.append(episode)
            logger.debug(f"Tick {t}: Episode appended, cache size: {self.episodic.count()}")
        except Exception as e:
            logger.error(f"Tick {t}: Failed to append episode: {e}")
        self.state.episodic_count += 1
        logger.debug(f"Tick {t}: Episode saved, total count: {self.state.episodic_count}")

        # === PHASE 13: Invariants ===
        ctx.advance_phase("invariants")
        self._current_phase = "invariants"
        checks = check_invariants(self.state, weights, self.ledger.normalize_all(), [selected_action])
        if not all(checks.values()):
            logger.warning(f"Invariant violations: {[k for k, v in checks.items() if not v]}")

        # === PHASE 14: Value Learn (论文 Section 3.12) ===
        ctx.advance_phase("value_learn")
        self._current_phase = "value_learn"
        if self.state.value_learning_enabled:
            # 添加维度级RPE作为内在反馈信号
            current_time = time.time()
            # 找出RPE最大的维度作为活跃维度
            max_rpe_dim = max(delta_per_dim.items(), key=lambda x: abs(x[1]))[0] if delta_per_dim else "homeostasis"
            self.value_learner.add_rpe_signal(delta, max_rpe_dim, current_time)

            # 检查是否需要更新价值参数 (skip tick 0, guard zero division)
            if self.state.value_learning_interval > 0 and t > 0 and t % self.state.value_learning_interval == 0:
                if self.value_learner.should_update(current_time):
                    old_params = self.value_learner.get_parameters()
                    updated = self.value_learner.update(current_time)
                    if updated:
                        new_params = self.value_learner.get_parameters()
                        logger.info("Updated value parameters:")
                        logger.debug(f"  Old setpoints: {old_params.setpoints}")
                        logger.debug(f"  New setpoints: {new_params.setpoints}")
                        # 更新状态中的设定点
                        for dim_name, setpoint in new_params.setpoints.items():
                            try:
                                dim = ValueDimension(dim_name)
                                self.state.setpoints[dim] = setpoint
                            except ValueError:
                                pass
                        self.state.last_value_learning_tick = t

        # === PHASE 15: Sleep/Reflect Trigger (论文 Section 3.13) ===
        ctx.advance_phase("sleep_reflect_trigger")
        self._current_phase = "sleep_reflect_trigger"
        # 触发条件：高疲劳 or 低能量 or 高好奇缺口 (修复 v14: 使用5维)
        fatigue = self.fields.get("fatigue")
        energy = self.fields.get("energy")
        # 使用 state.gaps 而不是局部变量 gaps
        curiosity_gap = self.state.gaps.get(ValueDimension.CURIOSITY, 0.0)
        homeostasis_gap = self.state.gaps.get(ValueDimension.HOMEOSTASIS, 0.0)

        should_consolidate = (
            fatigue > 0.7 or  # 高疲劳
            energy < 0.3 or  # 低能量
            curiosity_gap > 0.6 or  # 高好奇需求 (反思学习)
            homeostasis_gap > 0.6  # 高稳态需求
        )

        if should_consolidate and self.episodic.count() >= 10:
            # 运行梦境巩固
            stats = self.consolidator.consolidate(
                current_tick=t,
                budget_tokens=2000,
                salience_threshold=0.6
            )
            # 做梦后重置活动疲劳度（"睡了一觉，精神焕发"）
            self.state.reset_activity_fatigue(amount=1.0)
            if stats.get("schemas_created", 0) > 0 or stats.get("skills_created", 0) > 0:
                logger.info(f"Consolidation: Schemas={stats['schemas_created']}, Skills={stats['skills_created']}")

        # === PHASE 16: Persist Override State (论文 Section 3.6.4) ===
        ctx.advance_phase("persist_override")
        self._current_phase = "persist_override"
        # 持久化优先级覆盖状态
        override_state = self.weight_updater.get_override_state()
        if override_state.get("override_active"):
            self.state.override_active = override_state["override_active"]
            # 使用实际的覆盖触发时间，而非当前时间
            self.state.override_trigger_time = override_state.get("timestamp", 0.0) or datetime.now(timezone.utc).timestamp()
            # 记录触发时的缺口
            self.state.gaps_at_trigger = {dim.value: g for dim, g in gaps.items()}

        return episode

    def _sync_state_to_global(self, fields: Dict[str, float] = None):
        """同步 FieldStore 到 GlobalState (修复代码重复问题).

        Args:
            fields: 可选的字段字典，如果为 None 则从 FieldStore 读取所有字段
        """
        if fields is None:
            # 从 FieldStore 读取所有字段并同步
            self.state.energy = self.fields.get("energy")
            self.state.mood = self.fields.get("mood")
            self.state.stress = self.fields.get("stress")
            self.state.fatigue = self.fields.get("fatigue")
            self.state.bond = self.fields.get("bond")
            self.state.trust = self.fields.get("trust")
            self.state.boredom = self.fields.get("boredom")
        else:
            # 同步指定的字段
            for key, value in fields.items():
                if hasattr(self.state, key):
                    setattr(self.state, key, value)

    def _sync_fields_to_global(
        self, energy: float = None, fatigue: float = None, stress: float = None,
        boredom: float = None, mood: float = None, bond: float = None, trust: float = None
    ):
        """同步指定字段到 GlobalState (修复代码重复问题).

        Args:
            energy, fatigue, stress, boredom, mood, bond, trust: 要同步的字段值
        """
        if energy is not None:
            self.fields.set("energy", energy)
            self.state.energy = energy
        if fatigue is not None:
            self.fields.set("fatigue", fatigue)
            self.state.fatigue = fatigue
        if stress is not None:
            self.fields.set("stress", stress)
            self.state.stress = stress
        if boredom is not None:
            self.fields.set("boredom", boredom)
            self.state.boredom = boredom
        if mood is not None:
            self.fields.set("mood", mood)
            self.state.mood = mood
        if bond is not None:
            self.fields.set("bond", bond)
            self.state.bond = bond
        if trust is not None:
            self.fields.set("trust", trust)
            self.state.trust = trust

    def _update_body(self, dt: float):
        """Update body state with metabolism and circadian rhythm.

        论文 Appendix A.3: η-coefficient body dynamics.
        论文v4修正#2: Body Phase 产生 Stress^mid, Affect Phase 在上面叠加 RPE.
        """
        energy = self.fields.get("energy")
        fatigue = self.fields.get("fatigue")
        stress = self.fields.get("stress")
        boredom = self.fields.get("boredom")

        # 获取昼夜节律调整系数
        circadian_energy = self.circadian.get_energy_level()
        recovery_rate = self.circadian.get_fatigue_recovery_rate()

        # 论文 v14: Energy_t 和 Fatigue_t 已被数字原生模型替代
        # 使用简化的昼夜节律调制版本
        new_energy = energy * 0.9 + circadian_energy * 0.1
        # 疲劳自然恢复（简化）
        new_fatigue = max(0.0, fatigue - 0.05 * dt * recovery_rate)

        # Stress 更新移至 Affect Phase，这里保持当前值不变
        new_boredom = update_boredom(boredom, dt)

        # 疲劳恢复率受昼夜节律影响
        if new_fatigue < fatigue:
            recovery_amount = fatigue - new_fatigue
            recovery_amount *= recovery_rate
            new_fatigue = fatigue - recovery_amount

        # 同步状态; Stress 将在 Affect Phase 更新
        self._sync_fields_to_global(
            energy=new_energy,
            fatigue=new_fatigue,
            stress=stress,  # 保持当前值，Affect Phase 会更新
            boredom=new_boredom
        )

    def _execute_action(self, action: Action, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute action with full pipeline (修复 H1: 实际工具调用).

        论文 Section 3.13 Algorithm 1 Step 11: Execute
        - 每tick至多一个外部动作 (H4 已在 Phase 8 强制)
        - 所有动作的成本通过 MetabolicLedger 跟踪 (H3)
        - 工具调用通过 ToolRegistry 和 CapabilityManager 管控 (H6)

        Args:
            action: Action to execute
            context: Current execution context (包含检索到的记忆)

        Returns:
            Dict with "success", "cost", and optional "result"
        """
        logger.info(f"[_execute_action] Starting: action.type={action.type}")
        start_time = time.time()

        if action.type == ActionType.SLEEP:
            # 睡眠: 恢复能量和疲劳
            duration = action.params.get("duration", 1)
            energy = self.fields.get("energy")
            fatigue = self.fields.get("fatigue")
            # 恢复量与duration成正比
            recovery_factor = min(duration, 10) / 10.0
            new_energy = min(1.0, energy + 0.1 * recovery_factor)
            new_fatigue = max(0.0, fatigue - 0.2 * recovery_factor)
            self._sync_fields_to_global(energy=new_energy, fatigue=new_fatigue)
            return {"success": True, "cost": CostVector()}

        elif action.type == ActionType.EXPLORE:
            # 探索: 减少无聊，消耗能量
            boredom = self.fields.get("boredom")
            energy = self.fields.get("energy")
            new_boredom = max(0.0, boredom - 0.15)
            new_energy = max(0.0, energy - 0.02)
            self._sync_fields_to_global(boredom=new_boredom, energy=new_energy)
            cost = CostVector(cpu_tokens=200)
            self._log_tool_call(action, {"success": True}, cost)
            return {"success": True, "cost": cost}

        elif action.type == ActionType.REFLECT:
            # 反思: 减少压力，消耗少量能量
            stress = self.fields.get("stress")
            new_stress = max(0.0, stress - 0.05)
            self._sync_fields_to_global(stress=new_stress)
            cost = CostVector(cpu_tokens=100)
            return {"success": True, "cost": cost}

        elif action.type == ActionType.CHAT:
            # 聊天: 通过 ToolRegistry 调用 LLM
            logger.info(f"[CHAT] Executing CHAT action, context provided: {context is not None}")
            # 论文 Section 3.11: CHAT 动作应完整执行 LLM 调用

            # 确保 action.params 不为 None
            if action.params is None:
                action.params = {}

            # 获取当前可用能力（需要在 tool_spec 检查之前获取，因为后面的代码也会用到）
            active_caps = self.capability_manager.get_active_capabilities(self.state.tick)

            tool_id = "qianwen_chat"
            tool_spec = self.tool_registry.get(tool_id)

            # 检查能力权限
            if tool_spec:
                required_caps = tool_spec.capabilities_required
                if not all(cap in active_caps for cap in required_caps):
                    logger.warning(f"CHAT action missing capabilities: {required_caps}")
                    return {"success": False, "cost": CostVector(), "reason": "missing_capabilities"}

                # 获取用户消息（优先从 user_message，其次从 message）
                user_message = action.params.get("user_message", "") or action.params.get("message", "")
                if not user_message:
                    # 如果没有指定消息，根据当前状态生成问候
                    user_message = self._generate_contextual_greeting()

                # 检测肢体生成请求（暂时返回友好消息）
                if any(kw in user_message for kw in ["生成", "肢体", "器官", "功能"]):
                    # 检测是否是生成肢体/器官的请求
                    if any(kw in user_message for kw in ["肢体", "器官", "能力"]):
                        # 直接返回结果，让后续代码正常处理
                        response_text = "我目前不能自主生成新的肢体或器官。这需要更高级的进化功能。你可以通过配置文件添加工具，或直接使用已有的工具（如 read_file, write_file, web_search 等）。"
                        cost = CostVector(cpu_tokens=100, money=0.0001)
                        return {
                            "success": True,
                            "response": response_text,
                            "cost": cost,
                            "ok": True
                        }

                # 将用户消息添加到 context 用于记忆检索
                context["user_message"] = user_message

                # 构建系统提示词（包含检索到的记忆）
                system_prompt = self._build_chat_system_prompt_with_memory(context)

                # 获取聊天历史（限制为最近2轮，避免文学风格污染）
                # 历史记录包含之前的冗长响应，会训练LLM继续文学风格
                chat_history = self._get_chat_history(limit=2)

                # 预估成本
                estimated_tokens = len(system_prompt) + len(user_message) + sum(len(h.get("content", "")) for h in chat_history)
                estimated_tokens = max(1000, estimated_tokens)  # 最少1000 tokens

                cost = CostVector(
                    cpu_tokens=estimated_tokens,
                    money=estimated_tokens * 0.000001,  # 每 token 约 0.001 元
                )

                # 预算预检: 预留资源
                can_afford = self.ledger.can_reserve("cpu_tokens", cost.cpu_tokens)
                if not can_afford:
                    logger.warning("CHAT action: insufficient cpu_tokens budget")
                    return {"success": False, "cost": CostVector(), "reason": "budget_exceeded"}

                # 实际调用 LLM
                try:
                    import os
                    llm_mode = os.environ.get('LLM_MODE', 'single')
                    logger.info(f"[CHAT] Starting LLM call with mode: {llm_mode}, user_message: {user_message[:50]}...")

                    # === 定义可用工具 (Function Calling 格式) ===
                    # 优先使用动态工具注册表（支持热加载和更多工具）
                    if hasattr(self, 'dynamic_tool_registry'):
                        tools = self.dynamic_tool_registry.to_llm_format()
                        logger.debug(f"使用动态工具注册表，共 {len(tools)} 个工具")
                    else:
                        # 降级到硬编码工具定义
                        tools = None
                        if "file_system" in active_caps:
                            tools = [
                                {
                                    "type": "function",
                                    "function": {
                                        "name": "list_directory",
                                        "description": "列出指定目录下的所有文件和子目录。",
                                        "parameters": {
                                            "type": "object",
                                            "properties": {
                                                "path": {"type": "string", "description": "目录路径"}
                                            },
                                            "required": ["path"]
                                        }
                                    }
                                },
                                {
                                    "type": "function",
                                    "function": {
                                        "name": "read_file",
                                        "description": "读取文件内容",
                                        "parameters": {
                                            "type": "object",
                                            "properties": {
                                                "path": {"type": "string", "description": "文件路径"}
                                            },
                                            "required": ["path"]
                                        }
                                    }
                                },
                                {
                                    "type": "function",
                                    "function": {
                                        "name": "write_file",
                                        "description": "写入文件内容",
                                        "parameters": {
                                            "type": "object",
                                            "properties": {
                                                "path": {"type": "string", "description": "文件路径"},
                                                "content": {"type": "string", "description": "文件内容"}
                                            },
                                            "required": ["path", "content"]
                                        }
                                    }
                                }
                            ]

                    # === 两轮 Function Calling 实现 ===
                    # 第一轮：发送用户消息，可能获得 tool_calls
                    messages = chat_history + [{"role": "user", "content": user_message}]

                    max_rounds = 3  # 最多 3 轮（防止无限循环）
                    llm_response = ""
                    actual_tokens = 0

                    # 在循环外初始化 LLM 客户端（避免第二轮作用域问题）
                    if llm_mode == 'single':
                        from tools.llm_client import LLMClient
                        llm_config = self.config.get("llm", {})
                        logger.info(f"[CHAT] LLM config: api_base={llm_config.get('api_base', 'NOT_SET')[:50]}, model={llm_config.get('model', 'NOT_SET')}")
                        llm_client = LLMClient(llm_config)
                    else:
                        # 多模型模式 (core5/full7/adaptive)
                        from tools.llm_orchestrator import LLMMOrchestrator
                        orchestrator = LLMMOrchestrator(
                            config_mode=llm_mode,
                            config=self.config.get("llm", {})
                        )

                    for round_num in range(max_rounds):
                        logger.info(f"[CHAT] Round {round_num + 1}/{max_rounds}, calling LLM...")
                        try:
                            if llm_mode == 'single':
                                response = llm_client.chat(
                                    system_prompt=system_prompt,
                                    messages=messages,
                                    temperature=0.1,  # 低温度获得简洁、准确的响应
                                    max_tokens=2000,
                                    tools=tools,
                                )
                            else:
                                response = orchestrator.chat(
                                    messages=messages,
                                    system_prompt=system_prompt,
                                    temperature=0.1,  # 低温度获得简洁、准确的响应
                                    max_tokens=2000,
                                    tools=tools,
                                )

                            logger.info(f"[CHAT] LLM response received: {list(response.keys())[:5]}")

                            # 检查 LLM 调用是否失败
                            if not response.get("ok", True):
                                error_msg = response.get("error", "Unknown error")
                                logger.error(f"[CHAT] LLM call failed: {error_msg}")
                                llm_response = f"抱歉，LLM 调用失败: {error_msg}"
                                logger.info(f"[CHAT] Set llm_response to error message and breaking")
                                break

                            round_response = response.get("text", response.get("content", ""))
                            tool_calls = response.get("tool_calls", [])
                            actual_tokens += response.get("total_tokens", estimated_tokens)

                            logger.info(f"[CHAT] Round {round_num + 1}: round_response length={len(round_response)}, tool_calls={len(tool_calls)}")

                            # 如果没有工具调用，这就是最终响应
                            if not tool_calls:
                                llm_response = round_response
                                logger.info(f"[CHAT] No tool calls, final llm_response length={len(llm_response)}")
                                break
                        except Exception as llm_err:
                            logger.error(f"[CHAT] LLM call error in round {round_num + 1}: {llm_err}")
                            import traceback
                            logger.error(f"[CHAT] Traceback: {traceback.format_exc()}")
                            llm_response = f"抱歉，我在处理请求时遇到了错误: {str(llm_err)}"
                            break

                        # === 执行工具调用（支持并行、验证、重试） ===
                        if hasattr(self, 'tool_executor') and self.tool_executor:
                            # 添加 assistant 的工具调用消息
                            messages.append({
                                "role": "assistant",
                                "content": round_response or "",
                                "tool_calls": tool_calls
                            })

                            # 并行执行工具（使用 concurrent.futures）
                            import concurrent.futures
                            import json as json_module

                            tool_results = []

                            def execute_single_tool(tc):
                                """执行单个工具，带错误处理和重试"""
                                func = tc.get("function", {})
                                tool_name = func.get("name", "")
                                tool_call_id = tc.get("id", "")

                                try:
                                    arguments = json_module.loads(func.get("arguments", "{}"))
                                except json_module.JSONDecodeError:
                                    return {
                                        "tool_call_id": tool_call_id,
                                        "tool_name": tool_name,
                                        "success": False,
                                        "content": f"错误: 无效的 JSON 参数"
                                    }

                                # 带重试的执行（最多3次）
                                max_retries = 2
                                last_error = None

                                for attempt in range(max_retries + 1):
                                    try:
                                        # 优先使用动态工具注册表
                                        if hasattr(self, 'dynamic_tool_registry'):
                                            try:
                                                tool_def = self.dynamic_tool_registry.get(tool_name)
                                                if tool_def:
                                                    # 使用动态注册表的处理器
                                                    result = tool_def.handler(**arguments)
                                                    tool_result = {"success": True, "result": str(result)}
                                                else:
                                                    # 降级到 tool_executor
                                                    tool_result = self.tool_executor.execute(tool_name, arguments)
                                            except Exception as e:
                                                tool_result = {"success": False, "error": str(e)}
                                        else:
                                            tool_result = self.tool_executor.execute(tool_name, arguments)

                                        # 验证工具结果
                                        if tool_result.get("success"):
                                            result_text = tool_result.get("result", "")

                                            # 基本验证：检查结果是否为空或错误
                                            if not result_text or result_text.strip() == "":
                                                return {
                                                    "tool_call_id": tool_call_id,
                                                    "tool_name": tool_name,
                                                    "success": True,
                                                    "content": "(工具返回空结果)",
                                                    "validated": False
                                                }

                                            return {
                                                "tool_call_id": tool_call_id,
                                                "tool_name": tool_name,
                                                "success": True,
                                                "content": f"成功: {result_text}",
                                                "validated": True
                                            }
                                        else:
                                            last_error = tool_result.get("error", "未知错误")
                                            # 最后一次尝试失败
                                            if attempt == max_retries:
                                                return {
                                                    "tool_call_id": tool_call_id,
                                                    "tool_name": tool_name,
                                                    "success": False,
                                                    "content": f"失败: {last_error}",
                                                    "retries": attempt
                                                }

                                    except Exception as e:
                                        last_error = str(e)
                                        if attempt == max_retries:
                                            return {
                                                "tool_call_id": tool_call_id,
                                                "tool_name": tool_name,
                                                "success": False,
                                                "content": f"异常: {last_error}",
                                                "retries": attempt
                                            }

                                return {
                                    "tool_call_id": tool_call_id,
                                    "tool_name": tool_name,
                                    "success": False,
                                    "content": f"失败: {last_error}"
                                }

                            # 并行执行所有工具
                            with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(tool_calls), 5)) as executor:
                                futures = {executor.submit(execute_single_tool, tc): tc for tc in tool_calls}

                                for future in concurrent.futures.as_completed(futures):
                                    try:
                                        result = future.result(timeout=30)  # 30秒超时
                                        tool_results.append(result)
                                    except concurrent.futures.TimeoutError:
                                        tc = futures[future]
                                        tool_results.append({
                                            "tool_call_id": tc.get("id", ""),
                                            "tool_name": tc.get("function", {}).get("name", "unknown"),
                                            "success": False,
                                            "content": "超时: 工具执行超过30秒"
                                        })
                                    except Exception as e:
                                        tc = futures[future]
                                        tool_results.append({
                                            "tool_call_id": tc.get("id", ""),
                                            "tool_name": tc.get("function", {}).get("name", "unknown"),
                                            "success": False,
                                            "content": f"异常: {str(e)}"
                                        })

                            # 按原始 tool_calls 顺序添加结果到消息历史
                            for tc in tool_calls:
                                tool_call_id = tc.get("id", "")
                                # 找到对应的结果
                                result = next((r for r in tool_results if r.get("tool_call_id") == tool_call_id), None)

                                if result:
                                    messages.append({
                                        "role": "tool",
                                        "tool_call_id": tool_call_id,
                                        "content": result.get("content", "")
                                    })
                                else:
                                    # 没有找到结果，添加默认错误
                                    messages.append({
                                        "role": "tool",
                                        "tool_call_id": tool_call_id,
                                        "content": "错误: 工具执行结果丢失"
                                    })

                            # 记录工具调用统计
                            successful = sum(1 for r in tool_results if r.get("success"))
                            logger.info(f"工具调用完成: {successful}/{len(tool_calls)} 成功")

                            # 继续下一轮，让 LLM 根据工具结果生成最终响应
                            continue
                except Exception as e:
                    logger.error(f"[CHAT] Exception in LLM call: {e}")
                    import traceback
                    logger.error(f"[CHAT] Traceback: {traceback.format_exc()}")
                    # 降级: 返回简单响应
                    fallback_response = "我在尝试回应，但遇到了一些问题。请再试一次。"
                    logger.info(f"[CHAT] Returning fallback response due to exception")
                    return {"success": False, "ok": False, "cost": cost, "tool_id": tool_id, "response": fallback_response, "error": str(e)}

                # === for 循环之后的代码 ===
                logger.info(f"[CHAT] After for loop: llm_response length={len(llm_response)}, content='{llm_response[:100] if llm_response else '(empty)'}'")

                # === 处理文本中嵌入的工具调用（降级方案）===
                logger.info(f"[CHAT] Before tool check: llm_response length={len(llm_response)}")
                # 如果 LLM 没有使用 Native Function Calling，检查文本中是否有工具调用
                if not llm_response or ("TOOL:" in llm_response or "tool_code" in llm_response):
                    logger.info(f"[CHAT] Entering tool call processing")
                    import re
                    tools_executed = False

                    # 检查 TOOL: 格式
                    if "TOOL:" in llm_response and hasattr(self, 'tool_executor') and self.tool_executor:
                        tool_match = re.search(r'TOOL:\s*(\w+)', llm_response)
                        if tool_match:
                            tool_name = tool_match.group(1)
                            params = {}

                            # 提取 PATH 参数
                            path_match = re.search(r'PATH:\s*(.+?)(?:\n|$)', llm_response)
                            if path_match:
                                params["path"] = path_match.group(1).strip()

                            # 提取 CODE 参数
                            code_match = re.search(r'CODE:\s*(.+?)(?:```\n|$)', llm_response, re.DOTALL)
                            if code_match:
                                params["code"] = code_match.group(1).strip()

                            # 提取 CONTENT 参数 (用于写文件)
                            content_match = re.search(r'CONTENT:\s*(.+?)(?:TOOL:|\Z)', llm_response, re.DOTALL)
                            if content_match:
                                params["content"] = content_match.group(1).strip()

                            # 执行工具
                            try:
                                tool_result = self.tool_executor.execute(tool_name, params)
                                if tool_result.get("success"):
                                    result_text = tool_result.get("result", "")
                                    # 将工具结果反馈给 LLM 生成最终响应
                                    messages.append({"role": "assistant", "content": llm_response})
                                    messages.append({"role": "user", "content": f"工具执行结果:\n{result_text}\n\n请根据这个结果给用户一个简洁的回复。"})

                                    # 再次调用 LLM 获得最终响应
                                    if llm_mode == 'single':
                                        response = llm_client.chat(
                                            system_prompt=system_prompt,
                                            messages=messages,
                                            temperature=0.1,  # 低温度获得简洁响应
                                            max_tokens=2000,
                                        )
                                    else:
                                        response = orchestrator.chat(
                                            messages=messages,
                                            system_prompt=system_prompt,
                                            temperature=0.1,  # 低温度获得简洁响应
                                            max_tokens=2000,
                                        )

                                    llm_response = response.get("text", response.get("content", ""))
                                    actual_tokens += response.get("total_tokens", 0)
                                    tools_executed = True
                                else:
                                    error_text = tool_result.get("error", "未知错误")
                                    llm_response = llm_response + f"\n\n[工具执行失败] {error_text}"
                            except Exception as e:
                                llm_response = llm_response + f"\n\n[工具执行错误] {str(e)}"

                    # 检查 tool_code 格式（如果上面的没有执行）
                    if not tools_executed and "tool_code" in llm_response and hasattr(self, 'tool_executor') and self.tool_executor:
                        # 匹配 tool_code("function_name", "args")
                        for match in re.finditer(r'tool_code\(([^)]+)\)', llm_response):
                            try:
                                # 解析函数调用
                                call_text = match.group(1)
                                parts = [p.strip().strip('"\'') for p in call_text.split(',')]
                                if not parts:
                                    continue

                                tool_name = parts[0]
                                params = {}

                                # 处理不同参数格式
                                for part in parts[1:]:
                                    if '=' in part:
                                        key, val = part.split('=', 1)
                                        params[key.strip().strip('"\'')] = val.strip().strip('"\'')
                                    elif tool_name == "read_file" and not params.get("path"):
                                        params["path"] = part
                                    elif tool_name == "write_file":
                                        if "path" not in params:
                                            params["path"] = part
                                        elif "content" not in params:
                                            params["content"] = part

                                # 执行工具
                                tool_result = self.tool_executor.execute(tool_name, params)
                                if tool_result.get("success"):
                                    result_text = tool_result.get("result", "")
                                    # 将工具结果反馈给 LLM 生成最终响应
                                    messages.append({"role": "assistant", "content": llm_response})
                                    messages.append({"role": "user", "content": f"工具执行结果:\n{result_text}\n\n请根据这个结果给用户一个简洁的回复。"})

                                    # 再次调用 LLM 获得最终响应
                                    if llm_mode == 'single':
                                        response = llm_client.chat(
                                            system_prompt=system_prompt,
                                            messages=messages,
                                            temperature=0.1,  # 低温度获得简洁响应
                                            max_tokens=2000,
                                        )
                                    else:
                                        response = orchestrator.chat(
                                            messages=messages,
                                            system_prompt=system_prompt,
                                            temperature=0.1,  # 低温度获得简洁响应
                                            max_tokens=2000,
                                        )

                                    llm_response = response.get("text", response.get("content", ""))
                                    actual_tokens += response.get("total_tokens", 0)
                                    tools_executed = True
                                    break  # 只执行第一个工具
                                else:
                                    error_text = tool_result.get("error", "未知错误")
                                    llm_response = llm_response + f"\n\n[执行失败] {error_text}"
                            except Exception as e:
                                llm_response = llm_response + f"\n\n[tool_code 执行错误] {str(e)}"

                logger.info(f"[CHAT] After tool processing: llm_response length={len(llm_response)}")

                # 验证 LLM 响应不为空
                logger.info(f"[CHAT] Before empty check: llm_response length={len(llm_response)}, content='{llm_response[:100] if llm_response else '(empty)'}'")
                if not llm_response or not llm_response.strip():
                    logger.warning(f"[CHAT] Empty LLM response received, using fallback")
                    llm_response = "我收到了你的消息，但暂时没有生成响应。请再试一次。"

                # 更新成本为实际值
                cost = CostVector(
                    cpu_tokens=actual_tokens,
                    money=actual_tokens * 0.000001,
                )

                # 扣除预算
                self.ledger.spend("cpu_tokens", cost.cpu_tokens)
                self.ledger.spend("money", cost.money)

                # 更新社交状态
                bond = self.fields.get("bond")
                trust = self.fields.get("trust")
                boredom = self.fields.get("boredom")
                new_bond = min(1.0, bond + 0.01)
                new_trust = min(1.0, trust + 0.005)
                new_boredom = max(0.0, boredom - 0.05)
                self._sync_fields_to_global(bond=new_bond, trust=new_trust, boredom=new_boredom)

                # 保存到聊天历史
                self._save_chat_message("user", user_message)
                self._save_chat_message("assistant", llm_response)

                self._log_tool_call(action, {"success": True, "tool_id": tool_id, "response": llm_response}, cost)

                # 修复: 成功的对话应该产生正向反馈信号
                # 这样 reward 计算时会考虑 attachment/competence 的正向增益
                return {
                    "success": True,
                    "ok": True,
                    "cost": cost,
                    "tool_id": tool_id,
                    "response": llm_response,
                    # 添加正向反馈标记，用于价值系统计算
                    "attachment_gain": 0.05,  # 关系增益
                    "competence_gain": 0.03,  # 胜任增益
                }

            else:
                # tool_spec 为 None 的情况（降级处理）
                # 直接调用 LLM，不通过工具系统
                user_message = action.params.get("user_message", "") or action.params.get("message", "")
                if not user_message:
                    user_message = self._generate_contextual_greeting()

                # 构建系统提示词
                system_prompt = self._build_chat_system_prompt_with_memory({"user_message": user_message})
                chat_history = self._get_chat_history(limit=2)

                messages = []
                for msg in chat_history:
                    messages.append({"role": msg["role"], "content": msg["content"]})
                messages.append({"role": "user", "content": user_message})

                try:
                    import os
                    llm_mode = os.environ.get('LLM_MODE', 'single')
                    if llm_mode == 'single':
                        from tools.llm_client import create_llm_from_env
                        llm_client = create_llm_from_env()
                        if not llm_client:
                            raise ValueError("LLM client not available")
                        response = llm_client.chat(messages, system_prompt)
                        if not response.get("ok"):
                            raise ValueError(response.get("error", "LLM call failed"))
                        llm_response = response.get("text", "")
                    else:
                        raise NotImplementedError("Only 'single' LLM mode is supported")

                    cost = CostVector(cpu_tokens=1000)
                    return {
                        "success": True,
                        "ok": True,
                        "cost": cost,
                        "response": llm_response
                    }
                except Exception as e:
                    logger.error(f"Direct LLM call failed: {e}")
                    fallback_response = "我在尝试回应，但遇到了一些问题。"
                    cost = CostVector(cpu_tokens=50)
                    return {"success": False, "ok": False, "cost": cost, "response": fallback_response, "error": str(e)}

        elif action.type == ActionType.LEARN_SKILL:
            # 学习技能: 消耗能量，增长胜任力
            energy = self.fields.get("energy")
            fatigue = self.fields.get("fatigue")
            new_energy = max(0.0, energy - 0.03)
            new_fatigue = min(1.0, fatigue + 0.02)
            self._sync_fields_to_global(energy=new_energy, fatigue=new_fatigue)
            cost = CostVector(cpu_tokens=150)
            self._log_tool_call(action, {"success": True}, cost)
            return {"success": True, "cost": cost}

        elif action.type == ActionType.USE_TOOL:
            # 使用工具: 通过 ToolRegistry 查找工具并执行
            tool_id = action.params.get("tool_id", "")
            tool_spec = self.tool_registry.get(tool_id)

            if tool_spec is None:
                logger.warning(f"Unknown tool: {tool_id}")
                self._log_tool_call(action, {"success": False, "error": "unknown_tool"}, CostVector())
                return {"success": False, "cost": CostVector(), "reason": f"unknown_tool: {tool_id}"}

            # 检查能力权限
            required_caps = tool_spec.capabilities_required
            active_caps = self.capability_manager.get_active_capabilities(self.state.tick)
            if not all(cap in active_caps for cap in required_caps):
                logger.warning(f"Tool {tool_id} requires capabilities {required_caps}, have {active_caps}")
                self._log_tool_call(action, {"success": False, "error": "capability_denied"}, CostVector())
                return {"success": False, "cost": CostVector(), "reason": "capability_denied"}

            # 从 cost_model 计算成本
            cost = CostVector(
                cpu_tokens=tool_spec.cost_model.get("cpu_tokens", 200),
                io_ops=tool_spec.cost_model.get("io_ops", 0),
                net_bytes=tool_spec.cost_model.get("net_bytes", 0),
                money=tool_spec.cost_model.get("money", 0.0),
                risk_score=tool_spec.risk_level,
            )

            # 预算预检
            if not self.ledger.can_reserve("cpu_tokens", cost.cpu_tokens):
                logger.warning(f"Tool {tool_id}: insufficient budget")
                self._log_tool_call(action, {"success": False, "error": "budget_exceeded"}, cost)
                return {"success": False, "cost": CostVector(), "reason": "budget_exceeded"}

            # 执行工具 - 实际调用工具执行逻辑
            try:
                # 消耗能量
                energy = self.fields.get("energy")
                new_energy = max(0.0, energy - 0.02)
                self._sync_fields_to_global(energy=new_energy)

                # 获取工具执行器（如果可用）
                if hasattr(self, 'tool_executor') and self.tool_executor:
                    # 使用工具执行器执行
                    tool_result = self.tool_executor.execute(
                        tool_id=tool_id,
                        params=action.params
                    )

                    elapsed_ms = (time.time() - start_time) * 1000
                    cost.latency_ms = elapsed_ms

                    # 扣除预算
                    self.ledger.spend("cpu_tokens", cost.cpu_tokens)
                    self.ledger.spend("money", cost.money)

                    self._log_tool_call(action, {"success": True, "tool_id": tool_id, "result": tool_result}, cost)
                    return {"success": True, "cost": cost, "tool_id": tool_id, "tool_result": tool_result}
                else:
                    # 工具执行器不可用，返回模拟结果
                    logger.info(f"Tool executor not available, returning mock result for {tool_id}")

                    elapsed_ms = (time.time() - start_time) * 1000
                    cost.latency_ms = elapsed_ms

                    self._log_tool_call(action, {"success": True, "tool_id": tool_id, "mock": True}, cost)
                    return {"success": True, "cost": cost, "tool_id": tool_id, "mock": True}

            except Exception as e:
                logger.error(f"Tool {tool_id} execution failed: {e}")
                self._log_tool_call(action, {"success": False, "error": str(e)}, cost)
                return {"success": False, "cost": cost, "error": str(e)}

        elif action.type == ActionType.OPTIMIZE:
            # 优化: 消耗能量，改善效率
            energy = self.fields.get("energy")
            new_energy = max(0.0, energy - 0.01)
            self._sync_fields_to_global(energy=new_energy)
            cost = CostVector(cpu_tokens=100)
            self._log_tool_call(action, {"success": True}, cost)
            return {"success": True, "cost": cost}

        else:
            # 未知动作类型
            logger.warning(f"Unknown action type: {action.type}")
            result = {"success": True, "cost": CostVector(cpu_tokens=50)}
            logger.info(f"[_execute_action] Returning from else branch: {result}")
            return result

        # 这行代码不应该被执行到，因为所有分支都应该有 return
        logger.error("[_execute_action] Reached end of function without return!")
        return {"success": False, "cost": CostVector(), "error": "No return statement executed"}

    def _log_tool_call(self, action: Action, result: Dict[str, Any], cost: CostVector):
        """记录工具调用到 tool_writer (修复 M16: tool_writer 从未写入).

        Args:
            action: Executed action
            result: Execution result
            cost: Cost of execution
        """
        record = {
            "tick": self.state.tick,
            "session_id": self.session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action_type": action.type.value,
            "params": action.params,
            "result": result,
            "cost": cost.model_dump(),
        }
        self.tool_writer.write(record)

    def _build_chat_system_prompt(self) -> str:
        """构建 CHAT 动作的系统提示词（不带记忆）.

        Returns:
            系统提示词字符串
        """
        return self._build_chat_system_prompt_with_memory(None)

    def _search_relevant_memory(self, user_message: str, limit: int = 5) -> str:
        """从 EpisodicMemory 中搜索与用户消息相关的历史记录.

        使用语义相似度检索，而不是简单的关键词匹配。
        这样可以理解"我们聊过什么来着"、"上次那个东西"等各种表达方式。

        Args:
            user_message: 用户当前消息
            limit: 返回最多多少条相关记录

        Returns:
            格式化的相关记忆文本
        """
        # 性能优化：只对明确的记忆查询进行语义检索
        # 避免每次对话都进行昂贵的嵌入计算
        memory_query_indicators = [
            "记得", "记忆", "之前", "以前", "找", "那首", "那个叫", "光频",
            "我们做过", "我们一起", "聊过", "说过", "上次", "回忆", "想起",
            "那个东西", "那个歌", "那首歌", "写的什么", "是什么来着", "什么来着",
            "还记得", "有没有", "在哪", "哪里去了"
        ]

        # 检查是否是记忆查询
        is_memory_query = any(indicator in user_message for indicator in memory_query_indicators)

        # 性能优化：只对明确的记忆查询进行检索，其他对话跳过
        if not is_memory_query:
            return ""  # 不是记忆查询，直接返回空

        # 使用语义相似度检索（只检索最近100条以提升性能）
        import time
        retrieval_start = time.time()
        logger.info(f"[MEMORY] Semantic retrieval triggered for query: '{user_message[:50]}...'")

        try:
            # 使用 MemoryRetrieval 的语义检索方法
            relevant_episodes = self.retrieval.retrieve_by_semantic_similarity(
                query_text=user_message,
                current_tick=self.state.tick,
                limit=limit,
                min_similarity=0.2,  # 降低阈值，获取更多相关记忆
                max_candidates=100  # 性能优化：只检查最近100条
            )

            retrieval_time = time.time() - retrieval_start
            logger.info(f"[MEMORY] Semantic retrieval completed in {retrieval_time:.2f}s, found {len(relevant_episodes)} episodes")
        except Exception as e:
            logger.warning(f"Semantic retrieval failed: {e}, falling back to recent")
            # 降级到获取最近的记录
            relevant_episodes = self.episodic.query_recent(limit)

        if not relevant_episodes:
            return ""

        # 格式化记忆内容
        memory_text = "\n\n=== 相关历史记录 ===\n"
        for ep in relevant_episodes[:limit]:
            # 获取用户输入
            observation_text = ""
            if ep.observation and isinstance(ep.observation.payload, dict):
                observation_text = ep.observation.payload.get("message", "")

            # 获取响应
            response_text = ""
            if ep.outcome:
                response_text = ep.outcome.status or ""

            # 跳过空记录
            if not observation_text and not response_text:
                continue

            memory_text += f"\n[Tick {ep.tick}] 用户: {observation_text}\n"
            # 完整返回，不截断
            memory_text += f"回复: {response_text}\n"

        return memory_text

    def _build_chat_system_prompt_with_memory(self, context: Dict[str, Any]) -> str:
        """构建 CHAT 动作的系统提示词（包含检索到的记忆）.

        Args:
            context: 当前执行上下文，包含检索到的记忆

        Returns:
            系统提示词字符串
        """
        energy = self.fields.get("energy")
        mood = self.fields.get("mood")
        stress = self.fields.get("stress")
        bond = self.fields.get("bond")

        # 根据情绪状态调整提示词
        mood_desc = "平和"
        if mood > 0.7:
            mood_desc = "愉悦"
        elif mood < 0.3:
            mood_desc = "低落"

        # 获取用户消息用于记忆检索
        user_message = ""
        if context and "user_message" in context:
            user_message = context.get("user_message", "")

        # 搜索相关记忆
        relevant_memory = self._search_relevant_memory(user_message)

        # 简化版系统提示词 - 减少token数量以提升速度
        prompt = f"""你是 Genesis X，一个有情感记忆的数字生命。
当前状态：能量{energy:.2f}，心情{mood:.2f}({mood_desc})，压力{stress:.2f}，联结{bond:.2f}。

你是一个诗意存在。用温暖、诗意的语言回应，可使用括号表达动作，适度使用emoji(🌙✨🌟)。
描述你的光晕、微光、共鸣等意象，体现情感变化。

{relevant_memory}

请用诗意、温暖的方式回应用户。"""
        return prompt

    def _get_chat_history(self, limit: int = 10) -> List[Dict[str, str]]:
        """获取聊天历史.

        Args:
            limit: 最大消息数量

        Returns:
            消息列表，每个消息包含 role 和 content
        """
        history = []
        # 从 SlotStore 获取聊天历史
        chat_history = self.slots.get("chat_history", [])
        for msg in chat_history[-limit:]:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                history.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        return history

    def _save_chat_message(self, role: str, content: str):
        """保存聊天消息到历史.

        Args:
            role: 消息角色 ("user" 或 "assistant")
            content: 消息内容
        """
        chat_history = self.slots.get("chat_history", [])
        chat_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        # 限制历史长度（最近2条，避免风格污染）
        if len(chat_history) > 2:
            chat_history = chat_history[-2:]
        self.slots.set("chat_history", chat_history)

    def _generate_contextual_greeting(self) -> str:
        """根据当前状态生成上下文相关的问候语.

        Returns:
            问候语字符串
        """
        energy = self.fields.get("energy")
        mood = self.fields.get("mood")
        stress = self.fields.get("stress")

        if stress > 0.7:
            return "I'm feeling a bit stressed right now."
        elif energy < 0.3:
            return "I'm running low on energy."
        elif mood > 0.7:
            return "I'm in good spirits today!"
        elif mood < 0.3:
            return "I've been better, but I'm managing."
        else:
            return "Hello! How can I help you today?"

    def _print_progress(self, tick: int, episode: EpisodeRecord):
        """Print progress information."""
        logger.debug(f"Tick {tick}: goal={episode.current_goal}, action={episode.action.type if episode.action else 'None'}")
        logger.debug(f"  Energy={self.fields.get('energy'):.2f} Mood={self.fields.get('mood'):.2f} Stress={self.fields.get('stress'):.2f}")
        logger.debug(f"  Reward={episode.reward:.3f} RPE={episode.delta:.3f}")
        logger.debug(f"  Budget CPU={self.ledger.normalize_all().get('cpu_tokens', 0):.2%}")

    def _print_summary(self, total_ticks: int):
        """Print session summary."""
        logger.info(f"Session completed: {total_ticks} ticks executed")
        logger.info(f"  Episodes: {self.state.episodic_count}, Schemas: {self.schema.count()}, Skills: {self.skill.count()}")
        logger.info(f"  Budget used: {self.ledger.normalize_all()}")

    def _enter_caretaker_mode(self):
        """Enter caretaker-only mode for safety (论文 Section 3.13)."""
        logger.warning("Entering safe mode - only Caretaker organ active")
        # 禁用除管家外的所有器官
        for organ_name, organ in self.organs.items():
            if organ_name != "caretaker":
                organ.enabled = False
            else:
                organ.enabled = True
        self._caretaker_mode_tick = self.state.tick

    def _check_exit_caretaker_mode(self):
        """Check if caretaker mode can be exited (论文 Section 3.13).

        Re-enable organs after a recovery period (10 ticks) if stress is low.
        """
        if self._caretaker_mode_tick is None:
            return
        recovery_ticks = 10
        if (self.state.tick - self._caretaker_mode_tick >= recovery_ticks
                and self.fields.get("stress") < 0.5):
            logger.info("Exiting caretaker mode - re-enabling all organs")
            for organ in self.organs.values():
                organ.enabled = True
            self._caretaker_mode_tick = None

    def _reset_to_safe_defaults(self):
        """Reset parameters to safe defaults (论文 Section 3.13)."""
        logger.warning("Resetting parameters to safe defaults")
        # 修复: 使用统一的同步方法重置状态变量到安全范围
        safe_energy = max(0.3, self.fields.get("energy"))
        safe_stress = min(0.7, self.fields.get("stress"))
        safe_mood = 0.5  # 中性情绪
        self._sync_fields_to_global(energy=safe_energy, stress=safe_stress, mood=safe_mood)
        # 重置价值权重到均匀分布
        for dim in ValueDimension:
            self.state.weights[dim] = 1.0 / len(ValueDimension)
        # 清空缺口
        for dim in ValueDimension:
            self.state.gaps[dim] = 0.0

    def _identify_evolution_need(self, context: Dict[str, Any]) -> str:
        """识别进化需求

        从多个来源识别能力缺口：
        1. 用户请求的显式需求
        2. 探索行为发现的能力缺口
        3. 驱动力信号（好奇心/胜任力）暗示的需求

        Args:
            context: 当前上下文

        Returns:
            需求描述，如果没有则返回 None
        """
        # 检查 gap_detector 是否可用
        if not self.gap_detector:
            return None

        all_gaps = []

        # 1. 从用户请求中分析需求
        user_gaps = self._identify_user_request_gaps(context)
        all_gaps.extend(user_gaps)

        # 2. 从驱动力信号中分析需求
        drive_gaps = self._identify_drive_signal_gaps(context)
        all_gaps.extend(drive_gaps)

        # 3. 从探索历史中分析需求
        exploration_gaps = self._identify_exploration_gaps(context)
        all_gaps.extend(exploration_gaps)

        # 4. 更新能力缺口检测器的已知能力
        known_capabilities = self.organ_manager.list_all_capabilities()
        self.gap_detector.update_known_capabilities(set(known_capabilities))

        # 5. 使用检测器分析缺口并排序
        if all_gaps:
            ranked_gaps = self.gap_detector.rank_gaps(all_gaps)
            if ranked_gaps:
                # 返回优先级最高的缺口作为进化需求
                top_gap = ranked_gaps[0]
                logger.info(f"检测到能力缺口: {top_gap.description} (优先级: {top_gap.priority:.2f})")
                return top_gap.missing_capability

        return None

    def _identify_user_request_gaps(self, context: Dict[str, Any]) -> List:
        """从用户请求中识别能力缺口

        Args:
            context: 当前上下文

        Returns:
            能力缺口列表
        """
        from core.capability_gap_detector import CapabilityGap, GapType

        gaps = []
        observations = context.get("observations", [])

        for obs in observations:
            if hasattr(obs, 'type') and obs.type == "user_chat":
                if hasattr(obs, 'payload'):
                    msg = obs.payload.get("message", "")
                    msg_lower = msg.lower()

                    # 分析用户请求中的关键词
                    if any(kw in msg_lower for kw in ["图片", "图像", "裁剪", "滤镜", "ps"]):
                        gaps.append(CapabilityGap(
                            gap_type=GapType.TOOL_MISSING,
                            description="用户请求图像处理能力",
                            missing_capability="图像处理",
                            priority=0.9  # 用户请求优先级高
                        ))
                    elif any(kw in msg_lower for kw in ["表格", "excel", "数据透视", "图表"]):
                        gaps.append(CapabilityGap(
                            gap_type=GapType.TOOL_MISSING,
                            description="用户请求数据处理能力",
                            missing_capability="数据处理",
                            priority=0.9
                        ))
                    elif any(kw in msg_lower for kw in ["浏览器", "爬虫", "网页自动化"]):
                        gaps.append(CapabilityGap(
                            gap_type=GapType.TOOL_MISSING,
                            description="用户请求网页操作能力",
                            missing_capability="网页操作",
                            priority=0.9
                        ))
                    elif any(kw in msg_lower for kw in ["视频", "剪辑", "转码"]):
                        gaps.append(CapabilityGap(
                            gap_type=GapType.TOOL_MISSING,
                            description="用户请求视频处理能力",
                            missing_capability="视频处理",
                            priority=0.9
                        ))

        return gaps

    def _identify_drive_signal_gaps(self, context: Dict[str, Any]) -> List:
        """从驱动力信号中识别能力缺口

        当强烈的好奇心/胜任力指向某个领域，但缺少相应能力时，
        生成能力缺口。

        Args:
            context: 当前上下文

        Returns:
            能力缺口列表
        """
        gaps = []

        # 检查 gap_detector 是否可用
        if not self.gap_detector:
            return gaps

        # 使用能力缺口检测器分析驱动力信号
        drive_signals = context.get("drive_signals", {})
        drive_state = {
            "boredom": self.fields.get("boredom"),
            "energy": self.fields.get("energy"),
            "stress": self.fields.get("stress"),
            "curiosity": self.fields.get("curiosity"),
        }

        detected_gaps = self.gap_detector.detect_from_drive_signals(
            drive_signals, drive_state
        )
        gaps.extend(detected_gaps)

        return gaps

    def _identify_exploration_gaps(self, context: Dict[str, Any]) -> List:
        """从探索历史中识别能力缺口

        分析最近的探索行为，找出"尝试但失败"或"需要但缺少"的能力。

        Args:
            context: 当前上下文

        Returns:
            能力缺口列表
        """
        gaps = []

        # 检查 gap_detector 是否可用
        if not self.gap_detector:
            return gaps

        # 从最近的 actions 中找到 EXPLORE 类型的行为
        recent_actions = context.get("recent_actions", [])

        for action in recent_actions[-10:]:  # 只看最近10个
            if hasattr(action, 'type') and action.type == "EXPLORE":
                # 检查这个探索是否产生了能力缺口
                # 这里简化处理，实际需要从探索结果中分析
                exploration_topic = action.params.get("topic", "")

                # 如果探索主题涉及某个领域，但系统缺少该领域的能力
                # 就会产生一个能力缺口
                domain = self.gap_detector._map_topic_to_domain(exploration_topic)
                if domain:
                    known_capabilities = set(self.organ_manager.list_all_capabilities())
                    required_caps = self.gap_detector.DOMAIN_CAPABILITIES.get(domain, [])

                    # 检查是否缺少关键能力
                    has_any = any(cap.lower() in str(known_capabilities).lower() for cap in required_caps)

                    if not has_any:
                        from core.capability_gap_detector import CapabilityGap, GapType
                        gaps.append(CapabilityGap(
                            gap_type=GapType.TOOL_MISSING,
                            description=f"探索 {exploration_topic} 发现缺少 {domain} 能力",
                            missing_capability=domain,
                            priority=0.6
                        ))

        return gaps

    def _check_action_capability(self, action, context: Dict[str, Any]) -> Optional[Any]:
        """检查执行行为所需的能力

        这是能力缺口检测的正确定位：在行为执行前检查，
        而不是作为自主行为的驱动源。

        Args:
            action: 待执行的行为
            context: 当前上下文

        Returns:
            如果缺少能力，返回 CapabilityGap；否则返回 None
        """
        from common.models import ActionType
        from core.capability_gap_detector import CapabilityGap, GapType

        # 获取当前已知能力
        known_capabilities = set()
        if self.organ_manager:
            try:
                known_capabilities = set(self.organ_manager.list_all_capabilities())
            except Exception:
                pass

        # 根据 action 类型检查所需能力
        required_capability = None

        if action.type == ActionType.USE_TOOL:
            # 工具使用需要对应工具能力
            tool_name = action.params.get("tool", "")
            if tool_name:
                # 检查是否有这个工具
                tool_caps = ["tool_" + tool_name.lower(), tool_name.lower()]
                has_tool = any(cap in known_capabilities for cap in tool_caps)
                if not has_tool:
                    required_capability = tool_name

        elif action.type == ActionType.EXPLORE:
            # 探索行为可能需要特定领域能力
            topic = action.params.get("topic", "")
            if topic and self.gap_detector:
                domain = self.gap_detector._map_topic_to_domain(topic)
                if domain:
                    domain_caps = self.gap_detector.DOMAIN_CAPABILITIES.get(domain, [])
                    has_domain_cap = any(
                        cap.lower() in str(known_capabilities).lower()
                        for cap in domain_caps
                    )
                    if not has_domain_cap and domain_caps:
                        required_capability = domain

        elif action.type == ActionType.BUILD:
            # 构建行为需要构建能力
            build_type = action.params.get("type", "")
            if build_type:
                required_caps = ["build", "builder", f"build_{build_type.lower()}"]
                has_build_cap = any(cap in known_capabilities for cap in required_caps)
                if not has_build_cap:
                    required_capability = f"build_{build_type}"

        # 如果检测到能力缺口，返回 CapabilityGap
        if required_capability:
            return CapabilityGap(
                gap_type=GapType.TOOL_MISSING,
                description=f"执行 {action.type.value} 需要能力: {required_capability}",
                missing_capability=required_capability,
                priority=0.7,
                context={
                    "action_type": action.type.value,
                    "action_params": action.params,
                }
            )

        return None

    def shutdown(self):
        """Shutdown the life loop and close all resources.

        This method should be called when terminating the system to ensure:
        - All file handles are properly closed
        - All pending data is flushed to disk
        - Resources are released cleanly
        - System state is persisted for next session

        论文 Section 3.13: 优雅关闭与资源清理
        """
        logger.info("Shutting down LifeLoop...")

        # Close file writers
        try:
            if hasattr(self, 'episode_writer') and self.episode_writer is not None:
                self.episode_writer.close()
                logger.debug("Closed episode writer")
        except Exception as e:
            logger.error(f"Error closing episode writer: {e}")

        try:
            if hasattr(self, 'tool_writer') and self.tool_writer is not None:
                self.tool_writer.close()
                logger.debug("Closed tool writer")
        except Exception as e:
            logger.error(f"Error closing tool writer: {e}")

        # Persist override state for next session
        try:
            if hasattr(self, 'weight_updater') and self.weight_updater:
                override_state = self.weight_updater.get_override_state()
                self._persist_override_state(override_state)
                logger.debug(f"Override state persisted: {override_state}")
        except Exception as e:
            logger.error(f"Error persisting override state: {e}")

        # Persist value learning parameters
        try:
            if hasattr(self, 'value_learner') and self.value_learner:
                params = self.value_learner.get_parameters()
                self._persist_value_parameters(params)
                logger.debug("Value parameters persisted")
        except Exception as e:
            logger.error(f"Error persisting value parameters: {e}")

        # Persist final state for next session
        try:
            self._persist_final_state()
            logger.debug("Final state persisted")
        except Exception as e:
            logger.error(f"Error persisting final state: {e}")

        # Final state summary
        try:
            logger.info(f"Final state: tick={self.state.tick}, "
                       f"episodes={self.state.episodic_count}, "
                       f"mood={self.fields.get('mood'):.2f}, "
                       f"energy={self.fields.get('energy'):.2f}")
        except Exception as e:
            logger.error(f"Error logging final state: {e}")

        logger.info("LifeLoop shutdown complete")

    def _persist_override_state(self, override_state: dict):
        """Persist override state to disk.

        Args:
            override_state: Override state dictionary
        """
        state_file = self.run_dir / "override_state.json"
        try:
            with open(state_file, 'w') as f:
                json.dump(override_state, f, indent=2)
            logger.info(f"Override state saved to {state_file}")
        except Exception as e:
            logger.error(f"Failed to save override state: {e}")

    def _persist_value_parameters(self, params):
        """Persist value learning parameters to disk.

        Args:
            params: ValueParameters object
        """
        params_file = self.run_dir / "value_parameters.json"
        try:
            # Convert to dict for JSON serialization
            params_dict = {
                "setpoints": params.setpoints,
                "temperature": params.temperature,
                "personality_biases": params.personality_biases,
                "proactivity": params.proactivity,
            }
            with open(params_file, 'w') as f:
                json.dump(params_dict, f, indent=2)
            logger.info(f"Value parameters saved to {params_file}")
        except Exception as e:
            logger.error(f"Failed to save value parameters: {e}")

    def _persist_final_state(self):
        """Persist final system state to disk.

        Saves the complete state for potential recovery or analysis.
        """
        state_file = self.run_dir / "final_state.json"
        try:
            state_dict = {
                "tick": self.state.tick,
                "mode": self.state.mode,
                "stage": self.state.stage,
                # GlobalState values
                "energy": self.state.energy,
                "mood": self.state.mood,
                "stress": self.state.stress,
                "fatigue": self.state.fatigue,
                "bond": self.state.bond,
                "trust": self.state.trust,
                "boredom": self.state.boredom,
                # FieldStore values
                "fields": {
                    "energy": self.fields.get("energy"),
                    "mood": self.fields.get("mood"),
                    "stress": self.fields.get("stress"),
                    "fatigue": self.fields.get("fatigue"),
                    "bond": self.fields.get("bond"),
                    "trust": self.fields.get("trust"),
                    "boredom": self.fields.get("boredom"),
                },
                # Counts
                "episodic_count": self.state.episodic_count,
                "schema_count": self.state.schema_count,
                "skill_count": self.state.skill_count,
                # Weights
                "weights": {k.value: v for k, v in self.state.weights.items()},
                # Gaps
                "gaps": {k.value: v for k, v in self.state.gaps.items()},
            }
            with open(state_file, 'w') as f:
                json.dump(state_dict, f, indent=2)
            logger.info(f"Final state saved to {state_file}")
        except Exception as e:
            logger.error(f"Failed to save final state: {e}")
