"""Universal LLM API wrapper for Genesis X.

Provides unified interface for multiple LLM providers.
"""

import os
import json
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import requests


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
    QIANWEN = "qianwen"
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"
    CUSTOM = "custom"


class LLMErrorType(str, Enum):
    """LLM error types for better error handling."""
    NETWORK = "network"           # Network connectivity issues
    TIMEOUT = "timeout"           # Request timeout
    API_ERROR = "api_error"       # API returned error
    AUTH_ERROR = "auth_error"     # Authentication/authorization error
    RATE_LIMIT = "rate_limit"     # Rate limiting
    INVALID_RESPONSE = "invalid_response"  # Cannot parse response
    UNKNOWN = "unknown"           # Unknown error


@dataclass
class LLMConfig:
    """LLM configuration.

    Attributes:
        api_base: API base URL
        api_key: API key
        model: Model name
        provider: Provider enum
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate
        timeout: Request timeout in seconds (default 20, reduced for better UX)
    """
    model: str
    api_base: str = ""
    api_key: str = ""
    provider: LLMProvider = LLMProvider.CUSTOM
    temperature: float = 0.7
    max_tokens: int = 2000
    timeout: int = 20  # 降低默认超时，提升用户体验


class UniversalLLM:
    """Universal LLM client supporting multiple providers.

    Provides a unified interface for:
    - OpenAI-compatible APIs (OpenAI, DeepSeek, etc.)
    - Anthropic Claude
    - Local models (Ollama)
    - Custom OpenAI-compatible endpoints
    """

    DEFAULT_PRESETS = {
        "gpt-4": LLMConfig(
            api_base="https://api.openai.com/v1",
            model="gpt-4",
            provider=LLMProvider.OPENAI,
        ),
        "gpt-3.5-turbo": LLMConfig(
            api_base="https://api.openai.com/v1",
            model="gpt-3.5-turbo",
            provider=LLMProvider.OPENAI,
        ),
        "claude-3-sonnet": LLMConfig(
            api_base="https://api.anthropic.com/v1",
            model="claude-3-sonnet-20240229",
            provider=LLMProvider.ANTHROPIC,
        ),
        "deepseek-chat": LLMConfig(
            api_base="https://api.deepseek.com/v1",
            model="deepseek-chat",
            provider=LLMProvider.DEEPSEEK,
        ),
        "qwen-plus": LLMConfig(
            api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
            model="qwen-plus",
            provider=LLMProvider.QIANWEN,
        ),
        "ollama": LLMConfig(
            api_base="http://localhost:11434/v1",
            model="llama3",
            provider=LLMProvider.OLLAMA,
        ),
    }

    def __init__(self, config: LLMConfig):
        """Initialize LLM client.

        Args:
            config: LLM configuration
        """
        self.config = config

    def chat(self, messages: List[Dict[str, str]], tools: List[Dict] = None, **kwargs) -> Dict[str, Any]:
        """Send chat request to LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: Optional list of tool definitions for function calling
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            Response dict with 'ok', 'text', 'tool_calls', 'usage', etc.
        """
        temperature = kwargs.get("temperature", self.config.temperature)
        max_tokens = kwargs.get("max_tokens", self.config.max_tokens)

        try:
            # Build headers based on provider
            headers = self._build_headers()

            # Build request body based on provider
            payload = self._build_payload(messages, temperature, max_tokens, tools=tools)

            # Make request
            url = self._get_endpoint()
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.config.timeout,
            )

            if response.status_code == 200:
                return self._parse_response(response)
            else:
                # 修复: 更详细的错误分类
                return self._handle_error_response(response)

        except requests.exceptions.Timeout as e:
            return {
                "ok": False,
                "error": f"Request timeout after {self.config.timeout}s",
                "error_type": LLMErrorType.TIMEOUT,
            }
        except requests.exceptions.ConnectionError as e:
            return {
                "ok": False,
                "error": f"Network connection error: {str(e)}",
                "error_type": LLMErrorType.NETWORK,
            }
        except requests.exceptions.RequestException as e:
            return {
                "ok": False,
                "error": f"Request failed: {str(e)}",
                "error_type": LLMErrorType.NETWORK,
            }
        except (KeyError, IndexError, ValueError) as e:
            return {
                "ok": False,
                "error": f"Failed to parse response: {str(e)}",
                "error_type": LLMErrorType.INVALID_RESPONSE,
            }
        except Exception as e:
            return {
                "ok": False,
                "error": f"Unexpected error: {str(e)}",
                "error_type": LLMErrorType.UNKNOWN,
            }

    def _build_headers(self) -> Dict[str, str]:
        """Build request headers based on provider."""
        headers = {"Content-Type": "application/json"}

        if self.config.provider == LLMProvider.ANTHROPIC:
            headers["x-api-key"] = self.config.api_key
            headers["anthropic-version"] = "2023-06-01"
        else:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        return headers

    def _handle_error_response(self, response) -> Dict[str, Any]:
        """Handle non-200 responses with detailed error classification.

        Args:
            response: requests.Response object

        Returns:
            Error response dict with error type
        """
        status = response.status_code
        text = response.text

        # Classify error by status code
        if status == 401 or status == 403:
            error_type = LLMErrorType.AUTH_ERROR
            error_msg = f"Authentication failed (HTTP {status})"
        elif status == 429:
            error_type = LLMErrorType.RATE_LIMIT
            error_msg = f"Rate limit exceeded (HTTP {status})"
        elif status >= 500:
            error_type = LLMErrorType.API_ERROR
            error_msg = f"API server error (HTTP {status})"
        elif status >= 400:
            error_type = LLMErrorType.API_ERROR
            error_msg = f"Client error (HTTP {status}): {text[:200]}"
        else:
            error_type = LLMErrorType.UNKNOWN
            error_msg = f"Unexpected status (HTTP {status}): {text[:200]}"

        return {
            "ok": False,
            "error": error_msg,
            "error_type": error_type,
            "status_code": status,
        }

    def _convert_tools_to_anthropic(self, tools: List[Dict]) -> List[Dict]:
        """Convert OpenAI-format tools to Anthropic format.

        OpenAI format:
        [{"type": "function", "function": {"name": "...", "description": "...", "parameters": {...}}}]

        Anthropic format:
        [{"name": "...", "description": "...", "input_schema": {...}}]
        """
        anthropic_tools = []
        for tool in tools:
            # Check if already in Anthropic format
            if "name" in tool and "input_schema" in tool:
                anthropic_tools.append(tool)
                continue

            # Convert from OpenAI format
            if "function" in tool:
                func = tool["function"]
                params = func.get("parameters", {})
                # Ensure parameters is a dict
                if isinstance(params, str):
                    params = json.loads(params)

                anthropic_tools.append({
                    "name": func.get("name", ""),
                    "description": func.get("description", ""),
                    "input_schema": params
                })
            else:
                # Unknown format, pass through
                anthropic_tools.append(tool)

        return anthropic_tools

    def _build_payload(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        tools: List[Dict] = None,
    ) -> Dict[str, Any]:
        """Build request payload based on provider."""
        if self.config.provider == LLMProvider.ANTHROPIC:
            # Anthropic format
            payload = {
                "model": self.config.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if tools:
                # Convert OpenAI-format tools to Anthropic format
                payload["tools"] = self._convert_tools_to_anthropic(tools)
            return payload
        else:
            # OpenAI-compatible format
            payload = {
                "model": self.config.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if tools:
                payload["tools"] = tools
            return payload

    def _get_endpoint(self) -> str:
        """Get API endpoint for provider."""
        base = self.config.api_base.rstrip("/")

        if self.config.provider == LLMProvider.ANTHROPIC:
            return f"{base}/v1/messages"
        else:
            return f"{base}/chat/completions"

    def _parse_response(self, response) -> Dict[str, Any]:
        """Parse LLM response based on provider."""
        data = response.json()

        if self.config.provider == LLMProvider.ANTHROPIC:
            result = {
                "ok": True,
                "usage": data.get("usage", {}),
                "model": self.config.model,
            }
            # Parse all content blocks (Anthropic can return mixed text + tool_use)
            text_parts = []
            tool_calls = []
            if "content" in data and data["content"]:
                for content_block in data["content"]:
                    block_type = content_block.get("type", "")
                    if block_type == "tool_use":
                        tool_calls.append(content_block)
                    elif block_type == "text" or "text" in content_block:
                        text_parts.append(content_block.get("text", ""))
            result["text"] = "".join(text_parts)
            result["tool_calls"] = tool_calls if tool_calls else None
            return result
        else:
            # OpenAI-compatible format
            choices = data.get("choices", [])
            if not choices:
                return {
                    "ok": False,
                    "error": "No choices in response",
                    "text": "",
                    "usage": data.get("usage", {}),
                    "model": self.config.model,
                }
            choice = choices[0]
            message = choice.get("message", {})
            result = {
                "ok": True,
                "text": message.get("content", ""),
                "usage": data.get("usage", {}),
                "model": self.config.model,
            }
            # Check for tool_calls
            if "tool_calls" in message and message["tool_calls"]:
                result["tool_calls"] = message["tool_calls"]
            else:
                result["tool_calls"] = None
            return result

    def chat_stream(self, messages: List[Dict[str, str]], **kwargs):
        """Stream chat response from LLM (yields chunks).

        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Yields:
            Text chunks as they arrive
        """
        temperature = kwargs.get("temperature", self.config.temperature)
        max_tokens = kwargs.get("max_tokens", self.config.max_tokens)

        try:
            headers = self._build_headers()
            payload = self._build_payload(messages, temperature, max_tokens)
            payload["stream"] = True  # Enable streaming

            url = self._get_endpoint()
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.config.timeout,
                stream=True,
            )

            if response.status_code != 200:
                # 修复: 更详细的流式错误处理
                error_info = self._handle_error_response(response)
                yield f"[Error: {error_info['error']}]"
                return

            # Parse SSE stream
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data_str = line[6:]
                        if data_str.strip() == '[DONE]':
                            break
                        try:
                            import json
                            data = json.loads(data_str)
                            if self.config.provider == LLMProvider.ANTHROPIC:
                                # Anthropic 流式响应格式:
                                # {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "..."}}
                                if data.get("type") == "content_block_delta":
                                    delta = data.get("delta", {})
                                    if delta.get("type") == "text_delta" and "text" in delta:
                                        yield delta["text"]
                                # 兼容旧格式 (某些代理可能使用简化的格式)
                                elif 'delta' in data and 'text' in data['delta']:
                                    yield data['delta']['text']
                            else:
                                # OpenAI-compatible format
                                if 'choices' in data and len(data['choices']) > 0:
                                    delta = data['choices'][0].get('delta', {})
                                    if 'content' in delta:
                                        yield delta['content']
                        except json.JSONDecodeError:
                            continue

        except requests.exceptions.Timeout:
            yield f"[Error: Request timeout after {self.config.timeout}s]"
        except requests.exceptions.ConnectionError as e:
            yield f"[Error: Network connection error - {str(e)[:100]}]"
        except requests.exceptions.RequestException as e:
            yield f"[Error: Request failed - {str(e)[:100]}]"
        except Exception as e:
            yield f"[Error: Unexpected error - {str(e)[:100]}]"

    @classmethod
    def from_preset(cls, preset: str) -> "UniversalLLM":
        """Create LLM from preset name.

        Args:
            preset: Preset name (gpt-4, deepseek-chat, etc.)

        Returns:
            UniversalLLM instance

        Raises:
            ValueError: If preset not found
        """
        if preset not in cls.DEFAULT_PRESETS:
            raise ValueError(
                f"Unknown preset: {preset}. "
                f"Available: {list(cls.DEFAULT_PRESETS.keys())}"
            )

        import copy
        config = copy.copy(cls.DEFAULT_PRESETS[preset])
        config.api_key = os.getenv("LLM_API_KEY", "")
        return cls(config)

    @classmethod
    def from_env(cls, api_base: Optional[str] = None) -> "UniversalLLM":
        """Create LLM from environment variables.

        Environment variables:
            LLM_API_BASE: API base URL
            LLM_API_KEY: API key
            LLM_MODEL: Model name
            LLM_TEMPERATURE: Temperature (optional)
            LLM_MAX_TOKENS: Max tokens (optional)

        Returns:
            UniversalLLM instance

        Raises:
            ValueError: If required environment variables are missing
        """
        api_base = api_base or os.getenv("LLM_API_BASE")
        api_key = os.getenv("LLM_API_KEY", "")
        model = os.getenv("LLM_MODEL", "")
        temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        max_tokens = int(os.getenv("LLM_MAX_TOKENS", "2000"))

        if not api_base:
            raise ValueError("LLM_API_BASE environment variable not set")
        if not model:
            raise ValueError("LLM_MODEL environment variable not set")

        # Detect provider from api_base
        # IMPORTANT: Check for Anthropic-compatible endpoints first (e.g., bigmodel.cn/api/anthropic)
        # because they need special handling for tool format conversion
        provider = LLMProvider.CUSTOM
        if "anthropic.com" in api_base:
            provider = LLMProvider.ANTHROPIC
        elif "/api/anthropic" in api_base or "anthropic" in api_base.lower():
            # 智谱等第三方 Anthropic 兼容接口 (如 bigmodel.cn/api/anthropic)
            # 需要使用 Anthropic 格式，包括工具定义格式
            provider = LLMProvider.ANTHROPIC
        elif "openai.com" in api_base:
            provider = LLMProvider.OPENAI
        elif "deepseek" in api_base:
            provider = LLMProvider.DEEPSEEK
        elif "dashscope" in api_base:
            provider = LLMProvider.QIANWEN
        elif "localhost" in api_base or "127.0.0.1" in api_base:
            provider = LLMProvider.OLLAMA
        elif "openrouter" in api_base:
            provider = LLMProvider.OPENROUTER

        config = LLMConfig(
            api_base=api_base,
            api_key=api_key,
            model=model,
            provider=provider,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return cls(config)


def create_llm_from_preset(preset: str = "gpt-3.5-turbo") -> UniversalLLM:
    """Create LLM from preset name.

    Args:
        preset: Preset name

    Returns:
        UniversalLLM instance
    """
    return UniversalLLM.from_preset(preset)


def create_llm_from_env(api_base: Optional[str] = None) -> Union[UniversalLLM, "LLMAPIClient"]:
    """Create LLM client from environment variables.

    This function provides backward compatibility with chat_interactive.py
    which expects a simple client with a chat() method.

    Args:
        api_base: Optional API base URL override

    Returns:
        UniversalLLM instance

    Raises:
        ValueError: If required environment variables are missing
    """
    return UniversalLLM.from_env(api_base)


# Backward compatibility alias
LLMAPIClient = UniversalLLM
