"""
Experiment Harness: Minimal Multi-Session Transfer (Episodic Memory V1 vs. No-Memory Baseline)

Runs:
1. Session 1 (Memory Building): Pi explores service_repo, writes verify_admin_token.py, generates admin_token.txt.
2. Store Episode: Episode is saved into EpisodicMemoryV1 store.
3. Session 2 Condition A (No Memory): Pi attempts held-out auditor_service token generation without memory.
4. Session 2 Condition B (Episodic Memory): Pi queries EpisodicMemoryV1, retrieves S1 episode, and executes with injected memory.
5. Comparative Evaluation: Collects tokens, latency, tool calls, and success.
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict

# Ensure project root and src are in sys.path
research_root = Path(__file__).resolve().parent.parent
if str(research_root) not in sys.path:
    sys.path.insert(0, str(research_root))
if str(research_root / "src") not in sys.path:
    sys.path.insert(0, str(research_root / "src"))

from memory_adapters.episodic_v1 import EpisodicMemoryV1
from runner import run_baseline_task


def run_full_transfer_experiment() -> Dict[str, Any]:
    task1_path = str(research_root / "tasks" / "dataset" / "task_transfer_s1_build.json")
    task2_path = str(research_root / "tasks" / "dataset" / "task_transfer_s2_eval.json")
    config_path = str(research_root / "configs" / "baseline_frozen.json")

    results_dir = research_root / "results" / "baseline"
    results_dir.mkdir(parents=True, exist_ok=True)

    # Initialize clean Episodic Memory store
    memory_store_dir = research_root / "memory_adapters" / "episodic_store"
    memory = EpisodicMemoryV1(store_dir=str(memory_store_dir))
    memory.clear()

    print("=" * 70)
    print("PHASE 1: RUNNING SESSION 1 (MEMORY-BUILDING TASK)")
    print("=" * 70)
    s1_run_id = f"run_s1_build_{int(time.time())}"
    s1_result = run_baseline_task(
        task_path=task1_path,
        config_path=config_path,
        run_id=s1_run_id,
    )
    print(f"Session 1 Status: {'SUCCESS' if s1_result['success'] else 'FAILED'}")
    print(f"Session 1 Duration: {s1_result['duration_ms']} ms")
    print(f"Session 1 Tokens: {s1_result['token_usage']}")

    # Load S1 full trajectory from disk
    s1_json_path = s1_result["saved_paths"]["json_path"]
    with open(s1_json_path, "r", encoding="utf-8") as f:
        s1_trajectory = json.load(f)

    # Store into Episodic Memory
    stored_episode = memory.write_from_trajectory(
        s1_trajectory,
        stream_id="auth_service_transfer_01",
        trajectory_path=s1_json_path,
    )
    print(f"Stored Episode ID: {stored_episode.episode_id}")
    print(f"Tools in stored episode: {[tc.get('name') for tc in stored_episode.tool_calls]}")

    print("\n" + "=" * 70)
    print("PHASE 2: RUNNING SESSION 2 CONDITION A (NO MEMORY BASELINE)")
    print("=" * 70)
    s2_no_mem_run_id = f"run_s2_cond_A_no_mem_{int(time.time())}"
    s2_no_mem_result = run_baseline_task(
        task_path=task2_path,
        config_path=config_path,
        run_id=s2_no_mem_run_id,
    )
    print(f"Condition A Status: {'SUCCESS' if s2_no_mem_result['success'] else 'FAILED'}")
    print(f"Condition A Duration: {s2_no_mem_result['duration_ms']} ms")
    print(f"Condition A Tokens: {s2_no_mem_result['token_usage']}")

    print("\n" + "=" * 70)
    print("PHASE 3: RUNNING SESSION 2 CONDITION B (WITH EPISODIC MEMORY V1)")
    print("=" * 70)
    # 1. Query memory
    with open(task2_path, "r", encoding="utf-8") as f:
        task2_spec = json.load(f)
    s2_query = task2_spec["prompt"]
    retrievals = memory.retrieve(s2_query, stream_id="auth_service_transfer_01", limit=1)

    if not retrievals:
        print("WARNING: No episode retrieved!")
        injected_context = ""
        retrieval_meta = {}
    else:
        ret = retrievals[0]
        injected_context = ret["formatted_context"]
        retrieval_meta = {
            "retrieved_episode_id": ret["episode"].episode_id,
            "score": ret["score"],
            "matched_terms": ret["matched_terms"],
            "estimated_tokens": ret["estimated_tokens"],
        }
        print(f"Retrieved Episode: {retrieval_meta['retrieved_episode_id']}")
        print(f"Match Score: {retrieval_meta['score']}")
        print(f"Matched Terms: {retrieval_meta['matched_terms']}")

    # 2. Construct memory-augmented prompt
    augmented_prompt = (
        f"[EPISODIC MEMORY: Prior Experience Trace]\n"
        f"{injected_context}\n"
        f"[END EPISODIC MEMORY]\n\n"
        f"Task:\n{task2_spec['prompt']}"
    )

    s2_episodic_run_id = f"run_s2_cond_B_episodic_{int(time.time())}"
    s2_episodic_result = run_baseline_task(
        task_path=task2_path,
        config_path=config_path,
        run_id=s2_episodic_run_id,
        prompt_override=augmented_prompt,
        injected_memory=retrieval_meta,
    )
    print(f"Condition B Status: {'SUCCESS' if s2_episodic_result['success'] else 'FAILED'}")
    print(f"Condition B Duration: {s2_episodic_result['duration_ms']} ms")
    print(f"Condition B Tokens: {s2_episodic_result['token_usage']}")

    # Phase 4: Compile Comparative Summary
    with open(task1_path, "r", encoding="utf-8") as f:
        task1_spec = json.load(f)
    with open(s2_no_mem_result["saved_paths"]["json_path"], "r", encoding="utf-8") as f:
        s2_no_mem_traj = json.load(f)
    with open(s2_episodic_result["saved_paths"]["json_path"], "r", encoding="utf-8") as f:
        s2_episodic_traj = json.load(f)

    comparison = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "task_pair": {
            "session_1": task1_spec,
            "session_2": task2_spec,
        },
        "session_1_build": {
            "run_id": s1_run_id,
            "success": s1_result["success"],
            "duration_ms": s1_result["duration_ms"],
            "tokens": s1_result["token_usage"],
            "tools_called": [tc.get("name") for tc in s1_trajectory.get("tool_calls", [])],
            "trajectory_file": s1_result["saved_paths"]["json_path"],
        },
        "condition_A_no_memory": {
            "run_id": s2_no_mem_run_id,
            "success": s2_no_mem_result["success"],
            "duration_ms": s2_no_mem_result["duration_ms"],
            "tokens": s2_no_mem_result["token_usage"],
            "tool_calls_count": len(s2_no_mem_traj.get("tool_calls", [])),
            "tools_called": [tc.get("name") for tc in s2_no_mem_traj.get("tool_calls", [])],
            "final_answer": s2_no_mem_traj.get("final_response"),
            "trajectory_file": s2_no_mem_result["saved_paths"]["json_path"],
        },
        "condition_B_episodic_memory": {
            "run_id": s2_episodic_run_id,
            "success": s2_episodic_result["success"],
            "duration_ms": s2_episodic_result["duration_ms"],
            "tokens": s2_episodic_result["token_usage"],
            "tool_calls_count": len(s2_episodic_traj.get("tool_calls", [])),
            "tools_called": [tc.get("name") for tc in s2_episodic_traj.get("tool_calls", [])],
            "final_answer": s2_episodic_traj.get("final_response"),
            "retrieval": retrieval_meta,
            "injected_context": injected_context,
            "trajectory_file": s2_episodic_result["saved_paths"]["json_path"],
        },
        "delta": {
            "duration_diff_ms": round(s2_episodic_result["duration_ms"] - s2_no_mem_result["duration_ms"], 2),
            "total_tokens_diff": s2_episodic_result["token_usage"]["total_tokens"] - s2_no_mem_result["token_usage"]["total_tokens"],
            "tool_calls_diff": len(s2_episodic_traj.get("tool_calls", [])) - len(s2_no_mem_traj.get("tool_calls", [])),
        },
    }

    comparison_path = results_dir / "transfer_comparison_s1_s2.json"
    with open(comparison_path, "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2)

    print("\n" + "=" * 70)
    print("EXPERIMENT COMPLETE. SUMMARY SAVED TO:", comparison_path)
    print("=" * 70)
    return comparison


if __name__ == "__main__":
    comp = run_full_transfer_experiment()
    print(json.dumps(comp["delta"], indent=2))
