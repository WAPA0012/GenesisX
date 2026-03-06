"""
Pytest configuration and shared fixtures for Genesis X tests.

Provides comprehensive fixtures for:
- Test database and storage
- Mock Genesis X instances
- Test users and authentication
- API clients
- Mock LLM responses
- Test configuration
- Cleanup logic
"""

import pytest
from pathlib import Path
import tempfile
import shutil
from typing import Dict, Any, List
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
import json

# Genesis X imports
from core.state import GlobalState
from core.life_loop import LifeLoop
from common.models import (
    ValueDimension, Action, Observation, EpisodeRecord,
    CostVector, Outcome
)
from memory.episodic import EpisodicMemory
from persistence.replay import ReplayEngine, ReplayMode


# ============================================================================
# Directory and Storage Fixtures
# ============================================================================

@pytest.fixture
def temp_dir():
    """Temporary directory for test data."""
    temp = tempfile.mkdtemp()
    yield Path(temp)
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def test_artifacts_dir(temp_dir):
    """Test artifacts directory structure."""
    artifacts = temp_dir / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    (artifacts / "runs").mkdir()
    (artifacts / "snapshots").mkdir()
    (artifacts / "forks").mkdir()

    yield artifacts


@pytest.fixture
def test_run_dir(test_artifacts_dir):
    """Test run directory with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = test_artifacts_dir / f"run_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    yield run_dir


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def base_config():
    """Base configuration for Genesis X tests.

    修复 v15: 使用5维核心价值向量 (论文 Section 3.5.1)
    """
    return {
        "runtime": {
            "max_ticks": 100,
            "tick_dt": 1.0,
        },
        "axiology": {
            # 5维核心价值向量
            "dimensions": [
                "homeostasis", "attachment", "curiosity", "competence", "safety"
            ],
            "temperature": 2.0,
            "inertia": 0.3,
        },
        "value_setpoints": {
            "tau": 2.0,
            "value_dimensions": {
                "homeostasis": {"setpoint": 0.85, "weight": 0.2},
                "attachment": {"setpoint": 0.70, "weight": 0.2},
                "curiosity": {"setpoint": 0.60, "weight": 0.2},
                "competence": {"setpoint": 0.75, "weight": 0.2},
                "safety": {"setpoint": 0.70, "weight": 0.2},
            }
        },
        "genome": {
            "affect": {
                "gamma": 0.95,
                "k_plus": 0.1,
                "k_minus": 0.15,
            }
        },
        "memory": {
            "max_episodic": 100,
            "max_schema": 20,
            "max_skills": 10,
            "consolidation_threshold": 50,
        },
        "tools": {
            "max_risk_online": 1.0,
            "max_risk_offline": 0.3,
        },
        "api_key": "test_api_key",
        "cors_origins": ["*"],
        "data_dir": "artifacts",
    }


@pytest.fixture
def sample_config(base_config):
    """Alias for backward compatibility."""
    return base_config


# ============================================================================
# State and Data Fixtures
# ============================================================================

@pytest.fixture
def initial_state():
    """Initial global state for testing."""
    state = GlobalState()
    state.energy = 0.8
    state.mood = 0.5
    state.stress = 0.2
    state.fatigue = 0.1
    state.bond = 0.0
    state.trust = 0.5
    state.boredom = 0.0
    state.value_pred = 0.0
    state.tick = 0
    return state


@pytest.fixture
def sample_state():
    """Sample state dict for testing."""
    return {
        "tick": 0,
        "energy": 0.8,
        "mood": 0.5,
        "stress": 0.2,
        "fatigue": 0.1,
        "bond": 0.0,
        "trust": 0.5,
        "boredom": 0.0,
        "current_goal": "test_goal",
        "mode": "work",
        "stage": "adult",
        "episodic_count": 0,
        "schema_count": 0,
        "skill_count": 0,
    }


@pytest.fixture
def sample_context():
    """Sample context for organ testing."""
    return {
        "goal": "test_goal",
        "tick_duration": 10,
        "mode": "work",
        "weights": {dim: 0.125 for dim in ValueDimension},
    }


@pytest.fixture
def sample_observation():
    """Sample observation for testing."""
    return Observation(
        type="heartbeat",
        payload={"message": "test"},
        tick=0
    )


@pytest.fixture
def sample_action():
    """Sample action for testing."""
    return Action(
        type="CHAT",
        params={"message": "test"},
        risk_level=0.1,
        capability_req=[]
    )


@pytest.fixture
def sample_episode():
    """Sample episode record for testing."""
    return EpisodeRecord(
        tick=1,
        session_id="test_session",
        observation=Observation(type="test", payload={}, tick=1),
        action=Action(type="CHAT", params={}),
        reward=0.5,
        delta=0.2,
        value_pred=0.0,
        state_snapshot={
            "energy": 0.8,
            "mood": 0.5,
            "stress": 0.2,
        },
        weights={dim.value: 0.125 for dim in ValueDimension},
        gaps={dim.value: 0.1 for dim in ValueDimension},
        utilities={dim.value: 0.0 for dim in ValueDimension},
        current_goal="test_goal",
    )


# ============================================================================
# Genesis X Instance Fixtures
# ============================================================================

@pytest.fixture
def mock_genesis_instance(base_config, test_run_dir):
    """Mock Genesis X life loop instance."""
    life_loop = LifeLoop(config=base_config, run_dir=test_run_dir)
    return life_loop


@pytest.fixture
def genesis_with_state(mock_genesis_instance, initial_state):
    """Genesis X instance with initialized state."""
    mock_genesis_instance.state = initial_state
    return mock_genesis_instance


# ============================================================================
# Memory Fixtures
# ============================================================================

@pytest.fixture
def test_episodic_memory(temp_dir):
    """Episodic memory instance for testing."""
    episodes_path = temp_dir / "episodes.jsonl"
    memory = EpisodicMemory(episodes_path)
    return memory


@pytest.fixture
def episodic_memory_with_data(test_episodic_memory):
    """Episodic memory populated with test data."""
    for i in range(10):
        episode = EpisodeRecord(
            tick=i,
            session_id="test_session",
            observation=Observation(type="test", payload={"index": i}, tick=i),
            action=Action(type="CHAT", params={}),
            reward=0.5 + i * 0.01,
            delta=0.1,
            value_pred=0.0,
            state_snapshot={"tick": i, "energy": 0.8 - i * 0.01},
            weights={dim.value: 0.125 for dim in ValueDimension},
            gaps={dim.value: 0.1 for dim in ValueDimension},
            utilities={dim.value: 0.0 for dim in ValueDimension},
            current_goal=f"goal_{i % 3}",
            tags=[f"tag_{i % 2}"]
        )
        test_episodic_memory.append(episode)

    return test_episodic_memory


# ============================================================================
# Mock LLM Fixtures
# ============================================================================

@pytest.fixture
def mock_llm_response():
    """Mock LLM response generator."""
    def _generate_response(prompt: str, **kwargs) -> str:
        """Generate mock LLM response based on prompt."""
        if "plan" in prompt.lower():
            return "Test plan: 1. First step, 2. Second step, 3. Third step"
        elif "goal" in prompt.lower():
            return "Test goal decomposition: subgoal_1, subgoal_2, subgoal_3"
        elif "reflect" in prompt.lower():
            return "Reflection: This is a test reflection response"
        elif "explore" in prompt.lower():
            return "Exploration: Found interesting patterns in the test data"
        else:
            return "Generic test response"

    return _generate_response


@pytest.fixture
def mock_llm_client(mock_llm_response):
    """Mock LLM client for testing."""
    mock = Mock()
    mock.generate = Mock(side_effect=lambda prompt, **kwargs: mock_llm_response(prompt))
    mock.complete = Mock(side_effect=lambda prompt, **kwargs: mock_llm_response(prompt))
    mock.chat = Mock(side_effect=lambda messages, **kwargs: mock_llm_response(messages[-1].get("content", "")))
    return mock


@pytest.fixture
def patch_llm_calls(mock_llm_client):
    """Patch all LLM API calls with mocks."""
    with patch("tools.llm_api.UniversalLLM", return_value=mock_llm_client):
        yield mock_llm_client


# ============================================================================
# Persistence Fixtures
# ============================================================================

@pytest.fixture
def test_replay_dir(test_artifacts_dir):
    """Directory with test replay data."""
    replay_dir = test_artifacts_dir / "replay_test"
    replay_dir.mkdir(parents=True, exist_ok=True)

    # Create test episodes
    episodes_file = replay_dir / "episodes.jsonl"
    with open(episodes_file, 'w') as f:
        for i in range(5):
            episode = {
                "tick": i,
                "session_id": "test_session",
                "observation": {"type": "test", "payload": {}, "tick": i},
                "action": {"type": "CHAT", "params": {}},
                "reward": 0.5,
                "delta": 0.1,
                "value_pred": 0.0,
                "state_snapshot": {"tick": i},
                "weights": {dim.value: 0.125 for dim in ValueDimension},
                "gaps": {dim.value: 0.1 for dim in ValueDimension},
            }
            f.write(json.dumps(episode) + '\n')

    yield replay_dir


@pytest.fixture
def replay_engine(test_replay_dir):
    """Replay engine for testing."""
    return ReplayEngine(test_replay_dir, ReplayMode.STRICT)


# ============================================================================
# User and Authentication Fixtures
# ============================================================================

@pytest.fixture
def test_user():
    """Test user data."""
    return {
        "user_id": "test_user_001",
        "username": "test_user",
        "email": "test@example.com",
        "auth_token": "test_auth_token_12345",
        "permissions": ["read", "write", "execute"],
        "created_at": datetime.now().isoformat(),
    }


@pytest.fixture
def authenticated_headers(test_user):
    """Headers with authentication for API testing."""
    return {
        "Authorization": f"Bearer {test_user['auth_token']}",
        "Content-Type": "application/json",
    }


# ============================================================================
# Parametrized Test Data
# ============================================================================

@pytest.fixture(params=[
    {"energy": 0.2, "stress": 0.8, "expected_intervention": True},
    {"energy": 0.8, "stress": 0.2, "expected_intervention": False},
    {"energy": 0.5, "stress": 0.5, "expected_intervention": False},
])
def caretaker_scenarios(request):
    """Parametrized scenarios for caretaker organ testing."""
    return request.param


@pytest.fixture(params=[
    {"boredom": 0.8, "energy": 0.7, "should_explore": True},
    {"boredom": 0.2, "energy": 0.7, "should_explore": False},
    {"boredom": 0.8, "energy": 0.2, "should_explore": False},
])
def scout_scenarios(request):
    """Parametrized scenarios for scout organ testing."""
    return request.param


@pytest.fixture(params=list(ValueDimension))
def all_value_dimensions(request):
    """All value dimensions for parametrized tests."""
    return request.param


# ============================================================================
# Cleanup and Utilities
# ============================================================================

@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset any singleton instances between tests."""
    yield
    # Add cleanup for any singletons if needed


@pytest.fixture
def capture_logs():
    """Capture log output during tests."""
    import logging
    from io import StringIO

    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    yield log_capture

    logger.removeHandler(handler)


@pytest.fixture
def performance_timer():
    """Timer for performance testing."""
    import time

    timings = {}

    class Timer:
        def start(self, name: str):
            timings[name] = {"start": time.time()}

        def stop(self, name: str):
            if name in timings:
                timings[name]["end"] = time.time()
                timings[name]["duration"] = timings[name]["end"] - timings[name]["start"]

        def get_duration(self, name: str) -> float:
            return timings.get(name, {}).get("duration", 0.0)

        def get_all_timings(self) -> Dict[str, float]:
            return {name: data.get("duration", 0.0) for name, data in timings.items()}

    return Timer()


# ============================================================================
# Assertion Helpers
# ============================================================================

@pytest.fixture
def assert_state_valid():
    """Helper to assert state validity."""
    def _assert_valid(state: GlobalState):
        """Assert that state has valid values."""
        assert 0.0 <= state.energy <= 1.0, f"Invalid energy: {state.energy}"
        assert 0.0 <= state.mood <= 1.0, f"Invalid mood: {state.mood}"
        assert 0.0 <= state.stress <= 1.0, f"Invalid stress: {state.stress}"
        assert 0.0 <= state.fatigue <= 1.0, f"Invalid fatigue: {state.fatigue}"
        assert 0.0 <= state.bond <= 1.0, f"Invalid bond: {state.bond}"
        assert 0.0 <= state.trust <= 1.0, f"Invalid trust: {state.trust}"
        assert 0.0 <= state.boredom <= 1.0, f"Invalid boredom: {state.boredom}"
        assert state.tick >= 0, f"Invalid tick: {state.tick}"

    return _assert_valid


@pytest.fixture
def assert_episode_valid():
    """Helper to assert episode validity."""
    def _assert_valid(episode: EpisodeRecord):
        """Assert that episode has valid structure."""
        assert episode.tick >= 0
        assert episode.session_id
        assert -1.0 <= episode.reward <= 1.0
        assert len(episode.weights) == len(ValueDimension)
        assert len(episode.gaps) == len(ValueDimension)

        # Check weights sum to approximately 1
        weight_sum = sum(episode.weights.values())
        assert 0.99 <= weight_sum <= 1.01, f"Weights don't sum to 1: {weight_sum}"

    return _assert_valid
