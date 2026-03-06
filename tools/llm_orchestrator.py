"""LLM Orchestrator - Unified interface supporting paper architecture.

统一的 LLM 调用接口，支持:
- 单模型模式 (论文 Single)
- Core5 多模型模式
- Full7 完整模式
- Adaptive 自适应模式
"""

import os
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import yaml

from common.logger import get_logger

logger = get_logger(__name__)


class LLMMOrchestrator:
    """统一的 LLM 编排器

    根据 configuration 自动选择单模型或多模型模式。
    支持论文 3.4.2 节的四种配置模式。
    """

    def __init__(
        self,
        enable_multi_model: bool = False,
        config_mode: str = "single",
        config_path: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """初始化 LLM 编排器

        Args:
            enable_multi_model: 是否启用多模型（已弃用，使用 config_mode）
            config_mode: 配置模式 (single/core5/full7/adaptive)
            config_path: 配置文件路径
            config: 直接传入配置字典
        """
        self.config_mode = config_mode
        self._mind_field_orchestrator = None
        self._single_llm = None
        self._blackboard = None

        # 加载配置
        if config:
            self.config = config
        elif config_path:
            self.config = self._load_config_file(config_path)
        else:
            self.config = self._load_default_config()

        # 检查是否启用多模型
        mind_field_config = self.config.get("mind_field", {})
        enabled = mind_field_config.get("enabled", False)

        if enable_multi_model or enabled:
            # 使用指定的配置模式
            mode_from_config = mind_field_config.get("config_mode", "single")
            self.config_mode = mode_from_config
            self._init_mind_field()
        else:
            self._init_single_model()

        logger.info(f"LLMOrchestrator initialized (mode={self.config_mode})")

    def _load_config_file(self, path: str) -> Dict[str, Any]:
        """从文件加载配置"""
        config_path = Path(path)
        if not config_path.exists():
            logger.warning(f"Config file not found: {path}")
            return {}

        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        default_paths = [
            "config/mind_field.yaml",
            "config/multi_model.yaml",
            "../config/mind_field.yaml",
        ]

        for path in default_paths:
            if Path(path).exists():
                return self._load_config_file(path)

        return {}

    def _init_single_model(self):
        """初始化单模型模式"""
        from tools.llm_api import create_llm_from_env
        try:
            self._single_llm = create_llm_from_env()
            logger.info("Single model mode initialized")
        except Exception as e:
            logger.error(f"Failed to initialize single model: {e}")
            self._single_llm = None

    def _init_mind_field(self):
        """初始化 Mind Field 多模型模式"""
        from tools.blackboard import (
            MindFieldOrchestrator,
            ExpertConfig,
            ExpertRole,
            ModelConfig,
            Blackboard
        )
        try:
            # 解析配置
            mind_field_config = self.config.get("mind_field", {})
            experts_config = self.config.get("experts", [])

            # 构建专家配置列表
            expert_configs = []
            for exp_cfg in experts_config:
                if not exp_cfg.get("enabled", True):
                    continue

                role = ExpertRole(exp_cfg["role"])
                expert_cfg = ExpertConfig(
                    role=role,
                    name=exp_cfg["name"],
                    llm_config={
                        "model": self._expand_env(exp_cfg.get("model", "")),
                        "api_base": self._expand_env(exp_cfg.get("api_base", "")),
                        "api_key": self._expand_env(exp_cfg.get("api_key", "")),
                        "provider": exp_cfg.get("provider", "openai"),
                        "temperature": exp_cfg.get("temperature", 0.7),
                        "max_tokens": exp_cfg.get("max_tokens", 2000),
                    },
                    enabled=exp_cfg.get("enabled", True),
                    priority=exp_cfg.get("priority", 0)
                )
                expert_configs.append(expert_cfg)

            # 映射配置模式
            mode_map = {
                "single": ModelConfig.SINGLE,
                "core5": ModelConfig.CORE5,
                "full7": ModelConfig.FULL7,
                "adaptive": ModelConfig.ADAPTIVE,
            }
            model_config = mode_map.get(
                self.config_mode,
                ModelConfig.SINGLE
            )

            # 创建编排器
            self._mind_field_orchestrator = MindFieldOrchestrator(
                experts=expert_configs,
                config_mode=model_config
            )

            # 保存黑板引用
            self._blackboard = self._mind_field_orchestrator.blackboard

            logger.info(f"Mind Field mode initialized: {self.config_mode}")

        except Exception as e:
            logger.error(f"Failed to initialize Mind Field: {e}, falling back to single model")
            self.config_mode = "single"
            self._init_single_model()

    def _expand_env(self, value: str) -> str:
        """展开环境变量"""
        if not value:
            return ""

        if value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            return os.getenv(env_var, "")

        return value

    def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """发送聊天请求

        Args:
            messages: 对话消息列表
            tools: 可用工具列表
            **kwargs: 额外参数

        Returns:
            响应字典
        """
        context = kwargs.get("context", {})
        tick = kwargs.get("tick", 0)

        # 提取用户消息
        if messages and messages[-1].get("role") == "user":
            user_message = messages[-1]["content"]
        else:
            user_message = str(messages)

        if self._mind_field_orchestrator:
            # 多模型模式
            result = self._mind_field_orchestrator.process(
                user_message,
                context,
                tick
            )
            # 转换为统一格式
            return {
                "ok": result.get("ok", True),
                "text": result.get("text", ""),
                "tool_calls": result.get("tool_calls"),
                "usage": result.get("usage", {}),
                "config_mode": result.get("config_mode"),
                "active_experts": result.get("active_experts", 1),
                "blackboard": result.get("blackboard")
            }

        elif self._single_llm:
            # 单模型模式
            result = self._single_llm.chat(messages, tools=tools, **kwargs)
            # 转换为统一格式
            return {
                "ok": result.get("ok", True),
                "text": result.get("text", ""),
                "tool_calls": result.get("tool_calls"),
                "usage": result.get("usage", {}),
                "config_mode": "single",
                "active_experts": 1,
                "error": result.get("error")
            }

        else:
            return {
                "ok": False,
                "error": "LLM not initialized",
                "text": "",
                "config_mode": self.config_mode
            }

    @property
    def blackboard(self):
        """获取黑板实例（多模型模式下）"""
        if self._mind_field_orchestrator:
            return self._mind_field_orchestrator.blackboard
        return self._blackboard  # 单模型模式下可能为 None

    def set_config_mode(self, mode: str) -> None:
        """设置配置模式

        Args:
            mode: single, core5, full7, 或 adaptive
        """
        valid_modes = ["single", "core5", "full7", "adaptive"]
        if mode not in valid_modes:
            logger.warning(f"Invalid config mode: {mode}, must be one of {valid_modes}")
            return

        self.config_mode = mode

        if self._mind_field_orchestrator:
            from tools.blackboard import ModelConfig
            mode_map = {
                "single": ModelConfig.SINGLE,
                "core5": ModelConfig.CORE5,
                "full7": ModelConfig.FULL7,
                "adaptive": ModelConfig.ADAPTIVE,
            }
            self._mind_field_orchestrator.set_config_mode(mode_map[mode])
            logger.info(f"Config mode changed to: {mode}")

    def update_middle_vars(self, et: float, ct: float, es: float) -> None:
        """更新人格中间变量

        Args:
            et: 探索倾向 Exploration Tendency [0, 1]
            ct: 保守倾向 Conservation Tendency [0, 1]
            es: 情绪敏感度 Emotional Sensitivity [0, 1]
        """
        if self._blackboard:
            self._blackboard.update_middle_vars(et, ct, es)
            logger.debug(f"Middle vars updated: ET={et:.2f}, CT={ct:.2f}, ES={es:.2f}")

    def update_resource_state(self, compute: float, memory: float) -> None:
        """更新资源状态

        Args:
            compute: 算力可用度 [0, 1]
            memory: 内存可用度 [0, 1]
        """
        if self._blackboard:
            self._blackboard.update_resource_state(compute, memory)
            logger.debug(f"Resource state updated: Compute={compute:.2f}, Memory={memory:.2f}")

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        if self._mind_field_orchestrator:
            stats = self._mind_field_orchestrator.get_statistics()
            stats["multi_model_enabled"] = True
            return stats

        return {
            "mode": "single",
            "multi_model_enabled": False,
            "config_mode": self.config_mode
        }

    @classmethod
    def from_config(cls, config_path: str) -> "LLMMOrchestrator":
        """从配置文件创建编排器

        Args:
            config_path: 配置文件路径

        Returns:
            初始化好的编排器
        """
        return cls(config_path=config_path)

    @classmethod
    def from_env(cls) -> "LLMMOrchestrator":
        """从环境变量创建编排器（单模型模式）"""
        return cls(enable_multi_model=False, config_mode="single")


# 兼性别名
LLMOrchestrator = LLMMOrchestrator


def create_llm_orchestrator(
    enable_multi_model: bool = False,
    config_mode: str = "single",
    config_path: Optional[str] = None
) -> LLMMOrchestrator:
    """创建 LLM 编排器的便捷函数

    Args:
        enable_multi_model: 是否启用多模型（已弃用）
        config_mode: 配置模式
        config_path: 配置文件路径

    Returns:
        LLM 编排器实例
    """
    return LLMMOrchestrator(
        enable_multi_model=enable_multi_model,
        config_mode=config_mode,
        config_path=config_path
    )
