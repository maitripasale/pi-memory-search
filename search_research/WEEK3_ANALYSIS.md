# Week 3: matched-task review of the pilot

This is a new analysis of the saved Week 2 trajectories. No new Pi runs were made.

| Memory | Fewer calls than no memory | Equal | More |
|---|---:|---:|---:|
| Procedural | 4 | 1 | 1 |
| Metacognitive | 3 | 0 | 3 |
| Both | 2 | 1 | 3 |

The routing_2 task is a large outlier: no memory used 12 calls and made two KeyErrors. Procedural used 4 calls; metacognitive used 3; both used 5. This single task accounts for much of the drop in average calls. Outside that task, metacognitive memory helped some questions and added steps to others. The combination was slower than no memory on three of six questions.

The useful distinction is answer quality versus efficiency. All numeric answers were correct. One combined-memory run cited the profile mapping rather than the calculation rule. The corrected audit accepts valid merge-rule citations uniformly while retaining the original scores. A grounded citation failure is different from a wrong computed value.

Next evaluation milestone: rerun matched tasks with the memory snapshot frozen and report results per task family, error type, evidence validity, calls, tokens and latency. Keep the repeated run count and budgets fixed. Test whether benefits survive without the routing_2 outlier. Then introduce stale/conflicting records and measure whether retrieval abstains or causes interference. No conclusion about reliable general improvement follows from the current one-repeat pilot.
