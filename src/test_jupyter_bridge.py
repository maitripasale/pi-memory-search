"""Integration checks using a real kernel; no model calls."""
import sys
import uuid
from pathlib import Path
import nbformat
from jupyter_bridge import NotebookSession

root = Path(__file__).resolve().parents[1]
folder = root / 'results' / ('repl_test_' + uuid.uuid4().hex[:8])
folder.mkdir(parents=True)
s = NotebookSession(folder, folder / 'test.ipynb')
try:
    assert s.execute('values = [2, 4, 6]')['ok']
    assert s.execute('sum(values)')['text'].strip() == '12'
    failed = s.execute('1 / 0')
    assert not failed['ok'] and 'ZeroDivisionError' in failed['text']
    assert s.execute('sum(values) + 1')['text'].strip() == '13'
    assert '1 / 0' in s.history()['text']
    s.reset()
    assert 'False' in s.execute("'values' in globals()")['text']
    timed = s.execute('import time; time.sleep(5)', timeout=1)
    assert not timed['ok'] and 'timed out' in timed['text']
    assert s.execute('6 * 7')['text'].strip() == '42'
    nbformat.validate(nbformat.read(str(s.path), as_version=4))
    print('PASS: persistence, errors, recovery, history, reset, timeout recovery, notebook format')
    print(s.path)
finally:
    s.close()
