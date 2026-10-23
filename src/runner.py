"""
Baseline runner for Pi coding agent research.

Enforces:
- Complete memory isolation (no cross-session storage or retrieval)
- Pinned toolset (read, bash, edit, write)
- Full trajectory logging into JSON and JSONL event traces
- Non-interference with Optimus native runtime
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root and src are on sys.path
research_root = Path(__file__).resolve().parent.parent
if str(research_root) not in sys.path:
    sys.path.insert(0, str(research_root))
if str(research_root / "src") not in sys.path:
    sys.path.insert(0, str(research_root / "src"))

from evaluation.metrics import evaluate_task_outcome
from logger import TrajectoryLogger
from mock_server import start_mock_server


def setup_isolated_env(research_root: Path, mock_port: Optional[int] = None) -> Dict[str, str]:
    """
    Creates an isolated config directory (.pi_isolated) so Pi does not touch
    system or arkenOS config, and sets up custom-local provider for mock testing if requested.
    """
    isolated_dir = research_root / ".pi_isolated"
    isolated_dir.mkdir(parents=True, exist_ok=True)

    models_path = isolated_dir / "models.json"
    if mock_port:
        models_config = {
            "providers": {
                "custom-local": {
                    "name": "Local Mock Provider",
                    "baseUrl": f"http://127.0.0.1:{mock_port}/v1",
                    "api": "openai-completions",
                    "apiKey": "local-dummy-key",
                    "compat": {
                        "supportsDeveloperRole": False,
                        "supportsReasoningEffort": False,
                    },
                    "models": [
                        {
                            "id": "frozen-baseline-model",
                            "name": "Frozen Baseline Model",
                            "reasoning": False,
                            "contextWindow": 128000,
                            "maxTokens": 4096,
                        }
                    ],
                }
            }
        }
        with open(models_path, "w", encoding="utf-8") as f:
            json.dump(models_config, f, indent=2)
    elif not models_path.exists():
        # Ensure default particle-ai configuration exists
        particle_key = os.environ.get("ARKENOS_PARTICLE_AI_API_KEY", "")
        default_config = {
            "providers": {
                "particle-ai": {
                    "name": "Particle AI",
                    "baseUrl": "https://api.particle.ai/v1",
                    "api": "openai-completions",
                    "apiKey": particle_key,
                    "compat": {
                        "supportsDeveloperRole": False
                    },
                    "models": [
                        {
                            "id": "glm-5.3-flash",
                            "name": "GLM 5.3 Flash",
                            "reasoning": True,
                            "compat": {
                                "supportsReasoningEffort": False
                            },
                            "contextWindow": 1048576,
                            "maxTokens": 65536
                        }
                    ]
                }
            }
        }
        with open(models_path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=2)

    # Clean settings.json
    settings_path = isolated_dir / "settings.json"
    if not settings_path.exists():
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump({"lastChangelogVersion": "0.74.2"}, f, indent=2)

    # Clean auth.json
    auth_path = isolated_dir / "auth.json"
    if not auth_path.exists():
        with open(auth_path, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)

    env = os.environ.copy()
    env["PI_CODING_AGENT_DIR"] = str(isolated_dir)
    env["PI_ALLOW_BROWSER_COOKIES"] = "0"
    env["PI_OFFLINE"] = "0"
    if "ARKENOS_PARTICLE_AI_API_KEY" not in env:
        env["ARKENOS_PARTICLE_AI_API_KEY"] = ""
    return env


def run_baseline_task(
    task_path: str,
    config_path: str,
    run_id: Optional[str] = None,
    provider_override: Optional[str] = None,
    model_override: Optional[str] = None,
    prompt_override: Optional[str] = None,
    injected_memory: Optional[Dict[str, Any]] = None,
    mock_mode: bool = False,
    mock_port: int = 8765,
) -> Dict[str, Any]:
    research_root = Path(__file__).resolve().parent.parent

    # Load task
    with open(task_path, "r", encoding="utf-8") as f:
        task = json.load(f)
    task_id = task.get("task_id", "unknown_task")

    # Load experiment config
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    if not run_id:
        run_id = f"run_{task_id}_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    session_id = f"sess_{run_id}"

    # Setup isolated task execution workspace
    run_workspace = research_root / "workspace_runs" / run_id
    if run_workspace.exists():
        shutil.rmtree(run_workspace)
    run_workspace.mkdir(parents=True, exist_ok=True)

    # Write task setup files if any
    for rel_path, content in task.get("setup", {}).get("files", {}).items():
        dest = run_workspace / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            f.write(content)

    # Start mock server if mock_mode
    mock_server_instance = None
    if mock_mode:
        mock_server_instance = start_mock_server(mock_port)
        time.sleep(0.1)

    env = setup_isolated_env(research_root, mock_port if mock_mode else None)

    # Assemble Pi command line
    model_info = config.get("model", {})
    provider = "custom-local" if mock_mode else (provider_override or model_info.get("provider", "particle-ai"))
    model_id = "frozen-baseline-model" if mock_mode else (model_override or model_info.get("model_id", "glm-5.3-flash"))

    tools_whitelist = ",".join(config.get("agent", {}).get("tools", ["read", "bash", "edit", "write"]))

    prompt_to_run = prompt_override if prompt_override is not None else task["prompt"]

    cmd = [
        "node",
        str(research_root / "node_modules" / "@earendil-works" / "pi-coding-agent" / "dist" / "cli.js"),
        "-p",
        "--mode", "json",
        "--no-session",
        "--no-context-files",
        "--no-extensions",
        "--no-skills",
        "--no-prompt-templates",
        "--tools", tools_whitelist,
        "--provider", provider,
        "--model", model_id,
        prompt_to_run,
    ]

    start_time = time.time()
    start_time_iso = datetime.now(timezone.utc).isoformat()

    events: List[Dict[str, Any]] = []
    tool_calls: List[Dict[str, Any]] = []
    observations: List[Dict[str, Any]] = []
    final_response_parts: List[str] = []
    token_usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_write_tokens": 0,
        "total_tokens": 0,
    }

    error_msg: Optional[str] = None
    returncode = 0

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(run_workspace),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        stdout, stderr = proc.communicate(timeout=config.get("execution", {}).get("timeout_seconds", 60))
        returncode = proc.returncode

        # Parse JSONL events from stdout
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                events.append(event)

                # Capture message content, tool calls, results, and tokens
                event_type = event.get("type")
                if event_type == "message_end":
                    msg = event.get("message", {})
                    role = msg.get("role")
                    if role == "assistant":
                        usage = msg.get("usage", {})
                        if usage:
                            token_usage["input_tokens"] += usage.get("input", 0)
                            token_usage["output_tokens"] += usage.get("output", 0)
                            token_usage["cache_read_tokens"] += usage.get("cacheRead", 0)
                            token_usage["cache_write_tokens"] += usage.get("cacheWrite", 0)
                            token_usage["total_tokens"] += usage.get("totalTokens", 0)
                        for c in msg.get("content", []):
                            if isinstance(c, dict):
                                c_type = c.get("type")
                                if c_type == "text":
                                    final_response_parts.append(c.get("text", ""))
                                elif c_type == "toolCall":
                                    tool_calls.append({
                                        "id": c.get("id"),
                                        "name": c.get("name"),
                                        "arguments": c.get("arguments"),
                                    })
                    elif role == "toolResult":
                        observations.append(msg)
                elif event_type == "turn_end":
                    # Fallback usage if present in turn_end
                    usage = event.get("usage", {})
                    if usage and token_usage["total_tokens"] == 0:
                        token_usage["input_tokens"] += usage.get("input", 0)
                        token_usage["output_tokens"] += usage.get("output", 0)
                        token_usage["cache_read_tokens"] += usage.get("cacheRead", 0)
                        token_usage["cache_write_tokens"] += usage.get("cacheWrite", 0)
                        token_usage["total_tokens"] += usage.get("totalTokens", 0)

            except json.JSONDecodeError:
                events.append({"type": "raw_output", "raw": line})

        if returncode != 0 and stderr:
            error_msg = stderr.strip()

    except subprocess.TimeoutExpired:
        proc.kill()
        error_msg = f"Task execution exceeded {config.get('execution', {}).get('timeout_seconds', 60)}s timeout"
        returncode = -1
    except Exception as ex:
        error_msg = str(ex)
        returncode = -1
    finally:
        if mock_server_instance:
            mock_server_instance.shutdown()
            mock_server_instance.server_close()

    end_time = time.time()
    end_time_iso = datetime.now(timezone.utc).isoformat()
    duration_ms = round((end_time - start_time) * 1000, 2)

    final_response = "\n".join(final_response_parts).strip()

    # Evaluate task outcome
    eval_result = evaluate_task_outcome(task, str(run_workspace), final_response)
    if error_msg and not eval_result.get("error"):
        eval_result["error"] = error_msg

    # Record trajectory
    logger = TrajectoryLogger(str(research_root / "trajectories" / "runs"))
    saved_paths = logger.record_run(
        run_id=run_id,
        task_id=task_id,
        session_id=session_id,
        start_time_iso=start_time_iso,
        end_time_iso=end_time_iso,
        duration_ms=duration_ms,
        model_config={"provider": provider, "model_id": model_id},
        experiment_config=config,
        prompts=[{"role": "user", "content": prompt_to_run}],
        tool_calls=tool_calls,
        observations=observations,
        events=events,
        final_response=final_response,
        evaluation=eval_result,
        token_usage=token_usage,
        latency_ms=duration_ms,
        cost_usd=0.0,
        error=error_msg,
        injected_memory=injected_memory,
    )

    return {
        "run_id": run_id,
        "task_id": task_id,
        "command": " ".join(cmd),
        "command_args": cmd,
        "provider": provider,
        "model": model_id,
        "success": eval_result.get("success", False),
        "score": eval_result.get("score", 0.0),
        "duration_ms": duration_ms,
        "token_usage": token_usage,
        "eval_result": eval_result,
        "saved_paths": saved_paths,
        "error": error_msg,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run frozen no-memory Pi baseline task")
    parser.add_argument("--task", default="tasks/dataset/smoke_test.json", help="Path to task JSON")
    parser.add_argument("--config", default="configs/baseline_frozen.json", help="Path to config JSON")
    parser.add_argument("--run-id", default=None, help="Custom run ID")
    parser.add_argument("--provider", default=None, help="Provider override (e.g. particle-ai)")
    parser.add_argument("--model", default=None, help="Model override (e.g. deepseek-v4.1-flash, glm-5.3-flash)")
    parser.add_argument("--mock", action="store_true", default=False, help="Use local mock server")
    parser.add_argument("--port", type=int, default=8765, help="Mock server port")
    args = parser.parse_args()

    result = run_baseline_task(
        task_path=args.task,
        config_path=args.config,
        run_id=args.run_id,
        provider_override=args.provider,
        model_override=args.model,
        mock_mode=args.mock,
        mock_port=args.port,
    )

    print(json.dumps(result, indent=2))
    sys.exit(0 if result["success"] else 1)
