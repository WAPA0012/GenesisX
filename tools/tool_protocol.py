"""
Tool Protocol: Unified Tool Interface with Risk Assessment

Defines:
- Base tool interface
- Tool metadata (risk, cost, determinism)

References:
- 代码大纲架构 tools/tool_protocol.py
- 论文 3.11.3 Deterministic Tool & Replay
"""

from typing import Dict, Any, Optional, Callable, Tuple
from abc import ABC, abstractmethod
from enum import Enum


class ToolRiskLevel(str, Enum):
    """Tool risk levels"""
    SAFE = "safe"          # Read-only, no side effects
    LOW = "low"            # Minimal side effects
    MEDIUM = "medium"      # Moderate side effects
    HIGH = "high"          # Significant side effects
    CRITICAL = "critical"  # Irreversible actions


class ToolDeterminism(str, Enum):
    """Tool determinism levels"""
    DETERMINISTIC = "deterministic"      # Always same output for same input
    QUASI_DETERMINISTIC = "quasi"        # Mostly deterministic (time-dependent)
    NON_DETERMINISTIC = "non_deterministic"  # Random or external state


class ToolMetadata:
    """Tool metadata for safety and replay"""

    def __init__(
        self,
        tool_id: str,
        name: str,
        description: str,
        risk_level: ToolRiskLevel,
        determinism: ToolDeterminism,
        requires_approval: bool = False,
        cost_estimate: float = 0.0,
        tags: Optional[list] = None,
    ):
        self.tool_id = tool_id
        self.name = name
        self.description = description
        self.risk_level = risk_level
        self.determinism = determinism
        self.requires_approval = requires_approval
        self.cost_estimate = cost_estimate
        self.tags = tags or []

    def get_risk_score(self) -> float:
        """Get numeric risk score [0, 1]"""
        risk_scores = {
            ToolRiskLevel.SAFE: 0.0,
            ToolRiskLevel.LOW: 0.25,
            ToolRiskLevel.MEDIUM: 0.5,
            ToolRiskLevel.HIGH: 0.75,
            ToolRiskLevel.CRITICAL: 1.0,
        }
        return risk_scores.get(self.risk_level, 0.5)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict"""
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "description": self.description,
            "risk_level": self.risk_level,
            "determinism": self.determinism,
            "requires_approval": self.requires_approval,
            "cost_estimate": self.cost_estimate,
            "tags": self.tags,
        }


class Tool(ABC):
    """
    Abstract base class for all tools.

    All tools must implement:
    - get_metadata(): Return tool metadata
    - execute(): Execute tool with parameters

    Enhanced: 支持前置条件(preconditions)和后置条件(postconditions)检查.
    """

    def __init__(self):
        """Initialize tool with empty condition lists."""
        # 前置条件列表 (instance-level to avoid shared mutable state)
        self.preconditions: list = []
        # 后置条件列表
        self.postconditions: list = []

    @abstractmethod
    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata"""
        pass

    @abstractmethod
    def execute(self, parameters: Dict[str, Any]) -> Any:
        """
        Execute tool with parameters.

        Args:
            parameters: Tool parameters

        Returns:
            Tool output
        """
        pass

    def add_precondition(self, condition: Callable[[Dict[str, Any]], bool]):
        """添加前置条件（论文P2-11扩展: 异常处理）

        Args:
            condition: 条件函数，接收参数字典，返回bool
        """
        self.preconditions.append(condition)

    def add_postcondition(self, condition: Callable[[Any, Dict[str, Any]], bool]):
        """添加后置条件（论文P2-11扩展: 异常处理）

        Args:
            condition: 条件函数，接收输出和参数字典，返回bool
        """
        self.postconditions.append(condition)

    def validate_parameters(self, parameters: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate parameters before execution (含前置条件检查).

        Override this method to add custom validation.

        Args:
            parameters: Tool parameters

        Returns:
            (is_valid, error_message) 元组
        """
        # 检查前置条件
        for i, condition in enumerate(self.preconditions):
            try:
                if not condition(parameters):
                    return False, f"Precondition {i} failed"
            except Exception as e:
                return False, f"Precondition {i} error: {e}"

        return True, None

    def validate_output(self, output: Any, parameters: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """验证输出（含后置条件检查）

        Args:
            output: 工具执行输出
            parameters: 工具参数

        Returns:
            (is_valid, error_message) 元组
        """
        # 检查后置条件
        for i, condition in enumerate(self.postconditions):
            try:
                if not condition(output, parameters):
                    return False, f"Postcondition {i} failed"
            except Exception as e:
                return False, f"Postcondition {i} error: {e}"

        return True, None

