"""Tool Registry - manages available tools and their properties."""
from typing import Dict, List, Optional, Any
from common.models import CostVector
from pydantic import BaseModel


class ToolSpec(BaseModel):
    """Specification for a tool.

    论文 Section 3.11: 工具规范五元组 <id, schema, cost_model, pre, post>
    修复 H12: 添加 preconditions 和 postconditions 字段。
    """
    tool_id: str
    description: str
    risk_level: float = 0.0
    cost_model: Dict[str, Any] = {}
    capabilities_required: List[str] = []
    input_schema: Dict[str, Any] = {}
    # 修复 H12: 论文要求的前置条件和后置条件
    preconditions: List[str] = []   # 调用前必须满足的条件 (如 "energy > 0.2")
    postconditions: List[str] = []  # 调用成功后保证的状态 (如 "file_exists")


class ToolRegistry:
    """Registry of available tools."""

    def __init__(self):
        """Initialize tool registry."""
        self._tools: Dict[str, ToolSpec] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        """Register default tools."""
        # Qianwen Chat
        self.register(ToolSpec(
            tool_id="qianwen_chat",
            description="Chat with Qianwen LLM",
            risk_level=0.0,
            cost_model={"cpu_tokens": 1000, "money": 0.001},
            capabilities_required=["llm_access"],
            preconditions=["energy > 0.1"],
            postconditions=["response_generated"],
        ))

        # File Read
        self.register(ToolSpec(
            tool_id="file_read",
            description="Read file contents",
            risk_level=0.1,
            cost_model={"io_ops": 1},
            capabilities_required=["file_system"],
            preconditions=["energy > 0.05"],
            postconditions=["file_content_available"],
        ))

        # Web Search
        self.register(ToolSpec(
            tool_id="web_search",
            description="Search the web",
            risk_level=0.3,
            cost_model={"net_bytes": 10000, "money": 0.01},
            capabilities_required=["network"],
            preconditions=["energy > 0.15", "stress < 0.9"],
            postconditions=["search_results_available"],
        ))

        # ========== 新增工具 ==========

        # Time Perception
        self.register(ToolSpec(
            tool_id="get_time",
            description="Get current time and time context",
            risk_level=0.0,
            cost_model={"cpu_cycles": 100},
            capabilities_required=["time_awareness"],
            preconditions=[],
            postconditions=["time_perception_updated"],
        ))

        # Image Analysis
        self.register(ToolSpec(
            tool_id="analyze_image",
            description="Analyze image content using multimodal LLM",
            risk_level=0.1,
            cost_model={"cpu_tokens": 2000, "money": 0.005},
            capabilities_required=["vision"],
            preconditions=["energy > 0.1"],
            postconditions=["visual_perception_acquired"],
        ))

        # OCR
        self.register(ToolSpec(
            tool_id="image_to_text",
            description="Extract text from image using OCR",
            risk_level=0.1,
            cost_model={"cpu_tokens": 1500, "money": 0.003},
            capabilities_required=["vision"],
            preconditions=["energy > 0.1"],
            postconditions=["text_extracted"],
        ))

        # Read Own Logs
        self.register(ToolSpec(
            tool_id="read_own_logs",
            description="Read own log files for self-reflection",
            risk_level=0.0,
            cost_model={"io_ops": 5},
            capabilities_required=["self_awareness"],
            preconditions=[],
            postconditions=["self_reflection_data_acquired"],
        ))

        # System Stats
        self.register(ToolSpec(
            tool_id="system_stats",
            description="Get system resource statistics (CPU, memory)",
            risk_level=0.0,
            cost_model={"cpu_cycles": 500},
            capabilities_required=["self_awareness"],
            preconditions=[],
            postconditions=["homeostasis_perception_updated"],
        ))

        # Send Message
        self.register(ToolSpec(
            tool_id="send_message",
            description="Send proactive message to user",
            risk_level=0.2,
            cost_model={"io_ops": 2},
            capabilities_required=["messaging"],
            preconditions=["energy > 0.05"],
            postconditions=["message_sent"],
        ))

        # Voice Speak
        self.register(ToolSpec(
            tool_id="voice_speak",
            description="Convert text to speech and play audio",
            risk_level=0.1,
            cost_model={"cpu_cycles": 5000},
            capabilities_required=["voice_output"],
            preconditions=["energy > 0.1"],
            postconditions=["audio_played"],
        ))

        # Schedule Action
        self.register(ToolSpec(
            tool_id="schedule_action",
            description="Schedule an action for future execution",
            risk_level=0.2,
            cost_model={"cpu_cycles": 200},
            capabilities_required=["scheduling"],
            preconditions=["energy > 0.05"],
            postconditions=["action_scheduled"],
        ))

    def register(self, spec: ToolSpec):
        """Register a tool.

        Args:
            spec: Tool specification
        """
        self._tools[spec.tool_id] = spec

    def get(self, tool_id: str) -> Optional[ToolSpec]:
        """Get tool spec by ID.

        Args:
            tool_id: Tool ID

        Returns:
            ToolSpec or None
        """
        return self._tools.get(tool_id)

    def list_available(self, capabilities: List[str]) -> List[str]:
        """List tools available given capabilities.

        Args:
            capabilities: Available capabilities

        Returns:
            List of tool IDs
        """
        available = []
        for tool_id, spec in self._tools.items():
            # Check if all required capabilities are available
            if all(cap in capabilities for cap in spec.capabilities_required):
                available.append(tool_id)
        return available

    def get_all(self) -> Dict[str, ToolSpec]:
        """Get all registered tools.

        Returns:
            Dict of tool_id -> ToolSpec
        """
        return self._tools.copy()
