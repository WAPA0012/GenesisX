"""Schema Memory - compressed knowledge with evidence and confidence."""
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field

from common.logger import get_logger
from common.jsonl import JSONLWriter
from common.hashing import hash_dict

logger = get_logger(__name__)


class SchemaEntry(BaseModel):
    """A schema entry (belief/knowledge claim).

    From Section 3.10.3: schemas compress episodic patterns into beliefs.
    """
    # Core fields
    claim: str = Field(..., description="The belief/knowledge statement")
    scope: str = Field(..., description="Scope of applicability (general/specific/conditional)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence ∈ [0,1]")

    # Evidence
    evidence_refs: List[int] = Field(default_factory=list, description="Episode tick refs")
    supporting_count: int = Field(0, ge=0, description="Number of supporting episodes")
    conflicting_count: int = Field(0, ge=0, description="Number of conflicting episodes")

    # Metadata
    created_tick: int = Field(..., description="When schema was created")
    last_updated_tick: int = Field(..., description="When last updated")
    expiry_tick: Optional[int] = Field(None, description="Optional expiry time")

    # Risk and tags
    risk_level: float = Field(0.0, ge=0.0, le=1.0, description="Risk if schema is wrong")
    tags: List[str] = Field(default_factory=list, description="Tags for retrieval")

    # For deduplication
    schema_id: Optional[str] = None


class SchemaMemory:
    """Schema memory layer.

    Stores compressed knowledge with evidence tracking.
    Handles conflicts by lowering confidence, not deletion.
    Supports persistence to disk for long-term storage.
    """

    # 修复 M7: 论文 Appendix A.7 要求 Schema 容量上限 N_sch = 1000
    MAX_CAPACITY: int = 1000

    def __init__(self, persist_path: Optional[Path] = None, max_capacity: int = None):
        """Initialize schema memory.

        Args:
            persist_path: Optional path to persist schemas to disk
            max_capacity: Maximum capacity (论文默认 1000)
        """
        self._schemas: List[SchemaEntry] = []
        self._id_index: Dict[str, int] = {}  # schema_id -> index
        self.persist_path = persist_path
        self.max_capacity = max_capacity or self.MAX_CAPACITY

        # Load from disk if path provided
        if self.persist_path and self.persist_path.exists():
            self.load_from_disk()

    def save_to_disk(self) -> bool:
        """Save all schemas to disk.

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

            for schema in self._schemas:
                writer.write(schema.model_dump())

            writer.close()
            logger.info(f"Saved {len(self._schemas)} schemas to {self.persist_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save schemas to disk: {e}")
            return False

    def load_from_disk(self) -> bool:
        """Load schemas from disk.

        Returns:
            True if successful, False otherwise
        """
        if not self.persist_path or not self.persist_path.exists():
            logger.debug("No persist file exists, skipping load")
            return False

        try:
            from common.jsonl import read_jsonl

            schemas_loaded = 0
            for record in read_jsonl(self.persist_path):
                try:
                    schema = SchemaEntry(**record)
                    # Generate ID if missing
                    if schema.schema_id is None:
                        schema.schema_id = self._generate_id(schema)
                    # Add or merge
                    if schema.schema_id not in self._id_index:
                        idx = len(self._schemas)
                        self._schemas.append(schema)
                        self._id_index[schema.schema_id] = idx
                        schemas_loaded += 1
                    else:
                        # Merge with existing
                        self._merge_schema(schema)
                        schemas_loaded += 1
                except Exception as e:
                    logger.warning(f"Failed to load schema record: {e}")

            logger.info(f"Loaded {schemas_loaded} schemas from {self.persist_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to load schemas from disk: {e}")
            return False

    def add(self, schema: SchemaEntry):
        """Add a new schema (修复 M7: 含容量限制).

        论文 Appendix A.7: Schema budget N_sch = 1000.
        超出容量时淘汰最低置信度的 schema。

        Args:
            schema: Schema to add
        """
        # Generate ID if not present
        if schema.schema_id is None:
            schema.schema_id = self._generate_id(schema)

        # Check for duplicates
        if schema.schema_id in self._id_index:
            # Merge with existing
            self._merge_schema(schema)
        else:
            # 修复 M7: 超出容量时淘汰最低置信度的 schema
            if len(self._schemas) >= self.max_capacity:
                self._evict_lowest_confidence()

            idx = len(self._schemas)
            self._schemas.append(schema)
            self._id_index[schema.schema_id] = idx

    def _evict_lowest_confidence(self):
        """淘汰置信度最低的 schema (修复 M7)."""
        if not self._schemas:
            return

        # 找到置信度最低的 schema
        min_idx = 0
        min_conf = self._schemas[0].confidence
        for i, s in enumerate(self._schemas):
            if s.confidence < min_conf:
                min_conf = s.confidence
                min_idx = i

        # 从索引中移除
        evicted = self._schemas[min_idx]
        if evicted.schema_id and evicted.schema_id in self._id_index:
            del self._id_index[evicted.schema_id]

        # 移除并重建索引
        self._schemas.pop(min_idx)
        self._rebuild_id_index()
        logger.debug(f"Evicted schema (confidence={min_conf:.2f}): {evicted.claim[:50]}")

    def _rebuild_id_index(self):
        """Rebuild schema ID index after eviction."""
        self._id_index = {}
        for i, s in enumerate(self._schemas):
            if s.schema_id:
                self._id_index[s.schema_id] = i

    def _generate_id(self, schema: SchemaEntry) -> str:
        """Generate a unique ID for schema based on claim hash.

        Args:
            schema: Schema entry

        Returns:
            Schema ID
        """
        return hash_dict({"claim": schema.claim, "scope": schema.scope})[:16]

    def _merge_schema(self, new_schema: SchemaEntry):
        """Merge new schema with existing one.

        Args:
            new_schema: New schema to merge
        """
        idx = self._id_index.get(new_schema.schema_id)
        if idx is None:
            return

        existing = self._schemas[idx]

        # Merge evidence (cap at 50 to prevent unbounded growth)
        existing.evidence_refs.extend(new_schema.evidence_refs)
        if len(existing.evidence_refs) > 50:
            existing.evidence_refs = existing.evidence_refs[-50:]
        existing.supporting_count += new_schema.supporting_count
        existing.conflicting_count += new_schema.conflicting_count

        # Update confidence (weighted average)
        total_evidence = existing.supporting_count + existing.conflicting_count
        if total_evidence > 0:
            existing.confidence = existing.supporting_count / total_evidence

        # Update timestamps
        existing.last_updated_tick = new_schema.last_updated_tick

    def query_by_tags(self, tags: List[str], min_confidence: float = 0.5) -> List[SchemaEntry]:
        """Query schemas by tags.

        Args:
            tags: Tags to match
            min_confidence: Minimum confidence threshold

        Returns:
            List of matching schemas
        """
        matches = [
            s for s in self._schemas
            if any(tag in s.tags for tag in tags) and s.confidence >= min_confidence
        ]
        return matches

    def query_by_scope(self, scope: str, min_confidence: float = 0.5) -> List[SchemaEntry]:
        """Query schemas by scope.

        Args:
            scope: Scope to match
            min_confidence: Minimum confidence threshold

        Returns:
            List of matching schemas
        """
        matches = [
            s for s in self._schemas
            if s.scope == scope and s.confidence >= min_confidence
        ]
        return matches

    def get_high_confidence(self, threshold: float = 0.8) -> List[SchemaEntry]:
        """Get high-confidence schemas.

        Args:
            threshold: Confidence threshold

        Returns:
            List of high-confidence schemas
        """
        return [s for s in self._schemas if s.confidence >= threshold]

    def mark_conflict(self, schema_id: str, conflicting_tick: int):
        """Mark a schema as having conflicting evidence.

        Args:
            schema_id: Schema ID
            conflicting_tick: Tick with conflicting evidence
        """
        idx = self._id_index.get(schema_id)
        if idx is None:
            return

        schema = self._schemas[idx]
        schema.conflicting_count += 1
        schema.evidence_refs.append(conflicting_tick)

        # Lower confidence
        total = schema.supporting_count + schema.conflicting_count
        if total > 0:
            schema.confidence = schema.supporting_count / total

    def prune_expired(self, current_tick: int):
        """Remove expired schemas.

        Args:
            current_tick: Current tick number
        """
        unexpired = [
            s for s in self._schemas
            if s.expiry_tick is None or s.expiry_tick > current_tick
        ]

        # Rebuild index
        self._schemas = unexpired
        self._id_index = {s.schema_id: i for i, s in enumerate(self._schemas)}

    def count(self) -> int:
        """Get schema count.

        Returns:
            Number of schemas
        """
        return len(self._schemas)

    def get_all(self) -> List[SchemaEntry]:
        """Get all schemas.

        Returns:
            All schemas
        """
        return self._schemas.copy()

    @property
    def schemas(self) -> List[SchemaEntry]:
        """Public property accessor for schemas (used by chat.py).

        Returns:
            List of all schemas
        """
        return self._schemas.copy()
