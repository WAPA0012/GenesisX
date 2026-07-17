"""Tools system - Universal LLM API and other tools."""

from .llm_api import (
    UniversalLLM,
    LLMConfig,
    create_llm_from_preset,
    create_llm_from_env,
)

# LLM Client (unified interface)
try:
    from .llm_client import LLMClient
except ImportError:
    LLMClient = None

# Enhanced tool system v2
try:
    from .tool_system_v2 import (
        ToolCall,
        ToolResult,
        ToolCallRecord,
        ToolCallLogger,
        SmartToolParser,
        EnhancedToolExecutor,
    )
except ImportError:
    ToolCall = None
    ToolResult = None
    ToolCallRecord = None
    ToolCallLogger = None
    SmartToolParser = None
    EnhancedToolExecutor = None

# Tool registry and capability management
try:
    from .tool_registry import ToolRegistry, ToolSpec
except ImportError:
    ToolRegistry = None
    ToolSpec = None

try:
    from .capability import CapabilityToken, CapabilityManager
except ImportError:
    CapabilityToken = None
    CapabilityManager = None

# Import CostVector from common.models for convenience
try:
    from common.models import CostVector
except ImportError:
    CostVector = None

# Mind Field Architecture - Paper-compliant Multi-Model System
try:
    from .blackboard import (
        # Enums
        ModelConfig,
        ExpertRole,
        # Blackboard
        Blackboard,
        BlackboardState,
        BlackboardSlot,
        # Expert models
        ExpertConfig,
        ExpertModel,
        ExpertResult,
        DEFAULT_SYSTEM_PROMPTS,
        # Orchestrator
        MindFieldOrchestrator,
        # Factory functions
        config_select,
        create_core5_experts,
        create_orchestrator,
    )
except ImportError:
    ModelConfig = None
    ExpertRole = None
    Blackboard = None
    BlackboardState = None
    BlackboardSlot = None
    ExpertConfig = None
    ExpertModel = None
    ExpertResult = None
    DEFAULT_SYSTEM_PROMPTS = None
    MindFieldOrchestrator = None
    config_select = None
    create_core5_experts = None
    create_orchestrator = None

# P1-7/8/9 + tools dead code cleanup:
# 已删除: vision.py / messaging.py / voice.py / embeddings.py / code_exec.py /
#         safe_executor.py / web_search.py / file_ops.py (全部零引用)

__all__ = [
    # LLM API
    "UniversalLLM",
    "LLMConfig",
    "LLMClient",
    "create_llm_from_preset",
    "create_llm_from_env",
    # Tool system v2
    "ToolCall",
    "ToolResult",
    "ToolCallRecord",
    "ToolCallLogger",
    "SmartToolParser",
    "EnhancedToolExecutor",
    # Tool registry and capability management
    "ToolRegistry",
    "ToolSpec",
    "CapabilityToken",
    "CapabilityManager",
    "CostVector",
    # Mind Field Architecture (论文 3.4.2)
    "ModelConfig",
    "ExpertRole",
    "Blackboard",
    "BlackboardState",
    "BlackboardSlot",
    "ExpertConfig",
    "ExpertModel",
    "ExpertResult",
    "DEFAULT_SYSTEM_PROMPTS",
    "MindFieldOrchestrator",
    "config_select",
    "create_core5_experts",
    "create_orchestrator",
]
