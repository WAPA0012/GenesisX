"""Factory functions for creating core system components with configuration.

This module provides convenient factory functions that load configuration
from YAML files and create properly configured system components.

Author: Genesis X Team
"""

from typing import Optional
from pathlib import Path

from .ledger import MetabolicLedger
from .fields import FieldStore
from .slots import SlotStore
from .signals import SignalBus
from ..resource_config import get_resource_config
from common.logger import get_logger

logger = get_logger(__name__)


def create_ledger(
    config_dir: Optional[Path] = None,
    unlimited_resources: Optional[set] = None
) -> MetabolicLedger:
    """创建 MetabolicLedger，从配置文件加载设置.

    Args:
        config_dir: 配置文件目录 (默认: "config")
        unlimited_resources: 可选，覆盖配置文件中的无限资源设置

    Returns:
        配置好的 MetabolicLedger 实例

    Example:
        >>> # 使用默认配置 (cpu_tokens 无限)
        >>> ledger = create_ledger()

        >>> # 覆盖配置，禁用无限模式
        >>> ledger = create_ledger(unlimited_resources=set())
    """
    # 加载资源配置
    resource_config = get_resource_config(config_dir)

    # 如果提供了覆盖设置，使用它
    if unlimited_resources is not None:
        resource_config.unlimited_resources = unlimited_resources

    # 创建预算字典
    budgets = resource_config.budgets.copy()

    # 创建 ledger
    ledger = MetabolicLedger(
        budgets=budgets,
        unlimited_resources=resource_config.unlimited_resources
    )

    # 记录配置
    logger.info(f"Created MetabolicLedger with unlimited resources: {resource_config.unlimited_resources}")
    for resource in resource_config.unlimited_resources:
        logger.info(f"  ✓ {resource}: 无限模式（不检查预算）")

    return ledger


def create_field_store() -> FieldStore:
    """创建 FieldStore."""
    return FieldStore()


def create_slot_store() -> SlotStore:
    """创建 SlotStore."""
    return SlotStore()


def create_signal_bus() -> SignalBus:
    """创建 SignalBus."""
    return SignalBus()


def create_all_stores(
    config_dir: Optional[Path] = None,
    unlimited_resources: Optional[set] = None
) -> dict:
    """创建所有核心存储组件.

    Args:
        config_dir: 配置文件目录
        unlimited_resources: 覆盖无限资源设置

    Returns:
        包含所有存储组件的字典
    """
    return {
        "ledger": create_ledger(config_dir, unlimited_resources),
        "fields": create_field_store(),
        "slots": create_slot_store(),
        "signals": create_signal_bus(),
    }
