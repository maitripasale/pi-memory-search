# Pi agent Jupyter REPL

Implemented in `extensions/jupyter-repl.ts` and `src/jupyter_bridge.py`.

## Start

From this project directory, run `./start-repl.cmd` in PowerShell.
Ask Pi to use `python_cell` to run Python. Variables persist across cells in that Pi session.
`python_history` reads recent code and outputs. `python_reset` clears variables and retains saved cells.
Notebooks are written under `notebooks/` in the working directory. Open `.ipynb` files in a Jupyter-compatible notebook editor.
A new Pi session starts a new kernel; old notebook variables are not restored automatically.

## Demonstration

`./.venv-repl/Scripts/python.exe src/run_repl_demo.py`

This makes model calls using the existing isolated Particle AI configuration and GLM 5.3 Flash.
The model uses an exact search that returns no matches, then normalizes punctuation in a second cell and finds the match. It reads the history and saves a small result file.
The steps are prescribed. This verifies the REPL tools, not autonomous discovery or improved memory.

Completed demonstration: `results/repl_demo_82989b42/summary.json`.
The associated notebook and full Pi event log are in that directory.

## Local checks

`./.venv-repl/Scripts/python.exe src/test_jupyter_bridge.py`

Checks real-kernel variable persistence, errors and recovery, history, explicit reset, timeout recovery, and valid notebook output. All passed.
Dependencies are isolated in `.venv-repl`; exact versions are in `requirements-repl.lock.txt`.

## Execution and limits

The kernel runs on this computer with the user's permissions. It is not a sandbox.
Code can read and write files in the same way as a local Python process.
Cells time out after 30 seconds by default (maximum 60); a timeout resets the kernel.
Outputs are bounded; large outputs are truncated. Stdin prompts are disabled.
Cancellation is checked before queued cells start. A running cell may finish or reach its timeout after the Pi turn is cancelled.
Normal Pi shutdown closes the bridge and kernel. Abrupt OS process termination is not a supported cleanup guarantee.

## Research integration

Use the same REPL tools in both memory and no-memory conditions.
Keep notebook state within one run. Start a new kernel for each evaluation run.
Extract future lessons only from the practice stream. Keep evaluation notebooks out of memory building.
This extension does not automatically modify AGENTS.md or SKILL.md and does not implement metacognitive memory.
