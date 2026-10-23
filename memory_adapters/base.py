"""
Base contract for agent memory systems.

All memory implementations must adhere to this interface, supporting:
- provenance tracking
- timestamps
- scope (session, task, global)
- write
- retrieve
- revise
- forget
- strict budget enforcement (storage, retrieval, context limits)

NOTE: Concrete implementations (Procedural, Semantic, Episodic, Causal,
Prospective, Metacognitive) are deferred per project plan.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class MemoryScope(str, Enum):
    SESSION = "session"
    TASK = "task"
    GLOBAL = "global"


@dataclass
class MemoryProvenance:
    source_task_id: str
    source_session_id: str
    source_run_id: str
    source_step_index: Optional[int] = None
    attribution: str = ""
    evidence_snippet: str = ""


@dataclass
class MemoryEntry:
    memory_id: str
    memory_type: str
    content: str
    scope: MemoryScope
    provenance: MemoryProvenance
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    confidence: float = 1.0
    access_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BudgetConfig:
    max_storage_bytes: int = 100_000
    max_retrieval_tokens: int = 1_000
    max_context_injection_tokens: int = 1_000


@dataclass
class RetrievalResult:
    entries: List[MemoryEntry]
    total_tokens: int
    retrieval_latency_ms: float
    query: str


class MemoryAdapter(ABC):
    """Abstract base class for all memory systems."""

    def __init__(self, memory_type: str, budget: BudgetConfig):
        self.memory_type = memory_type
        self.budget = budget

    @abstractmethod
    def write(self, entry: MemoryEntry) -> bool:
        """Store a new memory entry respecting the storage budget."""
        raise NotImplementedError

    @abstractmethod
    def retrieve(self, query: str, limit: int = 5) -> RetrievalResult:
        """Retrieve relevant memory entries within the retrieval token budget."""
        raise NotImplementedError

    @abstractmethod
    def revise(self, memory_id: str, updated_content: str, updated_metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Revise or correct an existing memory entry."""
        raise NotImplementedError

    @abstractmethod
    def forget(self, memory_id: str) -> bool:
        """Explicitly purge or delete a memory entry."""
        raise NotImplementedError

    @abstractmethod
    def get_storage_usage_bytes(self) -> int:
        """Return the current storage footprint in bytes."""
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        """Clear all entries in this adapter (e.g. between isolated runs)."""
        raise NotImplementedError
