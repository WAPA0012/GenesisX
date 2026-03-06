"""
Tool Call Logger: tool_calls.jsonl Writer with Audit Trail

Logs all tool calls with:
- Input/output hashes
- Model version and parameters
- Cost/latency/risk assessment
- Optional data redaction

References:
- 代码大纲架构 persistence/tool_call_log.py
- 论文 3.11.3 可复现性: Deterministic Tool & Replay
"""

from pathlib import Path
from typing import Dict, Any, Optional
import orjson
import hashlib
import os
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class ToolCallSchema(BaseModel):
    """Schema for tool call records"""
    tick: int
    session_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Tool identification
    tool_id: str
    tool_type: str = "unknown"

    # Input/output
    input_params: Dict[str, Any] = Field(default_factory=dict)
    input_hash: str = ""
    output: Any = None
    output_hash: str = ""

    # Execution metadata
    model_id: Optional[str] = None
    model_version: Optional[str] = None
    model_params: Dict[str, Any] = Field(default_factory=dict)  # temperature, top_p, etc.

    # Cost and performance
    cost: Dict[str, float] = Field(default_factory=dict)
    latency_ms: float = 0.0
    risk_score: float = 0.0

    # Status
    success: bool = True
    error: Optional[str] = None

    # Redaction flag
    redacted: bool = False


class ToolCallLogger:
    """
    JSONL logger for tool calls with audit trail.

    Supports:
    - Hashing inputs/outputs for replay
    - Data redaction for sensitive info
    - Cost and risk tracking
    """

    def __init__(self, log_path: Path, enable_redaction: bool = False):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.enable_redaction = enable_redaction

        if not self.log_path.exists():
            self.log_path.touch()

    def log_tool_call(
        self,
        tick: int,
        session_id: str,
        tool_id: str,
        input_params: Dict[str, Any],
        output: Any,
        model_id: Optional[str] = None,
        model_version: Optional[str] = None,
        model_params: Optional[Dict[str, Any]] = None,
        cost: Optional[Dict[str, float]] = None,
        latency_ms: float = 0.0,
        risk_score: float = 0.0,
        success: bool = True,
        error: Optional[str] = None,
    ):
        """
        Log a tool call.

        Args:
            tick: Tick number
            session_id: Session ID
            tool_id: Tool identifier
            input_params: Tool input parameters
            output: Tool output
            model_id: LLM model ID (if applicable)
            model_version: Model version
            model_params: Model parameters (temperature, etc.)
            cost: Cost breakdown
            latency_ms: Execution latency
            risk_score: Risk assessment score
            success: Whether call succeeded
            error: Error message if failed
        """
        # Hash inputs/outputs for replay
        input_hash = self._hash_dict(input_params)
        output_hash = self._hash_dict(output)

        # Redact if enabled
        redacted_input = input_params
        redacted_output = output
        if self.enable_redaction:
            redacted_input = self._redact_sensitive(input_params)
            redacted_output = self._redact_sensitive(output)

        # Create record
        record = ToolCallSchema(
            tick=tick,
            session_id=session_id,
            tool_id=tool_id,
            input_params=redacted_input,
            input_hash=input_hash,
            output=redacted_output,
            output_hash=output_hash,
            model_id=model_id,
            model_version=model_version,
            model_params=model_params or {},
            cost=cost or {},
            latency_ms=latency_ms,
            risk_score=risk_score,
            success=success,
            error=error,
            redacted=self.enable_redaction,
        )

        # Write to log
        # Use model_dump() for Pydantic v2 compatibility, fallback to dict() for v1
        try:
            data = record.model_dump()
        except AttributeError:
            data = record.dict()

        json_line = orjson.dumps(
            data,
            option=orjson.OPT_APPEND_NEWLINE
        )

        with open(self.log_path, 'ab') as f:
            f.write(json_line)
            f.flush()
            os.fsync(f.fileno())

    def read_all_tool_calls(self) -> list:
        """Read all tool calls from log"""
        if not self.log_path.exists():
            return []

        calls = []
        with open(self.log_path, 'rb') as f:
            for line in f:
                if line.strip():
                    call = orjson.loads(line)
                    calls.append(call)

        return calls

    def get_tool_calls_for_tick(self, tick: int) -> list:
        """Get all tool calls for a specific tick"""
        all_calls = self.read_all_tool_calls()
        return [c for c in all_calls if c.get('tick') == tick]

    @staticmethod
    def _hash_dict(obj: Any) -> str:
        """Hash an object for replay matching"""
        serialized = orjson.dumps(
            obj,
            option=orjson.OPT_SORT_KEYS
        )
        return hashlib.sha256(serialized).hexdigest()[:16]

    @staticmethod
    def _redact_sensitive(obj: Any) -> Any:
        """
        Redact sensitive information.

        Simple implementation: replace API keys, passwords, etc.
        """
        if isinstance(obj, dict):
            redacted = {}
            for k, v in obj.items():
                if any(sensitive in k.lower() for sensitive in ['key', 'password', 'token', 'secret']):
                    redacted[k] = "[REDACTED]"
                else:
                    redacted[k] = ToolCallLogger._redact_sensitive(v)
            return redacted
        elif isinstance(obj, list):
            return [ToolCallLogger._redact_sensitive(item) for item in obj]
        else:
            return obj
