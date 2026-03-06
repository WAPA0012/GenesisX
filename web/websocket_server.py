"""WebSocket Server for Genesis X

提供实时双向通信，支持流式 LLM 响应和状态更新。
使用 websockets 库实现。
"""

import asyncio
import json
import logging
from typing import Set, Dict, Any, Optional, Callable
from datetime import datetime, timezone
import threading

logger = logging.getLogger(__name__)

# 尝试导入 websockets
try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    logger.warning("websockets library not available, WebSocket features disabled")


class WebSocketServer:
    """WebSocket 服务器，用于实时通信."""

    def __init__(self, host='127.0.0.1', port=5001):
        self.host = host
        self.port = port
        self.clients: Set[websockets.ServerConnection] = set()
        self.server = None
        self.is_running = False
        self.loop = None
        self.thread = None

        # 消息处理回调
        self.on_chat_message: Optional[Callable] = None

    async def _handle_client(self, websocket):
        """处理客户端连接."""
        self.clients.add(websocket)
        client_addr = websocket.remote_address
        logger.info(f"WebSocket client connected: {client_addr}")

        try:
            # 发送欢迎消息
            await websocket.send(json.dumps({
                "type": "connected",
                "message": "WebSocket 连接已建立",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }))

            # 消息处理循环
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._process_message(websocket, data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from client: {message}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {client_addr}")
        except Exception as e:
            logger.error(f"Error in client handler: {e}")
        finally:
            self.clients.discard(websocket)

    async def _process_message(self, websocket, data: Dict[str, Any]):
        """处理接收到的消息."""
        msg_type = data.get("type")

        if msg_type == "ping":
            # 心跳响应
            await websocket.send(json.dumps({
                "type": "pong",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }))

        elif msg_type == "chat":
            # 聊天消息 - 调用回调处理
            message = data.get("message", "")
            user = data.get("user", "User")

            if self.on_chat_message:
                try:
                    response = await self.on_chat_message(message, user)
                    await websocket.send(json.dumps({
                        "type": "chat_response",
                        "response": response,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }))
                except Exception as e:
                    logger.error(f"Error in chat callback: {e}")
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": str(e)
                    }))

        elif msg_type == "stream_chat":
            # 流式聊天消息 - 逐 token 发送
            message = data.get("message", "")
            await self._handle_stream_chat(websocket, message)

        elif msg_type == "get_state":
            # 请求当前状态
            state = await self._get_current_state()
            await websocket.send(json.dumps({
                "type": "state_update",
                "state": state,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }))

    async def _handle_stream_chat(self, websocket, message: str):
        """处理流式聊天，逐 token 发送响应."""
        # 发送开始标记
        await websocket.send(json.dumps({
            "type": "stream_start",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }))

        # 这里应该调用 LLM 流式生成接口
        # 暂时使用非流式方式模拟
        if self.on_chat_message:
            try:
                response = await self.on_chat_message(message, "User")

                # 模拟流式输出 - 按字符分块发送
                chunk_size = 10
                for i in range(0, len(response), chunk_size):
                    chunk = response[i:i + chunk_size]
                    await websocket.send(json.dumps({
                        "type": "stream_chunk",
                        "content": chunk,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }))
                    # 添加小延迟模拟打字效果
                    await asyncio.sleep(0.02)

            except Exception as e:
                logger.error(f"Error in stream chat: {e}")
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": str(e)
                }))

        # 发送结束标记
        await websocket.send(json.dumps({
            "type": "stream_end",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }))

    async def _get_current_state(self) -> Dict[str, Any]:
        """获取当前系统状态."""
        # 这个方法需要从外部注入或通过回调获取
        return {"status": "running"}

    async def broadcast(self, message: Dict[str, Any]):
        """向所有连接的客户端广播消息."""
        if not self.clients:
            return

        # 复制列表避免迭代时修改
        clients = list(self.clients)
        for client in clients:
            try:
                await client.send(json.dumps(message, ensure_ascii=False))
            except Exception as e:
                logger.error(f"Failed to send to client: {e}")
                self.clients.discard(client)

    async def broadcast_state(self, state: Dict[str, Any]):
        """广播系统状态更新."""
        await self.broadcast({
            "type": "state_update",
            "state": state,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    async def _run_server(self):
        """运行 WebSocket 服务器."""
        self.is_running = True
        logger.info(f"WebSocket server starting on ws://{self.host}:{self.port}")

        async with websockets.serve(self._handle_client, self.host, self.port):
            logger.info(f"WebSocket server running on ws://{self.host}:{self.port}")
            await asyncio.Future()  # 永远运行

    def start_in_thread(self):
        """在新线程中启动服务器."""
        if not WEBSOCKETS_AVAILABLE:
            logger.warning("websockets library not available, cannot start WebSocket server")
            return False

        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self._run_server())

        self.thread = threading.Thread(target=run_loop, daemon=True)
        self.thread.start()
        logger.info("WebSocket server thread started")
        return True

    async def stop(self):
        """停止服务器."""
        self.is_running = False
        # 关闭所有客户端连接
        for client in list(self.clients):
            await client.close()
        self.clients.clear()


# ============================================================================
# 全局 WebSocket 服务器实例
# ============================================================================

_ws_server: Optional[WebSocketServer] = None


def get_ws_server() -> WebSocketServer:
    """获取全局 WebSocket 服务器实例."""
    global _ws_server
    if _ws_server is None:
        _ws_server = WebSocketServer()
    return _ws_server


def start_ws_server(host='127.0.0.1', port=5001) -> Optional[WebSocketServer]:
    """启动 WebSocket 服务器.

    Args:
        host: 绑定地址
        port: 监听端口

    Returns:
        WebSocketServer 实例，如果启动失败则返回 None
    """
    if not WEBSOCKETS_AVAILABLE:
        logger.warning("websockets library not available")
        return None

    ws = get_ws_server()
    ws.host = host
    ws.port = port
    success = ws.start_in_thread()
    return ws if success else None


# ============================================================================
# 同步包装器，用于从 Flask 调用
# ============================================================================

def broadcast_state_sync(state: Dict[str, Any]):
    """同步方式广播状态（从 Flask 调用）."""
    ws = get_ws_server()
    if ws.loop and ws.clients:
        # 在 ws 的事件循环中执行
        asyncio.run_coroutine_threadsafe(
            ws.broadcast_state(state),
            ws.loop
        )


def broadcast_message_sync(message: Dict[str, Any]):
    """同步方式广播消息（从 Flask 调用）."""
    ws = get_ws_server()
    if ws.loop and ws.clients:
        asyncio.run_coroutine_threadsafe(
            ws.broadcast(message),
            ws.loop
        )
