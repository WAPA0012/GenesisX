"""
Snapshot Manager: State Checkpoint Saving/Loading

Supports:
- Full state snapshots (fields/slots/memory indices)
- Incremental snapshots
- Snapshot restore for replay

References:
- 代码大纲架构 persistence/snapshot.py
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
import orjson
from datetime import datetime, timezone


class SnapshotManager:
    """
    Manages state snapshots for checkpointing and replay.
    """

    def __init__(self, snapshot_dir: Path):
        self.snapshot_dir = Path(snapshot_dir)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    def save_snapshot(
        self,
        tick: int,
        session_id: str,
        state: Dict[str, Any],
        snapshot_type: str = "full"
    ) -> Path:
        """
        Save a state snapshot.

        Args:
            tick: Current tick
            session_id: Session ID
            state: Complete state dict
            snapshot_type: "full" or "incremental"

        Returns:
            Path to saved snapshot
        """
        snapshot_data = {
            "tick": tick,
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": snapshot_type,
            "state": state,
        }

        snapshot_path = self.snapshot_dir / f"snapshot_tick_{tick}.json"

        with open(snapshot_path, 'wb') as f:
            f.write(orjson.dumps(
                snapshot_data,
                option=orjson.OPT_INDENT_2
            ))

        return snapshot_path

    def load_snapshot(self, tick: int) -> Optional[Dict[str, Any]]:
        """
        Load a snapshot by tick number.

        Args:
            tick: Tick to load

        Returns:
            Snapshot data or None if not found
        """
        snapshot_path = self.snapshot_dir / f"snapshot_tick_{tick}.json"

        if not snapshot_path.exists():
            return None

        with open(snapshot_path, 'rb') as f:
            return orjson.loads(f.read())

    def list_snapshots(self) -> List[Dict[str, Any]]:
        """List all available snapshots"""
        snapshots = []
        for path in self.snapshot_dir.glob("snapshot_tick_*.json"):
            try:
                tick = int(path.stem.split("_")[-1])
            except (ValueError, IndexError):
                continue
            snapshots.append({
                "path": path,
                "tick": tick,
            })

        return sorted(snapshots, key=lambda x: x["tick"])

    def get_latest_snapshot(self) -> Optional[Dict[str, Any]]:
        """Get the most recent snapshot"""
        snapshots = self.list_snapshots()
        if not snapshots:
            return None

        latest_path = snapshots[-1]["path"]
        with open(latest_path, 'rb') as f:
            return orjson.loads(f.read())

    def prune_old_snapshots(self, keep_last_n: int = 10):
        """Keep only the N most recent snapshots"""
        snapshots = self.list_snapshots()
        if len(snapshots) <= keep_last_n:
            return

        to_delete = snapshots[:-keep_last_n]
        for snapshot in to_delete:
            snapshot["path"].unlink()
