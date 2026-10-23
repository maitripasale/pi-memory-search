"""
Procedural Memory V1 Adapter for Pi Coding Agent Research.

Core Principles:
- Stores reusable, successful procedures and workflows distilled from experience.
- Unlike episodic memory, procedural memory does not replay raw turn-by-turn history;
  it abstracts clean execution recipes (triggers, parameters, steps, verification).
- Fully supports: write(), retrieve(), revise(), forget(), and provenance tracking.
- Transparent file-based storage under memory_adapters/procedural_store/.
- Strictly adheres to storage, retrieval, and context token budgets.
"""

import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "her", "here", "hers", "herself", "him",
    "himself", "his", "how", "i", "if", "in", "into", "is", "isn't", "it", "its",
    "itself", "let's", "me", "more", "most", "mustn't", "my", "myself", "no",
    "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought",
    "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
    "should", "shouldn't", "so", "some", "such", "than", "that", "the", "their",
    "theirs", "them", "themselves", "then", "there", "these", "they", "this",
    "those", "through", "to", "too", "under", "until", "up", "very", "was",
    "wasn't", "we", "were", "weren't", "what", "when", "where", "which", "while",
    "who", "whom", "why", "with", "won't", "would", "wouldn't", "you", "your",
    "yours", "yourself", "yourselves", "create", "file", "named", "containing",
    "single", "line", "only", "the",
}


def tokenize_text(text: str) -> Set[str]:
    raw = re.findall(r"[a-zA-Z0-9_\-\./]+", text.lower())
    clean = set()
    for tok in raw:
        tok = tok.strip("._-")
        if len(tok) >= 2 and tok not in STOPWORDS:
            clean.add(tok)
    return clean


@dataclass
class ProcedureEntry:
    procedure_id: str
    title: str
    description: str
    triggers: List[str]
    parameters: Dict[str, str]
    preconditions: List[str]
    steps: List[str]
    verification: str
    provenance: Dict[str, Any]
    created_at: str
    updated_at: str
    usage_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProcedureEntry":
        return cls(**data)


class ProceduralMemoryV1:
    """Transparent file-based procedural memory store and retriever."""

    def __init__(
        self,
        store_dir: str = "memory_adapters/procedural_store",
        max_storage_bytes: int = 500_000,
        max_retrieval_tokens: int = 1000,
    ):
        self.store_dir = Path(store_dir)
        self.max_storage_bytes = max_storage_bytes
        self.max_retrieval_tokens = max_retrieval_tokens
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.store_dir / "index.json"
        self._ensure_index()

    def _ensure_index(self) -> None:
        if not self.index_path.exists():
            with open(self.index_path, "w", encoding="utf-8") as f:
                json.dump({"procedures": {}, "total_storage_bytes": 0}, f, indent=2)

    def _load_index(self) -> Dict[str, Any]:
        with open(self.index_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_index(self, index: Dict[str, Any]) -> None:
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2)

    def write(self, entry: ProcedureEntry) -> ProcedureEntry:
        """Persists a procedure to disk and updates index with budget checks."""
        proc_file = self.store_dir / f"{entry.procedure_id}.json"
        data = entry.to_dict()
        serialized = json.dumps(data, indent=2)
        byte_size = len(serialized.encode("utf-8"))

        index = self._load_index()
        current_bytes = index.get("total_storage_bytes", 0)

        if current_bytes + byte_size > self.max_storage_bytes and entry.procedure_id not in index["procedures"]:
            raise MemoryError(
                f"Procedural memory storage budget exceeded: {current_bytes + byte_size} > {self.max_storage_bytes}"
            )

        with open(proc_file, "w", encoding="utf-8") as f:
            f.write(serialized)

        index["procedures"][entry.procedure_id] = {
            "title": entry.title,
            "triggers": entry.triggers,
            "created_at": entry.created_at,
            "file": f"{entry.procedure_id}.json",
            "bytes": byte_size,
        }
        index["total_storage_bytes"] = sum(v["bytes"] for v in index["procedures"].values())
        self._save_index(index)
        return entry

    def retrieve(
        self,
        query: str,
        limit: int = 1,
        context_budget_tokens: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Deterministic keyword overlap search against procedure triggers, title, and description.
        Returns ranked list of {procedure: ProcedureEntry, score: float, matched_terms: List[str]}.
        """
        budget_tokens = context_budget_tokens or self.max_retrieval_tokens
        query_tokens = tokenize_text(query)
        if not query_tokens:
            return []

        index = self._load_index()
        candidates: List[Tuple[float, List[str], ProcedureEntry]] = []

        for proc_id, meta in index["procedures"].items():
            proc_file = self.store_dir / meta["file"]
            if not proc_file.exists():
                continue

            with open(proc_file, "r", encoding="utf-8") as f:
                proc = ProcedureEntry.from_dict(json.load(f))

            # Match against triggers, title, and description
            searchable = " ".join([
                proc.title,
                proc.description,
                " ".join(proc.triggers),
            ]).lower()

            matched_terms = [tok for tok in query_tokens if tok in searchable]
            score = len(matched_terms) / len(query_tokens) if query_tokens else 0.0

            if matched_terms:
                candidates.append((score, matched_terms, proc))

        # Sort descending by score, then creation timestamp
        candidates.sort(key=lambda x: (x[0], x[2].created_at), reverse=True)

        results: List[Dict[str, Any]] = []
        accumulated_tokens = 0

        for score, matched_terms, proc in candidates[:limit]:
            formatted_snippet = self.format_procedure_for_context(proc)
            est_tokens = len(formatted_snippet) // 4
            if accumulated_tokens + est_tokens <= budget_tokens:
                results.append({
                    "procedure": proc,
                    "score": round(score, 4),
                    "matched_terms": matched_terms,
                    "estimated_tokens": est_tokens,
                    "formatted_context": formatted_snippet,
                })
                accumulated_tokens += est_tokens

        return results

    def format_procedure_for_context(self, proc: ProcedureEntry) -> str:
        """Formats a procedure into a concise, actionable workflow template."""
        lines = [
            "--- BEGIN PROCEDURAL MEMORY: REUSABLE WORKFLOW ---",
            f"Procedure: {proc.title} ({proc.procedure_id})",
            f"Description: {proc.description}",
        ]
        if proc.parameters:
            lines.append("Parameters:")
            for p_name, p_desc in proc.parameters.items():
                lines.append(f"  - {p_name}: {p_desc}")
        if proc.preconditions:
            lines.append("Preconditions:")
            for prec in proc.preconditions:
                lines.append(f"  - {prec}")
        lines.append("Execution Steps:")
        for idx, step in enumerate(proc.steps, 1):
            lines.append(f"  {idx}. {step}")
        if proc.verification:
            lines.append(f"Verification: {proc.verification}")
        lines.append(f"Provenance: Extracted from verified run {proc.provenance.get('source_run_id')}")
        lines.append("--- END PROCEDURAL MEMORY ---")
        return "\n".join(lines)

    def revise(self, procedure_id: str, updated_fields: Dict[str, Any]) -> bool:
        proc_file = self.store_dir / f"{procedure_id}.json"
        if not proc_file.exists():
            return False

        with open(proc_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        data.update(updated_fields)
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        entry = ProcedureEntry.from_dict(data)
        self.write(entry)
        return True

    def forget(self, procedure_id: str) -> bool:
        proc_file = self.store_dir / f"{procedure_id}.json"
        if not proc_file.exists():
            return False

        os.remove(proc_file)
        index = self._load_index()
        if procedure_id in index["procedures"]:
            del index["procedures"][procedure_id]
            index["total_storage_bytes"] = sum(v["bytes"] for v in index["procedures"].values())
            self._save_index(index)
        return True

    def clear(self) -> None:
        for f in self.store_dir.glob("*.json"):
            try:
                os.remove(f)
            except OSError:
                pass
        self._ensure_index()
