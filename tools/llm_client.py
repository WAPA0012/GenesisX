"""LLM Client - 统一的大语言模型接口.

支持多个 LLM 提供商：
- OpenAI (GPT-4, GPT-3.5)
- Anthropic Claude (Claude 3.5, Claude 3 Opus)
- 通义千问 (Qwen)
- DeepSeek
- 智谱 GLM (GLM-5, GLM-4)
- 百度文心 (ERNIE)
- 腾讯混元 (Hunyuan)
- 月之暗面 (Kimi)
- 零一万物 (Yi)
- 本地模型 (Ollama, vLLM, LM Studio)

论文 Section 3.4.2: Mind Field 的 LLM 接口实现
"""

import os
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
import json
from pathlib import Path


@dataclass
class LLMConfig:
    """LLM 配置."""
    api_base: str
    api_key: str
    model: str
    temperature: float = 0.7
    max_tokens: int = 2000
    timeout: int = 60  # 增加到 60 秒以适应 GLM API 的波动
    # provider: openai, claude, qianwen, deepseek, glm, ernie, hunyuan, kimi, yi, local
    provider: str = "openai"
    # API 版本 (用于 Claude)
    version: str = "2023-06-01"


class LLMClient:
    """统一的 LLM 客户端接口.

    论文 Section 3.4.2: M_coord (调度模型) 的 LLM 调用接口
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化 LLM 客户端.

        Args:
            config: 配置字典，包含 api_base, api_key, model 等
        """
        self.config = self._load_config(config)
        self._validate_config()

    def _load_config(self, config: Optional[Dict[str, Any]]) -> LLMConfig:
        """加载配置，优先从环境变量读取.

        Args:
            config: 提供的配置字典

        Returns:
            LLMConfig 实例
        """
        # 环境变量优先
        env_api_base = os.getenv("LLM_API_BASE", "")
        env_api_key = os.getenv("LLM_API_KEY", "")
        env_model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")

        api_base = (config.get("api_base") if config else None) or env_api_base
        api_key = (config.get("api_key") if config else None) or env_api_key
        model = (config.get("model") if config else None) or env_model
        # 注意: temperature 可能是 0（有效值），所以需要显式检查 None
        temperature = config.get("temperature") if config and "temperature" in config else 0.7
        max_tokens = config.get("max_tokens") if config and "max_tokens" in config else 2000

        # 调试日志 (安全: 不输出敏感信息)
        from common.logger import get_logger
        logger = get_logger(__name__)
        # 安全地记录API base，隐藏敏感路径
        safe_api_base = api_base[:50] + "..." if len(api_base) > 50 else api_base
        logger.info(f"[LLMClient._load_config] using api_base={safe_api_base}")
        logger.info(f"[LLMClient._load_config] using model={model}")
        # 安全地记录API key状态（只显示是否存在，不显示内容）
        has_key = bool(api_key)
        key_preview = api_key[:4] + "****" + api_key[-4:] if api_key and len(api_key) > 8 else ("****" if api_key else "None")
        logger.info(f"[LLMClient._load_config] api_key configured={has_key}, preview={key_preview}")

        # 自动检测提供商
        # IMPORTANT: 检测顺序很重要！
        # 智谱的 Anthropic 兼容接口 (bigmodel.cn/api/anthropic) 需要使用 claude provider
        # 因为它需要 Anthropic 格式的 API 调用和工具定义
        provider = "openai"
        api_lower = api_base.lower()

        # 首先检查是否是 Anthropic 兼容接口（包括智谱的 /api/anthropic）
        if "/api/anthropic" in api_base or api_lower.endswith("/anthropic"):
            # 智谱或其他第三方 Anthropic 兼容接口
            provider = "claude"
        elif "anthropic.com" in api_lower or "claude" in api_lower:
            provider = "claude"
        elif "dashscope" in api_base or "qianwen" in api_lower:
            provider = "qianwen"
        elif "deepseek" in api_lower:
            provider = "deepseek"
        elif "zhipu" in api_lower or ("bigmodel" in api_lower and "/api/anthropic" not in api_base):
            # 智谱 OpenAI 兼容接口 (不是 /api/anthropic 端点)
            provider = "glm"
        elif "ernie" in api_lower or "baidu" in api_lower or "aip" in api_lower:
            provider = "ernie"  # 百度文心
        elif "hunyuan" in api_lower or "tencent" in api_lower:
            provider = "hunyuan"  # 腾讯混元
        elif "moonshot" in api_lower or "kimi" in api_lower:
            provider = "kimi"  # 月之暗面 Kimi
        elif "lingyi" in api_lower or "01" in api_lower or "yi-" in api_lower:
            provider = "yi"  # 零一万物
        elif "localhost" in api_base or "127.0.0.1" in api_base or "ollama" in api_lower:
            provider = "local"

        return LLMConfig(
            api_base=api_base,
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            provider=provider
        )

    def _validate_config(self):
        """验证配置是否完整."""
        if not self.config.api_base:
            raise ValueError("LLM_API_BASE 未配置")
        if not self.config.api_key and self.config.provider != "local":
            raise ValueError("LLM_API_KEY 未配置")

    def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """发送聊天请求.

        论文 Section 3.4.2: Mind Field 的核心 LLM 调用接口

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            system_prompt: 系统提示词
            temperature: 温度参数
            max_tokens: 最大生成 token 数
            tools: 工具定义列表 (用于 Function Calling)
            **kwargs: 其他参数

        Returns:
            响应字典，包含 "ok", "text", "tool_calls", "total_tokens" 等字段
        """
        # 构建完整消息列表
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        # 使用默认参数
        temperature = temperature if temperature is not None else self.config.temperature
        max_tokens = max_tokens if max_tokens is not None else self.config.max_tokens

        # 根据提供商调用不同实现
        try:
            if self.config.provider == "claude":
                return self._chat_claude(full_messages, temperature, max_tokens, tools)
            elif self.config.provider == "qianwen":
                return self._chat_qianwen(full_messages, temperature, max_tokens, tools)
            elif self.config.provider in ("glm", "ernie", "hunyuan", "kimi", "yi"):
                # 这些都使用 OpenAI 兼容格式
                return self._chat_openai_compatible(full_messages, temperature, max_tokens, tools)
            elif self.config.provider == "deepseek":
                return self._chat_openai_compatible(full_messages, temperature, max_tokens, tools)
            elif self.config.provider == "local":
                return self._chat_openai_compatible(full_messages, temperature, max_tokens, tools)
            else:
                return self._chat_openai_compatible(full_messages, temperature, max_tokens, tools)
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "text": "",
                "tool_calls": [],
                "total_tokens": 0
            }

    def _chat_openai_compatible(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        tools: Optional[List[Dict]]
    ) -> Dict[str, Any]:
        """OpenAI 兼容接口调用.

        支持 OpenAI, DeepSeek, 本地模型等
        """
        try:
            import requests
        except ImportError:
            return {
                "ok": False,
                "error": "requests 模块未安装",
                "text": "",
                "tool_calls": [],
                "total_tokens": 0
            }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}"
        }

        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # 添加工具定义 (Function Calling)
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            url = f"{self.config.api_base.rstrip('/')}/chat/completions"
            # 调试日志
            from common.logger import get_logger
            logger = get_logger(__name__)
            logger.info(f"[LLMClient] Calling API: {url}")
            logger.info(f"[LLMClient] Model: {self.config.model}")

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.config.timeout
            )
            response.raise_for_status()

            data = response.json()

            # 解析响应
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})

            # 提取文本（GLM-5 等模型可能使用 reasoning_content）
            text = message.get("content", "")
            if not text:
                # GLM-5 可能返回 reasoning_content 而不是 content
                text = message.get("reasoning_content", "")

            # 提取工具调用
            tool_calls = []
            if "tool_calls" in message:
                for tc in message["tool_calls"]:
                    function = tc.get("function", {})
                    tool_calls.append({
                        "id": tc.get("id", ""),
                        "type": "function",
                        "function": {
                            "name": function.get("name", ""),
                            "arguments": function.get("arguments", "{}")
                        }
                    })

            return {
                "ok": True,
                "text": text or "",
                "tool_calls": tool_calls,
                "total_tokens": data.get("usage", {}).get("total_tokens", 0)
            }

        except requests.RequestException as e:
            return {
                "ok": False,
                "error": f"请求失败: {str(e)}",
                "text": "",
                "tool_calls": [],
                "total_tokens": 0
            }

    def _chat_qianwen(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        tools: Optional[List[Dict]]
    ) -> Dict[str, Any]:
        """通义千问专用接口.

        使用 dashscope SDK
        """
        try:
            import dashscope
            # 设置 API key
            dashscope.api_key = self.config.api_key
        except ImportError:
            # 降级到 HTTP 调用
            return self._chat_openai_compatible(messages, temperature, max_tokens, tools)

        try:
            from dashscope import Generation

            # 构建参数
            generation_params = {
                "model": self.config.model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "result_format": "message"
            }

            # 添加工具定义 (通义千问 Function Calling)
            if tools:
                generation_params["tools"] = tools

            # 调用 API
            response = Generation.call(
                messages=messages,
                **generation_params
            )

            if response.status_code != 200:
                return {
                    "ok": False,
                    "error": f"API 错误: {response.message}",
                    "text": "",
                    "tool_calls": [],
                    "total_tokens": 0
                }

            # 解析响应
            output = response.output
            choices = output.get("choices", [])
            if not choices:
                return {
                    "ok": True,
                    "text": "",
                    "tool_calls": [],
                    "total_tokens": response.usage.get("total_tokens", 0)
                }

            message = choices[0].get("message", {})
            text = message.get("content", "")

            # 工具调用 (通义千问使用不同格式)
            tool_calls = []
            if "tool_calls" in message:
                for tc in message["tool_calls"]:
                    tool_calls.append({
                        "id": tc.get("id", ""),
                        "type": "function",
                        "function": {
                            "name": tc.get("function", {}).get("name", ""),
                            "arguments": tc.get("function", {}).get("arguments", "{}")
                        }
                    })

            return {
                "ok": True,
                "text": text,
                "tool_calls": tool_calls,
                "total_tokens": response.usage.get("total_tokens", 0)
            }

        except Exception as e:
            return {
                "ok": False,
                "error": f"调用失败: {str(e)}",
                "text": "",
                "tool_calls": [],
                "total_tokens": 0
            }

    def _chat_claude(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        tools: Optional[List[Dict]]
    ) -> Dict[str, Any]:
        """Anthropic Claude 兼容接口.

        支持真正的 Anthropic API 和智谱的 Anthropic 兼容接口
        """
        # 优先使用 anthropic 库
        try:
            import anthropic
            has_anthropic = True
        except ImportError:
            has_anthropic = False

        if has_anthropic:
            try:
                # 智谱的 Anthropic 兼容接口需要自定义 base_url
                client = anthropic.Anthropic(
                    api_key=self.config.api_key,
                    base_url=self.config.api_base
                )

                # 构建参数
                params = {
                    "model": self.config.model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                }

                # 处理 system 消息
                system_message = None
                filtered_messages = []
                for msg in messages:
                    if msg["role"] == "system":
                        system_message = msg["content"]
                    else:
                        filtered_messages.append(msg)

                if system_message:
                    params["system"] = system_message

                # 添加工具（Claude 使用不同的工具格式）
                if tools:
                    # 转换 OpenAI 格式到 Claude 格式
                    claude_tools = []
                    for tool in tools:
                        function = tool.get("function", {})
                        claude_tools.append({
                            "name": function.get("name", ""),
                            "description": function.get("description", ""),
                            "input_schema": json.loads(function.get("parameters", "{}"))
                        })
                    params["tools"] = claude_tools

                # 调用 API
                response = client.messages.create(**params, messages=filtered_messages)

                # 解析响应
                text = ""
                tool_calls = []

                for block in response.content:
                    if block.type == "text":
                        text += block.text
                    elif block.type == "tool_use":
                        tool_calls.append({
                            "id": block.id,
                            "type": "function",
                            "function": {
                                "name": block.name,
                                "arguments": json.dumps(block.input)
                            }
                        })

                return {
                    "ok": True,
                    "text": text,
                    "tool_calls": tool_calls,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                }

            except Exception as e:
                # 如果 anthropic 库调用失败，降级到 requests
                logger.warning(f"Anthropic library call failed: {e}, falling back to requests")

        # 使用 requests 直接调用 Anthropic 兼容接口（智谱）
        try:
            import requests
        except ImportError:
            return {
                "ok": False,
                "error": "requests 模块未安装",
                "text": "",
                "tool_calls": [],
                "total_tokens": 0
            }

        # 处理 system 消息
        system_message = None
        filtered_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                filtered_messages.append(msg)

        # 构建 Anthropic API 格式的请求
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01"
        }

        # 转换 OpenAI 格式的工具结果消息为 Anthropic 格式
        # OpenAI: {"role": "tool", "tool_call_id": "xxx", "content": "..."}
        # Anthropic: {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "xxx", "content": "..."}]}
        anthropic_messages = []
        for msg in filtered_messages:
            if msg.get("role") == "tool":
                # 转换工具结果消息
                anthropic_messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg.get("tool_call_id", ""),
                        "content": msg.get("content", "")
                    }]
                })
            elif msg.get("role") == "assistant" and "tool_calls" in msg:
                # 转换带工具调用的助手消息
                content = []
                if msg.get("content"):
                    content.append({"type": "text", "text": msg["content"]})
                for tc in msg.get("tool_calls", []):
                    func = tc.get("function", {})
                    content.append({
                        "type": "tool_use",
                        "id": tc.get("id", ""),
                        "name": func.get("name", ""),
                        "input": json.loads(func.get("arguments", "{}")) if isinstance(func.get("arguments"), str) else func.get("arguments", {})
                    })
                anthropic_messages.append({"role": "assistant", "content": content})
            else:
                anthropic_messages.append(msg)

        payload = {
            "model": self.config.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": anthropic_messages
        }

        if system_message:
            payload["system"] = system_message

        if tools:
            # 转换 OpenAI 格式到 Claude 格式
            claude_tools = []
            for tool in tools:
                function = tool.get("function", {})
                params = function.get("parameters", "{}")
                # parameters 可能已经是 dict，如果是就解析
                if isinstance(params, str):
                    input_schema = json.loads(params)
                else:
                    input_schema = params
                claude_tools.append({
                    "name": function.get("name", ""),
                    "description": function.get("description", ""),
                    "input_schema": input_schema
                })
            payload["tools"] = claude_tools

        try:
            # 智谱 Anthropic 兼容接口的 URL 是 /api/anthropic
            # 正确的端点是 /api/anthropic/v1/messages
            base = self.config.api_base.rstrip('/')
            # 统一使用 /v1/messages 端点
            url = f"{base}/v1/messages"
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.config.timeout
            )
            response.raise_for_status()

            data = response.json()

            # 解析 Anthropic 格式的响应
            text = ""
            tool_calls = []

            for block in data.get("content", []):
                if block.get("type") == "text":
                    text += block.get("text", "")
                elif block.get("type") == "tool_use":
                    tool_calls.append({
                        "id": block.get("id", ""),
                        "type": "function",
                        "function": {
                            "name": block.get("name", ""),
                            "arguments": json.dumps(block.get("input", {}))
                        }
                    })

            usage = data.get("usage", {})
            return {
                "ok": True,
                "text": text,
                "tool_calls": tool_calls,
                "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
            }

        except requests.RequestException as e:
            return {
                "ok": False,
                "error": f"Anthropic API 请求失败: {str(e)}",
                "text": "",
                "tool_calls": [],
                "total_tokens": 0
            }

        except Exception as e:
            return {
                "ok": False,
                "error": f"Claude 调用失败: {str(e)}",
                "text": "",
                "tool_calls": [],
                "total_tokens": 0
            }

    def embed(self, texts: List[str]) -> List[List[float]]:
        """获取文本嵌入向量.

        论文 Section 3.4.3: 用于熟悉度信号计算

        Args:
            texts: 待编码的文本列表

        Returns:
            嵌入向量列表
        """
        try:
            import requests
        except ImportError:
            raise RuntimeError("requests 模块未安装")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}"
        }

        embeddings = []
        for text in texts:
            payload = {
                "model": self.config.model,
                "input": text
            }

            response = requests.post(
                f"{self.config.api_base.rstrip('/')}/embeddings",
                headers=headers,
                json=payload,
                timeout=self.config.timeout
            )
            response.raise_for_status()

            data = response.json()
            embedding = data.get("data", [{}])[0].get("embedding", [])
            embeddings.append(embedding)

        return embeddings


def create_llm_from_env() -> Optional[LLMClient]:
    """从环境变量创建 LLM 客户端.

    论文 Section 3.4.2: 标准的 LLM 初始化方法

    Returns:
        LLMClient 实例，如果配置不全则返回 None
    """
    api_base = os.getenv("LLM_API_BASE", "")
    api_key = os.getenv("LLM_API_KEY", "")

    if not api_base:
        return None

    return LLMClient({
        "api_base": api_base,
        "api_key": api_key,
        "model": os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    })


# 便捷函数
def chat(
    prompt: str,
    system_prompt: Optional[str] = None,
    **kwargs
) -> str:
    """简单的聊天接口.

    Args:
        prompt: 用户消息
        system_prompt: 系统提示词
        **kwargs: 其他参数

    Returns:
        LLM 响应文本
    """
    client = create_llm_from_env()
    if client is None:
        return "错误: LLM 未配置"

    messages = [{"role": "user", "content": prompt}]
    result = client.chat(messages, system_prompt, **kwargs)

    if result.get("ok"):
        return result.get("text", "")
    else:
        return f"错误: {result.get('error', '未知错误')}"
