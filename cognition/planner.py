"""Planner - generate candidate plans using LLM."""
from typing import List, Dict, Any, Optional
from common.models import Action
from common.logger import get_logger
from common.constants import CognitionConstants

logger = get_logger(__name__)

try:
    from tools.llm_api import UniversalLLM
except ImportError:
    UniversalLLM = None


class Plan(Dict[str, Any]):
    """A candidate plan.

    Contains:
    - actions: List of actions to execute
    - reasoning: Why this plan was chosen
    - estimated_reward: Expected reward
    - estimated_cost: Expected cost
    """
    pass


class Planner:
    """LLM-based planner for action generation.

    From Section 3.9: Mind organ proposes candidate plans using LLM.

    修复：添加超时控制和重试机制。
    """

    def __init__(
        self,
        llm: Optional[UniversalLLM] = None,
        timeout: float = None,
        max_retries: int = None
    ):
        """Initialize planner.

        Args:
            llm: Universal LLM instance (optional).
                Note (P4-7): 历史上用于 propose_with_llm，但该方法已删除（零调用死代码）。
                参数保留是为兼容 tools/blackboard.py 的 `Planner(llm=...)` 构造，但 llm
                当前不会被使用——propose_plans 是纯规则版。如需重启 LLM 规划路径，
                参见 git history 中 propose_with_llm 的实现。
            timeout: LLM调用超时时间（秒），当前未使用（LLM 路径已删）。
            max_retries: 最大重试次数，当前未使用（LLM 路径已删）。
        """
        self.llm = llm
        self.timeout = timeout or CognitionConstants.LLM_TIMEOUT
        self.max_retries = max_retries or CognitionConstants.MAX_LLM_RETRIES

    def propose_plans(
        self,
        goal: str,
        context: Dict[str, Any],
        available_tools: List[str],
        num_plans: int = 3,
    ) -> List[Plan]:
        """Propose candidate plans for a goal.

        Args:
            goal: Current goal
            context: Context dict (state, retrieved memories, etc.)
            available_tools: List of available tool names
            num_plans: Number of plans to generate

        Returns:
            List of candidate plans
        """
        # In alpha version: simple rule-based plans
        # Full version would use LLM with function calling

        plans = []

        # 每个计划携带 dimension 字段，供 plan_evaluator 按维度权重评分
        if goal == "rest_and_recover":
            plans.append(Plan({
                "actions": [Action(type="SLEEP", params={"duration": 10}).model_dump()],
                "reasoning": "Sleep to recover energy",
                "estimated_reward": 0.5,
                "estimated_cost": 0.0,
                "dimension": "homeostasis",
            }))

        elif goal == "explore_and_learn":
            plans.append(Plan({
                "actions": [Action(type="EXPLORE", params={"topic": "knowledge"}).model_dump()],
                "reasoning": "Explore new topic to satisfy curiosity",
                "estimated_reward": 0.6,
                "estimated_cost": 100.0,
                "dimension": "curiosity",
            }))

        elif goal == "strengthen_bond":
            plans.append(Plan({
                "actions": [Action(type="CHAT", params={"message": "Hello! How are you?"}).model_dump()],
                "reasoning": "Initiate conversation to strengthen bond",
                "estimated_reward": 0.4,
                "estimated_cost": 50.0,
                "dimension": "attachment",
            }))

        elif goal == "reflect_and_consolidate":
            plans.append(Plan({
                "actions": [Action(type="REFLECT", params={"depth": 1}).model_dump()],
                "reasoning": "Reflect on recent experiences",
                "estimated_reward": 0.5,
                "estimated_cost": 200.0,
                "dimension": "meaning",
            }))

        elif goal == "improve_skills":
            plans.append(Plan({
                "actions": [Action(type="LEARN_SKILL", params={"skill": "problem_solving"}).model_dump()],
                "reasoning": "Practice problem solving skills",
                "estimated_reward": 0.7,
                "estimated_cost": 300.0,
                "dimension": "competence",
            }))

        elif goal == "fulfill_commitment":
            plans.append(Plan({
                "actions": [Action(type="USE_TOOL", params={"task": "execute_pending_commitment"}).model_dump()],
                "reasoning": "Execute pending user commitments to maintain attachment",
                "estimated_reward": 0.6,
                "estimated_cost": 200.0,
                "dimension": "attachment",  # v15: contract → attachment
            }))

        elif goal == "verify_and_correct":
            plans.append(Plan({
                "actions": [Action(type="REFLECT", params={"focus": "error_check"}).model_dump()],
                "reasoning": "Verify recent outputs and correct any errors to maintain safety",
                "estimated_reward": 0.5,
                "estimated_cost": 150.0,
                "dimension": "safety",  # v15: integrity → safety
            }))

        elif goal == "optimize_resources":
            plans.append(Plan({
                "actions": [Action(type="OPTIMIZE", params={"target": "resource_usage"}).model_dump()],
                "reasoning": "Optimize resource usage to improve homeostasis",
                "estimated_reward": 0.4,
                "estimated_cost": 50.0,
                "dimension": "homeostasis",  # v15: efficiency → homeostasis
            }))

        else:
            # Default: chat action
            plans.append(Plan({
                "actions": [Action(type="CHAT", params={"message": "Thinking..."}).model_dump()],
                "reasoning": "Default response",
                "estimated_reward": 0.3,
                "estimated_cost": 10.0,
            }))

        return plans[:num_plans]
