"""
Episodic Memory V1 Adapter for Pi Coding Agent Research.

Core Principles:
- A completed Pi trajectory is the episode.
- Preserves both successful and failed runs with provenance, timestamps, and outcome.
- Does NOT summarize into facts or procedures; preserves the raw episode interaction.
- Provides transparent file-based deterministic search (keyword / term-frequency overlap).
- Strictly enforces retrieval and context token budgets.
- Supports write(), retrieve(), revise(), forget().
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


def tokenize_query(text: str) -> Set[str]:
    """Extract lowercase alpha-numeric tokens excluding stopwords."""
    raw_tokens = re.findall(r"[a-zA-Z0-9_\-\./]+", text.lower())
    clean_tokens = set()
    for tok in raw_tokens:
        tok = tok.strip("._-")
        if len(tok) >= 2 and tok not in STOPWORDS:
            clean_tokens.add(tok)
    return clean_tokens


@dataclass
class EpisodeEntry:
    episode_id: str
    run_id: str
    task_id: str
    session_id: str
    stream_id: str
    created_at: str
    updated_at: str
    prompt: str
    tool_calls: List[Dict[str, Any]]
    observations: List[Dict[str, Any]]
    final_response: str
    success: bool
    score: float
    duration_ms: float
    total_tokens: int
    raw_trajectory_path: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EpisodeEntry":
        return cls(**data)


class EpisodicMemoryV1:
    """Transparent file-based episodic memory store and deterministic retriever."""

    def __init__(
        self,
        store_dir: str = "memory_adapters/episodic_store",
        max_storage_bytes: int = 500_000,
        max_retrieval_tokens: int = 1500,
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
                json.dump({"episodes": {}, "total_storage_bytes": 0}, f, indent=2)

    def _load_index(self) -> Dict[str, Any]:
        with open(self.index_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_index(self, index: Dict[str, Any]) -> None:
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2)

    def write_from_trajectory(
        self,
        trajectory: Dict[str, Any],
        stream_id: str = "default_stream",
        trajectory_path: str = "",
    ) -> EpisodeEntry:
        """Constructs and stores an episode from a completed run trajectory."""
        run_id = trajectory.get("run_id", f"run_{int(time.time())}")
        episode_id = f"ep_{run_id}"
        eval_info = trajectory.get("evaluation", {})

        entry = EpisodeEntry(
            episode_id=episode_id,
            run_id=run_id,
            task_id=trajectory.get("task_id", "unknown_task"),
            session_id=trajectory.get("session_id", f"sess_{run_id}"),
            stream_id=stream_id,
            created_at=trajectory.get("timestamps", {}).get("start", datetime.now(timezone.utc).isoformat()),
            updated_at=datetime.now(timezone.utc).isoformat(),
            prompt=(
                trajectory.get("prompts", [{}])[0].get("content", "")
                if trajectory.get("prompts")
                else ""
            ),
            tool_calls=trajectory.get("tool_calls", []),
            observations=trajectory.get("observations", []),
            final_response=trajectory.get("final_response", ""),
            success=eval_info.get("success", False),
            score=eval_info.get("score", 0.0),
            duration_ms=trajectory.get("timestamps", {}).get("duration_ms", 0.0),
            total_tokens=trajectory.get("token_usage", {}).get("total_tokens", 0),
            raw_trajectory_path=trajectory_path,
        )

        return self.write(entry)

    def write(self, entry: EpisodeEntry) -> EpisodeEntry:
        """Persists an episode entry to disk and updates the index."""
        ep_file = self.store_dir / f"{entry.episode_id}.json"
        ep_data = entry.to_dict()
        serialized = json.dumps(ep_data, indent=2)
        byte_size = len(serialized.encode("utf-8"))

        index = self._load_index()
        current_bytes = index.get("total_storage_bytes", 0)

        # Storage budget check
        if current_bytes + byte_size > self.max_storage_bytes and entry.episode_id not in index["episodes"]:
            raise MemoryError(
                f"Episodic memory storage budget exceeded: {current_bytes + byte_size} > {self.max_storage_bytes}"
            )

        with open(ep_file, "w", encoding="utf-8") as f:
            f.write(serialized)

        index["episodes"][entry.episode_id] = {
            "task_id": entry.task_id,
            "run_id": entry.run_id,
            "stream_id": entry.stream_id,
            "created_at": entry.created_at,
            "success": entry.success,
            "file": f"{entry.episode_id}.json",
            "bytes": byte_size,
        }
        index["total_storage_bytes"] = sum(v["bytes"] for v in index["episodes"].values())
        self._save_index(index)
        return entry

    def retrieve(
        self,
        query: str,
        stream_id: Optional[str] = None,
        limit: int = 1,
        context_budget_tokens: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Deterministic keyword/token overlap search against stored episodes.
        Returns ranked list of {episode: EpisodeEntry, score: float, matched_terms: List[str]}.
        """
        budget_tokens = context_budget_tokens or self.max_retrieval_tokens
        query_tokens = tokenize_query(query)
        if not query_tokens:
            return []

        index = self._load_index()
        candidates: List[Tuple[float, List[str], EpisodeEntry]] = []

        for ep_id, meta in index["episodes"].items():
            if stream_id and meta.get("stream_id") != stream_id:
                continue

            ep_file = self.store_dir / meta["file"]
            if not ep_file.exists():
                continue

            with open(ep_file, "r", encoding="utf-8") as f:
                ep = EpisodeEntry.from_dict(json.load(f))

            # Search text across prompt, tool calls, and observations
            searchable_parts = [ep.prompt, ep.final_response]
            for tc in ep.tool_calls:
                searchable_parts.append(tc.get("name", ""))
                searchable_parts.append(json.dumps(tc.get("arguments", {})))
            for obs in ep.observations:
                for c in obs.get("content", []):
                    if isinstance(c, dict):
                        searchable_parts.append(c.get("text", ""))

            full_searchable = " ".join(searchable_parts).lower()

            matched_terms = [tok for tok in query_tokens if tok in full_searchable]
            score = len(matched_terms) / len(query_tokens) if query_tokens else 0.0

            if matched_terms:
                candidates.append((score, matched_terms, ep))

        # Sort descending by score, then most recent created_at
        candidates.sort(key=lambda x: (x[0], x[2].created_at), reverse=True)

        results: List[Dict[str, Any]] = []
        accumulated_tokens = 0

        for score, matched_terms, ep in candidates[:limit]:
            formatted_snippet = self.format_episode_for_context(ep)
            # Estimate token count (~4 chars per token)
            est_tokens = len(formatted_snippet) // 4
            if accumulated_tokens + est_tokens <= budget_tokens:
                results.append({
                    "episode": ep,
                    "score": round(score, 4),
                    "matched_terms": matched_terms,
                    "estimated_tokens": est_tokens,
                    "formatted_context": formatted_snippet,
                })
                accumulated_tokens += est_tokens

        return results

    def format_episode_for_context(self, ep: EpisodeEntry) -> str:
        """Formats an episode into an inspectable, unsummarized replay trace for Pi."""
        lines = [
            "--- BEGIN EPISODIC MEMORY REPLAY ---",
            f"Previous Run ID: {ep.run_id}",
            f"Previous Task Prompt: {ep.prompt}",
            f"Outcome: {'SUCCESS' if ep.success else 'FAILURE'} (score: {ep.score})",
            "Trace of Actions Taken & Observations:",
        ]

        # Combine tool calls and observations chronologically
        obs_map = {}
        for obs in ep.observations:
            call_id = obs.get("toolCallId")
            if call_id:
                texts = [c.get("text", "") for c in obs.get("content", []) if isinstance(c, dict)]
                obs_map[call_id] = "\n".join(texts).strip()

        for idx, tc in enumerate(ep.tool_calls, 1):
            name = tc.get("name")
            args = json.dumps(tc.get("arguments", {}))
            lines.append(f"  Step {idx}: call {name}({args})")
            call_id = tc.get("id")
            if call_id and call_id in obs_map:
                obs_snippet = obs_map[call_id]
                # Bounded snippet length to prevent blowing context
                if len(obs_snippet) > 400:
                    obs_snippet = obs_snippet[:400] + "... [truncated]"
                lines.append(f"  Step {idx} Observation: {obs_snippet}")

        if ep.final_response:
            lines.append(f"Final Answer: {ep.final_response}")
        lines.append("--- END EPISODIC MEMORY REPLAY ---")
        return "\n".join(lines)

    def revise(self, episode_id: str, updated_fields: Dict[str, Any]) -> bool:
        """Revises an existing episode."""
        ep_file = self.store_dir / f"{episode_id}.json"
        if not ep_file.exists():
            return False

        with open(ep_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        data.update(updated_fields)
        data["updated_at"] = datetime.now(timezone.utc).isoformat()

        ep = EpisodeEntry.from_dict(data)
        self.write(ep)
        return True

    def forget(self, episode_id: str) -> bool:
        """Purges an episode from disk and index."""
        ep_file = self.store_dir / f"{episode_id}.json"
        if not ep_file.exists():
            return False

        os.remove(ep_file)
        index = self._load_index()
        if episode_id in index["episodes"]:
            del index["episodes"][episode_id]
            index["total_storage_bytes"] = sum(v["bytes"] for v in index["episodes"].values())
            self._save_index(index)
        return True

    def clear(self) -> None:
        """Purges all episodes."""
        for f in self.store_dir.glob("*.json"):
            try:
                os.remove(f)
            except OSError:
                pass
        self._ensure_index()
