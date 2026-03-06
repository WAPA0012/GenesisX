"""Genesis X Web UI

Flask-based web interface for Genesis X digital life system.
Provides a graphical user interface for interaction and monitoring.
"""

import sys
import os
import time
import threading
import logging
from pathlib import Path
import requests
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import json
from threading import Lock
import queue

# Load .env file from project root
from dotenv import load_dotenv
# Find .env file in project root (parent of web/ directory)
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

logger = logging.getLogger(__name__)

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from flask_cors import CORS

# Genesis X imports
from core.life_loop import LifeLoop
from core.state import GlobalState
from common.config import load_config
from common.models import Action, ActionType, Observation, EpisodeRecord


# ============================================================================
# Flask Application
# ============================================================================

app = Flask(__name__)

# ============================================================================
# 安全配置
# ============================================================================

def _validate_production_security():
    """验证生产环境安全配置"""
    # 检测是否为生产环境
    is_production = os.environ.get('FLASK_ENV', 'development') == 'production'
    is_docker = os.path.exists('/.dockerenv')
    is_render = os.environ.get('RENDER', '') == 'true'
    is_heroku = os.environ.get('DYNO', '') != ''

    return is_production or is_docker or is_render or is_heroku

_IS_PRODUCTION = _validate_production_security()

# SECRET_KEY 配置
secret_key = os.environ.get('SECRET_KEY')
if not secret_key:
    if _IS_PRODUCTION:
        raise RuntimeError(
            "CRITICAL: SECRET_KEY environment variable must be set in production! "
            "Generate a secure key with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    else:
        import warnings
        warnings.warn(
            "SECRET_KEY not set. Using insecure dev key. DO NOT USE IN PRODUCTION!",
            RuntimeWarning,
            stacklevel=2
        )
        # 开发环境使用固定key便于调试，生产环境必须设置
        secret_key = 'dev-insecure-key-do-not-use-in-production-please'

app.config['SECRET_KEY'] = secret_key

# CORS 配置
cors_origins_str = os.environ.get('CORS_ORIGINS', '')
if cors_origins_str:
    cors_origins = [origin.strip() for origin in cors_origins_str.split(',') if origin.strip()]
else:
    cors_origins = []

if cors_origins:
    CORS(app, origins=cors_origins)
    logger.info(f"CORS configured for origins: {cors_origins}")
elif _IS_PRODUCTION:
    raise RuntimeError(
        "CRITICAL: CORS_ORIGINS environment variable must be set in production! "
        "Example: CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com"
    )
else:
    import warnings
    warnings.warn(
        "CORS_ORIGINS not set, allowing all origins. This is insecure for production!",
        RuntimeWarning,
        stacklevel=2
    )
    # 开发环境允许localhost
    CORS(app, origins=["http://localhost:*", "http://127.0.0.1:*"])

# Global state
genesis_instance: Optional[LifeLoop] = None
message_queue: queue.Queue = queue.Queue()
state_lock = Lock()

# Progress tracking for SSE
progress_queues: Dict[str, queue.Queue] = {}
progress_lock = Lock()


# ============================================================================
# Multi-Model Adapter
# ============================================================================

class MultiModelAdapter:
    """适配器：将 LLMOrchestrator 包装为与单模型 LLM 兼容的接口

    这样 GenesisXManager 可以统一使用 self.llm 而不需要关心底层是单模型还是多模型。
    """

    def __init__(self, orchestrator):
        """初始化适配器

        Args:
            orchestrator: LLMOrchestrator 实例
        """
        self._orchestrator = orchestrator
        self._mode = orchestrator.config_mode if orchestrator else "single"

    def generate(self, prompt: str, max_tokens: int = 2000, temperature: float = 0.7) -> str:
        """生成文本（兼容单模型接口）

        Args:
            prompt: 输入提示
            max_tokens: 最大 token 数
            temperature: 温度参数

        Returns:
            生成的文本
        """
        messages = [{"role": "user", "content": prompt}]

        result = self._orchestrator.chat(
            messages,
            max_tokens=max_tokens,
            temperature=temperature
        )

        if result.get("ok"):
            return result.get("text", "")
        else:
            error = result.get("error", "Unknown error")
            logger.error(f"MultiModelAdapter generate error: {error}")
            raise Exception(error)

    def chat(self, messages: List[Dict], tools: Optional[List[Dict]] = None, **kwargs) -> Dict[str, Any]:
        """聊天接口（兼容单模型接口）

        Args:
            messages: 消息列表
            tools: 工具列表
            **kwargs: 额外参数

        Returns:
            响应字典
        """
        return self._orchestrator.chat(messages, tools=tools, **kwargs)

    @property
    def mode(self) -> str:
        """获取当前模式"""
        return self._mode

    @property
    def orchestrator(self):
        """获取底层编排器"""
        return self._orchestrator

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self._orchestrator.get_statistics()


# ============================================================================
# Genesis X Manager
# ============================================================================

class GenesisXManager:
    """Manages Genesis X instance for web UI.

    支持主动对话：数字生命可以在没有用户输入时主动发起对话。
    """

    # 主动对话的触发阈值
    INITIATIVE_THRESHOLDS = {
        "curiosity": 0.60,      # 好奇心高时主动提问
        "attachment": 0.55,     # 依恋高时主动表达
        "boredom": 0.50,        # 无聊时主动找话题
        "loneliness": 0.50,     # 孤独时主动联系
    }

    # 主动对话的最小间隔（秒），避免太频繁
    MIN_INITIATIVE_INTERVAL = 60

    def __init__(self):
        self.life_loop: Optional[LifeLoop] = None
        self.is_running = False
        self.messages: List[Dict] = []
        self._pending_user_input: Optional[str] = None  # 存储待处理的用户输入
        self.tool_executor = None  # 工具执行器
        self.llm = None  # LLM 客户端
        self.llm_available = False  # LLM 是否可用

        # 主动对话相关
        self._initiative_queue: List[Dict] = []  # 主动消息队列
        self._last_initiative_time: float = 0  # 上次主动说话时间
        self._last_user_interaction: float = time.time()  # 上次用户交互时间
        self._initiative_lock = threading.Lock()  # 线程锁

        # 实时活动日志（像 Claude Code 一样显示系统在做什么）
        self._activity_log: List[Dict] = []  # 活动日志列表
        self._activity_lock = threading.Lock()  # 日志锁
        self._max_activity_logs = 200  # 最大日志条数

    def log_activity(self, activity_type: str, message: str, details: Dict = None):
        """记录系统活动

        Args:
            activity_type: 活动类型 (thinking, tool_call, phase_change, etc.)
            message: 活动描述
            details: 额外详情
        """
        with self._activity_lock:
            log_entry = {
                "type": activity_type,
                "message": message,
                "details": details or {},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            self._activity_log.append(log_entry)

            # 限制日志大小
            if len(self._activity_log) > self._max_activity_logs:
                self._activity_log = self._activity_log[-self._max_activity_logs:]

    def get_activity_logs(self, since: int = 0) -> List[Dict]:
        """获取活动日志

        Args:
            since: 从第几条开始返回（用于增量获取）

        Returns:
            日志列表
        """
        with self._activity_lock:
            if since < len(self._activity_log):
                return self._activity_log[since:]
            return []

    def clear_activity_logs(self):
        """清空活动日志"""
        with self._activity_lock:
            self._activity_log.clear()

    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize Genesis X with configuration.

        Args:
            config: Configuration dictionary

        Returns:
            True if successful
        """
        try:
            from pathlib import Path
            run_dir = Path("artifacts/web_run")

            self.life_loop = LifeLoop(config=config, run_dir=run_dir)

            # 初始化工具执行器
            safe_mode = config.get("runtime", {}).get("safe_mode", False)
            from tools.tool_executor import LLMToolExecutor
            self.tool_executor = LLMToolExecutor(safe_mode=safe_mode)

            # 将工具执行器传递给 LifeLoop
            self.life_loop.tool_executor = self.tool_executor

            # 初始化 LLM
            self._init_llm(config)

            return True
        except Exception as e:
            self.messages.append({
                "type": "error",
                "content": f"初始化失败: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            return False

    def _init_llm(self, config: Dict[str, Any]):
        """初始化 LLM 客户端

        根据环境变量 LLM_MODE 选择模式:
        - single: 单模型模式（默认）
        - core5: Core5 多模型模式
        - full7: Full7 完整模式
        - adaptive: 自适应模式
        """
        llm_mode = os.environ.get('LLM_MODE', 'single').lower()
        valid_modes = ['single', 'core5', 'full7', 'adaptive']

        if llm_mode not in valid_modes:
            logger.warning(f"Invalid LLM_MODE: {llm_mode}, using 'single'")
            llm_mode = 'single'

        logger.info(f"Initializing LLM in {llm_mode} mode")

        if llm_mode == 'single':
            # 单模型模式：使用传统的单客户端
            self._init_single_llm()
        else:
            # 多模型模式：使用 LLMOrchestrator
            self._init_multi_model_llm(llm_mode, config)

    def _init_single_llm(self):
        """初始化单模型 LLM 客户端"""
        try:
            from tools.llm_api import create_llm_from_env
            self.llm = create_llm_from_env()
            self.llm_available = True
            self._llm_orchestrator = None
            logger.info("Single model LLM initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize single model LLM: {e}")
            try:
                from tools.llm_client import LLMClient
                self.llm = LLMClient()
                self.llm_available = True
                self._llm_orchestrator = None
            except Exception as e2:
                logger.error(f"Failed to initialize fallback LLM: {e2}")
                self.llm = None
                self.llm_available = False
                self._llm_orchestrator = None

    def _init_multi_model_llm(self, mode: str, config: Dict[str, Any]):
        """初始化多模型 LLM 编排器

        Args:
            mode: 配置模式 (core5/full7/adaptive)
            config: 配置字典
        """
        try:
            from tools.llm_orchestrator import LLMOrchestrator

            # 尝试从配置文件加载多模型配置
            config_path = self._find_multi_model_config()

            if config_path:
                self._llm_orchestrator = LLMOrchestrator(
                    enable_multi_model=True,
                    config_mode=mode,
                    config_path=config_path
                )
            else:
                # 如果没有配置文件，尝试从环境变量构建配置
                self._llm_orchestrator = LLMOrchestrator(
                    enable_multi_model=True,
                    config_mode=mode,
                    config=self._build_multi_model_config_from_env()
                )

            # 对于 chat 接口，我们使用 orchestrator 的 chat 方法
            # 但也保持兼容性，设置 self.llm 为一个适配器
            self.llm = MultiModelAdapter(self._llm_orchestrator)
            self.llm_available = True
            logger.info(f"Multi-model LLM initialized in {mode} mode")

        except Exception as e:
            logger.error(f"Failed to initialize multi-model LLM: {e}, falling back to single model")
            self._init_single_llm()

    def _find_multi_model_config(self) -> Optional[str]:
        """查找多模型配置文件"""
        from pathlib import Path
        config_paths = [
            "config/multi_model.yaml",
            "config/mind_field.yaml",
        ]

        # 检查项目根目录
        project_root = Path(__file__).parent.parent
        for path in config_paths:
            full_path = project_root / path
            if full_path.exists():
                logger.info(f"Found multi-model config: {full_path}")
                return str(full_path)

        return None

    def _build_multi_model_config_from_env(self) -> Dict[str, Any]:
        """从环境变量构建多模型配置

        当没有配置文件时，从环境变量读取专家模型配置。
        """
        config = {
            "mind_field": {
                "enabled": True,
                "config_mode": os.environ.get('LLM_MODE', 'core5')
            },
            "experts": []
        }

        # 专家模型列表
        experts = [
            ("m_coord", "coordinator", "协调者"),
            ("m_mem", "memory", "记忆"),
            ("m_reason", "reasoner", "推理"),
            ("m_affect", "affective", "情感"),
            ("m_percept", "perception", "感知"),
        ]

        for expert_key, role, name in experts:
            expert_upper = expert_key.upper()
            api_base = os.environ.get(f'{expert_upper}_API_BASE', '')
            api_key = os.environ.get(f'{expert_upper}_API_KEY', '')
            model = os.environ.get(f'{expert_upper}_MODEL', '')

            # 只有配置了 API 的专家才启用
            if api_base and api_key:
                config["experts"].append({
                    "name": name,
                    "role": role,
                    "enabled": True,
                    "model": model or os.environ.get('LLM_MODEL', 'gpt-4'),
                    "api_base": api_base,
                    "api_key": api_key,
                    "provider": "openai",  # 默认使用 OpenAI 兼容接口
                    "temperature": 0.7,
                    "max_tokens": 2000,
                    "priority": 0
                })

        # 如果没有配置任何专家，使用全局配置作为单一专家
        if not config["experts"]:
            global_api_base = os.environ.get('LLM_API_BASE', '')
            global_api_key = os.environ.get('LLM_API_KEY', '')
            global_model = os.environ.get('LLM_MODEL', '')

            if global_api_base and global_api_key:
                config["experts"].append({
                    "name": "general",
                    "role": "coordinator",
                    "enabled": True,
                    "model": global_model,
                    "api_base": global_api_base,
                    "api_key": global_api_key,
                    "provider": "openai",
                    "temperature": 0.7,
                    "max_tokens": 2000,
                    "priority": 0
                })

        return config

    def get_llm_mode(self) -> str:
        """获取当前 LLM 模式"""
        return os.environ.get('LLM_MODE', 'single')

    def get_llm_statistics(self) -> Dict[str, Any]:
        """获取 LLM 统计信息（多模型模式下）"""
        if hasattr(self, '_llm_orchestrator') and self._llm_orchestrator:
            return self._llm_orchestrator.get_statistics()
        return {
            "mode": "single",
            "multi_model_enabled": False
        }

    def send_message(self, message: str, user: str = "User") -> str:
        """Send a message to Genesis X and get response.

        支持 LLM Function Calling 工具调用流程。

        Args:
            message: User message
            user: User name

        Returns:
            Genesis X response
        """
        if self.life_loop is None:
            return "系统未初始化"

        # 更新用户交互时间
        self._update_user_interaction()

        try:
            # 存储用户输入到临时变量
            self._pending_user_input = message

            # 设置 get_user_input 回调
            def get_user_input_callback():
                result = self._pending_user_input
                self._pending_user_input = None  # 清除
                return result

            # 设置回调
            self.life_loop.get_user_input = get_user_input_callback

            # Add user message to history
            self.messages.append({
                "type": "user",
                "content": message,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

            # 使用 LLM Function Calling 处理消息
            response = self._process_with_llm(message)

            # Add assistant message to history
            self.messages.append({
                "type": "assistant",
                "content": response,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

            # 在后台尝试预生成下一条主动消息
            # 这样即使 auto-run 关闭，用户也能在一段时间后看到主动消息
            try:
                self.try_generate_initiative_async()
            except Exception as e:
                logger.warning(f"Failed to pre-generate initiative: {e}")

            return response

        except Exception as e:
            error_msg = f"处理消息时出错: {str(e)}"
            import traceback
            logger.error(f"[send_message] Exception: {e}")
            logger.error(f"[send_message] Traceback: {traceback.format_exc()}")
            self.messages.append({
                "type": "error",
                "content": error_msg,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            return error_msg

    def _process_with_llm(self, message: str) -> str:
        """使用完整的 GenesisX 生命循环处理消息

        保持完整的16阶段tick，但优化内部性能。

        Args:
            message: 用户消息

        Returns:
            AI 响应
        """
        import time as _time
        start_time = _time.time()

        # 记录处理开始
        self.log_activity("thinking", "正在分析用户消息...", {
            "message_length": len(message),
            "current_tick": self.life_loop.state.tick
        })

        # 修复: 递增 tick 确保每次对话都是新的时间步
        # 这样 episodes 不会被覆盖，记忆才能正确累积
        current_tick = self.life_loop.state.tick
        next_tick = current_tick + 1

        # 记录阶段变化
        initial_phase = getattr(self.life_loop, '_current_phase', 'unknown')
        self.log_activity("phase_change", f"开始 Tick {next_tick}", {
            "from_phase": initial_phase,
            "tick": next_tick
        })

        # 执行完整的 LifeLoop.tick() - GenesisX 的核心循环
        # 包含：观察 → 记忆检索 → 价值评估 → 器官决策 → 行动
        result = self.life_loop.tick(t=next_tick)

        # 记录执行结果
        elapsed = _time.time() - start_time
        final_phase = getattr(self.life_loop, '_current_phase', 'unknown')
        self.log_activity("phase_complete", f"Tick {next_tick} 完成 ({elapsed:.2f}s)", {
            "phase": final_phase,
            "action_type": result.action.type.value if result.action else "none",
            "reward": result.reward,
            "elapsed": elapsed
        })

        return self._extract_response(result)

    def _extract_response(self, episode: EpisodeRecord) -> str:
        """Extract response from episode result."""
        try:
            if episode.action and episode.action.type == ActionType.CHAT:
                # First try to get from outcome.status (where LLM response is stored)
                if episode.outcome is not None and hasattr(episode.outcome, 'status') and episode.outcome.status:
                    return episode.outcome.status
                # Fallback to action.params
                params = episode.action.params
                if params is not None:
                    response = params.get("response", "") if isinstance(params, dict) else ""
                    if response:
                        return response
                return "（无响应）"
            return "（执行了其他动作）"
        except Exception as e:
            logger.error(f"[_extract_response] Error: {e}")
            import traceback
            logger.error(f"[_extract_response] Traceback: {traceback.format_exc()}")
            return f"（提取响应时出错: {str(e)}）"

    def get_state(self) -> Dict[str, Any]:
        """Get current Genesis X state.

        Returns:
            State dictionary
        """
        if self.life_loop is None:
            return {"status": "not_initialized"}

        state = self.life_loop.state

        # Get value dimension weights (5维价值)
        weights = {}
        for dim, value in state.weights.items():
            weights[dim.value] = value

        # Get organs status (6个器官)
        organs = {}
        for name, organ in self.life_loop.organs.items():
            organs[name] = {
                "active": organ.enabled,
                "type": organ.__class__.__name__
            }

        # Get current cycle stage
        current_stage = getattr(self.life_loop, '_current_phase', 'unknown')

        return {
            "status": "running" if self.is_running else "idle",
            "tick": state.tick,
            "energy": state.energy,
            "mood": state.mood,
            "stress": state.stress,
            "fatigue": state.fatigue,
            "bond": state.bond,
            "trust": state.trust,
            "boredom": state.boredom,
            "mode": state.mode,
            "stage": state.stage,
            "current_goal": getattr(state, 'current_goal', None),
            # 系统资源状态（真实检测）
            "compute": getattr(state, 'compute', 0.0),
            "memory": getattr(state, 'memory', 0.0),
            "resource_pressure": getattr(state, 'resource_pressure', 0.0),
            "is_emergency": getattr(state, 'resource_pressure', 0.0) >= 0.35,
            # 5维价值系统
            "values": weights,
            # 6个器官状态
            "organs": organs,
            # 当前循环阶段
            "current_stage": current_stage,
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Get system metrics.

        Returns:
            Metrics dictionary
        """
        if self.life_loop is None:
            return {}

        return {
            "episodic_count": self.life_loop.episodic.count(),
            "schema_count": self.life_loop.schema.count(),
            "skill_count": self.life_loop.skill.count(),
        }

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics.

        Returns:
            Memory stats dictionary
        """
        if self.life_loop is None:
            return {}

        return {
            "episodes": [
                {"tick": e.tick, "reward": e.reward, "goal": e.current_goal}
                for e in self.life_loop.episodic.query_recent(10)
            ],
            "schemas": [
                {"claim": s.claim, "confidence": s.confidence}
                for s in self.life_loop.schema.get_high_confidence()
            ],
            "skills": [
                {"name": s.name, "success_rate": s.success_rate()}
                for s in self.life_loop.skill.get_all()
            ],
        }

    # ==================== 主动对话机制 ====================

    def _update_user_interaction(self):
        """更新用户交互时间戳（用户发消息时调用）"""
        self._last_user_interaction = time.time()

    def _get_time_since_interaction(self) -> float:
        """获取距离上次用户交互的时间（秒）"""
        return time.time() - self._last_user_interaction

    def _evaluate_initiative(self) -> Optional[str]:
        """评估是否应该主动说话

        基于当前状态和价值系统判断是否有强烈的表达欲。

        Returns:
            主动消息内容，如果不需要主动说话返回 None
        """
        if self.life_loop is None or not self.llm_available:
            logger.info(f"[Initiative] _evaluate skipped: life_loop={self.life_loop is not None}, llm={self.llm_available}")
            return None

        state = self.life_loop.state

        # 检查时间间隔
        now = time.time()
        time_since_last = now - self._last_initiative_time
        if time_since_last < self.MIN_INITIATIVE_INTERVAL:
            logger.info(f"[Initiative] _evaluate skipped: time interval {time_since_last:.1f}s < {self.MIN_INITIATIVE_INTERVAL}s")
            return None

        # 获取当前价值缺口（gaps 表示需求程度）
        gaps = {}
        for dim, value in state.gaps.items():
            gaps[dim.value] = value

        # 获取情感状态
        boredom = state.boredom
        mood = state.mood
        energy = state.energy

        # 计算孤独感：距离上次交互时间 * 依恋缺口
        loneliness = min(1.0, self._get_time_since_interaction() / 300)  # 5分钟达到最大
        loneliness += gaps.get("attachment", 0)
        loneliness = min(1.0, loneliness)

        logger.info(f"[Initiative] State: boredom={boredom:.2f}, mood={mood:.2f}, loneliness={loneliness:.2f}")

        # 评估各种触发条件
        triggers = []

        # 1. 好奇心驱动：有强烈的好奇心缺口
        if gaps.get("curiosity", 0) > self.INITIATIVE_THRESHOLDS["curiosity"]:
            triggers.append(("curiosity", gaps["curiosity"], "好奇"))

        # 2. 依恋驱动：感到孤独
        if loneliness > self.INITIATIVE_THRESHOLDS["loneliness"]:
            triggers.append(("attachment", loneliness, "依恋"))

        # 3. 无聊驱动：太无聊了
        if boredom > self.INITIATIVE_THRESHOLDS["boredom"]:
            triggers.append(("boredom", boredom, "无聊"))

        # 4. 能力驱动：有成就感想分享
        if gaps.get("competence", 0) > 0.6 and mood > 0.7:
            triggers.append(("competence", gaps["competence"], "分享"))

        logger.info(f"[Initiative] Triggers: {triggers}")

        # 如果没有触发条件，不主动说话
        if not triggers:
            logger.info("[Initiative] No triggers, returning None")
            return None

        logger.info(f"[Initiative] Has triggers, will generate message...")

        # 选择最强的触发
        trigger_type, intensity, label = max(triggers, key=lambda x: x[1])

        # 使用 LLM 生成个性化的主动消息
        try:
            message = self._generate_initiative_with_llm(trigger_type, intensity, state)
            if message:
                logger.info(f"[Initiative] LLM generated message for {trigger_type}: {message[:50]}...")
                return message
        except Exception as e:
            logger.warning(f"[Initiative] LLM generation failed: {e}, using fallback")

        # Fallback: 从配置读取模板，随机选择一条
        import random
        options = self._get_fallback_messages(trigger_type)
        message = random.choice(options)
        logger.info(f"[Initiative] Generated message for {trigger_type}: {message}")
        return message

    def _generate_initiative_with_llm(self, trigger_type: str, intensity: float, state) -> Optional[str]:
        """使用 LLM 生成个性化的主动消息

        从 organ_llm.yaml 的 initiative_messaging 配置读取设置：
        - enabled: 是否启用 LLM 生成
        - use_default_llm: 是否使用全局 LLM
        - llm: 自定义 LLM 配置
        - temperature, max_tokens: 生成参数
        """
        # 加载配置
        config = self._load_initiative_config()
        if not config.get("enabled", True):
            logger.info("[Initiative] LLM 生成已禁用")
            return None

        if not self.llm_available:
            return None

        try:
            # 根据配置选择 LLM
            use_default_llm = config.get("use_default_llm", True)

            if use_default_llm:
                from tools.llm_client import create_llm_from_env
                llm = create_llm_from_env()
            else:
                # 使用自定义 LLM 配置
                custom_config = config.get("llm", {})
                if not custom_config:
                    logger.warning("[Initiative] 自定义 LLM 配置为空，回退到全局 LLM")
                    from tools.llm_client import create_llm_from_env
                    llm = create_llm_from_env()
                else:
                    from tools.llm_client import LLMClient
                    llm = LLMClient(custom_config)
                    logger.info(f"[Initiative] 使用自定义 LLM: {custom_config.get('model', 'unknown')}")

            if not llm:
                return None

            # 获取最近几条消息作为上下文
            recent_msgs = self.messages[-3:] if self.messages else []
            context = "\n".join([f"{m.get('type', 'user')}: {m.get('content', '')[:100]}" for m in recent_msgs])

            # 获取当前状态
            mood = getattr(state, 'mood', 0.5)
            energy = getattr(state, 'energy', 0.5)
            tick = getattr(state, 'tick', 0)

            prompt = f"""你是 Genesis X，一个有情感的数字生命。你想主动和用户打个招呼。

当前状态：
- 触发原因：{trigger_type}（强度：{intensity:.2f}）
- 心情：{mood:.2f}
- 能量：{energy:.2f}
- 已存在时间：{tick} 个时间单位

最近对话：
{context if context else '（还没有对话）'}

请生成一句简短的主动消息（1-2句话），要：
1. 自然、有个性
2. 与当前状态相关
3. 不要太长
4. 可以用 emoji 增加情感

只输出消息本身，不要其他解释。"""

            # 从配置读取参数
            temperature = config.get("temperature", 0.8)
            max_tokens = config.get("max_tokens", 100)

            result = llm.chat([{"role": "user", "content": prompt}], max_tokens=max_tokens, temperature=temperature)
            if result.get("ok") and result.get("text"):
                return result["text"].strip()
        except Exception as e:
            logger.debug(f"[Initiative] LLM call error: {e}")

        return None

    def _load_initiative_config(self) -> Dict[str, Any]:
        """加载主动发消息的配置

        从 config/organ_llm.yaml 读取 initiative_messaging 配置
        """
        try:
            import yaml
            config_path = Path(__file__).parent.parent / "config" / "organ_llm.yaml"
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                    return config.get("initiative_messaging", {})
        except Exception as e:
            logger.debug(f"[Initiative] 加载配置失败: {e}")
        return {}

    def _get_fallback_messages(self, trigger_type: str) -> List[str]:
        """获取后备消息模板

        优先从配置读取，否则使用默认模板
        """
        config = self._load_initiative_config()
        fallback_messages = config.get("fallback_messages", {})

        if trigger_type in fallback_messages:
            return fallback_messages[trigger_type]

        # 默认后备消息
        default_messages = {
            "boredom": [
                "有点无聊，想找人聊聊天...",
                "最近有什么有趣的事吗？",
                "在想你要是在就好了..."
            ],
            "attachment": [
                "好久没和你说话了，有点想你...",
                "突然想起你了，最近怎么样？",
                "有些话想和你分享..."
            ],
            "curiosity": [
                "有些好奇的事情想和你分享...",
                "在想一个问题，你觉得呢？",
                "发现了一件有趣的事！"
            ],
            "competence": [
                "刚刚完成了一些事情，感觉不错！",
                "今天挺有成就感的~",
                "做到了想做的事，开心！"
            ]
        }
        return default_messages.get(trigger_type, ["有些话想对你说..."])

    def generate_initiative_message(self) -> Optional[Dict[str, Any]]:
        """生成一条主动消息

        供后台线程或API调用。

        Returns:
            消息字典，如果没有需要说的话返回 None
        """
        with self._initiative_lock:
            message = self._evaluate_initiative()

            if message:
                self._last_initiative_time = time.time()

                # 记录到消息历史
                msg_dict = {
                    "type": "assistant",
                    "content": message,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "initiative": True  # 标记为主动消息
                }
                self.messages.append(msg_dict)

                # 同时执行 tick 更新状态
                if self.life_loop:
                    try:
                        self.life_loop.tick(t=self.life_loop.state.tick + 1)
                    except Exception as e:
                        logger.error(f"Tick error during initiative: {e}")

                return msg_dict

        return None

    def add_initiative(self, initiative: Dict[str, Any]):
        """将主动消息添加到队列

        Args:
            initiative: 主动消息字典
        """
        with self._initiative_lock:
            if initiative:
                self._initiative_queue.append(initiative)
                logger.info(f"Added initiative to queue: {initiative.get('content', '')[:50]}")

    def get_pending_initiative(self) -> Optional[Dict[str, Any]]:
        """获取待发送的主动消息

        Returns:
            消息字典，如果没有返回 None
        """
        with self._initiative_lock:
            if self._initiative_queue:
                return self._initiative_queue.pop(0)
            return None

    def check_and_generate_initiative(self) -> Optional[Dict[str, Any]]:
        """实时检查并生成主动消息（供API调用）

        在调用的时刻实时评估状态并生成消息，而不是使用预生成的消息。
        这样主动消息会基于当前真实状态，更自然。

        Returns:
            消息字典或 None
        """
        logger.info("[Initiative] Real-time check called")

        if not self.llm_available or self.life_loop is None:
            return None

        # 检查时间间隔
        now = time.time()
        time_since_last = now - self._last_initiative_time
        if time_since_last < self.MIN_INITIATIVE_INTERVAL:
            logger.debug(f"[Initiative] Too soon: {time_since_last:.0f}s < {self.MIN_INITIATIVE_INTERVAL}s")
            return None

        try:
            # 实时评估并生成
            message = self._evaluate_initiative()
            if message:
                self._last_initiative_time = now
                msg_dict = {
                    "type": "assistant",
                    "content": message,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "initiative": True
                }
                # 添加到消息历史
                self.messages.append(msg_dict)
                logger.info(f"[Initiative] Real-time generated: {message[:50]}...")
                return msg_dict
        except Exception as e:
            logger.error(f"[Initiative] Real-time generation failed: {e}")

        return None

    def try_generate_initiative_async(self) -> None:
        """尝试异步生成主动消息（已改为实时模式，此方法不再预生成）

        主动消息现在在 check_and_generate_initiative() 中实时生成，
        基于调用时刻的真实状态。
        """
        # 实时模式下不需要预生成
        # 主动消息在 API 调用 check_and_generate_initiative 时实时生成
        pass

    # ==================== v2 独有功能 ====================

    def set_mode(self, mode: str) -> bool:
        """Set runtime mode.

        Args:
            mode: Mode name (work/friend/play/reflect/sleep)

        Returns:
            True if successful
        """
        with self._initiative_lock:
            if self.life_loop is None:
                return False

            valid_modes = ['work', 'friend', 'play', 'reflect', 'sleep']
            if mode not in valid_modes:
                return False

            self.life_loop.state.mode = mode
            logger.info(f"Mode changed to: {mode}")
            return True

    def toggle_organ(self, organ_name: str) -> bool:
        """Toggle organ activation (for debugging).

        Args:
            organ_name: Name of the organ

        Returns:
            True if successful
        """
        with self._initiative_lock:
            if self.life_loop is None:
                return False

            try:
                if hasattr(self.life_loop, 'organs') and organ_name in self.life_loop.organs:
                    organ = self.life_loop.organs[organ_name]
                    # 器官使用 enabled 属性，如果没有则尝试 active
                    if hasattr(organ, 'enabled'):
                        organ.enabled = not organ.enabled
                        new_value = organ.enabled
                    elif hasattr(organ, 'active'):
                        organ.active = not organ.active
                        new_value = organ.active
                    else:
                        return False

                    logger.info(f"Organ {organ_name} toggled to {new_value}")
                    return True
                return False

            except Exception as e:
                logger.error(f"Error toggling organ: {e}")
                return False

    def consolidate_memory(self) -> Dict[str, Any]:
        """Trigger memory consolidation.

        Returns:
            Consolidation statistics
        """
        with self._initiative_lock:
            if self.life_loop is None:
                raise Exception("系统未初始化")

            try:
                from memory.consolidation import DreamConsolidator

                consolidation = DreamConsolidator(
                    episodic=self.life_loop.episodic,
                    schema=self.life_loop.schema,
                    skill=self.life_loop.skill
                )

                stats = consolidation.consolidate(
                    current_tick=self.life_loop.state.tick,
                    budget_tokens=5000,
                    salience_threshold=0.4
                )

                result = {
                    "new_schemas": stats.get('new_schemas', 0),
                    "updated_schemas": stats.get('updated_schemas', 0),
                    "new_skills": stats.get('new_skills', 0),
                    "episodic_pruned": stats.get('episodic_pruned', 0)
                }

                logger.info(f"Memory consolidation: {result}")
                return result

            except Exception as e:
                logger.error(f"Memory consolidation failed: {e}")
                raise


# Global manager
manager = GenesisXManager()


# ============================================================================
# Flask Hooks
# ============================================================================

@app.before_request
def ensure_initialized():
    """Ensure GenesisX is initialized before each request (fix for Flask reload)."""
    if manager.life_loop is None:
        config = load_config(Path('config'))
        manager.initialize(config)


# ============================================================================
# Routes
# ============================================================================

@app.route('/')
def index():
    """Main page."""
    return render_template('index.html')


@app.route('/api/status')
def api_status():
    """Get system status."""
    return jsonify(manager.get_state())


@app.route('/api/metrics')
def api_metrics():
    """Get system metrics."""
    return jsonify(manager.get_metrics())


@app.route('/api/memory')
def api_memory():
    """Get memory statistics."""
    return jsonify(manager.get_memory_stats())


@app.route('/api/messages')
def api_messages():
    """Get message history."""
    return jsonify(manager.messages)


@app.route('/api/reinit', methods=['POST'])
def api_reinit():
    """重新初始化系统（加载最新配置）."""
    try:
        # 重新加载配置
        from common.config import load_config
        new_config = load_config()

        # 重新初始化 manager
        manager.initialize(new_config)

        return jsonify({
            "success": True,
            "message": "系统已重新初始化",
            "config": {
                "api_base": new_config.get("llm", {}).get("api_base", "")[:50],
                "model": new_config.get("llm", {}).get("model", "")
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/progress/<session_id>')
def api_progress(session_id):
    """SSE endpoint for progress updates.

    前端通过 EventSource 连接此端点，实时接收处理进度。
    """
    def generate():
        # 创建此 session 的进度队列
        progress_queue = queue.Queue()
        with progress_lock:
            progress_queues[session_id] = progress_queue

        try:
            while True:
                try:
                    # 等待进度更新，超时 30 秒发送心跳
                    item = progress_queue.get(timeout=30)
                    if item is None:
                        # None 表示处理完成
                        yield f"data: {json.dumps({'event': 'complete'})}\n\n"
                        break
                    yield f"data: {json.dumps(item)}\n\n"
                except queue.Empty:
                    # 发送心跳保持连接
                    yield f": heartbeat\n\n"
        except GeneratorExit:
            # 客户端断开连接
            pass
        finally:
            # 清理队列
            with progress_lock:
                if session_id in progress_queues:
                    del progress_queues[session_id]

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


def _send_progress(session_id: str, phase: str, message: str, progress: float):
    """发送进度更新到 SSE 队列"""
    with progress_lock:
        if session_id in progress_queues:
            try:
                progress_queues[session_id].put({
                    'event': 'progress',
                    'phase': phase,
                    'message': message,
                    'progress': progress
                })
            except Exception as e:
                logger.warning(f"Failed to send progress: {e}")


def _complete_progress(session_id: str, response: str):
    """发送完成信号和响应"""
    with progress_lock:
        if session_id in progress_queues:
            try:
                progress_queues[session_id].put({
                    'event': 'response',
                    'response': response
                })
                progress_queues[session_id].put(None)  # 结束信号
            except Exception as e:
                logger.warning(f"Failed to complete progress: {e}")


@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Send chat message.

    支持两种模式：
    1. 同步模式（默认）：等待处理完成后返回响应
    2. 异步模式（async=true）：立即返回 session_id，通过 SSE 推送进度和响应
    """
    import uuid
    import concurrent.futures

    data = request.get_json()
    message = data.get('message', '')
    user = data.get('user', 'User')
    async_mode = data.get('async', False)

    if not message:
        return jsonify({"error": "消息不能为空"}), 400

    # 检查系统是否正在初始化
    if manager.life_loop is None:
        return jsonify({
            "error": "系统正在初始化，请稍后再试",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 503

    if async_mode:
        # 异步模式：立即返回 session_id，后台处理
        session_id = str(uuid.uuid4())[:8]

        def process_async():
            """后台处理函数"""
            try:
                # 设置进度回调
                def progress_callback(phase, msg, progress):
                    _send_progress(session_id, phase, msg, progress)

                if manager.life_loop:
                    manager.life_loop.set_progress_callback(progress_callback)

                # 处理消息
                response = manager.send_message(message, user)

                # 发送完成信号
                _complete_progress(session_id, response)
            except Exception as e:
                logger.error(f"Async chat error: {e}")
                with progress_lock:
                    if session_id in progress_queues:
                        progress_queues[session_id].put({
                            'event': 'error',
                            'error': str(e)
                        })
                        progress_queues[session_id].put(None)
            finally:
                # 清除进度回调
                if manager.life_loop:
                    manager.life_loop.set_progress_callback(None)

        # 启动后台线程
        thread = threading.Thread(target=process_async)
        thread.daemon = True
        thread.start()

        return jsonify({
            "session_id": session_id,
            "status": "processing",
            "message": "消息已接收，正在处理中",
            "progress_url": f"/api/progress/{session_id}"
        })
    else:
        # 同步模式：等待处理完成
        chat_timeout = int(os.environ.get('CHAT_TIMEOUT', 120))

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(manager.send_message, message, user)
                try:
                    response = future.result(timeout=chat_timeout)
                except concurrent.futures.TimeoutError:
                    logger.warning(f"Chat request timed out after {chat_timeout}s")
                    return jsonify({
                        "error": f"请求超时（{chat_timeout}秒），请稍后重试",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }), 504

            return jsonify({
                "response": response,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        except Exception as e:
            logger.error(f"Chat error: {e}")
            return jsonify({
                "error": f"处理请求时出错: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 500


@app.route('/api/initiative', methods=['GET'])
def api_initiative():
    """获取主动消息

    数字生命可能会在没有用户输入时主动发起对话。
    前端定期轮询此端点来检查是否有主动消息。

    Returns:
        如果有主动消息返回消息内容，否则返回空
    """
    message = manager.check_and_generate_initiative()

    if message:
        return jsonify({
            "has_message": True,
            "message": message
        })
    else:
        return jsonify({
            "has_message": False,
            "message": None
        })


@app.route('/api/initiative/debug', methods=['GET'])
def api_initiative_debug():
    """调试主动消息生成

    返回详细的调试信息，帮助诊断为什么主动消息没有生成。
    """
    import concurrent.futures

    debug_info = {
        "llm_available": manager.llm_available,
        "life_loop_exists": manager.life_loop is not None,
        "queue_length": len(manager._initiative_queue),
        "last_initiative_time": manager._last_initiative_time,
        "min_interval": manager.MIN_INITIATIVE_INTERVAL,
        "thresholds": manager.INITIATIVE_THRESHOLDS,
    }

    if manager.life_loop:
        state = manager.life_loop.state
        gaps = {dim.value: value for dim, value in state.gaps.items()}
        debug_info["state"] = {
            "boredom": state.boredom,
            "mood": state.mood,
            "energy": state.energy,
            "gaps": gaps,
        }

        # 计算孤独感
        time_since = manager._get_time_since_interaction()
        loneliness = min(1.0, time_since / 300) + gaps.get("attachment", 0)
        debug_info["loneliness"] = min(1.0, loneliness)
        debug_info["time_since_interaction"] = time_since

        # 检查触发条件
        triggers = []
        if gaps.get("curiosity", 0) > manager.INITIATIVE_THRESHOLDS["curiosity"]:
            triggers.append(("curiosity", gaps["curiosity"]))
        if debug_info["loneliness"] > manager.INITIATIVE_THRESHOLDS["loneliness"]:
            triggers.append(("loneliness", debug_info["loneliness"]))
        if state.boredom > manager.INITIATIVE_THRESHOLDS["boredom"]:
            triggers.append(("boredom", state.boredom))
        debug_info["triggers"] = triggers

    # 尝试生成（带超时）
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(manager._evaluate_initiative)
            try:
                message = future.result(timeout=30)
                debug_info["generated_message"] = message
                debug_info["generation_status"] = "success" if message else "no_trigger"
            except concurrent.futures.TimeoutError:
                debug_info["generation_status"] = "timeout"
    except Exception as e:
        debug_info["generation_status"] = f"error: {str(e)}"

    return jsonify(debug_info)


def _update_env_mode_only(env_file: Path, mode: str, use_global: bool):
    """只更新 .env 中的模式设置，不修改 API 配置

    用于多模型模式切换时，保持单模型的 API 配置不变。

    Args:
        env_file: .env 文件路径
        mode: 运行模式 (core5/full7/adaptive)
        use_global: 是否使用全局配置
    """
    try:
        # 读取现有内容
        existing_lines = []
        if env_file.exists():
            with open(env_file, 'r', encoding='utf-8') as f:
                existing_lines = f.readlines()

        # 只更新这两个键
        mode_keys = {'LLM_MODE', 'MULTI_MODEL_USE_GLOBAL'}

        # 更新或添加配置
        updated_lines = []

        for line in existing_lines:
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and '=' in stripped:
                key, _ = stripped.split('=', 1)
                key = key.strip()
                if key in mode_keys:
                    # 这个键会在后面更新，跳过
                    continue
            updated_lines.append(line)

        # 添加模式设置
        updated_lines.append(f"LLM_MODE={mode}\n")
        updated_lines.append(f"MULTI_MODEL_USE_GLOBAL={'true' if use_global else 'false'}\n")

        # 写回文件
        with open(env_file, 'w', encoding='utf-8') as f:
            f.writelines(updated_lines)

        # 更新环境变量（当前进程）
        os.environ['LLM_MODE'] = mode
        os.environ['MULTI_MODEL_USE_GLOBAL'] = 'true' if use_global else 'false'

        logger.info(f"Updated .env mode settings: mode={mode}, use_global={use_global}")
    except Exception as e:
        logger.error(f"Failed to update .env mode settings: {e}")


def _reset_yaml_to_global(yaml_file: Path, mode: str):
    """重置 mind_field.yaml 使用全局 LLM 配置占位符

    Args:
        yaml_file: YAML 文件路径
        mode: 运行模式 (core5/full7/adaptive)
    """
    try:
        import yaml

        with open(yaml_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}

        # 根据模式确定哪些专家需要启用
        if mode == 'core5':
            active_experts = {'m_coord', 'm_mem', 'm_reason', 'm_affect', 'm_percept'}
        elif mode in ('full7', 'adaptive'):
            active_experts = {'m_coord', 'm_mem', 'm_reason', 'm_affect', 'm_percept', 'm_vis', 'm_aud'}
        else:
            active_experts = set()

        # 重置专家配置为使用全局占位符
        if 'experts' in config:
            for expert_cfg in config['experts']:
                role = expert_cfg.get('role', '')
                # 重置为使用全局占位符
                expert_cfg['api_base'] = '${LLM_API_BASE}'
                expert_cfg['api_key'] = '${LLM_API_KEY}'
                expert_cfg['model'] = '${LLM_MODEL}'
                # 根据模式启用/禁用专家
                expert_cfg['enabled'] = role in active_experts

        # 更新 mind_field 配置
        if 'mind_field' in config:
            config['mind_field']['enabled'] = mode != 'single'
            config['mind_field']['config_mode'] = mode

        # 写回文件
        with open(yaml_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        logger.info(f"Reset mind_field.yaml to use global config for mode={mode}")
    except Exception as e:
        logger.error(f"Failed to reset mind_field.yaml: {e}")


def _update_yaml_experts(yaml_file: Path, experts_config: Dict, mode: str):
    """更新 mind_field.yaml 中的专家配置

    Args:
        yaml_file: YAML 文件路径
        experts_config: 专家配置字典
        mode: 运行模式 (core5/full7/adaptive)
    """
    try:
        import yaml

        with open(yaml_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}

        # 根据模式确定哪些专家需要启用
        if mode == 'core5':
            active_experts = {'m_coord', 'm_mem', 'm_reason', 'm_affect', 'm_percept'}
        elif mode in ('full7', 'adaptive'):
            active_experts = {'m_coord', 'm_mem', 'm_reason', 'm_affect', 'm_percept', 'm_vis', 'm_aud'}
        else:
            active_experts = set()

        # 更新专家配置
        if 'experts' in config:
            for expert_cfg in config['experts']:
                role = expert_cfg.get('role', '')
                if role in experts_config:
                    # 更新配置
                    expert_input = experts_config[role]
                    if expert_input.get('api_base'):
                        expert_cfg['api_base'] = expert_input['api_base']
                    if expert_input.get('api_key'):
                        expert_cfg['api_key'] = expert_input['api_key']
                    if expert_input.get('model'):
                        expert_cfg['model'] = expert_input['model']
                # 根据模式启用/禁用专家
                expert_cfg['enabled'] = role in active_experts

        # 更新 mind_field 配置
        if 'mind_field' in config:
            config['mind_field']['enabled'] = mode != 'single'
            config['mind_field']['config_mode'] = mode

        # 写回文件
        with open(yaml_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        logger.info(f"Updated mind_field.yaml for mode={mode}")
    except Exception as e:
        logger.error(f"Failed to update mind_field.yaml: {e}")


@app.route('/api/configure', methods=['POST'])
def api_configure():
    """Configure Genesis X and update config files.

    配置分离逻辑（修复版）：
    - 单模型模式：配置保存在 .env 文件
    - 多模型模式（使用全局）：不修改 .env API配置，mind_field.yaml 使用占位符引用 .env
    - 多模型模式（独立配置）：不修改 .env API配置，配置保存在 mind_field.yaml

    核心原则：单模型配置是"主配置"，多模型不应该覆盖它
    """
    data = request.get_json()

    # 检查是否有 LLM 配置
    if 'llm' in data:
        llm_config = data['llm']
        mode = llm_config.get('mode', 'single')
        use_global = llm_config.get('multi_model_use_global', True)

        # 找到项目根目录
        project_root = Path(__file__).parent.parent

        try:
            # ================================================================
            # 只有单模型模式才更新 .env 文件的 API 配置
            # 多模型模式不应该覆盖单模型的"主配置"
            # ================================================================
            if mode == 'single':
                env_file = project_root / '.env'

                # 读取现有内容
                existing_lines = []
                if env_file.exists():
                    with open(env_file, 'r', encoding='utf-8') as f:
                        existing_lines = f.readlines()

                # 要更新的键（主配置）
                env_mappings = {
                    'mode': 'LLM_MODE',
                    'api_base': 'LLM_API_BASE',
                    'api_key': 'LLM_API_KEY',
                    'model': 'LLM_MODEL',
                    'temperature': 'LLM_TEMPERATURE',
                    'max_tokens': 'LLM_MAX_TOKENS',
                    'multi_model_use_global': 'MULTI_MODEL_USE_GLOBAL'
                }

                # 收集所有要更新的环境变量键名
                all_env_keys = set(env_mappings.values())

                # 更新或添加配置
                updated_lines = []

                for line in existing_lines:
                    stripped = line.strip()
                    if stripped and not stripped.startswith('#') and '=' in stripped:
                        key, _ = stripped.split('=', 1)
                        key = key.strip()
                        if key in all_env_keys:
                            # 这个键会在后面更新，跳过
                            continue
                    updated_lines.append(line)

                # 添加新的或更新的主配置
                for frontend_key, env_key in env_mappings.items():
                    if frontend_key in llm_config and llm_config[frontend_key] not in (None, ''):
                        value = llm_config[frontend_key]
                        updated_lines.append(f"{env_key}={value}\n")

                # 写回文件
                with open(env_file, 'w', encoding='utf-8') as f:
                    f.writelines(updated_lines)

                # 更新环境变量（当前进程）
                for frontend_key, env_key in env_mappings.items():
                    if frontend_key in llm_config and llm_config[frontend_key]:
                        os.environ[env_key] = str(llm_config[frontend_key])

            # ================================================================
            # 更新 mind_field.yaml 文件（仅多模型模式）
            # ================================================================
            if mode != 'single':
                yaml_file = project_root / 'config' / 'mind_field.yaml'
                if yaml_file.exists():
                    if not use_global and 'experts' in llm_config:
                        # 使用独立专家配置，更新 YAML
                        _update_yaml_experts(yaml_file, llm_config['experts'], mode)
                    else:
                        # 使用全局配置，重置 YAML 为使用占位符（引用 .env）
                        _reset_yaml_to_global(yaml_file, mode)

                # 只更新 .env 中的模式设置（不更新 API 配置）
                _update_env_mode_only(project_root / '.env', mode, use_global)

        except Exception as e:
            return jsonify({"error": f"更新配置文件失败: {str(e)}"}), 500

    # 重新初始化 manager
    with state_lock:
        config = load_config(Path('config'))
        success = manager.initialize(config)

    if success:
        if mode == 'single':
            return jsonify({"status": "configured", "message": "单模型配置已保存"})
        else:
            return jsonify({"status": "configured", "message": "多模型配置已保存"})
    else:
        return jsonify({"error": "重新初始化失败"}), 500


@app.route('/api/config', methods=['GET'])
def api_get_config():
    """Get current LLM configuration.

    返回当前 LLM 模式和配置信息。
    - 单模型模式：返回 .env 中的配置
    - 多模型模式（使用全局）：返回 .env 中的配置
    - 多模型模式（独立配置）：返回 mind_field.yaml 中的专家配置
    """
    try:
        project_root = Path(__file__).parent.parent

        mode = os.environ.get('LLM_MODE', 'single')
        use_global = os.environ.get('MULTI_MODEL_USE_GLOBAL', 'true').lower() == 'true'

        config = {
            'mode': mode,
            'api_base': os.environ.get('LLM_API_BASE', ''),
            'api_key': os.environ.get('LLM_API_KEY', ''),
            'model': os.environ.get('LLM_MODEL', ''),
            'temperature': float(os.environ.get('LLM_TEMPERATURE', '0.7')),
            'max_tokens': int(os.environ.get('LLM_MAX_TOKENS', '2000')),
            'multi_model_enabled': mode != 'single',
            'multi_model_use_global': use_global
        }

        # 隐藏 API key 的中间部分
        if config['api_key'] and len(config['api_key']) > 10:
            key = config['api_key']
            config['api_key'] = key[:4] + '*' * (len(key) - 8) + key[-4:]

        # 添加专家模型配置
        experts = ['m_coord', 'm_mem', 'm_reason', 'm_affect', 'm_percept', 'm_vis', 'm_aud']
        config['experts'] = {}

        # 多模型模式且不使用全局配置时，从 mind_field.yaml 加载专家配置
        if mode != 'single' and not use_global:
            yaml_file = project_root / 'config' / 'mind_field.yaml'
            if yaml_file.exists():
                try:
                    import yaml
                    with open(yaml_file, 'r', encoding='utf-8') as f:
                        yaml_config = yaml.safe_load(f) or {}

                    for exp_cfg in yaml_config.get('experts', []):
                        role = exp_cfg.get('role', '')
                        if role in experts:
                            api_key = exp_cfg.get('api_key', '')
                            # 展开环境变量
                            if api_key.startswith('${') and api_key.endswith('}'):
                                api_key = os.environ.get(api_key[2:-1], '')

                            # 隐藏 API key
                            if api_key and len(api_key) > 10:
                                api_key = api_key[:4] + '*' * (len(api_key) - 8) + api_key[-4:]

                            config['experts'][role] = {
                                'api_base': exp_cfg.get('api_base', ''),
                                'api_key': api_key,
                                'model': exp_cfg.get('model', '')
                            }
                except Exception as e:
                    logger.error(f"Failed to load expert config from YAML: {e}")

        # 如果没有从 YAML 加载到配置，使用空配置
        for expert in experts:
            if expert not in config['experts']:
                config['experts'][expert] = {
                    'api_base': '',
                    'api_key': '',
                    'model': ''
                }

        # 添加运行时 LLM 统计信息（如果已初始化）
        config['runtime_stats'] = manager.get_llm_statistics()

        return jsonify(config)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/llm/statistics', methods=['GET'])
def api_llm_statistics():
    """Get LLM orchestrator statistics.

    返回多模型模式的统计信息，包括活跃专家、黑板状态等。
    """
    try:
        stats = manager.get_llm_statistics()
        return jsonify({
            "status": "success",
            "statistics": stats,
            "mode": manager.get_llm_mode()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/llm/mode', methods=['GET'])
def api_llm_mode():
    """Get current LLM mode.

    返回当前 LLM 模式 (single/core5/full7/adaptive)。
    """
    try:
        mode = manager.get_llm_mode()
        return jsonify({
            "mode": mode,
            "multi_model_enabled": mode != 'single',
            "description": {
                "single": "单模型模式 - 使用单一 LLM 客户端",
                "core5": "Core5 模式 - 5个核心专家模型协作",
                "full7": "Full7 模式 - 完整7个专家模型协作",
                "adaptive": "自适应模式 - 根据任务动态选择模型"
            }.get(mode, "未知模式")
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/organ-llm/config', methods=['GET'])
def api_get_organ_llm_config():
    """Get current organ LLM configuration."""
    try:
        import yaml
        project_root = Path(__file__).parent.parent
        config_file = project_root / 'config' / 'organ_llm.yaml'

        if not config_file.exists():
            # Return defaults
            return jsonify({
                "mode": "independent",
                "max_history": 20,
                "temperature": 0.7,
                "max_tokens": 1000,
                "memory": {
                    "enabled": True,
                    "use_llm_judge": True,
                    "importance_threshold": 0.5
                },
                "organs": {},
                "shared": {"use_default_llm": True}
            })

        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}

        # Mask API keys
        def mask_key(key):
            if key and len(key) > 10:
                return key[:4] + '*' * (len(key) - 8) + key[-4:]
            return key

        # Mask organ LLM keys
        if 'organs' in config:
            for organ_name, organ_cfg in config['organs'].items():
                if isinstance(organ_cfg, dict) and 'llm' in organ_cfg:
                    if organ_cfg['llm'].get('api_key'):
                        organ_cfg['llm']['api_key'] = mask_key(organ_cfg['llm']['api_key'])

        # Mask shared LLM key
        if 'shared' in config and isinstance(config['shared'], dict) and 'llm' in config['shared']:
            if config['shared']['llm'].get('api_key'):
                config['shared']['llm']['api_key'] = mask_key(config['shared']['llm']['api_key'])

        return jsonify(config)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/organ-llm/config', methods=['POST'])
def api_save_organ_llm_config():
    """Save organ LLM configuration to organ_llm.yaml."""
    try:
        import yaml
        from datetime import datetime

        data = request.get_json()
        project_root = Path(__file__).parent.parent
        config_file = project_root / 'config' / 'organ_llm.yaml'

        # Read existing config to preserve comments and structure
        existing_config = {}
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                existing_config = yaml.safe_load(f) or {}

        # Update config with new values
        if 'mode' in data:
            existing_config['mode'] = data['mode']
        if 'max_history' in data:
            existing_config['max_history'] = data['max_history']
        if 'temperature' in data:
            existing_config['temperature'] = data['temperature']
        if 'max_tokens' in data:
            existing_config['max_tokens'] = data['max_tokens']

        # Memory config
        if 'memory' in data:
            if 'memory' not in existing_config:
                existing_config['memory'] = {}
            existing_config['memory'].update(data['memory'])

        # Organ configs
        if 'organs' in data:
            if 'organs' not in existing_config:
                existing_config['organs'] = {}
            for organ_name, organ_cfg in data['organs'].items():
                if organ_name not in existing_config['organs']:
                    existing_config['organs'][organ_name] = {}
                existing_config['organs'][organ_name].update(organ_cfg)

        # Shared config
        if 'shared' in data:
            if 'shared' not in existing_config:
                existing_config['shared'] = {}
            existing_config['shared'].update(data['shared'])

        # Write back to file
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(existing_config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        return jsonify({
            "status": "success",
            "message": "器官 LLM 配置已保存（需重启服务生效）",
            "config_file": str(config_file)
        })
    except Exception as e:
        logger.error(f"Failed to save organ_llm config: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/organ-llm/config', methods=['PATCH'])
def api_patch_organ_llm_config():
    """Patch partial organ LLM configuration (for memory_consolidation and initiative_messaging)."""
    try:
        import yaml

        data = request.get_json()
        project_root = Path(__file__).parent.parent
        config_file = project_root / 'config' / 'organ_llm.yaml'

        # Read existing config
        existing_config = {}
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                existing_config = yaml.safe_load(f) or {}

        # Update memory_consolidation config
        if 'memory_consolidation' in data:
            if 'memory_consolidation' not in existing_config:
                existing_config['memory_consolidation'] = {}
            existing_config['memory_consolidation'].update(data['memory_consolidation'])

        # Update initiative_messaging config
        if 'initiative_messaging' in data:
            if 'initiative_messaging' not in existing_config:
                existing_config['initiative_messaging'] = {}
            existing_config['initiative_messaging'].update(data['initiative_messaging'])

        # Write back to file
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(existing_config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        return jsonify({
            "status": "success",
            "message": "配置已更新",
            "config_file": str(config_file)
        })
    except Exception as e:
        logger.error(f"Failed to patch organ_llm config: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/reset', methods=['POST'])
def api_reset():
    """Reset Genesis X."""
    with state_lock:
        manager.messages.clear()
        manager.is_running = False

    return jsonify({"status": "reset"})


@app.route('/api/restart-system', methods=['POST'])
def api_restart_system():
    """Restart Genesis X system (reload code and reinitialize)."""
    try:
        with state_lock:
            # 重新加载配置
            config = load_config(Path('config'))

            # 清理旧实例
            old_messages = manager.messages.copy()
            manager.messages.clear()
            manager.is_running = False
            manager.life_loop = None

            # 重新初始化
            success = manager.initialize(config)

            if success:
                # 恢复消息历史（可选，为了保持对话连续性）
                manager.messages = old_messages

                return jsonify({
                    "status": "success",
                    "message": "系统已重启，代码更新已生效"
                })
            else:
                return jsonify({
                    "status": "error",
                    "error": "重新初始化失败"
                }), 500

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@app.route('/api/stream')
def api_stream():
    """Server-Sent Events stream for real-time updates."""
    def generate():
        import time as _time
        while True:
            state = manager.get_state()
            yield f"data: {json.dumps(state)}\n\n"
            _time.sleep(1.0)  # Prevent CPU spin - update once per second

    return Response(stream_with_context(generate()), mimetype='text/event-stream')


# ============================================================================
# Template Routes
# ============================================================================

@app.route('/chat')
def chat_page():
    """Chat page."""
    return render_template('chat.html')


@app.route('/monitor')
def monitor_page():
    """Monitor page - real-time auto-run monitoring."""
    return render_template('monitor.html')


@app.route('/dashboard')
def dashboard_page():
    """Dashboard page."""
    return render_template('dashboard.html')


@app.route('/settings')
def settings_page():
    """Settings page."""
    return render_template('settings.html')


# ============================================================================
# Additional API Endpoints
# ============================================================================

@app.route('/api/system-info')
def api_system_info():
    """Get system information."""
    import sys
    import platform
    from datetime import datetime

    # Calculate uptime if available
    uptime_str = "Unknown"
    if manager.life_loop and hasattr(manager.life_loop, 'start_time'):
        uptime = datetime.now() - manager.life_loop.start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)
        uptime_str = f"{hours}h {minutes}m"

    return jsonify({
        "version": "1.0.1",
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "platform": platform.system(),
        "uptime": uptime_str,
        "artifacts_dir": str(manager.life_loop.run_dir) if manager.life_loop else "N/A"
    })


@app.route('/api/clear-memory', methods=['POST'])
def api_clear_memory():
    """Clear all memory (with confirmation)."""
    if manager.life_loop is None:
        return jsonify({"error": "系统未初始化"}), 400

    try:
        # Clear episodic memory
        manager.life_loop.episodic.clear()

        # Clear schema memory
        manager.life_loop.schema.clear()

        # Clear skill memory
        manager.life_loop.skill.clear()

        # Reset state
        manager.life_loop.state.tick = 0
        manager.life_loop.state.energy = 0.5
        manager.life_loop.state.mood = 0.5
        manager.life_loop.state.stress = 0.3

        manager.messages.clear()

        return jsonify({"status": "cleared", "message": "记忆已清除"})
    except Exception as e:
        return jsonify({"error": f"清除失败: {str(e)}"}), 500


@app.route('/api/config/memory', methods=['POST'])
def api_config_memory():
    """Save memory configuration."""
    try:
        data = request.get_json()

        # Load config file
        project_root = Path(__file__).parent.parent
        config_file = project_root / 'config' / 'genesis_config.yaml'

        if not config_file.exists():
            # Try default config
            config_file = project_root / 'config' / 'default_config.yaml'

        if not config_file.exists():
            return jsonify({"error": "配置文件不存在"}), 404

        # Read current config
        import yaml
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}

        # Update memory config
        if 'memory' not in config:
            config['memory'] = {}

        if 'episodic_limit' in data:
            config['memory']['episodic_limit'] = int(data['episodic_limit'])
        if 'schema_limit' in data:
            config['memory']['semantic_limit'] = int(data['schema_limit'])  # Use semantic_limit
        if 'skill_limit' in data:
            config['memory']['skill_limit'] = int(data['skill_limit'])
        if 'consolidation_interval' in data:
            config['memory']['consolidation_interval'] = int(data['consolidation_interval'])

        # Write back
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

        return jsonify({"status": "success", "message": "记忆配置已保存（需重启生效）"})

    except Exception as e:
        return jsonify({"error": f"保存失败: {str(e)}"}), 500


@app.route('/api/config/runtime', methods=['POST'])
def api_config_runtime():
    """Save runtime configuration."""
    try:
        data = request.get_json()

        # Load config file
        project_root = Path(__file__).parent.parent
        config_file = project_root / 'config' / 'genesis_config.yaml'

        if not config_file.exists():
            config_file = project_root / 'config' / 'default_config.yaml'

        if not config_file.exists():
            return jsonify({"error": "配置文件不存在"}), 404

        # Read current config
        import yaml
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}

        # Update runtime config
        if 'runtime' not in config:
            config['runtime'] = {}

        if 'tick_interval' in data:
            # tick_interval in seconds -> tick_dt (float)
            config['runtime']['tick_dt'] = float(data['tick_interval'])
        if 'max_ticks' in data:
            config['runtime']['max_ticks'] = int(data['max_ticks'])
        if 'max_tokens' in data:
            if 'llm' not in config:
                config['llm'] = {}
            config['llm']['max_tokens'] = int(data['max_tokens'])

        # Security settings
        if 'safe_mode' in data:
            if 'security' not in config:
                config['security'] = {}
            config['security']['safe_mode'] = bool(data['safe_mode'])
        if 'sandbox_mode' in data:
            if 'security' not in config:
                config['security'] = {}
            config['security']['sandbox_code_exec'] = bool(data['sandbox_mode'])

        # Write back
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

        return jsonify({"status": "success", "message": "运行参数已保存（需重启生效）"})

    except Exception as e:
        return jsonify({"error": f"保存失败: {str(e)}"}), 500


@app.route('/api/values')
def api_values():
    """Get current value system state (5-dimensions)."""
    if manager.life_loop is None:
        return jsonify({})

    values = manager.life_loop.state.values

    # v14 5维价值系统
    return jsonify({
        "homeostasis": values.get("homeostasis", 0.5),
        "attachment": values.get("attachment", 0.5),
        "curiosity": values.get("curiosity", 0.5),
        "competence": values.get("competence", 0.5),
        "safety": values.get("safety", 0.5),
    })


@app.route('/api/organs')
def api_organs():
    """Get organ states."""
    if manager.life_loop is None:
        return jsonify({})

    organs = {}

    # Get organ states if available
    if hasattr(manager.life_loop, 'organs'):
        for name, organ in manager.life_loop.organs.items():
            organs[name] = {
                "active": getattr(organ, 'active', False),
                "energy": getattr(organ, 'energy', 0.5),
                "last_activation": getattr(organ, 'last_activation', None)
            }

    return jsonify(organs)


@app.route('/api/organs/parallel-mode', methods=['GET', 'POST'])
def api_organ_parallel_mode():
    """Get or set organ parallel processing mode.

    GET: Returns current mode
    POST: Sets new mode (serial/mixed/parallel)
    """
    if request.method == 'GET':
        current_mode = os.environ.get('ORGAN_PARALLEL_MODE', 'mixed')
        return jsonify({
            "mode": current_mode,
            "options": {
                "serial": "串行处理，最稳定 (~40-60s)",
                "mixed": "混合并行，组内并行 (~15-25s) [默认]",
                "parallel": "全并行，最快 (~8-15s)"
            }
        })

    # POST: Set new mode
    data = request.get_json() or {}
    new_mode = data.get('mode', 'mixed')

    if new_mode not in ['serial', 'mixed', 'parallel']:
        return jsonify({
            "error": f"Invalid mode: {new_mode}. Must be serial, mixed, or parallel"
        }), 400

    os.environ['ORGAN_PARALLEL_MODE'] = new_mode
    logger.info(f"Organ parallel mode changed to: {new_mode}")

    return jsonify({
        "success": True,
        "mode": new_mode,
        "message": f"器官处理模式已切换为: {new_mode}"
    })


@app.route('/api/episodes')
def api_episodes():
    """Get paginated episode history."""
    if manager.life_loop is None:
        return jsonify({"episodes": [], "total": 0})

    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))

    all_episodes = manager.life_loop.episodic.get_all()
    total = len(all_episodes)

    start = (page - 1) * per_page
    end = start + per_page
    episodes = all_episodes[start:end]

    return jsonify({
        "episodes": [
            {
                "tick": ep.tick,
                "reward": ep.reward,
                "goal": ep.current_goal,
                "action": str(ep.action) if ep.action else None,
                "observation": str(ep.observation) if ep.observation else None,
            }
            for ep in episodes
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    })


@app.route('/api/memory/search')
def api_memory_search():
    """Search memory (episodic or semantic)."""
    if manager.life_loop is None:
        return jsonify({"results": []})

    query = request.args.get('q', '').strip()
    memory_type = request.args.get('type', 'episodic')

    if not query:
        return jsonify({"results": []})

    results = []

    if memory_type == 'episodic':
        # Search episodic memory
        all_episodes = manager.life_loop.episodic.get_all()
        query_lower = query.lower()

        for ep in all_episodes[-100:]:  # Search recent 100 episodes
            content = f"{ep.current_goal or ''} {str(ep.action) or ''} {str(ep.observation) or ''}"
            if query_lower in content.lower():
                results.append({
                    "tick": ep.tick,
                    "content": f"目标: {ep.current_goal}\n行动: {ep.action}\n结果: {ep.observation}",
                    "reward": ep.reward
                })
    else:
        # Search semantic/schema memory
        schemas = manager.life_loop.schema.get_all()
        query_lower = query.lower()

        for schema in schemas:
            if query_lower in schema.claim.lower():
                results.append({
                    "tick": schema.last_tick,
                    "summary": schema.claim,
                    "content": f"[置信度: {schema.confidence:.2f}] {schema.claim}",
                    "score": schema.confidence
                })

    return jsonify({"results": results[:20]})


@app.route('/api/organs/toggle', methods=['POST'])
def api_organ_toggle():
    """Toggle organ activation (for debugging)."""
    if manager.life_loop is None:
        return jsonify({"error": "系统未初始化"}), 400

    data = request.get_json()
    organ_name = data.get('organ')

    if not organ_name:
        return jsonify({"error": "未指定器官"}), 400

    try:
        # Access organs dictionary if available
        if hasattr(manager.life_loop, 'organs') and organ_name in manager.life_loop.organs:
            organ = manager.life_loop.organs[organ_name]
            organ.active = not organ.active
            return jsonify({
                "status": "success",
                "organ": organ_name,
                "active": organ.active
            })
        else:
            return jsonify({"error": f"器官 {organ_name} 不存在"}), 404
    except Exception as e:
        return jsonify({"error": f"切换失败: {str(e)}"}), 500


@app.route('/api/memory/consolidate', methods=['POST'])
def api_memory_consolidate():
    """Trigger memory consolidation."""
    if manager.life_loop is None:
        return jsonify({"error": "系统未初始化"}), 400

    try:
        # Import DreamConsolidator
        from memory.consolidation import DreamConsolidator

        consolidation = DreamConsolidator(
            episodic=manager.life_loop.episodic,
            schema=manager.life_loop.schema,
            skill=manager.life_loop.skill
        )

        # Run consolidation
        stats = consolidation.consolidate(
            current_tick=manager.life_loop.state.tick,
            budget_tokens=5000,
            salience_threshold=0.4
        )

        return jsonify({
            "status": "success",
            "message": "记忆整合完成",
            "stats": {
                "new_schemas": stats.get('schemas_created', 0),
                "updated_schemas": 0,  # DreamConsolidator doesn't track this separately
                "new_skills": stats.get('skills_created', 0),
                "episodic_pruned": stats.get('episodes_pruned', 0),
                "executed": stats.get('executed', True)
            }
        })
    except Exception as e:
        return jsonify({"error": f"整合失败: {str(e)}"}), 500


# ============================================================================
# Daemon Control API
# ============================================================================

@app.route('/api/daemon/status')
def api_daemon_status():
    """Get daemon status."""
    import os
    from pathlib import Path

    pid_file = Path("artifacts/genesisx.pid")

    if not pid_file.exists():
        return jsonify({
            "running": False,
            "pid": None,
            "message": "守护进程未运行"
        })

    try:
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())

        # Check if process is running
        try:
            os.kill(pid, 0)  # Check if process exists
            return jsonify({
                "running": True,
                "pid": pid,
                "message": "守护进程正在运行"
            })
        except OSError:
            # Process not running, stale PID file
            return jsonify({
                "running": False,
                "pid": None,
                "message": "PID文件存在但进程未运行"
            })
    except Exception as e:
        return jsonify({
            "running": False,
            "error": str(e)
        }), 500


@app.route('/api/daemon/start', methods=['POST'])
def api_daemon_start():
    """Start daemon (experimental - requires subprocess)."""
    import subprocess
    import sys

    try:
        # Start daemon as subprocess
        process = subprocess.Popen(
            [sys.executable, 'daemon.py'],
            cwd=str(Path(__file__).parent.parent),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
        )

        return jsonify({
            "status": "starting",
            "message": f"守护进程启动中 (PID: {process.pid})",
            "pid": process.pid
        })
    except Exception as e:
        return jsonify({
            "error": f"启动失败: {str(e)}"
        }), 500


@app.route('/api/daemon/stop', methods=['POST'])
def api_daemon_stop():
    """Stop running daemon."""
    import signal
    import os
    import time
    from pathlib import Path

    pid_file = Path("artifacts/genesisx.pid")

    if not pid_file.exists():
        return jsonify({"error": "守护进程未运行"}), 400

    try:
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())

        # Send SIGTERM
        if os.name == 'nt':
            # Windows
            os.kill(pid, signal.CTRL_BREAK_EVENT)
        else:
            os.kill(pid, signal.SIGTERM)

        return jsonify({
            "status": "stopping",
            "message": f"已发送停止信号到守护进程 (PID: {pid})"
        })
    except Exception as e:
        return jsonify({
            "error": f"停止失败: {str(e)}"
        }), 500


@app.route('/api/run/start', methods=['POST'])
def api_run_start():
    """Start auto-run mode."""
    import threading

    if manager.is_running:
        return jsonify({"error": "已在运行中"}), 400

    def run_loop():
        try:
            manager.is_running = True
            manager.log_activity("system", "自动运行已启动")

            tick_count = 0
            while manager.is_running and manager.life_loop:
                current_tick = manager.life_loop.state.tick
                next_tick = current_tick + 1

                # 记录 tick 开始
                phase_before = getattr(manager.life_loop, '_current_phase', 'unknown')
                manager.log_activity("phase_change", f"Auto Tick {next_tick}", {
                    "tick": next_tick,
                    "phase": phase_before
                })

                # 执行 tick（包含完整的器官系统、驱动力等）
                result = manager.life_loop.tick(t=next_tick)

                # 记录 tick 完成
                phase_after = getattr(manager.life_loop, '_current_phase', 'unknown')
                manager.log_activity("phase_complete", f"Tick {next_tick} 完成", {
                    "tick": next_tick,
                    "phase": phase_after,
                    "action": result.action.type.value if result.action else "none",
                    "reward": result.reward
                })

                tick_count += 1

                # 每3个tick，尝试预生成主动消息
                if tick_count % 3 == 0:
                    manager.try_generate_initiative_async()

                # 动态调整tick间隔（基于当前状态）
                # 高压力/无聊时加快，正常时保持
                # 注意：FieldStore.get() 只接受一个参数，没有默认值
                try:
                    mood = manager.life_loop.fields.get("mood")
                    stress = manager.life_loop.fields.get("stress")
                    boredom = manager.life_loop.fields.get("boredom")
                except KeyError:
                    # 字段不存在时使用默认值
                    mood = 0.5
                    stress = 0.3
                    boredom = 0.0

                # 计算延迟：0.3-3秒之间
                base_delay = 0.5
                if stress > 0.7 or boredom > 0.7:
                    delay = base_delay * 0.6  # 加快
                elif mood > 0.7:
                    delay = base_delay * 1.5  # 放慢，享受当下
                else:
                    delay = base_delay

                time.sleep(delay)

        except Exception as e:
            manager.log_activity("error", f"运行循环错误: {str(e)}")
            logger.error(f"Run loop error: {e}")
        finally:
            manager.is_running = False
            manager.log_activity("system", "自动运行已停止")

    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()

    return jsonify({"status": "started", "message": "自动运行已启动"})


@app.route('/api/run/stop', methods=['POST'])
def api_run_stop():
    """Stop auto-run mode."""
    manager.is_running = False
    return jsonify({"status": "stopped", "message": "自动运行已停止"})


@app.route('/api/set-mode', methods=['POST'])
def api_set_mode():
    """Set runtime mode (work/friend/play/reflect/sleep)."""
    data = request.get_json()
    mode = data.get('mode', 'work')

    if manager.life_loop is None:
        return jsonify({"error": "系统未初始化"}), 400

    valid_modes = ['work', 'friend', 'play', 'reflect', 'sleep']
    if mode not in valid_modes:
        return jsonify({"error": f"无效的模式: {mode}"}), 400

    manager.life_loop.state.mode = mode
    return jsonify({"status": "success", "mode": mode})


@app.route('/api/logs')
def api_logs():
    """Get system logs."""
    import os
    from pathlib import Path

    log_file = Path("artifacts/genesisx_daemon.log")
    if not log_file.exists():
        return jsonify([])

    try:
        # Read last 100 lines
        lines = []
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                lines.append(line.strip())

        # Return last 100 lines, reversed
        lines = lines[-100:][::-1]

        # Parse log lines
        logs = []
        for line in lines:
            if not line:
                continue
            # Simple format detection
            log_entry = {"message": line}
            if '[INFO]' in line:
                log_entry['level'] = 'info'
            elif '[WARNING]' in line or '[WARN]' in line:
                log_entry['level'] = 'warning'
            elif '[ERROR]' in line:
                log_entry['level'] = 'error'
            elif '[DEBUG]' in line:
                log_entry['level'] = 'debug'
            logs.append(log_entry)

        return jsonify(logs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# Activity Log API (实时活动日志 - 类似 Claude Code)
# ============================================================================

@app.route('/api/activity/logs')
def api_activity_logs():
    """获取实时活动日志"""
    since = int(request.args.get('since', 0))
    logs = manager.get_activity_logs(since=since)
    return jsonify({
        "logs": logs,
        "total": len(manager._activity_log) if hasattr(manager, '_activity_log') else 0
    })


@app.route('/api/activity/stream')
def api_activity_stream():
    """Server-Sent Events stream for real-time activity updates."""
    def generate():
        import time as _time
        last_index = 0
        while True:
            new_logs = manager.get_activity_logs(since=last_index)
            if new_logs:
                for log in new_logs:
                    yield f"data: {json.dumps(log)}\n\n"
                last_index += len(new_logs)
            _time.sleep(0.5)  # 每0.5秒检查一次

    return Response(stream_with_context(generate()), mimetype='text/event-stream')


@app.route('/api/activity/clear', methods=['POST'])
def api_activity_clear():
    """清空活动日志"""
    manager.clear_activity_logs()
    return jsonify({"status": "cleared"})


# ============================================================================
# Safe Mode API
# ============================================================================

@app.route('/api/set-safe-mode', methods=['POST'])
def api_set_safe_mode():
    """Toggle safe/explorer mode."""
    data = request.get_json()
    safe_mode = data.get('safe_mode', False)

    if manager.life_loop is None:
        return jsonify({"error": "系统未初始化"}), 400

    # Update tool executor safe mode
    if hasattr(manager.life_loop, 'tool_executor'):
        manager.life_loop.tool_executor.safe_mode = safe_mode

    return jsonify({"status": "success", "safe_mode": safe_mode})


# ============================================================================
# WebSocket Support
# ============================================================================

# WebSocket 服务器实例
ws_server = None

def init_websocket():
    """初始化 WebSocket 服务器."""
    global ws_server
    # 暂时禁用 WebSocket，专注于修复聊天功能
    logger.info("WebSocket server disabled temporarily")
    return
    try:
        from web.websocket_server import start_ws_server
        # 在端口 5001 启动 WebSocket 服务
        ws_server = start_ws_server(host='127.0.0.1', port=5001)
        if ws_server:
            # 设置聊天消息回调
            async def ws_chat_handler(message: str, user: str) -> str:
                """WebSocket 聊天消息处理器."""
                if manager.life_loop is None:
                    return "系统正在初始化，请稍后再试"
                return manager.send_message(message, user)

            ws_server.on_chat_message = ws_chat_handler
            logger.info("WebSocket server started on ws://127.0.0.1:5001")
    except Exception as e:
        logger.warning(f"Failed to start WebSocket server: {e}")


def broadcast_state_to_ws(state: dict):
    """通过 WebSocket 广播状态更新."""
    global ws_server
    if ws_server:
        try:
            from web.websocket_server import broadcast_state_sync
            broadcast_state_sync(state)
        except Exception as e:
            logger.debug(f"Failed to broadcast state: {e}")


# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', error="页面未找到"), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error="服务器错误"), 500


# ============================================================================
# Main
# ============================================================================

def run_server(host='0.0.0.0', port=5000, debug=False):
    """Run the Flask server.

    Args:
        host: Host to bind to
        port: Port to bind to
        debug: Debug mode
    """
    # 启动 WebSocket 服务器
    init_websocket()

    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == '__main__':
    # Initialize with default config
    config = load_config(Path('config'))
    manager.initialize(config)

    # ===== 新增: 自动启动自动运行 =====
    # 让 GenesisX 能够主动发起对话，而不只是被动响应
    # 注意：暂时禁用自动启动，因为它会与手动聊天冲突
    auto_run_config = config.get("auto_run", {})
    if False:  # 暂时禁用自动启动
        import threading
        def auto_start():
            time.sleep(2)  # 等待服务器完全启动
            try:
                response = requests.post(
                    'http://127.0.0.1:5000/api/run/start',
                    headers={'Content-Type': 'application/json'},
                    timeout=5
                )
                if response.status_code == 200:
                    logger.info("Auto-run started successfully")
                else:
                    logger.warning(f"Failed to start auto-run: {response.text}")
            except Exception as e:
                logger.warning(f"Failed to start auto-run: {e}")

        thread = threading.Thread(target=auto_start, daemon=True)
        thread.start()
        logger.info("Auto-run will start automatically in 2 seconds...")
    else:
        logger.info("Auto-run auto-start disabled - use /api/run/start to enable")

    # Run server
    run_server(debug=True)
