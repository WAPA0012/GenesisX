"""Skill Memory - executable procedures with risk/cost profiles."""
from typing import List, Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel, Field
from common.models import Action, CostVector
from common.logger import get_logger
from common.jsonl import JSONLWriter
from common.hashing import hash_dict

logger = get_logger(__name__)


class SkillEntry(BaseModel):
    """A learned skill (macro-action).

    From Section 3.10.3: skills are learned procedures that can be invoked as single actions.
    """
    # Core fields
    name: str = Field(..., description="Skill name/identifier")
    description: str = Field("", description="What this skill does")

    # Execution spec
    action_sequence: List[Action] = Field(..., description="Sequence of actions to execute")
    success_criteria: str = Field("", description="How to verify success")

    # Cost and risk
    estimated_cost: CostVector = Field(default_factory=CostVector)
    risk_level: float = Field(0.0, ge=0.0, le=1.0, description="Risk level")

    # Capabilities required
    capabilities: List[str] = Field(default_factory=list, description="Required capabilities")

    # Performance tracking
    invocation_count: int = Field(0, ge=0)
    success_count: int = Field(0, ge=0)
    failure_count: int = Field(0, ge=0)
    average_reward: float = Field(0.0)

    # Metadata
    created_tick: int = Field(..., description="When skill was created")
    last_used_tick: Optional[int] = None
    evidence_refs: List[int] = Field(default_factory=list, description="Episode refs for learning this skill")

    # Tags for retrieval
    tags: List[str] = Field(default_factory=list)

    # For deduplication
    skill_id: Optional[str] = None

    def success_rate(self) -> float:
        """Calculate success rate.

        Returns:
            Success rate ∈ [0,1]
        """
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.0
        return self.success_count / total


class SkillMemory:
    """Skill memory layer.

    Stores learned procedures as macro-actions.
    Tracks performance and prunes low-performing skills.
    Supports persistence to disk for long-term storage.
    """

    # 修复 M8: 论文 Appendix A.7 要求 Skill 容量上限 N_sk = 300
    MAX_CAPACITY: int = 300

    def __init__(self, persist_path: Optional[Path] = None, max_capacity: int = None):
        """Initialize skill memory.

        Args:
            persist_path: Optional path to persist skills to disk
            max_capacity: Maximum capacity (论文默认 300)
        """
        self._skills: List[SkillEntry] = []
        self._name_index: Dict[str, int] = {}  # name -> index
        self._id_index: Dict[str, int] = {}  # skill_id -> index
        self.persist_path = persist_path
        self.max_capacity = max_capacity or self.MAX_CAPACITY

        # Load from disk if path provided
        if self.persist_path and self.persist_path.exists():
            self.load_from_disk()

    def save_to_disk(self) -> bool:
        """Save all skills to disk.

        Returns:
            True if successful, False otherwise
        """
        if not self.persist_path:
            logger.debug("No persist path set, skipping save")
            return False

        try:
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)

            # Use JSONL format for consistent storage
            writer = JSONLWriter(self.persist_path)
            writer.open()

            for skill in self._skills:
                writer.write(skill.model_dump())

            writer.close()
            logger.info(f"Saved {len(self._skills)} skills to {self.persist_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save skills to disk: {e}")
            return False

    def load_from_disk(self) -> bool:
        """Load skills from disk.

        Returns:
            True if successful, False otherwise
        """
        if not self.persist_path or not self.persist_path.exists():
            logger.debug("No persist file exists, skipping load")
            return False

        try:
            from common.jsonl import read_jsonl

            skills_loaded = 0
            for record in read_jsonl(self.persist_path):
                try:
                    skill = SkillEntry(**record)
                    # Add without generating new ID
                    if skill.name not in self._name_index:
                        idx = len(self._skills)
                        self._skills.append(skill)
                        self._name_index[skill.name] = idx
                        if skill.skill_id:
                            self._id_index[skill.skill_id] = idx
                        skills_loaded += 1
                    else:
                        logger.debug(f"Skill '{skill.name}' already exists, skipping load")
                except Exception as e:
                    logger.warning(f"Failed to load skill record: {e}")

            logger.info(f"Loaded {skills_loaded} skills from {self.persist_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to load skills from disk: {e}")
            return False

    def add(self, skill: SkillEntry):
        """Add a new skill (修复 M8: 含容量限制).

        论文 Appendix A.7: Skill budget N_sk = 300.
        超出容量时淘汰最低成功率的 skill。

        Args:
            skill: Skill to add
        """
        # Generate ID if not present
        if skill.skill_id is None:
            skill.skill_id = self._generate_id(skill)

        # Check for duplicates
        if skill.name in self._name_index:
            logger.debug(f"Skill '{skill.name}' already exists, skipping")
            return

        # 修复 M8: 超出容量时淘汰最低成功率的 skill
        if len(self._skills) >= self.max_capacity:
            self._evict_lowest_performing()

        idx = len(self._skills)
        self._skills.append(skill)
        self._name_index[skill.name] = idx
        self._id_index[skill.skill_id] = idx

    def _evict_lowest_performing(self):
        """淘汰成功率最低的 skill (修复 M8)."""
        if not self._skills:
            return

        # 找到成功率最低的 skill
        min_idx = 0
        min_rate = self._skills[0].success_rate()
        for i, s in enumerate(self._skills):
            rate = s.success_rate()
            if rate < min_rate:
                min_rate = rate
                min_idx = i

        evicted = self._skills[min_idx]
        logger.debug(f"Evicted skill (success_rate={min_rate:.2f}): {evicted.name}")

        # 移除
        self._skills.pop(min_idx)
        self._rebuild_indices()

    def _rebuild_indices(self):
        """Rebuild name and ID indices after eviction."""
        self._name_index = {}
        self._id_index = {}
        for i, s in enumerate(self._skills):
            self._name_index[s.name] = i
            if s.skill_id:
                self._id_index[s.skill_id] = i

    def _generate_id(self, skill: SkillEntry) -> str:
        """Generate a unique ID for skill.

        Args:
            skill: Skill entry

        Returns:
            Skill ID
        """
        return hash_dict({"name": skill.name, "actions": [a.type for a in skill.action_sequence]})[:16]

    def get_by_name(self, name: str) -> Optional[SkillEntry]:
        """Get skill by name.

        Args:
            name: Skill name

        Returns:
            Skill or None
        """
        idx = self._name_index.get(name)
        if idx is not None:
            return self._skills[idx]
        return None

    def record_invocation(self, skill_name: str, success: bool, reward: float, tick: int):
        """Record skill invocation result.

        Args:
            skill_name: Name of skill
            success: Whether invocation succeeded
            reward: Reward obtained
            tick: Current tick
        """
        idx = self._name_index.get(skill_name)
        if idx is None:
            return

        skill = self._skills[idx]
        skill.invocation_count += 1
        skill.last_used_tick = tick

        if success:
            skill.success_count += 1
        else:
            skill.failure_count += 1

        # Update average reward (exponential moving average)
        alpha = 0.2
        skill.average_reward = (1 - alpha) * skill.average_reward + alpha * reward

    def query_by_tags(self, tags: List[str], min_success_rate: float = 0.5) -> List[SkillEntry]:
        """Query skills by tags.

        Args:
            tags: Tags to match
            min_success_rate: Minimum success rate threshold

        Returns:
            List of matching skills
        """
        matches = [
            s for s in self._skills
            if any(tag in s.tags for tag in tags) and s.success_rate() >= min_success_rate
        ]
        return matches

    def query_by_capabilities(self, required_caps: List[str]) -> List[SkillEntry]:
        """Query skills by required capabilities.

        Args:
            required_caps: Required capabilities

        Returns:
            List of skills that require these capabilities
        """
        matches = [
            s for s in self._skills
            if any(cap in s.capabilities for cap in required_caps)
        ]
        return matches

    def get_high_performing(self, min_success_rate: float = 0.7, min_invocations: int = 3) -> List[SkillEntry]:
        """Get high-performing skills.

        Args:
            min_success_rate: Minimum success rate
            min_invocations: Minimum number of invocations

        Returns:
            List of high-performing skills
        """
        return [
            s for s in self._skills
            if s.invocation_count >= min_invocations and s.success_rate() >= min_success_rate
        ]

    def prune_low_performing(self, max_failure_rate: float = 0.8, min_invocations: int = 5):
        """Remove low-performing skills.

        Args:
            max_failure_rate: Maximum failure rate to keep
            min_invocations: Minimum invocations before pruning
        """
        kept = [
            s for s in self._skills
            if s.invocation_count < min_invocations or s.success_rate() > (1 - max_failure_rate)
        ]

        # Rebuild indices
        self._skills = kept
        self._name_index = {s.name: i for i, s in enumerate(self._skills)}
        self._id_index = {s.skill_id: i for i, s in enumerate(self._skills) if s.skill_id is not None}

    def count(self) -> int:
        """Get skill count.

        Returns:
            Number of skills
        """
        return len(self._skills)

    def get_all(self) -> List[SkillEntry]:
        """Get all skills.

        Returns:
            All skills
        """
        return self._skills.copy()

    @property
    def skills(self) -> List[SkillEntry]:
        """Public property accessor for skills (used by chat.py).

        Returns:
            List of all skills
        """
        return self._skills.copy()
