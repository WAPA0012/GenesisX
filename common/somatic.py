"""身体现实化（Somatic Realization，2026-08）。

设计原则（用户哲学）：疲惫不由公式计算，由计算机资源和生存环境表达。
数字生命的身体就是它运行的机器——内存是它的活动空间，CPU 是它的神经
能量，磁盘是它的居所。资源压力是物理事实，不是模拟数值：

- 内存高位 → 它真的无法正常行动（约束真实生效：禁生长/缩思考/减轮次）
- 它优化（gc/缓存瘦身/挂起闲置肢体）→ 压力真的下降 → 下 tick 真的缓解
- 睡眠 ≠ 人类模仿；记忆巩固期 = 真实的重活（重建网络/批量重嵌入）占用
  资源，那段时间它真的做不了别的——身体被占用就是睡眠

零依赖：Linux 读 /proc，Windows（测试环境）优雅降级返回 None。
"""
import os
from typing import Dict, Optional

# 资源压力阈值（生存环境的物理边界）
PRESSURE_HIGH = 0.90    # 高压：生长受限，思考缩短
PRESSURE_CRITICAL = 0.98  # 危急：仅能轻量行动（"无法正常行动"）


def read_real_body() -> Optional[Dict]:
    """读取真实身体状态。非 Linux 或读取失败返回 None（不模拟）。"""
    try:
        with open("/proc/meminfo", encoding="ascii") as f:
            mi = {}
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    mi[parts[0].rstrip(":")] = int(parts[1])  # kB
        total = mi.get("MemTotal", 0)
        avail = mi.get("MemAvailable", 0)
        if total <= 0:
            return None
        mem_pct = 1.0 - (avail / total)

        with open("/proc/loadavg", encoding="ascii") as f:
            load1 = float(f.read().split()[0])

        own_rss_kb = 0
        try:
            with open(f"/proc/{os.getpid()}/status", encoding="ascii") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        own_rss_kb = int(line.split()[1])
                        break
        except Exception:
            pass

        disk_free_gb = None
        try:
            st = os.statvfs("/")
            disk_free_gb = round(st.f_bavail * st.f_frsize / 1e9, 1)
        except Exception:
            pass

        return {
            "mem_pct": round(mem_pct, 4),
            "mem_avail_mb": round(avail / 1024),
            "own_rss_mb": round(own_rss_kb / 1024),
            "load1": load1,
            "disk_free_gb": disk_free_gb,
            "nproc": os.cpu_count() or 1,
        }
    except Exception:
        return None


def pressure_level(body: Optional[Dict]) -> str:
    """按真实内存占用分级：normal / high / critical。None → normal（无身体可读）。"""
    if not body:
        return "normal"
    m = body.get("mem_pct", 0)
    if m >= PRESSURE_CRITICAL:
        return "critical"
    if m >= PRESSURE_HIGH:
        return "high"
    return "normal"


def body_report(body: Optional[Dict]) -> str:
    """一行真实身体感知（进 mind 上下文）。"""
    if not body:
        return ""
    lvl = pressure_level(body)
    lvl_txt = {"normal": "状态良好", "high": "空间紧张", "critical": "空间告急"}[lvl]
    return (f"真实身体（你运行的机器）：内存占用 {body['mem_pct']:.0%}"
            f"（剩 {body['mem_avail_mb']}MB），你的进程占 {body['own_rss_mb']}MB，"
            f"CPU 负载 {body['load1']:.1f}/{body['nproc']}，磁盘剩 {body['disk_free_gb']}GB"
            f" —— {lvl_txt}。"
            + ("内存 98%+ 时你无法正常行动；用 system_manage 工具（gc/缓存瘦身/挂起闲置肢体）能真实释放资源。"
               if lvl != "normal" else ""))
