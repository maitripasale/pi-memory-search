"""
Trajectory and run logging for Pi agent research baseline.

Records:
- run_id, task_id, session_id
- start_time, end_time, duration_ms
- model, provider, config snapshot
- prompts, tool calls, observations
- final response
- evaluation success, score, metrics
- token usage (input, output, cache read/write, total)
- latency
- cost (USD)
"""

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class TrajectoryLogger:
    def __init__(self, log_dir: str = "trajectories/runs"):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)

    def record_run(
        self,
        run_id: str,
        task_id: str,
        session_id: str,
        start_time_iso: str,
        end_time_iso: str,
        duration_ms: float,
        model_config: Dict[str, Any],
        experiment_config: Dict[str, Any],
        prompts: List[Dict[str, Any]],
        tool_calls: List[Dict[str, Any]],
        observations: List[Dict[str, Any]],
        events: List[Dict[str, Any]],
        final_response: str,
        evaluation: Dict[str, Any],
        token_usage: Dict[str, Any],
        latency_ms: float,
        cost_usd: Optional[float] = None,
        error: Optional[str] = None,
        injected_memory: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """
        Saves run trajectory as both a complete structured JSON file
        and a JSONL events trace file.
        """
        run_record = {
            "run_id": run_id,
            "task_id": task_id,
            "session_id": session_id,
            "timestamps": {
                "start": start_time_iso,
                "end": end_time_iso,
                "duration_ms": duration_ms,
            },
            "model_config": model_config,
            "experiment_config": {
                "experiment_id": experiment_config.get("experiment_id"),
                "version": experiment_config.get("version"),
                "memory_type": experiment_config.get("memory", {}).get("type", "none"),
                "tools": experiment_config.get("agent", {}).get("tools", []),
            },
            "injected_memory": injected_memory,
            "prompts": prompts,
            "tool_calls": tool_calls,
            "observations": observations,
            "final_response": final_response,
            "evaluation": evaluation,
            "token_usage": token_usage,
            "latency_ms": latency_ms,
            "cost_usd": cost_usd,
            "error": error,
        }

        # 1. Write full JSON run record
        json_path = os.path.join(self.log_dir, f"{run_id}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(run_record, f, indent=2)

        # 2. Write JSONL event stream
        jsonl_path = os.path.join(self.log_dir, f"{run_id}.events.jsonl")
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for event in events:
                f.write(json.dumps(event) + "\n")

        return {
            "json_path": json_path,
            "jsonl_path": jsonl_path,
        }
