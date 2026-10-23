# Evaluation Framework

This directory houses the scoring logic and evaluation metrics for comparing memory configurations against the frozen baseline.

## Target Metrics
1. **Task Success**: Binary / graded completion of coding and retrieval benchmarks
2. **Grounded Factual Accuracy**: Verification against task ground truth
3. **Memory Relevance**: Precision/recall of injected memories
4. **Interference Score**: Degradation caused by irrelevant or conflicting memories
5. **Stale Memory Errors**: Failures due to out-of-date retrieved facts
6. **Tokens**: Input, output, reasoning, cache read/write, total
7. **Latency**: End-to-end execution duration (ms)
8. **Cost**: USD computation per run based on provider pricing
9. **Repeated-Run Uncertainty**: Mean, variance, std-dev, and stderr across seeds

## Protocol Rules
- **Holdout Separation**: Tasks in `task_splits/v1_splits.json` designate memory-building vs. held-out evaluation tasks.
- **No Evaluation Data Leakage**: Ground-truth answers in `hidden_evaluation_data` are strictly excluded from agent prompts, tool outputs, and memory persistence.
- **Budget Parity**: Any memory adapter tested must operate within identical token and storage boundaries.
