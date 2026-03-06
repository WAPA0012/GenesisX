"""CaretakerMode - 管家模式

从 LifeLoop 拆分出来的安全模式相关方法。
当系统遇到连续错误时进入管家模式，只保留基本功能。

论文 Section 3.13: 安全与降级策略

设计原则：
- 接收 LifeLoop 实例作为依赖（依赖注入）
- 保持与原始代码完全相同的行为
- 支持单元测试
"""

from typing import Optional

from common.models import ValueDimension
from common.logger import get_logger

logger = get_logger(__name__)


class CaretakerMode:
    """管家模式处理器

    负责：
    - 进入安全模式（禁用非必要器官）
    - 检查是否可以退出安全模式
    - 重置参数到安全默认值

    使用方式：
        caretaker = CaretakerMode(life_loop)
        caretaker.enter()
        if caretaker.should_exit():
            caretaker.exit()
    """

    def __init__(self, life_loop):
        """初始化管家模式处理器

        Args:
            life_loop: LifeLoop 实例，用于访问状态和依赖
        """
        self.life_loop = life_loop

        # 快捷引用
        self.fields = life_loop.fields
        self.state = life_loop.state
        self.organs = life_loop.organs

        # 管家模式启动时的 tick
        self._caretaker_mode_tick: Optional[int] = None

    @property
    def is_active(self) -> bool:
        """是否处于管家模式"""
        return self._caretaker_mode_tick is not None

    @property
    def entered_at_tick(self) -> Optional[int]:
        """进入管家模式时的 tick"""
        return self._caretaker_mode_tick

    def enter(self):
        """进入管家模式 (论文 Section 3.13)

        禁用除管家外的所有器官，只响应基本查询。
        """
        logger.warning("Entering safe mode - only Caretaker organ active")

        # 禁用除管家外的所有器官
        for organ_name, organ in self.organs.items():
            if organ_name != "caretaker":
                organ.enabled = False
            else:
                organ.enabled = True

        self._caretaker_mode_tick = self.state.tick

    def check_and_exit(self):
        """检查是否可以退出管家模式 (论文 Section 3.13)

        在以下条件下恢复：
        - 已经过足够的恢复时间（10 ticks）
        - 压力已降低（< 0.5）

        如果满足条件，重新启用所有器官。
        """
        if self._caretaker_mode_tick is None:
            return

        recovery_ticks = 10
        if (self.state.tick - self._caretaker_mode_tick >= recovery_ticks
                and self.fields.get("stress") < 0.5):
            logger.info("Exiting caretaker mode - re-enabling all organs")

            for organ in self.organs.values():
                organ.enabled = True

            self._caretaker_mode_tick = None

    def reset_to_safe_defaults(self):
        """重置参数到安全默认值 (论文 Section 3.13)

        当检测到参数漂移时调用。
        """
        logger.warning("Resetting parameters to safe defaults")

        # 使用统一的同步方法重置状态变量到安全范围
        safe_energy = max(0.3, self.fields.get("energy"))
        safe_stress = min(0.7, self.fields.get("stress"))
        safe_mood = 0.5  # 中性情绪

        self.life_loop._sync_fields_to_global(
            energy=safe_energy,
            stress=safe_stress,
            mood=safe_mood
        )

        # 重置价值权重到均匀分布
        for dim in ValueDimension:
            self.state.weights[dim] = 1.0 / len(ValueDimension)

        # 清空缺口
        for dim in ValueDimension:
            self.state.gaps[dim] = 0.0
