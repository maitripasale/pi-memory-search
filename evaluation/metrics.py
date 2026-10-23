"""
Evaluation metrics for agent memory experiments.

Tracks:
- Task success (binary or partial score)
- Grounded factual accuracy
- Memory relevance
- Memory interference score
- Stale memory errors
- Token usage (input, output, cache read/write, total)
- Latency (end-to-end and turn-by-turn ms)
- Cost (USD when provider pricing available)
- Repeated-run uncertainty (variance across runs)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import math


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    total_tokens: int = 0


@dataclass
class RunMetrics:
    task_id: str
    run_id: str
    success: bool
    score: float
    grounded_factual_accuracy: Optional[float] = None
    memory_relevance: Optional[float] = None
    interference_score: Optional[float] = None
    stale_memory_error: Optional[bool] = None
    tokens: TokenUsage = field(default_factory=TokenUsage)
    latency_ms: float = 0.0
    cost_usd: Optional[float] = None
    error_message: Optional[str] = None
    raw_metrics: Dict[str, Any] = field(default_factory=dict)


def compute_uncertainty(scores: List[float]) -> Dict[str, float]:
    """Compute mean, sample standard deviation, and standard error for repeated runs."""
    n = len(scores)
    if n == 0:
        return {"mean": 0.0, "std_dev": 0.0, "stderr": 0.0, "n": 0}
    mean = sum(scores) / n
    if n == 1:
        return {"mean": mean, "std_dev": 0.0, "stderr": 0.0, "n": 1}
    variance = sum((x - mean) ** 2 for x in scores) / (n - 1)
    std_dev = math.sqrt(variance)
    stderr = std_dev / math.sqrt(n)
    return {
        "mean": round(mean, 4),
        "std_dev": round(std_dev, 4),
        "stderr": round(stderr, 4),
        "n": n,
    }


def evaluate_task_outcome(task: Dict[str, Any], workspace_dir: str, agent_output: str) -> Dict[str, Any]:
    """
    Evaluates agent run output against the task specification.
    Supports file_content, regex_match, and script_execution.
    """
    import os
    import re
    import subprocess

    eval_spec = task.get("evaluation", {})
    eval_type = eval_spec.get("type", "file_content")

    if eval_type == "file_content":
        target_file = eval_spec.get("target_file")
        if not target_file:
            return {"success": False, "score": 0.0, "error": "No target_file specified"}
        target_path = os.path.join(workspace_dir, target_file)
        if not os.path.exists(target_path):
            return {"success": False, "score": 0.0, "error": f"Target file '{target_file}' was not created"}
        with open(target_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        expected = eval_spec.get("expected_value")
        if expected is not None:
            # Match stripped content
            is_match = content.strip() == str(expected).strip()
            return {
                "success": is_match,
                "score": 1.0 if is_match else 0.0,
                "actual": content.strip(),
                "expected": str(expected).strip(),
            }
        return {"success": True, "score": 1.0}

    elif eval_type == "regex_match":
        pattern = eval_spec.get("pattern", "")
        match = bool(re.search(pattern, agent_output))
        return {"success": match, "score": 1.0 if match else 0.0}

    elif eval_type == "script_execution":
        command = eval_spec.get("verification_command")
        if not command:
            return {"success": False, "score": 0.0, "error": "No verification_command"}
        try:
            res = subprocess.run(
                command,
                shell=True,
                cwd=workspace_dir,
                capture_output=True,
                text=True,
                timeout=eval_spec.get("timeout_seconds", 30),
            )
            success = res.returncode == 0
            return {
                "success": success,
                "score": 1.0 if success else 0.0,
                "stdout": res.stdout,
                "stderr": res.stderr,
            }
        except Exception as e:
            return {"success": False, "score": 0.0, "error": str(e)}

    return {"success": False, "score": 0.0, "error": f"Unknown evaluation type: {eval_type}"}
