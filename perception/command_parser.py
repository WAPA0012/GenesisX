"""
Command Parser: Active Command Detection and Parsing

Extracts and parses:
- User commands from input text
- Tool invocations
- Goals and constraints

References:
- 代码大纲架构 perception/command_parser.py
- Deterministic parsing for replay
"""

from typing import Dict, Any, List, Optional
import re
from enum import Enum


class CommandType(str, Enum):
    """Types of commands"""
    TOOL_CALL = "tool_call"
    GOAL_SET = "goal_set"
    QUERY = "query"
    FEEDBACK = "feedback"
    META = "meta"  # System commands like /reset, /save
    UNKNOWN = "unknown"


class Command:
    """Parsed command structure"""

    def __init__(
        self,
        command_type: CommandType,
        raw_text: str,
        tool_id: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        goal: Optional[str] = None,
        priority: float = 0.5,
    ):
        self.command_type = command_type
        self.raw_text = raw_text
        self.tool_id = tool_id
        self.parameters = parameters or {}
        self.goal = goal
        self.priority = priority

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for serialization"""
        return {
            "command_type": self.command_type.value,
            "raw_text": self.raw_text,
            "tool_id": self.tool_id,
            "parameters": self.parameters,
            "goal": self.goal,
            "priority": self.priority,
        }


class CommandParser:
    """
    Deterministic command parser for replay.

    Extracts commands from user input using regex patterns.
    """

    def __init__(self):
        # Tool call patterns
        self.tool_patterns = [
            r"use\s+(\w+)\s+tool",
            r"call\s+(\w+)",
            r"execute\s+(\w+)",
            r"run\s+(\w+)",
        ]

        # Goal setting patterns
        self.goal_patterns = [
            r"goal:\s*(.+)",
            r"objective:\s*(.+)",
            r"I want to\s+(.+)",
            r"please\s+(.+)",
        ]

        # Meta command patterns (system commands)
        self.meta_patterns = [
            r"^/(\w+)(?:\s+(.*))?$",  # /command args
        ]

    @staticmethod
    def _is_float(value: str) -> bool:
        """Check if string represents a valid float number.

        修复：更严格的浮点数检测，避免接受 "123." 这类格式

        Args:
            value: String to check

        Returns:
            True if value is a valid float
        """
        try:
            float(value)
            # 检查是否有小数点，且小数点后和前都有数字
            if '.' in value:
                parts = value.split('.')
                # 确保小数点前后都有数字
                return len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit()
            return False
        except ValueError:
            return False

    def parse(self, text: str) -> List[Command]:
        """
        Parse text into list of commands.

        Args:
            text: Input text

        Returns:
            List of parsed commands
        """
        commands = []

        # Check for meta commands first
        meta_cmd = self._parse_meta_command(text)
        if meta_cmd:
            commands.append(meta_cmd)
            return commands

        # Check for tool calls
        tool_cmd = self._parse_tool_call(text)
        if tool_cmd:
            commands.append(tool_cmd)

        # Check for goal setting
        goal_cmd = self._parse_goal(text)
        if goal_cmd:
            commands.append(goal_cmd)

        # If no specific command found, treat as query
        if not commands:
            commands.append(Command(
                command_type=CommandType.QUERY,
                raw_text=text,
                priority=0.5,
            ))

        return commands

    def _parse_tool_call(self, text: str) -> Optional[Command]:
        """Parse tool call from text"""
        text_lower = text.lower()

        for pattern in self.tool_patterns:
            match = re.search(pattern, text_lower)
            if match:
                tool_id = match.group(1)

                # Try to extract parameters
                params = self._extract_parameters(text)

                return Command(
                    command_type=CommandType.TOOL_CALL,
                    raw_text=text,
                    tool_id=tool_id,
                    parameters=params,
                    priority=0.7,
                )

        return None

    def _parse_goal(self, text: str) -> Optional[Command]:
        """Parse goal setting from text"""
        for pattern in self.goal_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                goal_text = match.group(1).strip()

                return Command(
                    command_type=CommandType.GOAL_SET,
                    raw_text=text,
                    goal=goal_text,
                    priority=0.8,
                )

        return None

    def _parse_meta_command(self, text: str) -> Optional[Command]:
        """Parse meta/system command"""
        text = text.strip()

        for pattern in self.meta_patterns:
            match = re.match(pattern, text)
            if match:
                command_name = match.group(1)
                args_str = match.group(2) if len(match.groups()) > 1 else ""

                params = {}
                if args_str:
                    # Simple key=value parsing
                    for arg in args_str.split():
                        if "=" in arg:
                            k, v = arg.split("=", 1)
                            params[k] = v

                return Command(
                    command_type=CommandType.META,
                    raw_text=text,
                    tool_id=command_name,
                    parameters=params,
                    priority=1.0,
                )

        return None

    def _extract_parameters(self, text: str) -> Dict[str, Any]:
        """
        Extract parameters from text.

        Simple implementation: look for key=value or key:value patterns.
        """
        params = {}

        # Pattern: key=value or key:value
        param_pattern = r'(\w+)[:=]\s*(["\']?)([^"\'=:,\s]+)\2'

        for match in re.finditer(param_pattern, text):
            key = match.group(1)
            value = match.group(3)

            # Try to convert to appropriate type
            if value.isdigit():
                value = int(value)
            # 修复：改进浮点数检测，避免接受 "123." 这类格式
            elif self._is_float(value):
                value = float(value)
            elif value.lower() in ["true", "false"]:
                value = value.lower() == "true"

            params[key] = value

        return params

    def is_active_command(self, text: str) -> bool:
        """
        Check if text contains an active command (not just passive query).

        Args:
            text: Input text

        Returns:
            True if active command detected
        """
        commands = self.parse(text)

        if not commands:
            return False

        # Active commands are anything other than simple queries
        for cmd in commands:
            if cmd.command_type != CommandType.QUERY:
                return True

        # Check for imperative verbs
        imperative_verbs = [
            "create", "build", "make", "write", "update", "delete",
            "run", "execute", "start", "stop", "save", "load",
            "analyze", "calculate", "generate", "find", "search"
        ]

        text_lower = text.lower()
        for verb in imperative_verbs:
            if re.search(rf'\b{verb}\b', text_lower):
                return True

        return False
