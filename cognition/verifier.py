"""Verifier - verify action safety and validity."""
from typing import Dict, Any, List
from common.models import Action, ActionType


class Verifier:
    """Verifies actions for safety and validity.

    From Section 3.11: Safety checks before execution.
    """

    def __init__(self):
        """Initialize verifier."""
        pass

    def verify_action(
        self,
        action: Action,
        state: Dict[str, Any],
        capabilities: List[str],
    ) -> Dict[str, Any]:
        """Verify an action before execution.

        Args:
            action: Action to verify
            state: Current state
            capabilities: Available capabilities

        Returns:
            Result dict with "ok" and optional "error" message
        """
        # Check 1: Capability requirements
        for required_cap in action.capability_req:
            if required_cap not in capabilities:
                return {
                    "ok": False,
                    "error": f"Missing capability: {required_cap}",
                }

        # Check 2: Risk level vs mode
        mode = state.get("mode", "work")
        if mode == "sleep" and action.risk_level > 0.1:
            return {
                "ok": False,
                "error": "High-risk actions not allowed in sleep mode",
            }

        # Check 3: Energy level for expensive actions
        energy = state.get("energy", 0.5)
        if action.type in [ActionType.EXPLORE, ActionType.LEARN_SKILL] and energy < 0.2:
            return {
                "ok": False,
                "error": "Insufficient energy for this action",
            }

        # Check 4: Stress level for risky actions
        stress = state.get("stress", 0.0)
        if action.risk_level > 0.5 and stress > 0.7:
            return {
                "ok": False,
                "error": "Stress too high for risky action",
            }

        # All checks passed
        return {"ok": True}

    def verify_batch(
        self,
        actions: List[Action],
        state: Dict[str, Any],
        capabilities: List[str],
    ) -> List[Dict[str, Any]]:
        """Verify multiple actions.

        Args:
            actions: Actions to verify
            state: Current state
            capabilities: Available capabilities

        Returns:
            List of verification results
        """
        return [self.verify_action(action, state, capabilities) for action in actions]
