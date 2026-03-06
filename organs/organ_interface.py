"""Organ Interface - Unified interface for organ execution.

Implements:
- Signal processing through organs
- Tool execution via organs
- Risk assessment
- Mode restrictions (online/offline)
- Execution tracking
"""

from typing import Dict, Any, Optional
from collections import defaultdict

from .base_organ import BaseOrgan
from .internal.mind_organ import MindOrgan
from .internal.caretaker_organ import CaretakerOrgan
from .internal.scout_organ import ScoutOrgan
from .internal.builder_organ import BuilderOrgan
from .internal.archivist_organ import ArchivistOrgan
from .internal.immune_organ import ImmuneOrgan


class OrganInterface:
    """Unified interface for organ execution and management."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize organ interface.

        Args:
            config: Configuration dictionary
        """
        self.config = config

        # Initialize available organs
        self.organs: Dict[str, BaseOrgan] = {
            "mind": MindOrgan(),
            "caretaker": CaretakerOrgan(),
            "scout": ScoutOrgan(),
            "builder": BuilderOrgan(),
            "archivist": ArchivistOrgan(),
            "immune": ImmuneOrgan(),
        }

        # Execution tracking
        self.execution_counts = defaultdict(int)
        self.last_results = {}

        # Risk thresholds (default 0.75 blocks CRITICAL risk tools)
        self.max_risk_online = config.get("tools", {}).get("max_risk_online", 0.75)
        self.max_risk_offline = config.get("tools", {}).get("max_risk_offline", 0.3)

        # Risk assessment rules
        self.tool_risks = {
            "web_search": 0.2,
            "web_fetch": 0.3,
            "file_read": 0.4,
            "file_write": 0.7,
            "code_exec": 0.9,
            "shell_exec": 1.0,
        }

    def process_signal(
        self,
        organ_id: str,
        signal: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process signal through specified organ.

        Args:
            organ_id: Organ to use
            signal: Input signal
            context: Optional context

        Returns:
            Processing result with output and success status
        """
        if organ_id not in self.organs:
            return {
                "success": False,
                "error": f"Unknown organ: {organ_id}",
            }

        organ = self.organs[organ_id]

        try:
            # Track execution
            self.execution_counts[organ_id] += 1

            # Convert signal to state/context format
            state = signal.copy()
            ctx = context or {}

            # Use organ's propose_actions method
            actions = organ.propose_actions(state, ctx)

            # Store result
            result = {
                "proposed_actions": actions,
                "action_count": len(actions),
            }
            self.last_results[organ_id] = result

            return {
                "success": True,
                "output": result,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def execute_action(
        self,
        organ_id: str,
        action: Dict[str, Any],
        is_offline: bool = False,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute action through specified organ.

        Args:
            organ_id: Organ to use
            action: Action to execute (tool_id, parameters)
            is_offline: Whether in offline mode
            context: Optional context

        Returns:
            Execution result
        """
        if organ_id not in self.organs:
            return {
                "success": False,
                "error": f"Unknown organ: {organ_id}",
            }

        # Assess risk
        risk_score = self.assess_risk(action)

        # Check mode restrictions
        max_risk = self.max_risk_offline if is_offline else self.max_risk_online

        if risk_score > max_risk:
            mode = "offline" if is_offline else "online"
            return {
                "success": False,
                "error": f"Action blocked: risk {risk_score:.2f} exceeds {mode} limit {max_risk:.2f}",
            }

        # Execute through organ
        organ = self.organs[organ_id]

        try:
            # Track execution
            self.execution_counts[organ_id] += 1

            # Convert action to state/context format for propose_actions
            state = {"action_request": action}
            ctx = context or {}

            # Use organ's propose_actions method
            actions = organ.propose_actions(state, ctx)

            # Store result
            result = {
                "proposed_actions": actions,
                "action_count": len(actions),
            }
            self.last_results[organ_id] = result

            return {
                "success": True,
                "output": result,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def assess_risk(self, action: Dict[str, Any]) -> float:
        """Assess risk level of an action.

        Args:
            action: Action to assess

        Returns:
            Risk score [0, 1]
        """
        tool_id = action.get("tool_id", "")

        # Check predefined risk levels
        if tool_id in self.tool_risks:
            base_risk = self.tool_risks[tool_id]
        else:
            # Unknown tools have medium risk
            base_risk = 0.5

        # Adjust based on parameters
        params = action.get("parameters", {})

        # File operations on system paths are riskier
        if "path" in params:
            path = str(params["path"])
            if any(sys_path in path for sys_path in ["/system", "C:\\Windows", "/etc"]):
                base_risk = min(1.0, base_risk + 0.3)

        # Code/shell execution with certain patterns is riskier
        if "code" in params or "command" in params:
            code = str(params.get("code", "") or params.get("command", ""))
            if any(dangerous in code for dangerous in ["rm -rf", "del /f", "format"]):
                base_risk = 1.0

        return base_risk

    def get_organ_stats(self, organ_id: str) -> Dict[str, Any]:
        """Get execution statistics for an organ.

        Args:
            organ_id: Organ to query

        Returns:
            Stats dictionary
        """
        if organ_id not in self.organs:
            return {}

        return {
            "execution_count": self.execution_counts.get(organ_id, 0),
            "last_result": self.last_results.get(organ_id),
            "organ_type": type(self.organs[organ_id]).__name__,
        }

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get stats for all organs.

        Returns:
            Dict of organ_id -> stats
        """
        return {
            organ_id: self.get_organ_stats(organ_id)
            for organ_id in self.organs
        }

    def reset_stats(self):
        """Reset execution statistics."""
        self.execution_counts.clear()
        self.last_results.clear()
