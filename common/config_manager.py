"""
Genesis X Configuration Manager

A production-ready configuration management system that supports:
- Multiple configuration sources (environment variables, YAML, JSON)
- Environment-specific configs (dev/staging/prod)
- Type-safe configuration validation with Pydantic
- Hot reload support for configuration files
- Secret management (API keys, database passwords)
- Default configurations with overrides

Author: Genesis X Team
License: MIT
"""

import os
import json
import yaml
import time
from pathlib import Path
from typing import Any, Dict, Optional, List, Union
from enum import Enum
from threading import Lock, Thread
from dataclasses import dataclass
from datetime import datetime, timezone

from pydantic import BaseModel, Field, ValidationError, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 修复 M31: 使用项目内置 logger 替代 loguru (未在 requirements.txt 中声明)
from .logger import get_logger
logger = get_logger(__name__)


class Environment(str, Enum):
    """Supported environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class DatabaseConfig(BaseModel):
    """Database configuration."""
    url: SecretStr = Field(description="Database connection URL")
    pool_size: int = Field(default=10, ge=1, le=100, description="Connection pool size")
    pool_timeout: int = Field(default=30, ge=1, description="Pool timeout in seconds")
    echo: bool = Field(default=False, description="Echo SQL statements")
    pool_recycle: int = Field(default=3600, description="Pool recycle time in seconds")


class APIConfig(BaseModel):
    """API server configuration."""
    host: str = Field(default="0.0.0.0", description="API host")
    port: int = Field(default=8000, ge=1, le=65535, description="API port")
    workers: int = Field(default=4, ge=1, le=32, description="Number of workers")
    reload: bool = Field(default=False, description="Enable auto-reload")
    cors_origins: List[str] = Field(default=["*"], description="CORS allowed origins")
    rate_limit: int = Field(default=100, ge=1, description="Requests per minute")
    timeout: int = Field(default=30, ge=1, description="Request timeout in seconds")


class LLMConfig(BaseModel):
    """LLM (Language Model) configuration."""
    provider: str = Field(default="dashscope", description="LLM provider")
    model: str = Field(default="qwen-plus", description="Model name")
    api_key: SecretStr = Field(description="API key for LLM service")
    max_tokens: int = Field(default=4000, ge=1, description="Max tokens per request")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    top_p: float = Field(default=0.9, ge=0.0, le=1.0, description="Top-p sampling")
    retry_attempts: int = Field(default=3, ge=1, description="Number of retry attempts")
    timeout: int = Field(default=25, ge=5, description="Request timeout in seconds (reduced for better UX)")


class MemoryConfig(BaseModel):
    """Memory system configuration."""
    episodic_limit: int = Field(default=10000, ge=1, description="Episodic memory limit")
    semantic_limit: int = Field(default=1000, ge=1, description="Semantic memory limit")
    skill_limit: int = Field(default=500, ge=1, description="Skill memory limit")
    embedding_model: str = Field(default="text-embedding-v1", description="Embedding model")
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Similarity threshold")


class AxiologyConfig(BaseModel):
    """Axiology (value system) configuration."""

    class ValueDimension(BaseModel):
        """Configuration for a single value dimension."""
        setpoint: float = Field(ge=0.0, le=1.0, description="Target satisfaction level")
        drift_limit_per_day: float = Field(ge=0.0, le=1.0, description="Maximum drift per day")
        weight_bias: float = Field(ge=0.0, description="Weight bias for this dimension")

    # Value dimensions
    homeostasis: ValueDimension = Field(description="Physical needs and well-being")
    integrity: ValueDimension = Field(description="Ethical consistency")
    attachment: ValueDimension = Field(description="Social bonds")
    contract: ValueDimension = Field(description="Commitment keeping")
    competence: ValueDimension = Field(description="Capability and mastery")
    curiosity: ValueDimension = Field(description="Knowledge seeking")
    meaning: ValueDimension = Field(description="Purpose and significance")
    efficiency: ValueDimension = Field(description="Resource optimization")

    # Weight dynamics
    tau: float = Field(default=4.0, ge=0.1, description="Temperature for softmax (论文 Appendix A.5: τ=4.0)")

    # Value learning
    learning_rate: float = Field(default=0.001, ge=0.0, le=1.0, description="Learning rate")
    enable_value_learning: bool = Field(default=True, description="Enable value learning")


class PersonalityConfig(BaseModel):
    """Personality configuration (Big Five traits)."""
    openness: float = Field(default=0.7, ge=0.0, le=1.0, description="Openness to experience")
    conscientiousness: float = Field(default=0.6, ge=0.0, le=1.0, description="Conscientiousness")
    extraversion: float = Field(default=0.5, ge=0.0, le=1.0, description="Extraversion")
    agreeableness: float = Field(default=0.6, ge=0.0, le=1.0, description="Agreeableness")
    neuroticism: float = Field(default=0.4, ge=0.0, le=1.0, description="Neuroticism")


class AffectConfig(BaseModel):
    """Affect and emotion configuration."""
    gamma: float = Field(default=0.95, ge=0.0, le=1.0, description="Discount factor")
    mood_k_plus: float = Field(default=0.1, ge=0.0, description="Positive RPE to mood")
    mood_k_minus: float = Field(default=0.15, ge=0.0, description="Negative RPE to mood")
    stress_s: float = Field(default=0.2, ge=0.0, description="Negative RPE to stress")
    stress_s_prime: float = Field(default=0.05, ge=0.0, description="Positive RPE to stress decrease")


class RuntimeConfig(BaseModel):
    """Runtime execution configuration."""
    tick_dt: float = Field(default=1.0, ge=0.1, description="Seconds per tick")
    max_ticks: int = Field(default=100000, ge=1, description="Maximum ticks per session")
    log_level: str = Field(default="INFO", description="Logging level")
    log_to_file: bool = Field(default=True, description="Enable file logging")
    log_dir: Path = Field(default=Path("artifacts/logs"), description="Log directory")
    safe_mode: bool = Field(default=False, description="Enable safe mode")
    phase_timeout: float = Field(default=30.0, ge=1.0, description="Phase timeout in seconds")


class SecurityConfig(BaseModel):
    """Security configuration."""
    jwt_secret: SecretStr = Field(description="JWT secret key")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration: int = Field(default=3600, ge=60, description="JWT expiration in seconds")
    enable_high_risk_tools: bool = Field(default=False, description="Enable high-risk tools")
    sandbox_code_exec: bool = Field(default=True, description="Sandbox code execution")
    allowed_domains: List[str] = Field(default=[], description="Allowed domains for API calls")


class GenesisXConfig(BaseSettings):
    """
    Main Genesis X configuration.

    This class combines all configuration sections and provides
    validation, environment variable support, and configuration loading.
    """

    # Meta configuration
    environment: Environment = Field(default=Environment.DEVELOPMENT, description="Current environment")
    config_dir: Path = Field(default=Path("config"), description="Configuration directory")
    artifacts_dir: Path = Field(default=Path("artifacts"), description="Artifacts directory")

    # Configuration sections
    database: Optional[DatabaseConfig] = None
    api: APIConfig = Field(default_factory=APIConfig)
    llm: Optional[LLMConfig] = None
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    axiology: Optional[AxiologyConfig] = None
    personality: PersonalityConfig = Field(default_factory=PersonalityConfig)
    affect: AffectConfig = Field(default_factory=AffectConfig)
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    security: Optional[SecurityConfig] = None

    # Custom configurations
    custom: Dict[str, Any] = Field(default_factory=dict, description="Custom configuration")

    # 修复：使用Pydantic v2的model_config替代class Config
    model_config = SettingsConfigDict(
        env_prefix="GENESISX_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    @field_validator('config_dir', 'artifacts_dir')
    @classmethod
    def ensure_directory_exists(cls, v: Path) -> Path:
        """Ensure directory exists."""
        v.mkdir(parents=True, exist_ok=True)
        return v


@dataclass
class ConfigSource:
    """Configuration source metadata."""
    source_type: str  # 'env', 'yaml', 'json', 'default'
    source_path: Optional[Path] = None
    loaded_at: datetime = None

    def __post_init__(self):
        if self.loaded_at is None:
            self.loaded_at = datetime.now(timezone.utc)


class ConfigManager:
    """
    Configuration manager with hot reload support.

    Features:
    - Load from multiple sources (env vars, YAML, JSON)
    - Environment-specific configurations
    - Type-safe validation with Pydantic
    - Hot reload for configuration files
    - Secret management
    - Configuration history and rollback

    Usage:
        manager = ConfigManager()
        config = manager.load()

        # Enable hot reload
        manager.enable_hot_reload(interval=30)

        # Access configuration
        print(config.llm.model)
    """

    def __init__(
        self,
        config_dir: Optional[Path] = None,
        environment: Optional[Environment] = None,
        env_file: Optional[Path] = None
    ):
        """
        Initialize configuration manager.

        Args:
            config_dir: Configuration directory path
            environment: Target environment (dev/staging/prod)
            env_file: Path to .env file
        """
        self.config_dir = config_dir or Path("config")
        self.environment = environment or self._detect_environment()
        self.env_file = env_file or Path(".env")

        self._config: Optional[GenesisXConfig] = None
        self._config_lock = Lock()
        self._sources: List[ConfigSource] = []
        self._hot_reload_enabled = False
        self._hot_reload_thread: Optional[Thread] = None
        self._last_reload_time: Optional[float] = None

        logger.info(f"ConfigManager initialized for environment: {self.environment}")

    def _detect_environment(self) -> Environment:
        """Detect environment from environment variables."""
        env_str = os.getenv("GENESISX_ENVIRONMENT", "development").lower()
        try:
            return Environment(env_str)
        except ValueError:
            logger.warning(f"Invalid environment '{env_str}', defaulting to development")
            return Environment.DEVELOPMENT

    def _load_env_file(self) -> Dict[str, str]:
        """Load environment variables from .env file."""
        env_vars = {}
        if self.env_file.exists():
            with open(self.env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        env_vars[key] = value
                        # Set in environment for Pydantic to pick up
                        if key not in os.environ:
                            os.environ[key] = value
            self._sources.append(ConfigSource('env', self.env_file))
            logger.debug(f"Loaded {len(env_vars)} variables from {self.env_file}")
        return env_vars

    def _load_yaml_file(self, filepath: Path) -> Dict[str, Any]:
        """Load YAML configuration file."""
        if not filepath.exists():
            return {}

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            self._sources.append(ConfigSource('yaml', filepath))
            logger.debug(f"Loaded YAML config from {filepath}")
            return data
        except Exception as e:
            logger.error(f"Error loading YAML from {filepath}: {e}")
            return {}

    def _load_json_file(self, filepath: Path) -> Dict[str, Any]:
        """Load JSON configuration file."""
        if not filepath.exists():
            return {}

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._sources.append(ConfigSource('json', filepath))
            logger.debug(f"Loaded JSON config from {filepath}")
            return data
        except Exception as e:
            logger.error(f"Error loading JSON from {filepath}: {e}")
            return {}

    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two configuration dictionaries."""
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    def load(self, force_reload: bool = False) -> GenesisXConfig:
        """
        Load configuration from all sources.

        Loading order (later sources override earlier ones):
        1. Default configuration (from Pydantic defaults)
        2. default.yaml
        3. {environment}.yaml (e.g., production.yaml)
        4. Environment variables
        5. .env file

        Args:
            force_reload: Force reload even if config is cached

        Returns:
            Validated GenesisXConfig instance
        """
        with self._config_lock:
            if self._config is not None and not force_reload:
                return self._config

            self._sources.clear()

            # Load .env file first to set environment variables
            self._load_env_file()

            # Start with empty config data
            config_data = {}

            # Load default.yaml
            default_config = self._load_yaml_file(self.config_dir / "default.yaml")
            config_data = self._merge_configs(config_data, default_config)

            # Load environment-specific config
            env_config = self._load_yaml_file(self.config_dir / f"{self.environment.value}.yaml")
            config_data = self._merge_configs(config_data, env_config)

            # Set environment explicitly
            config_data['environment'] = self.environment.value

            try:
                # Create and validate config
                self._config = GenesisXConfig(**config_data)
                self._last_reload_time = time.time()

                logger.info(
                    f"Configuration loaded successfully from {len(self._sources)} sources"
                )
                return self._config

            except ValidationError as e:
                logger.error(f"Configuration validation failed: {e}")
                raise

    def reload(self) -> GenesisXConfig:
        """Reload configuration from all sources."""
        logger.info("Reloading configuration...")
        return self.load(force_reload=True)

    def _hot_reload_worker(self, interval: int):
        """Background worker for hot reload."""
        while self._hot_reload_enabled:
            time.sleep(interval)
            try:
                self.reload()
            except Exception as e:
                logger.error(f"Hot reload failed: {e}")

    def enable_hot_reload(self, interval: int = 30):
        """
        Enable hot reload for configuration files.

        Args:
            interval: Reload interval in seconds
        """
        if self._hot_reload_enabled:
            logger.warning("Hot reload is already enabled")
            return

        self._hot_reload_enabled = True
        self._hot_reload_thread = Thread(
            target=self._hot_reload_worker,
            args=(interval,),
            daemon=True
        )
        self._hot_reload_thread.start()
        logger.info(f"Hot reload enabled with {interval}s interval")

    def disable_hot_reload(self):
        """Disable hot reload."""
        if not self._hot_reload_enabled:
            return

        self._hot_reload_enabled = False
        if self._hot_reload_thread:
            self._hot_reload_thread.join(timeout=5)
        logger.info("Hot reload disabled")

    def get_config(self) -> Optional[GenesisXConfig]:
        """Get current configuration without reloading."""
        return self._config

    def get_sources(self) -> List[ConfigSource]:
        """Get list of configuration sources."""
        return self._sources.copy()

    def validate_secrets(self) -> bool:
        """
        Validate that all required secrets are present.

        Returns:
            True if all secrets are valid, False otherwise
        """
        if not self._config:
            return False

        issues = []

        # Check LLM API key
        if self._config.llm and not self._config.llm.api_key.get_secret_value():
            issues.append("LLM API key is missing")

        # Check database URL
        if self._config.database and not self._config.database.url.get_secret_value():
            issues.append("Database URL is missing")

        # Check JWT secret
        if self._config.security and not self._config.security.jwt_secret.get_secret_value():
            issues.append("JWT secret is missing")

        if issues:
            logger.error(f"Secret validation failed: {', '.join(issues)}")
            return False

        logger.info("All secrets validated successfully")
        return True

    def export_config(self, output_path: Path, include_secrets: bool = False):
        """
        Export current configuration to YAML file.

        Args:
            output_path: Output file path
            include_secrets: Include secret values (USE WITH CAUTION)
        """
        if not self._config:
            raise ValueError("No configuration loaded")

        # 修复：使用Pydantic v2的model_dump()替代dict()
        config_dict = self._config.model_dump()

        if not include_secrets:
            # Mask secret values
            def mask_secrets(d, key=""):
                if isinstance(d, dict):
                    return {k: mask_secrets(v, k) for k, v in d.items()}
                elif isinstance(d, SecretStr):
                    return "***MASKED***"
                elif isinstance(d, str) and any(s in key.lower() for s in ['secret', 'password', 'key', 'token']):
                    return "***MASKED***"
                return d

            config_dict = mask_secrets(config_dict)

        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Configuration exported to {output_path}")


# Singleton instance for easy access
_global_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get global configuration manager instance."""
    global _global_manager
    if _global_manager is None:
        _global_manager = ConfigManager()
    return _global_manager


def load_config() -> GenesisXConfig:
    """Load configuration using global manager."""
    manager = get_config_manager()
    return manager.load()
