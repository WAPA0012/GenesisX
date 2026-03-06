"""Capability Router - 能力路由器

统一技能和器官的调用，对 LLM 来说透明。
"""
from typing import Dict, Any, List, Optional, Tuple
from memory.skills import SkillRegistry
from organs import OrganManager
from memory.skills.base import SkillResult
from organs.base_organ import CapabilityResult


class CapabilityRouter:
    """能力路由器

    统一管理技能和器官的能力调用，对 LLM 提供统一的接口。

    功能：
    1. 自动判断用技能还是器官
    2. 提供统一的调用接口
    3. 支持能力发现和查询
    4. 触发进化系统（当能力不足时）

    路由优先级：
    1. 原生技能（独立能力，无需器官）
    2. 器官使用技能（如 use_gimp，调用对应器官）
    3. 直接器官能力（如 "裁剪"，路由到 gimp 器官）
    4. 触发进化（都不存在时）
    """

    def __init__(self, skill_registry: SkillRegistry = None, organ_manager: OrganManager = None, evolution_system=None):
        """初始化能力路由器

        Args:
            skill_registry: 技能注册表
            organ_manager: 器官管理器
            evolution_system: 进化系统（可选）
        """
        self.skill_registry = skill_registry or SkillRegistry()
        self.organ_manager = organ_manager or OrganManager()
        self.evolution_system = evolution_system

    # ==================== 统一调用接口 ====================

    def execute(self, capability_name: str, **kwargs) -> Dict[str, Any]:
        """执行能力（统一入口）

        自动判断用技能还是器官，对 LLM 完全透明。

        路由逻辑：
        1. 检查是否是原生技能（如 file_skill）
        2. 检查是否是器官使用技能（如 use_gimp）
        3. 检查是否是器官能力（如 "裁剪" → gimp器官）
        4. 都没有则提示进化

        Args:
            capability_name: 能力名称
            **kwargs: 能力参数

        Returns:
            执行结果（统一格式）
        """
        # 1. 先找原生技能
        if self.skill_registry.get_names() and capability_name in self.skill_registry.get_names():
            skill_result = self.skill_registry.execute(capability_name, **kwargs)
            return self._skill_result_to_dict(skill_result)

        # 2. 再找器官能力（包括器官使用技能和直接能力）
        if self.organ_manager.has_capability(capability_name):
            organ_result = self.organ_manager.execute_capability(capability_name, **kwargs)
            return self._organ_result_to_dict(organ_result)

        # 3. 都没有 - 检查是否可以触发进化
        if self.evolution_system and self._should_trigger_evolution(capability_name):
            return {
                "success": False,
                "message": f"能力不存在，但可以触发进化获取: {capability_name}",
                "error": f"Capability not found: {capability_name}",
                "suggest_evolution": True,
                "evolution_capable": True,
                "requested_capability": capability_name,
            }

        # 4. 真的没有此能力
        return {
            "success": False,
            "message": f"能力不存在: {capability_name}",
            "error": f"Capability not found: {capability_name}",
            "suggest_evolution": False,
        }

    def _should_trigger_evolution(self, capability_name: str) -> bool:
        """检查是否应该触发进化

        只有当能力看起来是可以通过吞噬软件获得时才触发。
        """
        # 检查是否在软件仓库的候选能力中
        if not self.evolution_system:
            return False

        repo_capabilities = set()
        for manifest in self.evolution_system._software_repo.values():
            repo_capabilities.update(manifest.capabilities)
            repo_capabilities.add(manifest.name)

        return capability_name.lower() in {c.lower() for c in repo_capabilities}

    # ==================== 能力发现 ====================

    def list_all_capabilities(self) -> List[Dict[str, Any]]:
        """列出所有可用能力

        Returns:
            能力定义列表
        """
        capabilities = []

        # 技能能力
        for skill in self.skill_registry.list_all():
            capabilities.append({
                "name": skill.name,
                "description": skill.description,
                "type": "skill",
                "parameters": skill.get_parameters_schema(),
            })

        # 器官能力
        for organ_name in self.organ_manager.get_mounted_organs():
            organ_info = self.organ_manager.get_organ_info(organ_name)
            for cap_name in organ_info.get("capabilities", []):
                capabilities.append({
                    "name": cap_name,
                    "description": f"来自 {organ_name} 器官",
                    "type": "organ",
                    "organ": organ_name,
                })

        return capabilities

    def get_capability_schema(self) -> List[Dict[str, Any]]:
        """获取能力模式（用于 LLM function calling）

        Returns:
            OpenAI function calling 格式的工具定义列表
        """
        schemas = []

        # 技能模式
        for skill in self.skill_registry.list_all():
            schemas.append({
                "type": "function",
                "function": {
                    "name": skill.name,
                    "description": skill.description,
                    "parameters": skill.get_parameters_schema(),
                }
            })

        # 器官能力模式（简化）
        for organ_name in self.organ_manager.get_mounted_organs():
            organ_info = self.organ_manager.get_organ_info(organ_name)
            for cap_name in organ_info.get("capabilities", []):
                schemas.append({
                    "type": "function",
                    "function": {
                        "name": cap_name,
                        "description": f"来自 {organ_name} 器官的能力",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string", "description": "具体操作"},
                            },
                        },
                    }
                })

        return schemas

    # ==================== 格式转换 ====================

    def _skill_result_to_dict(self, result: SkillResult) -> Dict[str, Any]:
        """转换技能结果为统一格式"""
        return {
            "success": result.success,
            "message": result.message,
            "data": result.data,
            "error": result.error,
            "type": "skill",
        }

    def _organ_result_to_dict(self, result: CapabilityResult) -> Dict[str, Any]:
        """转换器官结果为统一格式"""
        return {
            "success": result.success,
            "message": result.message,
            "data": result.data,
            "error": result.error,
            "type": "organ",
        }

    # ==================== 状态查询 ====================

    def get_stats(self) -> Dict[str, Any]:
        """获取路由器状态"""
        skill_names = self.skill_registry.get_names()
        mounted_organs = self.organ_manager.get_mounted_organs()

        return {
            "total_skills": len(skill_names),
            "skills": skill_names,
            "total_mounted_organs": len(mounted_organs),
            "mounted_organs": mounted_organs,
            "total_capabilities": len(self.list_all_capabilities()),
        }

    def format_for_llm(self) -> str:
        """格式化为给 LLM 的能力描述

        Returns:
            能力描述文本
        """
        lines = ["## 可用能力\n"]

        # 技能
        if self.skill_registry.get_names():
            lines.append("### 技能（轻量级能力）")
            for skill in self.skill_registry.list_all():
                lines.append(f"- **{skill.name}**: {skill.description}")
            lines.append("")

        # 器官
        mounted_organs = self.organ_manager.get_mounted_organs()
        if mounted_organs:
            lines.append("### 器官（挂载的能力）")
            for organ_name in mounted_organs:
                organ_info = self.organ_manager.get_organ_info(organ_name)
                caps = organ_info.get("capabilities", [])
                lines.append(f"- **{organ_name}**: {', '.join(caps)}")
            lines.append("")

        return "\n".join(lines)


# 全局单例
_global_router: Optional[CapabilityRouter] = None


def get_global_router() -> CapabilityRouter:
    """获取全局能力路由器"""
    global _global_router
    if _global_router is None:
        _global_router = CapabilityRouter()
    return _global_router
