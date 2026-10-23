# Agent search memory prototype

This project tests procedural and metacognitive memory around Pi 0.74.2 with GLM 5.3 Flash on Particle AI.

## What is implemented

1. Pi chooses and writes its own Python search code in a persistent Jupyter kernel.
2. Each practice task produces a notebook, tool-call log, answer, and source-based score.
3. A separate call to the same model reviews only practice traces and proposes lessons.
4. The store validates practice provenance and requires observed problems for metacognitive candidates.
5. A frozen memory snapshot supplies selected lessons to fresh evaluation sessions.
6. The runner compares no memory, procedural, metacognitive, and both on identical questions.

The worker is not given a sequence of search steps. There are no supplied fuzzy or lexical search functions. It may write its own local code and indexes. Nothing automatically edits AGENTS.md or SKILL.md yet.

## Dataset

Public source: https://github.com/HandsOnLLM/Hands-On-Large-Language-Models
Pinned commit: ea3390819997999a51983677b80b3aac4dc50ada
Apache-2.0 LICENSE is retained in dataset_v1/corpus/LICENSE.

Three practice questions use Chapters 4 and 10. Three evaluation questions use Chapters 5, 8 and 11. Notebook example programs are not executed. Search tools inspect notebook source cells.

Gold is verified against exact source cells, including an absent parameter check. The scorer accepts a corpus/ path prefix, namespace aliases where documented, and exact evidence excerpts. Scores are narrow benchmark scores, not a universal semantic judge.

## Run

From C:\Users\pasal\Desktop\pi-memory-research in PowerShell:

```powershell
# Local checks: no model calls
.\.venv-repl\Scripts\python.exe -m unittest discover -s search_research/tests -v

# Full pilot: three practice sessions, reviewer, twelve evaluation sessions
.\.venv-repl\Scripts\python.exe search_research/experiment.py --repeats 1

# Reuse an existing practice snapshot and test on fresh sessions
.\.venv-repl\Scripts\python.exe search_research/experiment.py --from-practice search_research/runs/experiment_44e37b8b50 --repeats 1
```

These runs use the already configured .pi_isolated provider credentials and incur API usage. No API key needs to be pasted into a command.

## Files to show in a meeting

- A practice run's notebooks/*.ipynb: the agent's actual code and output.
- review.json: proposed and rejected lessons plus evidence IDs.
- memories.json: the frozen memory records.
- An evaluation run's retrieval.json: exactly what was injected.
- That run's notebook and run.json: what the agent actually did.
- REPORT.md: all four conditions on the same questions.

Use show_demo.py to print the latest completed comparison without making model calls.

## Controls

Each condition receives the same corpus, model ID, system instructions and tools. Each run gets a fresh process, kernel, working directory and empty memory-bin. Only the selected memory block differs. Order is shuffled with a fixed seed.

Limits: 18 tool attempts, 10 model requests, 100000 serialized input bytes per request, 4096 output tokens per request, 180 seconds per run, and 3000 memory bytes. The combined condition shares the same total memory budget. UTF-8 bytes provide a conservative injection bound rather than claiming exact model-token counting. temperature=0 and max_tokens are applied to request payloads; the provider may still be nondeterministic.

The manifest records code hashes, Pi version, corpus revision and budgets. Full notebooks and JSONL events allow inspection. Reviewer and practice tokens are recorded separately from evaluation tokens. Provider cost data is unavailable and is not reported as zero.

## Memory lifecycle

memory.py implements write, retrieve, revise and forget. Records contain type, scope, trigger, source evidence, timestamps, versions and optional expiry/conflict keys. Revised records are withheld until reviewed. Expired, forgotten and explicitly conflicting records are excluded from retrieval. Unit tests exercise these operations; their end-task effect is not evaluated in the small pilot.

## Important limits

- One run per condition on three questions gives a demonstration, not reliable evidence of improvement.
- Empty-result uncertainty is distinct from a measured recurring model weakness.
- Memory injection does not prove the agent followed or benefited from a lesson.
- Candidate provenance is checked; semantic usefulness still needs evaluation and review.
- Notebook snippets may have appeared in model training.
- Filesystem separation is not an OS sandbox. Gold is withheld from normal prompts/work directories, but there is no enforced filesystem boundary against deliberate traversal.
- Public source content is treated as untrusted data in the prompt; this is not a tested prompt-injection defense.
- No ordinary-retrieval baseline, larger held-out split, or write-policy/retrieval-policy ablation has been completed yet.
- The prototype does not automatically fetch tools, modify model weights, or edit project instructions.

## Next research work

Add more varied questions and repeated matched trials; ordinary retrieval as a separate baseline; irrelevant, stale and conflicting memory conditions; independently vary write and retrieval policies. Expand beyond a single corpus. Measure repeated named error classes across comparable task opportunities instead of claiming any drop in total errors demonstrates learning.
