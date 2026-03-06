"""Organ Guide Manager - 器官使用指南管理器

自动管理和生成器官使用指南。

器官类型：
- limb: 肢体（LLM 生成的）
- plugin: 插件（预制安装的）
- builtin: 内置器官（代码写死的）

使用指南存储在 memory/limb_guides/ 目录下，
AI 可以通过记忆检索查询"我有什么器官，怎么用"。
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import json

from common.logger import get_logger

logger = get_logger(__name__)


@dataclass
class OrganGuide:
    """器官使用指南"""
    name: str                           # 器官名称
    organ_type: str                     # 器官类型: limb/plugin/builtin
    description: str                    # 功能描述
    capabilities: List[str]             # 能力列表
    usage_examples: List[str]           # 使用示例
    parameters: Dict[str, Any] = field(default_factory=dict)  # 参数说明
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "organ_type": self.organ_type,
            "description": self.description,
            "capabilities": self.capabilities,
            "usage_examples": self.usage_examples,
            "parameters": self.parameters,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def to_llm_prompt(self) -> str:
        """转换为给 LLM 的提示词"""
        caps = ", ".join(self.capabilities) if self.capabilities else "无特定能力"
        examples = "\n".join(f"  - {ex}" for ex in self.usage_examples) if self.usage_examples else "  - 直接调用即可"

        return f"""## {self.name} ({self.organ_type})

{self.description}

**能力**: {caps}

**使用示例**:
{examples}
"""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OrganGuide":
        """从字典创建"""
        return cls(
            name=data["name"],
            organ_type=data["organ_type"],
            description=data["description"],
            capabilities=data.get("capabilities", []),
            usage_examples=data.get("usage_examples", []),
            parameters=data.get("parameters", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(timezone.utc),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(timezone.utc),
        )


class OrganGuideManager:
    """器官使用指南管理器

    负责：
    1. 为新器官自动生成使用指南
    2. 存储和检索指南
    3. 提供格式化的指南给 LLM

    使用方式：
        manager = OrganGuideManager()

        # 成长系统生成新肢体时
        manager.register_organ_guide(
            name="web_scraper",
            organ_type="limb",
            description="网页数据抓取工具",
            capabilities=["fetch_url", "parse_html", "extract_data"],
            usage_examples=["用 fetch_url 获取网页", "用 extract_data 提取数据"]
        )

        # 获取所有指南（给 LLM 用）
        guides = manager.get_all_guides_prompt()
    """

    def __init__(self, guides_dir: Path = None):
        """初始化

        Args:
            guides_dir: 指南存储目录，默认为 memory/limb_guides/data/
        """
        if guides_dir is None:
            guides_dir = Path(__file__).parent / "limb_guides" / "data"

        self.guides_dir = Path(guides_dir)
        self.guides_dir.mkdir(parents=True, exist_ok=True)

        # 内存缓存
        self._guides: Dict[str, OrganGuide] = {}

        # 加载已有指南
        self._load_guides()

        logger.info(f"OrganGuideManager initialized with {len(self._guides)} guides")

    def _load_guides(self):
        """从磁盘加载指南"""
        guides_file = self.guides_dir / "organ_guides.json"
        if not guides_file.exists():
            return

        try:
            with open(guides_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for name, guide_data in data.items():
                self._guides[name] = OrganGuide.from_dict(guide_data)

            logger.info(f"Loaded {len(self._guides)} organ guides from disk")

        except Exception as e:
            logger.error(f"Failed to load organ guides: {e}")

    def _save_guides(self):
        """保存指南到磁盘"""
        guides_file = self.guides_dir / "organ_guides.json"

        try:
            data = {name: guide.to_dict() for name, guide in self._guides.items()}

            with open(guides_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.debug(f"Saved {len(self._guides)} organ guides to disk")

        except Exception as e:
            logger.error(f"Failed to save organ guides: {e}")

    def register_organ_guide(
        self,
        name: str,
        organ_type: str,
        description: str,
        capabilities: List[str],
        usage_examples: List[str] = None,
        parameters: Dict[str, Any] = None,
    ) -> bool:
        """注册器官使用指南

        Args:
            name: 器官名称
            organ_type: 器官类型 (limb/plugin/builtin)
            description: 功能描述
            capabilities: 能力列表
            usage_examples: 使用示例
            parameters: 参数说明

        Returns:
            是否成功
        """
        # 生成使用示例（如果没有提供）
        if usage_examples is None:
            usage_examples = self._generate_usage_examples(name, capabilities)

        guide = OrganGuide(
            name=name,
            organ_type=organ_type,
            description=description,
            capabilities=capabilities,
            usage_examples=usage_examples,
            parameters=parameters or {},
        )

        self._guides[name] = guide
        self._save_guides()

        logger.info(f"Registered organ guide: {name} ({organ_type})")
        return True

    def _generate_usage_examples(self, name: str, capabilities: List[str]) -> List[str]:
        """自动生成使用示例

        Args:
            name: 器官名称
            capabilities: 能力列表

        Returns:
            使用示例列表
        """
        examples = []

        for cap in capabilities[:5]:  # 最多5个示例
            # 根据能力名称生成简单示例
            if "get" in cap.lower() or "fetch" in cap.lower():
                examples.append(f"使用 {cap} 获取数据")
            elif "post" in cap.lower() or "send" in cap.lower():
                examples.append(f"使用 {cap} 发送数据")
            elif "read" in cap.lower():
                examples.append(f"使用 {cap} 读取内容")
            elif "write" in cap.lower():
                examples.append(f"使用 {cap} 写入内容")
            elif "process" in cap.lower() or "analyze" in cap.lower():
                examples.append(f"使用 {cap} 处理数据")
            elif "search" in cap.lower() or "query" in cap.lower():
                examples.append(f"使用 {cap} 搜索信息")
            else:
                examples.append(f"使用 {cap} 执行操作")

        if not examples:
            examples.append(f"调用 {name} 执行相关操作")

        return examples

    def update_organ_guide(
        self,
        name: str,
        description: str = None,
        capabilities: List[str] = None,
        usage_examples: List[str] = None,
        parameters: Dict[str, Any] = None,
    ) -> bool:
        """更新器官使用指南

        Args:
            name: 器官名称
            description: 新描述
            capabilities: 新能力列表
            usage_examples: 新使用示例
            parameters: 新参数说明

        Returns:
            是否成功
        """
        if name not in self._guides:
            logger.warning(f"Organ guide not found: {name}")
            return False

        guide = self._guides[name]

        if description:
            guide.description = description
        if capabilities:
            guide.capabilities = capabilities
        if usage_examples:
            guide.usage_examples = usage_examples
        if parameters:
            guide.parameters = parameters

        guide.updated_at = datetime.now(timezone.utc)
        self._save_guides()

        logger.info(f"Updated organ guide: {name}")
        return True

    def remove_organ_guide(self, name: str) -> bool:
        """移除器官使用指南

        Args:
            name: 器官名称

        Returns:
            是否成功
        """
        if name not in self._guides:
            return False

        del self._guides[name]
        self._save_guides()

        logger.info(f"Removed organ guide: {name}")
        return True

    def get_guide(self, name: str) -> Optional[OrganGuide]:
        """获取单个指南

        Args:
            name: 器官名称

        Returns:
            指南，如果不存在返回 None
        """
        return self._guides.get(name)

    def get_all_guides(self) -> List[OrganGuide]:
        """获取所有指南"""
        return list(self._guides.values())

    def get_guides_by_type(self, organ_type: str) -> List[OrganGuide]:
        """按类型获取指南

        Args:
            organ_type: 器官类型 (limb/plugin/builtin)

        Returns:
            指南列表
        """
        return [g for g in self._guides.values() if g.organ_type == organ_type]

    def get_all_guides_prompt(self) -> str:
        """获取所有指南的 LLM 提示词

        Returns:
            格式化的指南文本
        """
        if not self._guides:
            return "# 器官使用指南\n\n暂无已注册的器官。"

        sections = ["# 器官使用指南\n"]
        sections.append("以下是你可以使用的器官/肢体/插件：\n")

        # 按类型分组
        for organ_type in ["builtin", "limb", "plugin"]:
            guides = self.get_guides_by_type(organ_type)
            if guides:
                type_names = {
                    "builtin": "内置器官",
                    "limb": "肢体",
                    "plugin": "插件",
                }
                sections.append(f"\n## {type_names.get(organ_type, organ_type)}\n")
                for guide in guides:
                    sections.append(guide.to_llm_prompt())

        return "\n".join(sections)

    def get_capabilities_summary(self) -> str:
        """获取能力摘要

        Returns:
            能力列表文本
        """
        all_caps = set()
        for guide in self._guides.values():
            all_caps.update(guide.capabilities)

        if not all_caps:
            return "暂无能力"

        return ", ".join(sorted(all_caps))

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_guides": len(self._guides),
            "by_type": {
                "builtin": len(self.get_guides_by_type("builtin")),
                "limb": len(self.get_guides_by_type("limb")),
                "plugin": len(self.get_guides_by_type("plugin")),
            },
            "total_capabilities": len(set(
                cap for g in self._guides.values() for cap in g.capabilities
            )),
        }


# 全局单例
_global_guide_manager: Optional[OrganGuideManager] = None


def get_organ_guide_manager() -> OrganGuideManager:
    """获取全局器官指南管理器"""
    global _global_guide_manager
    if _global_guide_manager is None:
        _global_guide_manager = OrganGuideManager()
    return _global_guide_manager
