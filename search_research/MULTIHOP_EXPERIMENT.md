# Multi-file memory comparison

Version 3.0.0: three practice questions, six held-out questions, 96 notebooks per question. Families: release-to-policy routing and arithmetic, terminology-to-profile-to-unit conversion, and revision/region/disabled-overlay precedence. Each question asks for source-backed input values and the final value. Names, values and layouts differ between practice and evaluation.

Pi chooses its own Python search code. No artificial failed tool or instructed bad query is added. Tools, request/cell/time limits and provider/model stay equal across conditions. The only condition difference is the memory block. Memory is generated only from practice traces, then frozen. Unsupported metacognitive candidates are rejected; an empty metacognitive condition is reported honestly.

## Commands, from the project root
```powershell
# Generate fixtures and verify source anchors.
.\.venv-repl\Scripts\python.exe .\search_research\build_multihop.py

# Three practice runs, memory review, then six questions x four conditions.
.\.venv-repl\Scripts\python.exe .\search_research\run_multihop.py

# Optional future repetition study: starts a new experiment with 72 held-out runs.
.\.venv-repl\Scripts\python.exe .\search_research\run_multihop.py --repeats 3
```
The first experiment has one repetition per condition: it is a pilot, not strong evidence of improvement. Model calls consume provider tokens; pricing is unavailable. Review failures against raw outputs before claiming search mistakes. The grader validates selected evidence anchors, not every intermediate reasoning step. Synthetic shared families establish near transfer only. Do not use held-out failures to write memory for this same evaluation.

Dashboard: http://127.0.0.1:8765. Refresh to reload completed runs, and select the multihop_* experiment. Frozen memories and review records are saved alongside run logs. No new database is needed.

## Completed pilot

Run: multihop_a9aff89630. Three practice runs produced two procedural lessons and one metacognitive lesson. One practice task had repeated path-key lookup errors. The 24 held-out runs used fresh sessions and frozen memory.

| Condition | Evidence-valid tasks | Mean tool calls | Tool errors |
|---|---:|---:|---:|
| No memory | 6/6 | 6.00 | 2 |
| Procedural | 6/6 | 4.33 | 1 |
| Metacognitive | 6/6 | 5.00 | 0 |
| Both | 5/6 | 6.83 | 1 |

All numeric answers were correct. The both condition lost one evidence-valid task because it cited a profile mapping rather than the documented calculation rule. This is a citation-compliance failure, not a wrong numeric answer.

An audit found the initial override scorer wrongly rejected the rule citations required by the prompt. Evidence audit v3.0.1 accepts the exact merge-rule source when requested input values have valid evidence. It applies uniformly across all conditions. Eight scores changed; original run.json evaluations and REPORT.md remain intact. AUDITED_REPORT.md and evaluation.audited.json hold corrected results. The reviewer and memory snapshot were not regenerated after the audit.

These are efficiency/error-count signals from six matched questions with one repetition, not proof of general improvement or harmful interference. More repetitions are required. Provider cost is unknown; logs count practice, review and evaluation tokens.

```powershell
# Audit the saved evidence scores, with no model calls.
.\.venv-repl\Scripts\python.exe .\search_research\audit_multihop.py --run .\search_research\runs\multihop_a9aff89630

# Print the saved lessons and corrected comparison, with no model calls.
.\.venv-repl\Scripts\python.exe .\search_research\show_demo.py --run .\search_research\runs\multihop_a9aff89630
```
