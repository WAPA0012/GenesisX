"""
Storage: Local File/SQLite Abstraction

Provides unified interface for:
- File-based storage (JSONL)
- SQLite database (optional, for querying)

References:
- 代码大纲架构 persistence/storage.py
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
from enum import Enum
import orjson


class StorageBackend(str, Enum):
    """Storage backend types"""
    FILE = "file"
    SQLITE = "sqlite"
    MEMORY = "memory"


class Storage:
    """
    Abstract storage interface.

    Default implementation uses file-based storage (JSONL).
    """

    def __init__(
        self,
        storage_dir: Path,
        backend: StorageBackend = StorageBackend.FILE
    ):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.backend = backend

        # In-memory cache for fast retrieval
        self._cache: Dict[str, Any] = {}

    def write(self, key: str, data: Any):
        """
        Write data to storage.

        Args:
            key: Storage key
            data: Data to store
        """
        if self.backend == StorageBackend.FILE:
            file_path = self.storage_dir / f"{key}.json"
            with open(file_path, 'wb') as f:
                f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))

        # Update cache
        self._cache[key] = data

    def read(self, key: str) -> Optional[Any]:
        """
        Read data from storage.

        Args:
            key: Storage key

        Returns:
            Stored data or None
        """
        # Check cache first
        if key in self._cache:
            return self._cache[key]

        # Read from backend
        if self.backend == StorageBackend.FILE:
            file_path = self.storage_dir / f"{key}.json"
            if not file_path.exists():
                return None

            with open(file_path, 'rb') as f:
                data = orjson.loads(f.read())
                self._cache[key] = data
                return data

        return None

    def append(self, key: str, item: Any):
        """
        Append item to a list.

        Args:
            key: Storage key
            item: Item to append
        """
        current = self.read(key) or []
        if not isinstance(current, list):
            raise ValueError(f"Key '{key}' is not a list")

        current.append(item)
        self.write(key, current)

    def delete(self, key: str):
        """Delete key from storage"""
        if self.backend == StorageBackend.FILE:
            file_path = self.storage_dir / f"{key}.json"
            if file_path.exists():
                file_path.unlink()

        if key in self._cache:
            del self._cache[key]

    def list_keys(self) -> List[str]:
        """List all storage keys"""
        if self.backend == StorageBackend.FILE:
            return [
                p.stem for p in self.storage_dir.glob("*.json")
            ]

        return list(self._cache.keys())

    def clear_cache(self):
        """Clear in-memory cache"""
        self._cache.clear()
