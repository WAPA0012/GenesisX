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
import os
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

# 进化系统（自我复制迭代）- 默认禁用（尚未成熟）
from .evolution import EvolutionEngine, EVOLUTION_ENABLED

# 成长系统（获取新能力）- 已启用
from .growth import GrowthManager, create_growth_manager

# 插件系统（预制能力）- 已启用
from .plugins import PluginManager, create_plugin_manager

# 能力管理器（统一调度成长和插件）- 已启用
from .capability_manager import CapabilityManager, create_capability_manager

# 能力缺口检测（连接探索和成长）- 已启用
from .capability_gap_detector import CapabilityGapDetector, create_capability_gap_detector

# 新架构：器官系统（整合驱动力）
from organs import OrganManager, UnifiedOrganManager, BuiltinOrgan
from organs.organ_llm_session import (
    OrganLLMManager,
    SharedBrainManager,
    SessionConfig,
    OrganMemoryWriter,
    create_llm_manager,
)

# Handlers - 功能拆分模块
from .handlers import ActionExecutor, ChatHandler, CaretakerMode, GapDetectorMixin

logger = get_logger(__name__)


class LifeLoop(GapDetectorMixin):
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
        # === 阶段1: 基础配置 ===
        self._init_basic_config(config, run_dir, replay_mode)

        # === 阶段2: 存储系统 ===
        self._init_stores()

        # === 阶段3: 记忆系统 ===
        self._init_memories()

        # === 阶段4: 认知系统 ===
        self._init_cognition()

        # === 阶段5: 器官和工具系统 ===
        self._init_organs_and_tools()

        # === 阶段6: 高级系统 (进化/插件/成长) ===
        self._init_advanced_systems()

        # === 阶段7: 情感和价值系统 ===
        self._init_affect_systems()

        # === 阶段8: 日志和处理器 ===
        self._init_loggers_and_handlers()

        logger.info(f"Initialized session: {self.session_id}")
        logger.info(f"Run directory: {self.run_dir}")
        logger.info(f"Replay mode: {self.replay_mode or 'None (live)'}")

    def set_progress_callback(self, callback):
        """设置进度回调函数

        Args:
            callback: 回调函数，签名为 callback(phase: str, message: str, progress: float)
                     - phase: 当前阶段名称
                     - message: 阶段描述信息
                     - progress: 进度百分比 (0.0 - 1.0)
        """
        self._progress_callback = callback

    def _update_phase(self, phase: str, message: str = "", progress: float = 0.0):
        """更新当前阶段并触发回调

        Args:
            phase: 阶段名称
            message: 阶段描述
            progress: 进度 (0.0 - 1.0)
        """
        self._current_phase = phase
        if self._progress_callback:
            try:
                self._progress_callback(phase, message, progress)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")

    def _init_basic_config(self, config: Dict[str, Any], run_dir: Path, replay_mode: str):
        """初始化基础配置"""
        self.config = config
        self.run_dir = run_dir
        self.replay_mode = replay_mode
        self.session_id = config.get("session_id", "genesisx_persistent")
        self._current_phase = "init"
        self._progress_callback = None  # 进度回调函数
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def _init_stores(self):
        """初始化存储系统"""
        self.state = GlobalState()
        self.fields = FieldStore()
        self.slots = SlotStore()
        self.signals = SignalBus()
        self.ledger = MetabolicLedger(
            budgets=self.config.get("runtime", {}).get("budgets", {})
        )
        self._init_state_from_config()

    def _init_memories(self):
        """初始化记忆系统"""
        episodes_path = self.run_dir / "episodes.jsonl"
        self.episodic = EpisodicMemory(episodes_path)
        self.schema = SchemaMemory()
        self.skill = SkillMemory()
        self.retrieval = MemoryRetrieval(self.episodic, self.schema, self.skill)
        self.consolidator = DreamConsolidator(self.episodic, self.schema, self.skill)
        self._restore_tick_from_history()
        self._restore_chat_history()

    def _init_cognition(self):
        """初始化认知系统"""
        self.goal_compiler = GoalCompiler()
        self.planner = Planner()
        self.evaluator = PlanEvaluator()
        self.verifier = Verifier()

    def _init_organs_and_tools(self):
        """初始化器官和工具系统"""
        # 初始化器官 LLM 会话管理器
        self._init_organ_llm_manager()

        # 初始化器官（传入 LLM 会话）
        self.organs = {
            "caretaker": CaretakerOrgan(
                llm_session=self._organ_llm_manager.get_session("caretaker") if self._organ_llm_manager else None
            ),
            "immune": ImmuneOrgan(
                llm_session=self._organ_llm_manager.get_session("immune") if self._organ_llm_manager else None
            ),
            "mind": MindOrgan(
                llm_session=self._organ_llm_manager.get_session("mind") if self._organ_llm_manager else None
            ),
            "scout": ScoutOrgan(
                llm_session=self._organ_llm_manager.get_session("scout") if self._organ_llm_manager else None
            ),
            "builder": BuilderOrgan(
                llm_session=self._organ_llm_manager.get_session("builder") if self._organ_llm_manager else None
            ),
            "archivist": ArchivistOrgan(
                llm_session=self._organ_llm_manager.get_session("archivist") if self._organ_llm_manager else None
            ),
        }

        # 记录 LLM 会话状态
        if self._organ_llm_manager:
            logger.info("OrganLLMManager: LLM sessions created for all organs")
        else:
            logger.info("OrganLLMManager: Not available, organs will use rule-based fallback")

        self.tool_registry = ToolRegistry()
        self._init_dynamic_tools()

        # 旧版器官管理器（向后兼容）
        self.organ_manager = OrganManager()

        # 新版统一器官管理器
        self.unified_organ_manager = UnifiedOrganManager()

        # 将内置器官注册到统一管理器
        for name, organ in self.organs.items():
            if isinstance(organ, BuiltinOrgan):
                self.unified_organ_manager.add_builtin_organ(organ)
            else:
                # 将其他器官包装为 BuiltinOrgan 的动态子类
                from organs import OrganType
                from common.models import Action

                # 创建动态子类来实现抽象方法
                class WrappedBuiltinOrgan(BuiltinOrgan):
                    def __init__(self, name, capabilities, description, value_dimension, original_organ):
                        super().__init__(name, capabilities, description, value_dimension)
                        self._original_organ = original_organ

                    def propose_actions(self, state, context):
                        if hasattr(self._original_organ, 'propose_actions'):
                            return self._original_organ.propose_actions(state, context)
                        return []

                wrapped = WrappedBuiltinOrgan(
                    name=name,
                    capabilities=organ.get_capabilities() if hasattr(organ, 'get_capabilities') else [],
                    description=getattr(organ, 'description', f'{name} organ'),
                    value_dimension=getattr(organ, 'value_dimension', None),
                    original_organ=organ,
                )
                self.unified_organ_manager.add_builtin_organ(wrapped)

        logger.info(f"UnifiedOrganManager: {len(self.organs)} builtin organs registered")

    def _init_dynamic_tools(self):
        """初始化动态工具注册表"""
        try:
            from tools.dynamic_tool_registry import get_global_registry, register_skills
            self.dynamic_tool_registry = get_global_registry()

            # 自动发现工具
            tools_dir = Path(__file__).parent.parent / "tools"
            if tools_dir.exists():
                self.dynamic_tool_registry.discover_from_directory(tools_dir)
                stats = self.dynamic_tool_registry.get_stats()
                logger.info(f"动态工具注册表: {stats}")

            # 注册技能系统
            register_skills(self.dynamic_tool_registry)
            logger.info("技能系统已注册到工具注册表")
        except Exception as e:
            logger.warning(f"初始化动态工具失败: {e}")
            self.dynamic_tool_registry = None

    def _init_organ_llm_manager(self):
        """初始化器官 LLM 会话管理器

        支持三种模式：
        - independent: 独立对话，每个器官有独立会话，可单独配置 LLM
        - shared: 共享对话，所有器官共享一个大脑
        - disabled: 无配置，器官使用规则模式
        """
        self._organ_llm_manager = None
        self._organ_memory_writer = None

        try:
            # 获取器官 LLM 配置
            organ_llm_config = self.config.get("organ_llm", {})
            mode = organ_llm_config.get("mode", "independent")

            # disabled 模式：不使用 LLM
            if mode == "disabled":
                logger.info("OrganLLMManager: Disabled, organs will use rule-based mode")
                return

            # 获取全局 LLM 配置
            global_llm_config = self.config.get("llm", {})
            if not global_llm_config or not global_llm_config.get("api_base"):
                logger.info("OrganLLMManager: No global LLM config found, organs will use rule-based mode")
                return

            from tools.llm_client import LLMClient
            global_llm_client = LLMClient(global_llm_config)

            # 创建全局会话配置
            global_session_config = SessionConfig(
                max_history=organ_llm_config.get("max_history", 20),
                temperature=organ_llm_config.get("temperature", 0.7),
                max_tokens=organ_llm_config.get("max_tokens", 1000),
            )

            # 根据模式创建管理器
            if mode == "shared":
                # 共享大脑模式：所有器官使用同一个会话
                # 获取共享模式配置
                shared_config = organ_llm_config.get("shared", {})
                use_default_llm = shared_config.get("use_default_llm", True)

                # 确定使用的 LLM 客户端
                if use_default_llm:
                    shared_llm_client = global_llm_client
                else:
                    # 使用自定义 LLM 配置
                    custom_llm_config = shared_config.get("llm", {})
                    if custom_llm_config and custom_llm_config.get("api_base"):
                        try:
                            shared_llm_client = LLMClient(custom_llm_config)
                            logger.info("OrganLLMManager: Shared mode using custom LLM")
                        except Exception as e:
                            logger.warning(f"OrganLLMManager: Failed to create custom LLM for shared mode: {e}")
                            shared_llm_client = global_llm_client
                    else:
                        shared_llm_client = global_llm_client

                # 会话配置（使用共享配置或全局默认）
                shared_session_config = SessionConfig(
                    max_history=shared_config.get("max_history", global_session_config.max_history),
                    temperature=shared_config.get("temperature", global_session_config.temperature),
                    max_tokens=shared_config.get("max_tokens", global_session_config.max_tokens),
                )

                self._organ_llm_manager = create_llm_manager(
                    llm_client=shared_llm_client,
                    mode="shared",
                    config=shared_session_config,
                )
                logger.info("OrganLLMManager: Initialized in 'shared' mode")

            else:
                # 独立模式：每个器官有独立会话
                # 获取器官独立配置
                organs_config = organ_llm_config.get("organs", {})

                # 为每个器官创建 LLM 客户端（如果配置了自定义 LLM）
                organ_clients = {}
                organ_session_configs = {}

                for organ_name in ["mind", "scout", "builder", "caretaker", "archivist", "immune"]:
                    organ_config = organs_config.get(organ_name, {})
                    use_default_llm = organ_config.get("use_default_llm", True)

                    # 会话配置（使用器官配置或全局默认）
                    organ_session_configs[organ_name] = SessionConfig(
                        max_history=organ_config.get("max_history", global_session_config.max_history),
                        temperature=organ_config.get("temperature", global_session_config.temperature),
                        max_tokens=organ_config.get("max_tokens", global_session_config.max_tokens),
                    )

                    # LLM 客户端配置
                    if use_default_llm:
                        organ_clients[organ_name] = global_llm_client
                    else:
                        # 使用自定义 LLM 配置
                        custom_llm_config = organ_config.get("llm", {})
                        if custom_llm_config and custom_llm_config.get("api_base"):
                            try:
                                organ_clients[organ_name] = LLMClient(custom_llm_config)
                                logger.info(f"OrganLLMManager: {organ_name} using custom LLM")
                            except Exception as e:
                                logger.warning(f"OrganLLMManager: Failed to create custom LLM for {organ_name}: {e}")
                                organ_clients[organ_name] = global_llm_client
                        else:
                            organ_clients[organ_name] = global_llm_client

                # 创建独立模式管理器
                self._organ_llm_manager = create_llm_manager(
                    llm_client=global_llm_client,  # 默认客户端
                    mode="independent",
                    config=global_session_config,
                    organ_clients=organ_clients,
                    organ_session_configs=organ_session_configs,
                )
                logger.info("OrganLLMManager: Initialized in 'independent' mode")

            # 初始化选择性记忆写入器（使用全局 LLM 客户端）
            memory_config = organ_llm_config.get("memory", {})
            if memory_config.get("enabled", True):
                self._organ_memory_writer = OrganMemoryWriter(
                    memory_system=self.episodic,
                    llm_client=global_llm_client,
                    importance_threshold=memory_config.get("importance_threshold", 0.5),
                    use_llm_judge=memory_config.get("use_llm_judge", True),
                )
                logger.info(f"OrganMemoryWriter: Initialized (llm_judge={memory_config.get('use_llm_judge', True)})")

        except Exception as e:
            logger.warning(f"OrganLLMManager: Failed to initialize: {e}")
            self._organ_llm_manager = None
            self._organ_memory_writer = None

    def _save_organ_thought_to_memory(
        self,
        organ_name: str,
        thought: str,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> bool:
        """保存器官思考到记忆（选择性）

        Args:
            organ_name: 器官名称
            thought: 思考内容
            state: 当前状态
            context: 上下文

        Returns:
            是否保存成功
        """
        if not self._organ_memory_writer:
            return False

        return self._organ_memory_writer.save_if_worthwhile(
            organ_name=organ_name,
            thought=thought,
            state=state,
            context=context,
            tick=self.state.tick,
        )

    def _init_advanced_systems(self):
        """初始化高级系统（进化、插件、成长）"""
        # 进化系统（默认禁用）
        self._init_evolution_system()

        # 插件系统（新架构：传入统一器官管理器）
        plugin_config = self.config.get("plugins", {})
        self.plugin_manager = create_plugin_manager(
            config=plugin_config,
            unified_organ_manager=self.unified_organ_manager
        )
        logger.info(f"PluginManager: {len(self.plugin_manager.list_plugins())} plugins loaded")

        # 成长系统（新架构：传入统一器官管理器）
        self._init_growth_system()

        # 能力管理器
        self.capability_manager = create_capability_manager(
            growth_manager=self.growth_manager,
            plugin_manager=self.plugin_manager,
            organ_manager=self.organ_manager,
            config=self.config.get("capability", {})
        )
        logger.info("CapabilityManager enabled")

        # 能力缺口检测器
        self._init_gap_detector()

    def _init_evolution_system(self):
        """初始化进化系统"""
        evolution_config = self.config.get("evolution", {})
        self.evolution_enabled = evolution_config.get("enabled", False) and EVOLUTION_ENABLED
        if self.evolution_enabled:
            self.evolution_system = EvolutionEngine(
                project_root=self.run_dir.parent,
                config=evolution_config
            )
            logger.info("EvolutionEngine enabled")
        else:
            self.evolution_system = None

    def _init_growth_system(self):
        """初始化成长系统"""
        growth_config = self.config.get("growth", {})
        self.growth_manager = create_growth_manager(
            organ_manager=self.organ_manager,
            llm_client=None,
            config=growth_config,
            plugin_manager=self.plugin_manager,
            unified_organ_manager=self.unified_organ_manager  # 新架构：传入统一器官管理器
        )
        self.growth_enabled = growth_config.get("enabled", True)
        if self.growth_enabled:
            logger.info("GrowthManager enabled")

    def _init_gap_detector(self):
        """初始化能力缺口检测器"""
        gap_detector_config = self.config.get("capability_gap_detector", {})
        self.gap_detector = create_capability_gap_detector(gap_detector_config)
        self.gap_detection_enabled = gap_detector_config.get("enabled", True)
        if self.gap_detection_enabled:
            try:
                known_caps = set(self.organ_manager.list_all_capabilities())
                self.gap_detector.update_known_capabilities(known_caps)
                logger.info(f"CapabilityGapDetector: {len(known_caps)} capabilities")
            except Exception as e:
                logger.warning(f"Failed to update capabilities: {e}")
                self.gap_detector.update_known_capabilities(set())

    def _init_affect_systems(self):
        """初始化情感和价值系统"""
        self.value_function = ValueFunction()
        self.rpe_computer = RPEComputer()
        self.weight_updater = WeightUpdater(self.config)

        # 恢复持久化覆盖状态
        if self.state.override_active:
            override_state = {
                "override_active": self.state.override_active,
                "timestamp": self.state.override_trigger_time
            }
            self.weight_updater.set_override_state(override_state)

        # 价值学习器
        self.value_learner = ValueLearner()
        if 'value_parameters' in self.config:
            self.value_learner.set_parameters(self.config['value_parameters'])

        # 昼夜节律
        self.circadian = CircadianRhythm(self.config.get("circadian", {}))

        # 情感调制
        self.affect_modulator = AffectModulation(self.config.get("affect_modulation", {}))
        logger.info("AffectModulation enabled")

        # 模块启用状态
        self.drives_enabled = True
        self.get_user_input = None
        self._caretaker_mode_tick = None

    def _init_loggers_and_handlers(self):
        """初始化日志和处理器"""
        self.episode_writer = JSONLWriter(self.run_dir / "states.jsonl")
        self.episode_writer.open()
        self.tool_writer = JSONLWriter(self.run_dir / "tool_calls.jsonl")
        self.tool_writer.open()

        # 功能处理器
        self.action_executor = ActionExecutor(self)
        self.chat_handler = ChatHandler(self)
        self.caretaker_mode = CaretakerMode(self)
        logger.info("Handlers initialized: ActionExecutor, ChatHandler, CaretakerMode")

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
                        self.caretaker_mode.enter()
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
                    self.caretaker_mode.reset_to_safe_defaults()

                else:
                    # 通用异常处理
                    import traceback as tb
                    logger.error(f"Unexpected error: {tb.format_exc()}")

                    if consecutive_errors >= max_consecutive_errors:
                        logger.warning("Too many errors, entering safe mode")
                        self.caretaker_mode.enter()
                        consecutive_errors = 0

        self._print_summary(ticks_executed)
        self.episode_writer.close()
        self.tool_writer.close()

    def tick(self, t: int) -> EpisodeRecord:
        """Execute one complete tick with full GA integration.

        16-Phase Life Loop:
        - Phase 0:  Caretaker mode exit check
        - Phase 1:  Body update (metabolism, circadian)
        - Phase 2:  Observe environment
        - Phase 3:  Memory retrieval
        - Phase 4:  Build context
        - Phase 4.5: Drive system
        - Phase 4.6: Evolution check
        - Phase 4.7: Growth maintenance
        - Phase 5:  Axiology (gaps, weights, utilities)
        - Phase 6:  Goal compilation
        - Phase 7:  Organ differentiation & proposals
        - Phase 8:  Plan evaluation
        - Phase 9:  Safety check (integrity, verifier, risk, budget, capability)
        - Phase 10: Execute action
        - Phase 11: Reward & affect update
        - Phase 12: Memory write
        - Phase 13: Invariants check
        - Phase 14: Value learning
        - Phase 15: Sleep/reflect trigger
        - Phase 16: Persist override state

        Args:
            t: Tick number

        Returns:
            EpisodeRecord
        """
        import time as _time
        tick_start = _time.time()
        phase_times = {}  # 性能日志：记录各阶段耗时

        dt = self.config.get("runtime", {}).get("tick_dt", 1.0)
        ctx = TickContext(t=t, dt=dt)
        self.state.tick = t

        # === PHASE 0: Check caretaker mode exit ===
        phase_start = _time.time()
        self.caretaker_mode.check_and_exit()
        self._update_phase("caretaker_check", "检查维护模式", 0.02)
        phase_times["phase_0"] = _time.time() - phase_start

        # === PHASE 1: Body Update ===
        phase_start = _time.time()
        ctx.advance_phase("body_update")
        self._update_phase("body_update", "更新身体状态", 0.05)
        self._update_body(dt)
        phase_times["phase_1_body"] = _time.time() - phase_start

        # === PHASE 2: Observe ===
        phase_start = _time.time()
        ctx.advance_phase("observe")
        self._update_phase("observe", "感知环境", 0.08)
        field_snapshot = self.fields.snapshot()

        # Get user input if available (for interactive mode)
        user_input = None
        if self.get_user_input is not None:
            user_input = self.get_user_input()

        observations = observe_environment(t, self.state.mode, field_snapshot, user_input)
        for obs in observations:
            ctx.add_observation(obs)
        phase_times["phase_2_observe"] = _time.time() - phase_start

        # === PHASE 3: Retrieve (智能检索：根据消息类型决定检索策略) ===
        phase_start = _time.time()
        ctx.advance_phase("retrieve")
        self._update_phase("retrieve", "检索记忆", 0.12)

        # 智能检索决策
        from memory.smart_retrieval import analyze_retrieval_need, get_retrieval_config

        # 提取用户消息
        user_message = None
        for obs in observations:
            if obs.payload and "user_input" in obs.payload:
                user_message = obs.payload["user_input"]
                break

        # 初始化 context（后续会在 PHASE 4 完整构建）
        context = {}

        # 分析检索需求
        retrieval_decision = analyze_retrieval_need(user_message or "", context)
        retrieval_config = get_retrieval_config(retrieval_decision)

        logger.debug(f"[PHASE 3] Retrieval decision: {retrieval_decision.need.value}, reason: {retrieval_decision.reason}")

        # 根据决策执行检索
        if retrieval_decision.need.value == "none":
            # 不需要检索，只获取最近的1-2条
            recent_episodes = self.episodic.query_recent(2)
            retrieved_episodes = []
            retrieved_schemas = []
            retrieved_skills = []
        else:
            # 基础或语义检索
            recent_episodes = self.episodic.query_recent(5)

            # 提取检索标签
            retrieval_tags = retrieval_decision.query_keywords or []
            for obs in observations:
                if obs.payload:
                    if "user_input" in obs.payload and obs.payload["user_input"]:
                        retrieval_tags.extend(obs.payload["user_input"].split()[:3])
                    if "type" in obs.payload:
                        retrieval_tags.append(obs.payload["type"])
                retrieval_tags.append(obs.type)

            # 执行检索
            retrieved_episodes = []
            if retrieval_tags:
                retrieved_episodes = self.retrieval.retrieve_episodes(
                    query_tags=retrieval_tags,
                    current_tick=t,
                    limit=retrieval_config["limit"],
                    recency_weight=retrieval_config["recency_weight"],
                    salience_weight=retrieval_config["salience_weight"],
                    keyword_weight=retrieval_config["keyword_weight"],
                    semantic_weight=retrieval_config["semantic_weight"],
                    query_text=user_message if retrieval_config["use_semantic"] else None,
                )

            # Schema检索
            if retrieval_decision.need.value == "semantic":
                retrieved_schemas = self.retrieval.retrieve_schemas(
                    query_tags=retrieval_tags, min_confidence=0.5, limit=5
                ) if retrieval_tags else []
            else:
                retrieved_schemas = self.retrieval.retrieve_schemas(
                    query_tags=retrieval_tags, min_confidence=0.6, limit=3
                ) if retrieval_tags else []

            retrieved_skills = self.retrieval.retrieve_skills(
                query_tags=retrieval_tags, min_success_rate=0.5, limit=3
            ) if retrieval_tags else []

        phase_times["phase_3_retrieve"] = _time.time() - phase_start

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
        # 进化系统默认禁用，需要显式启用
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
        self._update_phase("axiology", "评估价值", 0.20)
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
        self._update_phase("goal_compile", "编译目标", 0.25)
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
        self._update_phase("organ_proposals", "器官处理中", 0.35)

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

        phase_start = _time.time()
        proposed_actions = []

        # === 器官处理模式 ===
        # 支持 three modes:
        # - "serial": 串行处理，稳定但慢 (~40-60s)
        # - "mixed": 混合并行，组内并行组间串行 (~15-25s) [默认]
        # - "parallel": 全并行，最快但有依赖风险 (~8-15s)
        organ_parallel_mode = os.environ.get("ORGAN_PARALLEL_MODE", "mixed")

        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading

        # 辅助函数：处理单个器官
        def process_organ(organ_name: str):
            """处理单个器官，返回 (organ_name, actions, thought)"""
            organ = self.organs.get(organ_name)
            if not organ or not organ.enabled:
                return (organ_name, [], None)

            try:
                actions = organ.propose_actions(field_snapshot, context)
                thought = None
                if hasattr(organ, 'get_last_thought'):
                    thought = organ.get_last_thought()
                return (organ_name, actions, thought)
            except Exception as e:
                logger.error(f"Organ {organ_name} error: {e}")
                return (organ_name, [], None)

        # 辅助函数：保存器官思考到记忆
        def save_organ_thought(organ_name: str, thought):
            if thought and self._organ_memory_writer:
                self._save_organ_thought_to_memory(
                    organ_name=organ_name,
                    thought=thought,
                    state=field_snapshot,
                    context=context,
                )
            organ = self.organs.get(organ_name)
            if organ and hasattr(organ, 'clear_last_thought'):
                organ.clear_last_thought()

        # 按价值驱动优先级排序器官
        sorted_organs = sorted(
            expressed_organs,
            key=organ_priority_by_value,
            reverse=True
        )

        if organ_parallel_mode == "serial":
            # === 串行模式 ===
            # 逐个处理，最稳定
            for organ_name in sorted_organs:
                organ_name, actions, thought = process_organ(organ_name)
                proposed_actions.extend(actions)
                save_organ_thought(organ_name, thought)

        elif organ_parallel_mode == "parallel":
            # === 全并行模式 ===
            # 所有器官同时处理，最快
            actions_lock = threading.Lock()

            with ThreadPoolExecutor(max_workers=len(sorted_organs)) as executor:
                futures = {executor.submit(process_organ, o): o for o in sorted_organs}
                for future in as_completed(futures):
                    organ_name, actions, thought = future.result()
                    with actions_lock:
                        proposed_actions.extend(actions)
                    save_organ_thought(organ_name, thought)

        else:  # "mixed" (默认)
            # === 混合并行模式 ===
            # 按依赖关系分三组执行，组内并行，组间串行
            ORGAN_GROUPS = [
                ["scout", "builder", "archivist"],  # 组1: 观察存储
                ["mind", "caretaker"],               # 组2: 思考维护
                ["immune"],                          # 组3: 免疫检查
            ]

            actions_lock = threading.Lock()

            for group_idx, organ_group in enumerate(ORGAN_GROUPS):
                organs_to_process = [o for o in organ_group if o in expressed_organs]

                if not organs_to_process:
                    continue

                if len(organs_to_process) == 1:
                    organ_name, actions, thought = process_organ(organs_to_process[0])
                    with actions_lock:
                        proposed_actions.extend(actions)
                    save_organ_thought(organ_name, thought)
                else:
                    with ThreadPoolExecutor(max_workers=len(organs_to_process)) as executor:
                        futures = {executor.submit(process_organ, o): o for o in organs_to_process}
                        for future in as_completed(futures):
                            organ_name, actions, thought = future.result()
                            with actions_lock:
                                proposed_actions.extend(actions)
                            save_organ_thought(organ_name, thought)

        phase_times["phase_7_organs"] = _time.time() - phase_start

        # === PHASE 8: Plan Evaluation (含单外部动作强制, 修复 H4) ===
        ctx.advance_phase("plan_evaluate")
        self._update_phase("plan_evaluate", "评估计划", 0.45)
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
        self._update_phase("safety_check", "安全检查", 0.50)

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
        self._update_phase("execute", "执行行为", 0.65)
        phase_start = _time.time()

        try:
            outcome = self.action_executor.execute(selected_action, context)
        except Exception as e:
            logger.error(f"[tick] action_executor.execute raised exception: {e}")
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
        phase_times["phase_10_execute"] = _time.time() - phase_start

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
        self._update_phase("reward_affect", "更新情感状态", 0.75)

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
            # 安全获取 gaps 值，处理 None 和空字典情况
            meaning_gap = 0.0
            if gaps and isinstance(gaps, dict):
                gap_value = gaps.get(ValueDimension.CURIOSITY)
                if gap_value is not None:
                    meaning_gap = float(gap_value)
            boredom = self.fields.get("boredom") or 0.0
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
        self._update_phase("memory_write", "存储记忆", 0.85)
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
        self._update_phase("invariants", "检查不变量", 0.90)
        checks = check_invariants(self.state, weights, self.ledger.normalize_all(), [selected_action])
        if not all(checks.values()):
            logger.warning(f"Invariant violations: {[k for k, v in checks.items() if not v]}")

        # === PHASE 14: Value Learn (论文 Section 3.12) ===
        ctx.advance_phase("value_learn")
        self._update_phase("value_learn", "学习价值", 0.92)
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

        # === PHASE 15: Sleep/Reflect Trigger (优化: 减少触发频率) ===
        ctx.advance_phase("sleep_reflect_trigger")
        self._update_phase("sleep_reflect_trigger", "检查巩固", 0.95)
        # 触发条件：高疲劳 or 低能量 or 高好奇缺口 (修复 v14: 使用5维)
        fatigue = self.fields.get("fatigue")
        energy = self.fields.get("energy")
        # 使用 state.gaps 而不是局部变量 gaps
        curiosity_gap = self.state.gaps.get(ValueDimension.CURIOSITY, 0.0)
        homeostasis_gap = self.state.gaps.get(ValueDimension.HOMEOSTASIS, 0.0)

        # 优化: 提高触发阈值，减少不必要的巩固
        should_consolidate = (
            fatigue > 0.8 or  # 优化: 0.7 → 0.8
            energy < 0.2 or  # 优化: 0.3 → 0.2
            curiosity_gap > 0.7 or  # 优化: 0.6 → 0.7
            homeostasis_gap > 0.7  # 优化: 0.6 → 0.7
        )

        # 优化: 增加最小episode数量要求，减少频繁巩固
        if should_consolidate and self.episodic.count() >= 20:  # 优化: 10 → 20
            # 运行梦境巩固
            stats = self.consolidator.consolidate(
                current_tick=t,
                budget_tokens=1000,  # 优化: 2000 → 1000
                salience_threshold=0.7  # 优化: 0.6 → 0.7
            )
            # 做梦后重置活动疲劳度（"睡了一觉，精神焕发"）
            self.state.reset_activity_fatigue(amount=1.0)
            if stats.get("schemas_created", 0) > 0 or stats.get("skills_created", 0) > 0:
                logger.info(f"Consolidation: Schemas={stats['schemas_created']}, Skills={stats['skills_created']}")

        # === PHASE 16: Persist Override State (论文 Section 3.6.4) ===
        ctx.advance_phase("persist_override")
        self._update_phase("persist_override", "持久化状态", 0.98)
        # 持久化优先级覆盖状态
        override_state = self.weight_updater.get_override_state()
        if override_state.get("override_active"):
            self.state.override_active = override_state["override_active"]
            # 使用实际的覆盖触发时间，而非当前时间
            self.state.override_trigger_time = override_state.get("timestamp", 0.0) or datetime.now(timezone.utc).timestamp()
            # 记录触发时的缺口
            self.state.gaps_at_trigger = {dim.value: g for dim, g in gaps.items()}

        # === 性能日志：输出各阶段耗时 ===
        total_time = _time.time() - tick_start
        if total_time > 1.0:  # 只在超过1秒时输出详细日志
            slow_phases = sorted(phase_times.items(), key=lambda x: -x[1])[:3]
            slow_info = ", ".join([f"{k}:{v:.2f}s" for k, v in slow_phases])
            logger.info(f"[PERF] Tick {t} took {total_time:.2f}s. Slowest: {slow_info}")
        elif total_time > 0.5:
            logger.debug(f"[PERF] Tick {t} took {total_time:.2f}s")

        # === 完成 ===
        self._update_phase("complete", "处理完成", 1.0)

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

        # 更新真实系统资源（CPU、内存占用率）
        self.state.update_resources()
        self.state._update_resource_pressure()

        # 获取昼夜节律调整系数
        circadian_energy = self.circadian.get_energy_level()
        recovery_rate = self.circadian.get_fatigue_recovery_rate()

        # 论文 v14: Energy_t 和 Fatigue_t 已被数字原生模型替代
        # 修复：低能量时应该有恢复趋势，而不是持续下降
        # 如果能量低于昼夜节律水平，向其靠拢（恢复）
        # 如果能量高于昼夜节律水平，缓慢下降（消耗）
        if energy < circadian_energy:
            # 低能量恢复：向昼夜节律水平靠拢
            new_energy = energy + (circadian_energy - energy) * 0.05
        else:
            # 能量消耗：缓慢下降
            new_energy = energy * 0.99 + circadian_energy * 0.01

        # 疲劳自然恢复（简化）
        new_fatigue = max(0.0, fatigue - 0.05 * dt * recovery_rate)

        # Stress 更新移至 Affect Phase，这里保持当前值不变
        # 修复：无聊增长速度减半，避免持续积累导致死锁
        new_boredom = update_boredom(boredom, dt * 0.5)

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

    # ===== 以下方法已移至 ActionExecutor =====
    # _execute_action -> ActionExecutor.execute()
    # _log_tool_call -> ActionExecutor._log_tool_call()

    def _build_chat_system_prompt(self) -> str:
        """构建 CHAT 动作的系统提示词（不带记忆）.

        委托给 ChatHandler 实现。
        """
        return self.chat_handler.build_system_prompt()

    def _search_relevant_memory(self, user_message: str, limit: int = 5) -> str:
        """从 EpisodicMemory 中搜索与用户消息相关的历史记录.

        委托给 ChatHandler 实现。
        """
        return self.chat_handler.search_relevant_memory(user_message, limit)

    def _build_chat_system_prompt_with_memory(self, context: Dict[str, Any]) -> str:
        """构建 CHAT 动作的系统提示词（包含检索到的记忆）.

        委托给 ChatHandler 实现。
        """
        return self.chat_handler.build_system_prompt_with_memory(context)

    def _get_chat_history(self, limit: int = 10) -> List[Dict[str, str]]:
        """获取聊天历史.

        委托给 ChatHandler 实现。
        """
        return self.chat_handler.get_chat_history(limit)

    def _save_chat_message(self, role: str, content: str):
        """保存聊天消息到历史.

        委托给 ChatHandler 实现。
        """
        self.chat_handler.save_chat_message(role, content)

    def _generate_contextual_greeting(self) -> str:
        """根据当前状态生成上下文相关的问候语.

        委托给 ChatHandler 实现。
        """
        return self.chat_handler.generate_contextual_greeting()

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

    # ===== 以下方法已移至处理器或混入类 =====
    # _enter_caretaker_mode, _check_exit_caretaker_mode, _reset_to_safe_defaults -> CaretakerMode
    # _identify_evolution_need, _identify_user_request_gaps, etc. -> GapDetectorMixin (继承)

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
