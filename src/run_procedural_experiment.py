"""
Harness to execute Session 2 under Condition C (Procedural Memory V1)
and compile a 3-way benchmark: No Memory vs. Episodic Memory vs. Procedural Memory.
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


def run_procedural_experiment() -> Dict[str, Any]:
    task2_path = str(research_root / "tasks" / "dataset" / "task_transfer_s2_eval.json")
    config_path = str(research_root / "configs" / "baseline_frozen.json")
    results_dir = research_root / "results" / "baseline"
    results_dir.mkdir(parents=True, exist_ok=True)

    with open(task2_path, "r", encoding="utf-8") as f:
        task2 = json.load(f)

    # 1. Retrieve procedure from Procedural Memory
    mem = ProceduralMemoryV1(store_dir=str(research_root / "memory_adapters" / "procedural_store"))
    retrievals = mem.retrieve(task2["prompt"], limit=1)
    if not retrievals:
        raise RuntimeError("No matching procedure found in procedural store!")

    ret = retrievals[0]
    injected_context = ret["formatted_context"]
    retrieval_meta = {
        "memory_type": "procedural",
        "procedure_id": ret["procedure"].procedure_id,
        "score": ret["score"],
        "matched_terms": ret["matched_terms"],
        "estimated_tokens": ret["estimated_tokens"],
    }

    print("=" * 70)
    print("RUNNING SESSION 2 CONDITION C (PROCEDURAL MEMORY V1)")
    print("=" * 70)
    print(f"Retrieved Procedure: {ret['procedure'].procedure_id} ('{ret['procedure'].title}')")
    print(f"Match Score: {ret['score']}")
    print(f"Matched Terms: {ret['matched_terms']}")
    print(f"Estimated Prompt Overhead: ~{ret['estimated_tokens']} tokens")

    # 2. Inject procedure into context
    augmented_prompt = (
        f"[PROCEDURAL MEMORY: REUSABLE WORKFLOW]\n"
        f"{injected_context}\n"
        f"[END PROCEDURAL MEMORY]\n\n"
        f"Task:\n{task2['prompt']}"
    )

    run_id = f"run_s2_cond_C_procedural_{int(time.time())}"
    res = run_baseline_task(
        task_path=task2_path,
        config_path=config_path,
        run_id=run_id,
        prompt_override=augmented_prompt,
        injected_memory=retrieval_meta,
    )

    print(f"\nCondition C Status: {'SUCCESS' if res['success'] else 'FAILED'}")
    print(f"Condition C Duration: {res['duration_ms']} ms")
    print(f"Condition C Tokens: {res['token_usage']}")

    # 3. Load prior comparison data (Condition A and Condition B)
    prior_comp_path = results_dir / "transfer_comparison_s1_s2.json"
    with open(prior_comp_path, "r", encoding="utf-8") as f:
        prior_comp = json.load(f)

    with open(res["saved_paths"]["json_path"], "r", encoding="utf-8") as f:
        s2_procedural_traj = json.load(f)

    cond_A = prior_comp["condition_A_no_memory"]
    cond_B = prior_comp["condition_B_episodic_memory"]

    cond_C = {
        "run_id": run_id,
        "success": res["success"],
        "duration_ms": res["duration_ms"],
        "tokens": res["token_usage"],
        "tool_calls_count": len(s2_procedural_traj.get("tool_calls", [])),
        "tools_called": [tc.get("name") for tc in s2_procedural_traj.get("tool_calls", [])],
        "final_answer": s2_procedural_traj.get("final_response"),
        "retrieval": retrieval_meta,
        "injected_context": injected_context,
        "trajectory_file": res["saved_paths"]["json_path"],
    }

    three_way_comparison = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "task_evaluated": task2["task_id"],
        "frozen_model": "glm-5.3-flash (Particle AI)",
        "condition_A_no_memory": cond_A,
        "condition_B_episodic_memory": cond_B,
        "condition_C_procedural_memory": cond_C,
        "comparative_deltas": {
            "procedural_vs_no_memory": {
                "duration_diff_ms": round(cond_C["duration_ms"] - cond_A["duration_ms"], 2),
                "total_tokens_diff": cond_C["tokens"]["total_tokens"] - cond_A["tokens"]["total_tokens"],
                "tool_calls_diff": cond_C["tool_calls_count"] - cond_A["tool_calls_count"],
            },
            "procedural_vs_episodic": {
                "duration_diff_ms": round(cond_C["duration_ms"] - cond_B["duration_ms"], 2),
                "total_tokens_diff": cond_C["tokens"]["total_tokens"] - cond_B["tokens"]["total_tokens"],
                "tool_calls_diff": cond_C["tool_calls_count"] - cond_B["tool_calls_count"],
            },
        },
    }

    out_path = results_dir / "comparison_no_mem_vs_episodic_vs_procedural.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(three_way_comparison, f, indent=2)

    print("\n" + "=" * 70)
    print("THREE-WAY COMPARISON BENCHMARK COMPLETE")
    print(f"Saved to: {out_path}")
    print("=" * 70)
    return three_way_comparison


if __name__ == "__main__":
    benchmark = run_procedural_experiment()
    print(json.dumps(benchmark["comparative_deltas"], indent=2))
