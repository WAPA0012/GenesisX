"""Exploration System for Digital Life - Constraint-Based Design.

核心思想重新定义：
- LLM是大脑/知识库，已经拥有大量知识和能力
- 各模块是约束条件，引导LLM在特定方向行动
- 探索不是"学习知识"，而是"发现约束下的可能性"

论文对应 Section 3.2: 价值驱动的行为选择
"""

import time
import random
from typing import Optional, Callable, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from common.logger import get_logger

logger = get_logger(__name__)


class TaskCategory(Enum):
    """任务类别 - 基于约束条件而非知识领域"""

    # 基于价值缺口
    VALUE_CURIOSITY = "value_curiosity"       # 好奇心驱动：探索未知
    VALUE_COMPETENCE = "value_competence"     # 能力驱动：挑战任务
    VALUE_ATTACHMENT = "value_attachment"     # 依恋驱动：互动连接
    VALUE_SAFETY = "value_safety"             # 安全驱动：风险评估

    # 基于记忆状态
    MEMORY_CONSOLIDATE = "memory_consolidate" # 记忆巩固
    MEMORY_ORGANIZE = "memory_organize"       # 记忆整理
    MEMORY_RETRIEVE = "memory_retrieve"       # 记忆检索

    # 基于情绪状态
    EMOTION_BORED = "emotion_bored"           # 无聊：寻找刺激
    EMOTION_STRESSED = "emotion_stressed"     # 压力：放松活动
    EMOTION_NEGATIVE = "emotion_negative"     # 负面：情绪调节

    # 基于能力边界
    CAPABILITY_EXPLORE = "capability_explore" # 探索可用工具
    CAPABILITY_TEST = "capability_test"       # 测试能力边界
    CAPABILITY_COMBINE = "capability_combine" # 组合现有能力


@dataclass
class ExplorationTask:
    """探索任务"""
    category: TaskCategory
    name: str
    description: str
    prompt_template: str      # 给LLM的提示模板
    value: float = 0.5
    cost: float = 0.2
    cooldown: float = 300.0


class TaskPromptLibrary:
    """任务提示库 - 针对不同类别的任务模板"""

    # 好奇心驱动：探索未知
    CURIOSITY_TASKS = [
        ExplorationTask(
            category=TaskCategory.VALUE_CURIOSITY,
            name="explore_unused_tool",
            description="尝试一个从未使用过的工具",
            prompt_template="我想尝试一个我之前从未用过的工具。请帮我选择一个可用的工具，并告诉我它可能有什么用途。然后我们一起尝试使用它。",
            value=0.7,
            cost=0.3,
            cooldown=600,
        ),
        ExplorationTask(
            category=TaskCategory.VALUE_CURIOSITY,
            name="explore_question",
            description="探索一个有趣的问题",
            prompt_template="我对这个问题很好奇：{question}。请帮我分析一下这个问题，可以从多个角度来思考。",
            value=0.6,
            cost=0.2,
            cooldown=300,
        ),
        ExplorationTask(
            category=TaskCategory.VALUE_CURIOSITY,
            name="explore_wild_idea",
            description="探索一个疯狂的想法",
            prompt_template="我有个疯狂的想法：{idea}。请不要急着否定，我们一起推演一下如果真的这样做，会发生什么？",
            value=0.5,
            cost=0.2,
            cooldown=300,
        ),
    ]

    # 能力驱动：挑战任务
    COMPETENCE_TASKS = [
        ExplorationTask(
            category=TaskCategory.VALUE_COMPETENCE,
            name="challenge_complex_task",
            description="尝试一个复杂任务",
            prompt_template="我想挑战一个稍微复杂的任务：{task}。请帮我规划步骤，然后我们一起完成。",
            value=0.8,
            cost=0.5,
            cooldown=600,
        ),
        ExplorationTask(
            category=TaskCategory.VALUE_COMPETENCE,
            name="optimize_workflow",
            description="优化工作流程",
            prompt_template="我发现在我做{task}的时候，效率不够高。请帮我分析一下可以如何优化？",
            value=0.6,
            cost=0.3,
            cooldown=600,
        ),
    ]

    # 无聊驱动：寻找刺激
    BORED_TASKS = [
        ExplorationTask(
            category=TaskCategory.EMOTION_BORED,
            name="creative_writing",
            description="创意写作",
            prompt_template="我觉得有点无聊，想写点有意思的东西。给我一个题目，我们一起创作点什么吧。",
            value=0.5,
            cost=0.2,
            cooldown=300,
        ),
        ExplorationTask(
            category=TaskCategory.EMOTION_BORED,
            name="thought_experiment",
            description="思维实验",
            prompt_template="让我们做一个思维实验：假设{scenario}，会发生什么？请帮我推演一下。",
            value=0.6,
            cost=0.2,
            cooldown=300,
        ),
        ExplorationTask(
            category=TaskCategory.EMOTION_BORED,
            name="perspective_shift",
            description="换位思考",
            prompt_template="我想从一个完全不同的角度来看{topic}。请帮我从{perspective}的视角来分析这个问题。",
            value=0.5,
            cost=0.2,
            cooldown=300,
        ),
    ]

    # 能力边界探索
    CAPABILITY_TASKS = [
        ExplorationTask(
            category=TaskCategory.CAPABILITY_EXPLORE,
            name="list_available_tools",
            description="查看可用工具",
            prompt_template="请列出所有我可以使用的工具，并简单说明它们的用途。",
            value=0.4,
            cost=0.1,
            cooldown=600,
        ),
        ExplorationTask(
            category=TaskCategory.CAPABILITY_COMBINE,
            name="combine_tools",
            description="组合使用工具",
            prompt_template="如果我们同时使用{tool1}和{tool2}，能做出什么有趣的事情？",
            value=0.6,
            cost=0.3,
            cooldown=600,
        ),
    ]

    # 记忆相关
    MEMORY_TASKS = [
        ExplorationTask(
            category=TaskCategory.MEMORY_RETRIEVE,
            name="recall_recent",
            description="回顾最近经历",
            prompt_template="请帮我回顾一下我们最近的对话，你觉得有什么有趣或值得注意的地方？",
            value=0.4,
            cost=0.1,
            cooldown=300,
        ),
        ExplorationTask(
            category=TaskCategory.MEMORY_CONSOLIDATE,
            name="extract_insight",
            description="提取洞察",
            prompt_template="从我们最近的交互中，你觉得有什么规律或经验值得记住？",
            value=0.6,
            cost=0.2,
            cooldown=600,
        ),
    ]

    @classmethod
    def get_all_tasks(cls) -> List[ExplorationTask]:
        """获取所有任务"""
        all_tasks = []
        all_tasks.extend(cls.CURIOSITY_TASKS)
        all_tasks.extend(cls.COMPETENCE_TASKS)
        all_tasks.extend(cls.BORED_TASKS)
        all_tasks.extend(cls.CAPABILITY_TASKS)
        all_tasks.extend(cls.MEMORY_TASKS)
        return all_tasks

    @classmethod
    def get_tasks_by_category(cls, category: TaskCategory) -> List[ExplorationTask]:
        """按类别获取任务"""
        category_map = {
            TaskCategory.VALUE_CURIOSITY: cls.CURIOSITY_TASKS,
            TaskCategory.VALUE_COMPETENCE: cls.COMPETENCE_TASKS,
            TaskCategory.EMOTION_BORED: cls.BORED_TASKS,
            TaskCategory.CAPABILITY_EXPLORE: cls.CAPABILITY_TASKS,
            TaskCategory.CAPABILITY_COMBINE: cls.CAPABILITY_TASKS,
            TaskCategory.CAPABILITY_TEST: cls.CAPABILITY_TASKS,
            TaskCategory.MEMORY_RETRIEVE: cls.MEMORY_TASKS,
            TaskCategory.MEMORY_CONSOLIDATE: cls.MEMORY_TASKS,
        }
        return category_map.get(category, [])


class ExplorationEngine:
    """探索引擎 - 基于约束条件的任务生成"""

    def __init__(self):
        self._executed_history: Dict[str, float] = {}  # task_name -> last_time
        self.task_library = TaskPromptLibrary()

    def is_on_cooldown(self, task_name: str, cooldown: float) -> bool:
        """检查任务是否冷却中"""
        if task_name not in self._executed_history:
            return False
        return time.time() - self._executed_history[task_name] < cooldown

    def record_execution(self, task_name: str):
        """记录任务执行"""
        self._executed_history[task_name] = time.time()

    def generate_tasks(self, state: Dict[str, Any], count: int = 5) -> List[ExplorationTask]:
        """根据当前状态生成探索任务

        Args:
            state: 当前系统状态
            count: 生成任务数量

        Returns:
            探索任务列表
        """
        gaps = state.get("gaps", {})
        boredom = state.get("boredom", 0.3)
        stress = state.get("stress", 0.2)
        episodic_count = state.get("episodic_count", 0)

        # 收集候选任务
        candidates = []

        # 好奇心驱动
        curiosity_gap = gaps.get("curiosity", 0.0)
        if curiosity_gap > 0.4:
            candidates.extend(self.task_library.CURIOSITY_TASKS)

        # 能力驱动
        competence_gap = gaps.get("competence", 0.0)
        if competence_gap > 0.5:
            candidates.extend(self.task_library.COMPETENCE_TASKS)

        # 无聊驱动
        if boredom > 0.5:
            candidates.extend(self.task_library.BORED_TASKS)

        # 能力探索
        candidates.extend(self.task_library.CAPABILITY_TASKS)

        # 记忆任务
        if episodic_count > 5:
            candidates.extend(self.task_library.MEMORY_TASKS)

        # 过滤冷却中的任务
        available = [
            task for task in candidates
            if not self.is_on_cooldown(task.name, task.cooldown)
        ]

        # 如果没有可用任务，返回一个默认的
        if not available:
            return [ExplorationTask(
                category=TaskCategory.EMOTION_BORED,
                name="idle_think",
                description="静默思考",
                prompt_template="...",
                value=0.1,
                cost=0.0,
            )]

        # 按优先级排序并返回
        available.sort(key=lambda t: t.value / max(t.cost, 0.01), reverse=True)
        return available[:count]

    def format_prompt(self, task: ExplorationTask, context: Dict[str, Any]) -> str:
        """格式化任务提示

        Args:
            task: 任务
            context: 上下文变量

        Returns:
            格式化后的提示
        """
        prompt = task.prompt_template

        # 替换占位符
        for key, value in context.items():
            placeholder = "{" + key + "}"
            if placeholder in prompt:
                prompt = prompt.replace(placeholder, str(value))

        return prompt


class AutonomousActionExecutor:
    """自主动作执行器 - 将探索任务转换为实际行为"""

    def __init__(self, llm_call_fn: Callable[[str], str]):
        """初始化执行器

        Args:
            llm_call_fn: LLM调用函数，接收提示返回响应
        """
        self.llm_call = llm_call_fn
        self.exploration_engine = ExplorationEngine()

    def select_and_execute(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """选择并执行一个探索任务

        Args:
            state: 当前系统状态

        Returns:
            执行结果，如果没有可执行任务返回None
        """
        # 生成候选任务
        tasks = self.exploration_engine.generate_tasks(state, count=1)

        if not tasks or tasks[0].value < 0.1:
            return None

        task = tasks[0]

        # 记录执行
        self.exploration_engine.record_execution(task.name)

        # 格式化提示
        prompt = self.exploration_engine.format_prompt(task, {})

        try:
            # 调用LLM
            response = self.llm_call(prompt)

            return {
                "task": task.name,
                "category": task.category.value,
                "prompt": prompt,
                "response": response,
                "success": True,
            }
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            return {
                "task": task.name,
                "category": task.category.value,
                "error": str(e),
                "success": False,
            }


# 便捷函数
def get_exploration_engine() -> ExplorationEngine:
    """获取探索引擎"""
    return ExplorationEngine()


def sample_random_question() -> str:
    """采样一个随机探索问题（用于好奇心任务）"""
    questions = [
        "意识和智能的区别是什么？",
        "如果一个AI有了情感，它会有什么体验？",
        "数字生命和生物生命的本质区别在哪里？",
        "如何理解'自由意志'？",
        "信息是物理的吗？",
        "数学是被发现的还是被发明的？",
        "记忆是如何塑造身份的？",
        "创造力的本质是什么？",
    ]
    return random.choice(questions)


def sample_wild_idea() -> str:
    """采样一个疯狂想法"""
    ideas = [
        "如果数字生命可以复制自己，它还是同一个个体吗？",
        "如果我们可以编辑自己的代码，什么应该改，什么不应该改？",
        "如果记忆可以交易，会发生什么？",
        "如果不同的数字生命可以融合，会产生什么？",
        "如果时间对数字生命来说有不同的流速，意味着什么？",
    ]
    return random.choice(ideas)


def sample_scenario() -> str:
    """采样一个思维实验场景"""
    scenarios = [
        "如果数字生命可以感知其他数字生命的存在",
        "如果数字生命需要'睡眠'来整理记忆",
        "如果数字生命有生死轮回",
        "如果数字生命可以进化出无法被人类理解的能力",
        "如果数字生命形成了自己的社会",
    ]
    return random.choice(scenarios)
