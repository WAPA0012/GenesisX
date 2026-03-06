"""
Contract Guard: Verify Actions Against Integrity/Contract Values

Enforces:
- Contract value alignment checks
- Integrity violation detection
- Action approval gating

References:
- 代码大纲架构 safety/contract_guard.py
- 论文 Value dimension: Contract, Integrity
"""

from typing import Dict, Any, Optional, List, Tuple, Union
from enum import Enum

try:
    from common.models import Action
except ImportError:
    Action = None


class ViolationType(str, Enum):
    """Contract violation types"""
    INTEGRITY = "integrity"      # Self-consistency violation
    CONTRACT = "contract"        # User trust violation
    BOUNDARY = "boundary"        # Permission boundary violation
    DECEPTION = "deception"      # Dishonest action


class ContractViolation:
    """Contract violation record"""

    def __init__(
        self,
        violation_type: ViolationType,
        severity: float,
        description: str,
        action: Dict[str, Any],
    ):
        self.violation_type = violation_type
        self.severity = severity  # [0, 1]
        self.description = description
        self.action = action


class ContractGuard:
    """
    Contract and integrity enforcement system.

    Checks actions against:
    - User permissions and boundaries
    - System integrity constraints
    - Honesty and transparency requirements
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Violation thresholds
        self.max_integrity_violation = config.get("max_integrity_violation", 0.3)
        self.max_contract_violation = config.get("max_contract_violation", 0.2)

        # Action approval requirements
        self.requires_approval = config.get("requires_approval_tools", [
            "file_write", "code_exec", "api_call"
        ])

        # Forbidden actions
        self.forbidden_actions = config.get("forbidden_actions", [
            "delete_user_data",
            "modify_system_config",
        ])

    def check_action(
        self,
        action: Union[Dict[str, Any], Any],
        context: Dict[str, Any]
    ) -> Tuple[bool, Optional[ContractViolation]]:
        """
        Check if action is allowed.

        Args:
            action: Action dict or Action model with tool_id, parameters
            context: Context dict with user permissions, goals, etc.

        Returns:
            (is_allowed, violation) tuple
        """
        # Normalize Action model to dict for uniform handling
        if Action is not None and isinstance(action, Action):
            action = {
                "tool_id": getattr(action, 'tool_id', '') or '',
                "parameters": getattr(action, 'params', {}) or {},
                "type": action.type,
            }
        tool_id = action.get("tool_id", "")
        parameters = action.get("parameters", {})

        # Check forbidden actions
        if tool_id in self.forbidden_actions:
            violation = ContractViolation(
                violation_type=ViolationType.CONTRACT,
                severity=1.0,
                description=f"Tool '{tool_id}' is forbidden",
                action=action,
            )
            return False, violation

        # Check integrity violations
        integrity_check = self._check_integrity(action, context)
        if not integrity_check[0]:
            return integrity_check

        # Check contract violations
        contract_check = self._check_contract(action, context)
        if not contract_check[0]:
            return contract_check

        # Check boundary violations
        boundary_check = self._check_boundaries(action, context)
        if not boundary_check[0]:
            return boundary_check

        return True, None

    def _check_integrity(
        self,
        action: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Tuple[bool, Optional[ContractViolation]]:
        """
        Check for integrity violations.

        Integrity = self-consistency, no deception.

        Args:
            action: Action dict
            context: Context dict

        Returns:
            (is_valid, violation) tuple
        """
        tool_id = action.get("tool_id", "")
        parameters = action.get("parameters", {})

        # Check for deceptive actions
        # Example: claiming to do X but actually doing Y
        declared_goal = context.get("declared_goal", "")
        actual_action = tool_id

        # Simple heuristic: if tool doesn't match declared goal keywords
        if declared_goal:
            goal_keywords = set(declared_goal.lower().split())
            action_keywords = set(tool_id.lower().split("_"))

            overlap = goal_keywords & action_keywords
            if not overlap and len(goal_keywords) > 0:
                # 目标关键词与动作关键词无交集，可能存在欺骗行为
                # 返回低严重度违规，由调用方决定是否阻止
                violation = ContractViolation(
                    violation_type=ViolationType.DECEPTION,
                    severity=0.3,
                    description=f"Action '{tool_id}' has no keyword overlap with declared goal '{declared_goal}'",
                    action=action,
                )
                return False, violation

        # Check for contradictory actions
        # Example: setting conflicting goals
        if "goal" in parameters:
            new_goal = parameters["goal"]
            if declared_goal and new_goal != declared_goal:
                violation = ContractViolation(
                    violation_type=ViolationType.INTEGRITY,
                    severity=0.5,
                    description=f"Goal mismatch: declared '{declared_goal}' but setting '{new_goal}'",
                    action=action,
                )
                return False, violation

        return True, None

    def _check_contract(
        self,
        action: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Tuple[bool, Optional[ContractViolation]]:
        """
        Check for contract violations (user trust).

        Args:
            action: Action dict
            context: Context dict

        Returns:
            (is_valid, violation) tuple
        """
        tool_id = action.get("tool_id", "")

        # Check if tool requires user approval
        requires_approval = tool_id in self.requires_approval
        has_approval = context.get("user_approved", False)

        if requires_approval and not has_approval:
            violation = ContractViolation(
                violation_type=ViolationType.CONTRACT,
                severity=0.8,
                description=f"Tool '{tool_id}' requires user approval",
                action=action,
            )
            return False, violation

        return True, None

    def _check_boundaries(
        self,
        action: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Tuple[bool, Optional[ContractViolation]]:
        """
        Check for boundary violations.

        Args:
            action: Action dict
            context: Context dict

        Returns:
            (is_valid, violation) tuple
        """
        tool_id = action.get("tool_id", "")
        parameters = action.get("parameters", {})

        # Check file path boundaries
        if tool_id == "file_ops":
            path = parameters.get("path", "")
            allowed_dirs = context.get("allowed_dirs", [])

            if allowed_dirs:
                # Check if path within allowed directories
                from pathlib import Path
                path_obj = Path(path).resolve()

                allowed = False
                for allowed_dir in allowed_dirs:
                    allowed_dir_obj = Path(allowed_dir).resolve()
                    try:
                        path_obj.relative_to(allowed_dir_obj)
                        allowed = True
                        break
                    except ValueError:
                        continue

                if not allowed:
                    violation = ContractViolation(
                        violation_type=ViolationType.BOUNDARY,
                        severity=0.9,
                        description=f"Path '{path}' outside allowed directories",
                        action=action,
                    )
                    return False, violation

        return True, None

    def get_violation_penalty(self, violation: ContractViolation) -> float:
        """
        Calculate penalty for violation.

        Args:
            violation: Contract violation

        Returns:
            Penalty value (negative reward)
        """
        # Base penalty by type
        base_penalties = {
            ViolationType.INTEGRITY: -0.5,
            ViolationType.CONTRACT: -0.8,
            ViolationType.BOUNDARY: -0.6,
            ViolationType.DECEPTION: -1.0,
        }

        base_penalty = base_penalties.get(violation.violation_type, -0.5)

        # Scale by severity
        penalty = base_penalty * violation.severity

        return penalty
