"""Field store for bounded scalar state variables.

Implements automatic clipping and type-safe access for body/affect fields.
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class BoundedScalar:
    """A scalar value with automatic bounds clipping."""

    value: float
    min_val: float = 0.0
    max_val: float = 1.0

    def __post_init__(self):
        if self.min_val >= self.max_val:
            raise ValueError(f"min_val ({self.min_val}) must be less than max_val ({self.max_val})")
        # Clip initial value to bounds
        self.value = max(self.min_val, min(self.max_val, self.value))

    def set(self, new_value: float) -> float:
        """Set value with automatic clipping."""
        self.value = max(self.min_val, min(self.max_val, new_value))
        return self.value

    def get(self) -> float:
        """Get current value."""
        return self.value

    def increment(self, delta: float) -> float:
        """Increment value (with clipping)."""
        return self.set(self.value + delta)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "value": self.value,
            "min": self.min_val,
            "max": self.max_val,
        }


class Valence(BoundedScalar):
    """A value in [-1, 1] range (e.g., for signed emotions)."""

    def __init__(self, value: float = 0.0):
        super().__init__(value=value, min_val=-1.0, max_val=1.0)


class Prob(BoundedScalar):
    """A probability value in [0, 1] range."""

    def __init__(self, value: float = 0.5):
        super().__init__(value=value, min_val=0.0, max_val=1.0)


class FieldStore:
    """Central store for all bounded scalar fields.

    Provides type-safe access to:
    - Energy (E_t)
    - Mood_t
    - Stress_t
    - Fatigue_t
    - Bond_t
    - Trust_t
    - Boredom_t

    All fields are automatically clipped on write.
    """

    def __init__(self):
        """Initialize default fields."""
        self.fields: Dict[str, BoundedScalar] = {
            "energy": Prob(0.8),
            "mood": Prob(0.5),
            "stress": Prob(0.2),
            "fatigue": Prob(0.1),
            "bond": Prob(0.0),
            "trust": Prob(0.5),
            "boredom": Prob(0.0),
            "curiosity": Prob(0.5),  # 好奇心字段
        }

    def get(self, name: str, default: float = None) -> float:
        """Get field value.

        Args:
            name: Field name
            default: Default value if field not found (optional)

        Returns:
            Field value or default if not found
        """
        if name not in self.fields:
            if default is not None:
                return default
            raise KeyError(f"Field '{name}' not found")
        return self.fields[name].get()

    def set(self, name: str, value: float) -> float:
        """Set field value (with clipping)."""
        if name not in self.fields:
            raise KeyError(f"Field '{name}' not found")
        return self.fields[name].set(value)

    def increment(self, name: str, delta: float) -> float:
        """Increment field (with clipping)."""
        if name not in self.fields:
            raise KeyError(f"Field '{name}' not found")
        return self.fields[name].increment(delta)

    def snapshot(self) -> Dict[str, float]:
        """Get snapshot of all field values."""
        return {name: field.get() for name, field in self.fields.items()}

    def to_dict(self) -> Dict[str, Any]:
        """Serialize all fields to dict."""
        return {name: field.to_dict() for name, field in self.fields.items()}

    def from_dict(self, data: Dict[str, Any]):
        """Restore fields from dict."""
        for name, field_data in data.items():
            if name in self.fields:
                if isinstance(field_data, dict):
                    self.fields[name].set(field_data.get("value", 0.5))
                else:
                    self.fields[name].set(field_data)
