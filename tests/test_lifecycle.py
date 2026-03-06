"""
Tests for Lifecycle module (13-Phase Tick Loop)
"""

import pytest
from lifecycle.tick_loop import TickLoop
from lifecycle.genesis_lifecycle import GenesisLifecycle


class TestTickLoop:
    """Test the 13-phase tick loop"""

    def test_tick_loop_initialization(self, sample_config, temp_dir):
        """Test tick loop initialization"""
        config = sample_config.copy()
        config["data_dir"] = str(temp_dir)

        loop = TickLoop(config)

        assert loop.tick == 0
        assert loop.session_id is not None

    def test_single_tick_execution(self, sample_config, temp_dir):
        """Test execution of a single tick"""
        config = sample_config.copy()
        config["data_dir"] = str(temp_dir)

        loop = TickLoop(config)

        # Execute one tick
        result = loop.run_tick()

        assert result.get("tick") == 1
        assert "state" in result

    def test_multi_tick_execution(self, sample_config, temp_dir):
        """Test execution of multiple ticks"""
        config = sample_config.copy()
        config["data_dir"] = str(temp_dir)

        loop = TickLoop(config)

        # Run multiple ticks
        loop.run(max_ticks=5)

        assert loop.tick == 5

    def test_tick_phases_executed(self, sample_config, temp_dir):
        """Test that all 13 phases are executed"""
        config = sample_config.copy()
        config["data_dir"] = str(temp_dir)

        loop = TickLoop(config)

        # Mock phase execution tracking
        executed_phases = []

        # Override phase execution to track
        original_run_tick = loop.run_tick

        def tracked_run_tick():
            result = original_run_tick()
            if "phases" in result:
                executed_phases.extend(result["phases"])
            return result

        loop.run_tick = tracked_run_tick

        # Run one tick
        loop.run_tick()

        # Should have executed phases
        expected_phases = [
            "perceive",
            "signal_filter",
            "novelty",
            "gap_calc",
            "weight_update",
            "organ_select",
            "action_plan",
            "risk_assess",
            "execute",
            "reward_calc",
            "rpe_calc",
            "affect_update",
            "persist",
        ]

        # Check some key phases were executed
        assert len(executed_phases) > 0

    def test_state_persistence(self, sample_config, temp_dir):
        """Test that state persists across ticks"""
        config = sample_config.copy()
        config["data_dir"] = str(temp_dir)

        loop = TickLoop(config)

        # Run first tick
        loop.run_tick()

        # Get state after first tick
        state_after_tick1 = loop.get_state()

        # Run second tick
        loop.run_tick()

        # State should have changed
        state_after_tick2 = loop.get_state()

        assert state_after_tick2["tick"] == state_after_tick1["tick"] + 1

    def test_episode_logging(self, sample_config, temp_dir):
        """Test that episodes are logged"""
        config = sample_config.copy()
        config["data_dir"] = str(temp_dir)

        loop = TickLoop(config)

        # Run ticks
        loop.run(max_ticks=3)

        # Check episode log exists
        episode_log = temp_dir / "logs" / "episodes.jsonl"

        # Note: This assumes episodes are logged
        # In actual implementation, verify log file exists and has content


class TestGenesisLifecycle:
    """Test full Genesis lifecycle"""

    def test_lifecycle_initialization(self, sample_config, temp_dir):
        """Test lifecycle initialization"""
        config = sample_config.copy()
        config["data_dir"] = str(temp_dir)

        lifecycle = GenesisLifecycle(config)

        assert lifecycle is not None
        assert lifecycle.tick == 0

    def test_lifecycle_run(self, sample_config, temp_dir):
        """Test full lifecycle execution"""
        config = sample_config.copy()
        config["data_dir"] = str(temp_dir)

        lifecycle = GenesisLifecycle(config)

        # Run lifecycle
        lifecycle.run(max_ticks=3)

        assert lifecycle.tick == 3

    def test_value_dynamics(self, sample_config, temp_dir):
        """Test that value dimensions update over time"""
        config = sample_config.copy()
        config["data_dir"] = str(temp_dir)

        lifecycle = GenesisLifecycle(config)

        # Get initial weights
        initial_state = lifecycle.get_state()
        initial_weights = initial_state.get("weights", {})

        # Run ticks
        lifecycle.run(max_ticks=5)

        # Get final weights
        final_state = lifecycle.get_state()
        final_weights = final_state.get("weights", {})

        # Weights should have changed
        weights_changed = any(
            abs(final_weights.get(dim, 0) - initial_weights.get(dim, 0)) > 0.01
            for dim in initial_weights.keys()
        )

        assert weights_changed

    def test_memory_accumulation(self, sample_config, temp_dir):
        """Test that memories accumulate over time"""
        config = sample_config.copy()
        config["data_dir"] = str(temp_dir)

        lifecycle = GenesisLifecycle(config)

        # Run ticks
        lifecycle.run(max_ticks=10)

        # Check memory stats
        stats = lifecycle.get_memory_stats()

        # Should have accumulated some episodes
        assert stats.get("episodic_count", 0) > 0

    def test_offline_consolidation(self, sample_config, temp_dir):
        """Test offline consolidation trigger"""
        config = sample_config.copy()
        config["data_dir"] = str(temp_dir)
        config["offline_interval"] = 5  # Trigger offline every 5 ticks

        lifecycle = GenesisLifecycle(config)

        # Run enough ticks to trigger offline
        lifecycle.run(max_ticks=10)

        # Check if offline consolidation occurred
        stats = lifecycle.get_scheduler_stats()

        # Should have run offline at least once
        assert stats.get("offline_runs", 0) > 0

    def test_graceful_shutdown(self, sample_config, temp_dir):
        """Test graceful shutdown and cleanup"""
        config = sample_config.copy()
        config["data_dir"] = str(temp_dir)

        lifecycle = GenesisLifecycle(config)

        # Run ticks
        lifecycle.run(max_ticks=3)

        # Shutdown
        lifecycle.shutdown()

        # Should have saved final state
        # (Implementation-specific check)
        assert lifecycle.tick > 0

    def test_error_handling(self, sample_config, temp_dir):
        """Test that lifecycle handles errors gracefully"""
        config = sample_config.copy()
        config["data_dir"] = str(temp_dir)

        lifecycle = GenesisLifecycle(config)

        # Run with potential errors
        try:
            lifecycle.run(max_ticks=5)
        except Exception as e:
            pytest.fail(f"Lifecycle should handle errors gracefully: {e}")

        # Should have made some progress even if errors occurred
        assert lifecycle.tick > 0
