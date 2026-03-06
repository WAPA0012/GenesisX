"""Observer - collects observations from environment."""
from typing import List, Dict, Any, Optional
from common.models import Observation


def observe_environment(tick: int, mode: str, state: Dict[str, Any], user_input: Optional[str] = None) -> List[Observation]:
    """Observe the environment and collect observations.

    Args:
        tick: Current tick number
        mode: Current mode (work/friend/sleep)
        state: Current state dict
        user_input: Optional user input string

    Returns:
        List of observations
    """
    observations = []

    # 如果有用户输入，优先添加用户对话观察
    if user_input:
        observations.append(Observation(
            type="user_chat",
            payload={"message": user_input, "source": "user"},
            source_ref="user",
            tick=tick,
        ))

    # Always add a heartbeat observation
    observations.append(Observation(
        type="heartbeat",
        payload={"tick": tick, "mode": mode},
        tick=tick,
    ))

    # Add body state observation
    observations.append(Observation(
        type="body_state",
        payload={
            "energy": state.get("energy", 0.5),
            "mood": state.get("mood", 0.5),
            "stress": state.get("stress", 0.0),
            "fatigue": state.get("fatigue", 0.0),
        },
        tick=tick,
    ))

    return observations
