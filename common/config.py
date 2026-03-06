"""Configuration loading utilities."""
import os
import yaml
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Import logger
from .logger import get_logger
logger = get_logger(__name__)


class Config(BaseSettings):
    """Main configuration using Pydantic BaseSettings.

    Reads environment variables and config files.
    """
    # LLM API Configuration (Universal)
    llm_api_base: str = Field(default="")
    llm_api_key: str = Field(default="")
    llm_model: str = Field(default="")

    # Legacy: Dashscope (for backward compatibility)
    dashscope_api_key: str = Field(default="")

    # Paths
    config_dir: Path = Field(default=Path("config"))
    artifacts_dir: Path = Field(default=Path("artifacts"))

    # Runtime with validation
    tick_dt: float = Field(default=1.0, ge=0.1, le=60.0)  # 0.1s to 60s
    max_ticks: int = Field(default=100000, ge=1, le=10000000)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @field_validator('llm_model')
    @classmethod
    def validate_llm_model(cls, v: str) -> str:
        """Validate LLM model name is not empty if API key is set."""
        if not v or v.strip() == "":
            # Allow empty model if API key not set (simulation mode)
            return ""
        return v.strip()

    @model_validator(mode='after')
    def validate_llm_config(self) -> 'Config':
        """Validate LLM configuration consistency."""
        # If API key is set, API base should also be set
        if self.llm_api_key and not self.llm_api_base:
            logger.warning("LLM_API_KEY is set but LLM_API_BASE is not set")
        return self


class RuntimeConfig(BaseModel):
    """Runtime configuration with validation.

    修复 H17: 允许额外字段，避免 runtime.yaml 中的配置被静默丢弃。
    """
    model_config = {"extra": "allow"}  # 修复 H17: 允许额外字段

    max_ticks: int = Field(default=100, ge=1, le=10000000)
    tick_dt: float = Field(default=1.0, ge=0.1, le=60.0)
    budgets: Dict[str, float] = Field(default_factory=dict)
    offline_interval: int = Field(default=100, ge=10, le=10000)
    offline_budget: Dict[str, Any] = Field(default_factory=lambda: {
        "max_tokens": 10000,
        "max_time_seconds": 300,
    })

    @field_validator('budgets')
    @classmethod
    def validate_budgets(cls, v: Dict[str, float]) -> Dict[str, float]:
        """Validate budget values are non-negative."""
        for key, value in v.items():
            if value < 0:
                logger.warning(f"Budget {key} is negative, setting to 0")
                v[key] = 0.0
        return v


class ValueSetpointsConfig(BaseModel):
    """Value dimension setpoints with validation."""
    value_dimensions: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    @field_validator('value_dimensions')
    @classmethod
    def validate_dimensions(cls, v: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Validate value dimension setpoints are in [0, 1].

        修复 v14: 使用5维核心价值向量
        """
        valid_dimensions = {
            "homeostasis", "attachment", "curiosity",
            "competence", "safety"
        }

        for dim_name, dim_config in v.items():
            if dim_name not in valid_dimensions:
                logger.warning(f"Unknown dimension: {dim_name}")
                continue

            if "setpoint" in dim_config:
                setpoint = dim_config["setpoint"]
                if not isinstance(setpoint, (int, float)):
                    logger.warning(f"Invalid setpoint type for {dim_name}, using default 0.5")
                    dim_config["setpoint"] = 0.5
                else:
                    dim_config["setpoint"] = max(0.0, min(1.0, float(setpoint)))

        return v


# Valid organ names
VALID_ORGANS = {"mind", "scout", "builder", "caretaker", "archivist", "immune"}


class OrganLLMConfig(BaseModel):
    """Organ LLM configuration with validation.

    支持三种模式：
    - independent: 独立对话，每个器官有独立会话，可单独配置
    - shared: 共享对话，所有器官共享一个会话
    - disabled: 无配置，器官使用规则模式
    """
    model_config = {"extra": "allow"}  # 允许额外字段

    mode: str = Field(default="independent")  # independent, shared, disabled
    max_history: int = Field(default=20, ge=1, le=100)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, ge=100, le=10000)
    memory: Dict[str, Any] = Field(default_factory=lambda: {
        "enabled": True,
        "use_llm_judge": True,
        "importance_threshold": 0.5,
    })
    # 器官独立配置（independent 模式）
    organs: Dict[str, Any] = Field(default_factory=dict)
    # 共享模式配置（shared 模式）
    shared: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('mode')
    @classmethod
    def validate_mode(cls, v: str) -> str:
        """Validate mode is independent, shared, or disabled."""
        valid_modes = ("independent", "shared", "disabled")
        if v not in valid_modes:
            logger.warning(f"Invalid organ_llm mode: {v}, using default 'independent'")
            return "independent"
        return v

    @field_validator('memory')
    @classmethod
    def validate_memory(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate memory config and set defaults."""
        defaults = {
            "enabled": True,
            "use_llm_judge": True,
            "importance_threshold": 0.5,
        }
        for key, default_value in defaults.items():
            if key not in v:
                v[key] = default_value

        # Clamp importance_threshold to [0, 1]
        if "importance_threshold" in v:
            v["importance_threshold"] = max(0.0, min(1.0, float(v["importance_threshold"])))

        return v

    @field_validator('organs')
    @classmethod
    def validate_organs(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate organ configurations."""
        for organ_name, organ_config in v.items():
            if organ_name not in VALID_ORGANS:
                logger.warning(f"Unknown organ name: {organ_name}")
                continue

            if not isinstance(organ_config, dict):
                logger.warning(f"Invalid config for organ {organ_name}, skipping")
                continue

            # Set default use_default_llm if not specified
            if "use_default_llm" not in organ_config:
                organ_config["use_default_llm"] = True

        return v

    @field_validator('shared')
    @classmethod
    def validate_shared(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate shared mode configuration."""
        if not v:
            v = {}
        # Set default use_default_llm if not specified
        if "use_default_llm" not in v:
            v["use_default_llm"] = True
        return v

    def get_organ_config(self, organ_name: str) -> Dict[str, Any]:
        """获取器官的完整配置（合并全局默认值）

        Args:
            organ_name: 器官名称

        Returns:
            包含 llm_config 和 session_config 的字典
        """
        if organ_name not in VALID_ORGANS:
            return {}

        organ_config = self.organs.get(organ_name, {})
        use_default_llm = organ_config.get("use_default_llm", True)

        result = {
            "use_default_llm": use_default_llm,
            "llm_config": None,  # None 表示使用全局 LLM
            "session_config": {
                "max_history": organ_config.get("max_history", self.max_history),
                "temperature": organ_config.get("temperature", self.temperature),
                "max_tokens": organ_config.get("max_tokens", self.max_tokens),
            }
        }

        # 如果使用自定义 LLM 配置
        if not use_default_llm and "llm" in organ_config:
            result["llm_config"] = organ_config["llm"]

        return result

    def get_shared_config(self) -> Dict[str, Any]:
        """获取共享模式的配置

        Returns:
            包含 llm_config 和 session_config 的字典
        """
        shared_config = self.shared or {}
        use_default_llm = shared_config.get("use_default_llm", True)

        result = {
            "use_default_llm": use_default_llm,
            "llm_config": None,  # None 表示使用全局 LLM
            "session_config": {
                "max_history": shared_config.get("max_history", self.max_history),
                "temperature": shared_config.get("temperature", self.temperature),
                "max_tokens": shared_config.get("max_tokens", self.max_tokens),
            }
        }

        # 如果使用自定义 LLM 配置
        if not use_default_llm and "llm" in shared_config:
            result["llm_config"] = shared_config["llm"]

        return result


def load_yaml(file_path: Path) -> Dict[str, Any]:
    """Load YAML configuration file."""
    if not file_path.exists():
        raise FileNotFoundError(f"Config file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_env_from_project_root() -> None:
    """Load .env file from project root directory.

    This ensures that .env is found even when running from web/ subdirectory.
    Uses python-dotenv for better compatibility.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        logger.debug("python-dotenv not available, skipping .env loading")
        return

    # Find project root by looking for .env file
    current_path = Path.cwd()
    env_path = None

    # Search upward for .env file
    search_path = current_path
    for _ in range(5):  # Search up to 5 levels up
        potential_env = search_path / ".env"
        if potential_env.exists():
            env_path = potential_env
            break
        search_path = search_path.parent

    if env_path:
        # Load using python-dotenv with override=True to ensure .env values are used
        try:
            load_dotenv(dotenv_path=env_path, override=True)
            logger.info(f"Loaded .env from {env_path}")
        except Exception as e:
            logger.warning(f"Failed to load .env from {env_path}: {e}")
    else:
        logger.debug("No .env file found in project root or parent directories")


def load_config(config_dir: Path = Path("config")) -> Dict[str, Any]:
    """Load all configuration files with validation.

    Returns:
        Dict containing:
        - runtime: Runtime configuration
        - genome: Personality DNA
        - value_setpoints: Value system parameters
        - tool_manifest: Tool definitions
        - organ_llm: Organ LLM session configuration
        - llm: LLM API configuration
        - session_id: Persistent session ID
    """
    # 尝试从项目根目录加载 .env 文件（即使从 web/ 子目录启动）
    _load_env_from_project_root()

    config = {}

    # Load each config file
    config_files = {
        "runtime": "runtime.yaml",
        "genome": "default_genome.yaml",
        "value_setpoints": "value_setpoints.yaml",
        "tool_manifest": "tool_manifest.yaml",
        "organ_llm": "organ_llm.yaml",
    }

    for key, filename in config_files.items():
        filepath = config_dir / filename
        try:
            config[key] = load_yaml(filepath)
            logger.debug(f"Loaded config file: {filepath}")
        except FileNotFoundError:
            logger.warning(f"Config file not found: {filepath}, using defaults")
            config[key] = {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML in {filepath}: {e}, using defaults")
            config[key] = {}
        except Exception as e:
            logger.error(f"Unexpected error loading {filepath}: {e}, using defaults")
            config[key] = {}

    # Validate runtime config
    if config.get("runtime"):
        try:
            runtime_config = RuntimeConfig(**config["runtime"])
            config["runtime"] = runtime_config.model_dump()
            logger.debug("Runtime config validated successfully")
        except Exception as e:
            logger.error(f"Runtime config validation failed: {e}, using defaults")
            config["runtime"] = RuntimeConfig().model_dump()

    # Validate value setpoints config
    if config.get("value_setpoints"):
        try:
            value_config = ValueSetpointsConfig(**config["value_setpoints"])
            config["value_setpoints"] = value_config.model_dump()
            logger.debug("Value setpoints config validated successfully")
        except Exception as e:
            logger.error(f"Value setpoints validation failed: {e}, using defaults")
            config["value_setpoints"] = ValueSetpointsConfig().model_dump()

    # Validate organ_llm config
    if config.get("organ_llm"):
        try:
            organ_llm_config = OrganLLMConfig(**config["organ_llm"])
            config["organ_llm"] = organ_llm_config.model_dump()
            logger.debug(f"Organ LLM config validated successfully (mode={config['organ_llm']['mode']})")
        except Exception as e:
            logger.error(f"Organ LLM config validation failed: {e}, using defaults")
            config["organ_llm"] = OrganLLMConfig().model_dump()
    else:
        # Set defaults if organ_llm.yaml not found
        config["organ_llm"] = OrganLLMConfig().model_dump()
        logger.debug("Organ LLM config not found, using defaults")

    # Load API key from environment (try new format first, fallback to legacy)
    llm_api_key = os.getenv("LLM_API_KEY", "")
    llm_api_base = os.getenv("LLM_API_BASE", "")
    llm_model = os.getenv("LLM_MODEL", "")
    llm_temperature = os.getenv("LLM_TEMPERATURE", "0.7")
    llm_max_tokens = os.getenv("LLM_MAX_TOKENS", "2000")

    # Session ID for persistent memory - 让 GenesisX 成为一个长期持续的数字生命
    session_id = os.getenv("GENESISX_SESSION_ID", "genesisx_persistent")

    # Debug: log if LLM config was found
    if llm_api_base:
        logger.info(f"LLM_API_BASE found: {llm_api_base[:30]}...")
    if llm_api_key:
        logger.info(f"LLM_API_KEY found: {llm_api_key[:10]}...")
    if llm_model:
        logger.info(f"LLM_MODEL found: {llm_model}")

    # Legacy fallback: if new format not set, try dashscope
    if not llm_api_key:
        llm_api_key = os.getenv("DASHSCOPE_API_KEY", "")
        if llm_api_key and not llm_api_base:
            llm_api_base = "https://dashscope.aliyuncs.com/compatible-mode/v1"
            llm_model = llm_model or "qwen-plus"
            logger.warning("=" * 60)
            logger.warning("DEPRECATED: Using legacy DASHSCOPE_API_KEY")
            logger.warning("Please migrate to new environment variables:")
            logger.warning("  LLM_API_KEY (instead of DASHSCOPE_API_KEY)")
            logger.warning("  LLM_API_BASE (instead of deriving from Dashscope)")
            logger.warning("  LLM_MODEL (explicitly specify model)")
            logger.warning("=" * 60)
    # Log deprecation notice if legacy env var is set even when new vars are available
    elif os.getenv("DASHSCOPE_API_KEY"):
        logger.info("Note: Both LLM_API_KEY and DASHSCOPE_API_KEY are set. Using LLM_API_KEY (recommended).")
        logger.info("You can safely unset DASHSCOPE_API_KEY from your environment.")

    if not llm_api_base:
        logger.warning("LLM_API_BASE not found. System will run in simulation mode.")
        logger.info("To enable LLM features, set LLM_API_BASE and LLM_API_KEY environment variables.")

    # Validate and parse numeric parameters
    try:
        temperature = float(llm_temperature)
        temperature = max(0.0, min(2.0, temperature))  # Clamp to reasonable range
    except ValueError:
        logger.warning(f"Invalid LLM_TEMPERATURE: {llm_temperature}, using default 0.7")
        temperature = 0.7

    try:
        max_tokens = int(llm_max_tokens)
        max_tokens = max(1, min(32000, max_tokens))  # Clamp to reasonable range
    except ValueError:
        logger.warning(f"Invalid LLM_MAX_TOKENS: {llm_max_tokens}, using default 2000")
        max_tokens = 2000

    config["llm"] = {
        "api_base": llm_api_base,
        "api_key": llm_api_key,
        "model": llm_model,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    # Session ID for persistent memory
    config["session_id"] = session_id
    logger.info(f"Session ID: {session_id} (persistent memory enabled)")

    # Keep legacy key for backward compatibility
    # DEPRECATED: Use config["llm"]["api_key"] instead
    # This is only for compatibility with old code
    if llm_api_key:
        config["api_key"] = llm_api_key
        logger.debug("Legacy 'api_key' key set (DEPRECATED - use 'llm.api_key' instead)")

    logger.info("Configuration loaded and validated successfully")
    return config
