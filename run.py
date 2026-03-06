"""Main entry point for Genesis X.

Usage:
    python run.py
    python run.py --ticks 100
    python run.py --config config/runtime.yaml
"""
import argparse
from pathlib import Path
from datetime import datetime, timezone
import sys

# Load .env file before other imports to ensure environment variables are available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available, continue without it
    pass

from common.config import load_config
from core.life_loop import LifeLoop


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Genesis X - Digital Life System")

    parser.add_argument(
        "--config",
        type=str,
        default="config",
        help="Path to config directory (default: config)",
    )

    parser.add_argument(
        "--ticks",
        type=int,
        default=None,
        help="Number of ticks to run (default: from config)",
    )

    parser.add_argument(
        "--artifacts",
        type=str,
        default="artifacts",
        help="Directory for artifacts (default: artifacts)",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility",
    )

    parser.add_argument(
        "--mode",
        type=str,
        default="work",
        choices=["work", "friend", "sleep", "reflect", "play"],
        help="Initial mode (default: work)",
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    print("=" * 60)
    print("Genesis X: Axiology Engine for Digital Life")
    print("=" * 60)
    print()

    # Parse arguments
    args = parse_args()

    # Load configuration
    print(f"[Main] Loading configuration from: {args.config}")
    try:
        config = load_config(Path(args.config))
    except Exception as e:
        print(f"[ERROR] Failed to load config: {e}")
        sys.exit(1)

    # Check LLM API configuration
    llm_config = config.get("llm", {})
    if not llm_config.get("api_base"):
        print("[WARNING] LLM API not configured!")
        print("          The system will run in simulation mode (no LLM calls).")
        print("          To configure LLM API:")
        print("          1. Copy config/llm_config.env.example to .env")
        print("          2. Edit .env and fill in your API details")
        print("          Or set environment variables:")
        print("            Windows: set LLM_API_BASE=https://your-api/v1")
        print("                    set LLM_API_KEY=your-key")
        print("                    set LLM_MODEL=your-model")
        print("          See docs/LLM_API配置指南.md for details.")
        print()

    # Create run directory
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    seed_suffix = f"_{args.seed}" if args.seed else ""
    run_dir = Path(args.artifacts) / f"run_{timestamp}{seed_suffix}"

    print(f"[Main] Run directory: {run_dir}")
    print(f"[Main] Mode: {args.mode}")
    print()

    # Set random seed for reproducibility
    if args.seed is not None:
        import random
        random.seed(args.seed)
        try:
            import numpy as np
            np.random.seed(args.seed)
        except ImportError:
            pass

    # Initialize life loop
    life_loop = None
    try:
        life_loop = LifeLoop(config=config, run_dir=run_dir)

        # Set initial mode
        life_loop.state.mode = args.mode

        # Run session
        max_ticks = args.ticks or config.get("runtime", {}).get("max_ticks", 100)
        life_loop.run_session(max_ticks=max_ticks)

    except KeyboardInterrupt:
        print("\n[Main] Interrupted by user. Exiting gracefully...")
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Ensure state is persisted on exit
        if life_loop is not None:
            try:
                life_loop.shutdown()
            except Exception as e:
                print(f"[WARNING] Error during shutdown: {e}")

    print()
    print("=" * 60)
    print("Genesis X session completed.")
    print(f"Artifacts saved to: {run_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
