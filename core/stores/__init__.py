"""Core state stores for Genesis X GA.

Implements the canonical state management system with:
- FieldStore: Bounded scalar fields (E, Mood, Stress, etc.)
- SlotStore: Working memory slots (current_goal, plans, etc.)
- SignalBus: Half-life decay signals
- MetabolicLedger: Resource tracking and budgets (支持无限模式)

Factory functions for creating configured components:
- create_ledger(): 从配置文件创建 MetabolicLedger
- create_all_stores(): 创建所有存储组件
"""

from .fields import FieldStore, BoundedScalar, Valence, Prob
from .slots import SlotStore
from .signals import SignalBus
from .ledger import MetabolicLedger, ResourceBudget
from .factory import (
    create_ledger,
    create_field_store,
    create_slot_store,
    create_signal_bus,
    create_all_stores,
)

__all__ = [
    # Core stores
    "FieldStore",
    "BoundedScalar",
    "Valence",
    "Prob",
    "SlotStore",
    "SignalBus",
    "MetabolicLedger",
    "ResourceBudget",
    # Factory functions
    "create_ledger",
    "create_field_store",
    "create_slot_store",
    "create_signal_bus",
    "create_all_stores",
]
