"""
Scheduler: Online/Offline Thread Management + Scheduled Actions

Manages the execution of:
- OnlineThread: Must-run ticks (user interaction, tool execution)
- OfflineThread: Dream/Reflect/Consolidation (budget-permitting, low-risk only)
- Scheduled Actions: Time-based task scheduling

References:
- 代码大纲架构 core/scheduler.py
- Default Mode Network (DMN) research
"""

from typing import Dict, Any, Optional, Callable, List
from enum import Enum
import time
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from common.models import ValueDimension


class ThreadMode(str, Enum):
    """Execution thread modes"""
    ONLINE = "online"      # Real-time interaction
    OFFLINE = "offline"    # Background consolidation


class ScheduleType(str, Enum):
    """定时行动类型"""
    ONCE = "once"              # 一次性执行
    INTERVAL = "interval"      # 固定间隔重复
    CRON = "cron"              # Cron风格（简化版）
    CONDITION = "condition"    # 条件触发


@dataclass
class ScheduledAction:
    """定时行动数据结构"""
    action_id: str                         # 行动唯一ID
    callback: Callable                     # 回调函数
    schedule_type: ScheduleType           # 调度类型
    params: Dict[str, Any] = field(default_factory=dict)

    # 时间参数（根据schedule_type使用不同的字段）
    execute_at: Optional[float] = None     # ONCE: 执行时间戳
    interval_seconds: Optional[float] = None  # INTERVAL: 间隔秒数
    condition_func: Optional[Callable[[], bool]] = None  # CONDITION: 条件函数

    # 重复参数
    repeat_count: int = 0                  # 重复次数（0=无限）
    executed_count: int = 0                # 已执行次数
    last_executed: Optional[float] = None  # 上次执行时间

    # 状态
    enabled: bool = True                   # 是否启用
    metadata: Dict[str, Any] = field(default_factory=dict)


class Scheduler:
    """
    Manages online (interactive) and offline (consolidation) execution threads.
    Also manages scheduled actions for time-based and condition-based tasks.

    MUST禁止在离线线程中执行高风险工具。
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.current_mode = ThreadMode.ONLINE
        self.offline_budget = config.get("offline_budget", {
            "max_tokens": 10000,
            "max_time_seconds": 300,
        })
        self.last_offline_tick = 0
        self._spent_tokens = 0
        self._spent_time = 0.0

        # 定时行动管理
        self._scheduled_actions: Dict[str, ScheduledAction] = {}
        self._action_counter = 0
        self._scheduler_lock = threading.Lock()

    def _get_gap_value(self, state: Dict[str, Any], dimension: str) -> float:
        """Get gap value from state, handling both direct and gaps dict access.

        Args:
            state: State dictionary (may be GlobalState or dict)
            dimension: Value dimension name (e.g., "meaning", "efficiency")

        Returns:
            Gap value for the dimension
        """
        # Try to get from gaps dict first
        if hasattr(state, 'gaps'):
            # state is GlobalState object
            try:
                dim = ValueDimension(dimension)
                return state.gaps.get(dim, 0.0)
            except ValueError:
                return 0.0
        elif isinstance(state, dict):
            # state is a dict, check if gaps exists
            gaps = state.get("gaps", {})
            if isinstance(gaps, dict):
                # gaps might be Dict[ValueDimension, float] or Dict[str, float]
                for key, value in gaps.items():
                    # Handle both ValueDimension enum and string keys
                    key_str = key.value if hasattr(key, 'value') else str(key)
                    if key_str == dimension:
                        return value
            return state.get(f"{dimension}_gap", 0.0)
        return 0.0

    def should_run_offline(self, tick: int, state: Dict[str, Any]) -> bool:
        """
        Determine if offline thread (Dream/Reflect) should run.

        Args:
            tick: Current tick number
            state: Global state with fatigue, meaning_gap, etc.

        Returns:
            True if offline thread should execute
        """
        # Check budget constraints
        offline_interval = self.config.get("offline_interval", 100)
        if tick - self.last_offline_tick < offline_interval:
            return False

        # Check fatigue or meaning gap
        # Handle both GlobalState object and dict input
        if hasattr(state, 'fatigue'):
            fatigue = state.fatigue
        else:
            fatigue = state.get("fatigue", 0.0)

        meaning_gap = self._get_gap_value(state, "meaning")
        efficiency_gap = self._get_gap_value(state, "efficiency")

        # Trigger if fatigue high or meaning gap large
        if fatigue > 0.7 or meaning_gap > 0.5:
            return True

        # Check if efficiency gap high (need to consolidate/prune)
        if efficiency_gap > 0.6:
            return True

        return False

    def enter_offline_mode(self, tick: int):
        """Enter offline thread (Dream/Reflect/Consolidation)"""
        self.current_mode = ThreadMode.OFFLINE
        self.last_offline_tick = tick

    def enter_online_mode(self):
        """Return to online thread"""
        self.current_mode = ThreadMode.ONLINE

    def is_offline(self) -> bool:
        """Check if currently in offline mode"""
        return self.current_mode == ThreadMode.OFFLINE

    def can_use_tool(self, tool_id: str, tool_risk: float) -> bool:
        """
        Check if tool can be used in current mode.

        MUST: 离线线程禁止高风险工具

        Args:
            tool_id: Tool identifier
            tool_risk: Risk score [0, 1]

        Returns:
            True if tool usage allowed
        """
        if self.current_mode == ThreadMode.ONLINE:
            return True

        # Offline mode: only allow low-risk tools
        max_offline_risk = self.config.get("max_offline_risk", 0.3)

        # Get forbidden tools from config
        forbidden_offline = self.config.get("forbidden_offline_tools",
            {"web_search", "code_exec", "file_write", "api_call"})
        if tool_id in forbidden_offline:
            return False

        return tool_risk <= max_offline_risk

    def get_budget_remaining(self) -> Dict[str, float]:
        """Get remaining offline budget"""
        max_tokens = self.offline_budget.get("max_tokens", 10000)
        max_time = self.offline_budget.get("max_time_seconds", 300)
        return {
            "max_tokens": max_tokens - self._spent_tokens,
            "max_time_seconds": max_time - self._spent_time,
        }

    def consume_budget(self, tokens_used: int, time_used: float) -> bool:
        """Consume offline budget resources.

        Args:
            tokens_used: Number of tokens to consume
            time_used: Time in seconds to consume

        Returns:
            True if budget was sufficient and consumed, False if insufficient
        """
        max_tokens = self.offline_budget.get("max_tokens", float('inf'))
        max_time = self.offline_budget.get("max_time_seconds", float('inf'))

        # Check if sufficient budget remaining
        if self._spent_tokens + tokens_used > max_tokens:
            return False
        if self._spent_time + time_used > max_time:
            return False

        # Track spent resources
        self._spent_tokens += tokens_used
        self._spent_time += time_used

        return True

    def reset_offline_budget(self):
        """Reset offline budget (e.g., daily)"""
        self._spent_tokens = 0
        self._spent_time = 0.0

    # ========== 定时行动管理 ==========

    def schedule_action(
        self,
        callback: Callable,
        schedule_type: str = "once",
        delay_seconds: float = None,
        interval_seconds: float = None,
        execute_at: float = None,
        condition_func: Callable[[], bool] = None,
        repeat_count: int = 0,
        action_id: str = None,
        metadata: Dict[str, Any] = None,
    ) -> str:
        """添加定时行动

        Args:
            callback: 要执行的回调函数
            schedule_type: 调度类型 (once, interval, condition)
            delay_seconds: 延迟执行的秒数（用于ONCE）
            interval_seconds: 重复间隔秒数（用于INTERVAL）
            execute_at: 指定执行时间戳（用于ONCE）
            condition_func: 条件函数（用于CONDITION）
            repeat_count: 重复次数（0表示无限）
            action_id: 自定义行动ID（可选）
            metadata: 附加元数据

        Returns:
            行动ID
        """
        with self._scheduler_lock:
            # 生成ID
            if action_id is None:
                self._action_counter += 1
                action_id = f"action_{self._action_counter}"

            # 确定执行时间
            execute_time = execute_at
            if execute_time is None and delay_seconds is not None:
                execute_time = time.time() + delay_seconds

            # 创建定时行动
            action = ScheduledAction(
                action_id=action_id,
                callback=callback,
                schedule_type=ScheduleType(schedule_type),
                execute_at=execute_time,
                interval_seconds=interval_seconds,
                condition_func=condition_func,
                repeat_count=repeat_count,
                metadata=metadata or {},
            )

            self._scheduled_actions[action_id] = action
            return action_id

    def cancel_action(self, action_id: str) -> bool:
        """取消定时行动

        Args:
            action_id: 行动ID

        Returns:
            是否成功取消
        """
        with self._scheduler_lock:
            if action_id in self._scheduled_actions:
                del self._scheduled_actions[action_id]
                return True
            return False

    def enable_action(self, action_id: str) -> bool:
        """启用定时行动"""
        with self._scheduler_lock:
            if action_id in self._scheduled_actions:
                self._scheduled_actions[action_id].enabled = True
                return True
            return False

    def disable_action(self, action_id: str) -> bool:
        """禁用定时行动"""
        with self._scheduler_lock:
            if action_id in self._scheduled_actions:
                self._scheduled_actions[action_id].enabled = False
                return True
            return False

    def check_scheduled_actions(self) -> List[Dict[str, Any]]:
        """检查并执行到期的定时行动

        应该在每个tick中调用此方法。

        Returns:
            本次执行的行动列表
        """
        executed = []
        current_time = time.time()

        with self._scheduler_lock:
            to_remove = []

            for action_id, action in self._scheduled_actions.items():
                if not action.enabled:
                    continue

                should_execute = False

                # 检查执行条件
                if action.schedule_type == ScheduleType.ONCE:
                    if action.execute_at and current_time >= action.execute_at:
                        should_execute = True
                        to_remove.append(action_id)

                elif action.schedule_type == ScheduleType.INTERVAL:
                    if action.interval_seconds:
                        if action.last_executed is None:
                            # 首次执行
                            if action.execute_at and current_time >= action.execute_at:
                                should_execute = True
                        else:
                            # 重复执行
                            elapsed = current_time - action.last_executed
                            if elapsed >= action.interval_seconds:
                                should_execute = True

                        # 检查重复次数
                        if should_execute and action.repeat_count > 0:
                            if action.executed_count >= action.repeat_count:
                                should_execute = False
                                to_remove.append(action_id)

                elif action.schedule_type == ScheduleType.CONDITION:
                    if action.condition_func and action.condition_func():
                        should_execute = True
                        # 条件触发默认只执行一次
                        to_remove.append(action_id)

                # 执行行动
                if should_execute:
                    try:
                        action.callback()
                        action.last_executed = current_time
                        action.executed_count += 1

                        executed.append({
                            "action_id": action_id,
                            "schedule_type": action.schedule_type.value,
                            "executed_at": current_time,
                            "executed_count": action.executed_count,
                        })
                    except Exception as e:
                        # 记录错误但继续调度其他行动
                        executed.append({
                            "action_id": action_id,
                            "schedule_type": action.schedule_type.value,
                            "error": str(e),
                        })

            # 清理已完成的一次性行动
            for action_id in to_remove:
                if action_id in self._scheduled_actions:
                    del self._scheduled_actions[action_id]

        return executed

    def list_scheduled_actions(self) -> List[Dict[str, Any]]:
        """列出所有定时行动

        Returns:
            行动列表
        """
        with self._scheduler_lock:
            result = []
            for action in self._scheduled_actions.values():
                result.append({
                    "action_id": action.action_id,
                    "schedule_type": action.schedule_type.value,
                    "enabled": action.enabled,
                    "executed_count": action.executed_count,
                    "repeat_count": action.repeat_count,
                    "last_executed": action.last_executed,
                    "execute_at": action.execute_at,
                    "interval_seconds": action.interval_seconds,
                })
            return result

    def get_action_status(self, action_id: str) -> Optional[Dict[str, Any]]:
        """获取特定行动的状态

        Args:
            action_id: 行动ID

        Returns:
            行动状态信息
        """
        with self._scheduler_lock:
            action = self._scheduled_actions.get(action_id)
            if action is None:
                return None

            return {
                "action_id": action.action_id,
                "schedule_type": action.schedule_type.value,
                "enabled": action.enabled,
                "executed_count": action.executed_count,
                "repeat_count": action.repeat_count,
                "last_executed": action.last_executed,
                "execute_at": action.execute_at,
                "interval_seconds": action.interval_seconds,
                "metadata": action.metadata,
            }

    def clear_scheduled_actions(self):
        """清除所有定时行动"""
        with self._scheduler_lock:
            self._scheduled_actions.clear()

    def get_pending_action_count(self) -> int:
        """获取待执行的行动数量"""
        with self._scheduler_lock:
            return sum(1 for a in self._scheduled_actions.values() if a.enabled)
