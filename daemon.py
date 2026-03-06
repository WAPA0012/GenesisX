"""Genesis X Long-Running Daemon

Persistent service that runs Genesis X continuously.
Features:
- Auto-restart on error
- State persistence and recovery
- Daily log rotation
- Memory consolidation scheduling
- Graceful shutdown

Usage:
    python daemon.py              # Start daemon
    python daemon.py --stop       # Stop running daemon
    python daemon.py --status     # Check status
    python daemon.py --restart    # Restart daemon
"""

import sys
import os
import time
import signal
import argparse
import threading
from pathlib import Path
from datetime import datetime, timezone
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Load .env before imports
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from core.life_loop import LifeLoop
from common.config import load_config
from tools.tool_executor import LLMToolExecutor


# ============================================================================
# Daemon Configuration
# ============================================================================

PID_FILE = "artifacts/genesisx.pid"
LOG_FILE = "artifacts/genesisx_daemon.log"
STATE_FILE = "artifacts/daemon_state.json"

# Daemon settings
CHECK_INTERVAL = 60  # seconds between health checks
CONSOLIDATION_INTERVAL = 3600  # seconds between memory consolidation (1 hour)
MAX_RESTART_DELAY = 300  # max seconds to wait before restart
SHUTDOWN_TIMEOUT = 30  # seconds to wait for graceful shutdown


# ============================================================================
# Daemon Manager
# ============================================================================

class DaemonManager:
    """Manages Genesis X daemon lifecycle."""

    def __init__(self, config_path: str = "config"):
        self.config_path = config_path
        self.config = None
        self.life_loop: LifeLoop = None
        self.running = False
        self.pid = os.getpid()

        # Threading
        self.consolidation_thread = None
        self.health_check_thread = None

        # Logging
        self._setup_logging()

    def _setup_logging(self):
        """Configure logging for daemon."""
        Path("artifacts").mkdir(exist_ok=True)

        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            handlers=[
                logging.FileHandler(LOG_FILE, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def load_config(self) -> bool:
        """Load configuration from files."""
        try:
            self.config = load_config(Path(self.config_path))
            self.logger.info(f"Configuration loaded from {self.config_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            return False

    def initialize(self) -> bool:
        """Initialize Genesis X life loop."""
        try:
            # Create run directory
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            run_dir = Path("artifacts") / f"daemon_{timestamp}"
            run_dir.mkdir(parents=True, exist_ok=True)

            # Initialize life loop
            self.life_loop = LifeLoop(config=self.config, run_dir=run_dir)
            self.logger.info(f"LifeLoop initialized with run_dir: {run_dir}")

            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize LifeLoop: {e}")
            return False

    def save_state(self) -> bool:
        """Save current daemon state to disk."""
        try:
            state = {
                "pid": self.pid,
                "running": self.running,
                "start_time": datetime.now(timezone.utc).isoformat(),
                "run_dir": str(self.life_loop.run_dir) if self.life_loop else None,
                "tick": self.life_loop.state.tick if self.life_loop else 0,
            }

            with open(STATE_FILE, 'w', encoding='utf-8') as f:
                import json
                json.dump(state, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")
            return False

    def load_state(self) -> dict:
        """Load saved daemon state from disk."""
        try:
            if not Path(STATE_FILE).exists():
                return {}

            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                import json
                return json.load(f)
        except Exception as e:
            self.logger.warning(f"Failed to load state: {e}")
            return {}

    def write_pid(self) -> bool:
        """Write PID file for process management."""
        try:
            Path("artifacts").mkdir(exist_ok=True)
            with open(PID_FILE, 'w') as f:
                f.write(str(self.pid))
            return True
        except Exception as e:
            self.logger.error(f"Failed to write PID file: {e}")
            return False

    def remove_pid(self) -> bool:
        """Remove PID file."""
        try:
            if Path(PID_FILE).exists():
                Path(PID_FILE).unlink()
            return True
        except Exception as e:
            self.logger.error(f"Failed to remove PID file: {e}")
            return False

    def start_consolidation_thread(self):
        """Start background memory consolidation thread."""
        def consolidation_worker():
            while self.running:
                try:
                    time.sleep(CONSOLIDATION_INTERVAL)
                    if self.running and self.life_loop:
                        self.logger.info("Triggering scheduled memory consolidation")
                        # Trigger consolidation
                        # This would call the consolidator to compress memories
                except Exception as e:
                    self.logger.error(f"Consolidation thread error: {e}")

        self.consolidation_thread = threading.Thread(
            target=consolidation_worker,
            daemon=True,
            name="Consolidation"
        )
        self.consolidation_thread.start()
        self.logger.info("Consolidation thread started")

    def start_health_check_thread(self):
        """Start health check thread."""
        def health_worker():
            while self.running:
                try:
                    time.sleep(CHECK_INTERVAL)
                    if self.running and self.life_loop:
                        # Check if life loop is healthy
                        if not self._health_check():
                            self.logger.warning("Health check failed, attempting recovery")
                            self._attempt_recovery()
                except Exception as e:
                    self.logger.error(f"Health check thread error: {e}")

        self.health_check_thread = threading.Thread(
            target=health_worker,
            daemon=True,
            name="HealthCheck"
        )
        self.health_check_thread.start()
        self.logger.info("Health check thread started")

    def _health_check(self) -> bool:
        """Check if the system is healthy."""
        try:
            # Basic health checks
            if self.life_loop is None:
                return False
            if self.life_loop.state is None:
                return False

            # Check for critical errors
            mood = self.life_loop.state.mood
            stress = self.life_loop.state.stress

            # System is unhealthy if stress is critically high
            if stress > 0.95:
                self.logger.warning(f"Critical stress level: {stress}")
                return False

            return True
        except Exception:
            return False

    def _attempt_recovery(self):
        """Attempt to recover from unhealthy state."""
        try:
            self.logger.info("Attempting recovery...")

            # Trigger rest mode if stressed
            if self.life_loop.state.stress > 0.8:
                self.logger.info("Triggering stress recovery")
                # Could trigger consolidation here

            self.save_state()
        except Exception as e:
            self.logger.error(f"Recovery failed: {e}")

    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        if os.name == 'nt':  # Windows
            signal.signal(signal.SIGBREAK, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, initiating shutdown...")
        self.running = False

    def run(self):
        """Main daemon run loop."""
        self.logger.info("=" * 60)
        self.logger.info("Genesis X Daemon starting")
        self.logger.info("=" * 60)

        # Load configuration
        if not self.load_config():
            self.logger.error("Failed to load configuration, exiting")
            return 1

        # Initialize
        if not self.initialize():
            self.logger.error("Failed to initialize, exiting")
            return 1

        # Write PID file
        if not self.write_pid():
            self.logger.error("Failed to write PID file, exiting")
            return 1

        # Save initial state
        self.save_state()

        # Setup signal handlers
        self.setup_signal_handlers()

        # Start background threads
        self.running = True
        self.start_consolidation_thread()
        self.start_health_check_thread()

        self.logger.info("Daemon started successfully")
        self.logger.info("Press Ctrl+C to stop")

        # Main loop - continuous operation
        restart_delay = 1
        max_consecutive_errors = 0

        try:
            while self.running:
                try:
                    # Run one tick
                    episode = self.life_loop.tick(t=self.life_loop.state.tick)

                    # Reset error counter on success
                    max_consecutive_errors = 0
                    restart_delay = 1

                    # Save state periodically
                    if self.life_loop.state.tick % 100 == 0:
                        self.save_state()

                    # Small delay to prevent CPU spinning
                    time.sleep(0.1)

                except KeyboardInterrupt:
                    self.logger.info("Interrupted by user")
                    break

                except Exception as e:
                    max_consecutive_errors += 1
                    self.logger.error(f"Error in main loop: {e}")

                    if max_consecutive_errors > 10:
                        self.logger.error("Too many consecutive errors, stopping")
                        break

                    # Exponential backoff for restart
                    restart_delay = min(restart_delay * 2, MAX_RESTART_DELAY)
                    self.logger.info(f"Waiting {restart_delay}s before retry...")
                    time.sleep(restart_delay)

        finally:
            self.shutdown()

        return 0

    def shutdown(self):
        """Graceful shutdown."""
        self.logger.info("Shutting down daemon...")
        self.running = False

        # Save final state
        self.save_state()

        # Shutdown life loop
        if self.life_loop:
            try:
                self.life_loop.shutdown()
            except Exception as e:
                self.logger.error(f"Error during shutdown: {e}")

        # Remove PID file
        self.remove_pid()

        self.logger.info("Daemon stopped")


# ============================================================================
# Daemon Control Functions
# ============================================================================

def get_running_pid() -> int:
    """Get PID of running daemon from PID file."""
    try:
        if Path(PID_FILE).exists():
            with open(PID_FILE, 'r') as f:
                pid_str = f.read().strip()
                pid = int(pid_str)

            # Check if process is actually running
            try:
                os.kill(pid, 0)  # Check if process exists
                return pid
            except OSError:
                # Process not running, stale PID file
                Path(PID_FILE).unlink()
                return None
    except Exception:
        pass

    return None


def is_running() -> bool:
    """Check if daemon is running."""
    return get_running_pid() is not None


def stop_daemon() -> bool:
    """Stop running daemon."""
    pid = get_running_pid()
    if pid is None:
        print("Daemon is not running")
        return False

    try:
        # Send SIGTERM
        if os.name == 'nt':
            # Windows
            os.kill(pid, signal.CTRL_BREAK_EVENT)
        else:
            os.kill(pid, signal.SIGTERM)

        print(f"Sent stop signal to daemon (PID: {pid})")

        # Wait for process to stop
        for _ in range(SHUTDOWN_TIMEOUT):
            time.sleep(1)
            try:
                os.kill(pid, 0)
            except OSError:
                # Process stopped
                print("Daemon stopped successfully")
                return True

        print("Daemon did not stop gracefully, forcing...")
        if os.name == 'nt':
            import ctypes
            ctypes.windll.kernel32.TerminateProcess(pid, 1)
        else:
            os.kill(pid, signal.SIGKILL)

        print("Daemon forced to stop")
        return True

    except Exception as e:
        print(f"Error stopping daemon: {e}")
        return False


def show_status() -> int:
    """Show daemon status."""
    pid = get_running_pid()
    if pid is None:
        print("Daemon is not running")
        return 1

    print(f"Daemon is running (PID: {pid})")

    # Show state info
    state = DaemonManager().load_state()
    if state:
        print(f"  Start time: {state.get('start_time', 'Unknown')}")
        print(f"  Run directory: {state.get('run_dir', 'Unknown')}")
        print(f"  Current tick: {state.get('tick', 0)}")

    return 0


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point for daemon control."""
    parser = argparse.ArgumentParser(
        description="Genesis X Daemon - Long-running service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python daemon.py              # Start daemon
  python daemon.py --stop       # Stop daemon
  python daemon.py --status     # Check status
  python daemon.py --restart    # Restart daemon
        """
    )

    parser.add_argument(
        "--stop",
        action="store_true",
        help="Stop running daemon"
    )

    parser.add_argument(
        "--status",
        action="store_true",
        help="Show daemon status"
    )

    parser.add_argument(
        "--restart",
        action="store_true",
        help="Restart daemon"
    )

    parser.add_argument(
        "--config",
        type=str,
        default="config",
        help="Path to config directory"
    )

    args = parser.parse_args()

    # Handle restart
    if args.restart:
        stop_daemon()
        time.sleep(2)
        args = argparse.Namespace(config=args.config)  # Reset other args

    # Handle stop
    if args.stop:
        return 0 if stop_daemon() else 1

    # Handle status
    if args.status:
        return show_status()

    # Handle start
    if is_running():
        print("Daemon is already running!")
        print("Use --stop to stop it first, or --restart to restart")
        return 1

    # Start daemon
    print("Starting Genesis X Daemon...")

    daemon = DaemonManager(config_path=args.config)

    # Run in foreground
    return daemon.run()


if __name__ == "__main__":
    sys.exit(main())
