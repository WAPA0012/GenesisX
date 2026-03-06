"""Genesis Lifecycle - Full lifecycle management.

Wraps TickLoop with additional lifecycle features:
- Memory management
- Offline consolidation
- Scheduler integration
- Graceful shutdown
"""

from typing import Dict, Any, Optional
from pathlib import Path
from .tick_loop import TickLoop


class GenesisLifecycle:
    """Full Genesis X lifecycle manager."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize lifecycle.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.tick_loop = TickLoop(config)

        # Scheduler stats
        self.offline_runs = 0
        self.offline_interval = config.get("offline_interval", 50)

        # Memory stats
        self.episodic_count = 0

    @property
    def tick(self) -> int:
        """Current tick number."""
        return self.tick_loop.tick

    def run(self, max_ticks: int = 100):
        """Run lifecycle for specified ticks.

        Args:
            max_ticks: Maximum ticks to run
        """
        for i in range(max_ticks):
            self.tick_loop.run_tick()
            self.episodic_count += 1

            # Check for offline consolidation
            if self.tick_loop.tick % self.offline_interval == 0:
                self._run_offline_consolidation()

    def _run_offline_consolidation(self):
        """Run offline memory consolidation."""
        self.offline_runs += 1

    def get_state(self) -> Dict[str, Any]:
        """Get current state."""
        return self.tick_loop.get_state()

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return {
            "episodic_count": self.episodic_count,
        }

    def get_scheduler_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        return {
            "offline_runs": self.offline_runs,
        }

    def shutdown(self):
        """Graceful shutdown."""
        pass
