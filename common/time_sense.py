"""时间感知（2026-08）：数字生命的真实时钟。

LLM 的时间感停在训练截止日——模型以为还是 2024/2025，导致它们搜索
"2024年轻量小会"这类过期年份、对"今天/今年"没有概念。此模块提供统一的
真实时间感知行，注入决策、执行、搜索、社交的全部提示词。

哲学：时钟是感知不是规则——告诉它"现在是什么时候"，不告诉它"该做什么"。
"""
from datetime import datetime, timezone

_WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


def now_line() -> str:
    """一行真实时间感知（本机时区）。"""
    n = datetime.now()
    return (
        f"现在是 {n.year}年{n.month}月{n.day}日 {_WEEKDAYS[n.weekday()]} {n:%H:%M}。"
        f"这是真实世界的当前时间——你的训练知识截止在此之前，谈论'最近/今年/最新'"
        f"时以此刻为准（今年是 {n.year} 年），不要用训练时的旧年份。"
    )


def age_line(first_timestamp) -> str:
    """自诞生（第一条 episode）以来的运行时长。"""
    try:
        t = first_timestamp
        if isinstance(t, str):
            t = datetime.fromisoformat(t.replace("Z", "+00:00"))
        if not isinstance(t, datetime):
            return ""
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        days = (datetime.now(timezone.utc) - t).total_seconds() / 86400
        if days < 1:
            return f"你已持续运行约 {max(1, round(days * 24))} 小时"
        return f"你自 {t:%Y-%m-%d} 诞生，已持续运行约 {days:.0f} 天"
    except Exception:
        return ""
