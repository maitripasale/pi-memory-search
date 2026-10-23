"""JSON-lines bridge to one genuine Jupyter kernel per Pi session."""
import argparse
import json
import os
import queue
import sys
import time
from pathlib import Path

from jupyter_client import KernelManager
import nbformat


class NotebookSession:
    def __init__(self, cwd, notebook):
        self.cwd = str(Path(cwd).resolve())
        self.path = Path(notebook).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            raise ValueError('Use a new notebook path for a new session')
        self.nb = nbformat.v4.new_notebook(metadata={'kernelspec': {
            'name': 'python3', 'display_name': 'Pi research Python', 'language': 'python'}})
        self.km = None
        self.kc = None
        self.start()
        self.save()

    def start(self):
        self.km = KernelManager()
        self.km.kernel_spec.argv = [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}']
        self.km.start_kernel(cwd=self.cwd, stdout=sys.stderr, stderr=sys.stderr)
        self.kc = self.km.blocking_client()
        self.kc.start_channels()
        self.kc.wait_for_ready(timeout=30)

    def save(self):
        tmp = self.path.with_suffix('.tmp')
        nbformat.write(self.nb, str(tmp))
        os.replace(tmp, self.path)

    def close(self):
        if self.kc:
            self.kc.stop_channels()
        if self.km:
            self.km.shutdown_kernel(now=True)
        self.kc = self.km = None

    def reset(self):
        self.close()
        self.start()
        self.nb.cells.append(nbformat.v4.new_markdown_cell('Kernel reset: previous variables cleared.'))
        self.save()
        return {'ok': True, 'text': 'Kernel reset. Previous variables cleared.', 'notebook': str(self.path)}

    def execute(self, code, timeout=30):
        if not isinstance(code, str) or not code.strip() or len(code) > 50000:
            raise ValueError('Code must contain 1 to 50000 characters')
        timeout = max(1, min(float(timeout), 60))
        cell = nbformat.v4.new_code_cell(code)
        self.nb.cells.append(cell)
        self.save()
        mid = self.kc.execute(code, allow_stdin=False, stop_on_error=True)
        deadline = time.monotonic() + timeout
        ok, texts, output_size = True, [], 0
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                ok = False
                cell.outputs.append(nbformat.v4.new_output('error', ename='CellTimeout',
                    evalue=f'Exceeded {timeout}s; kernel reset', traceback=[]))
                texts.append(f'Cell timed out after {timeout}s. Kernel reset; variables cleared.')
                self.close()
                self.start()
                self.nb.cells.append(nbformat.v4.new_markdown_cell('Kernel reset after timeout.'))
                break
            try:
                msg = self.kc.get_iopub_msg(timeout=min(remaining, 0.5))
            except queue.Empty:
                continue
            if msg.get('parent_header', {}).get('msg_id') != mid:
                continue
            kind, content = msg['msg_type'], msg['content']
            if kind == 'status' and content.get('execution_state') == 'idle':
                break
            if kind == 'execute_input':
                cell.execution_count = content['execution_count']
            elif kind in ('stream', 'execute_result', 'display_data', 'error'):
                text = content.get('text', content.get('data', {}).get('text/plain', ''))
                if kind == 'error':
                    ok = False
                    text = content.get('ename', '') + ': ' + content.get('evalue', '')
                if output_size < 100000:
                    output = nbformat.v4.output_from_msg(msg)
                    # Bound rich output too. Save a text placeholder for oversized messages.
                    if len(json.dumps(output)) + output_size > 100000:
                        output = nbformat.v4.new_output('stream', name='stdout', text='[Output truncated]\n')
                    cell.outputs.append(output)
                    output_size += len(json.dumps(output))
                    texts.append(text[:12000])
        self.save()
        return {'ok': ok, 'text': ('\n'.join(texts) or '(Cell completed without printed output)')[:12000],
                'cell': len(self.nb.cells), 'notebook': str(self.path)}

    def history(self, last=5):
        cells = self.nb.cells[-max(1, min(int(last), 20)):]
        return {'ok': True, 'text': json.dumps([{'source': c.source, 'outputs': c.get('outputs', [])}
                for c in cells], ensure_ascii=False)[-20000:], 'notebook': str(self.path)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cwd', required=True)
    parser.add_argument('--notebook', required=True)
    args = parser.parse_args()
    session = None
    try:
        session = NotebookSession(args.cwd, args.notebook)
        for line in sys.stdin:
            req = {}
            try:
                req = json.loads(line)
                action = req.get('action', 'execute')
                if action == 'execute':
                    result = session.execute(req['code'], req.get('timeout', 30))
                elif action == 'history':
                    result = session.history(req.get('last', 5))
                elif action == 'reset':
                    result = session.reset()
                elif action == 'shutdown':
                    break
                else:
                    raise ValueError('Unknown action')
                print(json.dumps(dict(result, id=req.get('id'))), flush=True)
            except Exception as exc:
                print(json.dumps({'id': req.get('id'), 'ok': False, 'text': str(exc)}), flush=True)
    finally:
        if session:
            session.close()

if __name__ == '__main__':
    main()
