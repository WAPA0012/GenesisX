"""Tests for organ system (P5-12: organ_selector/organ_interface 已删除，测试改为验证器官基本功能)"""
import pytest
from common.models import ValueDimension


class TestOrganBasics:
    """验证 6 个内置器官的基本属性"""

    def test_all_organs_exist(self):
        """所有 6 个器官都能导入"""
        from organs.internal.mind_organ import MindOrgan
        from organs.internal.scout_organ import ScoutOrgan
        from organs.internal.builder_organ import BuilderOrgan
        from organs.internal.caretaker_organ import CaretakerOrgan
        from organs.internal.archivist_organ import ArchivistOrgan
        from organs.internal.immune_organ import ImmuneOrgan

        organs = [MindOrgan, ScoutOrgan, BuilderOrgan, CaretakerOrgan, ArchivistOrgan, ImmuneOrgan]
        assert len(organs) == 6

    def test_mind_organ_init(self):
        """Mind 器官能初始化"""
        from organs.internal.mind_organ import MindOrgan
        organ = MindOrgan()
        assert organ.name is not None
        assert hasattr(organ, 'plan_history')

    def test_scout_organ_init(self):
        """Scout 器官能初始化"""
        from organs.internal.scout_organ import ScoutOrgan
        organ = ScoutOrgan()
        assert organ.name is not None
        assert hasattr(organ, 'explored_topics')

    def test_caretaker_organ_init(self):
        """Caretaker 器官能初始化"""
        from organs.internal.caretaker_organ import CaretakerOrgan
        organ = CaretakerOrgan()
        assert organ.name is not None

    def test_immune_organ_init(self):
        """Immune 器官能初始化"""
        from organs.internal.immune_organ import ImmuneOrgan
        organ = ImmuneOrgan()
        assert organ.name is not None
