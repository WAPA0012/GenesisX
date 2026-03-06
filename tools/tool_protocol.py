"""
Tool Protocol: Unified Tool Interface with Risk Assessment

Defines:
- Base tool interface
- Tool metadata (risk, cost, determinism)
- Tool execution wrapper

References:
- 代码大纲架构 tools/tool_protocol.py
- 论文 3.11.3 Deterministic Tool & Replay
"""

from typing import Dict, Any, Optional, Callable, Tuple
from abc import ABC, abstractmethod
from enum import Enum
import time


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


class ToolExecutor:
    """
    Tool execution wrapper with risk assessment and logging.

    Wraps tool execution with:
    - Parameter validation
    - Risk checking
    - Cost estimation
    - Latency tracking
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tools: Dict[str, Tool] = {}

        # Execution limits
        # Default max_risk_online=0.75 blocks CRITICAL (1.0) tools unless overridden
        self.max_risk_online = config.get("max_risk_online", 0.75)
        self.max_risk_offline = config.get("max_risk_offline", 0.3)

    def register_tool(self, tool: Tool):
        """
        Register a tool.

        Args:
            tool: Tool instance
        """
        metadata = tool.get_metadata()
        self.tools[metadata.tool_id] = tool

    def execute_tool(
        self,
        tool_id: str,
        parameters: Dict[str, Any],
        is_offline: bool = False
    ) -> Dict[str, Any]:
        """
        Execute a tool with safety checks (含前置/后置条件验证).

        Enhanced:
        - 前置条件检查
        - 后置条件验证
        - 动态成本计算

        Args:
            tool_id: Tool identifier
            parameters: Tool parameters
            is_offline: Whether in offline mode

        Returns:
            Execution result dict with output, latency, cost
        """
        # Check if tool exists
        if tool_id not in self.tools:
            return {
                "success": False,
                "error": f"Tool '{tool_id}' not found",
            }

        tool = self.tools[tool_id]
        metadata = tool.get_metadata()

        # Risk check
        risk_score = metadata.get_risk_score()
        max_risk = self.max_risk_offline if is_offline else self.max_risk_online

        if risk_score > max_risk:
            return {
                "success": False,
                "error": f"Tool risk ({risk_score:.2f}) exceeds limit ({max_risk:.2f})",
                "risk_score": risk_score,
            }

        # Parameter validation (含前置条件检查)
        is_valid, error_msg = tool.validate_parameters(parameters)
        if not is_valid:
            return {
                "success": False,
                "error": error_msg or "Invalid parameters",
            }

        # Execute with timing
        start_time = time.time()

        try:
            output = tool.execute(parameters)
            success = True
            error = None

            # 后置条件验证（新增）
            is_valid, error_msg = tool.validate_output(output, parameters)
            if not is_valid:
                return {
                    "success": False,
                    "output": output,
                    "error": error_msg or "Postcondition validation failed",
                    "latency_ms": (time.time() - start_time) * 1000.0,
                    "risk_score": risk_score,
                }

        except Exception as e:
            output = None
            success = False
            error = str(e)

        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000.0

        # 动态成本计算（新增）
        actual_cost = self._compute_dynamic_cost(tool_id, parameters, latency_ms, metadata)

        return {
            "success": success,
            "output": output,
            "error": error,
            "latency_ms": latency_ms,
            "risk_score": risk_score,
            "cost_estimate": metadata.cost_estimate,
            "actual_cost": actual_cost,
        }

    def _compute_dynamic_cost(
        self,
        tool_id: str,
        parameters: Dict[str, Any],
        latency_ms: float,
        metadata: ToolMetadata,
    ) -> float:
        """计算动态成本（考虑实际执行情况）

        Args:
            tool_id: 工具ID
            parameters: 参数
            latency_ms: 延迟
            metadata: 工具元数据

        Returns:
            计算后的成本
        """
        # 基础成本
        base_cost = metadata.cost_estimate

        # 基于延迟调整成本
        latency_cost = latency_ms / 1000.0 * 0.001  # $0.001 per second

        # 基于风险等级调整
        risk_cost = metadata.get_risk_score() * 0.01

        # 参数大小成本（对于数据密集型工具）
        param_cost = 0.0
        if tool_id == "file_ops":
            file_size = len(str(parameters.get("content", "")))
            param_cost = min(0.01, file_size / 1024 / 1024 * 0.001)  # $0.001 per MB

        return base_cost + latency_cost + risk_cost + param_cost

    def get_tool_metadata(self, tool_id: str) -> Optional[ToolMetadata]:
        """Get metadata for a tool"""
        if tool_id not in self.tools:
            return None

        return self.tools[tool_id].get_metadata()

    def list_tools(self) -> list:
        """List all registered tools"""
        return [
            tool.get_metadata().to_dict()
            for tool in self.tools.values()
        ]

    def can_execute_in_mode(
        self,
        tool_id: str,
        is_offline: bool = False
    ) -> bool:
        """
        Check if tool can be executed in current mode.

        Args:
            tool_id: Tool identifier
            is_offline: Whether in offline mode

        Returns:
            True if allowed
        """
        metadata = self.get_tool_metadata(tool_id)
        if not metadata:
            return False

        risk_score = metadata.get_risk_score()
        max_risk = self.max_risk_offline if is_offline else self.max_risk_online

        return risk_score <= max_risk
