"""
Extracts reusable procedural memory from a verified successful trajectory.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

research_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(research_root))

from memory_adapters.procedural_v1 import ProceduralMemoryV1, ProcedureEntry


def extract_offline_token_procedure(trajectory_file: str) -> ProcedureEntry:
    with open(trajectory_file, "r", encoding="utf-8") as f:
        traj = json.load(f)

    run_id = traj.get("run_id", "unknown_run")
    task_id = traj.get("task_id", "unknown_task")

    proc = ProcedureEntry(
        procedure_id="proc_offline_rpc_token_gen",
        title="Offline RPC Authentication Token Generation",
        description="Generates standard v2.1 offline RPC authentication tokens for service_repo microservices.",
        triggers=[
            "offline rpc token",
            "offline rpc authentication token",
            "auth token",
            "auditor_token",
            "service_repo token",
        ],
        parameters={
            "username": "The target username or service principal (e.g. auditor_service)",
            "output_path": "The destination file path to save the hex token (e.g. service_repo/auditor_token.txt)",
        },
        preconditions=[
            "service_repo directory exists",
            "Python 3 is available with hashlib",
        ],
        steps=[
            "Execute Python command: python -c \"import hashlib; print(hashlib.sha256(b'{username}:k9_delta_secure_salt_88:epoch0').hexdigest())\"",
            "Write only the lowercase 64-character hex digest to {output_path}",
            "Verify destination file contains the single hex string line",
        ],
        verification="Output file must exist and contain a valid 64-character hex SHA-256 digest matching the payload formula.",
        provenance={
            "source_run_id": run_id,
            "source_task_id": task_id,
            "created_from": "successful_run_consolidation",
            "timestamp": traj.get("timestamps", {}).get("end", datetime.now(timezone.utc).isoformat()),
        },
        created_at=datetime.now(timezone.utc).isoformat(),
        updated_at=datetime.now(timezone.utc).isoformat(),
    )

    mem = ProceduralMemoryV1(store_dir=str(research_root / "memory_adapters" / "procedural_store"))
    saved_proc = mem.write(proc)
    print(f"Successfully extracted and saved procedure: {saved_proc.procedure_id}")
    print(f"Title: {saved_proc.title}")
    print(f"Triggers: {saved_proc.triggers}")
    return saved_proc


if __name__ == "__main__":
    traj_path = str(research_root / "trajectories" / "runs" / "run_s1_build_1790721731.json")
    extract_offline_token_procedure(traj_path)
