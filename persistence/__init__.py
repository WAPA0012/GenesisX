"""Persistence layer for Genesis X GA.

P7-16 修复（2026-07）：
- replay.py（回放引擎）已接入 life_loop PHASE 10，支持 STRICT 回放
- event_log/tool_call_log/snapshot/storage 已删除（零引用写入器，生产用
  common/jsonl + EpisodicMemory + life_loop._persist_final_state）
- 论文 C8（可复现性）从"实现但零接入"变为"STRICT 回放可用"
"""
from .replay import ReplayEngine, ReplayMode

__all__ = [
    "ReplayEngine",
    "ReplayMode",
]
