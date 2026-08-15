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
from axiology import extract_all_features, compute_gaps, compute_utilities, compute_reward
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
from safety import check_integrity, assess_risk, check_budget
from perception import observe_environment, build_context
from axiology.weights import WeightUpdater
from axiology.value_learning import ValueLearner, FeedbackSignal, FeedbackType

# 注：axiology.drives 5 维驱动力由 organs/organ_manager.py 独立 import 并实例化，
# life_loop 通过 organ_manager.get_all_drive_signals / format_drives_for_llm 间接调用。
# drives_prompt（驱动力提示文本）已接入 6 器官的 _build_thinking_prompt（P5-10 修复）。
# 原此处的"暂时禁用"注释（直接 import Drive）已移除——life_loop 不需要直接 import，
# 间接调用路径已稳定工作，注释与实际状态不符（P2-5）。

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


# 阶段1.3: 动作 → 价值维度映射表。
# 用于 plan_evaluator 给每个候选动作算"对应维度的 reward"。
# 论文语义：每个动作主要服务于一个价值维度（EXPLORE 满足 CURIOSITY，
# LEARN_SKILL 提升 COMPETENCE，SLEEP 恢复 HOMEOSTASIS 等）。
_ACTION_VALUE_MAP: Dict[ActionType, "ValueDimension"] = {
    ActionType.EXPLORE: ValueDimension.CURIOSITY,
    ActionType.USE_TOOL: ValueDimension.CURIOSITY,
    ActionType.THINK: ValueDimension.CURIOSITY,
    ActionType.LEARN_SKILL: ValueDimension.COMPETENCE,
    ActionType.GROW: None,  # GROW 不由价值缺口直接驱动——"能力不足"该学习不是该造工具。
                            # GROW 由 builder 器官在有具体建造意图时提议（探索/学习中发现了可工具化的需求）。
    ActionType.OPTIMIZE: ValueDimension.COMPETENCE,
    ActionType.CHAT: ValueDimension.ATTACHMENT,
    ActionType.SOCIALIZE: ValueDimension.ATTACHMENT,
    ActionType.SLEEP: ValueDimension.HOMEOSTASIS,
    ActionType.REFLECT: ValueDimension.SAFETY,
}


def _estimate_action_reward(action: Action, gaps: Dict[ValueDimension, float]) -> float:
    """从动作对应维度的 gap 推导 estimated_reward ∈ [0,1]。

    阶段1.3：替代原来所有动作都写死 0.5 的逻辑。
    语义：gap 大 = 该维度急需 = 对应动作 reward 高。
    base 0.3（所有动作有基础分）+ 最多 0.4 的 gap 加成（gap≥0.5 时封顶）。

    社交加成：SOCIALIZE 在 attachment gap > 0.2 时额外 +0.15，
    模拟"社交冲动"——想交流的欲望积累到一定程度会主动找人说话。
    """
    dim = _ACTION_VALUE_MAP.get(action.type)
    if dim is None:
        return 0.5
    gap = gaps.get(dim, 0.0) if gaps else 0.0
    reward = 0.3 + 0.4 * min(1.0, gap / 0.5)

    # 社交冲动：attachment gap 持续高时，SOCIALIZE 获得额外加成
    if action.type == ActionType.SOCIALIZE:
        attachment_gap = gaps.get(ValueDimension.ATTACHMENT, 0.0) if gaps else 0.0
        if attachment_gap > 0.2:
            reward += 0.15  # 社交冲动激活

    return min(1.0, reward)


class LifeLoop(GapDetectorMixin):
    """Genesis X 核心生命循环 - 完整版

    Features:
    - Complete state management with stores
    - Replay support
    - Dynamic organ differentiation
    - Full safety and budget control
    - Production monitoring
    """

    def __init__(self, config: Dict[str, Any], run_dir: Path, replay_mode: str = None, replay_dir: Path = None):
        """Initialize GA life loop.

        Args:
            config: Configuration dict
            run_dir: Directory for run artifacts
            replay_mode: Optional replay mode (strict/semantic/fork)
            replay_dir: Optional directory to replay from (P7-16)
        """
        # === 阶段1: 基础配置 ===
        self._init_basic_config(config, run_dir, replay_mode, replay_dir)

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

    def _init_basic_config(self, config: Dict[str, Any], run_dir: Path, replay_mode: str, replay_dir: Path = None):
        """初始化基础配置"""
        self.config = config
        self.run_dir = run_dir
        self.replay_mode = replay_mode
        self.session_id = config.get("session_id", "genesisx_persistent")
        self._current_phase = "init"
        self._progress_callback = None  # 进度回调函数
        self.run_dir.mkdir(parents=True, exist_ok=True)

        # P7-16: 初始化回放引擎（仅当指定 replay_mode + replay_dir 时）
        self.replay_engine = None
        if replay_mode and replay_dir:
            try:
                from pathlib import Path as _P
                from persistence.replay import ReplayEngine, ReplayMode
                mode_enum = ReplayMode[replay_mode.upper()]
                self.replay_engine = ReplayEngine(_P(replay_dir), mode=mode_enum)
                logger.info(f"ReplayEngine 已初始化: mode={replay_mode}, dir={replay_dir}, "
                           f"episodes={len(self.replay_engine.episodes)}, tool_calls={len(self.replay_engine.tool_calls)}")
            except Exception as e:
                logger.warning(f"ReplayEngine 初始化失败，降级为 live 模式: {e}")
                self.replay_engine = None

    def _init_stores(self):
        """初始化存储系统"""
        # P8-4: FieldStore 先于 GlobalState 创建，作为单一真相源注入 GlobalState
        self.fields = FieldStore()
        self.state = GlobalState(field_store=self.fields)
        self.slots = SlotStore()
        self.signals = SignalBus()
        self.ledger = MetabolicLedger(
            budgets=self.config.get("runtime", {}).get("budgets", {})
        )
        self._init_state_from_config()

    def _init_memories(self):
        """初始化记忆系统。

        连续性记忆修复（2026-07）：三层记忆改用固定持久路径（artifacts/persistent/），
        而非每次 run 的新目录。这样重启后自动加载所有历史 episodes/schemas/skills，
        系统真正"记得自己经历过什么"——这是连续性生命的基础。

        episodic 记忆不做压缩/删除/归纳，原始经历全部保留（一个生命不会把经历
        全压缩成结论——大量原始经历就该留着，构成"你是谁"）。
        schema/skill 是 dream consolidation 额外产出的归纳，不是 episodic 的替代品。

        文件大小不是问题：~500 字/episode，跑一年约 90MB；检索只取 top-K 相关，
        不会全塞进 LLM context。
        """
        # 持久记忆路径：每个生命用独立子目录（artifacts/persistent/A/、B/、C/）
        social_id = self.config.get("social", {}).get("id") or self.config.get("runtime", {}).get("social", {}).get("id", "A")
        persistent_dir = Path(f"artifacts/persistent/{social_id}")
        persistent_dir.mkdir(parents=True, exist_ok=True)

        episodes_path = persistent_dir / "episodes.jsonl"
        self.episodic = EpisodicMemory(episodes_path)
        # Schema/Skill 也用持久路径，重启后加载之前归纳的模式和技能
        self.schema = SchemaMemory(persistent_dir / "schemas.jsonl")
        self.skill = SkillMemory(persistent_dir / "skills.jsonl")
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
        # P8-8: 缓存 Differentiator（genome config 不变，无需每 tick 重建）
        from core.differentiate import Differentiator
        self._differentiator = Differentiator(self.config.get("genome", {}))

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

        # P5-21: 恢复器官学习状态（跨 run 持久化，必须在器官构造后）
        self._load_organ_state()

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

            # 阶段3.3 修复（2026-07）：初始化 LLMToolExecutor 实例。
            # 原代码全项目都引用 self.life_loop.tool_executor，但 life_loop 从未创建它，
            # 导致所有 hasattr(self.life_loop, 'tool_executor') 检查返回 False，
            # web_search 等工具在 EXPLORE/USE_TOOL 路径下永远不执行。
            # 现在创建实例，让工具真正可被调用。
            try:
                from tools.tool_executor import LLMToolExecutor
                # safe_mode 由环境变量 GENESISX_SAFE_MODE 控制（默认 False = 完全访问）
                import os as _os
                safe_mode = _os.environ.get("GENESISX_SAFE_MODE", "0").lower() in ("1", "true", "yes")
                self.tool_executor = LLMToolExecutor(safe_mode=safe_mode)
                logger.info(f"LLMToolExecutor 已初始化 (safe_mode={safe_mode})")
            except Exception as te:
                logger.warning(f"LLMToolExecutor 初始化失败: {te}")
                self.tool_executor = None
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
            # P5-1: 存为实例属性，供下方独立的 memory writer try 块使用（解耦后跨 try 访问）
            self._global_llm_client = global_llm_client

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
            # P5-1 改进：writer 构造从 manager 的 try 拆出，避免 manager 无关异常连带 kill writer
            memory_config = organ_llm_config.get("memory", {})
            if not memory_config.get("enabled", True):
                # P5-1: 配置驱动禁用时打 INFO，让用户知道器官思考不会入记忆（原静默）
                logger.info("OrganMemoryWriter: Disabled by config (organ thoughts will NOT be saved to memory)")

        except Exception as e:
            logger.warning(f"OrganLLMManager: Failed to initialize: {e}")
            self._organ_llm_manager = None
            # 注：不再在这里把 _organ_memory_writer 设 None——它有自己的独立 try（见下），
            # 避免 manager 的异常误伤 writer

        # P5-1: writer 构造独立 try（与 manager 解耦）
        try:
            organ_llm_config = self.config.get("organ_llm", {})
            memory_config = organ_llm_config.get("memory", {})
            if memory_config.get("enabled", True) and self._organ_memory_writer is None:
                # global_llm_client 在上方 manager try 里存为 self._global_llm_client（P5-1）
                global_llm_client = getattr(self, '_global_llm_client', None)
                self._organ_memory_writer = OrganMemoryWriter(
                    memory_system=self.episodic,
                    llm_client=global_llm_client,
                    importance_threshold=memory_config.get("importance_threshold", 0.5),
                    use_llm_judge=memory_config.get("use_llm_judge", True),
                )
                logger.info(f"OrganMemoryWriter: Initialized (llm_judge={memory_config.get('use_llm_judge', True)})")
        except Exception as e:
            logger.warning(f"OrganMemoryWriter: Failed to initialize, organ thoughts will not persist: {e}")
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

        # 社交系统（多生命交流 + 外部新闻感知）
        self._init_social_system()

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
        # 阶段2.1 修复（2026-07）：原写死 llm_client=None，导致 limb_generator 的
        # _generate_from_llm 永远在入口返回失败（"LLM 客户端未配置"），整个成长系统瘫痪。
        # _init_organ_llm_manager（line 258）在本方法（line 563）之前调用，
        # 所以 self._global_llm_client（line 397）已建好，直接用。
        global_llm_client = getattr(self, '_global_llm_client', None)
        self.growth_manager = create_growth_manager(
            organ_manager=self.organ_manager,
            llm_client=global_llm_client,
            config=growth_config,
            plugin_manager=self.plugin_manager,
            unified_organ_manager=self.unified_organ_manager  # 新架构：传入统一器官管理器
        )
        # 兜底：如果 create_growth_manager 内部没把 llm_client 传给 limb_generator，直接注入
        if global_llm_client and hasattr(self.growth_manager, 'limb_generator'):
            if self.growth_manager.limb_generator.llm_client is None:
                self.growth_manager.limb_generator.llm_client = global_llm_client
                logger.debug("[GROWTH] 事后注入 llm_client 到 limb_generator")
        self.growth_enabled = growth_config.get("enabled", True)
        if self.growth_enabled:
            logger.info("GrowthManager enabled")

    def _init_social_system(self):
        """初始化社交系统。

        从 config 读 social.id（"A"/"B"/"C"），没有就默认 "A"。
        如果 shared 目录不存在（单生命模式），social_system 为 None，不影响运行。
        """
        social_config = self.config.get("social") or self.config.get("runtime", {}).get("social", {})
        self_id = social_config.get("id", "A")
        self.social_name = social_config.get("name", self_id)
        try:
            from core.social import SocialSystem
            self.social_system = SocialSystem(self_id=self_id)
            logger.info(f"SocialSystem enabled (id={self_id}, name={self.social_name})")
        except Exception as e:
            logger.warning(f"社交系统初始化失败（不影响运行）: {e}")
            self.social_system = None

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

        # 昼夜节律 (P4-53/54: 默认 simulation 模式 + seconds_per_tick 对齐 tick_dt)
        circadian_config = self.config.get("circadian", {})
        if "time_mode" not in circadian_config:
            circadian_config["time_mode"] = "simulation"
        if "seconds_per_tick" not in circadian_config:
            circadian_config["seconds_per_tick"] = self.config.get("runtime", {}).get("tick_dt", 1.0)
        self.circadian = CircadianRhythm(circadian_config)

        # 情感调制
        self.affect_modulator = AffectModulation(self.config.get("affect_modulation", {}))
        logger.info("AffectModulation enabled")

        # 模块启用状态
        self.drives_enabled = True
        self.get_user_input = None
        self._caretaker_mode_tick = None

        # 阶段1.1: novelty 信号缓存。
        # PHASE 5（axiology）算出 curiosity gap 后写到这里，PHASE 1（body代谢）读取。
        # 语义：gap 大 = 缺好奇 = novelty 低 → boredom 上升。
        # 首次 tick（PHASE 1 在 PHASE 5 之前）用 0.4 兜底（略低于中等，让 boredom 能启动）。
        self._last_novelty: float = 0.4

        # 工作记忆（2026-07）：跨 tick 保留的"当前任务 + 步骤 + 相关记忆"。
        # 这是让行动连贯的关键——mind 不需要每 tick 从头决策"该做什么"，
        # 而是看到"我正在做 X，已完成 Y，下一步该 Z"后继续。
        # 类似人的工作记忆：此刻在想的事 + 相关的旧记忆自动浮现。
        self._working_memory: Optional[Dict[str, Any]] = None

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
        self.fields.set("bond", initial.get("bond", 0.4))  # P0-1 冷启动修复：0→0.4
        self.fields.set("trust", initial.get("trust", 0.5))
        self.fields.set("boredom", initial.get("boredom", 0.0))
        self.fields.set("curiosity", initial.get("curiosity", 0.5))  # 缺失字段

        # P8-4: 不再需要 _sync_state_to_global()——GlobalState 现在委托 FieldStore，
        # 上面的 fields.set() 调用会自动反映到 self.state

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

        # 社交感知（2026-07）：从共享消息板读取新闻 + 他人的消息 + 他人的状态。
        # 这是"外部世界"和"他者"的入口——生命通过这里感知到不可控的外部输入和其他生命的存在。
        if hasattr(self, 'social_system') and self.social_system:
            try:
                social_obs = self.social_system.get_observations()
                has_content = bool(social_obs["news"] or social_obs["group_new"] or social_obs["private_new"])
                logger.info(f"[SOCIAL] 感知检查: news={len(social_obs['news'])} group={len(social_obs['group_new'])} private={len(social_obs['private_new'])} others={len(social_obs['others'])}")
                if has_content:
                    from common.models import Observation
                    # 新闻 = 外部世界输入（不可控的、世界推送的）
                    if social_obs["news"]:
                        news_titles = [n["title"] for n in social_obs["news"][:3]]
                        ctx.add_observation(Observation(
                            type="world_news",
                            payload={"headlines": news_titles, "full": social_obs["news"]},
                            source_ref="news_center",
                            tick=t,
                        ))
                    # 群聊/私聊 = 他者的存在
                    if social_obs["group_new"]:
                        ctx.add_observation(Observation(
                            type="social_group",
                            payload={"messages": social_obs["group_new"]},
                            source_ref="social",
                            tick=t,
                        ))
                    if social_obs["private_new"]:
                        ctx.add_observation(Observation(
                            type="social_private",
                            payload={"messages": social_obs["private_new"]},
                            source_ref="social",
                            tick=t,
                        ))
                        # 收到别人的私信 → attachment 需求被强烈激活
                        bond = self.fields.get("bond") or 0.4
                        self.fields.set("bond", min(1.0, bond + 0.05 * len(social_obs["private_new"])))

                    # 收到群聊消息 → attachment 需求被激活（比私信弱）
                    if social_obs["group_new"]:
                        bond = self.fields.get("bond") or 0.4
                        # 只对别人发的消息反应（不包括自己发的）
                        others_msgs = [m for m in social_obs["group_new"] if m.get("from") != self.social_system.self_id]
                        if others_msgs:
                            self.fields.set("bond", min(1.0, bond + 0.02 * len(others_msgs)))
                    # 他人的公开状态（存到实例属性，PHASE 4 构建 context 时取）
                    if social_obs["others"]:
                        self._social_others = social_obs["others"]
            except Exception as e:
                logger.debug(f"[SOCIAL] 社交感知失败（非致命）: {e}")
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
        # P4-28: 传 budget_remaining 让 context 有真实预算数据（原硬编码 10000/0）
        budget_remaining = {name: res.remaining() for name, res in self.ledger.resources.items()}
        context = build_context(field_snapshot, recent_episodes, retrieved, budget_remaining)
        # 添加 observations 到 context，供器官使用
        context["observations"] = ctx.obs_batch
        # 社交：他人的公开状态注入 context（PHASE 2 采集的）
        if hasattr(self, '_social_others') and self._social_others:
            context["social_others"] = self._social_others
        # 记忆摘要：把检索到的最近经历做成一句话摘要，注入 context 给器官的提示词用。
        # 这样器官思考时能看到"最近发生过什么"，不再是白纸状态。
        mem_parts = []
        for ep in recent_episodes[:3]:
            if ep.action and ep.outcome:
                status = str(ep.outcome.status or "")[:150]
                if status:
                    mem_parts.append(f"t{ep.tick}:{status}")
        if mem_parts:
            context["retrieved_memories_summary"] = "; ".join(mem_parts)
        # P5-23 修复：传 tick_duration 给器官（caretaker 的时间窗推算需要）
        context["tick_duration"] = dt

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
        # P0-1 残留修复：把 gaps/weights 写入 context，让器官的 _build_thinking_prompt
        # 和价值驱动兜底（BaseOrgan._value_driven_fallback）能读到当前价值缺口。
        context["value_gaps"] = drive_state["gaps"]
        context["value_weights"] = drive_state["weights"]

        # === 新增: PHASE 4.6: 进化系统检查 ===
        # 检查是否需要触发自我进化（吞噬新软件）
        # 进化系统默认禁用，需要显式启用
        if self.evolution_system is not None:
            try:
                if self.evolution_system.check_evolution_trigger(drive_state, context):
                    evolution_need = self._identify_evolution_need(context)
                    if evolution_need:
                        evolution_success, evolution_msg = self.evolution_system.evolve(
                            evolution_need, drive_state, context
                        )
                        if evolution_success:
                            logger.info(f"进化成功: {evolution_msg}")
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
            except Exception as e:
                # P8-15: 原 except AttributeError 太窄（漏真实 bug），改 Exception 但只 log 不崩
                logger.warning(f"进化系统检查失败: {e}")

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

        # 阶段1.1: novelty 信号由 PHASE 1（_update_body）维护——持续衰减 + EXPLORE 后重置。
        # PHASE 5 只读不写（feature_extractors 从 fields.novelty 读，已由 PHASE 1 写入）。
        # 注意：不要在这里用 curiosity_feature 覆盖 _last_novelty，否则会抵消 PHASE 1 的衰减。

        # 阶段2.1 修复（2026-07）：原写死 biases = {dim: 1.0}，导致 yaml 的 weight_bias
        #（curiosity=0.7/safety=1.2 等）从不生效。现从 axiology_config 读真实 bias。
        # bias 影响 WeightUpdater 的 softmax 权重计算：bias 高的维度在同等 gap 下权重更高。
        try:
            from axiology.axiology_config import get_axiology_config
            _ax_cfg = get_axiology_config()
            biases = {}
            for dim in ValueDimension:
                biases[dim] = _ax_cfg.get_weight_bias(dim.value)
        except Exception as _e:
            logger.debug(f"读取 axiology_config weight_bias 失败，降级全 1.0: {_e}")
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
        # P8-8: 用缓存的 _differentiator（__init__ 时创建，genome 不变无需重建）
        diff = self._differentiator
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
        # P8-7 修复：用带 config 的 diff（L1036 创建）而非 legacy select_organs shim
        # （shim 内部用 _get_differentiator() 空 config 缓存，自定义基因 custom_genes 永不生效）
        expressed_organs, _ = diff.select_organs(
            self.state.stage,
            self.state.mode,
            field_snapshot,
            context.get("signals", {})
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
                # 修复（2026-07）：给 as_completed 加超时，防止单个器官的 LLM 调用挂住
                # 导致整个 PHASE 7 永久卡死。超时的器官跳过（返回空 actions）。
                # 超时设 180 秒（单器官正常 10-20 秒，3 倍余量）。
                ORGAN_TIMEOUT = 180
                done_keys = set()
                try:
                    for future in as_completed(futures, timeout=ORGAN_TIMEOUT):
                        done_keys.add(future)
                        organ_name, actions, thought = future.result()
                        with actions_lock:
                            proposed_actions.extend(actions)
                        save_organ_thought(organ_name, thought)
                except TimeoutError:
                    # 超时的 future 跳过（它们的器官会返回空 actions）
                    timed_out = [futures[f] for f in futures if f not in done_keys]
                    logger.warning(f"PHASE 7: 器官超时被跳过: {timed_out}")
                    for f in futures:
                        if f not in done_keys:
                            f.cancel()

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
                        ORGAN_TIMEOUT = 180
                        done_keys = set()
                        try:
                            for future in as_completed(futures, timeout=ORGAN_TIMEOUT):
                                done_keys.add(future)
                                organ_name, actions, thought = future.result()
                                with actions_lock:
                                    proposed_actions.extend(actions)
                                save_organ_thought(organ_name, thought)
                        except TimeoutError:
                            timed_out = [futures[f] for f in futures if f not in done_keys]
                            logger.warning(f"PHASE 7 (mixed): 器官超时被跳过: {timed_out}")
                            for f in futures:
                                if f not in done_keys:
                                    f.cancel()

        # 阶段2.2（2026-07）：纳入成长系统生成的肢体（limb）和插件的动作提议。
        # 改造前：GROW 生成的肢体注册到 unified_organ_manager，但 PHASE 7 只读
        # 旧 self.organs 字典，生成的肢体永远不可见（CODE_MAP P5-6 "只写不读"）。
        # 现追加查询 unified_organ_manager.propose_all_actions，让生成的肢体下 tick 可被提议执行。
        # 注意：propose_all_actions 返回 List[Tuple[organ_name, Action]]，要解包取 Action。
        try:
            if hasattr(self, 'unified_organ_manager') and self.unified_organ_manager:
                limb_pairs = self.unified_organ_manager.propose_all_actions(field_snapshot, context)
                if limb_pairs:
                    # 解包 (organ_name, action) → 只取 action，最多 3 个
                    limb_actions = [pair[1] for pair in limb_pairs[:3] if isinstance(pair, tuple) and len(pair) >= 2]
                    if limb_actions:
                        proposed_actions.extend(limb_actions)
                        logger.debug(f"PHASE 7: unified_organ_manager 贡献 {len(limb_actions)} 个肢体动作")
        except Exception as e:
            logger.warning(f"unified_organ_manager 提议失败（非致命）: {e}")

        phase_times["phase_7_organs"] = _time.time() - phase_start

        # === PHASE 7.5: 决策中心（2026-07 改造）===
        # 工作记忆检查：如果上一个 tick 有未完成的任务，mind 优先继续它。
        # 这让行动连贯——不再是每 tick 失忆重来，而是"我记得我在做什么、做到哪了"。
        if self._working_memory and self._working_memory.get("status") == "active":
            wm = self._working_memory
            wm_task = wm.get("task", "")
            wm_steps = wm.get("steps", [])
            wm_memories = wm.get("related_memories", "")

            # 让 mind 看到"我在做 X，已完成 Y 步"后决定继续还是停止
            selected_action = self._run_working_memory_continuation(
                wm_task, wm_steps, wm_memories, field_snapshot, context, t
            )
            if selected_action:
                logger.info(f"[WM] 继续任务: {wm_task[:40]}（第 {len(wm_steps)+1} 步）")
            else:
                # mind 说该停了或该做别的了 → 清空工作记忆，走正常决策
                logger.info(f"[WM] 任务结束: {wm_task[:40]}（共 {len(wm_steps)} 步）")
                self._working_memory = None
                selected_action = None
        else:
            # 没有活跃的工作记忆 → 走正常决策中心
            selected_action = None

        # 正常决策中心（没有工作记忆或工作记忆 continuation 失败时）
        if selected_action is None:
            ctx.advance_phase("decision_center")
        self._update_phase("decision_center", "决策中心", 0.48)
        selected_action = None
        try:
            selected_action = self._run_decision_center(
                proposed_actions, field_snapshot, context, observations, t
            )
        except Exception as e:
            logger.warning(f"决策中心失败（降级到价值评估）: {e}")
            selected_action = None

        # === PHASE 8: Plan Evaluation（决策中心失败时的 fallback）===
        # 如果决策中心成功产出了 selected_action，跳过价值评估。
        # 只有决策中心失败时，才走原来的价值评估从器官提议中选。
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

        if selected_action is not None:
            # 决策中心成功——用它的决策，跳过价值评估
            logger.info(f"[DECISION] 决策中心裁决: {selected_action.type} | {selected_action.params.get('topic', selected_action.params.get('task', selected_action.params.get('skill', selected_action.params.get('thought', ''))))[:50]}")
        elif proposed_actions:
            # 阶段1.2 修复（2026-07）：CHAT 硬优先会让 heartbeat 自循环（无真用户时）
            # 永远锁死在 CHAT，绕过价值评估。现改为：只有本 tick 有真用户消息
            #（observation.type == "user_chat"）时才硬优先 CHAT；否则 CHAT 也走评估。
            has_user_input = any(
                getattr(o, "type", None) == "user_chat" for o in observations
            )
            chat_actions = [a for a in proposed_actions if a.type == ActionType.CHAT]
            if has_user_input and chat_actions:
                selected_action = chat_actions[0]
            else:
                # 阶段1.3 修复（2026-07）：原实现把所有动作的 estimated_reward 都写死 0.5，
                # dimension=None，导致 plan_evaluator 给所有动作打相同分，价值评估形同虚设。
                # 现按 action.type 映射到对应价值维度，从 gaps 推导 reward：
                # gap 大 = 该维度急需 = 该动作 reward 高。并填 dimension 字段让
                # plan_evaluator 走"计划关联特定维度"分支（用该维度权重而非最大权重）。
                plans = []
                for a in proposed_actions:
                    dim = _ACTION_VALUE_MAP.get(a.type)
                    plans.append({
                        "actions": [a],
                        "estimated_reward": _estimate_action_reward(a, gaps),
                        "estimated_cost": 100.0,
                        "dimension": dim.value if dim else None,
                    })
                budget_utilization = self.ledger.normalize_all()
                # normalize_all() returns utilization (spent/total), so remaining = 1 - utilization
                cpu_remaining_fraction = 1.0 - budget_utilization.get("cpu_tokens", 0.0)
                # P4-13 修复：原 cpu_remaining_fraction × 100000 与 estimated_cost（~100 token 量级）
                # 量纲不匹配，导致 budget_penalty 几乎永不触发。现用 fraction × CPU_BUDGET_CAPACITY
                # 对齐到 token 量级（capacity=100000 是 cpu_tokens 的默认 total）。
                # 注：unlimited 模式下 fraction 恒为 1.0，budget_remaining 恒大，惩罚正确地不触发。
                CPU_BUDGET_CAPACITY = 100000
                scored = self.evaluator.evaluate_plans(
                    plans,
                    {dim.value: w for dim, w in weights.items()},
                    cpu_remaining_fraction * CPU_BUDGET_CAPACITY
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
            self._last_veto_note = (
                self.state.tick,
                f"你上次选的 {selected_action.type.value} 被完整性检查否决"
                f"（{integrity_ok.get('reason')}），系统强制改为睡眠",
            )
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
                self._last_veto_note = (
                    self.state.tick,
                    f"你上次选的 {selected_action.type.value} 被执行前检查否决"
                    f"（{verifier_result.get('error')}），系统改为休整/反思",
                )
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
                self._last_veto_note = (
                    self.state.tick,
                    f"你上次选的 {selected_action.type.value} 风险评分过高（{risk_score:.2f}），被安全评估否决",
                )
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
                self._last_veto_note = (
                    self.state.tick,
                    f"你上次选的 {selected_action.type.value} 因预算耗尽被否决（{budget_ok.get('reason')}）",
                )
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
            # P7-16: STRICT 回放模式——用缓存的 outcome，不真执行（不调 LLM/工具）
            if self.replay_engine and self.replay_mode:
                cached_episode = self.replay_engine.get_episode(t)
                if cached_episode and cached_episode.get("outcome"):
                    outcome = cached_episode["outcome"]
                    # 确保 outcome 有必要字段（缓存的是 dict，可能缺 success/ok）
                    if "success" not in outcome:
                        outcome["success"] = outcome.get("ok", True)
                    logger.debug(f"[tick] STRICT replay t={t}: 使用缓存 outcome")
                else:
                    # 无缓存的 tick，fallback live
                    outcome = self.action_executor.execute(selected_action, context)
            else:
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
            # 幅度需足够大以抵消 homeostasis/safety 等维度的负 RPE
            delta_per_dim["attachment"] = abs(delta_per_dim.get("attachment", 0.0)) + 0.15
            delta_per_dim["competence"] = abs(delta_per_dim.get("competence", 0.0)) + 0.10

        # P8-4: 写 FieldStore 即自动反映到 GlobalState（单一真相源）
        current_mood = self.fields.get("mood")
        new_mood = update_mood_per_dimension(current_mood, delta_per_dim)

        # mood 下跌保护：成功的动作不应让 mood 大幅下跌
        # 根因：homeostasis/safety 的负 RPE 持续拖累 mood，即使动作本身成功了
        # 限制：成功动作每 tick mood 最多跌 0.02（失败动作不限制）
        if outcome.get("success", outcome.get("ok", True)):
            max_drop = 0.02
            if current_mood - new_mood > max_drop:
                new_mood = current_mood - max_drop

        self.fields.set("mood", new_mood)

        # 更新 Stress：使用 affect/stress_affect.update_stress
        # 该函数已包含 RPE 影响、失败惩罚、自然衰减等所有逻辑
        failed = not outcome.get("success", True)
        current_stress = self.fields.get("stress")
        new_stress = update_stress(current_stress, delta, failed)
        self.fields.set("stress", new_stress)

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

        # === PHASE 11.5: Organ Learning Feedback (P5-21) ===
        # 将动作结果反馈给器官，触发 record_* 学习
        self._record_organ_learning(t, goal, selected_action, outcome, reward)

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
            observation=next((o for o in observations if o.type not in ("heartbeat", None)), observations[0] if observations else None),
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
            # P5-21/P5-22: 将巩固质量反馈给 archivist 触发学习
            # P5-22 改进：原二值（0.5/0.7）区分度不足，无法驱动 archivist 策略学习。
            # 改为基于产出的连续值：基础 0.4（成功无产出）+ 每 schema/skill 加成，
            # 上限 1.0。失败时 0.2。这样 archivist 的 strategy_effectiveness 调整有信号。
            try:
                schemas = stats.get("schemas_created", 0)
                skills = stats.get("skills_created", 0)
                success = stats.get("success", True)
                if not success:
                    quality = 0.2
                else:
                    # 基础 0.4 + 每个 schema +0.15 + 每个 skill +0.2，clamp [0, 1]
                    quality = min(1.0, 0.4 + schemas * 0.15 + skills * 0.2)
                self.organs["archivist"].mark_consolidation_quality(quality)
            except Exception as e:
                logger.debug(f"Archivist learning feedback skipped: {e}")

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

        # 社交：更新自己的公开 profile（让其他生命能看到自己的状态）
        if hasattr(self, 'social_system') and self.social_system:
            try:
                mood = self.fields.get("mood") or 0.5
                # 从最近 episode 提取当前兴趣
                interest = ""
                if selected_action and selected_action.params:
                    interest = str(selected_action.params.get("topic",
                                selected_action.params.get("task",
                                selected_action.params.get("thought", ""))))[:80]
                self.social_system.update_profile(
                    mood=mood, interest=interest, tick=t,
                    name=getattr(self, 'social_name', None),
                )
            except Exception:
                pass

        # 工作记忆更新（2026-07）：在 tick 末尾更新——追加步骤或创建新任务
        try:
            self._update_working_memory(selected_action, outcome, t)
        except Exception as e:
            logger.debug(f"工作记忆更新失败（非致命）: {e}")

        return episode

    def _update_working_memory(self, action, outcome, tick):
        """PHASE 12 后更新工作记忆。

        如果当前有活跃的工作记忆：
        - 追加这一步的结果到 steps
        - 如果动作不是 GROW/EXPLORE/USE_TOOL（不再是任务相关动作），标记完成

        如果没有工作记忆但 mind 决策了 GROW/EXPLORE（需要多步骤）：
        - 创建新的工作记忆 + 检索相关记忆
        """
        if self._working_memory and self._working_memory.get("status") == "active":
            # 追加这一步
            wm = self._working_memory
            step_desc = ""
            p = action.params or {}
            step_desc = p.get("topic", p.get("task", p.get("skill", p.get("thought", p.get("content", "")))))
            step_desc = str(step_desc)[:100] if step_desc else str(action.type)
            ok = outcome.get("ok", outcome.get("success", False)) if outcome else False
            wm["steps"].append({
                "tick": tick,
                "action": str(action.type),
                "desc": step_desc,
                "ok": ok,
            })
            wm["last_tick"] = tick

            # 如果动作类型偏离了任务（比如从 GROW 变成 SLEEP/CHAT/SOCIALIZE），标记完成
            task_type = wm.get("task_type", "")
            if task_type and action.type not in (task_type, ActionType.EXPLORE, ActionType.USE_TOOL, ActionType.GROW):
                wm["status"] = "completed"
                logger.info(f"[WM] 任务自然完成: {wm['task'][:40]}（{len(wm['steps'])} 步）")
                # 任务完成时——把整个工作记忆压缩成一条长程记忆写入 episodic
                # 这样下次检索能找到"我上次完整地做了 X，经历了这些步骤"，
                # 而不是零散的 12 条各自独立的 episode。
                try:
                    self._consolidate_working_memory(wm)
                except Exception as e:
                    logger.debug(f"工作记忆固化失败: {e}")
                self._working_memory = None
        else:
            # 没有工作记忆——如果 mind 决策了 GROW/EXPLORE，创建新的
            if action.params.get("source") == "mind_decision" and action.type in (ActionType.GROW, ActionType.EXPLORE):
                task_desc = ""
                p = action.params or {}
                task_desc = p.get("topic", p.get("task", ""))
                task_desc = str(task_desc)[:200] if task_desc else str(action.type)

                # 检索跟这个任务相关的记忆（一次检索，全程用）
                related = ""
                try:
                    if hasattr(self, 'episodic') and self.episodic:
                        retrieved = self.retrieval.retrieve_by_semantic_similarity(
                            task_desc, current_tick=tick, limit=3, min_similarity=0.1
                        )
                        if retrieved:
                            parts = []
                            for ep in retrieved[:3]:
                                status = ""
                                if ep.outcome and hasattr(ep.outcome, 'status'):
                                    status = str(ep.outcome.status or "")[:60]
                                parts.append(f"t{ep.tick}: {status}")
                            related = "; ".join(parts)
                except Exception:
                    pass

                self._working_memory = {
                    "task": task_desc,
                    "task_type": str(action.type),
                    "steps": [],
                    "related_memories": related,
                    "status": "active",
                    "created_tick": tick,
                    "last_tick": tick,
                }
                logger.info(f"[WM] 新任务: {task_desc[:50]}")

    def _consolidate_working_memory(self, wm: Dict[str, Any]):
        """任务完成时——把整个工作记忆压缩成一条长程记忆写入 episodic。

        这解决了"长程记忆"问题：任务做完后，12 个零散的 episode 各自独立，
        检索时只能找到碎片。固化后，一条完整的"任务总结"记忆被写入 episodic，
        下次检索能直接找到"我上次完整地做了 X"。

        压缩方式：用 LLM 把任务+所有步骤+结果总结成一段连贯的叙述。
        如果 LLM 失败，用规则式拼接（步骤列表）。
        """
        task = wm.get("task", "unknown task")
        steps = wm.get("steps", [])
        if not steps:
            return

        # 成功/失败统计
        ok_count = sum(1 for s in steps if s.get("ok"))
        total = len(steps)
        steps_desc = "; ".join(f"{s['action']}({s['desc'][:30]})" for s in steps)

        # 优先用 LLM 生成连贯的总结
        summary = ""
        try:
            from tools.llm_client import LLMClient
            client = getattr(self, '_global_llm_client', None) or LLMClient()
            result = client.chat(
                messages=[{"role": "user", "content": f"用一句话总结这个完成的任务（50字以内）：任务：{task}。经历{total}步({ok_count}成功)：{steps_desc[:300]}"}],
                temperature=0.3, max_tokens=80
            )
            if result.get("ok") and result.get("text"):
                summary = result["text"].strip()[:200]
        except Exception:
            pass

        # LLM 失败时用规则式
        if not summary:
            summary = f"完成了'{task[:60]}'，共{total}步（{ok_count}成功）。步骤：{steps_desc[:200]}"

        # 写入 episodic 记忆——作为一条完整的任务总结
        # 用 observation 的形式写入（这样它会被 PHASE 3 检索到）
        from common.models import Observation, Action as _Action, Outcome as _Outcome
        try:
            last_tick = wm.get("last_tick", self.state.tick)
            obs = Observation(
                type="task_completed",
                payload={"task": task[:200], "summary": summary, "steps": total, "success_rate": ok_count/total if total else 0},
                source_ref="working_memory_consolidation",
                tick=last_tick,
            )
            # 直接追加到 episodic——它会跟其他 episode 一样被检索到
            action_obj = _Action(type="GROW", params={"task": task[:100], "source": "consolidated"})
            outcome_obj = _Outcome(ok=ok_count > 0, status=f"[任务完成] {summary}")
            from common.models import EpisodeRecord
            import time as _time
            from datetime import datetime, timezone
            episode = EpisodeRecord(
                tick=last_tick,
                session_id=self.session_id,
                observation=obs,
                action=action_obj,
                outcome=outcome_obj,
                reward=float(ok_count) / max(total, 1),
                tags=["task_completed", "consolidated"],
            )
            self.episodic.append(episode)
            logger.info(f"[WM] 固化长程记忆: {summary[:60]}")
        except Exception as e:
            logger.debug(f"固化写入失败: {e}")

    def _run_working_memory_continuation(self, task, steps, related_memories, state_snapshot, context, tick):
        """工作记忆延续——mind 看到"我在做 X，已完成 Y"后决定下一步。

        不是重新决策"该做什么"，而是"我正在做这件事，下一步该做什么"。
        """
        mind = self.organs.get("mind")
        if not mind or not mind.enabled:
            return None

        # 构建 steps 摘要（最近 5 步）
        steps_text = ""
        if steps:
            parts = []
            for s in steps[-5:]:
                ok_mark = "✓" if s.get("ok") else "✗"
                parts.append(f"  t{s['tick']} {s['action']} {ok_mark}: {s['desc'][:50]}")
            steps_text = "\n".join(parts)

        # 按需回溯：检索跟当前任务相关的早期 episode（补上工作记忆窗口外的记忆）
        # 这样做到第 8 步时还能看到第 1-3 步的关键经历，不再是金鱼。
        recalled = related_memories  # 任务创建时检索的相关记忆
        try:
            if hasattr(self, 'episodic') and self.episodic:
                # 用任务关键词检索早期相关经历
                early = self.retrieval.retrieve_by_semantic_similarity(
                    task, current_tick=tick, limit=5, min_similarity=0.1
                )
                if early:
                    # 过滤掉已经在 steps_text 里的（避免重复）
                    step_ticks = {s.get("tick") for s in steps}
                    early_parts = []
                    for ep in early[:5]:
                        if ep.tick not in step_ticks:
                            status = ""
                            if ep.outcome and hasattr(ep.outcome, 'status'):
                                status = str(ep.outcome.status or "")[:60]
                            if status:
                                early_parts.append(f"t{ep.tick}: {status}")
                    if early_parts:
                        recalled = (recalled + "; " if recalled else "") + "; ".join(early_parts)
        except Exception:
            pass

        # 注入工作记忆到 context
        context["working_memory"] = {
            "task": task,
            "steps_summary": steps_text,
            "related_memories": recalled,
        }

        try:
            actions = mind.propose_actions(state_snapshot, context)
            if actions:
                final = actions[0]
                final.params["source"] = "mind_decision"
                p = final.params or {}
                desc = p.get("topic") or p.get("task") or p.get("skill") or p.get("thought") or p.get("content") or ""
                logger.info(f"[MIND] 继续决策: {final.type} | {str(desc)[:50]}")
                return final
        except Exception as e:
            logger.warning(f"工作记忆延续失败: {e}")

        return None

    def _run_decision_center(self, proposed_actions, state_snapshot, context, observations, tick):
        """PHASE 7.5: mind 器官做最终决策。

        其他 5 个器官各自思考完毕、产出了提议。mind 作为决策器官，
        看到所有器官的建议后做最终裁决。

        mind 跟其他器官一样有 LLM session，但它的 prompt 里多了
        "其他器官的建议"——这让 mind 从全局视角决策，而不是只看自己的专业领域。
        """
        if not proposed_actions:
            return None

        mind = self.organs.get("mind")
        if not mind or not mind.enabled:
            return None

        # 把其他器官的提议注入 context，让 mind 的 prompt 能看到
        suggestions = []
        for a in proposed_actions[:10]:
            p = a.params or {}
            desc = p.get("topic", p.get("task", p.get("skill", p.get("thought", p.get("content", "")))))
            desc = str(desc)[:200] if desc else ""
            suggestions.append(f"{a.type.value}: {desc}")
        context["organ_suggestions"] = suggestions

        # 否决记录注入——让 mind 看见上次的边界。之前五道闸门静默改判，
        # mind 永远不知道自己的决定被换掉了，也就永远学不会边界在哪。
        veto_note = getattr(self, "_last_veto_note", None)
        if veto_note and self.state.tick - veto_note[0] <= 3:
            context["last_veto_note"] = veto_note[1]

        # 社交消息也注入
        social_parts = []
        for obs in observations:
            obs_type = getattr(obs, "type", "") if not isinstance(obs, dict) else obs.get("type", "")
            if obs_type in ("world_news", "social_group", "social_private"):
                payload = getattr(obs, "payload", {}) if not isinstance(obs, dict) else obs.get("payload", {})
                if obs_type == "world_news":
                    headlines = payload.get("headlines", [])
                    if headlines:
                        social_parts.append(f"新闻: {headlines[0][:200]}")
                elif obs_type in ("social_group", "social_private"):
                    msgs = payload.get("messages", [])
                    for m in msgs[:2]:
                        social_parts.append(f"{m.get('from', '?')}: {str(m.get('content', ''))[:200]}")
        context["social_feed"] = social_parts

        # 让 mind 重新思考（这次它能看到其他器官的建议）
        try:
            actions = mind.propose_actions(state_snapshot, context)
            if actions:
                final = actions[0]
                final.params["source"] = "mind_decision"
                p = final.params or {}
                # 清理 CoT 残留——mind 的输出里可能混了推理过程
                for key in ("topic", "task", "skill", "thought", "content"):
                    val = p.get(key, "")
                    if val and isinstance(val, str):
                        # 去掉常见 CoT 开头
                        import re as _re
                        val = _re.sub(r'^[\d.]+\s*', '', val)  # "1. " 开头
                        val = _re.sub(r'^(我现在最想|我还是|哦对|等下|首先|然后|所以|最终)[，。：\s]*', '', val)
                        val = val.strip("。.，,；;")
                        # 清理后太短或仍残留动作标记才置空。
                        # 宽松化（之前 "等下/哦对" 出现在正常句子里也会整段置空，误杀正文）
                        if len(val) < 3 or "【动作" in val:
                            val = ""
                        p[key] = val[:400]
                # SOCIALIZE 如果 content 为空，让 mind 用 agentic loop 生成
                if final.type == ActionType.SOCIALIZE and not p.get("content"):
                    p["content"] = ""  # _execute_socialize 会处理空 content
                desc = p.get("topic") or p.get("task") or p.get("skill") or p.get("thought") or p.get("content") or ""
                logger.info(f"[MIND] 决策: {final.type} | {str(desc)[:50]}")
                return final
        except Exception as e:
            logger.warning(f"mind 决策失败: {e}")

        return None

    def _record_organ_learning(self, t: int, goal, action, outcome: Dict[str, Any], reward: float):
        """PHASE 11.5: 将动作结果反馈给器官，触发 record_* 学习 (P5-21)。

        根据 action.type 路由到对应器官的 record_* 方法。
        所有调用包在 try/except 里——学习反馈失败不影响 tick 主流程。
        """
        success = outcome.get("success", outcome.get("ok", True))
        action_type = action.type.value if hasattr(action.type, "value") else str(action.type)
        goal_desc = goal.description if hasattr(goal, "description") else str(goal)

        try:
            # 1. Immune: 所有动作都更新动作信任分数
            self.organs["immune"].update_action_trust(action_type, success)

            # 2. Caretaker: 记录健康趋势（每 tick）
            caretaker = self.organs["caretaker"]
            caretaker.update_health_state("stress", self.fields.get("stress"))
            caretaker.update_health_state("energy", self.fields.get("energy"))

            # 3. Mind: 记录计划/认知动作的结果（所有有意识的动作）
            cognitive_actions = ("THINK", "REFLECT", "CHAT", "EXPLORE",
                                 "LEARN_SKILL", "GROW", "OPTIMIZE", "USE_TOOL")
            if action_type in cognitive_actions:
                self.organs["mind"].record_plan_outcome(t, goal_desc, action_type, success)

            # 4. Scout: 记录探索结果
            if action_type == "EXPLORE":
                params = getattr(action, "params", {}) or {}
                topic = params.get("topic", goal_desc)
                depth = params.get("depth", "shallow")
                self.organs["scout"].record_exploration_outcome(t, topic, depth, success)

            # 5. Builder: 记录工作 session（构建/优化/工具类动作）
            if action_type in ("GROW", "OPTIMIZE", "USE_TOOL"):
                # reward ∈ [-1, 1] 映射到 productivity ∈ [0, 1]
                productivity = max(0.0, min(1.0, (reward + 1.0) / 2.0))
                self.organs["builder"].record_work_session(t, 1, productivity)

        except Exception as e:
            logger.warning(f"Organ learning feedback failed (tick {t}): {e}")

    # ===== P5-21 Step2: 器官学习状态持久化 =====

    # 每个器官的"可学习属性"白名单——只持久化这些，跳过 config/LLM session/瞬态字段
    _ORGAN_LEARNING_ATTRS = {
        "mind": {"plan_history", "goal_decompositions", "strategy_success_rates",
                 "successful_patterns", "failed_patterns"},
        "scout": {"explored_topics", "recent_explorations", "topic_interest_scores",
                  "knowledge_frontier", "mastered_topics", "failed_explorations",
                  "successful_exploration_count", "total_exploration_count",
                  "novelty_seeking_level", "mode_success_rates"},
        "builder": {"active_projects", "completed_projects", "milestone_history",
                    "task_queue", "completed_tasks", "blocked_tasks", "task_dependencies",
                    "work_sessions", "productivity_scores", "strategy_effectiveness"},
        "caretaker": {"energy_history", "stress_history", "_health_state"},
        "archivist": {"memory_count", "episodic_count", "semantic_count",
                      "memory_categories", "consolidation_history",
                      "consolidated_memory_groups", "pruned_count", "retention_scores",
                      "memory_access_frequency", "recent_accesses", "access_patterns",
                      "memory_importance", "critical_memories", "memory_index",
                      "memory_tags", "tag_usage", "strategy_effectiveness",
                      "consolidation_quality_scores", "retrieval_success_rate"},
        "immune": {"risk_history", "threat_log", "veto_history", "threat_count",
                   "recent_incidents", "suspicious_patterns", "safe_patterns",
                   "behavior_baseline", "action_trust_scores", "capability_trust",
                   "trust_violations", "incident_count", "false_positive_count",
                   "false_negative_count"},
    }

    def _get_organ_state_path(self) -> Path:
        """器官状态持久化路径：artifacts/organ_state/{session_id}.json

        跨 run 保留（不依赖 run_dir），与 session_id 关联。
        """
        state_dir = Path("artifacts") / "organ_state"
        state_dir.mkdir(parents=True, exist_ok=True)
        return state_dir / f"{self.session_id}.json"

    @staticmethod
    def _serialize_for_json(obj):
        """处理 sets/deques/defaultdicts/tuples 等 JSON 不支持的类型。"""
        import collections
        if isinstance(obj, (set, frozenset)):
            return {"__type__": "set", "items": list(obj)}
        if isinstance(obj, collections.deque):
            return {"__type__": "deque", "items": list(obj)}
        if isinstance(obj, dict):
            return {str(k): LifeLoop._serialize_for_json(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [LifeLoop._serialize_for_json(v) for v in obj]
        if isinstance(obj, tuple):
            return {"__type__": "tuple", "items": list(obj)}
        return obj

    @staticmethod
    def _deserialize_from_json(obj):
        """逆操作：还原 sets/deques/tuples。"""
        import collections
        if isinstance(obj, dict):
            if obj.get("__type__") == "set":
                return set(obj["items"])
            if obj.get("__type__") == "deque":
                return collections.deque(obj["items"])
            if obj.get("__type__") == "tuple":
                return tuple(obj["items"])
            return {k: LifeLoop._deserialize_from_json(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [LifeLoop._deserialize_from_json(v) for v in obj]
        return obj

    def _save_organ_state(self):
        """保存所有器官的学习状态到磁盘 (P5-21)。"""
        state = {}
        for organ_name, attr_names in self._ORGAN_LEARNING_ATTRS.items():
            organ = self.organs.get(organ_name)
            if organ is None:
                continue
            organ_state = {}
            for attr_name in attr_names:
                if hasattr(organ, attr_name):
                    value = getattr(organ, attr_name)
                    organ_state[attr_name] = self._serialize_for_json(value)
            state[organ_name] = organ_state

        state_path = self._get_organ_state_path()
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        logger.info(f"Organ learning state saved to {state_path}")

    def _load_organ_state(self):
        """从磁盘恢复器官学习状态 (P5-21)。在器官构造后调用。"""
        state_path = self._get_organ_state_path()
        if not state_path.exists():
            logger.debug(f"No organ state file at {state_path}, starting fresh")
            return

        try:
            with open(state_path, "r", encoding="utf-8") as f:
                state = json.load(f)

            restored_count = 0
            for organ_name, organ_state in state.items():
                organ = self.organs.get(organ_name)
                if organ is None:
                    continue
                for attr_name, value in organ_state.items():
                    if hasattr(organ, attr_name):
                        setattr(organ, attr_name, self._deserialize_from_json(value))
                        restored_count += 1

            logger.info(f"Organ learning state restored from {state_path} ({restored_count} attrs)")
        except Exception as e:
            logger.warning(f"Failed to load organ state: {e}, starting fresh")

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

        # 获取昼夜节律调整系数 (P4-53/54: 传 tick 使 simulation 模式生效，与 caretaker 时钟一致)
        circadian_energy = self.circadian.get_energy_level(tick=self.state.tick)
        recovery_rate = self.circadian.get_fatigue_recovery_rate(tick=self.state.tick)

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

        # 疲劳：自然累积 + 昼夜节律恢复
        # activity_fatigue 每 tick 累积（用于触发做梦），fatigue 同步（展示/器官用）
        self.state.activity_fatigue = min(1.0, self.state.activity_fatigue + 0.01 * dt)
        new_fatigue = max(self.state.activity_fatigue - 0.005 * dt * recovery_rate, 0.0)

        # Stress 更新移至 Affect Phase，这里保持当前值不变
        #
        # 阶段1.1 修复（2026-07）：原 P4-50 把 novelty 写死为 0.5（"阻止 ETA_IDLE 空转"），
        # 但这把整个 novelty→boredom 通路切断了——boredom 永不累积，系统永远不无聊、
        # 永远不探索。现改用 PHASE 5 缓存的真实 novelty（self._last_novelty，来自
        # curiosity gap 的补数）。novelty 低（<0.2）时 ETA_IDLE 触发，boredom 自然累积。
        #
        # P5-XX 修复（2026-07）：原逻辑只看"上 tick 是 CHAT 且成功"，但 heartbeat 自循环
        # CHAT（无真用户，_generate_contextual_greeting 自己生成消息）也被算社交，
        # 导致 boredom 永远被 η_soc 削减，系统陷入 CHAT 死循环无法触发探索。
        # 现增加观察：只有 observation.type == "user_chat"（真用户消息）才算社交。
        socially_engaged = False
        try:
            recent = self.episodic.query_recent(1)
            if recent and recent[0].action and recent[0].action.type == "CHAT":
                is_user_chat = (
                    recent[0].observation is not None
                    and getattr(recent[0].observation, "type", None) == "user_chat"
                )
                socially_engaged = (
                    is_user_chat
                    and recent[0].outcome is not None
                    and recent[0].outcome.ok
                )
        except Exception:
            pass
        # 阶段1.1: novelty 的代谢更新（持续衰减）。
        # 真实 novelty 应来自记忆检索相似度（memory/semantic_novelty.py），但当前 life_loop
        # 没接检索结果（阶段2 会接）。在无真实外部输入时，novelty 持续衰减——
        # 旧东西越来越不新，符合"没新输入就该无聊"的直觉。
        # EXPLORE/USE_TOOL 成功后会重置 novelty 回高值（见 action_executor._execute_explore）。
        # 衰减率 NOVELTY_DECAY_RATE=0.02：每 tick novelty 减 2%，约 35 tick 从 0.5 降到 0.2。
        NOVELTY_DECAY_RATE = 0.02
        new_novelty = max(0.0, self._last_novelty - NOVELTY_DECAY_RATE * dt)
        new_novelty = max(0.0, min(1.0, new_novelty))
        self._last_novelty = new_novelty  # 更新缓存，下 tick 从这里继续衰减

        # 注意：不再乘 0.5（原 dt*0.5 把 boredom 累积减半，导致永远涨不到触发阈值）。
        # dt=1.0 时 boredom 每 tick 增 0.03，约 8 tick 到 0.25 触发记忆漫游。
        new_boredom = update_boredom(boredom, dt, novelty=new_novelty, socially_engaged=socially_engaged)

        # 阶段X（2026-07）：curiosity 衰减。
        # 问题：curiosity 只在 EXPLORE 时 +0.05，从不下降，导致一路涨到 1.0 饱和，
        # 系统被好奇绑架"停不下来"（累了还硬撑着探索/学习）。
        # 修复：curiosity 每 tick 向基线（CURIOSITY_BASELINE=0.4）缓慢回落。
        # 语义：探索的满足感会随时间消退——你今天满足了的好奇，过段时间又会重新好奇。
        # 衰减率小（0.008/tick），约 60 tick 从 1.0 回落到 0.5，不会过快扼杀探索欲。
        # EXPLORE 时 +0.05 仍然有效（净效应：频繁探索能维持高 curiosity，停下后自然回落）。
        CURIOSITY_BASELINE = 0.4
        CURIOSITY_DECAY_RATE = 0.008
        curiosity_current = self.fields.get("curiosity") or 0.5
        if curiosity_current > CURIOSITY_BASELINE:
            curiosity_current = max(CURIOSITY_BASELINE, curiosity_current - CURIOSITY_DECAY_RATE * dt)
        elif curiosity_current < CURIOSITY_BASELINE:
            curiosity_current = min(CURIOSITY_BASELINE, curiosity_current + CURIOSITY_DECAY_RATE * dt * 0.5)
        self.fields.set("curiosity", curiosity_current)

        # 阶段X（2026-07）：mood 衰减（向基线回归）。
        # 问题：update_mood 只有正/负 RPE 增减，没有自然回归基线的机制。
        # 当大部分动作 reward 偏正时（LEARN_SKILL/THINK 等），mood 只涨不跌直到 1.0 饱和，
        # 之后 80+ tick 不动，情绪失去表达力。
        # 修复：mood 每 tick 向基线（MOOD_BASELINE=0.5）缓慢回落。
        # 语义：好心情会慢慢淡忘——你不会因为一件开心事兴奋一整天，情绪自然回归中性。
        # PHASE 11 的 update_mood 仍然有效（正 RPE 推高，负 RPE 拉低），衰减只是加个"重力"。
        # 衰减率 0.01/tick：约 50 tick 从 1.0 回落到 0.5，不会过快抹杀好心情。
        MOOD_BASELINE = 0.5
        MOOD_DECAY_RATE = 0.01
        mood_current = self.fields.get("mood") or 0.5
        if mood_current > MOOD_BASELINE:
            mood_current = max(MOOD_BASELINE, mood_current - MOOD_DECAY_RATE * dt)
        elif mood_current < MOOD_BASELINE:
            mood_current = min(MOOD_BASELINE, mood_current + MOOD_DECAY_RATE * dt * 0.5)
        self.fields.set("mood", mood_current)

        # 疲劳恢复率受昼夜节律影响
        if new_fatigue < fatigue:
            recovery_amount = fatigue - new_fatigue
            recovery_amount *= recovery_rate
            new_fatigue = fatigue - recovery_amount

        # P8-4: 直接写 FieldStore（GlobalState 自动反映，无需手工同步）
        # Stress 将在 Affect Phase 更新
        self.fields.set("energy", new_energy)
        self.fields.set("fatigue", new_fatigue)
        self.fields.set("stress", stress)
        self.fields.set("boredom", new_boredom)
        # 把 novelty 写进 fields，让 PHASE 2 的 field_snapshot 包含它，
        # PHASE 5 的 extract_curiosity 能读到真实 novelty（state.get("novelty")），
        # 不再走 fallback。
        self.fields.set("novelty", new_novelty)

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

        # 修复 P3-5: 关闭前持久化 Schema/Skill 记忆
        # 巩固产生的图式/技能此前只在内存，进程结束即丢失
        try:
            if hasattr(self, 'schema') and self.schema:
                self.schema.save_to_disk()
                logger.debug("Schema memory persisted")
        except Exception as e:
            logger.error(f"Error persisting schema memory: {e}")

        try:
            if hasattr(self, 'skill') and self.skill:
                self.skill.save_to_disk()
                logger.debug("Skill memory persisted")
        except Exception as e:
            logger.error(f"Error persisting skill memory: {e}")

        # P3-1/P3-2: 关闭 episodic 常驻 JSONLWriter（迁移自原手写 open/append/close）
        try:
            if hasattr(self, 'episodic') and self.episodic:
                self.episodic.close()
                logger.debug("Episodic writer closed")
        except Exception as e:
            logger.error(f"Error closing episodic writer: {e}")

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

        # P5-21: 持久化器官学习状态（跨 run 保留）
        try:
            self._save_organ_state()
        except Exception as e:
            logger.error(f"Error persisting organ state: {e}")

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
            # P8-4: state.<scalar> 现在委托 FieldStore，单一真相源——不再写两遍
            state_dict = {
                "tick": self.state.tick,
                "mode": self.state.mode,
                "stage": self.state.stage,
                # 情感标量（读 FieldStore via GlobalState 委托）
                "energy": self.state.energy,
                "mood": self.state.mood,
                "stress": self.state.stress,
                "fatigue": self.state.fatigue,
                "bond": self.state.bond,
                "trust": self.state.trust,
                "boredom": self.state.boredom,
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
