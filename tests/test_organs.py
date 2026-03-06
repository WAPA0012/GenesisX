"""
Tests for Organ system (Dynamic Organ Differentiation)
"""

import pytest
from organs.organ_selector import OrganSelector
from organs.organ_interface import OrganInterface


class TestOrganSelector:
    """Test organ selection logic"""

    def test_select_organ_by_signal(self, sample_config):
        """Test organ selection based on signal type"""
        selector = OrganSelector(sample_config)

        # Homeostasis signal -> Caretaker
        signal = {
            "type": "homeostasis_low",
            "value": 0.2,
        }

        organ_id = selector.select_organ(signal=signal, stage="adult", mode="work")

        assert organ_id == "caretaker"

    def test_select_organ_by_stage(self, sample_config):
        """Test that stage affects organ selection"""
        selector = OrganSelector(sample_config)

        signal = {
            "type": "exploration",
            "value": 0.8,
        }

        # Child stage might select Scout more often
        organ_id = selector.select_organ(signal=signal, stage="child", mode="play")

        assert organ_id in ["scout", "mind", "builder"]

    def test_select_organ_by_mode(self, sample_config):
        """Test that mode affects organ selection"""
        selector = OrganSelector(sample_config)

        signal = {
            "type": "task",
            "value": 0.5,
        }

        # Work mode -> Mind or Builder
        organ_id = selector.select_organ(signal=signal, stage="adult", mode="work")

        assert organ_id in ["mind", "builder"]

        # Rest mode -> Caretaker or Archivist
        organ_id = selector.select_organ(signal=signal, stage="adult", mode="rest")

        assert organ_id in ["caretaker", "archivist"]

    def test_select_organ_urgency(self, sample_config):
        """Test that urgency overrides normal selection"""
        selector = OrganSelector(sample_config)

        # High urgency signal
        signal = {
            "type": "threat",
            "value": 0.95,
            "urgency": 1.0,
        }

        organ_id = selector.select_organ(signal=signal, stage="adult", mode="work")

        # Should select Immune for threat
        assert organ_id == "immune"

    def test_organ_availability(self, sample_config):
        """Test that only available organs are selected"""
        selector = OrganSelector(sample_config)

        # Disable Scout organ
        selector.available_organs = {
            "caretaker": True,
            "immune": True,
            "mind": True,
            "scout": False,  # Disabled
            "builder": True,
            "archivist": True,
        }

        signal = {
            "type": "exploration",
            "value": 0.8,
        }

        organ_id = selector.select_organ(signal=signal, stage="adult", mode="work")

        # Should not select Scout
        assert organ_id != "scout"


class TestOrganInterface:
    """Test organ interface and execution"""

    def test_organ_process_signal(self, sample_config):
        """Test that organs can process signals"""
        interface = OrganInterface(sample_config)

        signal = {
            "type": "task",
            "content": "analyze data",
        }

        # Mind organ should process analysis tasks
        result = interface.process_signal(
            organ_id="mind",
            signal=signal
        )

        assert "output" in result
        assert result.get("success") is not None

    def test_organ_tool_execution(self, sample_config):
        """Test that organs can execute tools"""
        interface = OrganInterface(sample_config)

        action = {
            "tool_id": "web_search",
            "parameters": {
                "query": "test query"
            }
        }

        # Scout organ should handle web search
        result = interface.execute_action(
            organ_id="scout",
            action=action
        )

        assert "output" in result or "error" in result

    def test_organ_risk_assessment(self, sample_config):
        """Test pre-execution risk assessment"""
        interface = OrganInterface(sample_config)

        # High-risk action
        action = {
            "tool_id": "file_write",
            "parameters": {
                "path": "/system/important.txt",
                "content": "test"
            }
        }

        risk_score = interface.assess_risk(action)

        assert isinstance(risk_score, float)
        assert 0.0 <= risk_score <= 1.0
        assert risk_score > 0.5  # File write should have medium+ risk

    def test_organ_mode_restrictions(self, sample_config):
        """Test that offline mode restricts high-risk tools"""
        interface = OrganInterface(sample_config)

        high_risk_action = {
            "tool_id": "code_exec",
            "parameters": {
                "code": "print('test')"
            }
        }

        # Should fail in offline mode
        result = interface.execute_action(
            organ_id="builder",
            action=high_risk_action,
            is_offline=True
        )

        assert result.get("success") is False or "error" in result

        # Should succeed in online mode
        result = interface.execute_action(
            organ_id="builder",
            action=high_risk_action,
            is_offline=False
        )

        # May still fail for other reasons, but not due to offline restriction
        assert "offline" not in str(result.get("error", "")).lower()

    def test_organ_specialization(self, sample_config):
        """Test that organs have specialized capabilities"""
        interface = OrganInterface(sample_config)

        # Caretaker should handle homeostasis
        caretaker_signal = {
            "type": "homeostasis_low",
            "value": 0.3,
        }

        result = interface.process_signal("caretaker", caretaker_signal)
        assert result.get("success") is not False

        # Archivist should handle memory operations
        archivist_signal = {
            "type": "memory_consolidation",
            "episodes": [],
        }

        result = interface.process_signal("archivist", archivist_signal)
        assert result.get("success") is not False

    def test_organ_state_tracking(self, sample_config):
        """Test that organ execution state is tracked"""
        interface = OrganInterface(sample_config)

        signal = {
            "type": "task",
            "content": "test task",
        }

        # Execute multiple times
        for i in range(3):
            interface.process_signal("mind", signal)

        stats = interface.get_organ_stats("mind")

        assert "execution_count" in stats
        assert stats["execution_count"] >= 3
