"""
Voice Module - 语音输出能力

提供数字生命的语音输出能力，支持多种TTS引擎。

支持的TTS引擎：
- pyttsx3: 离线TTS，跨平台
- edge-tts: Microsoft Edge TTS，高质量在线
- 百度AI: 百度语音合成
- 讯飞AI: 讯飞语音合成
"""

import os
from typing import Dict, Any, Optional, List
from enum import Enum
import threading
import queue


class TTSEngine(str, Enum):
    """TTS引擎类型"""
    OFFLINE = "pyttsx3"       # 离线TTS
    EDGE = "edge_tts"         # Microsoft Edge TTS
    BAIDU = "baidu"           # 百度AI
    XUNFEI = "xunfei"         # 讯飞AI


class VoiceGender(str, Enum):
    """音色性别"""
    MALE = "male"
    FEMALE = "female"


class VoiceEmotion(str, Enum):
    """语音情感"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    EXCITED = "excited"
    CALM = "calm"


class TTSErrorType:
    """TTS错误类型"""
    ENGINE_NOT_AVAILABLE = "engine_not_available"
    NETWORK_ERROR = "network_error"
    AUTH_ERROR = "auth_error"
    INVALID_TEXT = "invalid_text"
    UNKNOWN = "unknown"


class VoiceOutput:
    """语音输出管理器"""

    def __init__(self, engine: TTSEngine = TTSEngine.OFFLINE):
        """初始化语音输出

        Args:
            engine: TTS引擎类型
        """
        self.engine = engine
        self._engine_instance = None
        self._initialized = False

        # 语音队列（用于异步播放）
        self._queue = queue.Queue()
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False

        # 默认语音参数
        self.voice_params = {
            "rate": 150,        # 语速
            "volume": 1.0,      # 音量
            "gender": VoiceGender.FEMALE,
            "emotion": VoiceEmotion.NEUTRAL,
        }

    def initialize(self) -> Dict[str, Any]:
        """初始化TTS引擎

        Returns:
            初始化结果
        """
        try:
            if self.engine == TTSEngine.OFFLINE:
                return self._init_pyttsx3()
            elif self.engine == TTSEngine.EDGE:
                return self._init_edge_tts()
            elif self.engine == TTSEngine.BAIDU:
                return self._init_baidu()
            elif self.engine == TTSEngine.XUNFEI:
                return self._init_xunfei()
            else:
                return {
                    "ok": False,
                    "error": f"Unknown engine: {self.engine}",
                    "error_type": TTSErrorType.ENGINE_NOT_AVAILABLE,
                }
        except Exception as e:
            return {
                "ok": False,
                "error": f"Initialization failed: {str(e)}",
                "error_type": TTSErrorType.UNKNOWN,
            }

    def _init_pyttsx3(self) -> Dict[str, Any]:
        """初始化pyttsx3离线引擎"""
        try:
            import pyttsx3
            self._engine_instance = pyttsx3.init()
            self._initialized = True

            # 设置默认参数
            self._engine_instance.setProperty('rate', self.voice_params["rate"])
            self._engine_instance.setProperty('volume', self.voice_params["volume"])

            return {
                "ok": True,
                "engine": TTSEngine.OFFLINE.value,
                "voices": [self._get_voice_info(id) for id in self._engine_instance.getProperty('voices')],
            }
        except ImportError:
            return {
                "ok": False,
                "error": "pyttsx3 not installed. Run: pip install pyttsx3",
                "error_type": TTSErrorType.ENGINE_NOT_AVAILABLE,
            }
        except Exception as e:
            return {
                "ok": False,
                "error": f"Failed to initialize pyttsx3: {str(e)}",
                "error_type": TTSErrorType.UNKNOWN,
            }

    def _init_edge_tts(self) -> Dict[str, Any]:
        """初始化Edge TTS引擎"""
        try:
            import edge_tts
            self._engine_instance = edge_tts
            self._initialized = True

            return {
                "ok": True,
                "engine": TTSEngine.EDGE.value,
                "note": "Edge TTS generates audio files that can be played",
            }
        except ImportError:
            return {
                "ok": False,
                "error": "edge-tts not installed. Run: pip install edge-tts",
                "error_type": TTSErrorType.ENGINE_NOT_AVAILABLE,
            }

    def _init_baidu(self) -> Dict[str, Any]:
        """初始化百度TTS引擎"""
        api_key = os.getenv("BAIDU_API_KEY")
        secret_key = os.getenv("BAIDU_SECRET_KEY")

        if not api_key or not secret_key:
            return {
                "ok": False,
                "error": "BAIDU_API_KEY and BAIDU_SECRET_KEY required",
                "error_type": TTSErrorType.AUTH_ERROR,
            }

        try:
            import requests
            self._engine_instance = {
                "type": "baidu",
                "api_key": api_key,
                "secret_key": secret_key,
                "token": self._get_baidu_token(api_key, secret_key),
            }
            self._initialized = True

            return {
                "ok": True,
                "engine": TTSEngine.BAIDU.value,
            }
        except Exception as e:
            return {
                "ok": False,
                "error": f"Failed to initialize Baidu TTS: {str(e)}",
                "error_type": TTSErrorType.UNKNOWN,
            }

    def _init_xunfei(self) -> Dict[str, Any]:
        """初始化讯飞TTS引擎"""
        app_id = os.getenv("XUNFEI_APP_ID")
        api_key = os.getenv("XUNFEI_API_KEY")
        api_secret = os.getenv("XUNFEI_API_SECRET")

        if not all([app_id, api_key, api_secret]):
            return {
                "ok": False,
                "error": "XUNFEI_APP_ID, XUNFEI_API_KEY, XUNFEI_API_SECRET required",
                "error_type": TTSErrorType.AUTH_ERROR,
            }

        self._engine_instance = {
            "type": "xunfei",
            "app_id": app_id,
            "api_key": api_key,
            "api_secret": api_secret,
        }
        self._initialized = True

        return {
            "ok": True,
            "engine": TTSEngine.XUNFEI.value,
        }

    def _get_baidu_token(self, api_key: str, secret_key: str) -> str:
        """获取百度API Token"""
        import requests

        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials",
            "client_id": api_key,
            "client_secret": secret_key,
        }
        response = requests.post(url, params=params)
        return response.json().get("access_token", "")

    def _get_voice_info(self, voice) -> Dict[str, Any]:
        """获取语音信息"""
        try:
            return {
                "id": getattr(voice, 'id', 'unknown'),
                "name": getattr(voice, 'name', 'unknown'),
                "languages": getattr(voice, 'languages', []),
                "gender": getattr(voice, 'gender', 'unknown'),
            }
        except:
            return {"id": "unknown", "name": "unknown"}

    def speak(
        self,
        text: str,
        rate: int = None,
        volume: float = None,
        save_to_file: str = None,
        async_mode: bool = False,
    ) -> Dict[str, Any]:
        """语音合成并播放

        Args:
            text: 要朗读的文本
            rate: 语速（默认使用初始化设置）
            volume: 音量0-1（默认使用初始化设置）
            save_to_file: 保存到文件（仅部分引擎支持）
            async_mode: 异步模式（在后台播放）

        Returns:
            播放结果
        """
        if not self._initialized:
            init_result = self.initialize()
            if not init_result.get("ok"):
                return init_result

        if not text or not text.strip():
            return {
                "ok": False,
                "error": "Text is empty",
                "error_type": TTSErrorType.INVALID_TEXT,
            }

        try:
            if self.engine == TTSEngine.OFFLINE:
                return self._speak_pyttsx3(text, rate, volume, async_mode)
            elif self.engine == TTSEngine.EDGE:
                return self._speak_edge(text, save_to_file)
            elif self.engine == TTSEngine.BAIDU:
                return self._speak_baidu(text, save_to_file)
            elif self.engine == TTSEngine.XUNFEI:
                return self._speak_xunfei(text, save_to_file)
            else:
                return {
                    "ok": False,
                    "error": f"Unknown engine: {self.engine}",
                    "error_type": TTSErrorType.UNKNOWN,
                }
        except Exception as e:
            return {
                "ok": False,
                "error": f"Speech failed: {str(e)}",
                "error_type": TTSErrorType.UNKNOWN,
            }

    def _speak_pyttsx3(
        self,
        text: str,
        rate: int = None,
        volume: float = None,
        async_mode: bool = False,
    ) -> Dict[str, Any]:
        """使用pyttsx3播放"""
        engine = self._engine_instance

        # 设置参数
        if rate:
            engine.setProperty('rate', rate)
        if volume:
            engine.setProperty('volume', volume)

        if async_mode:
            # 异步播放：在单独线程中播放
            import threading

            def play():
                engine.say(text)
                engine.runAndWait()

            thread = threading.Thread(target=play, daemon=True)
            thread.start()

            return {
                "ok": True,
                "engine": TTSEngine.OFFLINE.value,
                "async": True,
                "text": text,
            }
        else:
            # 同步播放
            engine.say(text)
            engine.runAndWait()

            return {
                "ok": True,
                "engine": TTSEngine.OFFLINE.value,
                "text": text,
            }

    async def _speak_edge(self, text: str, save_to_file: str = None) -> Dict[str, Any]:
        """使用Edge TTS生成音频"""
        import edge_tts
        import asyncio

        communicate = edge_tts.Communicate(text, "zh-CN-XiaoxiaoNeural")

        if save_to_file:
            await communicate.save(save_to_file)
            return {
                "ok": True,
                "engine": TTSEngine.EDGE.value,
                "file": save_to_file,
                "text": text,
            }
        else:
            # 生成临时文件并播放
            import tempfile
            import platform
            import subprocess

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                temp_file = f.name

            await communicate.save(temp_file)

            # 播放音频文件
            if platform.system() == "Windows":
                subprocess.call(["powershell", "-c", f"(New-Object Media.SoundPlayer '{temp_file}').PlaySync()"])
            elif platform.system() == "Darwin":  # macOS
                subprocess.call(["afplay", temp_file])
            else:  # Linux
                subprocess.call(["aplay", temp_file])

            # 删除临时文件
            try:
                os.unlink(temp_file)
            except:
                pass

            return {
                "ok": True,
                "engine": TTSEngine.EDGE.value,
                "text": text,
            }

    def _speak_edge(self, text: str, save_to_file: str = None) -> Dict[str, Any]:
        """同步版本的Edge TTS"""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self._speak_edge(text, save_to_file))

    def _speak_baidu(self, text: str, save_to_file: str = None) -> Dict[str, Any]:
        """使用百度TTS"""
        import requests
        import tempfile

        token = self._engine_instance.get("token")
        if not token:
            return {
                "ok": False,
                "error": "Baidu token not available",
                "error_type": TTSErrorType.AUTH_ERROR,
            }

        url = "https://tsn.baidu.com/text2audio"
        params = {
            "tex": text,
            "tok": token,
            "cuid": "genesis_x",
            "ctp": "1",
            "lan": "zh",
        }

        response = requests.get(url, params=params)

        if save_to_file:
            with open(save_to_file, 'wb') as f:
                f.write(response.content)
            return {
                "ok": True,
                "engine": TTSEngine.BAIDU.value,
                "file": save_to_file,
                "text": text,
            }
        else:
            # 保存到临时文件并播放
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                temp_file = f.name
                f.write(response.content)

            # 播放
            import platform
            import subprocess

            if platform.system() == "Windows":
                subprocess.call(["powershell", "-c", f"(New-Object Media.SoundPlayer '{temp_file}').PlaySync()"])
            elif platform.system() == "Darwin":
                subprocess.call(["afplay", temp_file])
            else:
                subprocess.call(["aplay", temp_file])

            try:
                os.unlink(temp_file)
            except:
                pass

            return {
                "ok": True,
                "engine": TTSEngine.BAIDU.value,
                "text": text,
            }

    def _speak_xunfei(self, text: str, save_to_file: str = None) -> Dict[str, Any]:
        """使用讯飞TTS（需要实现WebSocket连接）"""
        # 讯飞TTS需要WebSocket连接，这里简化处理
        return {
            "ok": False,
            "error": "Xunfei TTS not fully implemented yet",
            "error_type": TTSErrorType.ENGINE_NOT_AVAILABLE,
        }

    def set_voice_params(self, **kwargs):
        """设置语音参数

        Args:
            rate: 语速
            volume: 音量
            gender: 性别
            emotion: 情感
        """
        self.voice_params.update(kwargs)

        # 如果引擎已初始化，实时更新参数
        if self._initialized and self.engine == TTSEngine.OFFLINE:
            engine = self._engine_instance
            if "rate" in kwargs:
                engine.setProperty('rate', kwargs["rate"])
            if "volume" in kwargs:
                engine.setProperty('volume', kwargs["volume"])

    def stop(self):
        """停止当前播放"""
        if self._initialized and self.engine == TTSEngine.OFFLINE:
            self._engine_instance.stop()

    def is_available(self, engine: TTSEngine = None) -> bool:
        """检查TTS引擎是否可用

        Args:
            engine: 要检查的引擎（默认使用当前引擎）

        Returns:
            是否可用
        """
        if engine is None:
            engine = self.engine

        try:
            if engine == TTSEngine.OFFLINE:
                import pyttsx3
                return True
            elif engine == TTSEngine.EDGE:
                import edge_tts
                return True
            elif engine == TTSEngine.BAIDU:
                return bool(os.getenv("BAIDU_API_KEY") and os.getenv("BAIDU_SECRET_KEY"))
            elif engine == TTSEngine.XUNFEI:
                return all([
                    os.getenv("XUNFEI_APP_ID"),
                    os.getenv("XUNFEI_API_KEY"),
                    os.getenv("XUNFEI_API_SECRET"),
                ])
            return False
        except ImportError:
            return False


# 全局语音输出实例
_voice_output: Optional[VoiceOutput] = None


def get_voice_output(engine: str = None) -> VoiceOutput:
    """获取语音输出单例

    Args:
        engine: TTS引擎类型（可选）

    Returns:
        VoiceOutput 实例
    """
    global _voice_output
    if _voice_output is None:
        if engine:
            _voice_output = VoiceOutput(TTSEngine(engine))
        else:
            # 自动选择可用的引擎
            for eng in [TTSEngine.OFFLINE, TTSEngine.EDGE, TTSEngine.BAIDU]:
                test = VoiceOutput(eng)
                if test.is_available():
                    _voice_output = test
                    break
            if _voice_output is None:
                _voice_output = VoiceOutput(TTSEngine.OFFLINE)
    return _voice_output


# 便捷函数
def speak(text: str, engine: str = None, **kwargs) -> Dict[str, Any]:
    """语音输出的便捷函数

    Args:
        text: 要朗读的文本
        engine: TTS引擎类型
        **kwargs: 其他参数

    Returns:
        播放结果
    """
    voice = get_voice_output(engine)
    return voice.speak(text, **kwargs)


def is_voice_available(engine: str = None) -> bool:
    """检查语音输出是否可用"""
    voice = VoiceOutput(TTSEngine(engine)) if engine else get_voice_output()
    return voice.is_available()
