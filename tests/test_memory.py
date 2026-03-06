"""
Tests for Memory module (CLS - Complementary Learning Systems)
"""

import pytest
import numpy as np
from memory.gates import MemoryGate
from memory.indices import MemoryIndex
from memory.pruning import MemoryPruner


class TestMemoryGate:
    """Test memory gating mechanism"""

    def test_should_store_high_novelty(self, sample_config, sample_episode):
        """Test that high novelty episodes are stored"""
        gate = MemoryGate(sample_config.get("memory", {}))

        should_store, strength = gate.should_store_episodic(
            sample_episode,
            novelty_score=0.8
        )

        assert should_store is True
        assert strength > 0.3

    def test_should_not_store_low_novelty(self, sample_config, sample_episode):
        """Test that low novelty, low significance episodes are not stored"""
        gate = MemoryGate(sample_config.get("memory", {}))

        # Low novelty, low reward/delta episode
        episode = sample_episode.model_copy(update={"reward": 0.1, "delta": 0.05})

        should_store, strength = gate.should_store_episodic(
            episode,
            novelty_score=0.2
        )

        assert should_store is False

    def test_should_store_high_delta(self, sample_config, sample_episode):
        """Test that high RPE episodes are stored"""
        gate = MemoryGate(sample_config.get("memory", {}))

        episode = sample_episode.model_copy(update={"delta": 0.8})  # High prediction error

        should_store, strength = gate.should_store_episodic(
            episode,
            novelty_score=0.2  # Low novelty
        )

        assert should_store is True

    def test_consolidation_threshold(self, sample_config, sample_episode):
        """Test consolidation to schema based on frequency"""
        gate = MemoryGate(sample_config.get("memory", {}))

        # Seen 5 times -> should consolidate
        should_consolidate = gate.should_consolidate_to_schema(
            sample_episode,
            frequency=5
        )

        assert should_consolidate is True

        # Seen only once -> should not consolidate
        should_consolidate = gate.should_consolidate_to_schema(
            sample_episode,
            frequency=1
        )

        assert should_consolidate is False

    def test_skill_extraction(self, sample_config):
        """Test skill extraction based on success rate"""
        gate = MemoryGate(sample_config.get("memory", {}))

        action_sequence = ["action1", "action2", "action3"]

        # High success rate -> extract skill
        should_extract = gate.should_extract_skill(
            action_sequence,
            success_rate=0.9
        )

        assert should_extract is True

        # Low success rate -> don't extract
        should_extract = gate.should_extract_skill(
            action_sequence,
            success_rate=0.3
        )

        assert should_extract is False


class TestMemoryIndex:
    """Test memory indexing and retrieval"""

    def test_add_and_retrieve_episode(self, sample_config, sample_episode):
        """Test adding and retrieving episodes"""
        index = MemoryIndex(sample_config.get("memory", {}))

        episode_id = "test_episode_1"
        index.add_episode(episode_id, sample_episode)

        # Retrieve by time
        episodes = index.retrieve_by_time(
            start_tick=1,
            end_tick=1
        )

        assert len(episodes) == 1
        from memory.indices import _get_episode_attr
        assert _get_episode_attr(episodes[0], "tick", 0) == 1

    def test_retrieve_by_value(self, sample_config, sample_episode):
        """Test retrieval by reward value"""
        index = MemoryIndex(sample_config.get("memory", {}))

        # Add high and low value episodes
        high_value_episode = sample_episode.model_copy(update={"reward": 0.9})
        low_value_episode = sample_episode.model_copy(update={"reward": 0.2})

        index.add_episode("high", high_value_episode)
        index.add_episode("low", low_value_episode)

        # Retrieve high value only
        episodes = index.retrieve_by_value(min_reward=0.5)

        assert len(episodes) >= 1
        # Access episodes via helper function
        from memory.indices import _get_episode_attr
        assert all(_get_episode_attr(e, "reward", 0.0) >= 0.5 for e in episodes)

    def test_retrieve_by_tag(self, sample_config, sample_episode):
        """Test retrieval by tags"""
        index = MemoryIndex(sample_config.get("memory", {}))

        episode1 = sample_episode.model_copy(update={"tags": ["test", "important"]})
        episode2 = sample_episode.model_copy(update={"tags": ["test"]})

        index.add_episode("ep1", episode1)
        index.add_episode("ep2", episode2)

        # Retrieve by tag
        episodes = index.retrieve_by_tag(tags=["important"])

        assert len(episodes) >= 1
        from memory.indices import _get_episode_attr
        assert any("important" in _get_episode_attr(e, "tags", []) for e in episodes)

    def test_retrieve_by_similarity(self, sample_config, sample_episode):
        """Test embedding-based similarity retrieval"""
        index = MemoryIndex(sample_config.get("memory", {}))

        # Add episodes with embeddings
        embedding1 = np.array([1.0, 0.0, 0.0])
        embedding2 = np.array([0.9, 0.1, 0.0])  # Similar to embedding1
        embedding3 = np.array([0.0, 0.0, 1.0])  # Different

        index.add_episode("ep1", sample_episode, embedding1)
        index.add_episode("ep2", sample_episode, embedding2)
        index.add_episode("ep3", sample_episode, embedding3)

        # Query with embedding similar to ep1/ep2
        query = np.array([1.0, 0.0, 0.0])

        episodes = index.retrieve_by_similarity(
            query_embedding=query,
            min_similarity=0.5
        )

        # Should return ep1 and ep2, not ep3
        assert len(episodes) >= 2

    def test_remove_episode(self, sample_config, sample_episode):
        """Test episode removal from indices"""
        index = MemoryIndex(sample_config.get("memory", {}))

        episode_id = "test_episode"
        index.add_episode(episode_id, sample_episode)

        # Remove episode
        index.remove_episode(episode_id)

        # Verify removed
        episodes = index.retrieve_by_time(start_tick=1, end_tick=1)
        assert len(episodes) == 0


class TestMemoryPruner:
    """Test memory pruning and consolidation"""

    def test_should_prune_at_capacity(self, sample_config):
        """Test that pruning triggers near capacity"""
        pruner = MemoryPruner(sample_config.get("memory", {}))

        max_capacity = 100

        # At 95% capacity -> should prune
        should_prune = pruner.should_prune(
            current_count=95,
            max_capacity=max_capacity
        )

        assert should_prune is True

        # At 50% capacity -> should not prune
        should_prune = pruner.should_prune(
            current_count=50,
            max_capacity=max_capacity
        )

        assert should_prune is False

    def test_select_episodes_to_prune(self, sample_config, sample_episode):
        """Test selection of episodes for pruning"""
        pruner = MemoryPruner(sample_config.get("memory", {}))

        # Create episodes with varying importance
        episodes = []
        for i in range(10):
            ep = sample_episode.model_copy(update={
                "episode_id": f"ep_{i}",
                "reward": i / 10.0
            })
            episodes.append(ep)

        # Prune to keep only 5
        to_prune = pruner.select_episodes_to_prune(episodes, target_count=5)

        assert len(to_prune) == 5

    def test_consolidate_episodes(self, sample_config, sample_episode):
        """Test episode consolidation into schemas"""
        pruner = MemoryPruner(sample_config.get("memory", {}))

        # Create similar episodes
        episodes = []
        for i in range(5):
            ep = sample_episode.model_copy(update={
                "episode_id": f"ep_{i}",
                "tags": ["similar", "test"]
            })
            episodes.append(ep)

        schemas = pruner.consolidate_episodes(episodes)

        # Should create at least one schema
        assert len(schemas) >= 1
        assert "episode_count" in schemas[0]

    def test_extract_skills(self, sample_config, sample_episode):
        """Test skill extraction from repeated patterns"""
        pruner = MemoryPruner(sample_config.get("memory", {}))

        # Create episodes with repeated successful actions
        episodes = []
        for i in range(5):
            ep = sample_episode.model_copy(update={
                "episode_id": f"ep_{i}",
                "action": {"tool_id": "web_search"},
                "reward": 0.8
            })
            episodes.append(ep)

        skills = pruner.extract_skills(episodes)

        # Should extract web_search skill
        assert len(skills) >= 1
        assert any("web_search" in s["skill_id"] for s in skills)
