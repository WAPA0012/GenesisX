"""Continuous Autonomous Action Scheduler.

优化目标：闲置时不浪费算力，而是持续做有价值的事情

核心思想：
1. 持续工作：不结束进程，不长时间休眠
2. 价值驱动：根据当前价值缺口选择最有意义的行动
3. 动态生成：任务根据需求动态生成，不是固定列表
4. 防死循环：多样化任务 + 失败降级
5. 全方位成长：知识、能力、社交、自我、进化五大维度

论文对应 Section 3.2: 价值驱动的行为选择
"""

import time
import random
import threading
import sys
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List, Tuple, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum
from common.logger import get_logger

logger = get_logger(__name__)

# 尝试导入探索系统（延迟导入以避免循环依赖）
EXPLORATION_AVAILABLE = False
_exploration_module = None

def _get_exploration_module():
    """延迟导入探索模块"""
    global _exploration_module, EXPLORATION_AVAILABLE
    if _exploration_module is not None:
        return _exploration_module

    try:
        # 添加项目根目录到路径
        project_root = Path(__file__).parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        from core.exploration import (
            ExplorationEngine,
            ExplorationTask,
            TaskCategory,
            TaskPromptLibrary,
            get_exploration_engine,
            sample_random_question,
            sample_wild_idea,
            sample_scenario,
        )
        _exploration_module = type('Module', (), {
            'ExplorationEngine': ExplorationEngine,
            'ExplorationTask': ExplorationTask,
            'TaskCategory': TaskCategory,
            'TaskPromptLibrary': TaskPromptLibrary,
            'get_exploration_engine': get_exploration_engine,
            'sample_random_question': sample_random_question,
            'sample_wild_idea': sample_wild_idea,
            'sample_scenario': sample_scenario,
        })
        EXPLORATION_AVAILABLE = True
        return _exploration_module
    except ImportError as e:
        logger.warning(f"Exploration module not available: {e}")
        EXPLORATION_AVAILABLE = False
        return None


class ActionType(Enum):
    """自主行动类型"""
    # 高优先级行动（解决紧急需求）
    DREAM = "dream"                   # 做梦/记忆巩固
    CONSOLIDATE = "consolidate"       # 巩固学习

    # 中优先级行动（探索与发展）
    EXPLORE_LOCAL = "explore_local"   # 本地探索（文件、代码）
    EXPLORE_WEB = "explore_web"       # 网络探索（搜索、发现）
    REFLECT = "reflect"               # 反思经验
    PRACTICE = "practice"             # 练习技能

    # 低优先级行动（维护与优化）
    ORGANIZE = "organize"             # 整理记忆
    OPTIMIZE = "optimize"             # 优化策略
    SCAN = "scan"                     # 扫描环境

    # 降级行动（无其他选择时）
    IDLE_THINK = "idle_think"         # 静默思考


@dataclass
class ActionTask:
    """可执行的行动任务"""
    type: ActionType
    name: str
    description: str
    value: float              # 预期价值 [0,1]
    cost: float               # 预期成本 [0,1]
    cooldown: float = 0.0     # 冷却时间（秒），防止重复执行
    can_parallel: bool = False
    dynamic_params: Dict[str, Any] = field(default_factory=dict)  # 动态参数

    def priority(self) -> float:
        """优先级 = 价值 / 成本"""
        if self.cost <= 0.01:
            return self.value * 100
        return self.value / self.cost


class TaskGenerator:
    """动态任务生成器

    根据当前状态和价值缺口动态生成任务，而不是使用固定列表
    这样可以避免死循环，并且适应各种情况
    """

    # 已执行任务的历史（用于防重复）
    def __init__(self):
        self._executed_history: List[Tuple[str, float]] = []  # (task_name, timestamp)
        self._consecutive_failures: Dict[str, int] = {}  # 任务类型 -> 失败次数

        # 探索引擎（延迟初始化）
        self._exploration_engine = None

    @property
    def exploration_engine(self):
        """获取探索引擎（延迟加载）"""
        if self._exploration_engine is None and EXPLORATION_AVAILABLE:
            mod = _get_exploration_module()
            if mod:
                self._exploration_engine = mod.get_exploration_engine()
        return self._exploration_engine

    def is_on_cooldown(self, task_name: str, cooldown_seconds: float) -> bool:
        """检查任务是否在冷却中"""
        current_time = time.time()
        # 清理旧记录
        self._executed_history = [
            (name, ts) for name, ts in self._executed_history
            if current_time - ts < 3600  # 只保留最近1小时的记录
        ]

        # 检查是否最近执行过
        for name, ts in self._executed_history:
            if name == task_name and current_time - ts < cooldown_seconds:
                return True
        return False

    def record_execution(self, task_name: str, success: bool = True):
        """记录任务执行"""
        self._executed_history.append((task_name, time.time()))

        if not success:
            # 记录失败
            task_type = task_name.split(":")[0] if ":" in task_name else task_name
            self._consecutive_failures[task_type] = self._consecutive_failures.get(task_type, 0) + 1
        else:
            # 成功则重置失败计数
            task_type = task_name.split(":")[0] if ":" in task_name else task_name
            self._consecutive_failures[task_type] = 0

    def get_failure_count(self, task_type: str) -> int:
        """获取任务类型的连续失败次数"""
        return self._consecutive_failures.get(task_type, 0)

    def generate_tasks(self, state: Dict[str, Any]) -> List[ActionTask]:
        """根据当前状态动态生成任务列表

        Args:
            state: 当前系统状态

        Returns:
            可执行的任务列表（按优先级排序）
        """
        tasks = []
        gaps = state.get("gaps", {})

        # 1. 做梦任务（当疲劳度高时）
        activity_fatigue = state.get("activity_fatigue", 0.0)
        episodic_count = state.get("episodic_count", 0)
        if activity_fatigue > 0.5 and episodic_count >= 5:
            tasks.append(ActionTask(
                type=ActionType.DREAM,
                name="dream:consolidate",
                description=f"整理记忆（疲劳度{activity_fatigue:.2f}）",
                value=0.8,
                cost=0.2,
                cooldown=300,  # 5分钟冷却
            ))

        # 2. 探索任务（根据好奇心缺口）- 使用探索系统
        curiosity_gap = gaps.get("curiosity", 0.0)
        if curiosity_gap > 0.3:
            tasks.extend(self._generate_exploration_tasks(state))

        # 3. 肢体生成任务（能力缺口高时）
        competence_gap = gaps.get("competence", 0.0)
        if competence_gap > 0.6:
            tasks.append(ActionTask(
                type=ActionType.EXPLORE_LOCAL,  # 复用这个类型
                name="limb:generate",
                description="生成新的能力肢体",
                value=0.7,
                cost=0.5,
                cooldown=600,  # 10分钟冷却
                dynamic_params={"action": "generate_limb"},
            ))

        # 4. 反思任务（总是可用）
        tasks.append(ActionTask(
            type=ActionType.REFLECT,
            name="reflect:summary",
            description="总结最近的经历",
            value=0.4,
            cost=0.1,
            cooldown=60,
        ))

        # 5. 整理任务（当记忆多时）
        if episodic_count > 20:
            tasks.append(ActionTask(
                type=ActionType.ORGANIZE,
                name="organize:prune",
                description="清理低价值记忆",
                value=0.3,
                cost=0.1,
                cooldown=600,  # 10分钟冷却
            ))

        # 6. 降级任务（确保总有事可做）
        tasks.append(ActionTask(
            type=ActionType.IDLE_THINK,
            name="idle:think",
            description="静默思考",
            value=0.1,
            cost=0.0,
            cooldown=0,
        ))

        # 过滤冷却中的任务
        available_tasks = [
            t for t in tasks
            if not self.is_on_cooldown(t.name, t.cooldown)
        ]

        # 如果没有可用任务（都在冷却），返回降级任务
        if not available_tasks:
            return [ActionTask(
                type=ActionType.IDLE_THINK,
                name="idle:wait",
                description="等待冷却",
                value=0.05,
                cost=0.0,
            )]

        # 按优先级排序
        available_tasks.sort(key=lambda t: t.priority(), reverse=True)
        return available_tasks

    def _generate_exploration_tasks(self, state: Dict[str, Any]) -> List[ActionTask]:
        """生成探索任务（使用探索系统）"""
        tasks = []

        if self.exploration_engine:
            # 使用探索系统生成主题
            exploration_topics = self.exploration_engine.generate_exploration_tasks(
                state, count=3
            )

            for topic in exploration_topics:
                # 根据维度确定任务类型
                action_type = self._dimension_to_action_type(topic.dimension)

                tasks.append(ActionTask(
                    type=action_type,
                    name=f"explore:{topic.dimension.value}:{topic.topic}",
                    description=topic.description,
                    value=topic.value,
                    cost=0.3 + topic.difficulty * 0.2,  # 难度越高成本越大
                    cooldown=300,
                    dynamic_params={
                        "dimension": topic.dimension.value,
                        "topic": topic.topic,
                        "difficulty": topic.difficulty,
                    },
                ))
        else:
            # 回退到简单的探索任务
            tasks.extend(self._generate_fallback_explore_tasks(state))

        return tasks

    def _dimension_to_action_type(self, dimension: 'GrowthDimension') -> ActionType:
        """将成长维度映射到行动类型"""
        # 简化映射：网络相关用 EXPLORE_WEB，其他用 EXPLORE_LOCAL
        dim_value = dimension.value if hasattr(dimension, 'value') else str(dimension)

        if 'world' in dim_value or 'web' in dim_value:
            return ActionType.EXPLORE_WEB
        else:
            return ActionType.EXPLORE_LOCAL

    def _generate_fallback_explore_tasks(self, state: Dict[str, Any]) -> List[ActionTask]:
        """回退探索任务（探索系统不可用时）"""
        tasks = []

        # 简单的探索任务
        topics = [
            ("学习数学知识", "knowledge_domain", 0.6),
            ("学习编程技能", "knowledge_programming", 0.7),
            ("理解人类情感", "social_understanding", 0.5),
            ("提升推理能力", "capability_cognition", 0.6),
            ("反思自我认知", "self_metacognition", 0.4),
        ]

        for topic, dim, value in topics:
            tasks.append(ActionTask(
                type=ActionType.EXPLORE_LOCAL,
                name=f"explore:{dim}:{topic}",
                description=topic,
                value=value,
                cost=0.2,
                cooldown=300,
                dynamic_params={"dimension": dim, "topic": topic},
            ))

        return tasks

    def _generate_local_explore_tasks(self, state: Dict[str, Any]) -> List[ActionTask]:
        """生成本地探索任务"""
        tasks = []

        # 探索项目文件
        tasks.append(ActionTask(
            type=ActionType.EXPLORE_LOCAL,
            name="explore:files",
            description="探索项目文件",
            value=0.5,
            cost=0.2,
            cooldown=180,
            dynamic_params={"scope": "project"},
        ))

        # 阅读文档
        tasks.append(ActionTask(
            type=ActionType.EXPLORE_LOCAL,
            name="explore:docs",
            description="阅读项目文档",
            value=0.6,
            cost=0.3,
            cooldown=300,
            dynamic_params={"scope": "docs"},
        ))

        # 分析代码
        skill_count = state.get("skill_count", 0)
        if skill_count < 10:  # 技能少时多练习
            tasks.append(ActionTask(
                type=ActionType.PRACTICE,
                name="practice:code_analysis",
                description="分析代码结构",
                value=0.4,
                cost=0.2,
                cooldown=120,
            ))

        return tasks

    def _generate_web_explore_tasks(self, state: Dict[str, Any]) -> List[ActionTask]:
        """生成网络探索任务"""
        tasks = []

        # 根据当前兴趣生成探索主题
        interests = self._infer_interests(state)

        for interest in interests[:3]:  # 最多3个主题
            tasks.append(ActionTask(
                type=ActionType.EXPLORE_WEB,
                name=f"explore:web:{interest}",
                description=f"网络探索：{interest}",
                value=0.7,
                cost=0.4,
                cooldown=600,  # 网络探索冷却时间长
                dynamic_params={"topic": interest},
            ))

        return tasks

    def _infer_interests(self, state: Dict[str, Any]) -> List[str]:
        """推断当前兴趣主题"""
        # 从最近的对话和行动中推断兴趣
        # 这里简化为一些常见主题
        default_interests = [
            "数字生命技术",
            "AI agent 开发",
            "记忆系统设计",
            "价值驱动架构",
            "工具调用优化",
        ]
        random.shuffle(default_interests)
        return default_interests


class IdleWorker:
    """闲置期工作器

    当没有用户交互时，持续执行有价值的后台任务
    """

    def __init__(self):
        self.generator = TaskGenerator()
        self.current_task: Optional[ActionTask] = None
        self.task_start_time: float = 0
        self.completed_tasks: List[Dict[str, Any]] = []
        self._last_result: Optional[Dict[str, Any]] = None

    def select_task(self, state: Dict[str, Any], user_idle_seconds: float) -> Optional[ActionTask]:
        """根据当前状态选择最有价值的任务

        Args:
            state: 当前系统状态
            user_idle_seconds: 用户闲置时长

        Returns:
            选择的任务，或 None（如果没有任何可用任务）
        """
        # 动态生成任务列表
        tasks = self.generator.generate_tasks(state)

        if not tasks:
            return None

        # 用户刚闲置，优先做高价值任务
        if user_idle_seconds < 300:  # 5分钟内
            # 选择价值最高的
            return tasks[0]

        # 闲置较久，考虑多样性
        # 避免连续执行相同类型的任务
        if self._last_result:
            last_type = self._last_result.get("type")
            # 尝试找一个不同类型的任务
            for task in tasks:
                if task.type.value != last_type:
                    return task

        # 默认返回最高优先级
        return tasks[0]

    def execute_task(self, task: ActionTask, executor_func: Optional[Callable] = None) -> Dict[str, Any]:
        """执行一个任务

        Args:
            task: 要执行的任务
            executor_func: 实际执行器函数（可选），如果为 None 则模拟执行

        Returns:
            执行结果
        """
        self.current_task = task
        self.task_start_time = time.time()

        logger.info(f"Executing task: {task.name} - {task.description}")

        try:
            # 如果提供了执行器，调用它
            if executor_func:
                result = executor_func(task)
                success = result.get("success", True)
            else:
                # 模拟执行
                result = {
                    "task": task.name,
                    "type": task.type.value,
                    "duration": 0.1,
                    "success": True,
                    "output": f"完成{task.description}",
                }
                success = True

            # 记录执行
            self.generator.record_execution(task.name, success)

            if success:
                self.completed_tasks.append(result)
                self._last_result = result

        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            self.generator.record_execution(task.name, False)
            result = {
                "task": task.name,
                "type": task.type.value,
                "duration": 0.0,
                "success": False,
                "error": str(e),
            }

        self.current_task = None
        return result

    def get_task_summary(self) -> str:
        """获取最近完成任务摘要"""
        if not self.completed_tasks:
            return "暂无后台任务"

        recent = self.completed_tasks[-5:]
        # 美化任务名称
        pretty_names = []
        for t in recent:
            name = t["task"]
            if ":" in name:
                name = name.split(":")[1]
            pretty_names.append(name)

        return "、".join(pretty_names)


class AutonomousScheduler:
    """持续工作的自主行为调度器

    优化效果：
    1. 不闲置：用户不交互时持续做有价值的事
    2. 智能选择：根据价值缺口动态生成任务
    3. 防死循环：冷却机制 + 多样化任务 + 失败降级
    4. 可中断：用户交互立即响应

    使用示例:
        scheduler = AutonomousScheduler(
            state_getter=lambda: {...},
            task_executor=actual_executor_function
        )
        scheduler.start()
    """

    def __init__(
        self,
        state_getter: Callable[[], Dict[str, Any]],
        action_callback: Callable[[str], None],
        task_executor: Optional[Callable[[ActionTask], Dict[str, Any]]] = None,
        check_interval: float = 3.0,
    ):
        """初始化调度器

        Args:
            state_getter: 获取当前系统状态的函数
            action_callback: 执行自主动作的回调函数（用于用户可见输出）
            task_executor: 实际任务执行器（如果为 None 则模拟执行）
            check_interval: 检查间隔（秒）
        """
        self.state_getter = state_getter
        self.action_callback = action_callback
        self.task_executor = task_executor
        self.check_interval = check_interval

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_interaction = time.time()
        self._worker = IdleWorker()

        # 统计
        self.total_tasks_executed = 0
        self.total_value_generated = 0.0
        self.execution_history: List[Dict[str, Any]] = []

    def update_last_interaction(self, timestamp: Optional[float] = None):
        """更新最后交互时间（用户输入时调用）"""
        self._last_interaction = timestamp or time.time()

    def _should_act(self, user_idle_seconds: float) -> bool:
        """判断是否应该执行自主行动"""
        # 用户闲置超过 30 秒才开始行动
        return user_idle_seconds > 30

    def _get_user_output(self, task: ActionTask, result: Dict[str, Any]) -> Optional[str]:
        """根据任务类型生成用户可见的输出"""
        if not result.get("success"):
            return None

        output_map = {
            ActionType.DREAM: "我正在整理最近的记忆...",
            ActionType.CONSOLIDATE: "我正在巩固学到的东西...",
            ActionType.EXPLORE_LOCAL: f"我在探索{task.dynamic_params.get('scope', '项目')}...",
            ActionType.EXPLORE_WEB: f"我在网上搜索关于{task.dynamic_params.get('topic', '新知识')}的信息...",
            ActionType.REFLECT: "我在反思最近的经历...",
            ActionType.PRACTICE: "我在练习技能...",
        }

        return output_map.get(task.type)

    def _scheduler_loop(self):
        """调度器主循环"""
        logger.info("Autonomous scheduler started - continuous mode")

        consecutive_idle_cycles = 0
        max_idle_cycles = 10  # 连续空闲10个周期后增加休眠

        while self._running:
            try:
                time.sleep(self.check_interval)

                current_time = time.time()
                user_idle_time = current_time - self._last_interaction

                # 用户活跃，跳过
                if not self._should_act(user_idle_time):
                    consecutive_idle_cycles = 0
                    continue

                # 获取当前状态
                state = self.state_getter()

                # 选择任务
                task = self._worker.select_task(state, user_idle_time)

                if task:
                    # 执行任务
                    result = self._worker.execute_task(task, self.task_executor)

                    self.total_tasks_executed += 1
                    self.total_value_generated += task.value if result.get("success") else 0

                    # 记录历史
                    self.execution_history.append({
                        "time": current_time,
                        "task": task.name,
                        "success": result.get("success", False),
                        "value": task.value,
                    })

                    # 生成用户可见输出
                    user_output = self._get_user_output(task, result)
                    if user_output:
                        self.action_callback(user_output)

                    # 重置空闲计数
                    consecutive_idle_cycles = 0

                    # 根据任务耗时短暂休眠
                    task_duration = result.get("duration", 0.1)
                    if task_duration > 0:
                        time.sleep(min(task_duration, 1.0))
                else:
                    # 没有可用任务
                    consecutive_idle_cycles += 1
                    if consecutive_idle_cycles > max_idle_cycles:
                        # 长时间没有任务，延长休眠
                        time.sleep(self.check_interval * 3)

            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                time.sleep(self.check_interval * 2)

        logger.info(f"Autonomous scheduler stopped - executed {self.total_tasks_executed} tasks")

    def start(self):
        """启动调度器"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True,
            name="AutonomousScheduler"
        )
        self._thread.start()
        logger.info("Scheduler started")

    def stop(self):
        """停止调度器"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("Scheduler stopped")

    def is_running(self) -> bool:
        """检查调度器是否运行中"""
        return self._running

    def get_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        current_task_name = None
        if self._worker.current_task:
            current_task_name = self._worker.current_task.name

        # 计算成功率
        recent = self.execution_history[-20:] if self.execution_history else []
        success_rate = sum(1 for e in recent if e["success"]) / len(recent) if recent else 1.0

        return {
            "running": self._running,
            "current_task": current_task_name,
            "total_tasks_executed": self.total_tasks_executed,
            "total_value_generated": self.total_value_generated,
            "recent_tasks": self._worker.get_task_summary(),
            "success_rate": success_rate,
        }


# 兼容旧接口
NeedType = ActionType
Need = ActionTask
AutonomousDecision = ActionTask
AdaptiveSleep = IdleWorker
