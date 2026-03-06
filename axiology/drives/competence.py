"""Competence Drive - 胜任力驱动力

提供胜任力驱动力信号，告诉 LLM "想要提升能力"。

这是价值系统的一部分，对应价值维度：competence
"""
from typing import Dict, Any, List, Set
from .base import BaseDrive, DriveSignal


class CompetenceDrive(BaseDrive):
    """胜任力驱动力

    驱动数字生命去提升能力、掌握技能、完成挑战。
    对应价值维度：competence
    """

    def __init__(self):
        super().__init__(
            name="胜任力",
            value_dimension="competence"
        )
        self._active_goals: List[str] = []
        self._mastered_skills: Set[str] = set()

    def generate_drive_signal(
        self,
        state: Dict[str, Any],
        context: Dict[str, Any]
    ) -> DriveSignal:
        """生成胜任力驱动力信号"""
        gaps = state.get("gaps", {})
        gap = gaps.get("competence", 0.0)
        weights = state.get("weights", {})
        weight = weights.get("competence", 0.25)
        mood = state.get("mood", 0.5)
        energy = state.get("energy", 0.5)
        stress = state.get("stress", 0.0)

        # 计算强度
        base_intensity = gap * weight
        mood_bonus = mood * 0.2
        goal_bonus = len(self._active_goals) * 0.1
        stress_penalty = stress * 0.15

        intensity = min(1.0, max(0.0, base_intensity + mood_bonus + goal_bonus - stress_penalty))

        # 生成描述
        if intensity > 0.7:
            if self._active_goals:
                description = f"强烈渴望提升能力，想要攻克当前的挑战和目标: {', '.join(self._active_goals[:2])}"
            else:
                description = "想要掌握新技能，寻找有意义的挑战"
        elif intensity > 0.4:
            if self._active_goals:
                description = f"有明确的目标，想要一步步提升能力"
            else:
                description = "愿意学习新东西，对自己的成长有兴趣"
        elif intensity > 0.2:
            description = "如果有合适的挑战，愿意尝试一下"
        else:
            if len(self._mastered_skills) > 3:
                description = "最近掌握了一些技能，暂时满足于当前水平"
            else:
                description = "当前对能力提升的需求较低"

        signal = DriveSignal(
            name=self.name,
            intensity=intensity,
            description=description,
            context={
                "gap": gap,
                "weight": weight,
                "active_goals": self._active_goals.copy(),
                "mastered_skills": len(self._mastered_skills),
            },
            priority=weight * intensity
        )

        self._last_signal = signal
        return signal

    def set_active_goals(self, goals: list):
        """设置当前活跃的目标"""
        self._active_goals = goals

    def add_active_goal(self, goal: str):
        """添加一个活跃目标"""
        if goal not in self._active_goals:
            self._active_goals.append(goal)

    def remove_active_goal(self, goal: str):
        """移除一个活跃目标"""
        if goal in self._active_goals:
            self._active_goals.remove(goal)

    def record_achievement(self, skill: str):
        """记录一次成就"""
        self._mastered_skills.add(skill)
