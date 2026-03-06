"""
Modulation: Affect-Driven Behavior Modulation

Affect (Mood/Stress) modulates decision-making:
- Exploration rate
- Planning depth K
- Reflection trigger threshold
- Risk tolerance

References:
- 论文 3.6 Affect via RPE - modulation section
- 代码大纲 affect/modulation.py
"""

from typing import Dict, Any


class AffectModulation:
    """
    Modulates behavior based on affective state (Mood/Stress).

    High mood → more exploration, deeper planning
    Low mood → more cautious, shallower planning
    High stress → trigger reflection, reduce risk tolerance

    NOTE: This module expects mood in [0, 1] range to be consistent with
    GlobalState and the rest of the system. The internal modulation logic
    converts [0, 1] to [-1, 1] for calculating modulation effects.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Modulation parameters
        self.exploration_mood_factor = config.get("exploration_mood_factor", 0.5)
        self.planning_depth_mood_factor = config.get("planning_depth_mood_factor", 2)
        self.risk_stress_factor = config.get("risk_stress_factor", 0.3)
        self.reflection_stress_threshold = config.get("reflection_stress_threshold", 0.7)

        # Base values (to be modulated)
        self.base_exploration_rate = config.get("base_exploration_rate", 0.1)
        self.base_planning_depth = config.get("base_planning_depth", 3)
        self.base_risk_tolerance = config.get("base_risk_tolerance", 0.5)

    def _normalize_mood(self, mood: float) -> float:
        """
        Normalize mood from [0, 1] to [-1, 1] for modulation calculations.

        Args:
            mood: Mood value in [0, 1] range (0 = very negative, 1 = very positive)

        Returns:
            Normalized mood in [-1, 1] range for modulation
        """
        # Map [0, 1] to [-1, 1]: 0 → -1, 0.5 → 0, 1 → 1
        return (mood - 0.5) * 2.0

    def modulate_exploration(self, mood: float, base_rate: float = None) -> float:
        """
        Modulate exploration rate based on mood.

        High mood → higher exploration (willing to try new things)
        Low mood → lower exploration (stick to known strategies)

        Args:
            mood: Current mood in [0, 1] (0 = very negative, 1 = very positive)
            base_rate: Base exploration rate (or use default)

        Returns:
            Modulated exploration rate [0, 1]
        """
        if base_rate is None:
            base_rate = self.base_exploration_rate

        # Normalize mood to [-1, 1] for modulation calculation
        mood_norm = self._normalize_mood(mood)

        # Map normalized mood [-1, 1] to multiplier [0.5, 1.5]
        # mood_norm = 1 → multiplier = 1 + factor
        # mood_norm = 0 → multiplier = 1
        # mood_norm = -1 → multiplier = 1 - factor
        multiplier = 1.0 + mood_norm * self.exploration_mood_factor

        modulated_rate = base_rate * multiplier

        # Clamp to [0, 1]
        return max(0.0, min(1.0, modulated_rate))

    def modulate_planning_depth(self, mood: float, base_depth: int = None) -> int:
        """
        Modulate planning depth based on mood.

        High mood → deeper planning (more optimistic about future)
        Low mood → shallower planning (focus on immediate concerns)

        Args:
            mood: Current mood in [0, 1] (0 = very negative, 1 = very positive)
            base_depth: Base planning depth (or use default)

        Returns:
            Modulated planning depth (integer)
        """
        if base_depth is None:
            base_depth = self.base_planning_depth

        # Normalize mood to [-1, 1] for modulation calculation
        mood_norm = self._normalize_mood(mood)

        # Map normalized mood to depth adjustment
        # mood_norm = 1 → +planning_depth_mood_factor steps
        # mood_norm = -1 → -planning_depth_mood_factor steps
        adjustment = int(mood_norm * self.planning_depth_mood_factor)

        modulated_depth = base_depth + adjustment

        # Clamp to [1, 10]
        return max(1, min(10, modulated_depth))

    def modulate_risk_tolerance(self, stress: float, base_tolerance: float = None) -> float:
        """
        Modulate risk tolerance based on stress.

        High stress → lower risk tolerance (more cautious)
        Low stress → normal risk tolerance

        Args:
            stress: Current stress level [0, 1]
            base_tolerance: Base risk tolerance (or use default)

        Returns:
            Modulated risk tolerance [0, 1]
        """
        if base_tolerance is None:
            base_tolerance = self.base_risk_tolerance

        # High stress reduces risk tolerance
        # stress = 1 → multiplier = 1 - risk_stress_factor
        # stress = 0 → multiplier = 1
        multiplier = 1.0 - stress * self.risk_stress_factor

        modulated_tolerance = base_tolerance * multiplier

        # Clamp to [0, 1]
        return max(0.0, min(1.0, modulated_tolerance))

    def should_trigger_reflection(
        self,
        stress: float,
        meaning_gap: float,
        boredom: float
    ) -> bool:
        """
        Determine if reflection should be triggered.

        Triggers on:
        - High stress (need to process and reduce)
        - High meaning gap (need to make sense of experiences)
        - High boredom (need to find new purpose)

        Args:
            stress: Current stress level [0, 1]
            meaning_gap: Meaning gap value [0, 1]
            boredom: Boredom level [0, 1]

        Returns:
            True if reflection should be triggered
        """
        # Stress-based trigger
        if stress >= self.reflection_stress_threshold:
            return True

        # Meaning gap trigger
        meaning_threshold = self.config.get("reflection_meaning_threshold", 0.6)
        if meaning_gap >= meaning_threshold:
            return True

        # Boredom trigger
        boredom_threshold = self.config.get("reflection_boredom_threshold", 0.7)
        if boredom >= boredom_threshold:
            return True

        return False

    def modulate_temperature(self, stress: float, base_temp: float) -> float:
        """
        Modulate softmax temperature based on stress.

        High stress → lower temperature (more focused on highest priority)
        Low stress → normal temperature (more balanced)

        Args:
            stress: Current stress level [0, 1]
            base_temp: Base temperature parameter

        Returns:
            Modulated temperature (positive)
        """
        # High stress makes decisions more deterministic (lower temp)
        # stress = 1 → temp *= 0.5
        # stress = 0 → temp *= 1.0
        stress_factor = self.config.get("temperature_stress_factor", 0.5)
        multiplier = 1.0 - stress * stress_factor

        modulated_temp = base_temp * multiplier

        # Ensure temperature stays positive and reasonable
        return max(0.1, min(2.0, modulated_temp))

    def modulate_goal_persistence(self, mood: float) -> float:
        """
        Modulate goal persistence based on mood.

        High mood → more persistent (stick with current goal)
        Low mood → less persistent (more likely to switch goals)

        Args:
            mood: Current mood in [0, 1] (0 = very negative, 1 = very positive)

        Returns:
            Goal persistence multiplier [0.5, 1.5]
        """
        # Normalize mood to [-1, 1] for modulation calculation
        mood_norm = self._normalize_mood(mood)

        # mood_norm = 1 → persistence = 1.5 (very persistent)
        # mood_norm = 0 → persistence = 1.0 (normal)
        # mood_norm = -1 → persistence = 0.5 (easily distracted)
        persistence_factor = self.config.get("goal_persistence_factor", 0.5)
        persistence = 1.0 + mood_norm * persistence_factor

        return max(0.5, min(1.5, persistence))

    def get_modulated_params(
        self,
        mood: float,
        stress: float
    ) -> Dict[str, Any]:
        """
        Get all modulated parameters at once.

        Args:
            mood: Current mood [0, 1] (0 = very negative, 1 = very positive)
            stress: Current stress [0, 1]

        Returns:
            Dict of modulated parameters
        """
        return {
            "exploration_rate": self.modulate_exploration(mood),
            "planning_depth": self.modulate_planning_depth(mood),
            "risk_tolerance": self.modulate_risk_tolerance(stress),
            "temperature": self.modulate_temperature(stress, 1.0),
            "goal_persistence": self.modulate_goal_persistence(mood),
        }

    def get_stats(self, mood: float, stress: float) -> Dict[str, Any]:
        """Get modulation statistics"""
        modulated = self.get_modulated_params(mood, stress)

        return {
            "base_exploration": self.base_exploration_rate,
            "modulated_exploration": modulated["exploration_rate"],
            "base_planning_depth": self.base_planning_depth,
            "modulated_planning_depth": modulated["planning_depth"],
            "base_risk_tolerance": self.base_risk_tolerance,
            "modulated_risk_tolerance": modulated["risk_tolerance"],
            "mood": mood,
            "stress": stress,
        }
