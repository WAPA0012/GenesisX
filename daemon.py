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

        # P9-5: 连续健康失败计数（超阈值退出 daemon 让外部 supervisor 重启）
        self._consecutive_health_failures = 0
        self._health_failure_threshold = 5  # 连续 5 次失败（约 5 分钟）后退出

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
                        # P9-5 修复：实际调用 consolidator（原来是空注释）
                        if hasattr(self.life_loop, 'consolidator') and self.life_loop.consolidator:
                            if self.life_loop.episodic.count() >= 20:
                                stats = self.life_loop.consolidator.consolidate(
                                    current_tick=self.life_loop.state.tick + 1,
                                    budget_tokens=1000,
                                    salience_threshold=0.7,
                                )
                                self.logger.info(f"Consolidation done: {stats}")
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
                            self.logger.warning("Health check failed")
                            self._report_unhealthy()
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

            # P9-5: 健康时清零连续失败计数
            self._consecutive_health_failures = 0
            return True
        except Exception:
            return False

    def _report_unhealthy(self):
        """Report unhealthy state (P9-5: replaces _attempt_recovery).

        原设计的"恢复"逻辑有缺陷：
        1. life_loop is None / state is None 是致命错误，daemon 自己救不了
           （调 self.life_loop.state.stress 会 AttributeError）
        2. stress > 0.95 是非致命状态，life_loop 内部已有自愈：
           - stress > 0.7 触发 REFLECT stress_relief (life_loop.py:1258)
           - fatigue > 0.8 触发巩固 + reset_activity_fatigue (life_loop.py:1598)
        所以 daemon 做 recovery 是冗余且可能冲突（多线程并发调 consolidate 会破坏
        cooldown 状态）。改为报警 + 标记 + 连续失败超阈值退出，让外部 supervisor 重启。
        """
        self._consecutive_health_failures += 1
        failures = self._consecutive_health_failures

        # 尽力保存状态（不阻塞）
        try:
            self.save_state()
        except Exception:
            pass

        if failures >= self._health_failure_threshold:
            self.logger.error(
                f"Health check failed {failures} consecutive times "
                f"(threshold={self._health_failure_threshold}). Exiting daemon for external restart. "
                f"Last state: stress={getattr(self.life_loop.state, 'stress', '?') if self.life_loop else '?'}, "
                f"life_loop_alive={self.life_loop is not None}"
            )
            self.running = False  # 让主循环退出，外部 supervisor（systemd/supervisor）可重启
        else:
            self.logger.warning(
                f"Health check failed ({failures}/{self._health_failure_threshold}). "
                f"Will retry; daemon will exit after threshold exceeded."
            )

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
                    # P0: 文件式用户输入注入（/tmp/user_input.txt 有内容则注入）
                    import os as _os
                    _input_file = "/tmp/user_input.txt"
                    if _os.path.exists(_input_file):
                        try:
                            with open(_input_file, 'r') as _f:
                                _msg = _f.read().strip()
                            if _msg:
                                _os.remove(_input_file)
                                self.life_loop.get_user_input = lambda msg=_msg: msg
                                self.logger.info(f"[USER_INPUT] Injected: {_msg[:60]}")
                            else:
                                if self.life_loop.get_user_input is not None:
                                    self.life_loop.get_user_input = None
                        except Exception as _e:
                            self.logger.warning(f"[USER_INPUT] Read failed: {_e}")
                    else:
                        # 没有新消息时，清掉上次的回调（避免重复注入）
                        if self.life_loop.get_user_input is not None:
                            self.life_loop.get_user_input = None
                    episode = self.life_loop.tick(t=self.life_loop.state.tick + 1)
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
