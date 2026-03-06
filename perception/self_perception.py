"""
Self Perception Module - 自我感知能力

提供数字生命对自身的感知能力，包括：
- read_own_logs: 读取自己的日志，用于自我反思
- system_stats: 感知系统资源状态（CPU、内存等）

配合 memory/consolidation.py 的反思阶段和 axiology/homeostasis 使用。
"""

import os
import psutil
import platform
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime, timedelta
import threading
import time


class SelfPerception:
    """自我感知器 - 提供自我相关的感知能力"""

    def __init__(self, log_dir: str = "logs"):
        """初始化自我感知器

        Args:
            log_dir: 日志目录路径
        """
        self.log_dir = Path(log_dir)
        self._process = psutil.Process()
        self._boot_time = psutil.boot_time()
        self._start_time = time.time()

        # 缓存系统状态（避免频繁查询）
        self._stats_cache: Dict[str, Any] = {}
        self._cache_ttl = 5.0  # 缓存5秒
        self._last_cache_time = 0.0
        self._cache_lock = threading.Lock()

    def read_own_logs(
        self,
        log_file: str = None,
        lines: int = 100,
        level: str = None,
        since: str = None,
        search: str = None,
    ) -> Dict[str, Any]:
        """读取自己的日志

        用于自我反思，了解自己最近的行为和状态。

        Args:
            log_file: 日志文件名（默认genesis.json）
            lines: 读取的行数（默认100，-1表示全部）
            level: 过滤日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            since: 时间范围，如 "1h", "30m", "1d"
            search: 搜索关键词

        Returns:
            日志内容字典，包含:
            - ok: 是否成功
            - entries: 日志条目列表
            - count: 条目数量
            - summary: 日志摘要
            - error: 错误信息（如果失败）
        """
        try:
            # 确定日志文件
            if log_file is None:
                log_file = "genesis.json"

            log_path = self.log_dir / log_file

            if not log_path.exists():
                return {
                    "ok": False,
                    "error": f"Log file not found: {log_path}",
                    "entries": [],
                    "count": 0,
                }

            # 读取日志
            entries = self._read_log_file(log_path, lines, level, since, search)

            # 生成摘要
            summary = self._summarize_logs(entries)

            return {
                "ok": True,
                "entries": entries,
                "count": len(entries),
                "summary": summary,
                "log_file": str(log_path),
            }

        except Exception as e:
            return {
                "ok": False,
                "error": f"Failed to read logs: {str(e)}",
                "entries": [],
                "count": 0,
            }

    def _read_log_file(
        self,
        log_path: Path,
        lines: int,
        level: str,
        since: str,
        search: str,
    ) -> List[Dict[str, Any]]:
        """读取并解析日志文件"""
        import json

        entries = []

        # 计算时间阈值
        time_threshold = None
        if since:
            time_threshold = self._parse_time_range(since)

        # 从后往前读取（日志通常是追加的）
        with open(log_path, 'r', encoding='utf-8') as f:
            if lines == -1:
                # 读取全部
                all_lines = f.readlines()
            else:
                # 读取最后N行
                all_lines = f.readlines()[-lines * 10:]  # 多读一些，因为可能有过滤

        # 解析JSON日志
        for line in reversed(all_lines):
            if lines != -1 and len(entries) >= lines:
                break

            try:
                entry = json.loads(line.strip())

                # 级别过滤
                if level and entry.get("level") != level.upper():
                    continue

                # 时间过滤
                if time_threshold:
                    entry_time = entry.get("timestamp", "")
                    if entry_time:
                        try:
                            # 解析ISO时间
                            entry_dt = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
                            if entry_dt < time_threshold:
                                continue
                        except (ValueError, TypeError):
                            # 修复：使用更精确的异常类型
                            pass

                # 搜索过滤
                if search:
                    message = entry.get("message", "")
                    if search.lower() not in message.lower():
                        continue

                entries.append(entry)

            except (json.JSONDecodeError, KeyError):
                continue

        return entries

    def _parse_time_range(self, since: str) -> datetime:
        """解析时间范围字符串

        Args:
            since: 时间范围，如 "1h", "30m", "1d", "90s"

        Returns:
            阈值时间
        """
        now = datetime.now()

        if since.endswith("h"):
            hours = int(since[:-1])
            return now - timedelta(hours=hours)
        elif since.endswith("m"):
            minutes = int(since[:-1])
            return now - timedelta(minutes=minutes)
        elif since.endswith("d"):
            days = int(since[:-1])
            return now - timedelta(days=days)
        elif since.endswith("s"):
            # 修复：添加秒单位支持
            seconds = int(since[:-1])
            return now - timedelta(seconds=seconds)
        else:
            # 默认1小时
            return now - timedelta(hours=1)

    def _summarize_logs(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成日志摘要"""
        if not entries:
            return {
                "level_counts": {},
                "top_modules": {},
                "has_errors": False,
                "time_range": None,
            }

        # 统计级别
        level_counts = {}
        for entry in entries:
            level = entry.get("level", "UNKNOWN")
            level_counts[level] = level_counts.get(level, 0) + 1

        # 统计模块
        module_counts = {}
        for entry in entries:
            module = entry.get("module", "unknown")
            module_counts[module] = module_counts.get(module, 0) + 1

        # 取前5个模块
        top_modules = dict(sorted(
            module_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5])

        # 检查是否有错误
        has_errors = any(
            entry.get("level") in ("ERROR", "CRITICAL")
            for entry in entries
        )

        # 时间范围
        timestamps = [
            entry.get("timestamp", "")
            for entry in entries
            if entry.get("timestamp")
        ]
        time_range = None
        if timestamps:
            time_range = {
                "earliest": min(timestamps),
                "latest": max(timestamps),
            }

        return {
            "level_counts": level_counts,
            "top_modules": top_modules,
            "has_errors": has_errors,
            "time_range": time_range,
        }

    def get_recent_errors(
        self,
        hours: float = 1.0,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """获取最近的错误日志

        Args:
            hours: 时间范围（小时）
            limit: 最大条数

        Returns:
            错误日志列表
        """
        return self.read_own_logs(
            log_file="errors.json",
            since=f"{int(hours * 60)}m",
            lines=limit,
        )

    def system_stats(self) -> Dict[str, Any]:
        """获取系统资源状态

        用于 HOMEOSTASIS 价值维度，感知自身资源压力。

        Returns:
            系统状态字典，包含:
            - cpu_percent: CPU使用率
            - memory: 内存信息
            - disk: 磁盘信息
            - process: 进程信息
            - uptime: 系统运行时间
            - pressure_score: 资源压力分数 [0-1]
        """
        with self._cache_lock:
            current_time = time.time()
            if current_time - self._last_cache_time < self._cache_ttl and self._stats_cache:
                return self._stats_cache

            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=0.1)

            # 内存信息
            memory = psutil.virtual_memory()
            memory_info = {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "percent": memory.percent,
                "pressure": memory.percent / 100.0,
            }

            # 磁盘信息 - 修复跨平台兼容性
            # Windows: 使用当前驱动器根目录，Unix: 使用根目录
            import os
            disk_path = os.path.expanduser("~") if platform.system() == "Windows" else "/"
            disk = psutil.disk_usage(disk_path)
            disk_info = {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent": disk.percent,
            }

            # 进程信息 - 修复异常处理
            connections = []
            try:
                connections = self._process.connections() if hasattr(self._process, 'connections') else []
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass

            process_info = {
                "pid": self._process.pid,
                "cpu_percent": self._process.cpu_percent(),
                "memory_mb": round(self._process.memory_info().rss / (1024**2), 2),
                "num_threads": self._process.num_threads(),
                "num_fds": len(connections),
            }

            # 系统运行时间
            uptime_seconds = time.time() - self._boot_time
            uptime_info = {
                "boot_time": datetime.fromtimestamp(self._boot_time).isoformat(),
                "uptime_seconds": int(uptime_seconds),
                "uptime_hours": round(uptime_seconds / 3600, 2),
                "process_runtime_seconds": int(time.time() - self._start_time),
            }

            # 平台信息
            platform_info = {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
            }

            # 计算资源压力分数（用于HOMEOSTASIS）
            pressure_score = self._calculate_pressure_score(
                cpu_percent, memory_info, process_info
            )

            result = {
                "cpu_percent": cpu_percent,
                "memory": memory_info,
                "disk": disk_info,
                "process": process_info,
                "uptime": uptime_info,
                "platform": platform_info,
                "pressure_score": pressure_score,
                "timestamp": datetime.now().isoformat(),
            }

            # 更新缓存
            self._stats_cache = result
            self._last_cache_time = current_time

            return result

    def _calculate_pressure_score(
        self,
        cpu_percent: float,
        memory_info: Dict[str, Any],
        process_info: Dict[str, Any],
    ) -> float:
        """计算资源压力分数

        用于价值系统的 HOMEOSTASIS 维度。

        Args:
            cpu_percent: CPU使用率
            memory_info: 内存信息
            process_info: 进程信息

        Returns:
            压力分数 [0-1]，越高表示压力越大
        """
        # CPU压力
        cpu_pressure = min(cpu_percent / 100.0, 1.0)

        # 内存压力
        memory_pressure = memory_info.get("pressure", 0.0)

        # 进程内存压力
        process_memory_mb = process_info.get("memory_mb", 0)
        process_memory_pressure = min(process_memory_mb / 1000.0, 1.0)  # 1GB为阈值

        # 综合压力（加权平均）
        pressure_score = (
            cpu_pressure * 0.3 +
            memory_pressure * 0.4 +
            process_memory_pressure * 0.3
        )

        return round(pressure_score, 3)

    def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态摘要

        返回简化的健康状态，用于快速检查。
        """
        stats = self.system_stats()

        # 判断健康等级
        pressure = stats["pressure_score"]
        if pressure < 0.3:
            health = "healthy"
            status = "系统运行正常"
        elif pressure < 0.6:
            health = "moderate"
            status = "系统负载中等"
        elif pressure < 0.8:
            health = "high_load"
            status = "系统负载较高"
        else:
            health = "critical"
            status = "系统负载过高，建议优化"

        return {
            "health": health,
            "status": status,
            "pressure_score": pressure,
            "cpu_percent": stats["cpu_percent"],
            "memory_percent": stats["memory"]["percent"],
            "uptime_hours": stats["uptime"]["uptime_hours"],
            "timestamp": stats["timestamp"],
        }

    def clear_cache(self):
        """清除状态缓存"""
        with self._cache_lock:
            self._stats_cache = {}
            self._last_cache_time = 0


# 单例实例
_perception_instance: Optional[SelfPerception] = None


def get_self_perception(log_dir: str = "logs") -> SelfPerception:
    """获取自我感知器单例

    Args:
        log_dir: 日志目录路径

    Returns:
        SelfPerception 实例
    """
    global _perception_instance
    if _perception_instance is None:
        _perception_instance = SelfPerception(log_dir)
    return _perception_instance


# 便捷函数
def read_logs(
    lines: int = 100,
    level: str = None,
    since: str = None,
    search: str = None,
) -> Dict[str, Any]:
    """读取日志的便捷函数"""
    return get_self_perception().read_own_logs(
        lines=lines,
        level=level,
        since=since,
        search=search,
    )


def get_system_stats() -> Dict[str, Any]:
    """获取系统状态的便捷函数"""
    return get_self_perception().system_stats()


def get_health_status() -> Dict[str, Any]:
    """获取健康状态的便捷函数"""
    return get_self_perception().get_health_status()
