"""三生命运行指标采样（每 2 小时由 crontab 调用，追加到 life_metrics.log）。

同时运行时代（2026-08-16 00:15 UTC 起）的连续验证数据：
- 每生命：episode 数、动作分布、CoT 残留率、tick 间隔
- 消息板：各生命发言量
- 错误：最近日志 Traceback 计数
输出一行 JSON + 人类可读摘要。
"""
import collections
import json
import re
from datetime import datetime, timezone

SIMULTANEOUS_CUTOFF = "2026-08-16T00:1"  # 同时运行开始时刻（UTC ISO 前缀）
COT_KEYS = ["【动作", "【主题", "等下", "哦对", "组织语言", "思考部分", "理清楚",
            "用户现在", "数下字数", "调整下"]
HOME = "/home/genesisx"


def ts_of(d):
    ts = d.get("timestamp")
    if isinstance(ts, (int, float)):
        return ts
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def life_stats(life):
    p = f"{HOME}/projects/Genesis{life}/artifacts/persistent/{life}/episodes.jsonl"
    total = 0
    sim_total = 0
    cot = 0
    acts = collections.Counter()
    sim_ts = []
    try:
        with open(p, encoding="utf-8") as f:
            for l in f:
                if not l.strip():
                    continue
                try:
                    d = json.loads(l)
                except Exception:
                    continue
                total += 1
                ts = d.get("timestamp") or ""
                if str(ts) > SIMULTANEOUS_CUTOFF:
                    sim_total += 1
                    acts[d.get("action", {}).get("type", "?")] += 1
                    st = str((d.get("outcome") or {}).get("status") or "")
                    if any(k in st for k in COT_KEYS):
                        cot += 1
                    t = ts_of(d)
                    if t:
                        sim_ts.append(t)
    except FileNotFoundError:
        pass
    gaps = sorted(b - a for a, b in zip(sim_ts, sim_ts[1:]) if 0 < b - a < 3600)
    median_gap = gaps[len(gaps) // 2] if gaps else None
    return {
        "episodes_total": total,
        "simultaneous_era": sim_total,
        "cot_residue": f"{cot}/{sim_total}",
        "actions": dict(acts.most_common(6)),
        "tick_median_s": round(median_gap) if median_gap else None,
    }


def board_stats():
    counts = collections.Counter()
    cutoff_epoch = datetime(2026, 8, 16, 0, 15, tzinfo=timezone.utc).timestamp()
    try:
        with open(f"{HOME}/shared/channels/group.jsonl", encoding="utf-8") as f:
            for l in f:
                if not l.strip():
                    continue
                try:
                    d = json.loads(l)
                except Exception:
                    continue
                ts = d.get("timestamp")
                try:  # 消息板的 timestamp 可能是 epoch 或 ISO，统一转 epoch 比较
                    t = (datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
                         if isinstance(ts, str) else float(ts))
                    if t >= cutoff_epoch:
                        counts[d.get("from", "?")] += 1
                except Exception:
                    pass
    except FileNotFoundError:
        pass
    return dict(counts)


def error_counts():
    out = {}
    for life in "ABC":
        n = 0
        try:
            with open(f"{HOME}/logs/genesisx-{life.lower()}.log", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()[-300:]
            n = sum(1 for x in lines if "Traceback" in x)
        except FileNotFoundError:
            n = -1
        out[life] = n
    return out


def main():
    result = {
        "time": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "lives": {L: life_stats(L) for L in "ABC"},
        "board": board_stats(),
        "recent_tracebacks": error_counts(),
    }
    print(json.dumps(result, ensure_ascii=False))
    for L in "ABC":
        s = result["lives"][L]
        print(f"  {L}: 总量{s['episodes_total']} 同跑期+{s['simultaneous_era']} "
              f"CoT残留{s['cot_residue']} tick中位{s['tick_median_s']}s "
              f"动作{list(s['actions'].items())[:4]}")
    print(f"  群聊(同跑期): {result['board']} | 近期错误: {result['recent_tracebacks']}")


if __name__ == "__main__":
    main()
