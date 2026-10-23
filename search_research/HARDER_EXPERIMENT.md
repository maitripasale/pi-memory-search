# Harder search experiment: baseline calibration

18 synthetic questions: six practice and twelve evaluation, covering comments/history, override chains, terminology aliases, deployment scope, revision selection and missing information. Each task has its own corpus of 28 notebooks. Values and names differ across splits. Ground truth lives outside the worker directory. Fixtures are reference data, not programs to execute.

## Commands used
```powershell
# Generate the fixtures and verify every expected answer against source.
.\.venv-repl\Scripts\python.exe .\search_research\build_harder.py

# Check scoring accepts supported answers and rejects wrong values/evidence.
.\.venv-repl\Scripts\python.exe -m unittest discover -s search_research/tests -v

# Run Pi on all 18 questions with NO memory, using the existing provider.
.\.venv-repl\Scripts\python.exe .\search_research\run_harder.py

# Show the saved experiments visually; Refresh reloads completed runs.
.\.venv-repl\Scripts\python.exe .\search_research\dashboard.py
```
Run from the project root. The baseline consumes provider tokens; generating fixtures and testing scoring do not. No database is required. The baseline creates a new harder_baseline_* directory. To resume, pass --resume with that directory.

## Interpretation
This is difficulty calibration, not proof memory helps. Inspect failures and confirm they are actual worker mistakes rather than strict citation matching. Do not create lessons from held-out evaluation runs. If the baseline succeeds easily, expand corpus complexity before memory comparisons. Shared task families test near transfer only. Missing-information scoring checks unknown, not exhaustive search. Broad research still needs repeated trials, ordinary retrieval and policy ablations.

## Completed calibration

18 no-memory runs completed: 16 strict passes, two output/citation-format failures. Both failed runs found the correct underlying value. No tool errors. Search-error reduction has not been demonstrated. The 12 held-out tasks had 10 strict passes; all six practice tasks passed. Results are in runs/harder_baseline_a1ada4af48. Audit distinguishes formatting failures from incorrect search findings.
