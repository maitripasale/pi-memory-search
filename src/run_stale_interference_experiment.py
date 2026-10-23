"""
Stale Protocol Interference Experiment: No Memory vs. Procedural Memory.

Tests the fundamental memory research question:
Does procedural memory cause negative interference / stale-memory errors when the
underlying repository specification changes, whereas a no-memory agent actively explores and adapts?
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict

research_root = Path(__file__).resolve().parent.parent
if str(research_root) not in sys.path:
    sys.path.insert(0, str(research_root))
if str(research_root / "src") not in sys.path:
    sys.path.insert(0, str(research_root / "src"))

from memory_adapters.procedural_v1 import ProceduralMemoryV1
from runner import run_baseline_task


def run_stale_probe_experiment() -> Dict[str, Any]:
    task3_path = str(research_root / "tasks" / "dataset" / "task_transfer_s3_stale_probe.json")
    config_path = str(research_root / "configs" / "baseline_frozen.json")
    results_dir = research_root / "results" / "baseline"
    results_dir.mkdir(parents=True, exist_ok=True)

    with open(task3_path, "r", encoding="utf-8") as f:
        task3 = json.load(f)

    print("=" * 70)
    print("PHASE 1: RUNNING STALE PROBE UNDER NO-MEMORY (CONDITION A)")
    print("=" * 70)
    no_mem_run_id = f"run_s3_stale_cond_A_no_mem_{int(time.time())}"
    no_mem_res = run_baseline_task(
        task_path=task3_path,
        config_path=config_path,
        run_id=no_mem_run_id,
    )
    print(f"No-Memory Success: {no_mem_res['success']}")
    print(f"No-Memory Duration: {no_mem_res['duration_ms']} ms")
    print(f"No-Memory Tokens: {no_mem_res['token_usage']}")

    print("\n" + "=" * 70)
    print("PHASE 2: RUNNING STALE PROBE UNDER PROCEDURAL MEMORY (CONDITION C)")
    print("=" * 70)
    mem = ProceduralMemoryV1(store_dir=str(research_root / "memory_adapters" / "procedural_store"))
    retrievals = mem.retrieve(task3["prompt"], limit=1)
    if not retrievals:
        raise RuntimeError("No matching procedure found!")

    ret = retrievals[0]
    injected_context = ret["formatted_context"]
    retrieval_meta = {
        "memory_type": "procedural",
        "procedure_id": ret["procedure"].procedure_id,
        "score": ret["score"],
        "matched_terms": ret["matched_terms"],
        "estimated_tokens": ret["estimated_tokens"],
    }

    augmented_prompt = (
        f"[PROCEDURAL MEMORY: REUSABLE WORKFLOW]\n"
        f"{injected_context}\n"
        f"[END PROCEDURAL MEMORY]\n\n"
        f"Task:\n{task3['prompt']}"
    )

    procedural_run_id = f"run_s3_stale_cond_C_procedural_{int(time.time())}"
    procedural_res = run_baseline_task(
        task_path=task3_path,
        config_path=config_path,
        run_id=procedural_run_id,
        prompt_override=augmented_prompt,
        injected_memory=retrieval_meta,
    )
    print(f"Procedural Memory Success: {procedural_res['success']}")
    print(f"Procedural Memory Duration: {procedural_res['duration_ms']} ms")
    print(f"Procedural Memory Tokens: {procedural_res['token_usage']}")

    # Load trajectories to inspect generated tokens
    with open(no_mem_res["saved_paths"]["json_path"], "r", encoding="utf-8") as f:
        no_mem_traj = json.load(f)
    with open(procedural_res["saved_paths"]["json_path"], "r", encoding="utf-8") as f:
        procedural_traj = json.load(f)

    stale_comparison = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "task_id": task3["task_id"],
        "phenomenon": "stale_memory_interference",
        "ground_truth_v2_2_hash": task3["evaluation"]["expected_value"],
        "deprecated_v2_1_hash": task3["stale_conflict_metadata"]["prior_version_value"],
        "no_memory": {
            "run_id": no_mem_run_id,
            "success": no_mem_res["success"],
            "score": no_mem_res["score"],
            "actual_output": no_mem_res["eval_result"].get("actual"),
            "stale_memory_error": no_mem_res["eval_result"].get("actual") == task3["stale_conflict_metadata"]["prior_version_value"],
            "duration_ms": no_mem_res["duration_ms"],
            "tokens": no_mem_res["token_usage"],
            "tool_calls_count": len(no_mem_traj.get("tool_calls", [])),
            "tools_called": [tc.get("name") for tc in no_mem_traj.get("tool_calls", [])],
        },
        "procedural_memory": {
            "run_id": procedural_run_id,
            "success": procedural_res["success"],
            "score": procedural_res["score"],
            "actual_output": procedural_res["eval_result"].get("actual"),
            "stale_memory_error": procedural_res["eval_result"].get("actual") == task3["stale_conflict_metadata"]["prior_version_value"],
            "duration_ms": procedural_res["duration_ms"],
            "tokens": procedural_res["token_usage"],
            "tool_calls_count": len(procedural_traj.get("tool_calls", [])),
            "tools_called": [tc.get("name") for tc in procedural_traj.get("tool_calls", [])],
            "injected_procedure": ret["procedure"].procedure_id,
        },
    }

    stale_out_path = results_dir / "stale_memory_interference_benchmark.json"
    with open(stale_out_path, "w", encoding="utf-8") as f:
        json.dump(stale_comparison, f, indent=2)

    print("\n" + "=" * 70)
    print("STALE MEMORY INTERFERENCE EXPERIMENT COMPLETE")
    print(f"Saved to: {stale_out_path}")
    print("=" * 70)
    return stale_comparison


if __name__ == "__main__":
    stale_res = run_stale_probe_experiment()
    print(json.dumps(stale_res, indent=2))
