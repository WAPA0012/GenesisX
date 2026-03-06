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

# Cost model
try:
    from .cost_model import CostModel, ModelType
except ImportError:
    CostModel = None
    ModelType = None

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

# ========== 新增工具模块 ==========

# Vision module (image analysis, OCR)
try:
    from .vision import (
        VisionClient,
        VisionModel,
        VisionCapability,
        create_vision_client,
        analyze_image,
        ocr_image,
    )
except ImportError:
    VisionClient = None
    VisionModel = None
    VisionCapability = None
    create_vision_client = None
    analyze_image = None
    ocr_image = None

# Messaging module (active message sending)
try:
    from .messaging import (
        Message,
        MessagePriority,
        MessageType,
        MessageChannel,
        ConsoleChannel,
        LogChannel,
        WebhookChannel,
        CallbackChannel,
        MessagingSystem,
        get_messaging_system,
        send_message,
        notify_user,
        alert_error,
        share_insight,
    )
except ImportError:
    Message = None
    MessagePriority = None
    MessageType = None
    MessageChannel = None
    ConsoleChannel = None
    LogChannel = None
    WebhookChannel = None
    CallbackChannel = None
    MessagingSystem = None
    get_messaging_system = None
    send_message = None
    notify_user = None
    alert_error = None
    share_insight = None

# Voice module (TTS)
try:
    from .voice import (
        VoiceOutput,
        TTSEngine,
        VoiceGender,
        VoiceEmotion,
        get_voice_output,
        speak,
        is_voice_available,
    )
except ImportError:
    VoiceOutput = None
    TTSEngine = None
    VoiceGender = None
    VoiceEmotion = None
    get_voice_output = None
    speak = None
    is_voice_available = None

__all__ = [
    # LLM API
    "UniversalLLM",
    "LLMConfig",
    "LLMClient",  # 添加向后兼容
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
    # Cost model
    "CostModel",
    "ModelType",
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
    # Vision module
    "VisionClient",
    "VisionModel",
    "VisionCapability",
    "create_vision_client",
    "analyze_image",
    "ocr_image",
    # Messaging module
    "Message",
    "MessagePriority",
    "MessageType",
    "MessageChannel",
    "ConsoleChannel",
    "LogChannel",
    "WebhookChannel",
    "CallbackChannel",
    "MessagingSystem",
    "get_messaging_system",
    "send_message",
    "notify_user",
    "alert_error",
    "share_insight",
    # Voice module
    "VoiceOutput",
    "TTSEngine",
    "VoiceGender",
    "VoiceEmotion",
    "get_voice_output",
    "speak",
    "is_voice_available",
]
