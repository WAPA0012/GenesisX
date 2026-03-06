"""
Messaging Module - 主动消息发送能力

提供数字生命主动发送消息给用户的能力。

这是实现自主性的关键能力之一，让数字生命从"被动响应"
转变为"主动发起"，能够在满足特定条件时主动联系用户。

支持多种通知渠道：
- 控制台输出
- 日志记录
- 文件消息
- Webhook通知
- 未来可扩展：邮件、短信、即时通讯等
"""

import os
import json
import requests
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field
import threading
import queue


class MessagePriority(str, Enum):
    """消息优先级"""
    LOW = "low"           # 低优先级，可以延迟发送
    NORMAL = "normal"     # 普通优先级
    HIGH = "high"         # 高优先级，尽快发送
    URGENT = "urgent"     # 紧急，立即发送


class MessageType(str, Enum):
    """消息类型"""
    INFO = "info"         # 信息
    WARNING = "warning"   # 警告
    ERROR = "error"       # 错误
    QUESTION = "question" # 问题/询问
    INSIGHT = "insight"   # 洞察
    REPORT = "report"     # 报告
    GREETING = "greeting" # 问候


@dataclass
class Message:
    """消息数据结构"""
    content: str                    # 消息内容
    type: MessageType = MessageType.INFO
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)  # 附加元数据
    source: str = "genesis"          # 消息来源


class MessageChannel:
    """消息通道基类"""

    def __init__(self, name: str, enabled: bool = True):
        self.name = name
        self.enabled = enabled

    def send(self, message: Message) -> Dict[str, Any]:
        """发送消息

        Args:
            message: 消息对象

        Returns:
            发送结果字典
        """
        if not self.enabled:
            return {"ok": False, "error": f"Channel {self.name} is disabled"}
        return self._send(message)

    def _send(self, message: Message) -> Dict[str, Any]:
        """实际发送消息的子类实现"""
        raise NotImplementedError


class ConsoleChannel(MessageChannel):
    """控制台消息通道"""

    def __init__(self, enabled: bool = True):
        super().__init__("console", enabled)

        # ANSI颜色代码
        self.colors = {
            MessageType.INFO: "\033[36m",      # 青色
            MessageType.WARNING: "\033[33m",   # 黄色
            MessageType.ERROR: "\033[31m",     # 红色
            MessageType.QUESTION: "\033[35m",  # 紫色
            MessageType.INSIGHT: "\033[32m",   # 绿色
            MessageType.REPORT: "\033[34m",    # 蓝色
            MessageType.GREETING: "\033[97m",  # 白色
        }
        self.reset = "\033[0m"

    def _send(self, message: Message) -> Dict[str, Any]:
        """输出到控制台"""
        color = self.colors.get(message.type, "")
        prefix = f"[{message.type.value.upper()}]"

        # 格式化输出
        print(f"{color}{prefix}{self.reset} {message.content}")

        return {"ok": True, "channel": "console"}


class LogChannel(MessageChannel):
    """日志文件消息通道"""

    def __init__(self, log_dir: str = "logs/messages", enabled: bool = True):
        super().__init__("log", enabled)
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _send(self, message: Message) -> Dict[str, Any]:
        """写入日志文件"""
        log_file = self.log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.jsonl"

        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps({
                    "content": message.content,
                    "type": message.type.value,
                    "priority": message.priority.value,
                    "timestamp": message.timestamp,
                    "metadata": message.metadata,
                    "source": message.source,
                }, ensure_ascii=False) + "\n")

            return {"ok": True, "channel": "log", "file": str(log_file)}
        except Exception as e:
            return {"ok": False, "error": str(e)}


class WebhookChannel(MessageChannel):
    """Webhook消息通道"""

    def __init__(self, url: str, enabled: bool = True):
        super().__init__("webhook", enabled)
        self.url = url
        self.timeout = 10

    def _send(self, message: Message) -> Dict[str, Any]:
        """发送HTTP请求"""
        try:
            payload = {
                "content": message.content,
                "type": message.type.value,
                "priority": message.priority.value,
                "timestamp": message.timestamp,
                "metadata": message.metadata,
                "source": message.source,
            }

            response = requests.post(
                self.url,
                json=payload,
                timeout=self.timeout,
            )

            if response.status_code == 200:
                return {"ok": True, "channel": "webhook"}
            else:
                return {
                    "ok": False,
                    "error": f"HTTP {response.status_code}",
                    "channel": "webhook"
                }

        except requests.exceptions.Timeout:
            return {"ok": False, "error": "Timeout", "channel": "webhook"}
        except Exception as e:
            return {"ok": False, "error": str(e), "channel": "webhook"}


class CallbackChannel(MessageChannel):
    """回调函数消息通道"""

    def __init__(self, callback: Callable[[Message], Dict[str, Any]], enabled: bool = True):
        super().__init__("callback", enabled)
        self.callback = callback

    def _send(self, message: Message) -> Dict[str, Any]:
        """调用回调函数"""
        try:
            return self.callback(message)
        except Exception as e:
            return {"ok": False, "error": str(e), "channel": "callback"}


class MessagingSystem:
    """消息发送系统

    管理多个消息通道，提供统一的消息发送接口。
    """

    def __init__(self):
        """初始化消息系统"""
        self.channels: List[MessageChannel] = []
        self.message_queue: queue.Queue = queue.Queue()
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None

        # 添加默认通道
        self.add_channel(ConsoleChannel())
        self.add_channel(LogChannel())

    def add_channel(self, channel: MessageChannel):
        """添加消息通道

        Args:
            channel: 消息通道对象
        """
        self.channels.append(channel)

    def remove_channel(self, channel_name: str):
        """移除消息通道

        Args:
            channel_name: 通道名称
        """
        self.channels = [c for c in self.channels if c.name != channel_name]

    def send_message(
        self,
        content: str,
        type: MessageType = MessageType.INFO,
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """发送消息

        Args:
            content: 消息内容
            type: 消息类型
            priority: 消息优先级
            metadata: 附加元数据

        Returns:
            发送结果字典，包含各通道的发送状态
        """
        message = Message(
            content=content,
            type=type,
            priority=priority,
            metadata=metadata or {},
        )

        results = []
        for channel in self.channels:
            # 根据优先级决定是否发送
            if priority == MessagePriority.URGENT or channel.enabled:
                result = channel.send(message)
                results.append(result)

        # 返回汇总结果
        success_count = sum(1 for r in results if r.get("ok"))
        return {
            "ok": success_count > 0,
            "success_count": success_count,
            "total_channels": len(results),
            "results": results,
            "message": {
                "content": content,
                "type": type.value,
                "priority": priority.value,
                "timestamp": message.timestamp,
            }
        }

    # 便捷方法
    def info(self, content: str, **kwargs) -> Dict[str, Any]:
        """发送信息消息"""
        return self.send_message(content, MessageType.INFO, **kwargs)

    def warning(self, content: str, **kwargs) -> Dict[str, Any]:
        """发送警告消息"""
        return self.send_message(content, MessageType.WARNING, **kwargs)

    def error(self, content: str, **kwargs) -> Dict[str, Any]:
        """发送错误消息"""
        return self.send_message(content, MessageType.ERROR,
                               MessagePriority.HIGH, **kwargs)

    def question(self, content: str, **kwargs) -> Dict[str, Any]:
        """发送问题/询问"""
        return self.send_message(content, MessageType.QUESTION, **kwargs)

    def insight(self, content: str, **kwargs) -> Dict[str, Any]:
        """发送洞察消息（用于反思阶段）"""
        return self.send_message(content, MessageType.INSIGHT, **kwargs)

    def report(self, content: str, **kwargs) -> Dict[str, Any]:
        """发送报告消息"""
        return self.send_message(content, MessageType.REPORT, **kwargs)

    def greet(self, content: str, **kwargs) -> Dict[str, Any]:
        """发送问候消息"""
        return self.send_message(content, MessageType.GREETING, **kwargs)


# 全局消息系统实例
_messaging_system: Optional[MessagingSystem] = None


def get_messaging_system() -> MessagingSystem:
    """获取消息系统单例

    Returns:
        MessagingSystem 实例
    """
    global _messaging_system
    if _messaging_system is None:
        _messaging_system = MessagingSystem()
    return _messaging_system


# 便捷函数
def send_message(
    content: str,
    type: str = "info",
    priority: str = "normal",
    metadata: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """发送消息的便捷函数

    Args:
        content: 消息内容
        type: 消息类型 (info, warning, error, question, insight, report, greeting)
        priority: 优先级 (low, normal, high, urgent)
        metadata: 附加元数据

    Returns:
        发送结果
    """
    system = get_messaging_system()

    # 转换枚举
    try:
        msg_type = MessageType(type)
    except ValueError:
        msg_type = MessageType.INFO

    try:
        msg_priority = MessagePriority(priority)
    except ValueError:
        msg_priority = MessagePriority.NORMAL

    return system.send_message(content, msg_type, msg_priority, metadata)


def notify_user(content: str, **kwargs) -> Dict[str, Any]:
    """通知用户的便捷函数"""
    return send_message(content, **kwargs)


def alert_error(content: str, **kwargs) -> Dict[str, Any]:
    """发送错误警报的便捷函数"""
    return send_message(content, type="error", priority="high", **kwargs)


def share_insight(content: str, **kwargs) -> Dict[str, Any]:
    """分享洞察的便捷函数"""
    return send_message(content, type="insight", **kwargs)
