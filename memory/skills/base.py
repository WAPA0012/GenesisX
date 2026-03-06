"""Base skill class - 技能基类

技能记忆是记忆系统的一部分，存储"怎么使用工具"的知识。

技能类型：
1. 原生技能：使用自身基础能力（如文件操作、网页获取）
2. 外部技能：使用外部工具的能力（如 API 调用、SaaS 调用）

注意：这是新位置，原文件在 skills/base.py
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import abc


class SkillCostType(Enum):
    """技能消耗类型"""
    CPU_TOKENS = "cpu_tokens"
    IO_OPS = "io_ops"
    NET_BYTES = "net_bytes"
    MONEY = "money"
    TIME = "time"


@dataclass
class SkillCost:
    """技能执行成本"""
    cpu_tokens: int = 0
    io_ops: int = 0
    net_bytes: int = 0
    money: float = 0.0
    time_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu_tokens": self.cpu_tokens,
            "io_ops": self.io_ops,
            "net_bytes": self.net_bytes,
            "money": self.money,
            "time_seconds": self.time_seconds,
        }

    def __add__(self, other):
        return SkillCost(
            cpu_tokens=self.cpu_tokens + other.cpu_tokens,
            io_ops=self.io_ops + other.io_ops,
            net_bytes=self.net_bytes + other.net_bytes,
            money=self.money + other.money,
            time_seconds=self.time_seconds + other.time_seconds,
        )


@dataclass
class SkillResult:
    """技能执行结果"""
    success: bool
    message: str                          # 结果描述
    data: Optional[Dict[str, Any]] = None  # 结果数据
    cost: SkillCost = field(default_factory=SkillCost)
    error: Optional[str] = None            # 错误信息
    can_continue: bool = True              # 是否可以继续执行

    def to_llm_message(self) -> str:
        """转换为给 LLM 的消息"""
        if self.success:
            msg = f"✓ {self.message}"
            if self.data:
                # 简化数据展示
                if isinstance(self.data, dict):
                    items = [f"{k}: {v}" for k, v in list(self.data.items())[:5]]
                    msg += f"\n  数据: {', '.join(items)}"
            return msg
        else:
            return f"✗ {self.message}" + (f"\n  错误: {self.error}" if self.error else "")


class BaseSkill(abc.ABC):
    """技能基类

    技能是 LLM 可以直接调用的工具，真正干活的模块。

    设计原则：
    1. 每个技能只做一件事，做好一件事
    2. 输入输出清晰，易于 LLM 理解
    3. 提供成本估算，用于预算控制
    4. 支持异步执行（如果需要）
    """

    def __init__(self, name: str, description: str):
        """初始化技能

        Args:
            name: 技能名称
            description: 技能描述（给 LLM 理解）
        """
        self.name = name
        self.description = description
        self._usage_count = 0
        self._success_count = 0

    @abc.abstractmethod
    def execute(self, **kwargs) -> SkillResult:
        """执行技能

        Args:
            **kwargs: 技能参数

        Returns:
            SkillResult: 执行结果
        """
        pass

    @abc.abstractmethod
    def estimate_cost(self, **kwargs) -> SkillCost:
        """估算执行成本

        Args:
            **kwargs: 技能参数

        Returns:
            SkillCost: 估算的成本
        """
        pass

    @abc.abstractmethod
    def get_parameters_schema(self) -> Dict[str, Any]:
        """获取参数模式

        返回参数的结构描述，用于生成工具定义。

        Returns:
            参数模式字典
        """
        pass

    def can_execute(self, **kwargs) -> tuple[bool, Optional[str]]:
        """检查是否可以执行

        Args:
            **kwargs: 技能参数

        Returns:
            (是否可以执行, 原因)
        """
        # 默认实现：总是可以执行
        return True, None

    def get_usage_stats(self) -> Dict[str, Any]:
        """获取使用统计"""
        success_rate = 0.0
        if self._usage_count > 0:
            success_rate = self._success_count / self._usage_count

        return {
            "name": self.name,
            "usage_count": self._usage_count,
            "success_count": self._success_count,
            "success_rate": success_rate,
        }

    def _record_usage(self, success: bool):
        """记录使用"""
        self._usage_count += 1
        if success:
            self._success_count += 1

    def __repr__(self) -> str:
        return f"Skill({self.name})"


class SkillRegistry:
    """技能注册表

    管理所有可用的技能，提供查询和调用接口。
    """

    def __init__(self):
        self._skills: Dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill):
        """注册技能"""
        self._skills[skill.name] = skill

    def get(self, name: str) -> Optional[BaseSkill]:
        """获取技能"""
        return self._skills.get(name)

    def list_all(self) -> List[BaseSkill]:
        """列出所有技能"""
        return list(self._skills.values())

    def get_names(self) -> List[str]:
        """获取所有技能名称"""
        return list(self._skills.keys())

    def execute(self, name: str, **kwargs) -> SkillResult:
        """执行技能

        Args:
            name: 技能名称
            **kwargs: 技能参数

        Returns:
            SkillResult: 执行结果
        """
        skill = self.get(name)
        if not skill:
            return SkillResult(
                success=False,
                message=f"技能不存在: {name}",
                error=f"Unknown skill: {name}",
                can_continue=True
            )

        # 检查是否可以执行
        can_execute, reason = skill.can_execute(**kwargs)
        if not can_execute:
            return SkillResult(
                success=False,
                message=f"技能 {name} 无法执行",
                error=reason,
                can_continue=True
            )

        # 执行技能
        result = skill.execute(**kwargs)
        skill._record_usage(result.success)

        return result

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """获取所有技能的参数模式

        用于生成 LLM 工具定义。

        Returns:
            技能定义列表
        """
        schemas = []
        for skill in self.list_all():
            schemas.append({
                "name": skill.name,
                "description": skill.description,
                "parameters": skill.get_parameters_schema(),
            })
        return schemas
