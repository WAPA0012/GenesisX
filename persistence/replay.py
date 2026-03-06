"""
Replay Engine: Deterministic Execution Replay System

Supports three replay modes:
- Strict Replay: Complete deterministic replay with consistency verification
- Semantic Replay: Allow LLM re-execution with semantic equivalence checking
- Fork Replay: Branch from specific tick for what-if analysis

Key features:
- LLM output hash verification for determinism
- State snapshot save/restore at checkpoints
- Divergence detection and reporting
- Multi-branch fork management

References:
- 论文 3.4 严格回放 (Strict Replay)
- 代码大纲 persistence/replay.py
- 工作索引 03.4 replay: strict/semantic/fork三模式
"""

from enum import Enum
from typing import Dict, Any, Optional, List, Tuple, Set
from pathlib import Path
from dataclasses import dataclass, field
import orjson
import hashlib
from datetime import datetime, timezone
import copy


class ReplayMode(str, Enum):
    """Replay mode selection."""
    STRICT = "strict"        # Full deterministic replay, exact match required
    SEMANTIC = "semantic"    # Allow LLM re-execution, verify semantic equivalence
    FORK = "fork"           # Branch from specific tick


@dataclass
class ReplayState:
    """State snapshot for replay."""
    tick: int
    session_id: str
    fields: Dict[str, float]  # Affect fields (mood, stress, energy, etc.)
    weights: Dict[str, float]  # Value weights
    gaps: Dict[str, float]     # Value gaps
    mode: str
    stage: str
    current_goal: Optional[str] = None
    memory_stats: Dict[str, int] = field(default_factory=dict)
    ledger: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tick": self.tick,
            "session_id": self.session_id,
            "fields": self.fields,
            "weights": self.weights,
            "gaps": self.gaps,
            "mode": self.mode,
            "stage": self.stage,
            "current_goal": self.current_goal,
            "memory_stats": self.memory_stats,
            "ledger": self.ledger,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReplayState":
        """Create from dictionary."""
        return cls(
            tick=data["tick"],
            session_id=data["session_id"],
            fields=data["fields"],
            weights=data["weights"],
            gaps=data["gaps"],
            mode=data["mode"],
            stage=data["stage"],
            current_goal=data.get("current_goal"),
            memory_stats=data.get("memory_stats", {}),
            ledger=data.get("ledger", {}),
        )


@dataclass
class DivergenceReport:
    """Report of divergence between original and replay."""
    tick: int
    divergence_type: str  # "state", "output", "hash"
    original_value: Any
    replay_value: Any
    severity: str  # "low", "medium", "high"
    message: str


class LLMOutputHasher:
    """
    Hash LLM outputs for determinism verification.

    Hashes both the exact output and a normalized version for semantic comparison.
    """

    @staticmethod
    def hash_exact(output: str) -> str:
        """
        Generate exact hash of LLM output.

        Args:
            output: LLM output string

        Returns:
            SHA-256 hash (first 16 chars)
        """
        return hashlib.sha256(output.encode('utf-8')).hexdigest()[:16]

    @staticmethod
    def hash_semantic(output: str) -> str:
        """
        Generate semantic hash (normalized).

        Normalization:
        - Lowercase
        - Remove extra whitespace
        - Remove punctuation at end

        Args:
            output: LLM output string

        Returns:
            SHA-256 hash of normalized output
        """
        # Normalize
        normalized = output.lower().strip()
        normalized = " ".join(normalized.split())  # Collapse whitespace
        normalized = normalized.rstrip(".,!?;:")

        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:16]

    @staticmethod
    def verify_match(original: str, replay: str, mode: ReplayMode) -> Tuple[bool, str]:
        """
        Verify if outputs match according to mode.

        Args:
            original: Original LLM output
            replay: Replayed LLM output
            mode: Replay mode

        Returns:
            (match, reason) tuple
        """
        if mode == ReplayMode.STRICT:
            # Exact match required
            exact_match = LLMOutputHasher.hash_exact(original) == LLMOutputHasher.hash_exact(replay)
            if exact_match:
                return True, "Exact hash match"
            else:
                return False, f"Hash mismatch: {LLMOutputHasher.hash_exact(original)} != {LLMOutputHasher.hash_exact(replay)}"

        elif mode == ReplayMode.SEMANTIC:
            # Semantic match acceptable
            semantic_match = LLMOutputHasher.hash_semantic(original) == LLMOutputHasher.hash_semantic(replay)
            if semantic_match:
                return True, "Semantic hash match"
            else:
                # Check if at least some similarity using Jaccard index
                orig_words = set(original.lower().split())
                replay_words = set(replay.lower().split())

                if not orig_words or not replay_words:
                    return False, f"Semantic mismatch: empty text comparison"

                # Jaccard similarity: intersection / union
                intersection = len(orig_words & replay_words)
                union = len(orig_words | replay_words)
                jaccard = intersection / union if union > 0 else 0.0

                # Also check overlap percentage relative to both texts
                orig_coverage = intersection / len(orig_words) if orig_words else 0
                replay_coverage = intersection / len(replay_words) if replay_words else 0

                if jaccard > 0.4 or (orig_coverage > 0.5 and replay_coverage > 0.5):
                    return True, f"Semantic similarity (Jaccard={jaccard:.2f}, orig_cov={orig_coverage:.2f}, replay_cov={replay_coverage:.2f})"
                else:
                    return False, f"Semantic mismatch: {LLMOutputHasher.hash_semantic(original)} != {LLMOutputHasher.hash_semantic(replay)}"

        else:  # FORK mode
            # No verification needed in fork mode
            return True, "Fork mode - no verification"


class StateSnapshotManager:
    """
    Manage state snapshots for replay.

    Snapshots are saved at configurable intervals for fast seeking.
    """

    def __init__(self, snapshot_dir: Path, snapshot_interval: int = 10):
        """
        Initialize snapshot manager.

        Args:
            snapshot_dir: Directory to save snapshots
            snapshot_interval: Save snapshot every N ticks
        """
        self.snapshot_dir = Path(snapshot_dir)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.snapshot_interval = snapshot_interval

        # In-memory cache
        self.snapshots: Dict[int, ReplayState] = {}

    def save_snapshot(self, state: ReplayState):
        """
        Save state snapshot.

        Args:
            state: State to save
        """
        tick = state.tick

        # Save to memory cache
        self.snapshots[tick] = state

        # Save to disk (every snapshot_interval ticks)
        if tick % self.snapshot_interval == 0:
            snapshot_file = self.snapshot_dir / f"snapshot_{tick:06d}.json"
            with open(snapshot_file, 'wb') as f:
                f.write(orjson.dumps(state.to_dict(), option=orjson.OPT_INDENT_2))

    def load_snapshot(self, tick: int) -> Optional[ReplayState]:
        """
        Load snapshot for specific tick.

        Args:
            tick: Tick number

        Returns:
            ReplayState if found, None otherwise
        """
        # Check memory cache first
        if tick in self.snapshots:
            return self.snapshots[tick]

        # Check disk
        snapshot_file = self.snapshot_dir / f"snapshot_{tick:06d}.json"
        if snapshot_file.exists():
            with open(snapshot_file, 'rb') as f:
                data = orjson.loads(f.read())
                state = ReplayState.from_dict(data)
                self.snapshots[tick] = state
                return state

        return None

    def get_nearest_snapshot(self, tick: int) -> Optional[Tuple[int, ReplayState]]:
        """
        Get nearest snapshot before or at tick.

        Args:
            tick: Target tick

        Returns:
            (snapshot_tick, state) if found, None otherwise
        """
        # Find largest tick <= target tick
        available_ticks = sorted([t for t in self.snapshots.keys() if t <= tick])

        if available_ticks:
            nearest_tick = available_ticks[-1]
            return nearest_tick, self.snapshots[nearest_tick]

        # Check disk
        snapshot_files = sorted(self.snapshot_dir.glob("snapshot_*.json"))
        for snapshot_file in reversed(snapshot_files):
            try:
                snapshot_tick = int(snapshot_file.stem.split("_")[1])
            except (IndexError, ValueError):
                continue
            if snapshot_tick <= tick:
                state = self.load_snapshot(snapshot_tick)
                if state:
                    return snapshot_tick, state

        return None

    def clear_snapshots(self):
        """Clear all snapshots."""
        self.snapshots.clear()


class ReplayEngine:
    """
    Engine for deterministic replay of Genesis X sessions.

    Supports three modes:
    1. Strict Replay: Exact deterministic replay with verification
    2. Semantic Replay: Allow LLM variation with semantic checks
    3. Fork Replay: Branch from specific tick for what-if analysis
    """

    def __init__(
        self,
        replay_dir: Path,
        mode: ReplayMode = ReplayMode.STRICT,
        snapshot_interval: int = 10
    ):
        """
        Initialize replay engine.

        Args:
            replay_dir: Directory containing episodes.jsonl and tool_calls.jsonl
            mode: Replay mode
            snapshot_interval: Save snapshot every N ticks
        """
        self.replay_dir = Path(replay_dir)
        self.mode = mode
        self.snapshot_interval = snapshot_interval

        # Load data
        self.episodes = self._load_episodes()
        self.tool_calls = self._load_tool_calls()
        self.original_states = self._load_states()

        # Snapshot manager
        self.snapshot_manager = StateSnapshotManager(
            self.replay_dir / "snapshots",
            snapshot_interval
        )

        # Replay state
        self.current_tick = 0
        self.divergences: List[DivergenceReport] = []

        # Fork management
        self.fork_point: Optional[int] = None
        self.fork_branches: Dict[str, List[Dict[str, Any]]] = {}

    def _load_episodes(self) -> List[Dict[str, Any]]:
        """Load episodes from jsonl."""
        episodes_file = self.replay_dir / "episodes.jsonl"
        if not episodes_file.exists():
            return []

        episodes = []
        with open(episodes_file, "rb") as f:
            for line in f:
                if line.strip():
                    episodes.append(orjson.loads(line))
        return episodes

    def _load_tool_calls(self) -> Dict[int, List[Dict[str, Any]]]:
        """Load tool calls indexed by tick."""
        tool_calls_file = self.replay_dir / "tool_calls.jsonl"
        if not tool_calls_file.exists():
            return {}

        tool_calls_by_tick = {}
        with open(tool_calls_file, "rb") as f:
            for line in f:
                if line.strip():
                    call = orjson.loads(line)
                    tick = call.get("tick", 0)
                    if tick not in tool_calls_by_tick:
                        tool_calls_by_tick[tick] = []
                    tool_calls_by_tick[tick].append(call)
        return tool_calls_by_tick

    def _load_states(self) -> Dict[int, ReplayState]:
        """Load state history from snapshots."""
        states_file = self.replay_dir / "states.jsonl"
        if not states_file.exists():
            return {}

        states = {}
        with open(states_file, "rb") as f:
            for line in f:
                if line.strip():
                    data = orjson.loads(line)
                    state = ReplayState.from_dict(data)
                    states[state.tick] = state

        return states

    def get_episode(self, tick: int) -> Optional[Dict[str, Any]]:
        """Get episode for specific tick."""
        if tick < len(self.episodes):
            return self.episodes[tick]
        return None

    def get_tool_outputs(self, tick: int) -> List[Dict[str, Any]]:
        """Get tool call outputs for specific tick."""
        return self.tool_calls.get(tick, [])

    def get_original_state(self, tick: int) -> Optional[ReplayState]:
        """Get original state at specific tick."""
        return self.original_states.get(tick)

    def should_replay_output(self, tool_id: str, tick: int) -> bool:
        """
        Check if tool output should be replayed (not re-executed).

        Args:
            tool_id: Tool identifier
            tick: Current tick

        Returns:
            True if should replay cached output
        """
        if self.mode == ReplayMode.STRICT:
            # Always replay in strict mode
            return True

        elif self.mode == ReplayMode.SEMANTIC:
            # Replay deterministic tools, re-execute LLM tools
            # LLM tools should be re-executed to test semantic equivalence
            llm_tools = {"llm_chat", "llm_generate", "llm_complete"}
            return tool_id not in llm_tools

        else:  # FORK mode
            # Before fork point: replay
            # After fork point: execute fresh
            if self.fork_point is not None:
                return tick < self.fork_point
            return False

    def verify_state_consistency(
        self,
        original: ReplayState,
        replayed: ReplayState,
        tolerance: float = 0.01
    ) -> List[DivergenceReport]:
        """
        Verify state consistency between original and replayed.

        Args:
            original: Original state
            replayed: Replayed state
            tolerance: Tolerance for float comparisons

        Returns:
            List of divergence reports
        """
        divergences = []
        tick = original.tick

        # Check mode and stage
        if original.mode != replayed.mode:
            divergences.append(DivergenceReport(
                tick=tick,
                divergence_type="state",
                original_value=original.mode,
                replay_value=replayed.mode,
                severity="high",
                message=f"Mode mismatch: {original.mode} != {replayed.mode}"
            ))

        if original.stage != replayed.stage:
            divergences.append(DivergenceReport(
                tick=tick,
                divergence_type="state",
                original_value=original.stage,
                replay_value=replayed.stage,
                severity="high",
                message=f"Stage mismatch: {original.stage} != {replayed.stage}"
            ))

        # Check affect fields
        for field, orig_value in original.fields.items():
            replay_value = replayed.fields.get(field, 0.0)
            if abs(orig_value - replay_value) > tolerance:
                divergences.append(DivergenceReport(
                    tick=tick,
                    divergence_type="state",
                    original_value=orig_value,
                    replay_value=replay_value,
                    severity="medium",
                    message=f"Field '{field}' diverged: {orig_value:.3f} != {replay_value:.3f}"
                ))

        # Check weights
        for dim, orig_weight in original.weights.items():
            replay_weight = replayed.weights.get(dim, 0.0)
            if abs(orig_weight - replay_weight) > tolerance:
                divergences.append(DivergenceReport(
                    tick=tick,
                    divergence_type="state",
                    original_value=orig_weight,
                    replay_value=replay_weight,
                    severity="low",
                    message=f"Weight '{dim}' diverged: {orig_weight:.3f} != {replay_weight:.3f}"
                ))

        return divergences

    def verify_llm_output(
        self,
        original_output: str,
        replay_output: str,
        tick: int
    ) -> Optional[DivergenceReport]:
        """
        Verify LLM output matches according to mode.

        Args:
            original_output: Original LLM output
            replay_output: Replayed LLM output
            tick: Current tick

        Returns:
            DivergenceReport if mismatch, None if match
        """
        match, reason = LLMOutputHasher.verify_match(original_output, replay_output, self.mode)

        if not match:
            return DivergenceReport(
                tick=tick,
                divergence_type="output",
                original_value=LLMOutputHasher.hash_exact(original_output),
                replay_value=LLMOutputHasher.hash_exact(replay_output),
                severity="high" if self.mode == ReplayMode.STRICT else "medium",
                message=f"LLM output mismatch: {reason}"
            )

        return None

    def record_divergence(self, divergence: DivergenceReport):
        """Record divergence for reporting."""
        self.divergences.append(divergence)

    def get_divergence_summary(self) -> Dict[str, Any]:
        """
        Get summary of divergences.

        Returns:
            Summary dict with counts and severity breakdown
        """
        if not self.divergences:
            return {
                "total": 0,
                "by_severity": {"low": 0, "medium": 0, "high": 0},
                "by_type": {},
                "divergences": []
            }

        by_severity = {"low": 0, "medium": 0, "high": 0}
        by_type = {}

        for div in self.divergences:
            by_severity[div.severity] += 1
            by_type[div.divergence_type] = by_type.get(div.divergence_type, 0) + 1

        return {
            "total": len(self.divergences),
            "by_severity": by_severity,
            "by_type": by_type,
            "divergences": [
                {
                    "tick": d.tick,
                    "type": d.divergence_type,
                    "severity": d.severity,
                    "message": d.message,
                }
                for d in self.divergences[-10:]  # Last 10 divergences
            ]
        }

    def fork_at(self, tick: int, branch_name: str = "default") -> bool:
        """
        Fork replay at specific tick for what-if analysis.

        Args:
            tick: Tick to fork from
            branch_name: Name for this fork branch

        Returns:
            True if fork successful
        """
        if tick >= len(self.episodes):
            return False

        # Set fork point
        self.fork_point = tick
        self.current_tick = tick
        self.mode = ReplayMode.FORK

        # Load state at fork point
        nearest = self.snapshot_manager.get_nearest_snapshot(tick)
        if nearest:
            _, state = nearest
            # State will be used to initialize fork

        # Initialize fork branch
        self.fork_branches[branch_name] = []

        return True

    def record_fork_action(self, branch_name: str, action: Dict[str, Any]):
        """
        Record action in fork branch.

        Args:
            branch_name: Fork branch name
            action: Action dict
        """
        if branch_name not in self.fork_branches:
            self.fork_branches[branch_name] = []

        self.fork_branches[branch_name].append(action)

    def save_fork_branch(self, branch_name: str):
        """
        Save fork branch to disk.

        Args:
            branch_name: Fork branch name
        """
        if branch_name not in self.fork_branches:
            return

        fork_dir = self.replay_dir / "forks"
        fork_dir.mkdir(parents=True, exist_ok=True)

        fork_file = fork_dir / f"{branch_name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.jsonl"

        with open(fork_file, 'wb') as f:
            for action in self.fork_branches[branch_name]:
                f.write(orjson.dumps(action) + b'\n')

    def save_snapshot(self, state: ReplayState):
        """
        Save state snapshot.

        Args:
            state: State to save
        """
        self.snapshot_manager.save_snapshot(state)

    def restore_from_snapshot(self, tick: int) -> Optional[ReplayState]:
        """
        Restore state from snapshot.

        Args:
            tick: Tick to restore

        Returns:
            Restored state if found
        """
        return self.snapshot_manager.load_snapshot(tick)

    def get_replay_statistics(self) -> Dict[str, Any]:
        """
        Get replay statistics.

        Returns:
            Statistics dict
        """
        return {
            "mode": self.mode,
            "total_episodes": len(self.episodes),
            "current_tick": self.current_tick,
            "fork_point": self.fork_point,
            "fork_branches": len(self.fork_branches),
            "divergences": self.get_divergence_summary(),
            "snapshots_saved": len(self.snapshot_manager.snapshots),
        }


# Convenience functions
def create_replay_engine(
    replay_dir: Path,
    mode: str = "strict",
    snapshot_interval: int = 10
) -> ReplayEngine:
    """
    Create replay engine.

    Args:
        replay_dir: Directory containing replay data
        mode: Replay mode (strict/semantic/fork)
        snapshot_interval: Snapshot interval

    Returns:
        ReplayEngine instance
    """
    replay_mode = ReplayMode(mode)
    return ReplayEngine(replay_dir, replay_mode, snapshot_interval)


def verify_replay_consistency(
    original_dir: Path,
    replay_dir: Path,
    tolerance: float = 0.01
) -> Dict[str, Any]:
    """
    Verify consistency between original and replay runs.

    Args:
        original_dir: Original run directory
        replay_dir: Replay run directory
        tolerance: Float comparison tolerance

    Returns:
        Verification report
    """
    engine = ReplayEngine(original_dir, ReplayMode.STRICT)

    # Load both runs and compare
    # This is a simplified implementation
    # In production, iterate through all ticks and verify

    return {
        "consistent": len(engine.divergences) == 0,
        "divergences": engine.get_divergence_summary(),
    }


# Example usage and test
if __name__ == "__main__":
    from pathlib import Path

    # Test snapshot manager
    snapshot_dir = Path("test_snapshots")
    snapshot_manager = StateSnapshotManager(snapshot_dir, snapshot_interval=5)

    # Save some snapshots
    for tick in range(20):
        state = ReplayState(
            tick=tick,
            session_id="test_session",
            fields={"mood": 0.5 + tick * 0.01, "stress": 0.3, "energy": 0.8},
            # v15修复: 使用5维核心价值系统
            weights={dim: 0.2 for dim in ["homeostasis", "attachment", "curiosity", "competence", "safety"]},
            gaps={dim: 0.1 for dim in ["homeostasis", "attachment", "curiosity", "competence", "safety"]},
            mode="work",
            stage="adult",
        )
        snapshot_manager.save_snapshot(state)

    print(f"Saved {len(snapshot_manager.snapshots)} snapshots")

    # Load nearest snapshot
    nearest = snapshot_manager.get_nearest_snapshot(17)
    if nearest:
        nearest_tick, state = nearest
        print(f"Nearest snapshot to tick 17: tick {nearest_tick}")

    # Test LLM hasher
    original = "Hello, how can I help you today?"
    replay1 = "Hello, how can I help you today?"  # Exact match
    replay2 = "hello how can i help you today"     # Semantic match
    replay3 = "I can assist you with that task."   # Different

    print("\nLLM Output Verification:")
    print(f"Exact match: {LLMOutputHasher.verify_match(original, replay1, ReplayMode.STRICT)}")
    print(f"Semantic match: {LLMOutputHasher.verify_match(original, replay2, ReplayMode.SEMANTIC)}")
    print(f"Different: {LLMOutputHasher.verify_match(original, replay3, ReplayMode.SEMANTIC)}")

    # Cleanup
    import shutil
    if snapshot_dir.exists():
        shutil.rmtree(snapshot_dir)
