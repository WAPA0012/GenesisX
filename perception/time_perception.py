"""
Time Perception Module - 时间感知能力

提供数字生命对时间的感知能力，包括：
- get_time: 获取当前时间
- get_time_context: 获取时间上下文（时段、星期几等）

配合 metabolism/circadian.py 昼夜节律系统使用。
"""

from datetime import datetime
from typing import Dict, Any, Optional
import pytz


class TimePerception:
    """时间感知器 - 提供时间相关的感知能力"""

    def __init__(self, timezone: str = "Asia/Shanghai"):
        """初始化时间感知器

        Args:
            timezone: 时区，默认亚洲/上海
        """
        self.timezone = pytz.timezone(timezone)
        self._cached_time: Optional[datetime] = None
        self._cache_ttl = 1.0  # 缓存1秒
        self._last_cache_time = 0.0

    def get_time(self, format: str = "iso") -> Dict[str, Any]:
        """获取当前时间

        Args:
            format: 返回格式，可选 "iso", "timestamp", "dict", "natural"

        Returns:
            包含时间信息的字典
        """
        now = datetime.now(self.timezone)

        result = {
            "timezone": str(self.timezone),
            "unix_timestamp": int(now.timestamp()),
        }

        if format == "iso":
            result["iso"] = now.isoformat()
            result["readable"] = now.strftime("%Y-%m-%d %H:%M:%S")
        elif format == "timestamp":
            result["timestamp"] = now.timestamp()
        elif format == "dict":
            result.update({
                "year": now.year,
                "month": now.month,
                "day": now.day,
                "hour": now.hour,
                "minute": now.minute,
                "second": now.second,
                "weekday": now.weekday(),  # 0=Monday, 6=Sunday
                "weekday_name": now.strftime("%A"),
            })
        elif format == "natural":
            result["natural"] = self._natural_time(now)

        return result

    def get_time_context(self) -> Dict[str, Any]:
        """获取时间上下文信息

        用于与昼夜节律系统配合，判断当前时段特征。

        Returns:
            包含时段、时期等上下文信息的字典
        """
        now = datetime.now(self.timezone)
        hour = now.hour

        # 时段划分
        if 5 <= hour < 8:
            period = "dawn"        # 黎明
            energy_trend = "rising"
        elif 8 <= hour < 12:
            period = "morning"     # 上午
            energy_trend = "high"
        elif 12 <= hour < 14:
            period = "noon"        # 中午
            energy_trend = "dip"
        elif 14 <= hour < 18:
            period = "afternoon"   # 下午
            energy_trend = "stable"
        elif 18 <= hour < 22:
            period = "evening"     # 晚上
            energy_trend = "declining"
        else:
            period = "night"       # 深夜
            energy_trend = "low"

        # 星期几
        weekday = now.weekday()
        is_weekend = weekday >= 5  # 5=Saturday, 6=Sunday

        # 月份季节
        month = now.month
        if month in [12, 1, 2]:
            season = "winter"
        elif month in [3, 4, 5]:
            season = "spring"
        elif month in [6, 7, 8]:
            season = "summer"
        else:
            season = "autumn"

        return {
            "period": period,
            "energy_trend": energy_trend,
            "hour": hour,
            "weekday": weekday,
            "weekday_name": now.strftime("%A"),
            "is_weekend": is_weekend,
            "month": month,
            "season": season,
            "day_of_year": now.timetuple().tm_yday,
        }

    def _natural_time(self, dt: datetime) -> str:
        """生成自然语言描述的时间

        Args:
            dt: 时间对象

        Returns:
            自然语言时间描述
        """
        hour = dt.hour
        minute = dt.minute

        # 时段
        if 5 <= hour < 8:
            period = "黎明"
        elif 8 <= hour < 12:
            period = "上午"
        elif 12 <= hour < 14:
            period = "中午"
        elif 14 <= hour < 18:
            period = "下午"
        elif 18 <= hour < 22:
            period = "晚上"
        elif 22 <= hour or hour < 2:
            period = "深夜"
        else:
            period = "凌晨"

        # 具体时间
        if minute == 0:
            time_str = f"{hour}点整"
        elif minute < 10:
            time_str = f"{hour}点零{minute}分"
        else:
            time_str = f"{hour}点{minute}分"

        return f"{period}{time_str}"

    def get_time_since(self, timestamp: float) -> Dict[str, Any]:
        """计算距离某时间的时间差

        Args:
            timestamp: Unix时间戳

        Returns:
            时间差信息
        """
        now = datetime.now(self.timezone)
        then = datetime.fromtimestamp(timestamp, self.timezone)
        delta = now - then

        seconds = int(delta.total_seconds())
        minutes = seconds // 60
        hours = minutes // 60
        days = hours // 24

        return {
            "seconds": seconds,
            "minutes": minutes,
            "hours": hours,
            "days": days,
            "natural_delta": self._natural_delta(seconds),
        }

    def _natural_delta(self, seconds: int) -> str:
        """生成自然语言的时间差描述

        Args:
            seconds: 秒数

        Returns:
            自然语言描述
        """
        if seconds < 60:
            return f"{seconds}秒前"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes}分钟前"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{hours}小时前"
        elif seconds < 2592000:  # 30天
            days = seconds // 86400
            return f"{days}天前"
        elif seconds < 31536000:  # 365天
            months = seconds // 2592000
            return f"{months}个月前"
        else:
            years = seconds // 31536000
            return f"{years}年前"


# 单例实例
_perception_instance: Optional[TimePerception] = None


def get_time_perception(timezone: str = "Asia/Shanghai") -> TimePerception:
    """获取时间感知器单例

    Args:
        timezone: 时区

    Returns:
        TimePerception 实例
    """
    global _perception_instance
    if _perception_instance is None:
        _perception_instance = TimePerception(timezone)
    return _perception_instance


# 便捷函数
def get_current_time(format: str = "dict") -> Dict[str, Any]:
    """获取当前时间的便捷函数"""
    return get_time_perception().get_time(format)


def get_time_info() -> Dict[str, Any]:
    """获取完整时间上下文的便捷函数"""
    perception = get_time_perception()
    result = perception.get_time("dict")
    result["context"] = perception.get_time_context()
    return result
