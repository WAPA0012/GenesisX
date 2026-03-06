"""
Event Logger: Episodes.jsonl Writer with Schema Validation

Implements append-only episode logging with:
- Schema validation (Pydantic)
- Atomic writes with fsync
- Crash recovery

References:
- 代码大纲架构 persistence/event_log.py
- 论文 3.10.2 每步经验记录
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
import orjson
import os
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone


class EpisodeSchema(BaseModel):
    """
    Schema for episode records.

    Must contain all fields required for replay and analysis.
    """
    tick: int = Field(..., description="Tick number")
    session_id: str = Field(..., description="Session identifier")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Core episode data
    observation: Dict[str, Any] = Field(default_factory=dict)
    action: Dict[str, Any] = Field(default_factory=dict)
    reward: float = Field(..., description="Total reward r_t")
    delta: float = Field(..., description="RPE (TD error)")

    # State snapshot
    state: Dict[str, Any] = Field(default_factory=dict)
    weights: Dict[str, float] = Field(default_factory=dict)
    gaps: Dict[str, float] = Field(default_factory=dict)

    # Goal and context
    goal: Optional[str] = None
    mode: str = "work"
    stage: str = "adult"

    # Cost tracking
    cost: Dict[str, float] = Field(default_factory=dict)

    # Tags for retrieval
    tags: List[str] = Field(default_factory=list)

    @field_validator('weights')
    @classmethod
    def validate_weights_simplex(cls, w):
        """Ensure weights sum to 1 (simplex constraint)"""
        if w:
            total = sum(w.values())
            if not (0.99 <= total <= 1.01):  # Allow small floating point error
                raise ValueError(f"Weights must sum to 1, got {total}")
        return w


class EventLogger:
    """
    Append-only JSONL writer for episodes.

    Features:
    - Schema validation before write
    - Atomic writes with fsync
    - Automatic file creation
    """

    def __init__(self, log_path: Path):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        # Create file if doesn't exist
        if not self.log_path.exists():
            self.log_path.touch()

        self._file_handle = None

    def write_episode(self, episode_data: Dict[str, Any]):
        """
        Write an episode to the log.

        Args:
            episode_data: Episode data dict

        Raises:
            ValueError: If schema validation fails
        """
        # Validate with Pydantic
        episode = EpisodeSchema(**episode_data)

        # Serialize to JSON
        # Use model_dump() for Pydantic v2 compatibility, fallback to dict() for v1
        try:
            data = episode.model_dump()
        except AttributeError:
            data = episode.dict()

        json_line = orjson.dumps(
            data,
            option=orjson.OPT_APPEND_NEWLINE
        )

        # Atomic write
        with open(self.log_path, 'ab') as f:
            f.write(json_line)
            f.flush()
            os.fsync(f.fileno())  # Force write to disk

    def read_all_episodes(self) -> list:
        """
        Read all episodes from log.

        修复：添加对格式错误JSON行的处理。

        Returns:
            List of episode dicts
        """
        if not self.log_path.exists():
            return []

        episodes = []
        with open(self.log_path, 'rb') as f:
            for line_num, line in enumerate(f, 1):
                if line.strip():
                    try:
                        episode = orjson.loads(line)
                        episodes.append(episode)
                    except orjson.JSONDecodeError as e:
                        # 修复：记录但继续处理其他行
                        import warnings
                        warnings.warn(f"Failed to parse JSON at line {line_num}: {e}")
                        continue

        return episodes

    def get_episode_count(self) -> int:
        """Get total number of episodes"""
        if not self.log_path.exists():
            return 0

        count = 0
        with open(self.log_path, 'rb') as f:
            for line in f:
                if line.strip():
                    count += 1
        return count

    def close(self):
        """Close file handle if open"""
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None
