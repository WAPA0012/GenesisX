"""Skill registry - 技能注册表

管理记忆系统中的技能，提供查询和调用接口。

修复：添加线程安全保护。
"""
from typing import Dict, Any, List, Optional
import threading
from .base import BaseSkill, SkillResult


class SkillRegistry:
    """技能注册表

    管理所有可用的技能，提供查询和调用接口。

    修复：添加线程锁保护，防止并发访问问题。
    """

    def __init__(self):
        self._skills: Dict[str, BaseSkill] = {}
        self._lock = threading.RLock()  # 使用可重入锁

    def register(self, skill: BaseSkill):
        """注册技能

        修复：添加线程安全保护。
        """
        with self._lock:
            self._skills[skill.name] = skill

    def get(self, name: str) -> Optional[BaseSkill]:
        """获取技能

        修复：添加线程安全保护。
        """
        with self._lock:
            return self._skills.get(name)

    def list_all(self) -> List[BaseSkill]:
        """列出所有技能

        修复：添加线程安全保护，返回副本防止外部修改。
        """
        with self._lock:
            return list(self._skills.values())

    def get_names(self) -> List[str]:
        """获取所有技能名称

        修复：添加线程安全保护。
        """
        with self._lock:
            return list(self._skills.keys())

    def execute(self, name: str, **kwargs) -> SkillResult:
        """执行技能

        修复：添加线程安全保护。

        Args:
            name: 技能名称
            **kwargs: 技能参数

        Returns:
            SkillResult: 执行结果
        """
        with self._lock:
            skill = self.get(name)
            if not skill:
                return SkillResult(
                    success=False,
                    message=f"技能不存在: {name}",
                    error=f"Unknown skill: {name}",
                    can_continue=True
                )

        # 检查是否可以执行（在锁外执行，避免死锁）
        can_execute, reason = skill.can_execute(**kwargs)
        if not can_execute:
            return SkillResult(
                success=False,
                message=f"技能 {name} 无法执行",
                error=reason,
                can_continue=True
            )

        # 执行技能（在锁外执行，避免死锁）
        result = skill.execute(**kwargs)

        # 记录使用（需要锁保护）
        with self._lock:
            skill._record_usage(result.success)

        return result

    def unregister(self, name: str) -> bool:
        """注销技能

        修复：新增方法，用于移除技能。

        Args:
            name: 技能名称

        Returns:
            是否成功移除
        """
        with self._lock:
            if name in self._skills:
                del self._skills[name]
                return True
            return False

    def clear(self):
        """清空所有技能

        修复：新增方法，用于重置注册表。
        """
        with self._lock:
            self._skills.clear()

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """获取所有技能的参数模式

        用于生成 LLM 工具定义。

        修复：添加线程安全保护。

        Returns:
            技能定义列表
        """
        with self._lock:
            schemas = []
            for skill in self._skills.values():
                schemas.append({
                    "name": skill.name,
                    "description": skill.description,
                    "parameters": skill.get_parameters_schema(),
                })
            return schemas

    def format_for_llm(self) -> str:
        """格式化为给 LLM 的工具描述

        修复：添加线程安全保护。

        Returns:
            工具描述文本
        """
        with self._lock:
            lines = ["## 可用技能\n"]

            for skill in self._skills.values():
                lines.append(f"### {skill.name}")
                lines.append(f"{skill.description}")

                # 显示参数
                params = skill.get_parameters_schema()
                if params.get("properties"):
                    lines.append("**参数:**")
                    for param_name, param_info in params["properties"].items():
                        required = param_name in params.get("required", [])
                        req_mark = " (必需)" if required else " (可选)"
                        lines.append(f"- `{param_name}`{req_mark}: {param_info.get('description', '')}")

                lines.append("")

            return "\n".join(lines)


# 全局单例 - 修复：添加线程锁保护
_global_registry: Optional[SkillRegistry] = None
_global_registry_lock = threading.Lock()


def get_global_registry() -> SkillRegistry:
    """获取全局技能注册表

    修复：添加线程安全保护，防止并发创建多个实例。

    Returns:
        全局唯一的 SkillRegistry 实例
    """
    global _global_registry
    if _global_registry is None:
        with _global_registry_lock:
            # 双重检查锁定模式
            if _global_registry is None:
                _global_registry = SkillRegistry()
    return _global_registry


def reset_global_registry():
    """重置全局技能注册表

    修复：新增方法，用于测试和重置。

    Returns:
        旧的注册表实例
    """
    global _global_registry
    with _global_registry_lock:
        old_registry = _global_registry
        _global_registry = None
        return old_registry
