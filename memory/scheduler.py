"""读侧记忆调度器（实验性，2026-08）—— Level 1。

来源：讨论"OrganMemoryWriter 能否变成主动记忆调度器"。它的判断回路
（这段经历值得记吗？）翻转方向复用（此刻该想起什么？）。

两级演进的第一级：
1. 多角度查询（零 LLM）：从当前任务/工作记忆/社交消息派生查询变体，
   各做一次语义检索，合并去重。——蓝本基准证明"agent 查询改写是召回
   第一功臣"（33%→100%），Level 1 用语境现成文本当变体，省一次 LLM。
2. LLM 相关性裁决（每 tick ≤1 次调用）：给候选记忆 + 当 tick 语境，
   让模型挑出真正决策相关的（≤3 条）并给一句理由。
3. 保底原则（只加不删）：近因 + 高显著记忆永远保送。裁决失误的
   最坏情况退化为现状，不会更糟。

门控：GENESISX_MEMORY_SCHEDULER=1 启用，默认关。
输出经 context["scheduled_memories"] 进入 mind 提示词的【相关记忆】区块。
"""
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from common.logger import get_logger

logger = get_logger(__name__)

# LLM 裁决的行式输出解析："0. 理由" / "1、理由"（序号前允许有元思考文字）
_JUDGE_LINE_RE = re.compile(r"(\d+)[.、)．]\s*(.+)$")


def _episode_digest(ep) -> str:
    """一行记忆摘要：t<tick> 动作 简述 => 结果。"""
    try:
        obs = ep.observation
        obs_text = str(getattr(obs, "payload", "") or "")[:70] if obs else ""
        act = ep.action.type.value if ep.action else "?"
        status = str(ep.outcome.status or "")[:50] if ep.outcome else ""
        return f"t{ep.tick} {act} {obs_text} => {status}".strip()
    except Exception:
        return f"t{getattr(ep, 'tick', '?')}"


class MemoryScheduler:
    """读侧记忆调度器：mind 决策前主动调度相关记忆。"""

    def __init__(self, retrieval, episodic, llm_client=None, external_client=None):
        self.retrieval = retrieval
        self.episodic = episodic
        self.llm = llm_client
        # 外部记忆服务（实验供给源，D）：有配置时优先从服务取相关记忆，
        # 本地语义池+LLM 裁决自动退为回退。服务细节见 memory/external_memory.py
        self.external = external_client
        self.stats = {
            "dispatches": 0,
            "query_angles": 0,
            "llm_judgments": 0,
            "llm_failures": 0,
            "memories_surfaced": 0,
            "external_recalls": 0,
            "external_hits": 0,
        }

    # ---- 1. 查询角度（零 LLM）----

    def _query_angles(self, context: Dict[str, Any]) -> List[str]:
        """从当 tick 语境派生查询变体：任务/工作记忆/社交消息。"""
        angles: List[str] = []

        def _add(text: str):
            text = str(text or "").strip()
            if len(text) >= 4 and text[:80] not in angles:
                angles.append(text[:80])

        for key in ("task", "goal"):
            _add((context or {}).get(key))
        wm = (context or {}).get("working_memory") or {}
        _add(wm.get("task"))
        for s in ((context or {}).get("social_feed") or [])[:2]:
            # "B: 消息内容" / "新闻: 标题" → 取冒号后的正文
            body = str(s).split(":", 1)[-1].strip()
            if len(body) >= 6:
                _add(body)
        return angles[:3]

    # ---- 2. 保底集（只加不删的底线）----

    def _floor_memories(self, tick: int, n_recent: int = 2, n_salient: int = 2) -> list:
        """近因 + 高显著（|delta|）记忆，不经 LLM 直接保送。"""
        out = []
        try:
            out.extend(self.episodic.query_recent(n_recent))
        except Exception:
            pass
        try:
            for ep in self.episodic.query_by_rpe_magnitude(limit=n_recent * 3):
                if all(getattr(ep, "tick", None) != getattr(o, "tick", None) for o in out):
                    out.append(ep)
                if len(out) >= n_recent + n_salient:
                    break
        except Exception:
            pass
        return out

    # ---- 3. LLM 相关性裁决 ----

    def _judge(self, candidates: list, context: Dict[str, Any]) -> List[Tuple[Any, str]]:
        """让 LLM 从候选中挑真正决策相关的（≤3 条），附一句理由。

        行式输出而非 JSON——step_plan 端点的推理残留会破坏 JSON，
        行式 + 正则解析更鲁棒。
        """
        if not self.llm or not candidates:
            return []

        ctx_parts = []
        for key, label in (("task", "当前任务"), ("goal", "目标")):
            v = str((context or {}).get(key) or "").strip()
            if v:
                ctx_parts.append(f"{label}: {v[:60]}")
        feed = (context or {}).get("social_feed") or []
        if feed:
            ctx_parts.append("最近消息: " + " / ".join(str(s)[:40] for s in feed[:2]))
        ctx_text = "；".join(ctx_parts) if ctx_parts else "常规决策时刻"

        cand_lines = "\n".join(f"[{i}] {_episode_digest(ep)}" for i, ep in enumerate(candidates))

        prompt = (
            f"一个数字生命马上要做本 tick 的决策。当前处境：{ctx_text}。\n"
            f"候选记忆（它过去的经历）：\n{cand_lines}\n\n"
            f"从候选里挑出【对当前处境真正有用】的记忆，最多 3 条，一条都不到位就都不选。\n"
            f"输出格式（每行一条，不要多余解释）：序号. 为什么此刻该想起它"
        )
        try:
            result = self.llm.chat(messages=[{"role": "user", "content": prompt}],
                                   temperature=0.2, max_tokens=300)
        except Exception as e:
            self.stats["llm_failures"] += 1
            logger.debug(f"[SCHEDULER] 裁决调用失败: {e}")
            return []

        if not (result and result.get("ok") and result.get("text")):
            self.stats["llm_failures"] += 1
            return []

        self.stats["llm_judgments"] += 1
        picked: List[Tuple[Any, str]] = []
        for line in result["text"].splitlines():
            # search 而非 match：推理模型常在序号前垫一句元思考（"首先看看。1. …"）
            m = _JUDGE_LINE_RE.search(line.strip())
            if not m:
                continue
            idx = int(m.group(1))
            reason = m.group(2).strip()[:60]
            if 0 <= idx < len(candidates) and idx not in (i for i, _ in picked):
                picked.append((candidates[idx], reason))
            if len(picked) >= 3:
                break
        return picked

    @staticmethod
    def _grep_patterns(query: str, limit: int = 10) -> List[str]:
        """从查询派生 grep 变体（基准经验：单次 grep 召回弱，~10 次变体才达 98.9%）。

        变体策略：全句 → 标点分段 → 长词优先，去重保序。
        """
        import re as _re
        q = str(query or "").strip()
        if not q:
            return []
        pats: List[str] = []
        if len(q) >= 4:
            pats.append(q)
        segs = [s for s in _re.split(r"[，。！？；：、\s,.!?;:()\[\]（）【】]+", q) if len(s) >= 2]
        pats.extend(segs[:4])
        for w in sorted(segs, key=len, reverse=True):
            if w not in pats:
                pats.append(w)
        out: List[str] = []
        for p in pats:
            if p not in out:
                out.append(p)
        return out[:limit]

    # ---- 主入口 ----

    def dispatch(self, context: Dict[str, Any], tick: int) -> List[Tuple[Any, str, str]]:
        """调度本 tick 的相关记忆。返回 (episode, 理由, 一行摘要) 列表。"""
        self.stats["dispatches"] += 1

        # 多角度语义检索（零 LLM）
        angles = self._query_angles(context)
        self.stats["query_angles"] += len(angles)

        # 外部记忆服务优先（实验供给源）：服务有结果时本 tick 的供给来自它，
        # 本地语义池/LLM 裁决跳过；服务失败或为空则自动走本地路径
        if self.external is not None and angles:
            self.stats["external_recalls"] += 1
            ext_rows = self.external.recall(angles[0], top_k=4)
            if not ext_rows:
                # 多轮 grep 回退（基准经验：~10 次变体才达 98.9% 召回）。
                # grep 零 LLM 零延迟，变体跑满不贵；逐模式试，凑够即停。
                try:
                    seen = set()
                    ext_rows = []
                    patterns = self._grep_patterns(angles[0])
                    for pat in patterns:
                        for r in self.external.grep(pat, top_k=3):
                            if r["summary"] not in seen:
                                seen.add(r["summary"])
                                ext_rows.append(r)
                        if len(ext_rows) >= 6:
                            break
                    if ext_rows:
                        self.stats["grep_fallbacks"] = self.stats.get("grep_fallbacks", 0) + 1
                        self.stats["grep_attempts"] = self.stats.get("grep_attempts", 0) + len(patterns[:10])
                except Exception:
                    ext_rows = []
            if ext_rows:
                self.stats["external_hits"] += 1
                result: List[Tuple[Any, str, str]] = [
                    (None, "记忆网络联想", r["summary"]) for r in ext_rows]
                for ep in self._floor_memories(tick):
                    t = getattr(ep, "tick", None)
                    if t not in {getattr(r2[0], "tick", None) for r2 in result}:
                        result.append((ep, "近因/高显著保底", _episode_digest(ep)))
                self.stats["memories_surfaced"] += len(result)
                logger.info(f"[SCHEDULER] t{tick} 外部记忆供给 {len(ext_rows)} 条: "
                            + " | ".join(r["summary"][:40] for r in ext_rows[:3]))
                return result[:6]

        pool: List[Any] = []
        seen_ticks = set()
        for q in angles:
            try:
                hits = self.retrieval.retrieve_by_semantic_similarity(
                    q, current_tick=tick, limit=5, min_similarity=0.05)
            except Exception as e:
                logger.debug(f"[SCHEDULER] 角度检索失败（非致命）: {e}")
                continue
            for ep in hits or []:
                t = getattr(ep, "tick", None)
                if t not in seen_ticks:
                    seen_ticks.add(t)
                    pool.append(ep)
        pool = pool[:8]

        # LLM 裁决（有候选且有角度才值得花这一次调用）
        judged = self._judge(pool, context) if pool else []

        # 合成：裁决选中的在前（带理由），保底集补位（不删任何保底）
        result: List[Tuple[Any, str, str]] = []
        taken = set()
        for ep, reason in judged:
            t = getattr(ep, "tick", None)
            if t not in taken:
                taken.add(t)
                result.append((ep, reason, _episode_digest(ep)))
        for ep in self._floor_memories(tick):
            t = getattr(ep, "tick", None)
            if t not in taken:
                taken.add(t)
                result.append((ep, "近因/高显著保底", _episode_digest(ep)))

        result = result[:6]
        self.stats["memories_surfaced"] += len(result)
        if result:
            logger.info(f"[SCHEDULER] t{tick} 调度 {len(result)} 条记忆 "
                        f"(角度{len(angles)} 裁决{len(judged)}): "
                        + " | ".join(r[2][:40] for r in result[:3]))
        return result
