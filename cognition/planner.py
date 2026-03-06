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
            llm: Universal LLM instance (optional)
            timeout: LLM调用超时时间（秒），默认使用常量配置
            max_retries: 最大重试次数
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

    def propose_with_llm(
        self,
        goal: str,
        context: Dict[str, Any],
        available_tools: List[str],
    ) -> List[Plan]:
        """Propose plans using LLM (full version).

        修复：添加超时控制和重试机制。

        Args:
            goal: Current goal
            context: Context dict
            available_tools: Available tools

        Returns:
            List of plans
        """
        if self.llm is None:
            return self.propose_plans(goal, context, available_tools)

        # Build prompt
        prompt = self._build_prompt(goal, context, available_tools)

        # 重试循环
        for attempt in range(self.max_retries):
            try:
                # Call LLM with proper message format and timeout
                messages = [{"role": "user", "content": prompt}]
                result = self._call_llm_with_timeout(messages)

                if not result.get("ok", False):
                    if attempt < self.max_retries - 1:
                        logger.warning(f"LLM call failed (attempt {attempt + 1}): {result.get('error')}")
                        continue
                    raise RuntimeError(result.get("error", "LLM call failed"))

                response_text = result.get("text", "")

                # Parse response into plans
                plans = self._parse_llm_response(response_text)
                return plans

            except TimeoutError as e:
                logger.warning(f"LLM call timeout (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt >= self.max_retries - 1:
                    # 最后一次尝试仍然超时，回退到规则生成
                    logger.error("LLM call timeout after all retries, falling back to rule-based")
                    return self.propose_plans(goal, context, available_tools)

            except Exception as e:
                logger.warning(f"LLM call failed (attempt {attempt + 1}): {e}")
                if attempt >= self.max_retries - 1:
                    # 最后一次尝试仍然失败，回退到规则生成
                    return self.propose_plans(goal, context, available_tools)

        # 不应该到这里
        return self.propose_plans(goal, context, available_tools)

    def _call_llm_with_timeout(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """使用超时控制调用 LLM

        修复：添加超时控制，防止无限等待。

        Args:
            messages: 消息列表

        Returns:
            LLM响应字典

        Raises:
            TimeoutError: 如果调用超时
        """
        import signal
        import concurrent.futures

        def llm_call():
            return self.llm.chat(messages)

        # 使用线程池执行器实现超时
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(llm_call)
            try:
                result = future.result(timeout=self.timeout)
                return result
            except concurrent.futures.TimeoutError:
                # 尝试取消任务
                future.cancel()
                raise TimeoutError(f"LLM call exceeded timeout of {self.timeout}s")

    def _build_prompt(
        self,
        goal: str,
        context: Dict[str, Any],
        available_tools: List[str],
    ) -> str:
        """Build prompt for LLM.

        Args:
            goal: Current goal
            context: Context dict
            available_tools: Available tools

        Returns:
            Prompt string
        """
        state_summary = context.get("state", {})
        energy = state_summary.get("energy", 0.5)
        mood = state_summary.get("mood", 0.5)

        prompt = f"""You are an autonomous agent with the following state:
- Energy: {energy:.2f}
- Mood: {mood:.2f}
- Current Goal: {goal}

Available actions: {', '.join(available_tools)}

Generate 2-3 candidate plans to achieve the goal. Each plan should be a sequence of actions.
Format your response as a list of plans with reasoning.
"""
        return prompt

    def _parse_llm_response(self, response: str) -> List[Plan]:
        """Parse LLM response into plans.

        Args:
            response: LLM response string

        Returns:
            List of plans
        """
        # Simplified parsing - just create one plan
        return [Plan({
            "actions": [Action(type="CHAT", params={"message": response[:100]}).model_dump()],
            "reasoning": "LLM-generated response",
            "estimated_reward": 0.5,
            "estimated_cost": 100.0,
        })]
