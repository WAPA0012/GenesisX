"""Context Builder - constructs execution context."""
from typing import Dict, Any, List
from common.models import EpisodeRecord


def build_context(
    state: Dict[str, Any],
    recent_episodes: List[EpisodeRecord],
    retrieved_memories: Dict[str, Any],
) -> Dict[str, Any]:
    """Build execution context for decision making.

    Args:
        state: Current state
        recent_episodes: Recent episode history
        retrieved_memories: Retrieved memories dict with episodes/schemas/skills

    Returns:
        Context dict
    """
    context = {}

    # State summary
    context["state"] = {
        "energy": state.get("energy", 0.5),
        "mood": state.get("mood", 0.5),
        "stress": state.get("stress", 0.0),
        "fatigue": state.get("fatigue", 0.0),
        "boredom": state.get("boredom", 0.0),
        "mode": state.get("mode", "work"),
    }

    # Goal information - convert to string to avoid JSON serialization issues
    current_goal = state.get("current_goal", "")
    if current_goal:
        # 如果是 Goal 对象，提取其描述
        if hasattr(current_goal, "description"):
            context["goal"] = current_goal.description
        elif isinstance(current_goal, str):
            context["goal"] = current_goal
        else:
            context["goal"] = str(current_goal)
    else:
        context["goal"] = ""

    # Recent performance
    if recent_episodes:
        recent_rewards = [ep.reward for ep in recent_episodes[-10:]]
        context["recent_successes"] = sum(1 for r in recent_rewards if r > 0)
        context["recent_attempts"] = len(recent_rewards)
    else:
        context["recent_successes"] = 0
        context["recent_attempts"] = 0

    # === 修复: 添加检索到的记忆到 context ===
    # 这是最重要的修复！让 LLM 能够看到历史对话
    if retrieved_memories:
        # 提取检索到的情节记忆
        retrieved_episodes = retrieved_memories.get("episodes", [])
        if retrieved_episodes:
            # 构建记忆摘要文本
            memory_summary = []
            for ep in retrieved_episodes[:5]:  # 最多 5 条
                if hasattr(ep, 'observation') and ep.observation:
                    obs_text = str(ep.observation.payload) if hasattr(ep.observation, 'payload') else str(ep.observation)
                else:
                    obs_text = "unknown"

                memory_summary.append({
                    "tick": ep.tick,
                    "observation": obs_text[:100] if len(obs_text) > 100 else obs_text,
                    "reward": ep.reward,
                })

            context["retrieved_memories"] = memory_summary
            context["has_memory"] = True
        else:
            context["retrieved_memories"] = []
            context["has_memory"] = False

        # Schema 记忆
        retrieved_schemas = retrieved_memories.get("schemas", [])
        if retrieved_schemas:
            context["retrieved_schemas"] = [
                {"claim": s.claim, "confidence": s.confidence}
                for s in retrieved_schemas[:3]
            ]

        # Skill 记忆
        retrieved_skills = retrieved_memories.get("skills", [])
        if retrieved_skills:
            context["retrieved_skills"] = [
                {"name": s.name, "success_rate": s.success_rate()}
                for s in retrieved_skills[:3]
            ]
    else:
        context["retrieved_memories"] = []
        context["has_memory"] = False

    # Memory counts
    context["episodic_count"] = state.get("episodic_count", 0)
    context["schema_count"] = state.get("schema_count", 0)
    context["skill_count"] = state.get("skill_count", 0)

    # Budget info
    context["budget_tokens"] = 10000  # Default
    context["recent_errors"] = 0  # Simplified

    return context
