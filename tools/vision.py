"""
Vision Module - 视觉感知能力

提供数字生命的视觉感知能力，包括：
- analyze_image: 看图理解，使用多模态LLM分析图像内容
- image_to_text: OCR文字识别，提取图像中的文本

支持多种视觉模型：
- Claude 3.5/4 (claude-opus-4-6)
- GPT-4 Vision (gpt-4-vision-preview)
- Qwen VL (qwen-vl-max)
- 本地模型 (通过 Ollama)
"""

import os
import base64
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import requests
from io import BytesIO

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class VisionErrorType:
    """视觉处理错误类型"""
    NETWORK = "network"
    TIMEOUT = "timeout"
    INVALID_IMAGE = "invalid_image"
    API_ERROR = "api_error"
    AUTH_ERROR = "auth_error"
    MODEL_NOT_SUPPORTED = "model_not_supported"
    UNKNOWN = "unknown"


class VisionCapability:
    """视觉能力类型"""
    ANALYZE = "analyze"      # 图像理解/分析
    OCR = "ocr"              # 文字提取
    DESCRIBE = "describe"    # 图像描述
    DETECT = "detect"        # 物体检测


class VisionModel:
    """支持的视觉模型"""
    CLAUDE_OPUS = "claude-opus-4-6"
    CLAUDE_SONNET = "claude-3-5-sonnet"
    GPT4_VISION = "gpt-4-vision-preview"
    GPT4O = "gpt-4o"
    QWEN_VL_MAX = "qwen-vl-max"
    QWEN_VL_PLUS = "qwen-vl-plus"
    LLAVA = "llava"  # 本地模型


class VisionClient:
    """统一视觉感知客户端"""

    # 模型配置
    MODEL_CONFIGS = {
        VisionModel.CLAUDE_OPUS: {
            "api_base": "https://api.anthropic.com/v1",
            "provider": "anthropic",
            "supports": [VisionCapability.ANALYZE, VisionCapability.OCR, VisionCapability.DESCRIBE],
        },
        VisionModel.CLAUDE_SONNET: {
            "api_base": "https://api.anthropic.com/v1",
            "provider": "anthropic",
            "supports": [VisionCapability.ANALYZE, VisionCapability.OCR, VisionCapability.DESCRIBE],
        },
        VisionModel.GPT4_VISION: {
            "api_base": "https://api.openai.com/v1",
            "provider": "openai",
            "supports": [VisionCapability.ANALYZE, VisionCapability.OCR, VisionCapability.DESCRIBE],
        },
        VisionModel.GPT4O: {
            "api_base": "https://api.openai.com/v1",
            "provider": "openai",
            "supports": [VisionCapability.ANALYZE, VisionCapability.OCR, VisionCapability.DESCRIBE],
        },
        VisionModel.QWEN_VL_MAX: {
            "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "provider": "qwen",
            "supports": [VisionCapability.ANALYZE, VisionCapability.OCR, VisionCapability.DESCRIBE],
        },
        VisionModel.QWEN_VL_PLUS: {
            "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "provider": "qwen",
            "supports": [VisionCapability.ANALYZE, VisionCapability.OCR, VisionCapability.DESCRIBE],
        },
    }

    def __init__(
        self,
        model: str = VisionModel.CLAUDE_SONNET,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        timeout: int = 30,
    ):
        """初始化视觉客户端

        Args:
            model: 视觉模型名称
            api_key: API密钥（默认从环境变量读取）
            api_base: API基础URL（可选）
            timeout: 请求超时时间（秒）
        """
        self.model = model
        self.timeout = timeout

        config = self.MODEL_CONFIGS.get(model, {})
        self.provider = config.get("provider", "openai")
        self.api_base = api_base or config.get("api_base", "")
        self.api_key = api_key or self._get_default_api_key()

    def _get_default_api_key(self) -> str:
        """从环境变量获取默认API密钥"""
        if self.provider == "anthropic":
            return os.getenv("ANTHROPIC_API_KEY", "")
        elif self.provider == "qwen":
            return os.getenv("DASHSCOPE_API_KEY", "")
        else:  # openai
            return os.getenv("OPENAI_API_KEY", "")

    def analyze_image(
        self,
        image_source: Union[str, Path, bytes],
        prompt: str = "请详细描述这张图片的内容",
        detail: str = "auto",
        max_tokens: int = 1000,
    ) -> Dict[str, Any]:
        """分析图像内容

        Args:
            image_source: 图像来源（文件路径、URL或字节流）
            prompt: 分析提示词
            detail: 详细程度 (low, high, auto)
            max_tokens: 最大返回token数

        Returns:
            分析结果字典，包含:
            - ok: 是否成功
            - description: 图像描述/分析结果
            - error: 错误信息（如果失败）
            - usage: token使用情况
        """
        try:
            # 准备图像数据
            image_data = self._prepare_image(image_source)
            if not image_data["ok"]:
                return image_data

            # 根据provider调用相应API
            if self.provider == "anthropic":
                return self._analyze_with_anthropic(image_data, prompt, max_tokens)
            elif self.provider == "qwen":
                return self._analyze_with_qwen(image_data, prompt, max_tokens)
            else:
                return self._analyze_with_openai(image_data, prompt, detail, max_tokens)

        except requests.exceptions.Timeout:
            return {
                "ok": False,
                "error": "Request timeout",
                "error_type": VisionErrorType.TIMEOUT,
            }
        except requests.exceptions.RequestException as e:
            return {
                "ok": False,
                "error": f"Network error: {str(e)}",
                "error_type": VisionErrorType.NETWORK,
            }
        except Exception as e:
            return {
                "ok": False,
                "error": f"Unexpected error: {str(e)}",
                "error_type": VisionErrorType.UNKNOWN,
            }

    def image_to_text(
        self,
        image_source: Union[str, Path, bytes],
        language: str = "zh",
        preserve_format: bool = True,
    ) -> Dict[str, Any]:
        """OCR：从图像中提取文本

        Args:
            image_source: 图像来源
            language: 语言偏好 (zh, en, auto)
            preserve_format: 是否保留格式（换行、空格等）

        Returns:
            识别结果字典，包含:
            - ok: 是否成功
            - text: 提取的文本
            - confidence: 置信度（如果可用）
            - error: 错误信息（如果失败）
        """
        # 构建OCR提示词
        if language == "zh":
            prompt = "请仔细识别这张图片中的所有文字内容，包括中文和英文。"
            if preserve_format:
                prompt += "请保留原有的排版格式，包括换行和空格。只输出识别到的文字内容，不要添加任何解释。"
            else:
                prompt += "只输出识别到的文字内容，不要添加任何解释。"
        elif language == "en":
            prompt = "Please carefully identify all text content in this image."
            if preserve_format:
                prompt += " Preserve the original formatting including line breaks and spaces. Output only the recognized text without any explanation."
            else:
                prompt += " Output only the recognized text without any explanation."
        else:  # auto
            prompt = "请仔细识别这张图片中的所有文字内容（可能是中文或英文）。"
            if preserve_format:
                prompt += "请保留原有的排版格式。只输出识别到的文字内容，不要添加任何解释。"
            else:
                prompt += "只输出识别到的文字内容，不要添加任何解释。"

        result = self.analyze_image(
            image_source=image_source,
            prompt=prompt,
            max_tokens=2000,
        )

        # 重命名字段以符合OCR语义
        if result.get("ok"):
            result["text"] = result.pop("description", "")
        return result

    def _prepare_image(self, image_source: Union[str, Path, bytes]) -> Dict[str, Any]:
        """准备图像数据

        Args:
            image_source: 图像来源

        Returns:
            包含图像数据的字典
        """
        try:
            # 处理字节数据
            if isinstance(image_source, bytes):
                image_bytes = image_source
                media_type = self._guess_media_type(image_bytes)

            # 处理URL
            elif isinstance(image_source, str) and image_source.startswith(("http://", "https://")):
                response = requests.get(image_source, timeout=10)
                if response.status_code != 200:
                    return {
                        "ok": False,
                        "error": f"Failed to fetch image: HTTP {response.status_code}",
                        "error_type": VisionErrorType.NETWORK,
                    }
                image_bytes = response.content
                media_type = response.headers.get("Content-Type", "image/jpeg")

            # 处理文件路径
            else:
                path = Path(image_source)
                if not path.exists():
                    return {
                        "ok": False,
                        "error": f"File not found: {image_source}",
                        "error_type": VisionErrorType.INVALID_IMAGE,
                    }
                with open(path, "rb") as f:
                    image_bytes = f.read()
                media_type = self._get_media_type(path.suffix)

            # 编码为base64
            base64_data = base64.b64encode(image_bytes).decode("utf-8")

            return {
                "ok": True,
                "data": base64_data,
                "media_type": media_type,
                "size": len(image_bytes),
            }

        except Exception as e:
            return {
                "ok": False,
                "error": f"Failed to prepare image: {str(e)}",
                "error_type": VisionErrorType.INVALID_IMAGE,
            }

    def _guess_media_type(self, image_bytes: bytes) -> str:
        """根据字节猜测媒体类型"""
        # 简单的magic number检测
        if image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
            return "image/png"
        elif image_bytes[:2] == b'\xff\xd8':
            return "image/jpeg"
        elif image_bytes[:4] == b'GIF8':
            return "image/gif"
        elif image_bytes[:4] == b'RIFF' and image_bytes[8:12] == b'WEBP':
            return "image/webp"
        return "image/jpeg"  # 默认

    def _get_media_type(self, suffix: str) -> str:
        """根据文件扩展名获取媒体类型"""
        suffix_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
        }
        return suffix_map.get(suffix.lower(), "image/jpeg")

    def _analyze_with_anthropic(
        self,
        image_data: Dict[str, Any],
        prompt: str,
        max_tokens: int,
    ) -> Dict[str, Any]:
        """使用Claude API分析图像"""
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": image_data["media_type"],
                                "data": image_data["data"],
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        }

        url = f"{self.api_base}/messages"
        response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)

        if response.status_code == 200:
            data = response.json()
            # 提取文本内容
            text_content = ""
            for block in data.get("content", []):
                if block.get("type") == "text":
                    text_content += block.get("text", "")

            return {
                "ok": True,
                "description": text_content,
                "usage": data.get("usage", {}),
                "model": self.model,
            }
        else:
            return {
                "ok": False,
                "error": f"API error: HTTP {response.status_code} - {response.text[:200]}",
                "error_type": VisionErrorType.API_ERROR if response.status_code < 500 else VisionErrorType.NETWORK,
            }

    def _analyze_with_openai(
        self,
        image_data: Dict[str, Any],
        prompt: str,
        detail: str,
        max_tokens: int,
    ) -> Dict[str, Any]:
        """使用OpenAI API分析图像"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{image_data['media_type']};base64,{image_data['data']}",
                                "detail": detail
                            }
                        }
                    ]
                }
            ],
            "max_tokens": max_tokens,
        }

        url = f"{self.api_base}/chat/completions"
        response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)

        if response.status_code == 200:
            data = response.json()
            return {
                "ok": True,
                "description": data["choices"][0]["message"]["content"],
                "usage": data.get("usage", {}),
                "model": self.model,
            }
        else:
            return {
                "ok": False,
                "error": f"API error: HTTP {response.status_code} - {response.text[:200]}",
                "error_type": VisionErrorType.API_ERROR if response.status_code < 500 else VisionErrorType.NETWORK,
            }

    def _analyze_with_qwen(
        self,
        image_data: Dict[str, Any],
        prompt: str,
        max_tokens: int,
    ) -> Dict[str, Any]:
        """使用通义千问VL API分析图像"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{image_data['media_type']};base64,{image_data['data']}"
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ],
            "max_tokens": max_tokens,
        }

        url = f"{self.api_base}/chat/completions"
        response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)

        if response.status_code == 200:
            data = response.json()
            return {
                "ok": True,
                "description": data["choices"][0]["message"]["content"],
                "usage": data.get("usage", {}),
                "model": self.model,
            }
        else:
            return {
                "ok": False,
                "error": f"API error: HTTP {response.status_code} - {response.text[:200]}",
                "error_type": VisionErrorType.API_ERROR if response.status_code < 500 else VisionErrorType.NETWORK,
            }


# 便捷函数
def create_vision_client(
    model: str = None,
    api_key: str = None,
) -> VisionClient:
    """创建视觉客户端的便捷函数

    Args:
        model: 模型名称（默认从环境变量读取）
        api_key: API密钥（默认从环境变量读取）

    Returns:
        VisionClient实例
    """
    if model is None:
        model = os.getenv("VISION_MODEL", VisionModel.CLAUDE_SONNET)

    return VisionClient(model=model, api_key=api_key)


def analyze_image(
    image_source: Union[str, Path, bytes],
    prompt: str = "请详细描述这张图片的内容",
    model: str = None,
) -> Dict[str, Any]:
    """分析图像的便捷函数

    Args:
        image_source: 图像来源（文件路径、URL或字节流）
        prompt: 分析提示词
        model: 模型名称（可选）

    Returns:
        分析结果字典
    """
    client = create_vision_client(model=model)
    return client.analyze_image(image_source, prompt)


def ocr_image(
    image_source: Union[str, Path, bytes],
    language: str = "zh",
    model: str = None,
) -> Dict[str, Any]:
    """OCR识别图像文字的便捷函数

    Args:
        image_source: 图像来源
        language: 语言偏好 (zh, en, auto)
        model: 模型名称（可选）

    Returns:
        识别结果字典
    """
    client = create_vision_client(model=model)
    return client.image_to_text(image_source, language=language)
