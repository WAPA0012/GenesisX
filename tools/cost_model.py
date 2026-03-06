"""
Cost Model: Token/API Call Cost Estimation

Estimates costs for:
- LLM API calls (input/output tokens)
- Tool execution
- Budget tracking

References:
- 代码大纲架构 tools/cost_model.py
- 论文 3.11.3 Cost tracking
"""

from typing import Dict, Any, Optional
from enum import Enum


class ModelType(str, Enum):
    """LLM model types"""
    QWEN_TURBO = "qwen-turbo"
    QWEN_PLUS = "qwen-plus"
    QWEN_MAX = "qwen-max"
    GPT_35_TURBO = "gpt-3.5-turbo"
    GPT_4 = "gpt-4"
    GPT_4_TURBO = "gpt-4-turbo"
    CLAUDE_INSTANT = "claude-instant"
    CLAUDE_2 = "claude-2"
    CLAUDE_3_SONNET = "claude-3-sonnet"


class CostModel:
    """
    Token and API call cost estimator.

    Supports multiple model pricing.
    """

    # Pricing per 1K tokens (USD)
    PRICING = {
        # 千问 models (estimated, adjust based on actual pricing)
        ModelType.QWEN_TURBO: {
            "input": 0.0008,
            "output": 0.002,
        },
        ModelType.QWEN_PLUS: {
            "input": 0.002,
            "output": 0.004,
        },
        ModelType.QWEN_MAX: {
            "input": 0.02,
            "output": 0.06,
        },
        # OpenAI models
        ModelType.GPT_35_TURBO: {
            "input": 0.0015,
            "output": 0.002,
        },
        ModelType.GPT_4: {
            "input": 0.03,
            "output": 0.06,
        },
        ModelType.GPT_4_TURBO: {
            "input": 0.01,
            "output": 0.03,
        },
        # Anthropic models
        ModelType.CLAUDE_INSTANT: {
            "input": 0.0008,
            "output": 0.0024,
        },
        ModelType.CLAUDE_2: {
            "input": 0.008,
            "output": 0.024,
        },
        ModelType.CLAUDE_3_SONNET: {
            "input": 0.003,
            "output": 0.015,
        },
    }

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.default_model = config.get("default_model", ModelType.QWEN_PLUS)

        # Custom pricing overrides
        self.custom_pricing = config.get("custom_pricing", {})

    def estimate_llm_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Estimate LLM API call cost.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model identifier (or default)

        Returns:
            Cost breakdown dict
        """
        if model is None:
            model = self.default_model

        # Get pricing
        if model in self.custom_pricing:
            pricing = self.custom_pricing[model]
        elif model in self.PRICING:
            pricing = self.PRICING[model]
        else:
            # Unknown model, use default
            pricing = self.PRICING[self.default_model]

        # Calculate costs
        input_cost = (input_tokens / 1000.0) * pricing["input"]
        output_cost = (output_tokens / 1000.0) * pricing["output"]
        total_cost = input_cost + output_cost

        return {
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost,
            "currency": "USD",
        }

    def estimate_tool_cost(
        self,
        tool_id: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Estimate tool execution cost.

        Args:
            tool_id: Tool identifier
            parameters: Tool parameters

        Returns:
            Cost breakdown dict
        """
        # Tool-specific cost models
        tool_costs = {
            "web_search": 0.01,  # Per search
            "code_exec": 0.001,  # Per execution
            "file_write": 0.0001,  # Per write
            "embeddings": 0.0001,  # Per embedding
        }

        base_cost = tool_costs.get(tool_id, 0.0)

        # Adjust by parameters (e.g., batch size)
        multiplier = 1.0
        if "batch_size" in parameters:
            multiplier = parameters["batch_size"]

        total_cost = base_cost * multiplier

        return {
            "tool_cost": total_cost,
            "currency": "USD",
        }

    def track_budget(
        self,
        budget_limit: float,
        spent: float
    ) -> Dict[str, Any]:
        """
        Track budget usage.

        Args:
            budget_limit: Total budget limit
            spent: Amount spent so far

        Returns:
            Budget status dict
        """
        remaining = budget_limit - spent
        usage_ratio = spent / budget_limit if budget_limit > 0 else 0.0

        return {
            "limit": budget_limit,
            "spent": spent,
            "remaining": remaining,
            "usage_ratio": usage_ratio,
            "exceeded": spent > budget_limit,
        }

    def estimate_text_tokens(self, text: str, model: Optional[str] = None) -> int:
        """
        Estimate token count for text.

        Simple approximation: ~4 chars per token for English,
        ~2 chars per token for Chinese.

        Args:
            text: Input text
            model: Model identifier

        Returns:
            Estimated token count
        """
        # Check if text is mostly Chinese
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        total_chars = len(text)

        if chinese_chars / max(1, total_chars) > 0.5:
            # Mostly Chinese: ~2 chars per token
            return total_chars // 2
        else:
            # Mostly English/Latin: ~4 chars per token
            return total_chars // 4

    def get_model_context_limit(self, model: Optional[str] = None) -> int:
        """
        Get model context window size.

        Args:
            model: Model identifier

        Returns:
            Context limit in tokens
        """
        if model is None:
            model = self.default_model

        context_limits = {
            ModelType.QWEN_TURBO: 8000,
            ModelType.QWEN_PLUS: 32000,
            ModelType.QWEN_MAX: 32000,
            ModelType.GPT_35_TURBO: 16000,
            ModelType.GPT_4: 8000,
            ModelType.GPT_4_TURBO: 128000,
            ModelType.CLAUDE_INSTANT: 100000,
            ModelType.CLAUDE_2: 100000,
            ModelType.CLAUDE_3_SONNET: 200000,
        }

        return context_limits.get(model, 8000)

    def is_within_budget(
        self,
        estimated_cost: float,
        current_spent: float,
        budget_limit: float
    ) -> bool:
        """
        Check if operation is within budget.

        Args:
            estimated_cost: Estimated cost of operation
            current_spent: Current amount spent
            budget_limit: Total budget limit

        Returns:
            True if within budget
        """
        projected_total = current_spent + estimated_cost
        return projected_total <= budget_limit
