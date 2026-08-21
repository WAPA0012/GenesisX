"""外部记忆服务适配层（纯 REST 客户端，2026-08）。

记忆服务是独立进程（协议：POST /api/recall、POST /api/intake、GET /api/health）。
本文件只做协议对接，不包含任何记忆机制的实现——服务地址由环境变量
GENESISX_MEMORY_SERVICE 指定（不设置即完全关闭，A/B/C 默认关闭）。

用法：
    client = ExternalMemoryClient("http://127.0.0.1:18234")
    rows = client.recall("上次探索天气工具学到什么")   # [{summary, level, score}]
    client.intake("EXPLORE: 学到了wttr.in支持ASCII渲染")  # 写入经历摘要
"""
import json as _json
import os
import urllib.request
from typing import Any, Dict, List, Optional

from common.logger import get_logger

logger = get_logger(__name__)


def service_url() -> Optional[str]:
    """读 GENESISX_MEMORY_SERVICE；未设置返回 None（功能关闭）。"""
    url = os.environ.get("GENESISX_MEMORY_SERVICE", "").strip()
    return url.rstrip("/") if url else None


class ExternalMemoryClient:
    """极简 HTTP 客户端：recall / intake / health。全部尽力而为，失败不阻塞主循环。"""

    def __init__(self, base_url: str, timeout: int = 90):
        # 90s：完整 recall 含 CP2 校验 + 回忆事件判定（多轮推理模型调用），
        # 实测 30-60s+；30s 会在服务正常时反而超时拿空
        self.base = base_url.rstrip("/")
        self.timeout = timeout
        self.calls = 0
        self.failures = 0

    def _post(self, path: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        req = urllib.request.Request(
            f"{self.base}{path}",
            data=_json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        self.calls += 1
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return _json.loads(r.read().decode("utf-8"))
        except Exception as e:
            self.failures += 1
            logger.debug(f"[EXT-MEM] {path} 失败（非致命）: {e}")
            return None

    def recall(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """查询相关记忆，返回 [{summary, level, score}]（失败/为空返回 []）。"""
        d = self._post("/api/recall", {"query": str(query)[:200]})
        if not d:
            return []
        items = d.get("recalled") or d.get("results") or d.get("items") or []
        out = []
        for it in items[:top_k]:
            summary = str(it.get("summary") or it.get("content") or "")[:150].strip()
            if summary:
                out.append({
                    "summary": summary,
                    "level": str(it.get("cognitive_level") or ""),
                    "score": it.get("score") or 0.0,
                })
        return out

    def grep(self, pattern: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """精确文本搜索（零 LLM）——向量检索对精确标识符弱，grep 互补。"""
        d = self._post("/api/grep", {"pattern": str(pattern)[:100]})
        if not d:
            return []
        out = []
        for m in (d.get("matches") or [])[:top_k]:
            summary = str(m.get("summary") or "")[:150].strip()
            if summary:
                out.append({"summary": summary, "level": str(m.get("cognitive_level") or "")})
        return out

    def intake(self, text: str, factual: bool = False) -> bool:
        """写入一条经历摘要。factual=True 表示来自外部信息源（新闻等）。"""
        return self._post("/api/intake", {"text": str(text)[:500], "factual": factual}) is not None

    def health(self) -> bool:
        try:
            with urllib.request.urlopen(f"{self.base}/api/health", timeout=5) as r:
                return r.status == 200
        except Exception:
            return False
