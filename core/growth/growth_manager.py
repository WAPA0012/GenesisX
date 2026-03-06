"""Growth Manager - 成长管理器

统一管理成长系统的所有功能：
- 肢体生成 → 肢体 (Limb)
- 容器构建
- 能力学习
- 技能获取

新架构 (v2.0):
- 生成的肢体自动转换为 Limb
- 注册到 UnifiedOrganManager

成长 vs 进化：
- 成长：同一个体获取新能力（学习、生成器官）
- 进化：创建新世代（复制、变异、选择）

触发条件：
- 能力缺口检测（想要做但做不到）
- 用户请求（需要新功能）
- 好奇心驱动（探索新领域）
"""
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import json

from common.logger import get_logger
from .limb_generator import LimbGenerator, LimbRequirement, GeneratedLimb, GenerationType
from .limb_builder import LimbBuilder, BuildConfig, BuildResult

# 器官指南管理器
from memory.organ_guide_manager import OrganGuideManager, get_organ_guide_manager

logger = get_logger(__name__)


@dataclass
class GrowthEvent:
    """成长事件记录"""
    timestamp: datetime
    event_type: str  # "limb_generated", "skill_learned", "capability_added"
    description: str
    details: Dict[str, Any] = field(default_factory=dict)


class GrowthManager:
    """成长管理器

    负责协调成长系统的各个组件，提供统一的成长接口。

    新架构 (v2.0):
    - 生成的肢体自动转换为 Limb
    - 注册到 UnifiedOrganManager

    使用方式：
        growth_manager = GrowthManager(organ_manager, llm_client, config)

        # 检测能力缺口并成长
        growth_manager.check_and_grow(context)

        # 直接生成器官
        success, organ = growth_manager.generate_limb(requirement)

        # 获取成长历史
        history = growth_manager.get_growth_history()
    """

    def __init__(
        self,
        organ_manager,
        llm_client=None,
        config: Dict[str, Any] = None,
        plugin_manager=None,
        unified_organ_manager=None,  # 新增：统一器官管理器
    ):
        """初始化成长管理器

        Args:
            organ_manager: 器官管理器（旧版，向后兼容）
            llm_client: LLM 客户端（用于代码生成）
            config: 配置
            plugin_manager: 插件管理器（作为学习参考，可选）
            unified_organ_manager: 统一器官管理器（新版，可选）
        """
        self.organ_manager = organ_manager
        self.llm_client = llm_client
        self.config = config or {}
        self.plugin_manager = plugin_manager
        self.unified_organ_manager = unified_organ_manager

        # 器官指南管理器（自动生成使用说明）
        self.organ_guide_manager = get_organ_guide_manager()

        # 初始化子组件
        self.limb_generator = LimbGenerator(
            organ_manager=organ_manager,
            llm_client=llm_client,
            config=self.config,
            plugin_manager=plugin_manager  # 传递插件管理器用于学习参考
        )
        self.limb_builder = LimbBuilder(
            config=BuildConfig(
                python_version=self.config.get("python_version", "3.11"),
                base_image=self.config.get("base_image", "python:3.11-slim"),
            )
        ) if self.config.get("enable_docker", False) else None

        # 成长历史
        self._growth_history: List[GrowthEvent] = []

        # 已获取的能力
        self._acquired_capabilities: Dict[str, Any] = {}

        # 成长统计
        self._stats = {
            "limbs_generated": 0,
            "skills_learned": 0,
            "capabilities_added": 0,
            "containers_deployed": 0,
        }

        # 成长开关（可通过配置控制）
        self._growth_enabled = self.config.get("growth_enabled", True)
        self._auto_build = self.config.get("auto_build_containers", False)
        self._auto_deploy = self.config.get("auto_deploy", False)

        logger.info("GrowthManager initialized")

    def check_and_grow(self, context: Dict[str, Any]) -> Optional[GrowthEvent]:
        """检测成长需求并自动成长

        从上下文中分析是否需要获取新能力，如果需要则自动触发成长。

        Args:
            context: 当前上下文（包含 observations, drive_signals 等）

        Returns:
            成长事件，如果没有成长则返回 None
        """
        if not self._growth_enabled:
            return None

        # 1. 从肢体生成器识别需求
        requirement = self.limb_generator.identify_requirement(context)
        if requirement:
            success, limb = self.generate_limb(requirement)
            if success and limb:
                return GrowthEvent(
                    timestamp=datetime.now(timezone.utc),
                    event_type="limb_generated",
                    description=f"生成了新肢体: {limb.name}",
                    details={
                        "limb_name": limb.name,
                        "capabilities": limb.capabilities,
                        "generation_type": limb.generation_type.value,
                    }
                )

        # 2. 从驱动力信号中检测学习需求
        drive_signals = context.get("drive_signals", {})
        competence_signal = drive_signals.get("competence")
        if competence_signal and competence_signal.intensity > 0.8:
            # 强烈的胜任力需求可能需要学习新技能
            target = competence_signal.context.get("target_domain")
            if target:
                event = self._try_learn_skill(target, context)
                if event:
                    return event

        return None

    def generate_limb(
        self,
        requirement: LimbRequirement,
        build_container: bool = None
    ) -> Tuple[bool, Optional[GeneratedLimb]]:
        """生成肢体

        自主成长：使用 LLM 动态生成代码。
        如需预制插件，请使用 PluginManager。

        Args:
            requirement: 肢体需求
            build_container: 是否构建容器（None 表示使用配置默认值）

        Returns:
            (是否成功, 生成的肢体)
        """
        if not self._growth_enabled:
            logger.warning("Growth is disabled")
            return False, None

        logger.info(f"开始生成肢体: {requirement.name}")

        # 使用肢体生成器生成（LLM 自主生成）
        success, limb = self.limb_generator.generate_limb(requirement)

        if not success or not limb:
            logger.warning(f"肢体生成失败: {requirement.name}")
            return False, None

        # 记录能力
        for cap in limb.capabilities:
            self._acquired_capabilities[cap] = {
                "source": "limb",
                "limb_name": limb.name,
                "acquired_at": datetime.now(timezone.utc).isoformat(),
            }

        # 构建容器（如果启用）
        if build_container is None:
            build_container = self._auto_build

        if build_container and self.limb_builder and limb.requirements:
            build_result = self.limb_builder.build_limb(
                limb_name=limb.name,
                code=limb.code,
                requirements=limb.requirements,
                dockerfile_content=limb.dockerfile
            )

            if build_result.success:
                self._stats["containers_deployed"] += 1
                logger.info(f"肢体容器构建成功: {limb.name}")

                # 自动部署（如果启用）
                if self._auto_deploy:
                    success, container_id = self.limb_builder.deploy_limb(
                        build_result.image_name,
                        build_result.image_tag
                    )
                    if success:
                        logger.info(f"肢体已部署: {container_id}")

        # 新架构：注册到统一器官管理器
        if self.unified_organ_manager:
            from organs import Limb, OrganType
            limb_organ = Limb(
                name=limb.name,
                code=limb.code,
                capabilities=limb.capabilities,
                description=requirement.description,
                generation_prompt=requirement.description,
                organ_type=OrganType.INTERNAL if limb.generation_type == GenerationType.INTERNAL else OrganType.EXTERNAL,
                config=limb.parameters,
            )
            self.unified_organ_manager.add_limb(limb_organ)
            logger.info(f"已将肢体注册到器官管理器: {limb.name}")

        # 注册器官使用指南（存入记忆系统）
        self.organ_guide_manager.register_organ_guide(
            name=limb.name,
            organ_type="limb",
            description=requirement.description,
            capabilities=limb.capabilities,
            usage_examples=requirement.examples if hasattr(requirement, 'examples') else None,
        )
        logger.info(f"已为肢体生成使用指南: {limb.name}")

        # 更新统计
        self._stats["limbs_generated"] += 1
        self._stats["capabilities_added"] += len(limb.capabilities)

        # 记录成长事件
        event = GrowthEvent(
            timestamp=datetime.now(timezone.utc),
            event_type="limb_generated",
            description=f"生成了新肢体: {limb.name}",
            details={
                "limb_name": limb.name,
                "capabilities": limb.capabilities,
                "generation_type": limb.generation_type.value,
            }
        )
        self._growth_history.append(event)

        logger.info(f"肢体生成成功: {limb.name}, 能力: {limb.capabilities}")
        return True, limb

    def _try_learn_skill(
        self,
        skill_name: str,
        context: Dict[str, Any]
    ) -> Optional[GrowthEvent]:
        """尝试学习技能

        Args:
            skill_name: 技能名称
            context: 当前上下文

        Returns:
            成长事件，如果学习失败则返回 None
        """
        # 检查是否已经拥有该技能
        if skill_name in self._acquired_capabilities:
            return None

        # 创建肢体需求
        requirement = LimbRequirement(
            name=skill_name,
            description=f"学习 {skill_name} 技能",
            capabilities=[skill_name],
            generation_type=GenerationType.INTERNAL,
            examples=[f"使用 {skill_name}"],
        )

        success, limb = self.generate_limb(requirement)
        if success and limb:
            self._stats["skills_learned"] += 1
            return GrowthEvent(
                timestamp=datetime.now(timezone.utc),
                event_type="skill_learned",
                description=f"学习了新技能: {skill_name}",
                details={"skill_name": skill_name}
            )

        return None

    # ========================================================================
    # V32 风格便捷方法
    # ========================================================================

    def devour(self, target_path: str, **kwargs) -> Dict[str, Any]:
        """吞噬 - 读取文件或目录内容

        Args:
            target_path: 目标路径
            **kwargs: 额外参数

        Returns:
            吞噬结果
        """
        return self.limb_generator.devour(target_path, **kwargs)

    def grow(self, task_description: str, llm_func: callable = None, **kwargs) -> Tuple[bool, str, Optional[str]]:
        """生长 - 根据任务生成代码

        Args:
            task_description: 任务描述
            llm_func: LLM 调用函数
            **kwargs: 额外参数

        Returns:
            (success, filepath_or_error, code)
        """
        if llm_func is None:
            llm_func = self._default_llm_func

        if llm_func is None:
            return False, "LLM function not provided", None

        return self.limb_generator.grow_limb_v32(task_description, llm_func, **kwargs)

    def flex(self, filepath: str, **kwargs) -> Tuple[bool, str, Optional[str]]:
        """挥舞 - 执行生成的代码

        Args:
            filepath: 代码文件路径
            **kwargs: 额外参数

        Returns:
            (success, output, error)
        """
        return self.limb_generator.flex_limb_v32(filepath, **kwargs)

    def _default_llm_func(self, prompt: str, system: str, temperature: float) -> str:
        """默认 LLM 调用函数"""
        if self.llm_client:
            # 尝试调用 LLM 客户端
            try:
                if hasattr(self.llm_client, 'generate'):
                    return self.llm_client.generate(prompt, system, temperature)
                elif hasattr(self.llm_client, 'chat'):
                    return self.llm_client.chat(prompt, system)
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
        return ""

    # ========================================================================
    # 查询方法
    # ========================================================================

    def get_acquired_capabilities(self) -> Dict[str, Any]:
        """获取已获取的能力"""
        return self._acquired_capabilities.copy()

    def has_capability(self, capability: str) -> bool:
        """检查是否拥有某能力"""
        return capability in self._acquired_capabilities

    def get_growth_history(self, limit: int = 10) -> List[GrowthEvent]:
        """获取成长历史

        Args:
            limit: 最大返回数量

        Returns:
            成长事件列表
        """
        return self._growth_history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """获取成长统计"""
        return {
            **self._stats,
            "acquired_capabilities_count": len(self._acquired_capabilities),
            "growth_events_count": len(self._growth_history),
            "growth_enabled": self._growth_enabled,
        }

    def set_growth_enabled(self, enabled: bool):
        """启用/禁用成长"""
        self._growth_enabled = enabled
        logger.info(f"Growth {'enabled' if enabled else 'disabled'}")

    def save_state(self, filepath: Path = None):
        """保存成长状态

        Args:
            filepath: 保存路径
        """
        if filepath is None:
            filepath = Path("artifacts/growth_state.json")

        filepath.parent.mkdir(parents=True, exist_ok=True)

        state = {
            "stats": self._stats,
            "acquired_capabilities": self._acquired_capabilities,
            "growth_history": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "event_type": e.event_type,
                    "description": e.description,
                    "details": e.details,
                }
                for e in self._growth_history
            ],
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

        logger.info(f"Growth state saved to {filepath}")

    def load_state(self, filepath: Path = None):
        """加载成长状态

        Args:
            filepath: 状态文件路径
        """
        if filepath is None:
            filepath = Path("artifacts/growth_state.json")

        if not filepath.exists():
            return

        with open(filepath, 'r', encoding='utf-8') as f:
            state = json.load(f)

        self._stats = state.get("stats", self._stats)
        self._acquired_capabilities = state.get("acquired_capabilities", {})

        for e in state.get("growth_history", []):
            self._growth_history.append(GrowthEvent(
                timestamp=datetime.fromisoformat(e["timestamp"]),
                event_type=e["event_type"],
                description=e["description"],
                details=e["details"],
            ))

        logger.info(f"Growth state loaded from {filepath}")


def create_growth_manager(
    organ_manager,
    llm_client=None,
    config: Dict[str, Any] = None,
    plugin_manager=None,
    unified_organ_manager=None
) -> GrowthManager:
    """创建成长管理器

    Args:
        organ_manager: 器官管理器
        llm_client: LLM 客户端
        config: 配置
        plugin_manager: 插件管理器（作为学习参考，可选）
        unified_organ_manager: 统一器官管理器（新版，可选）

    Returns:
        GrowthManager 实例
    """
    return GrowthManager(organ_manager, llm_client, config, plugin_manager, unified_organ_manager)
