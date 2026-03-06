"""Slot store for working memory.

Implements slots that must be replay-deterministic:
- current_goal
- plans
- milestones
- last_cmd_active
"""
from typing import Dict, Any, Optional, List


class SlotStore:
    """Working memory slots for goal/plan/milestone tracking.

    All slots must be serializable for replay.
    """

    def __init__(self):
        """Initialize empty slots."""
        self.slots: Dict[str, Any] = {
            "current_goal": None,
            "plans": [],
            "milestones": [],
            "last_cmd_active": None,
            "last_user_interaction_tick": None,
        }

    def get(self, slot_name: str, default: Any = None) -> Any:
        """Get slot value."""
        return self.slots.get(slot_name, default)

    def set(self, slot_name: str, value: Any):
        """Set slot value."""
        self.slots[slot_name] = value

    def append(self, slot_name: str, value: Any):
        """Append to list slot."""
        if slot_name not in self.slots:
            self.slots[slot_name] = []
        if not isinstance(self.slots[slot_name], list):
            raise TypeError(f"Slot '{slot_name}' is not a list")
        self.slots[slot_name].append(value)

    def clear(self, slot_name: str):
        """Clear slot value."""
        if slot_name in self.slots:
            if isinstance(self.slots[slot_name], list):
                self.slots[slot_name] = []
            else:
                self.slots[slot_name] = None

    def snapshot(self) -> Dict[str, Any]:
        """Get deep copy snapshot of all slots."""
        import copy
        return copy.deepcopy(self.slots)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize slots to dict."""
        return dict(self.slots)

    def from_dict(self, data: Dict[str, Any]):
        """Restore slots from dict."""
        self.slots.update(data)
