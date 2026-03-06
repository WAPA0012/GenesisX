"""Organ Selector - Dynamic organ differentiation system.

Implements Paper Section 3.8: 动态器官分化
Selects appropriate organ based on:
- Signal type
- Current stage (child/adult/elder)
- Current mode (work/rest/play)
- Urgency level
"""

from typing import Dict, Any, Optional
import random


class OrganSelector:
    """Selects appropriate organ based on context and signal."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize organ selector.

        Args:
            config: Configuration dictionary
        """
        self.config = config

        # 修复 M51: 使用独立的 Random 实例并设置种子，保证可复现性
        seed = config.get("random_seed", 42)
        self._rng = random.Random(seed)

        # Available organs
        self.available_organs = {
            "caretaker": True,
            "immune": True,
            "mind": True,
            "scout": True,
            "builder": True,
            "archivist": True,
        }

        # Signal type to organ mapping
        self.signal_to_organ = {
            "homeostasis_low": "caretaker",
            "threat": "immune",
            "task": "mind",
            "exploration": "scout",
            "build": "builder",
            "memory_consolidation": "archivist",
        }

        # Stage preferences (child/adult/elder)
        self.stage_preferences = {
            "child": {
                "scout": 1.5,  # Higher exploration
                "mind": 0.8,
                "builder": 1.2,
            },
            "adult": {
                "mind": 1.3,  # Higher productivity
                "builder": 1.3,
                "scout": 1.0,
            },
            "elder": {
                "archivist": 1.5,  # More reflection
                "mind": 1.2,
                "caretaker": 1.2,
            },
        }

        # Mode preferences (work/rest/play)
        self.mode_preferences = {
            "work": {
                "mind": 1.5,
                "builder": 1.4,
                "scout": 1.0,
                "caretaker": 0.5,
                "archivist": 0.5,
            },
            "rest": {
                "caretaker": 2.0,
                "archivist": 1.8,
                "mind": 0.3,
                "builder": 0.3,
                "scout": 0.3,
                "immune": 0.5,
            },
            "play": {
                "scout": 1.5,
                "builder": 1.2,
                "mind": 0.8,
                "caretaker": 0.6,
            },
        }

    def select_organ(
        self,
        signal: Dict[str, Any],
        stage: str = "adult",
        mode: str = "work"
    ) -> str:
        """Select appropriate organ for signal.

        Args:
            signal: Input signal with type, value, urgency
            stage: Life stage (child/adult/elder)
            mode: Current mode (work/rest/play)

        Returns:
            Organ ID (e.g., "mind", "scout", "caretaker")
        """
        # Check urgency - high urgency overrides normal selection
        urgency = signal.get("urgency", 0.0)
        if urgency > 0.8:
            return self._select_urgent_organ(signal)

        # For rest mode, prioritize rest-appropriate organs
        # regardless of signal type
        if mode == "rest":
            return self._select_by_context(signal, stage, mode)

        # Direct mapping from signal type (only for non-rest modes)
        signal_type = signal.get("type", "task")
        if signal_type in self.signal_to_organ:
            candidate = self.signal_to_organ[signal_type]
            if self.available_organs.get(candidate, False):
                return candidate

        # Otherwise, select based on stage and mode preferences
        return self._select_by_context(signal, stage, mode)

    def _select_urgent_organ(self, signal: Dict[str, Any]) -> str:
        """Select organ for urgent signals.

        Args:
            signal: Urgent signal

        Returns:
            Organ ID for urgent handling
        """
        signal_type = signal.get("type", "")

        # Threat -> Immune
        if "threat" in signal_type:
            if self.available_organs.get("immune", False):
                return "immune"

        # Homeostasis crisis -> Caretaker
        if "homeostasis" in signal_type or signal.get("value", 1.0) < 0.3:
            if self.available_organs.get("caretaker", False):
                return "caretaker"

        # Default to Mind for urgent unknown signals
        if self.available_organs.get("mind", False):
            return "mind"

        # Fallback to any available organ
        return self._get_any_available_organ()

    def _select_by_context(
        self,
        signal: Dict[str, Any],
        stage: str,
        mode: str
    ) -> str:
        """Select organ based on stage and mode context.

        Args:
            signal: Input signal
            stage: Life stage
            mode: Current mode

        Returns:
            Selected organ ID
        """
        # Calculate scores for each organ
        scores = {}

        for organ_id in self.available_organs:
            if not self.available_organs[organ_id]:
                continue

            score = 1.0

            # Apply stage preference
            stage_prefs = self.stage_preferences.get(stage, {})
            score *= stage_prefs.get(organ_id, 1.0)

            # Apply mode preference
            mode_prefs = self.mode_preferences.get(mode, {})
            score *= mode_prefs.get(organ_id, 1.0)

            # Add some randomness for exploration (修复 M51: 使用可复现的 RNG)
            score *= (0.8 + self._rng.random() * 0.4)

            scores[organ_id] = score

        # Select organ with highest score
        if not scores:
            return self._get_any_available_organ()

        selected = max(scores.items(), key=lambda x: x[1])
        return selected[0]

    def _get_any_available_organ(self) -> str:
        """Get any available organ as fallback.

        Returns:
            First available organ ID
        """
        for organ_id, available in self.available_organs.items():
            if available:
                return organ_id

        # Absolute fallback
        return "mind"

    def set_organ_availability(self, organ_id: str, available: bool):
        """Enable or disable an organ.

        Args:
            organ_id: Organ to modify
            available: Whether organ is available
        """
        if organ_id in self.available_organs:
            self.available_organs[organ_id] = available

    def get_available_organs(self) -> Dict[str, bool]:
        """Get current organ availability.

        Returns:
            Dict of organ_id -> available
        """
        return self.available_organs.copy()
