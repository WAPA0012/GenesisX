"""JSONL (JSON Lines) file handling with append-only writes.

For episodes.jsonl and tool_calls.jsonl logging.
"""
try:
    import orjson
except ImportError:
    orjson = None

from pathlib import Path
from typing import Any, Dict, Iterator, Optional
from datetime import datetime


class JSONLWriter:
    """Append-only JSONL writer with fsync for crash recovery."""

    def __init__(self, filepath: Path, fsync: bool = True):
        """Initialize JSONL writer.

        Args:
            filepath: Path to JSONL file
            fsync: Whether to fsync after each write (safer but slower)
        """
        self.filepath = filepath
        self.fsync = fsync
        self._ensure_directory()
        self._file = None

    def _ensure_directory(self):
        """Create parent directory if it doesn't exist."""
        self.filepath.parent.mkdir(parents=True, exist_ok=True)

    def open(self):
        """Open file for appending."""
        if self._file is None:
            self._file = open(self.filepath, "ab")  # Append binary mode

    def write(self, record: Dict[str, Any]):
        """Write a record to JSONL file.

        Args:
            record: Dictionary to write as JSON line
        """
        if self._file is None:
            self.open()

        # Serialize to JSON bytes
        if orjson is not None:
            json_bytes = orjson.dumps(
                record,
                option=orjson.OPT_APPEND_NEWLINE | orjson.OPT_SERIALIZE_NUMPY
            )
        else:
            import json
            json_bytes = (json.dumps(record, ensure_ascii=False) + '\n').encode('utf-8')

        # Write to file
        self._file.write(json_bytes)

        # Optionally fsync for durability
        if self.fsync:
            self._file.flush()
            import os
            os.fsync(self._file.fileno())

    def close(self):
        """Close the file."""
        if self._file is not None:
            self._file.close()
            self._file = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def read_jsonl(filepath: Path) -> Iterator[Dict[str, Any]]:
    """Read JSONL file and yield records.

    Args:
        filepath: Path to JSONL file

    Yields:
        Dict records from the file
    """
    # Return immediately if file doesn't exist
    if not filepath.exists():
        return

    with open(filepath, "rb") as f:
        for line in f:
            line = line.strip()
            if line:
                if orjson is not None:
                    yield orjson.loads(line)
                else:
                    import json
                    yield json.loads(line)
