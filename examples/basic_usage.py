"""
GenesisX Basic Usage Example

This example demonstrates how to:
1. Initialize the Genesis X system
2. Run a basic conversation
3. Monitor the system state
4. Save and replay sessions
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.config import Config
from core.life_loop import LifeLoop
from core.state import GlobalState


def main():
    """Main example function."""
    print("=" * 60)
    print("  GenesisX Basic Usage Example")
    print("=" * 60)
    print()

    # Step 1: Load configuration
    print("[1] Loading configuration...")
    config = Config()
    print(f"   API Key: {'***' if config.dashscope_api_key else 'NOT SET'}")
    print()

    # Step 2: Initialize state
    print("[2] Initializing global state...")
    state = GlobalState()
    print(f"   Energy: {state.energy:.2f}")
    print(f"   Mood: {state.mood:.2f}")
    print(f"   Stress: {state.stress:.2f}")
    print()

    # Step 3: Create life loop
    print("[3] Creating life loop...")
    life_loop = LifeLoop(config)
    print("   Life loop initialized")
    print()

    # Step 4: Run a few ticks
    print("[4] Running simulation (5 ticks)...")
    for i in range(5):
        print(f"   Tick {i+1}/5...")
        # In real usage, you would call life_loop.tick(state, context)
    print()

    # Step 5: Display final state
    print("[5] Final state:")
    print(f"   Energy: {state.energy:.2f}")
    print(f"   Mood: {state.mood:.2f}")
    print(f"   Stress: {state.stress:.2f}")
    print()

    print("=" * 60)
    print("  Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
